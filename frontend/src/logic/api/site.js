// Гостевая страница: блоки (публично) и управление ими (владелец).
import { apiFetch } from './client.js'

const V1 = '/api/v1'
export const fetchSiteBlocks = () => apiFetch(`${V1}/site/blocks`, { auth: false })
export const fetchAdminSiteBlocks = () => apiFetch(`${V1}/admin/site/blocks`)
export const createSiteBlock = (block) => apiFetch(`${V1}/admin/site/blocks`, { method: 'POST', body: block })
export const updateSiteBlock = (id, block) => apiFetch(`${V1}/admin/site/blocks/${id}`, { method: 'PUT', body: block })
export const deleteSiteBlock = (id) => apiFetch(`${V1}/admin/site/blocks/${id}`, { method: 'DELETE' })
export const orderSiteBlocks = (ids) => apiFetch(`${V1}/admin/site/blocks/order`, { method: 'POST', body: { ids } })
