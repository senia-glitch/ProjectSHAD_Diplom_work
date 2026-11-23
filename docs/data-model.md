# Модель данных

## Маппинг понятий на таблицы

| Понятие | Таблица | Ключевые поля |
|---------|---------|---------------|
| Ресурс | `tutors` | `id`, `user_id` |
| Владелец ресурса | `tutors` → `users` | — |
| Участник | `students` → `users` | — |
| Связь | `configurations` | `student_id`, `tutor_id`, `hourly_rate`, `discount`, `slot_step_minutes`, `link_visibility_enabled`, `link_lead_time_minutes`, `allow_self_booking`, `booking_lead_time_hours`, `cancellation_lead_time_hours` |
| Настройки ресурса | `tutor_settings` | `tutor_id`, `self_booking_mode`, `self_booking_whitelist` (JSON), `default_links` (JSON), `booking_lead_time_hours`, `cancellation_lead_time_hours` |
| Настройки участника | `student_settings` | `student_id`, `status` |
| Бронь | `bookings` | `tutor_id`, `weekday`, `start_time`, `end_time`, `access_rule`, `access_targets` |
| Запись | `lessons` | `tutor_id`, `start_time`, `end_time`, `created_by_id` |
| Участник записи | `lesson_participants` | `lesson_id`, `student_id` |

## Правила доступа

| Значение | Описание |
|----------|----------|
| `EVERYONE` | Интервал доступен всем |
| `ONLY` | Интервал доступен только перечисленным (`access_targets`) |
| `ALL_EXCEPT` | Интервал доступен всем, кроме перечисленных (`access_targets`) |
| `NOBODY` | Интервал недоступен никому |

По умолчанию всё время недоступно. Бронь **открывает** время, а не закрывает.

## JSON-поля
Все JSON-колонки (`tutor_settings.self_booking_whitelist/default_links`,
`configurations.default_links`, `bookings.access_targets/booking_metadata`,
`lessons.lesson_settings/links/metadata`) сериализуются единым кодеком.
Правила: `docs/json-fields.md`, код: `app/utils/json_codec.py`.
