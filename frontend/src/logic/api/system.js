// Системная телеметрия ядра: метрики и серверное время.
import { apiFetch } from './client.js'

export function getSystemStats() {
  return apiFetch('/api/v1/system/stats')
}

export function getServerTime() {
  return apiFetch('/api/v1/system/server-time')
}
