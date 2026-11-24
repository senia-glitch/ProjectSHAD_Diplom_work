import { describe, expect, it, vi } from 'vitest'

vi.mock('../store/index.js', () => ({ useAuthStore: () => ({ accessToken: null }) }))
vi.mock('./auth.js', () => ({ refreshSession: async () => null }))

const { explainValidation } = await import('./modules.js')
const { ApiError } = await import('../api/index.js')

describe('explainValidation', () => {
  it('показывает причину из ответа 422 вместо общей фразы', () => {
    const error = new ApiError(422, 'Проверьте правильность заполнения полей', {
      error: { details: [{ loc: ['body', 'tags'], msg: 'Value error, Тег «a@b» содержит недопустимые символы' }] },
    })
    expect(explainValidation(error).message).toBe('Тег «a@b» содержит недопустимые символы')
  })

  it('называет поле, если причины нет', () => {
    const error = new ApiError(422, 'x', { error: { details: [{ loc: ['body', 'title'], msg: 'String too long' }] } })
    expect(explainValidation(error).message).toBe('заголовок: некорректное значение')
  })

  it('не трогает другие ошибки', () => {
    const error = new ApiError(404, 'Не найдено', null)
    expect(explainValidation(error)).toBe(error)
  })
})
