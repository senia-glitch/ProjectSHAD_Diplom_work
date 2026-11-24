// Транспорт модулей тестирования, досок и блога. Один эндпойнт = одна функция.
// Перенесённые DOM-страницы тестирования ходят через testingRequest (тот же токен и refresh).
import { apiFetch, withQuery } from './client.js'

const V1 = '/api/v1'

export function testingRequest(path, { method = 'GET', body } = {}) {
  return apiFetch(path, { method, body })
}

// ---------- доски ----------
export const fetchMyBoards = () => apiFetch(`${V1}/boards/mine`)
export const fetchJoinedBoards = () => apiFetch(`${V1}/boards/joined`)
export const createBoard = (body) => apiFetch(`${V1}/boards`, { method: 'POST', body })
export const resolveBoard = (code) => apiFetch(`${V1}/boards/resolve`, { method: 'POST', body: { code } })
export const deleteBoard = (id) => apiFetch(`${V1}/boards/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const importBoard = (id, body) =>
  apiFetch(`${V1}/boards/${encodeURIComponent(id)}/import`, { method: 'POST', body, timeout: 120000 })

// ---------- блог ----------
export const fetchBlogFeed = (params) => apiFetch(withQuery(`${V1}/blog/posts`, params), { auth: true })
export const fetchBlogPost = (id) => apiFetch(`${V1}/blog/posts/${id}`)
export const fetchBlogComments = (id) => apiFetch(`${V1}/blog/posts/${id}/comments`)
export const fetchBlogAuthors = () => apiFetch(`${V1}/blog/authors`)
export const fetchBlogAuthor = (id) => apiFetch(`${V1}/blog/authors/${id}`)
export const postBlogComment = (id, text) => apiFetch(`${V1}/blog/posts/${id}/comments`, { method: 'POST', body: { text } })
export const removeBlogComment = (id) => apiFetch(`${V1}/blog/comments/${id}`, { method: 'DELETE' })
export const fetchMyPosts = () => apiFetch(`${V1}/blog/my/posts`)
export const createPost = (body) => apiFetch(`${V1}/blog/my/posts`, { method: 'POST', body })
export const updatePost = (id, body) => apiFetch(`${V1}/blog/my/posts/${id}`, { method: 'PUT', body })
export const removePost = (id) => apiFetch(`${V1}/blog/my/posts/${id}`, { method: 'DELETE' })
