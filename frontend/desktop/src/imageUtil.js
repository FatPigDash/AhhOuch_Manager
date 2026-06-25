// 圖片最佳化（M3）— 匯入時等比縮放並重新編碼，降低本機儲存量，
// 以支撐「預設 2000 張圖片」的容量基準（計畫 §6.3 / D5）。
//
// 每張圖片產出兩份：
//   full  — 完整圖（最長邊 ≤ MAX_FULL），供燈箱檢視與發布排版使用。
//   thumb — 縮圖（最長邊 ≤ MAX_THUMB），供卡片列表與編輯頁網格快速顯示。

const MAX_FULL = 1600   // 完整圖最長邊（px）
const MAX_THUMB = 400   // 縮圖最長邊（px）
const FULL_QUALITY = 0.85
const THUMB_QUALITY = 0.7
const OUT_MIME = 'image/jpeg'

// 解碼成可繪製來源；優先用 createImageBitmap（較快、可依 EXIF 自動轉正），
// 不支援時退回 HTMLImageElement。
async function decode(blob) {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(blob, { imageOrientation: 'from-image' })
    } catch { /* 部分瀏覽器不支援第二參數，往下退回 */ }
  }
  return await new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('圖片解碼失敗')) }
    img.src = url
  })
}

function fit(srcW, srcH, max) {
  if (srcW <= max && srcH <= max) return { w: srcW, h: srcH }
  const r = srcW > srcH ? max / srcW : max / srcH
  return { w: Math.max(1, Math.round(srcW * r)), h: Math.max(1, Math.round(srcH * r)) }
}

function render(source, max, quality) {
  const sw = source.width, sh = source.height
  const { w, h } = fit(sw, sh, max)
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  // JPEG 無透明度；先鋪白底，避免透明 PNG 轉檔後出現黑色背景。
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, w, h)
  ctx.drawImage(source, 0, 0, w, h)
  return new Promise((resolve) => canvas.toBlob((b) => resolve(b), OUT_MIME, quality))
}

// 將輸入圖片（File / Blob）最佳化為 { full, thumb }。
// 任一步驟失敗時退回原圖，確保上傳不會因最佳化而中斷。
export async function processImage(input) {
  try {
    const source = await decode(input)
    const full = await render(source, MAX_FULL, FULL_QUALITY)
    const thumb = await render(source, MAX_THUMB, THUMB_QUALITY)
    if (source.close) source.close()
    return {
      full: full || input,
      thumb: thumb || full || input,
    }
  } catch {
    return { full: input, thumb: input }
  }
}
