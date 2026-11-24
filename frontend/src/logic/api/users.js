// Пользователь: регистрация и собственный профиль.
import { apiFetch } from './client.js'

export function postRegister({ role, username, password, fullName, email, timezoneOffset }) {
  return apiFetch('/api/v1/users/register', {
    method: 'POST',
    body: { role, username, password, full_name: fullName, email, timezone_offset: timezoneOffset ?? 0 },
    auth: false,
    retry: false,
  })
}

export function getMe() {
  return apiFetch('/api/v1/users/me')
}

export function patchMe(patch) {
  return apiFetch('/api/v1/users/me', { method: 'PATCH', body: patch })
}
