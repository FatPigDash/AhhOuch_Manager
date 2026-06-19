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

export const api = {
  meta: () => request('GET', '/api/meta'),

  // 養身館 (C1/C2/C3)
  listSpas: () => request('GET', '/api/customer/spas'),
  createSpa: (data) => request('POST', '/api/customer/spas', data),
  getSpa: (id) => request('GET', `/api/customer/spas/${id}`),
  updateSpa: (id, data) => request('PATCH', `/api/customer/spas/${id}`, data),
  deleteSpa: (id) => request('DELETE', `/api/customer/spas/${id}`),

  // 看板 (C4/C5/C6)
  createBoard: (spaId, data) => request('POST', `/api/customer/spas/${spaId}/boards`, data),
  updateBoard: (id, data) => request('PATCH', `/api/customer/boards/${id}`, data),
  deleteBoard: (id) => request('DELETE', `/api/customer/boards/${id}`),
  // 看板拖曳排序 (C5)：position 為新的左右索引
  moveBoard: (id, data) => request('POST', `/api/customer/boards/${id}/move`, data),

  // 卡片 (C7/C8/C11)
  createCard: (boardId, data) => request('POST', `/api/customer/boards/${boardId}/cards`, data),
  updateCard: (id, data) => request('PATCH', `/api/customer/cards/${id}`, data),
  deleteCard: (id) => request('DELETE', `/api/customer/cards/${id}`),
  // 拖曳移動 (C9)：position 為在目標看板的插入索引
  moveCard: (id, data) => request('POST', `/api/customer/cards/${id}/move`, data),
}
