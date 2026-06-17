import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(error)
  }
)

// ---- Knowledge Bases ----
export function listKnowledgeBases() {
  return api.get('/knowledge-bases')
}

export function createKnowledgeBase(data) {
  return api.post('/knowledge-bases', data)
}

export function getKnowledgeBase(id) {
  return api.get(`/knowledge-bases/${id}`)
}

export function updateKnowledgeBase(id, data) {
  return api.put(`/knowledge-bases/${id}`, data)
}

export function deleteKnowledgeBase(id) {
  return api.delete(`/knowledge-bases/${id}`)
}

// ---- Documents ----
export function listDocuments(kbId) {
  return api.get('/documents', { params: { kb_id: kbId } })
}

export function uploadDocuments(kbId, files) {
  const form = new FormData()
  form.append('kb_id', kbId)
  files.forEach(f => form.append('files', f))
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
}

export function processDocument(docId) {
  return api.post(`/documents/${docId}/process`)
}

export function batchProcessDocuments(kbId) {
  const form = new FormData()
  form.append('kb_id', kbId)
  return api.post('/documents/batch-process', form)
}

export function getDocument(docId) {
  return api.get(`/documents/${docId}`)
}

export function getDocumentChunks(docId) {
  return api.get(`/documents/${docId}/chunks`)
}

export function getDocumentContent(docId) {
  return api.get(`/documents/${docId}/content`)
}

export function deleteDocument(docId) {
  return api.delete(`/documents/${docId}`)
}

// ---- Search / QA ----
export function searchRetrieve(kbId, query, topK = 5) {
  return api.post('/search/retrieve', { kb_id: kbId, query, top_k: topK })
}

export function searchQA(kbId, query, topK = 5) {
  return api.post('/search/qa', { kb_id: kbId, query, top_k: topK, stream: false })
}

// ---- Stats ----
export function getOverviewStats() {
  return api.get('/stats/overview')
}

export function getKbStats(kbId) {
  return api.get(`/stats/kb/${kbId}`)
}

export default api
