// Сценарии модулей тестирования, досок и блога. Транспорт — logic/api.
import {
  createBoard, createPost, deleteBoard, fetchBlogAuthor, fetchBlogAuthors, fetchBlogComments, fetchBlogFeed,
  fetchBlogPost, fetchJoinedBoards, fetchMyBoards, fetchMyPosts, importBoard, postBlogComment, removeBlogComment,
  removePost, resolveBoard, testingRequest, updatePost, ApiError,
} from '../api/index.js'
import { useAuthStore } from '../store/index.js'
import { refreshSession } from './auth.js'

// Ответ 422 модулей содержит причину по полю (например, «Тег … содержит недопустимые символы»):
// показываем её вместо общей фразы транспорта.
const FIELD_NAMES = { title: 'заголовок', body: 'текст', tags: 'теги', code: 'код', text: 'комментарий' }

export function explainValidation(error) {
  const details = error?.payload?.error?.details
  if (!(error instanceof ApiError) || error.status !== 422 || !Array.isArray(details) || !details.length) return error
  const reasons = details.slice(0, 3).map((d) => {
    const msg = String(d?.msg || '')
    if (msg.startsWith('Value error, ')) return msg.slice(13)
    const field = [...(d?.loc || [])].reverse().find((k) => typeof k === 'string' && FIELD_NAMES[k])
    return field ? `${FIELD_NAMES[field]}: некорректное значение` : ''
  }).filter(Boolean)
  return reasons.length ? new ApiError(422, reasons.join('; '), error.payload) : error
}

const explained = (fn) => async (...args) => {
  try {
    return await fn(...args)
  } catch (error) {
    throw explainValidation(error)
  }
}

// ---------- тестирование ----------
export const requestTesting = (path, opts) => testingRequest(path, opts)

// ---------- доски ----------
export async function loadBoards(role) {
  const [mine, joined] = await Promise.all([
    role === 'tutor' ? fetchMyBoards() : Promise.resolve({ items: [] }),
    fetchJoinedBoards(),
  ])
  return { mine: mine.items, joined: joined.items }
}
export const openNewBoard = explained((title, code) => createBoard({ title, code: code || null }))
export const findBoardByCode = (code) => resolveBoard(code)
export const removeBoard = (id) => deleteBoard(id)
export const uploadBoardFile = explained((id, body) => importBoard(id, body))

// Токен для первого сообщения WebSocket доски. forceRefresh — после отказа сервера по истёкшей сессии.
export async function boardSocketToken({ forceRefresh = false } = {}) {
  if (forceRefresh) return refreshSession()
  return useAuthStore().accessToken
}

// ---------- блог ----------
export const loadFeed = (params) => fetchBlogFeed(params)
export const loadAuthors = () => fetchBlogAuthors()
export const loadAuthor = (id) => fetchBlogAuthor(id)
export async function loadPost(id) {
  const [post, comments] = await Promise.all([fetchBlogPost(id), fetchBlogComments(id).catch(() => ({ items: [] }))])
  return { post, comments: comments.items }
}
export const addComment = explained((postId, text) => postBlogComment(postId, text))
export const deleteComment = (id) => removeBlogComment(id)
export const loadMyPosts = () => fetchMyPosts()
export const savePost = explained((id, body) => (id ? updatePost(id, body) : createPost(body)))
export const deletePost = (id) => removePost(id)
