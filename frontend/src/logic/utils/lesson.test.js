import { describe, it, expect } from 'vitest'
import { lessonSafeLinks, tutorNameOf, lessonDateLabel, lessonTimeLabel } from './lesson.js'

describe('lessonSafeLinks', () => {
  it('оставляет только http(s) ссылки с подписью', () => {
    const links = [
      { alias: 'Материалы', url: 'https://example.com/1' },
      { alias: 'Звонок', url: 'http://meet.example/x' },
      { alias: 'Плохая', url: 'javascript:alert(1)' },
      { alias: 'Пустая', url: '' },
      { alias: '', url: 'https://example.com/2' },
    ]
    const out = lessonSafeLinks(links)
    expect(out).toHaveLength(3)
    expect(out[0]).toEqual({ alias: 'Материалы', url: 'https://example.com/1', safe: 'https://example.com/1' })
    expect(out[2].alias).toBe('Ссылка')
  })

  it('пустой список — пустой результат', () => {
    expect(lessonSafeLinks(null)).toEqual([])
  })
})

describe('tutorNameOf', () => {
  const tutors = [{ tutor_id: 42, full_name: 'Анна С.' }]

  it('имя из ростера', () => {
    expect(tutorNameOf({ tutor_id: 42 }, tutors)).toBe('Анна С.')
  })

  it('без ростера — фолбэк по id', () => {
    expect(tutorNameOf({ tutor_id: 42 }, [])).toBe('Репетитор #42')
    expect(tutorNameOf({}, tutors)).toBe('')
    expect(tutorNameOf(null, tutors)).toBe('')
  })
})

describe('lessonDateLabel', () => {
  it('человекочитаемая дата', () => {
    expect(lessonDateLabel('2030-03-02 10:00:00')).toMatch(/2 марта 2030/)
  })

  it('мусор не ломает', () => {
    expect(lessonDateLabel('')).toBe('')
  })
})

describe('lessonTimeLabel', () => {
  it('диапазон времени', () => {
    expect(lessonTimeLabel('2030-03-02 10:00:00', '2030-03-02 11:30:00')).toBe('10:00–11:30')
  })

  it('неполные данные', () => {
    expect(lessonTimeLabel('2030-03-02 10:00:00', '')).toBe('10:00')
    expect(lessonTimeLabel('', '')).toBe('')
  })
})

import { lessonPhase, durationText, boardIdFromLink } from './lesson.js'

describe('lessonPhase', () => {
  const at = (s) => new Date(s).getTime()
  const lesson = (status, start = '2030-01-10T10:00:00', end = '2030-01-10T11:00:00') => ({ status, start_time: start, end_time: end })

  it('до начала: больше часа — upcoming, меньше — soon с минутами', () => {
    expect(lessonPhase(lesson('SCHEDULED'), at('2030-01-10T07:00:00'))).toEqual({ kind: 'upcoming', minutes: 180 })
    expect(lessonPhase(lesson('SCHEDULED'), at('2030-01-10T09:35:00'))).toEqual({ kind: 'soon', minutes: 25 })
  })
  it('идёт сейчас — live с минутами до конца, после конца — over', () => {
    expect(lessonPhase(lesson('ONGOING'), at('2030-01-10T10:20:00'))).toEqual({ kind: 'live', minutes: 40 })
    expect(lessonPhase(lesson('SCHEDULED'), at('2030-01-10T11:05:00')).kind).toBe('over')
  })
  it('статусы важнее времени: заявка, отмена, завершён', () => {
    expect(lessonPhase(lesson('PENDING'), at('2030-01-10T09:00:00')).kind).toBe('request')
    expect(lessonPhase(lesson('CANCELLED'), at('2030-01-10T10:20:00')).kind).toBe('closed')
    expect(lessonPhase(lesson('REJECTED'), at('2030-01-10T09:00:00')).kind).toBe('closed')
    expect(lessonPhase(lesson('SYSTEM_FINISHED'), at('2030-01-10T10:20:00')).kind).toBe('over')
  })
})

describe('durationText', () => {
  it('минуты, часы и дни', () => {
    expect(durationText(25)).toBe('25 мин')
    expect(durationText(120)).toBe('2 ч')
    expect(durationText(190)).toBe('3 ч 10 мин')
    expect(durationText(3 * 24 * 60 + 5)).toBe('3 дн.')
  })
})

describe('boardIdFromLink', () => {
  const origin = 'https://myshad.ru'
  it('распознаёт доску своего сайта и отвергает чужие ссылки', () => {
    expect(boardIdFromLink('https://myshad.ru/boards/AbCdEfGhIjKlMnOp12', origin)).toBe('AbCdEfGhIjKlMnOp12')
    expect(boardIdFromLink('/boards/AbCdEfGhIjKlMnOp12', origin)).toBe('AbCdEfGhIjKlMnOp12')
    expect(boardIdFromLink('https://evil.example/boards/AbCdEfGhIjKlMnOp12', origin)).toBeNull()
    expect(boardIdFromLink('https://zoom.us/j/123', origin)).toBeNull()
  })
})
