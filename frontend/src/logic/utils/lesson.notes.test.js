import { describe, it, expect } from 'vitest'
import { describeStatusNote, describeAbsence, statusHistoryLines, lessonStatusLabel } from './lesson.js'

describe('пометки урока', () => {
  it('отмена: кто, когда, почему', () => {
    expect(describeStatusNote({ status: 'CANCELLED', by: 'student', at: '2026-11-25T03:15:00', reason: 'заболел' }))
      .toBe('Отменён учеником 25.11.2026 03:15. Причина: заболел')
    expect(describeStatusNote({ status: 'REJECTED', by: 'system', at: '2026-11-26T10:00:00', reason: 'Репетитор не ответил' }))
      .toBe('Заявка отклонена системой 26.11.2026 10:00. Причина: Репетитор не ответил')
    expect(describeStatusNote({ status: 'PENDING', by: 'student' })).toBe('Заявка ждёт подтверждения репетитора')
    expect(describeStatusNote({ status: 'CANCELLED', scope: 'participant', by: 'tutor', at: '2026-11-25T03:15:00' }))
      .toBe('Репетитор убрал вас из группового урока 25.11.2026 03:15')
    expect(describeStatusNote(null)).toBe('')
  })

  it('отпуск помечает урок замороженным', () => {
    expect(describeAbsence({ status: 'VACATION', from: '2026-11-26T00:00:00', to: '2026-12-01T00:00:00' }))
      .toBe('Репетитор в отпуске с 26.11.2026 00:00 по 01.12.2026 00:00 — урок заморожен')
  })

  it('история — новые сверху', () => {
    const lines = statusHistoryLines([
      { status: 'PENDING', by: 'student', at: '2026-11-25T03:00:00' },
      { status: 'SCHEDULED', by: 'tutor', at: '2026-11-25T04:00:00' },
    ])
    expect(lines[0]).toEqual({ at: '25.11.2026 04:00', text: 'Запланирован — репетитором' })
    expect(lessonStatusLabel('SYSTEM_FINISHED')).toBe('Завершён системой')
  })
})
