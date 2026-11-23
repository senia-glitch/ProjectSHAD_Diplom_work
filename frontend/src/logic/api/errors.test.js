import { describe, it, expect, vi, beforeEach } from 'vitest'
import { translateErrorMessage } from './errors.js'
import { apiFetch, registerTokenProvider, registerRefreshHandler, registerUnauthorizedHandler } from './client.js'

describe('translateErrorMessage', () => {
  it('переводит известные сообщения backend', () => {
    expect(translateErrorMessage(401, 'Invalid username or password')).toBe('Неверный логин или пароль')
    expect(translateErrorMessage(404, 'User with this personal number not found')).toBe(
      'Пользователь с таким личным кодом не найден',
    )
  })

  it('переводит сообщения с параметрами', () => {
    expect(translateErrorMessage(400, 'Lesson must be booked at least 24h in advance')).toBe(
      'Записаться можно не позднее чем за 24 ч до начала',
    )
    expect(translateErrorMessage(409, 'Configuration for student 6 and tutor 5 already exists')).toBe(
      'Ученик уже связан с этим репетитором',
    )
  })

  it('без текста и для недоступного сервера даёт понятную формулировку', () => {
    expect(translateErrorMessage(502, '')).toBe('Сервер временно недоступен. Попробуйте позже')
    expect(translateErrorMessage(503, 'upstream error')).toBe('Сервер временно недоступен. Попробуйте позже')
    expect(translateErrorMessage(0, undefined)).toBe('Нет соединения с сервером. Проверьте подключение')
    expect(translateErrorMessage(418, null)).toBe('Не удалось выполнить запрос (код 418)')
  })

  it('неизвестное сообщение оставляет как есть', () => {
    expect(translateErrorMessage(400, 'Something new')).toBe('Something new')
  })
})

describe('apiFetch: русские сообщения ошибок', () => {
  beforeEach(() => {
    registerTokenProvider(() => null)
    registerRefreshHandler(() => Promise.resolve(null))
    registerUnauthorizedHandler(() => {})
  })

  it('HTTP-ошибка получает перевод, исходный payload сохраняется', async () => {
    const payload = { error: { message: 'Invalid username or password' } }
    globalThis.fetch = vi.fn(async () => ({ ok: false, status: 401, json: async () => payload }))
    await expect(apiFetch('/x', { auth: false })).rejects.toMatchObject({
      status: 401,
      message: 'Неверный логин или пароль',
      payload,
    })
  })

  it('502 без тела не показывает технический текст', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('no json')
      },
    }))
    await expect(apiFetch('/x', { auth: false })).rejects.toMatchObject({
      status: 502,
      message: 'Сервер временно недоступен. Попробуйте позже',
    })
  })

  it('сетевой сбой fetch превращается в ApiError со status 0', async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(apiFetch('/x', { auth: false })).rejects.toMatchObject({
      status: 0,
      message: 'Нет соединения с сервером. Проверьте подключение',
    })
  })
})
