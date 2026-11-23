// Интеграционный тест флоу окон ученика при листании недель:
// стор + экшены + композабл страницы с подменённым fetch.
// Регрессия: новая неделя должна показывать окна, старые — не стираться.
import { describe, test, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSchedulePage } from './useSchedulePage.js'
import { useScheduleStore } from '../../../logic/store/index.js'
import { useAuthStore } from '../../../logic/store/index.js'
import { useRosterStore } from '../../../logic/store/index.js'
import { pruneStudentWindows } from '../../../logic/actions/index.js'

const fetchCalls = []
globalThis.fetch = async (url) => {
  fetchCalls.push(String(url))
  const u = new URL(String(url), 'http://x')
  if (u.pathname.endsWith('/slots')) {
    const df = u.searchParams.get('date_from')
    return {
      ok: true,
      status: 200,
      json: async () => ({ slots: [{ start: `${df}T09:00:00`, end: `${df}T10:00:00` }] }),
    }
  }
  return { ok: true, status: 200, json: async () => ({}) }
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchCalls.length = 0
  useAuthStore().setSession({ accessToken: 't', refreshToken: 'r', user: { role: 'student' } })
  useRosterStore().setTutors([{ tutor_user_id: 2, full_name: 'T', slot_step_minutes: 60 }])
})

describe('week navigation keeps windows', () => {
  test('листание вперёд догружает новую неделю и не стирает старую', async () => {
    const pg = useSchedulePage()
    pg.createSlots.value = [{ key: 1, tutor_user_id: 2 }]
    const week1 = { ...pg.weekRange.value }

    await pg.fetchWeekWindows()
    const afterFirst = useScheduleStore().studentWindows.length
    expect(afterFirst).toBeGreaterThan(0)
    expect(pg.freeWindows.value.length).toBe(afterFirst)

    pg.nextWeek()
    const week2 = { ...pg.weekRange.value }
    expect(week2.dateFrom).not.toBe(week1.dateFrom)

    await vi.waitFor(() => {
      const store = useScheduleStore().studentWindows
      if (!store.some((w) => w.start.slice(0, 10) === week2.dateFrom)) {
        throw new Error('week2 not loaded yet')
      }
    })
    const store = useScheduleStore().studentWindows
    const hasWeek1 = store.some((w) => w.start.slice(0, 10) === week1.dateFrom)
    const hasWeek2 = store.some((w) => w.start.slice(0, 10) === week2.dateFrom)
    expect(hasWeek1).toBe(true)
    expect(hasWeek2).toBe(true)
    expect(pg.freeWindows.value.length).toBe(store.length)
  })

  test('prune оставляет только живых репетиторов', async () => {
    const pg = useSchedulePage()
    pg.createSlots.value = [{ key: 1, tutor_user_id: 2 }]
    await pg.fetchWeekWindows()
    expect(useScheduleStore().studentWindows.length).toBeGreaterThan(0)
    pg.createSlots.value = []
    pruneStudentWindows([])
    expect(useScheduleStore().studentWindows).toEqual([])
  })

  test('outlinedWeekdays — объединение отмеченных дней weekly-форм', () => {
    const pg = useSchedulePage()
    expect(pg.outlinedWeekdays.value).toEqual([])
    pg.createSlots.value = [
      { key: 1, tutor_user_id: 2, mode: 'weekly', weekdays: { MONDAY: { on: true }, TUESDAY: { on: false } } },
      { key: 2, tutor_user_id: 5, mode: 'dates', weekdays: { MONDAY: { on: true } } },
    ]
    expect(pg.outlinedWeekdays.value).toEqual(['MONDAY'])
  })
})
