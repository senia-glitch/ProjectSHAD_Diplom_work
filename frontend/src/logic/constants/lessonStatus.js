// Статусы уроков: подпись и цвет значка на сетке.
export const LESSON_STATUSES = [
  { value: 'SCHEDULED', label: 'Запланирован', color: 'var(--color-gray-500)' },
  { value: 'ONGOING', label: 'Идёт', color: 'var(--color-success)' },
  { value: 'FINISHED', label: 'Завершён', color: 'var(--color-gray-800)' },
  { value: 'CANCELLED', label: 'Отменён', color: 'var(--color-danger)' },
  { value: 'NO_SHOW', label: 'Неявка', color: 'var(--status-no-show)' },
]

// Статусы, которые репетитор ставит вручную в форме урока.
export const MANUAL_LESSON_STATUSES = [
  { value: 'FINISHED', label: 'Завершён' },
  { value: 'CANCELLED', label: 'Отменён' },
  { value: 'NO_SHOW', label: 'Неявка' },
]
