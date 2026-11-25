// Перевод ошибок API на русский язык на границе транспорта.
// Backend возвращает англоязычные `error.message`; контракт API не меняется,
// исходный текст остаётся в ApiError.payload. Неизвестное сообщение
// показывается как есть, чтобы не терять смысл новой ошибки.

const EXACT = {
  'Lesson is not awaiting confirmation': 'Заявка уже решена',
  'Lesson request has expired': 'Срок заявки истёк: урок уже начался',
  'Time is already taken by another lesson': 'Это время уже занято другим уроком',
  'Link is not awaiting confirmation': 'Заявка на связь уже решена',
  'Only the other side can answer this link request': 'Ответить на заявку может только вторая сторона',
  'absence_from and absence_to are required': 'Укажите начало и конец периода',
  'absence_from must be less than absence_to': 'Конец периода должен быть позже начала',
  'Absence period is already over': 'Этот период уже закончился',
  'Invalid username or password': 'Неверный логин или пароль',
  'Username or email already registered': 'Логин или почта уже зарегистрированы',
  'Username, email or personal number already registered': 'Логин, почта или личный код уже зарегистрированы',
  'Username, email or personal number already in use': 'Логин, почта или личный код уже используются',
  'User with this personal number not found': 'Пользователь с таким личным кодом не найден',
  'Authentication required': 'Требуется вход в аккаунт',
  Unauthorized: 'Требуется вход в аккаунт',
  Forbidden: 'Недостаточно прав для этого действия',
  'Invalid token': 'Сессия недействительна, войдите снова',
  'Invalid token type': 'Сессия недействительна, войдите снова',
  'Refresh token revoked': 'Сессия завершена, войдите снова',
  'User not found': 'Пользователь не найден',
  'Tutor not found': 'Репетитор не найден',
  'Student not found': 'Ученик не найден',
  'Tutor profile not found': 'Профиль репетитора не найден',
  'Student profile not found': 'Профиль ученика не найден',
  'Tutor settings not found': 'Настройки репетитора не найдены',
  'Student settings not found': 'Настройки ученика не найдены',
  'Configuration not found': 'Связь ученика и репетитора не найдена',
  'No configuration found for this student-tutor pair': 'Связь ученика и репетитора не найдена',
  "You don't have a configuration with this tutor": 'Вы не связаны с этим репетитором',
  'Student has no configuration with you': 'Ученик не связан с вами',
  'You do not own this configuration': 'Эта связь принадлежит другому репетитору',
  'Target user is not a tutor': 'Пользователь не является репетитором',
  'Target user is not a student': 'Пользователь не является учеником',
  'Student and tutor cannot be the same user': 'Нельзя связать аккаунт с самим собой',
  'Student is not active': 'Ученик неактивен',
  'Tutor is not working': 'Репетитор сейчас не принимает записи',
  'Self-booking is not available for you': 'Самостоятельная запись вам недоступна',
  'Self-booking is not allowed by configuration': 'Самостоятельная запись отключена репетитором',
  'Self-booking is not allowed for you': 'Самостоятельная запись вам недоступна',
  'Lesson not found': 'Урок не найден',
  'Lesson not found or access denied': 'Урок не найден или недоступен',
  'Lesson already exists': 'Такой урок уже существует',
  'Lesson overlaps with an existing one': 'Урок пересекается с уже существующим',
  'Booking overlaps with an existing one': 'Бронь пересекается с уже существующей',
  'Requested time slot is not available': 'Выбранное время недоступно',
  'Student is already a participant': 'Ученик уже участвует в уроке',
  'Participant not found': 'Участник не найден',
  'Participant record is cancelled': 'Участие уже отменено',
  'Not a participant of this lesson': 'Вы не участвуете в этом уроке',
  'Only group lessons can be joined directly': 'Напрямую можно записаться только на групповой урок',
  'You can only manage your own lessons': 'Можно управлять только своими уроками',
  'You can only update your own bookings': 'Можно изменять только свои брони',
  'You can only delete your own bookings': 'Можно удалять только свои брони',
  'Notification not found': 'Уведомление не найдено',
  'No fields to update': 'Нет изменений для сохранения',
  'full_name must not be empty': 'ФИО не может быть пустым',
  'start_time must be less than end_time': 'Начало должно быть раньше окончания',
  'display_time_from must be less than display_time_to': 'Время «от» должно быть раньше времени «до»',
  'date_from must not be greater than date_to': 'Начальная дата не может быть позже конечной',
  'date_from must be less than or equal to date_to': 'Начальная дата не может быть позже конечной',
  'link_lead_time_minutes must be between 0 and 15': 'Время показа ссылки — от 0 до 15 минут',
  'slot_step_minutes must be greater than 0': 'Шаг записи должен быть больше нуля',
  'Invalid year': 'Некорректный год',
  'Request timeout': 'Сервер не ответил вовремя. Попробуйте ещё раз',
  'Validation failed': 'Проверьте правильность заполнения полей',
  'Not found': 'Не найдено',
  'Internal server error': 'Внутренняя ошибка сервера. Попробуйте позже',
}

const PATTERNS = [
  [/^Lesson must be booked at least (\d+)h in advance$/, (m) => `Записаться можно не позднее чем за ${m[1]} ч до начала`],
  [/^Lesson is already (\w+)$/, () => 'Статус урока уже установлен'],
  [/^Lesson duration cannot exceed/, () => 'Урок не может длиться дольше 168 часов'],
  [/^Lesson \d+ not found$/, () => 'Урок не найден'],
  [/^Booking \d+ not found$/, () => 'Бронь не найдена'],
  [/^User \d+ not found$/, () => 'Пользователь не найден'],
  [/^Configuration for student \d+ and tutor \d+ already exists$/, () => 'Ученик уже связан с этим репетитором'],
  [/^password must be at most \d+ bytes$/, () => 'Пароль слишком длинный'],
  [/^Cancellation deadline passed for student \d+ \((\d+)h before lesson\)$/, (m) => `Срок отмены прошёл: отменить можно не позже чем за ${m[1]} ч до начала. Обратитесь к репетитору`],
  [/^Cannot leave lesson in status \w+$/, () => 'Этот урок уже нельзя отменить'],
]

function byStatus(status) {
  if (status === 0) return 'Нет соединения с сервером. Проверьте подключение'
  if (status === 401) return 'Требуется вход в аккаунт'
  if (status === 403) return 'Недостаточно прав для этого действия'
  if (status === 404) return 'Не найдено'
  if (status === 409) return 'Конфликт с текущими данными'
  if (status === 422) return 'Проверьте правильность заполнения полей'
  if (status === 429) return 'Слишком много запросов. Подождите немного'
  if (status >= 500) return 'Сервер временно недоступен. Попробуйте позже'
  return `Не удалось выполнить запрос (код ${status})`
}

export function translateErrorMessage(status, message) {
  const text = typeof message === 'string' ? message.trim() : ''
  // 5xx без понятного текста и прокси-ответы (502/503/504) — общая формулировка.
  if (!text || status >= 502) return byStatus(status)
  if (EXACT[text]) return EXACT[text]
  for (const [re, make] of PATTERNS) {
    const m = text.match(re)
    if (m) return make(m)
  }
  return text
}
