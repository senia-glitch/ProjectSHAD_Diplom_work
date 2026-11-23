// Эндпойнты аутентификации. Ходят без токена и без ретраев (§6.3).
import { apiFetch } from './client.js'

export function postLogin({ username, password }) {
  return apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: { username, password },
    auth: false,
    retry: false,
  })
}

export function postRefresh({ refreshToken }) {
  return apiFetch('/api/v1/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    auth: false,
    retry: false,
  })
}

export function postLogout({ refreshToken }) {
  return apiFetch('/api/v1/auth/logout', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    auth: false,
    retry: false,
  })
}
