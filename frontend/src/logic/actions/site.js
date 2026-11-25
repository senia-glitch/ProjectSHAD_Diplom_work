// Гостевая страница: чтение для всех, редактирование — владельцу.
import {
  fetchSiteBlocks, fetchAdminSiteBlocks, createSiteBlock, updateSiteBlock, deleteSiteBlock, orderSiteBlocks,
} from '../api/index.js'

export const loadSiteBlocks = async () => (await fetchSiteBlocks()).items || []
export const loadAdminSiteBlocks = async () => (await fetchAdminSiteBlocks()).items || []
export const saveSiteBlock = (id, block) => (id ? updateSiteBlock(id, block) : createSiteBlock(block))
export const removeSiteBlock = (id) => deleteSiteBlock(id)
export const reorderSiteBlocks = async (ids) => (await orderSiteBlocks(ids)).items || []
