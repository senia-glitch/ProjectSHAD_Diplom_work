<template>
  <AdminShell title="Логи интерфейса" lead="События фронтенда: API, навигация, интерфейс, ошибки.">
    <div class="logs-page">

      <div class="filters">
        <label class="fl">Уровень
          <select v-model="lvl">
            <option value="">Все</option>
            <option value="info">info</option>
            <option value="warn">warn</option>
            <option value="error">error</option>
          </select>
        </label>
        <label class="fl">Категория
          <select v-model="cat">
            <option value="">Все</option>
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
        <label class="fl">Дата
          <input v-model="date" type="date" />
        </label>
        <label class="fl fl--grow">Поиск
          <input v-model="q" type="search" placeholder="текст сообщения" />
        </label>
        <button type="button" class="btn btn--gry" @click="reset">Сбросить</button>
      </div>

      <div v-if="loading && !items.length" class="loading">Загрузка...</div>
      <div v-else-if="error" class="fmsg fmsg--err">{{ error }}</div>
      <div v-else-if="!items.length" class="empty">Записей нет</div>

      <template v-else>
        <div class="table-wrap">
          <table class="log-table">
            <thead>
              <tr>
                <th class="col-ts">Время</th>
                <th class="col-lvl">Уровень</th>
                <th class="col-cat">Категория</th>
                <th>Сообщение</th>
                <th>Данные</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, i) in items" :key="i">
                <td class="col-ts">{{ formatLogTs(item.ts) }}</td>
                <td><span :class="logLevelClass(item.lvl)">{{ item.lvl }}</span></td>
                <td class="col-cat">{{ item.cat }}</td>
                <td class="col-msg">{{ item.msg }}</td>
                <td class="col-data" :title="item.data ? JSON.stringify(item.data) : ''">{{ formatLogData(item.data) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pager">
          <button type="button" class="btn btn--gry btn--sm" :disabled="!hasPrev" @click="goPrev">← Назад</button>
          <span class="pager-info">Страница {{ page }} из {{ pages }} · всего {{ total }}</span>
          <button type="button" class="btn btn--gry btn--sm" :disabled="!hasNext" @click="goNext">Вперёд →</button>
        </div>
      </template>
    </div>
  </AdminShell>
</template>

<script setup>
import AdminShell from '../AdminShell.vue'
import { useLogsPage } from './useLogsPage.js'
import { formatLogTs, logLevelClass, formatLogData } from '../../../../logic/utils/index.js'

// Категории фронтенд-логгера (logic/logger/logger.js).
const CATEGORIES = ['api', 'ui', 'nav', 'form', 'state', 'error']

const {
  lvl, cat, date, q,
  items, total, loading, error,
  page, pages, hasPrev, hasNext,
  goPrev, goNext, reset,
} = useLogsPage()
</script>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 16px;
}
.fl { display: flex; flex-direction: column; gap: 4px; font-size: 13px; font-weight: 500; color: var(--color-gray-700); }
.fl--grow { flex: 1; min-width: 180px; }
.fl select, .fl input {
  padding: 7px 10px;
  border: 1px solid var(--color-gray-300);
  border-radius: var(--radius-md, 6px);
  font-size: 13px;
  font-family: var(--font-family);
  color: var(--color-gray-800);
  box-sizing: border-box;
}
.fl select:focus, .fl input:focus { border-color: var(--color-accent); outline: none; }
.table-wrap { overflow-x: auto; }
.log-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.log-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--color-gray-500);
  border-bottom: 2px solid var(--color-gray-200);
}
.log-table td { padding: 6px 10px; border-bottom: 1px solid var(--color-gray-100); color: var(--color-gray-800); vertical-align: top; }
.col-ts { white-space: nowrap; color: var(--color-gray-600); font-variant-numeric: tabular-nums; }
.col-cat { white-space: nowrap; color: var(--color-gray-600); }
.col-msg { min-width: 260px; }
.col-data { max-width: 280px; color: var(--color-gray-500); font-size: 11px; word-break: break-all; }
.lvl {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--radius-md, 6px);
  font-size: 11px;
  font-weight: 600;
}
.lvl--info { background: var(--color-gray-100); color: var(--color-gray-600); }
.lvl--warn { background: #fff3bf; color: #e67700; }
.lvl--error { background: #ffc9c9; color: #c92a2a; }
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}
.pager-info { font-size: 13px; color: var(--color-gray-600); }
.empty { padding: 40px 20px; text-align: center; font-size: 14px; color: var(--color-gray-500); }
</style>
