// Сценарии модулей тестирования, досок и блога. Транспорт — logic/api.
import {
  createBoard, createPost, deleteBoard, fetchBlogAuthor, fetchBlogAuthors, fetchBlogComments, fetchBlogFeed,
  fetchBlogPost, fetchJoinedBoards, fetchMyBoards, fetchMyPosts, importBoard, postBlogComment, removeBlogComment,
  removePost, resolveBoard, testingRequest, updatePost,
} from '../api/index.js'
import { useAuthStore } from '../store/index.js'
import { refreshSession } from './auth.js'

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
export const openNewBoard = (title, code) => createBoard({ title, code: code || null })
export const findBoardByCode = (code) => resolveBoard(code)
export const removeBoard = (id) => deleteBoard(id)
export const uploadBoardFile = (id, body) => importBoard(id, body)

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
export const addComment = (postId, text) => postBlogComment(postId, text)
export const deleteComment = (id) => removeBlogComment(id)
export const loadMyPosts = () => fetchMyPosts()
export const savePost = (id, body) => (id ? updatePost(id, body) : createPost(body))
export const deletePost = (id) => removePost(id)
