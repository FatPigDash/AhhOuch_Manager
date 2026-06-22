// 後端 API 呼叫封裝。開發時 /api 由 Vite 代理到後端；打包後同源直接呼叫。

async function request(method, url, body) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(url, opts)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data.detail) detail = data.detail
    } catch (_) { /* 忽略非 JSON 回應 */ }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

// 檔案上傳（multipart）。不設 Content-Type，讓瀏覽器自帶 boundary。
async function uploadForm(url, formData) {
  const res = await fetch(url, { method: 'POST', body: formData })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data.detail) detail = data.detail
    } catch (_) { /* 忽略 */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  meta: () => request('GET', '/api/meta'),

  // 養身館 (C1/C2/C3)
  listSpas: () => request('GET', '/api/customer/spas'),
  createSpa: (data) => request('POST', '/api/customer/spas', data),
  getSpa: (id) => request('GET', `/api/customer/spas/${id}`),
  updateSpa: (id, data) => request('PATCH', `/api/customer/spas/${id}`, data),
  deleteSpa: (id) => request('DELETE', `/api/customer/spas/${id}`),
  // 養身館拖曳排序 (C3)：position 為新的列表索引
  moveSpa: (id, data) => request('POST', `/api/customer/spas/${id}/move`, data),

  // 看板 (C4/C5/C6)
  createBoard: (spaId, data) => request('POST', `/api/customer/spas/${spaId}/boards`, data),
  updateBoard: (id, data) => request('PATCH', `/api/customer/boards/${id}`, data),
  deleteBoard: (id) => request('DELETE', `/api/customer/boards/${id}`),
  // 看板拖曳排序 (C5)：position 為新的左右索引
  moveBoard: (id, data) => request('POST', `/api/customer/boards/${id}/move`, data),
  // 切換排序方式 (C10)：mode = "unicode"（預設/標題）| "manual"（手動）
  // 後端會保存手動排序快照（切預設時）或還原快照（切手動時）
  setSortMode: (id, mode) => request('POST', `/api/customer/boards/${id}/sort-mode`, { mode }),

  // 卡片 (C7/C8/C11)
  createCard: (boardId, data) => request('POST', `/api/customer/boards/${boardId}/cards`, data),
  updateCard: (id, data) => request('PATCH', `/api/customer/cards/${id}`, data),
  deleteCard: (id) => request('DELETE', `/api/customer/cards/${id}`),
  // 拖曳移動 (C9)：position 為在目標看板的插入索引
  moveCard: (id, data) => request('POST', `/api/customer/cards/${id}/move`, data),

  // 卡片詳情（簡介 + 心得，C12–C22）
  getCard: (id) => request('GET', `/api/customer/cards/${id}`),

  // 圖片 (C13)
  uploadImage: (cardId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return uploadForm(`/api/customer/cards/${cardId}/images`, fd)
  },
  pasteImage: (cardId, dataUrl) =>
    request('POST', `/api/customer/cards/${cardId}/images/paste`, { data_url: dataUrl }),
  setCover: (imageId) => request('POST', `/api/customer/images/${imageId}/cover`),
  deleteImage: (imageId) => request('DELETE', `/api/customer/images/${imageId}`),

  // 評分模板 (C17/C18/C20)
  listTemplates: () => request('GET', '/api/customer/templates'),
  createTemplate: (name) => request('POST', '/api/customer/templates', { name }),
  renameTemplate: (id, name) => request('PATCH', `/api/customer/templates/${id}`, { name }),
  // 整批覆蓋模板（名稱 + 全部項目），供「儲存」草稿用
  replaceTemplate: (id, data) => request('PUT', `/api/customer/templates/${id}`, data),
  deleteTemplate: (id) => request('DELETE', `/api/customer/templates/${id}`),
  addTemplateItem: (templateId, name) =>
    request('POST', `/api/customer/templates/${templateId}/items`, { name }),
  renameTemplateItem: (itemId, name) =>
    request('PATCH', `/api/customer/template-items/${itemId}`, { name }),
  setTemplateItemType: (itemId, item_type) =>
    request('PATCH', `/api/customer/template-items/${itemId}`, { item_type }),
  moveTemplateItem: (itemId, direction) =>
    request('POST', `/api/customer/template-items/${itemId}/move`, { direction }),
  deleteTemplateItem: (itemId) =>
    request('DELETE', `/api/customer/template-items/${itemId}`),
  copyTemplateTo: (sourceId, targetId) =>
    request('POST', `/api/customer/templates/${sourceId}/copy-to`, { target_id: targetId }),

  // 心得 (C16/C19/C21/C22)
  createReview: (cardId, data = {}) =>
    request('POST', `/api/customer/cards/${cardId}/reviews`, data),
  updateReview: (id, data) => request('PATCH', `/api/customer/reviews/${id}`, data),
  applyReviewTemplate: (reviewId, templateId) =>
    request('POST', `/api/customer/reviews/${reviewId}/template`, { template_id: templateId }),
  // 將心得更新為其所屬模板的最新項目（保留同名項目評分）
  syncReviewTemplate: (reviewId) => request('POST', `/api/customer/reviews/${reviewId}/sync`),
  deleteReview: (id) => request('DELETE', `/api/customer/reviews/${id}`),
  updateScore: (id, data) => request('PATCH', `/api/customer/scores/${id}`, data),

  // ===== 店家：美容師資訊卡片 (S2–S5) =====
  listStoreCards: () => request('GET', '/api/store/cards'),
  createStoreCard: (name) => request('POST', '/api/store/cards', { name }),
  getStoreCard: (id) => request('GET', `/api/store/cards/${id}`),
  updateStoreCard: (id, data) => request('PATCH', `/api/store/cards/${id}`, data),
  deleteStoreCard: (id) => request('DELETE', `/api/store/cards/${id}`),
  uploadStoreImage: (cardId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return uploadForm(`/api/store/cards/${cardId}/images`, fd)
  },
  pasteStoreImage: (cardId, dataUrl) =>
    request('POST', `/api/store/cards/${cardId}/images/paste`, { data_url: dataUrl }),
  setStoreCover: (imageId) => request('POST', `/api/store/images/${imageId}/cover`),
  deleteStoreImage: (imageId) => request('DELETE', `/api/store/images/${imageId}`),
  publishText: (cardId, variant) =>
    request('GET', `/api/store/cards/${cardId}/publish-text?variant=${variant}`),
  // 自動發布卡片（含勾選的圖片 + 文字）到指定發布目標
  publishCard: (cardId, data) => request('POST', `/api/store/cards/${cardId}/publish`, data),

  // ===== 店家：班表 (S6–S12) =====
  listSchedules: () => request('GET', '/api/store/schedules'),
  createSchedule: (title = '') => request('POST', '/api/store/schedules', { title }),
  getSchedule: (id) => request('GET', `/api/store/schedules/${id}`),
  updateSchedule: (id, data) => request('PATCH', `/api/store/schedules/${id}`, data),
  deleteSchedule: (id) => request('DELETE', `/api/store/schedules/${id}`),
  addEntry: (scheduleId, storeCardId) =>
    request('POST', `/api/store/schedules/${scheduleId}/entries`, { store_card_id: storeCardId }),
  updateEntry: (entryId, data) => request('PATCH', `/api/store/entries/${entryId}`, data),
  deleteEntry: (entryId) => request('DELETE', `/api/store/entries/${entryId}`),
  shiftSlots: (start) => request('GET', `/api/store/shift-slots?start=${encodeURIComponent(start)}`),
  schedulePublishText: (id) => request('GET', `/api/store/schedules/${id}/publish-text`),
  // 自動發布班表（HTML，名字自動連到該美容師資訊訊息）
  publishSchedule: (id, data) => request('POST', `/api/store/schedules/${id}/publish`, data),

  // 標題／結語文字模板（kind = "title" | "footer"）
  listTextTemplates: (kind) => request('GET', `/api/store/text-templates?kind=${encodeURIComponent(kind)}`),
  createTextTemplate: (data) => request('POST', '/api/store/text-templates', data),
  updateTextTemplate: (id, data) => request('PATCH', `/api/store/text-templates/${id}`, data),
  deleteTextTemplate: (id) => request('DELETE', `/api/store/text-templates/${id}`),

  // ===== 社群發布 (P1) =====
  publishPlatforms: () => request('GET', '/api/publish/platforms'),
  listTargets: () => request('GET', '/api/publish/targets'),
  createTarget: (data) => request('POST', '/api/publish/targets', data),
  updateTarget: (id, data) => request('PATCH', `/api/publish/targets/${id}`, data),
  deleteTarget: (id) => request('DELETE', `/api/publish/targets/${id}`),
  sendPublish: (targetId, text) => request('POST', '/api/publish/send', { target_id: targetId, text }),
}
