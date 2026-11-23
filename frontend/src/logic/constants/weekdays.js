// Справочник дней недели. Единственное место правды о порядке,
// подписях и соответствии JS-getDay() ↔ API-именам.
export const WEEK_DAYS = [
  { id: 'MONDAY', short: 'Пн', full: 'Понедельник' },
  { id: 'TUESDAY', short: 'Вт', full: 'Вторник' },
  { id: 'WEDNESDAY', short: 'Ср', full: 'Среда' },
  { id: 'THURSDAY', short: 'Чт', full: 'Четверг' },
  { id: 'FRIDAY', short: 'Пт', full: 'Пятница' },
  { id: 'SATURDAY', short: 'Сб', full: 'Суббота' },
  { id: 'SUNDAY', short: 'Вс', full: 'Воскресенье' },
]

// Индекс дня недели в порядке Пн..Вс из JS Date.getDay() (0 = Вс).
export function weekdayIndexFromDate(date) {
  return (date.getDay() + 6) % 7
}

export function weekdayIdFromDate(date) {
  return WEEK_DAYS[weekdayIndexFromDate(date)].id
}

// Короткие подписи для заголовков сетки, индекс — getDay().
export const WD_SHORT = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

export const WEEKDAY_ORDER = WEEK_DAYS.map((d) => d.id)

export const WEEKDAY_LABELS = Object.fromEntries(WEEK_DAYS.map((d) => [d.id, d.full]))

export const WEEKDAY_SHORT = Object.fromEntries(WEEK_DAYS.map((d) => [d.id, d.short]))

// Короткие названия месяцев для диапазона недели.
export const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
