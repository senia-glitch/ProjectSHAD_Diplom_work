// Пользователь: регистрация и собственный профиль.
import { apiFetch } from './client.js'

export function postRegister({ role, username, password, fullName, email }) {
  return apiFetch('/api/v1/users/register', {
    method: 'POST',
    body: { role, username, password, full_name: fullName, email },
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
