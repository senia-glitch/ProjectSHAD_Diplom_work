// Строки платежей и сводка: из детализации уроков в плоский реестр.
// Чистые функции — страница только рисует и вызывает действия.

export function buildPaymentRows(lessons) {
  const rows = []
  for (const lesson of lessons || []) {
    for (const s of lesson.students || []) {
      rows.push({
        lesson_id: lesson.lesson_id,
        date: lesson.date,
        start: lesson.start,
        end: lesson.end,
        status: lesson.status,
        is_group: Boolean(lesson.is_group),
        student_id: s.student_id,
        student_user_id: s.student_user_id,
        student_name: s.student_name,
        amount: s.amount || 0,
        paid: Boolean(s.paid),
      })
    }
  }
  // Новые сверху: ISO-строки дат сравниваются лексикографически.
  // Равные ключи дают 0 — иначе сортировка внутри одного дня нестабильна.
  return rows.sort((a, b) => {
    const ka = `${a.date} ${a.start}`
    const kb = `${b.date} ${b.start}`
    return ka < kb ? 1 : ka > kb ? -1 : 0
  })
}

export function summarizePayments(rows) {
  let collected = 0
  let debt = 0
  const byStudent = new Map()
  for (const r of rows || []) {
    if (r.paid) collected += r.amount
    else debt += r.amount
    let entry = byStudent.get(r.student_id)
    if (!entry) {
      entry = {
        student_id: r.student_id,
        student_name: r.student_name,
        collected: 0,
        debt: 0,
      }
      byStudent.set(r.student_id, entry)
    }
    if (r.paid) entry.collected += r.amount
    else entry.debt += r.amount
  }
  return {
    collected,
    debt,
    byStudent: [...byStudent.values()].sort((a, b) => b.debt - a.debt),
  }
}

export function filterPaymentRows(rows, paid) {
  if (paid === 'paid') return rows.filter((r) => r.paid)
  if (paid === 'unpaid') return rows.filter((r) => !r.paid)
  return rows
}
