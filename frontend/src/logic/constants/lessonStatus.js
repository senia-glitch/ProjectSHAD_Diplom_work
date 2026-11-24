// Статусы уроков: подпись и цвет значка на сетке.
export const LESSON_STATUSES = [
  { value: 'PENDING', label: 'Ожидает подтверждения', color: 'var(--color-warning, #d4a72c)' },
  { value: 'SCHEDULED', label: 'Запланирован', color: 'var(--color-gray-500)' },
  { value: 'ONGOING', label: 'Идёт', color: 'var(--color-success)' },
  { value: 'FINISHED', label: 'Завершён', color: 'var(--color-gray-800)' },
  { value: 'CANCELLED', label: 'Отменён', color: 'var(--color-danger)' },
  { value: 'NO_SHOW', label: 'Неявка', color: 'var(--status-no-show)' },
  { value: 'REJECTED', label: 'Заявка отклонена', color: 'var(--color-danger)' },
  { value: 'SYSTEM_FINISHED', label: 'Завершён системой', color: 'var(--color-gray-600)' },
]

// Статусы, которые репетитор ставит вручную в форме урока.
export const MANUAL_LESSON_STATUSES = [
  { value: 'FINISHED', label: 'Завершён' },
  { value: 'CANCELLED', label: 'Отменён' },
  { value: 'NO_SHOW', label: 'Неявка' },
]

// Неактивные уроки: время не занимают, на сетке приглушены.
export const INACTIVE_LESSON_STATUSES = ['CANCELLED', 'REJECTED']

// Кто изменил статус урока.
export const STATUS_ACTORS = { system: 'системой', tutor: 'репетитором', student: 'учеником' }

export const ABSENCE_LABELS = { VACATION: 'в отпуске', SICK: 'болеет' }
