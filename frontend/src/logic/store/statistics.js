// Данные страницы статистики репетитора.
// filters живут здесь, чтобы вкладки-роуты делили один фильтр.
import { defineStore } from 'pinia'

export const DEFAULT_STAT_FILTERS = {
  year: new Date().getFullYear(),
  preset: 'year',
  month: '',
  weekAnchor: '',
  customFrom: '',
  customTo: '',
  granularity: 'auto',
  studentIds: [],
  // Динамика (новая): режим таблицы и метрика. Переключение метрики/режима
  // не требует перезагрузки — пивот строится на клиенте из годовых деталей.
  dynMode: 'year',
  dynMetric: 'conducted',
}

export const DEFAULT_REPORT_INCLUDE = {
  conducted: true,
  planned: true,
  cancelled: true,
  paid: true,
  unpaid: true,
}

export const useStatisticsStore = defineStore('statistics', {
  state: () => ({
    data: null,
    lessons: [],
    lessonsLoading: false,
    lessonsError: '',
    filters: { ...DEFAULT_STAT_FILTERS },
    // «Что включаем» в отчёт динамики + показ ссылок.
    // Живёт в сторе: контролы — в сайдбаре, потребление — в отчёте.
    reportInclude: { ...DEFAULT_REPORT_INCLUDE },
    reportShowLinks: false,
    // Вид блока «Уроки»: контролы — в сайдбаре, потребление — в списке.
    lessonsStatuses: ['FINISHED', 'SCHEDULED'],
    lessonsType: 'all',
    // Сигнал выгрузки блока «Уроки»: сайдбар просит, список выполняет.
    lessonsExport: { kind: '', n: 0 },
  }),
  actions: {
    setStatistics(data) {
      this.data = data
    },
    setLessons(lessons) {
      this.lessons = lessons || []
    },
    setFilters(patch) {
      // Мутация по месту, БЕЗ замены объекта: все компоненты держат
      // ссылку на statsStore.filters, замена отвязывала их от стора
      // (UI замирал, вотчер переставал срабатывать).
      Object.assign(this.filters, patch)
    },
    setReportInclude(patch) {
      Object.assign(this.reportInclude, patch)
    },
    setReportShowLinks(v) {
      this.reportShowLinks = Boolean(v)
    },
    resetReportInclude() {
      Object.assign(this.reportInclude, DEFAULT_REPORT_INCLUDE)
      this.reportShowLinks = false
    },
    toggleLessonsStatus(v) {
      const list = this.lessonsStatuses.includes(v)
        ? this.lessonsStatuses.filter((x) => x !== v)
        : [...this.lessonsStatuses, v]
      this.lessonsStatuses = list
    },
    setLessonsType(v) {
      this.lessonsType = v
    },
    resetLessonsView() {
      this.lessonsStatuses = ['FINISHED', 'SCHEDULED']
      this.lessonsType = 'all'
    },
    requestLessonsExport(kind) {
      this.lessonsExport = { kind, n: this.lessonsExport.n + 1 }
    },
    clearStatistics() {
      this.data = null
    },
  },
})
