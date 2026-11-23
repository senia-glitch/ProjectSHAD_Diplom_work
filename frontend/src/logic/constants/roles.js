// Подписи ролей для отображения.
export const ROLE_LABELS = {
  student: 'Студент',
  tutor: 'Репетитор',
  admin: 'Администратор',
}

// Роли открытой регистрации. admin здесь нет осознанно:
// создание администраторов — только через сид/админ-панель.
export const REGISTER_ROLES = [
  { value: 'student', label: 'Студент' },
  { value: 'tutor', label: 'Репетитор' },
]

export function roleLabel(role) {
  return ROLE_LABELS[role] || role
}
