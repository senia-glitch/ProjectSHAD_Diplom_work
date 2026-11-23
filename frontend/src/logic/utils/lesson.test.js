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
