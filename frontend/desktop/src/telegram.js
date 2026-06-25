// Telegram 發布（純前端直連）— PWA 直接呼叫 api.telegram.org，bot token 與 chat_id
// 存於手機本機，不需任何開發者後端。Telegram Bot API 回應含 CORS 標頭，瀏覽器可直接呼叫。
//
// 移植自原後端 publish_service.py 的 Telegram 邏輯：
//   無圖 → sendMessage；1 張 → sendPhoto；多張 → sendMediaGroup（相簿）。
//   文字未超過 caption 上限（1024）時當圖片說明文字，否則圖片送完再補一則純文字。

const CAPTION_MAX = 1024
const MEDIA_GROUP_MAX = 10

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
export async function sendText(token, chatId, text) {
  if (!chatId) throw new Error('尚未設定群組編號')
  return tgCall(token, 'sendMessage', { chat_id: chatId, text })
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

  if (files.length === 1) {
    const fd = new FormData()
    fd.append('chat_id', chatId)
    if (caption) fd.append('caption', caption)
    fd.append('photo', files[0])
    await tgCall(token, 'sendPhoto', fd, true)
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
    await tgCall(token, 'sendMediaGroup', fd, true)
  }

  // 文字過長未能當說明文字時，圖片送完補一則純文字。
  if (text && !captionInline) await sendText(token, chatId, text)
}
