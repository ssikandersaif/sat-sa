const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const request = async (path, options = {}) => { const response = await fetch(`${API}${path}`, options); if (!response.ok) { let detail = `API error ${response.status}`; try { detail = (await response.json()).detail || detail } catch {} throw new Error(detail) } return response.json() }
export const getEntities = () => request('/entities')
export const getFindings = () => request('/findings')
export const getPeers = () => request('/peers/summary')
export const getEntity = (id) => request(`/entities/${id}`)
export const uploadDataset = (files) => { const body = new FormData(); Object.entries(files).forEach(([key, file]) => body.append(key, file)); return request('/ingest/upload', { method: 'POST', body }) }
export const uploadSingleLog = (file) => { const body = new FormData(); body.append('file', file); return request('/ingest/single', { method: 'POST', body }) }
export const runAiAction = (findingId, action) => request(`/findings/${findingId}/ai/${action}`, { method: 'POST' })
