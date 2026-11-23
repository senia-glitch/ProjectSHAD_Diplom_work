<template>
  <div class="payments-tab">
    <div v-if="loading" class="state-box"><p>Загрузка...</p></div>
    <div v-else-if="error" class="state-box state-box--warn"><p>{{ error }}</p></div>
    <template v-else>
      <div class="summary">
        <div class="metric-card">
          <span class="metric-label">Собрано</span>
          <span class="metric-value">{{ formatMoney(summary.collected) }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Долг</span>
          <span class="metric-value">{{ formatMoney(summary.debt) }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Записей</span>
          <span class="metric-value">{{ rows.length }}</span>
        </div>
      </div>
      <div v-if="!rows.length" class="state-box"><p>Нет данных за выбранный период</p></div>
      <template v-else>
        <table class="pay-table">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Время</th>
              <th>Ученик</th>
              <th>Сумма</th>
              <th>Оплата</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.lesson_id + ':' + r.student_id">
              <td>{{ formatDate(r.date) }}</td>
              <td>{{ r.start }}–{{ r.end }}</td>
              <td>{{ r.student_name }}</td>
              <td>{{ formatMoney(r.amount) }}</td>
              <td>
                <button
                  class="btn btn--sm"
                  :class="r.paid ? 'btn--gry' : 'btn--primary'"
                  :disabled="togglingId === r.lesson_id + ':' + r.student_id"
                  @click="togglePaid(r)"
                >
                  {{ r.paid ? 'Отменить' : 'Отметить' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <section class="card">
          <h3>Итоги по ученикам</h3>
          <table class="pay-table">
            <thead>
              <tr>
                <th>Ученик</th>
                <th>Собрано</th>
                <th>Долг</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in perStudent" :key="s.name">
                <td>{{ s.name }}</td>
                <td>{{ formatMoney(s.collected) }}</td>
                <td>{{ formatMoney(s.debt) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePaymentsPage } from '../payments/usePaymentsPage.js'

const {
  rows, summary, loading, error, togglingId,
  togglePaid,
} = usePaymentsPage({ root: true })

const perStudent = computed(() => {
  const map = new Map()
  for (const r of rows.value) {
    if (!map.has(r.student_name)) {
      map.set(r.student_name, { name: r.student_name, collected: 0, debt: 0 })
    }
    const entry = map.get(r.student_name)
    if (r.paid) entry.collected += r.amount
    else entry.debt += r.amount
  }
  return [...map.values()]
})

function formatMoney(v) {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(v || 0)
}

function formatDate(iso) {
  if (!iso) return ''
  return iso.split('-').reverse().join('.')
}
</script>

<style scoped>
.payments-tab { display: flex; flex-direction: column; gap: 16px; }
.state-box {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg); padding: 28px 20px; text-align: center;
  color: var(--color-gray-600); font-size: 14px;
}
.state-box p { margin: 0; }
.state-box--warn { padding: 12px 16px; }
.summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.metric-card {
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg); padding: 16px; display: flex; flex-direction: column; gap: 4px;
}
.metric-label { font-size: 12px; color: var(--color-gray-600); }
.metric-value { font-size: 20px; font-weight: 600; }
.pay-table { width: 100%; border-collapse: collapse; background: var(--color-white); border-radius: var(--radius-lg); overflow: hidden; }
.pay-table th, .pay-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-gray-200); font-size: 14px; }
.pay-table th { background: var(--color-gray-50); font-weight: 600; }
.card { background: var(--color-white); border: 1px solid var(--color-gray-200); border-radius: var(--radius-lg); padding: 16px; }
.card h3 { margin: 0 0 12px; font-size: 16px; }
@media (max-width: 700px) {
  .summary { grid-template-columns: 1fr; }
}
</style>
