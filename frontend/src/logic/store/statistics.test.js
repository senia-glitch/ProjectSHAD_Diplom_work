import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { watch, nextTick } from 'vue'
import { useStatisticsStore, DEFAULT_STAT_FILTERS } from './statistics.js'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('statistics store filters', () => {
  it('setFilters не подменяет объект: ссылка стабильна', () => {
    const store = useStatisticsStore()
    const ref1 = store.filters
    store.setFilters({ preset: 'month' })
    store.setFilters({ studentIds: [5] })
    expect(store.filters).toBe(ref1)
    expect(store.filters.preset).toBe('month')
    expect(store.filters.studentIds).toEqual([5])
    expect(store.filters.year).toBe(DEFAULT_STAT_FILTERS.year)
  })

  it('вотчер на filters срабатывает и после нескольких setFilters', async () => {
    const store = useStatisticsStore()
    let fires = 0
    watch(
      () => store.filters,
      () => { fires += 1 },
      { deep: true },
    )
    store.setFilters({ preset: 'month' })
    await nextTick()
    store.setFilters({ preset: 'week' })
    await nextTick()
    expect(fires).toBe(2)
  })

  it('reportInclude/showLinks: patch и сброс', () => {
    const store = useStatisticsStore()
    expect(store.reportInclude.conducted).toBe(true)
    store.setReportInclude({ conducted: false })
    expect(store.reportInclude.conducted).toBe(false)
    store.setReportShowLinks(true)
    expect(store.reportShowLinks).toBe(true)
    store.resetReportInclude()
    expect(store.reportInclude.conducted).toBe(true)
    expect(store.reportShowLinks).toBe(false)
  })

  it('вид уроков и сигнал экспорта', () => {
    const store = useStatisticsStore()
    expect(store.lessonsStatuses).toEqual(['FINISHED', 'SCHEDULED'])
    store.toggleLessonsStatus('CANCELLED')
    expect(store.lessonsStatuses).toContain('CANCELLED')
    store.toggleLessonsStatus('FINISHED')
    expect(store.lessonsStatuses).not.toContain('FINISHED')
    store.setLessonsType('group')
    expect(store.lessonsType).toBe('group')
    store.requestLessonsExport('csv')
    expect(store.lessonsExport).toEqual({ kind: 'csv', n: 1 })
    store.resetLessonsView()
    expect(store.lessonsStatuses).toEqual(['FINISHED', 'SCHEDULED'])
    expect(store.lessonsType).toBe('all')
  })

  it('clearStatistics не трогает фильтр', () => {
    const store = useStatisticsStore()
    const ref1 = store.filters
    store.setStatistics({ totals: {} })
    store.clearStatistics()
    expect(store.filters).toBe(ref1)
    expect(store.data).toBeNull()
  })
})
