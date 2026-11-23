// Доменные расчёты цены со скидкой. Чистые функции без состояния.
export function finalPrice(hourlyRate, discount) {
  return Math.round(hourlyRate * (1 - discount / 100))
}

export function discountAmount(hourlyRate, discount) {
  return Math.round((hourlyRate * discount) / 100)
}
