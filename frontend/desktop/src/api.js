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

  // ===== 幹部：美容師資訊卡片 (S2–S5) =====
  listCadreCards: () => request('GET', '/api/cadre/cards'),
  createCadreCard: (name) => request('POST', '/api/cadre/cards', { name }),
  getCadreCard: (id) => request('GET', `/api/cadre/cards/${id}`),
  updateCadreCard: (id, data) => request('PATCH', `/api/cadre/cards/${id}`, data),
  deleteCadreCard: (id) => request('DELETE', `/api/cadre/cards/${id}`),
  uploadCadreImage: (cardId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return uploadForm(`/api/cadre/cards/${cardId}/images`, fd)
  },
  pasteCadreImage: (cardId, dataUrl) =>
    request('POST', `/api/cadre/cards/${cardId}/images/paste`, { data_url: dataUrl }),
  setCadreCover: (imageId) => request('POST', `/api/cadre/images/${imageId}/cover`),
  deleteCadreImage: (imageId) => request('DELETE', `/api/cadre/images/${imageId}`),
  publishText: (cardId, variant) =>
    request('GET', `/api/cadre/cards/${cardId}/publish-text?variant=${variant}`),
  // 自動發布卡片（含勾選的圖片 + 文字）到指定發布目標
  publishCard: (cardId, data) => request('POST', `/api/cadre/cards/${cardId}/publish`, data),

  // ===== 幹部：班表 (S6–S12) =====
  listSchedules: () => request('GET', '/api/cadre/schedules'),
  createSchedule: (title = '') => request('POST', '/api/cadre/schedules', { title }),
  getSchedule: (id) => request('GET', `/api/cadre/schedules/${id}`),
  updateSchedule: (id, data) => request('PATCH', `/api/cadre/schedules/${id}`, data),
  deleteSchedule: (id) => request('DELETE', `/api/cadre/schedules/${id}`),
  addEntry: (scheduleId, cadreCardId) =>
    request('POST', `/api/cadre/schedules/${scheduleId}/entries`, { cadre_card_id: cadreCardId }),
  updateEntry: (entryId, data) => request('PATCH', `/api/cadre/entries/${entryId}`, data),
  deleteEntry: (entryId) => request('DELETE', `/api/cadre/entries/${entryId}`),
  shiftSlots: (start) => request('GET', `/api/cadre/shift-slots?start=${encodeURIComponent(start)}`),
  schedulePublishText: (id) => request('GET', `/api/cadre/schedules/${id}/publish-text`),
  // 自動發布班表（HTML，名字自動連到該美容師資訊訊息）
  publishSchedule: (id, data) => request('POST', `/api/cadre/schedules/${id}/publish`, data),

  // 標題／結語文字模板（kind = "title" | "footer"）
  listTextTemplates: (kind) => request('GET', `/api/cadre/text-templates?kind=${encodeURIComponent(kind)}`),
  createTextTemplate: (data) => request('POST', '/api/cadre/text-templates', data),
  updateTextTemplate: (id, data) => request('PATCH', `/api/cadre/text-templates/${id}`, data),
  deleteTextTemplate: (id) => request('DELETE', `/api/cadre/text-templates/${id}`),

  // ===== 社群發布 (P1) =====
  publishPlatforms: () => request('GET', '/api/publish/platforms'),
  listTargets: () => request('GET', '/api/publish/targets'),
  createTarget: (data) => request('POST', '/api/publish/targets', data),
  updateTarget: (id, data) => request('PATCH', `/api/publish/targets/${id}`, data),
  deleteTarget: (id) => request('DELETE', `/api/publish/targets/${id}`),
  sendPublish: (targetId, text) => request('POST', '/api/publish/send', { target_id: targetId, text }),
}
