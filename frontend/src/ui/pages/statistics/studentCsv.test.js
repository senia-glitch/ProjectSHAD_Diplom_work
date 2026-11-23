import { describe, it, expect } from 'vitest'
import { studentBriefCsv, studentDetailedCsv, lessonsCsv, studentsTableToCsv, reportFileName } from './studentCsv.js'

const row = {
  student_id: 5, student_name: 'Иван', lessons: 4, billed_hours: 6, revenue: 7200,
  cancelled: 1, no_show: 0, forecast_lessons: 1, forecast_revenue: 1800,
  first_lesson: '2030-03-02', last_lesson: '2030-05-06',
}

const lessons = [{
  lesson_id: 1, date: '2030-03-02', start: '10:00', end: '11:00', minutes: 60,
  is_group: false, status: 'FINISHED', descriptions: 'Дроби',
  links: [{ alias: 'М', url: 'https://example.com/1' }],
  students: [{ student_id: 5, student_name: 'Иван', amount: 1800, estimated: false }],
  total: 1800,
}]

describe('reportFileName', () => {
  it('шаблон statistika_тип_период_ученик', () => {
    expect(reportFileName('summary', '2030-03-01_2030-03-31')).toBe('statistika_summary_2030-03-01_2030-03-31.csv')
    expect(reportFileName('brief', 'p', 5)).toBe('statistika_brief_p_5.csv')
  })
})

describe('studentBriefCsv', () => {
  it('одна строка итогов с BOM', () => {
    const csv = studentBriefCsv(row)
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
    expect(csv).toContain('Средний чек')
    expect(csv).toContain('7200')
  })
})

describe('studentDetailedCsv', () => {
  it('только уроки ученика со всеми полями', () => {
    const csv = studentDetailedCsv(lessons, 5)
    expect(csv).toContain('2030-03-02')
    expect(csv).toContain('Дроби')
    expect(csv).toContain('https://example.com/1')
    expect(studentDetailedCsv(lessons, 6)).not.toContain('2030-03-02')
  })
})

describe('studentsTableToCsv', () => {
  it('таблица как на экране плюс долг', () => {
    const csv = studentsTableToCsv([{ ...row, statusText: 'Активен' }], { 5: 1800 })
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
    expect(csv).toContain('Долг')
    expect(csv).toContain('Активен')
    expect(csv).toContain('1800')
  })
})

describe('lessonsCsv', () => {
  it('строки хронологии', () => {
    const csv = lessonsCsv(lessons)
    expect(csv).toContain('Дата')
    expect(csv).toContain('Иван')
    expect(csv).toContain('1800')
  })
})
