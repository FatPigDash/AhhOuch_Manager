// Web Share API 封裝（M4）— 透過手機原生分享選單傳送至 LINE 等社群軟體。
// 開發者不維護任何發布端點；分享在使用者手機端本機完成（計畫 §4.3）。
//
// 注意：navigator.share 必須在使用者手勢（如點擊）中直接呼叫，否則會被瀏覽器拒絕；
// 故各視窗的分享按鈕直接呼叫此處函式，不經非同步包裝延遲。

export function canShare() {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

// 是否能攜帶檔案（圖片）分享；iOS 15+ Safari 與 Android Chrome 支援，舊版可能僅支援文字。
export function canShareFiles(files) {
  return canShare() && typeof navigator.canShare === 'function' && navigator.canShare({ files })
}

// 統一分享入口。回傳：
//   'shared'      成功送出
//   'cancelled'   使用者在分享選單中取消
//   'unsupported' 此裝置不支援 Web Share
// 不支援的檔案會由呼叫端先行剔除（見 canShareFiles），此處只負責送出。
export async function share({ title, text, files }) {
  if (!canShare()) return 'unsupported'
  const payload = {}
  if (title) payload.title = title
  if (text) payload.text = text
  if (files && files.length) payload.files = files
  try {
    await navigator.share(payload)
    return 'shared'
  } catch (e) {
    if (e && e.name === 'AbortError') return 'cancelled'
    throw e
  }
}

// 將圖片 Object URL 轉為 File[]，供 share({ files }) 使用。
export async function urlsToFiles(urls, baseName = 'image') {
  const files = []
  for (let i = 0; i < urls.length; i++) {
    if (!urls[i]) continue
    const blob = await fetch(urls[i]).then((r) => r.blob())
    const ext = (blob.type.split('/')[1] || 'jpg').replace('jpeg', 'jpg')
    files.push(new File([blob], `${baseName}_${i + 1}.${ext}`, { type: blob.type }))
  }
  return files
}
