// 備份匯出／匯入（M6）— 將本機全部資料打包為 ZIP，供幹部上傳自有雲端（iCloud/Drive），
// 換機或清快取後再匯入還原（需求 D4、計畫 §4.4 / §6.5）。
//
// ZIP 結構：
//   manifest.json          結構化資料（卡片/班表/出勤/文字模板）＋圖片索引（指向 images/ 內檔名）
//   images/<id>.<ext>      每張圖的完整圖
//   images/<id>_t.<ext>    每張圖的縮圖
//
// 選擇性加密：匯出可設密碼（AES-GCM，見 crypto.js）；明文則為標準 ZIP。匯入自動辨識。

import { zip, unzip, strToU8, strFromU8 } from 'fflate'
import * as db from './db.js'
import { encryptBytes, decryptBytes, isEncrypted } from './crypto.js'

const BACKUP_VERSION = 1

function extFromType(type) {
  return (type && type.split('/')[1] ? type.split('/')[1] : 'jpg').replace('jpeg', 'jpg')
}

async function blobToU8(blob) {
  return new Uint8Array(await blob.arrayBuffer())
}

// fflate async 包裝
function zipAsync(files, opts) {
  return new Promise((resolve, reject) => zip(files, opts, (err, data) => (err ? reject(err) : resolve(data))))
}
function unzipAsync(data) {
  return new Promise((resolve, reject) => unzip(data, (err, files) => (err ? reject(err) : resolve(files))))
}

// 匯出：回傳 { bytes: Uint8Array, filename }。password 留空＝明文 ZIP。
export async function exportBackup(password = '') {
  const data = await db.dumpAll()
  const files = {}            // zip 內檔案
  const imageIndex = []       // manifest 的圖片索引（不含 Blob）

  for (const img of data.images || []) {
    const entry = { id: img.id, card_id: img.card_id, sort_order: img.sort_order }
    if (img.blob) {
      const ext = extFromType(img.blob.type)
      const path = `images/${img.id}.${ext}`
      files[path] = [await blobToU8(img.blob), { level: 0 }]  // JPEG 已壓縮，store 即可
      entry.blob = path
      entry.blob_type = img.blob.type
    }
    if (img.thumb) {
      const ext = extFromType(img.thumb.type)
      const path = `images/${img.id}_t.${ext}`
      files[path] = [await blobToU8(img.thumb), { level: 0 }]
      entry.thumb = path
      entry.thumb_type = img.thumb.type
    }
    imageIndex.push(entry)
  }

  const manifest = {
    app: 'AhhOuch_Manager',
    backup_version: BACKUP_VERSION,
    exported_at: new Date().toISOString(),
    cards: data.cards || [],
    schedules: data.schedules || [],
    entries: data.entries || [],
    text_templates: data.text_templates || [],
    images: imageIndex,
  }
  files['manifest.json'] = strToU8(JSON.stringify(manifest))

  let bytes = await zipAsync(files, { level: 6 })
  if (password) bytes = await encryptBytes(bytes, password)

  const stamp = new Date().toISOString().slice(0, 10)
  return { bytes, filename: `AhhOuch備份_${stamp}.ahbk` }
}

// 偵測檔案是否為加密備份（供 UI 決定是否需要密碼）。
export async function fileIsEncrypted(file) {
  const head = new Uint8Array(await file.slice(0, 4).arrayBuffer())
  return isEncrypted(head)
}

// 匯入：整批覆蓋還原。加密檔需提供 password。
export async function importBackup(file, password = '') {
  let bytes = new Uint8Array(await file.arrayBuffer())
  if (isEncrypted(bytes)) {
    if (!password) throw new Error('此備份檔已加密，請輸入密碼。')
    bytes = await decryptBytes(bytes, password)
  }

  let files
  try {
    files = await unzipAsync(bytes)
  } catch {
    throw new Error('備份檔格式錯誤，無法解開。')
  }
  if (!files['manifest.json']) throw new Error('備份檔缺少 manifest.json，可能不是有效備份。')

  const manifest = JSON.parse(strFromU8(files['manifest.json']))
  if (manifest.app !== 'AhhOuch_Manager') throw new Error('這不是 AhhOuch_Manager 的備份檔。')

  // 重建 images（從 zip 內檔案還原 Blob）
  const images = []
  for (const idx of (manifest.images || [])) {
    const rec = { id: idx.id, card_id: idx.card_id, sort_order: idx.sort_order }
    if (idx.blob && files[idx.blob]) rec.blob = new Blob([files[idx.blob]], { type: idx.blob_type || 'image/jpeg' })
    if (idx.thumb && files[idx.thumb]) rec.thumb = new Blob([files[idx.thumb]], { type: idx.thumb_type || 'image/jpeg' })
    images.push(rec)
  }

  await db.restoreAll({
    cards: manifest.cards || [],
    schedules: manifest.schedules || [],
    entries: manifest.entries || [],
    text_templates: manifest.text_templates || [],
    images,
  })

  return {
    cards: (manifest.cards || []).length,
    images: images.length,
    schedules: (manifest.schedules || []).length,
  }
}
