// Лимиты предметной области (не env, не feature flags).
export const LESSON_COUNT_MIN = 1
export const LESSON_COUNT_MAX = 500
export const LESSON_COUNT_DEFAULT = 4

// Страховка генератора превью: дальше 5 лет не считаем.
export const PREVIEW_WEEKS_CAP = 260

// Периодичность «раз в N недель»: значения селекта.
export const PERIOD_MIN = 1
export const PERIOD_MAX = 12

// Шаг записи ученика (минуты): значения селекта в форме связи.
export const SLOT_STEP_OPTIONS = [15, 30, 45, 60, 90, 120]
export const SLOT_STEP_DEFAULT = 60

// Диапазон запроса свободных окон: не шире 120 дней за раз.
export const SLOTS_RANGE_MAX_DAYS = 120
