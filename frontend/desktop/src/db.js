// IndexedDB 資料層（Local-First）— 取代 FastAPI 後端

const DB_NAME = 'ahhouch_db'
const DB_VERSION = 1

let _db = null

function openDB() {
  if (_db) return Promise.resolve(_db)
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = (e) => {
      const db = e.target.result
      if (!db.objectStoreNames.contains('cards'))
        db.createObjectStore('cards', { keyPath: 'id', autoIncrement: true })
      if (!db.objectStoreNames.contains('images')) {
        const s = db.createObjectStore('images', { keyPath: 'id', autoIncrement: true })
        s.createIndex('by_card', 'card_id', { unique: false })
      }
      if (!db.objectStoreNames.contains('schedules'))
        db.createObjectStore('schedules', { keyPath: 'id', autoIncrement: true })
      if (!db.objectStoreNames.contains('entries')) {
        const s = db.createObjectStore('entries', { keyPath: 'id', autoIncrement: true })
        s.createIndex('by_schedule', 'schedule_id', { unique: false })
      }
      if (!db.objectStoreNames.contains('text_templates')) {
        const s = db.createObjectStore('text_templates', { keyPath: 'id', autoIncrement: true })
        s.createIndex('by_kind', 'kind', { unique: false })
      }
    }
    req.onsuccess = (e) => { _db = e.target.result; resolve(_db) }
    req.onerror = () => reject(req.error)
  })
}

// IDBRequest → Promise
function p(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

// IDBTransaction 完成 → Promise（用於只需要知道「完成了」的寫入）
function txDone(t) {
  return new Promise((resolve, reject) => {
    t.oncomplete = resolve
    t.onerror = () => reject(t.error)
    t.onabort = () => reject(t.error)
  })
}

function now() { return new Date().toISOString() }

// ── 時間輔助 ────────────────────────────────────────────────────────────

// 把 "1830" 正規化為 "18:30"；已有冒號則原樣返回
export function normalizeTime(raw) {
  const s = String(raw || '').trim().replace(':', '')
  if (!/^\d{3,4}$/.test(s)) return raw
  const h = s.length === 3 ? parseInt(s[0]) : parseInt(s.slice(0, 2))
  const m = parseInt(s.slice(-2))
  if (h > 23 || m > 59) return raw
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

// ── 美容師資訊卡片 ──────────────────────────────────────────────────────

export async function listCards() {
  const db = await openDB()
  const cards = await p(db.transaction('cards', 'readonly').objectStore('cards').getAll())
  cards.sort((a, b) => (a.sort_order ?? a.id) - (b.sort_order ?? b.id))

  const result = []
  for (const card of cards) {
    let coverUrl = null
    if (card.cover_image_id) {
      const img = await p(db.transaction('images', 'readonly').objectStore('images').get(card.cover_image_id))
      if (img?.blob) coverUrl = URL.createObjectURL(img.blob)
    }
    result.push({ id: card.id, name: card.name, short_intro: card.short_intro || '', cover_image: coverUrl })
  }
  return result
}

export async function createCard(name) {
  const db = await openDB()
  const t = db.transaction('cards', 'readwrite')
  const id = await p(t.objectStore('cards').add({
    name, full_intro: '', short_intro: '', info_link: '',
    cover_image_id: null, sort_order: Date.now(), created_at: now(), updated_at: now(),
  }))
  return { id, name }
}

export async function getCard(id) {
  const db = await openDB()
  const numId = Number(id)
  const card = await p(db.transaction('cards', 'readonly').objectStore('cards').get(numId))
  if (!card) throw new Error('找不到資訊卡片')
  const imgs = await p(db.transaction('images', 'readonly').objectStore('images').index('by_card').getAll(numId))
  imgs.sort((a, b) => (a.sort_order ?? a.id) - (b.sort_order ?? b.id))
  const coverImg = card.cover_image_id ? imgs.find(i => i.id === card.cover_image_id) : null
  return {
    id: card.id,
    name: card.name,
    full_intro: card.full_intro || '',
    short_intro: card.short_intro || '',
    info_link: card.info_link || '',
    cover_image: coverImg?.blob ? URL.createObjectURL(coverImg.blob) : null,
    images: imgs.map(img => ({
      id: img.id,
      url: img.blob ? URL.createObjectURL(img.blob) : null,
      is_cover: img.id === card.cover_image_id,
    })),
  }
}

export async function updateCard(id, data) {
  const db = await openDB()
  const numId = Number(id)
  const t = db.transaction('cards', 'readwrite')
  const store = t.objectStore('cards')
  const card = await p(store.get(numId))
  if (!card) throw new Error('找不到資訊卡片')
  if (data.name !== undefined) card.name = data.name
  if (data.full_intro !== undefined) card.full_intro = data.full_intro
  if (data.short_intro !== undefined) card.short_intro = data.short_intro
  if (data.info_link !== undefined) card.info_link = data.info_link
  card.updated_at = now()
  await p(store.put(card))
  return card
}

export async function deleteCard(id) {
  const db = await openDB()
  const numId = Number(id)
  const imgs = await p(db.transaction('images', 'readonly').objectStore('images').index('by_card').getAll(numId))
  // 一次交易刪除圖片 + 卡片
  const t = db.transaction(['cards', 'images'], 'readwrite')
  for (const img of imgs) t.objectStore('images').delete(img.id)
  t.objectStore('cards').delete(numId)
  await txDone(t)
}

// ── 圖片 ────────────────────────────────────────────────────────────────

export async function addImage(cardId, blob) {
  const db = await openDB()
  const id = await p(db.transaction('images', 'readwrite').objectStore('images').add({
    card_id: Number(cardId), blob, sort_order: Date.now(),
  }))
  return { id, url: URL.createObjectURL(blob), is_cover: false }
}

export async function setCover(imageId) {
  const db = await openDB()
  const imgId = Number(imageId)
  const img = await p(db.transaction('images', 'readonly').objectStore('images').get(imgId))
  if (!img) throw new Error('找不到圖片')
  const t = db.transaction('cards', 'readwrite')
  const store = t.objectStore('cards')
  const card = await p(store.get(img.card_id))
  if (!card) throw new Error('找不到卡片')
  card.cover_image_id = imgId
  card.updated_at = now()
  await p(store.put(card))
}

export async function deleteImage(imageId) {
  const db = await openDB()
  const imgId = Number(imageId)
  const img = await p(db.transaction('images', 'readonly').objectStore('images').get(imgId))
  if (!img) return
  // 若是封面，清除封面參照
  const t1 = db.transaction('cards', 'readwrite')
  const cardStore = t1.objectStore('cards')
  const card = await p(cardStore.get(img.card_id))
  if (card?.cover_image_id === imgId) {
    card.cover_image_id = null
    card.updated_at = now()
    await p(cardStore.put(card))
  }
  await p(db.transaction('images', 'readwrite').objectStore('images').delete(imgId))
}

// ── 班表 ────────────────────────────────────────────────────────────────

export async function listSchedules() {
  const db = await openDB()
  const schedules = await p(db.transaction('schedules', 'readonly').objectStore('schedules').getAll())
  schedules.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
  const result = []
  for (const s of schedules) {
    const entries = await p(db.transaction('entries', 'readonly').objectStore('entries').index('by_schedule').getAll(s.id))
    result.push({ id: s.id, title: s.title || '', entry_count: entries.length, updated_at: s.updated_at })
  }
  return result
}

export async function createSchedule(title = '') {
  const db = await openDB()
  const id = await p(db.transaction('schedules', 'readwrite').objectStore('schedules').add({
    title, footer: '', date: '', created_at: now(), updated_at: now(),
  }))
  return { id, title }
}

export async function getSchedule(id) {
  const db = await openDB()
  const numId = Number(id)
  const s = await p(db.transaction('schedules', 'readonly').objectStore('schedules').get(numId))
  if (!s) throw new Error('找不到班表')
  const entries = await p(db.transaction('entries', 'readonly').objectStore('entries').index('by_schedule').getAll(numId))
  entries.sort((a, b) => (a.sort_order ?? a.id) - (b.sort_order ?? b.id))
  const enriched = []
  for (const e of entries) {
    const card = await p(db.transaction('cards', 'readonly').objectStore('cards').get(e.cadre_card_id))
    enriched.push({
      id: e.id,
      cadre_card_id: e.cadre_card_id,
      name: card ? card.name : '（已刪除）',
      short_intro: card ? (card.short_intro || '') : '',
      slots: e.slots || [],
      time_mode: e.time_mode || 'manual',
      auto_start: e.auto_start || '',
    })
  }
  return { id: s.id, title: s.title || '', footer: s.footer || '', date: s.date || '', entries: enriched }
}

export async function updateSchedule(id, data) {
  const db = await openDB()
  const numId = Number(id)
  const t = db.transaction('schedules', 'readwrite')
  const store = t.objectStore('schedules')
  const s = await p(store.get(numId))
  if (!s) throw new Error('找不到班表')
  if (data.title !== undefined) s.title = data.title
  if (data.footer !== undefined) s.footer = data.footer
  if (data.date !== undefined) s.date = data.date
  s.updated_at = now()
  await p(store.put(s))
  return s
}

export async function deleteSchedule(id) {
  const db = await openDB()
  const numId = Number(id)
  const entries = await p(db.transaction('entries', 'readonly').objectStore('entries').index('by_schedule').getAll(numId))
  const t = db.transaction(['schedules', 'entries'], 'readwrite')
  for (const e of entries) t.objectStore('entries').delete(e.id)
  t.objectStore('schedules').delete(numId)
  await txDone(t)
}

// ── 出勤記錄 ────────────────────────────────────────────────────────────

export async function addEntry(scheduleId, cadreCardId) {
  const db = await openDB()
  const schedId = Number(scheduleId)
  const id = await p(db.transaction('entries', 'readwrite').objectStore('entries').add({
    schedule_id: schedId, cadre_card_id: Number(cadreCardId),
    slots: [], time_mode: 'manual', auto_start: '', sort_order: Date.now(),
  }))
  // 更新班表的 updated_at
  const t2 = db.transaction('schedules', 'readwrite')
  const s = await p(t2.objectStore('schedules').get(schedId))
  if (s) { s.updated_at = now(); await p(t2.objectStore('schedules').put(s)) }
  return { id }
}

export async function updateEntry(id, data) {
  const db = await openDB()
  const numId = Number(id)
  const t = db.transaction('entries', 'readwrite')
  const store = t.objectStore('entries')
  const e = await p(store.get(numId))
  if (!e) throw new Error('找不到出勤記錄')
  if (data.slots !== undefined) e.slots = data.slots.map(normalizeTime)
  if (data.time_mode !== undefined) e.time_mode = data.time_mode
  if (data.auto_start !== undefined) e.auto_start = data.auto_start
  await p(store.put(e))
  return { id: e.id, slots: e.slots, time_mode: e.time_mode, auto_start: e.auto_start }
}

export async function deleteEntry(id) {
  const db = await openDB()
  await p(db.transaction('entries', 'readwrite').objectStore('entries').delete(Number(id)))
}

// ── 班次自動換算 ─────────────────────────────────────────────────────────

// 從 startRaw 開始，每 1.5 小時一個班次，共列出 8 個班次（涵蓋 12 小時）
export function calcShiftSlots(startRaw) {
  const start = normalizeTime(startRaw)
  const [h, m] = start.split(':').map(Number)
  if (isNaN(h) || isNaN(m)) throw new Error('無效的時間格式')
  const startMin = h * 60 + m
  const slots = []
  for (let i = 0; i < 8; i++) {
    const total = (startMin + i * 90) % 1440
    slots.push(`${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`)
  }
  return slots
}

// ── 文字模板 ────────────────────────────────────────────────────────────

export async function listTextTemplates(kind) {
  const db = await openDB()
  const templates = await p(db.transaction('text_templates', 'readonly').objectStore('text_templates').index('by_kind').getAll(kind))
  return templates.sort((a, b) => a.id - b.id)
}

export async function createTextTemplate(data) {
  const db = await openDB()
  const id = await p(db.transaction('text_templates', 'readwrite').objectStore('text_templates').add({
    kind: data.kind, name: data.name, content: data.content || '', created_at: now(),
  }))
  return { id, ...data }
}

export async function updateTextTemplate(id, data) {
  const db = await openDB()
  const t = db.transaction('text_templates', 'readwrite')
  const store = t.objectStore('text_templates')
  const tpl = await p(store.get(Number(id)))
  if (!tpl) throw new Error('找不到模板')
  if (data.name !== undefined) tpl.name = data.name
  if (data.content !== undefined) tpl.content = data.content
  await p(store.put(tpl))
  return tpl
}

export async function deleteTextTemplate(id) {
  const db = await openDB()
  await p(db.transaction('text_templates', 'readwrite').objectStore('text_templates').delete(Number(id)))
}

// ── 發布文字生成（本機） ─────────────────────────────────────────────────

export async function cardPublishText(cardId, variant) {
  const card = await getCard(Number(cardId))
  const intro = variant === 'short' ? card.short_intro : card.full_intro
  const lines = [card.name]
  if (intro?.trim()) lines.push(intro.trim())
  return lines.join('\n')
}

const WEEKDAY_TW = ['日', '一', '二', '三', '四', '五', '六']

export async function schedulePublishText(scheduleId) {
  const s = await getSchedule(Number(scheduleId))
  const lines = []
  if (s.date) {
    const [y, mo, d] = s.date.split('-').map(Number)
    const wd = WEEKDAY_TW[new Date(y, mo - 1, d).getDay()]
    lines.push(`${y}/${String(mo).padStart(2,'0')}/${String(d).padStart(2,'0')} (${wd})`)
  }
  if (s.title?.trim()) lines.push(s.title.trim())
  for (const e of s.entries) {
    lines.push('')
    lines.push(e.name)
    if (e.short_intro?.trim()) lines.push(e.short_intro.trim())
    if (e.slots?.length) lines.push(e.slots.join('、'))
  }
  if (s.footer?.trim()) { lines.push(''); lines.push(s.footer.trim()) }
  return lines.join('\n')
}
