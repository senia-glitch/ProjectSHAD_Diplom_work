<template>
  <MainLayout :is-logged-in="isLoggedIn" :role="role" @logout="handleLogout">
    <div class="payments-page">
      <div class="page-header">
        <div class="page-title-row">
          <h1 class="page-title">Оплаты</h1>
        </div>
        <p class="page-desc">Реестр оплат по урокам: отметка оплаты и задолженности</p>
      </div>

      <div class="filters">
        <label class="fl">Дата от
          <input v-model="dateFrom" type="date" />
        </label>
        <label class="fl">до
          <input v-model="dateTo" type="date" />
        </label>
        <label class="fl">Ученик
          <select v-model="studentId">
            <option value="">Все</option>
            <option v-for="s in students" :key="s.student_id" :value="String(s.student_id)">
              {{ s.full_name || s.username || `Ученик #${s.student_id}` }}
            </option>
          </select>
        </label>
        <label class="fl">Статус
          <select v-model="paidFilter">
            <option value="all">Все</option>
            <option value="paid">Оплачено</option>
            <option value="unpaid">Не оплачено</option>
          </select>
        </label>
      </div>

      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="error" class="fmsg fmsg--err">{{ error }}</div>
      <template v-else>
        <div class="summary">
          <div class="metric-card">
            <span class="metric-k">Собрано</span>
            <span class="metric-v metric-v--ok">{{ formatMoney(summary.collected) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">Долг</span>
            <span class="metric-v" :class="{ 'metric-v--bad': summary.debt }">{{ formatMoney(summary.debt) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-k">Записей</span>
            <span class="metric-v">{{ rows.length }}</span>
          </div>
        </div>

        <div v-if="!rows.length" class="empty">За период оплат нет</div>

        <template v-else>
          <div class="table-wrap">
            <table class="pay-table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Время</th>
                  <th>Ученик</th>
                  <th class="col-num">Сумма</th>
                  <th>Оплата</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rows" :key="r.lesson_id + ':' + r.student_id">
                  <td>{{ r.date }}</td>
                  <td>{{ r.start }}–{{ r.end }}</td>
                  <td>{{ r.student_name }}</td>
                  <td class="col-num">{{ formatMoney(r.amount) }}</td>
                  <td>
                    <button
                      type="button"
                      class="pay-toggle"
                      :class="{ 'pay-toggle--on': r.paid }"
                      :disabled="togglingId === r.lesson_id + ':' + r.student_id"
                      :title="r.paid ? 'Отметить неоплаченным' : 'Отметить оплаченным'"
                      @click="togglePaid(r)"
                    >
                      {{ r.paid ? 'Оплачено' : 'Не оплачено' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <section v-if="summary.byStudent.length" class="card">
            <h2 class="card-title">Итоги по ученикам</h2>
            <div class="table-wrap">
              <table class="pay-table">
                <thead>
                  <tr>
                    <th>Ученик</th>
                    <th class="col-num">Собрано</th>
                    <th class="col-num">Долг</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in summary.byStudent" :key="s.student_id">
                    <td>{{ s.student_name }}</td>
                    <td class="col-num">{{ formatMoney(s.collected) }}</td>
                    <td class="col-num" :class="{ 'metric-v--bad': s.debt }">{{ formatMoney(s.debt) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import MainLayout from '../../blocks/layout/MainLayout.vue'
import { useUser, useLogout } from '../../composables/index.js'
import { formatMoney } from '../../../logic/utils/index.js'
import { usePaymentsPage } from './usePaymentsPage.js'

const { role, isLoggedIn } = useUser()
const { handleLogout } = useLogout()
const {
  dateFrom, dateTo, studentId, paidFilter,
  students, rows, summary, loading, error, togglingId,
  togglePaid,
} = usePaymentsPage()
</script>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 16px;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
}
.metric-k { font-size: 11px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; color: var(--color-gray-500); }
.metric-v { font-size: 18px; font-weight: 600; color: var(--color-primary); }
.metric-v--ok { color: var(--color-success); }
.metric-v--bad { color: var(--color-danger); }
.table-wrap { overflow-x: auto; margin-bottom: 20px; }
.pay-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.pay-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--color-gray-500);
  border-bottom: 2px solid var(--color-gray-200);
}
.pay-table td { padding: 8px 10px; border-bottom: 1px solid var(--color-gray-100); color: var(--color-gray-800); }
.col-num { text-align: right; font-variant-numeric: tabular-nums; }
.pay-toggle {
  padding: 3px 8px;
  border: 1px solid var(--color-gray-300);
  border-radius: var(--radius-md, 6px);
  background: var(--color-white);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-gray-600);
  cursor: pointer;
}
.pay-toggle:hover:not(:disabled) { border-color: var(--color-accent); color: var(--color-accent); }
.pay-toggle--on {
  background: var(--color-success);
  border-color: var(--color-success);
  color: var(--on-accent);
}
.pay-toggle--on:hover:not(:disabled) { border-color: var(--color-success); color: var(--on-accent); }
.pay-toggle:disabled { opacity: 0.6; cursor: not-allowed; }
.card {
  background: var(--color-white);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg, 12px);
  padding: 16px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--color-primary); margin-bottom: 12px; }
.empty { padding: 40px 20px; text-align: center; font-size: 14px; color: var(--color-gray-500); }
</style>
