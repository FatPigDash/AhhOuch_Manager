// Telegram 發布（純前端直連）— PWA 直接呼叫 api.telegram.org，bot token 與 chat_id
// 存於手機本機，不需任何開發者後端。Telegram Bot API 回應含 CORS 標頭，瀏覽器可直接呼叫。
//
// 移植自原後端 publish_service.py 的 Telegram 邏輯：
//   無圖 → sendMessage；1 張 → sendPhoto；多張 → sendMediaGroup（相簿）。
//   文字未超過 caption 上限（1024）時當圖片說明文字，否則圖片送完再補一則純文字。

const CAPTION_MAX = 1024
const MEDIA_GROUP_MAX = 10

// 判斷 Telegram API 錯誤是否為「訊息已被刪除或不存在」。
// 用於覆蓋模式：若原訊息已刪，自動回退為發布新訊息。
export function isMessageNotFoundError(e) {
  const msg = (e?.message || '').toLowerCase()
  return (
    msg.includes('message to edit not found') ||
    msg.includes('message_id_invalid') ||
    msg.includes('message not found')
  )
}


async function tgCall(token, method, body, isForm) {
  if (!token) throw new Error('尚未設定機器人金鑰')
  const url = `https://api.telegram.org/bot${token}/${method}`
  // 重要：不要用 application/json，否則會觸發 CORS preflight(OPTIONS)，而 Telegram Bot API
  // 不回應 preflight，瀏覽器直連會失敗。改用 CORS 安全清單內的內容型別（不需 preflight）：
  //   一般呼叫 → URLSearchParams（application/x-www-form-urlencoded）
  //   含圖片   → FormData（multipart/form-data）
  let opts
  if (isForm) {
    opts = { method: 'POST', body }
  } else {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(body)) params.append(k, v)
    opts = { method: 'POST', body: params }
  }
  let resp
  try {
    resp = await fetch(url, opts)
  } catch (e) {
    throw new Error('連線 Telegram 失敗，請檢查網路。')
  }
  const data = await resp.json().catch(() => null)
  if (!data || !data.ok) {
    throw new Error(data?.description || `Telegram 回應錯誤（HTTP ${resp.status}）`)
  }
  return data.result
}

// 發送純文字（班表）。
export async function sendText(token, chatId, text, opts = {}) {
  if (!chatId) throw new Error('尚未設定群組編號')
  const body = { chat_id: chatId, text }
  if (opts.parse_mode) body.parse_mode = opts.parse_mode
  return tgCall(token, 'sendMessage', body)
}

// 發送班表純文字並回傳 messageId（供記錄 TG 訊息連結）。
export async function sendScheduleText(token, chatId, text, opts = {}) {
  if (!chatId) throw new Error('尚未設定群組編號')
  const body = { chat_id: chatId, text }
  if (opts.parse_mode) body.parse_mode = opts.parse_mode
  const result = await tgCall(token, 'sendMessage', body)
  return { messageId: result?.message_id }
}

// 覆蓋模式：以新內容取代現有班表訊息（純文字）。
export async function editScheduleText(token, chatId, messageId, text, opts = {}) {
  if (!chatId) throw new Error('尚未設定群組編號')
  if (!messageId) throw new Error('找不到原訊息編號，無法覆蓋')
  const body = { chat_id: chatId, message_id: messageId, text }
  if (opts.parse_mode) body.parse_mode = opts.parse_mode
  return tgCall(token, 'editMessageText', body)
}


// 發送卡片：files 為 File/Blob 陣列（可空），text 為文字（可空）。
export async function sendCard(token, chatId, files, text) {
  if (!chatId) throw new Error('尚未設定群組編號')
  text = text || ''
  files = files || []
  if (files.length > MEDIA_GROUP_MAX) throw new Error(`一次最多發送 ${MEDIA_GROUP_MAX} 張圖片`)
  if (!files.length) return sendText(token, chatId, text)

  const captionInline = !!text && text.length <= CAPTION_MAX
  const caption = captionInline ? text : ''

  let messageId
  if (files.length === 1) {
    const fd = new FormData()
    fd.append('chat_id', chatId)
    if (caption) fd.append('caption', caption)
    fd.append('photo', files[0])
    const result = await tgCall(token, 'sendPhoto', fd, true)
    messageId = result?.message_id
  } else {
    const fd = new FormData()
    fd.append('chat_id', chatId)
    const media = files.map((f, i) => {
      const key = `file${i}`
      fd.append(key, f)
      const item = { type: 'photo', media: `attach://${key}` }
      if (i === 0 && caption) item.caption = caption
      return item
    })
    fd.append('media', JSON.stringify(media))
    const result = await tgCall(token, 'sendMediaGroup', fd, true)
    messageId = Array.isArray(result) ? result[0]?.message_id : result?.message_id
  }

  // 文字過長未能當說明文字時，圖片送完補一則純文字。
  if (text && !captionInline) await sendText(token, chatId, text)
  return { messageId }
}

// 覆蓋模式：以新內容取代現有訊息。
// files 為空   → editMessageText（純文字）
// files 1 張   → editMessageMedia（換圖 + 說明文字）
// files 多張   → editMessageCaption（只更新說明，圖片群無法整批換）
// 若 API 回報類型不符，自動 fallback 到另一種方式。
export async function editCard(token, chatId, messageId, files, text) {
  if (!chatId) throw new Error('尚未設定群組編號')
  if (!messageId) throw new Error('找不到原訊息編號，無法覆蓋')
  text = text || ''
  files = files || []

  if (!files.length) {
    // 純文字訊息：直接 editMessageText
    try {
      return await tgCall(token, 'editMessageText', { chat_id: chatId, message_id: messageId, text })
    } catch (_) {
      // 原訊息可能是媒體訊息，改用 editMessageCaption
      const caption = text.slice(0, CAPTION_MAX)
      return await tgCall(token, 'editMessageCaption', { chat_id: chatId, message_id: messageId, caption })
    }
  }

  if (files.length === 1) {
    // 單張圖片：用 editMessageMedia 同時換圖與說明文字
    const captionInline = text.length <= CAPTION_MAX
    const fd = new FormData()
    fd.append('chat_id', chatId)
    fd.append('message_id', messageId)
    const mediaObj = { type: 'photo', media: 'attach://photo' }
    if (captionInline && text) mediaObj.caption = text
    fd.append('media', JSON.stringify(mediaObj))
    fd.append('photo', files[0])
    try {
      await tgCall(token, 'editMessageMedia', fd, true)
    } catch (_) {
      // 原訊息為純文字，改用 editMessageText
      await tgCall(token, 'editMessageText', { chat_id: chatId, message_id: messageId, text })
    }
    return
  }

  // 多張圖片：Telegram 不支援整組換圖，僅更新第一則的說明文字
  const caption = text.slice(0, CAPTION_MAX)
  try {
    return await tgCall(token, 'editMessageCaption', { chat_id: chatId, message_id: messageId, caption })
  } catch (_) {
    return await tgCall(token, 'editMessageText', { chat_id: chatId, message_id: messageId, text })
  }
}

