<template>
  <AdminShell title="База данных" lead="Прямой доступ к таблицам PostgreSQL. Все операции записываются в журнал; хэши паролей и ключей скрыты.">
    <template #actions>
      <div class="seg" role="tablist" aria-label="Режим">
        <a href="#" role="tab" :class="{ on: mode === 'tables' }" :aria-selected="mode === 'tables'" @click.prevent="mode = 'tables'">Таблицы</a>
        <a href="#" role="tab" :class="{ on: mode === 'sql' }" :aria-selected="mode === 'sql'" @click.prevent="mode = 'sql'">SQL-консоль</a>
      </div>
    </template>

    <div v-if="tablesError" class="notice error" role="alert">{{ tablesError }}</div>

    <!-- ===== Таблицы ===== -->
    <div v-show="mode === 'tables'" class="db-grid">
      <aside class="db-tables">
        <input v-model="tableFilter" type="search" placeholder="Таблица…" aria-label="Фильтр таблиц" />
        <ul>
          <li v-for="t in visibleTables" :key="t.name">
            <button type="button" :class="{ active: t.name === table }" :aria-current="t.name === table ? 'true' : null" @click="openTable(t.name)">
              <span class="grow mono">{{ t.name }}</span><small class="muted">{{ t.rows }}</small>
            </button>
          </li>
        </ul>
      </aside>

      <section class="db-main">
        <p v-if="!table" class="muted">Выберите таблицу слева.</p>
        <template v-else>
          <form class="db-filter row" @submit.prevent="reloadRows(0)">
            <input v-model="search" type="search" placeholder="Поиск по всем столбцам" aria-label="Поиск по строкам" class="grow" />
            <button type="submit" class="btn ghost">Найти</button>
            <span class="muted small nowrap">{{ rangeText }}</span>
          </form>
          <div v-if="rowsError" class="notice error" role="alert">{{ rowsError }}</div>
          <div v-else-if="rowsData" class="table-wrap db-table">
            <table>
              <thead>
                <tr>
                  <th v-for="c in rowsData.columns" :key="c.name">
                    <button type="button" class="sort" :aria-label="`Сортировать по ${c.name}`" @click="sortBy(c.name)">
                      {{ c.name }}<span v-if="rowsData.pk.includes(c.name)" class="pk" title="Первичный ключ">🔑</span>
                      <span v-if="orderBy === c.name" aria-hidden="true">{{ desc ? '↓' : '↑' }}</span>
                    </button>
                    <div class="coltype">{{ c.type }}</div>
                  </th>
                  <th class="td-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in rowsData.rows" :key="i">
                  <td v-for="c in rowsData.columns" :key="c.name" :class="{ nullv: row[c.name] === null }" :title="cellTitle(row[c.name])">{{ cellText(row[c.name]) }}</td>
                  <td class="td-actions">
                    <span v-if="rowsData.pk.length" class="row-actions">
                      <button type="button" class="ibtn" data-tip="Изменить" aria-label="Изменить строку" @click="startEdit(row)"><UiIcon name="edit" /></button>
                      <button type="button" class="ibtn danger" data-tip="Удалить" aria-label="Удалить строку" @click="removeRow(row)"><UiIcon name="trash" /></button>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-if="!rowsData.rows.length" class="muted pad">Строк нет.</p>
          </div>
          <div v-if="rowsData && rowsData.total > PAGE" class="pager">
            <button type="button" class="btn ghost" :disabled="offset === 0 || rowsLoading" @click="reloadRows(Math.max(0, offset - PAGE))">← Назад</button>
            <button type="button" class="btn ghost" :disabled="offset + PAGE >= rowsData.total || rowsLoading" @click="reloadRows(offset + PAGE)">Далее →</button>
          </div>
          <p v-if="rowsData && !rowsData.pk.length" class="muted small">У таблицы нет первичного ключа — изменять строки можно через SQL-консоль.</p>
        </template>
      </section>
    </div>

    <!-- ===== Редактирование строки ===== -->
    <dialog ref="editDialog" class="dlg db-edit" aria-labelledby="edit-title" @close="editing = null">
      <form v-if="editing" class="stack-sm" @submit.prevent="saveEdit">
        <h2 id="edit-title">{{ table }} · {{ pkText(editing.pk) }}</h2>
        <div class="edit-fields">
          <label v-for="f in editing.fields" :key="f.name" class="edit-field">
            <span class="row"><span class="mono grow">{{ f.name }}</span><small class="muted">{{ f.type }}</small></span>
            <span v-if="f.locked" class="muted small">{{ f.secret ? 'скрыто — не редактируется' : 'первичный ключ' }}: {{ cellText(f.original) }}</span>
            <template v-else>
              <textarea v-if="f.multiline" v-model="f.value" rows="3" :disabled="f.isNull" class="mono"></textarea>
              <input v-else v-model="f.value" type="text" :disabled="f.isNull" class="mono" />
              <span v-if="f.nullable" class="check small"><input v-model="f.isNull" type="checkbox" :aria-label="`${f.name}: NULL`" /> NULL</span>
            </template>
          </label>
        </div>
        <div v-if="editError" class="notice error" role="alert">{{ editError }}</div>
        <div class="row dlg-actions">
          <button type="button" class="btn ghost" @click="closeEdit">Отмена</button>
          <button type="submit" class="btn primary" :disabled="saving">{{ saving ? 'Сохранение…' : 'Сохранить' }}</button>
        </div>
      </form>
    </dialog>

    <!-- ===== SQL-консоль ===== -->
    <section v-show="mode === 'sql'" class="sql stack">
      <label>
        Запрос
        <textarea v-model="sql" class="editor sql-editor mono" spellcheck="false" placeholder="SELECT * FROM users ORDER BY id DESC" @keydown.ctrl.enter.prevent="runSql" @keydown.meta.enter.prevent="runSql"></textarea>
      </label>
      <div class="row">
        <label class="check"><input v-model="writeMode" type="checkbox" /> Изменяющий запрос (INSERT / UPDATE / DELETE / DDL)</label>
        <span class="grow"></span>
        <button type="button" class="btn" :class="writeMode ? 'danger' : 'primary'" :disabled="sqlLoading || !sql.trim()" @click="runSql">
          {{ sqlLoading ? 'Выполняется…' : writeMode ? 'Выполнить изменение' : 'Выполнить (Ctrl+Enter)' }}
        </button>
      </div>
      <p class="muted small">Чтение выполняется сразу и возвращает до 500 строк. Изменение запускается только после подтверждения, в отдельной транзакции.</p>
      <div v-if="sqlError" class="notice error pre" role="alert">{{ sqlError }}</div>
      <template v-if="sqlResult">
        <div class="notice ok">{{ sqlResult.message }}</div>
        <div v-if="sqlResult.columns.length" class="table-wrap db-table">
          <table>
            <thead><tr><th v-for="c in sqlResult.columns" :key="c">{{ c }}</th></tr></thead>
            <tbody>
              <tr v-for="(row, i) in sqlResult.rows" :key="i">
                <td v-for="c in sqlResult.columns" :key="c" :class="{ nullv: row[c] === null }" :title="cellTitle(row[c])">{{ cellText(row[c]) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>
  </AdminShell>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import AdminShell from './AdminShell.vue'
import { UiIcon } from '../../components/index.js'
import { loadDbRows, loadDbTables, removeDbRow, runDbSql, updateDbRow } from '../../../logic/actions/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'
import { cellText, editText } from './adminFormat.js'

const PAGE = 50
const mode = ref('tables')
const tables = ref([])
const tablesError = ref('')
const tableFilter = ref('')
const table = ref('')
const search = ref('')
const orderBy = ref('')
const desc = ref(true)
const offset = ref(0)
const rowsData = ref(null)
const rowsError = ref('')
const rowsLoading = ref(false)

const visibleTables = computed(() => {
  const q = tableFilter.value.trim().toLowerCase()
  return q ? tables.value.filter((t) => t.name.includes(q)) : tables.value
})
const rangeText = computed(() => {
  const d = rowsData.value
  if (!d) return ''
  if (!d.total) return '0 строк'
  return `${offset.value + 1}–${offset.value + d.rows.length} из ${d.total}`
})

const cellTitle = (v) => (v === null || v === undefined ? 'NULL' : cellText(v, 2000))
const pkText = (pk) => Object.entries(pk).map(([k, v]) => `${k}=${v}`).join(', ')

async function loadTables() {
  tablesError.value = ''
  try {
    tables.value = (await loadDbTables()).tables
  } catch (e) {
    tablesError.value = e.message || 'Не удалось получить список таблиц'
  }
}

function openTable(name) {
  if (table.value !== name) {
    table.value = name
    search.value = ''
    const meta = tables.value.find((t) => t.name === name)
    orderBy.value = meta?.pk?.[0] || ''
    desc.value = true
  }
  reloadRows(0)
}

let seq = 0
async function reloadRows(nextOffset = offset.value) {
  if (!table.value) return
  const my = ++seq
  rowsLoading.value = true
  rowsError.value = ''
  try {
    const data = await loadDbRows(table.value, {
      search: search.value.trim() || undefined,
      order_by: orderBy.value || undefined,
      desc: desc.value,
      limit: PAGE,
      offset: nextOffset,
    })
    if (my !== seq) return
    rowsData.value = data
    offset.value = nextOffset
  } catch (e) {
    if (my === seq) { rowsError.value = e.message || 'Не удалось загрузить строки'; rowsData.value = null }
  } finally {
    if (my === seq) rowsLoading.value = false
  }
}

function sortBy(name) {
  if (orderBy.value === name) desc.value = !desc.value
  else { orderBy.value = name; desc.value = false }
  reloadRows(0)
}

function pkOf(row) {
  return Object.fromEntries(rowsData.value.pk.map((k) => [k, row[k]]))
}

// ----- редактирование строки -----
const editDialog = ref(null)
const editing = ref(null)
const editError = ref('')
const saving = ref(false)

async function startEdit(row) {
  const d = rowsData.value
  editError.value = ''
  editing.value = {
    pk: pkOf(row),
    fields: d.columns.map((c) => {
      const original = row[c.name]
      const secret = d.secret_columns.includes(c.name)
      const text = editText(original)
      return {
        name: c.name,
        type: c.type,
        udt: c.udt,
        nullable: c.nullable,
        original,
        secret,
        locked: secret || d.pk.includes(c.name),
        isNull: original === null,
        value: text,
        initialText: text,
        multiline: typeof original === 'object' && original !== null || text.length > 60 || text.includes('\n'),
      }
    }),
  }
  await nextTick()
  editDialog.value?.showModal()
}

function closeEdit() {
  editDialog.value?.close()
}

function changedValues() {
  const values = {}
  for (const f of editing.value.fields) {
    if (f.locked) continue
    const wasNull = f.original === null
    if (f.isNull) {
      if (!wasNull) values[f.name] = null
      continue
    }
    if (!wasNull && f.value === f.initialText) continue
    let value = f.value
    if (f.udt && f.udt.startsWith('_')) {
      // Массив: в форме — JSON-список.
      try { value = JSON.parse(f.value) } catch { throw new Error(`Столбец ${f.name}: укажите массив в виде JSON, например ["a", "b"]`) }
      if (!Array.isArray(value)) throw new Error(`Столбец ${f.name}: ожидается JSON-массив`)
    }
    values[f.name] = value
  }
  return values
}

async function saveEdit() {
  editError.value = ''
  let values
  try { values = changedValues() } catch (e) { editError.value = e.message; return }
  if (!Object.keys(values).length) { closeEdit(); return }
  saving.value = true
  try {
    await updateDbRow(table.value, editing.value.pk, values)
    toast('Строка сохранена', 'ok')
    closeEdit()
    reloadRows()
  } catch (e) {
    editError.value = e.message || 'Не удалось сохранить'
  } finally {
    saving.value = false
  }
}

async function removeRow(row) {
  const pk = pkOf(row)
  const ok = await askConfirm(`Удалить строку ${table.value} (${pkText(pk)})?`, 'Удаление необратимо. Связанные записи могут быть удалены каскадом.', { okText: 'Удалить', danger: true })
  if (!ok) return
  try {
    await removeDbRow(table.value, pk)
    toast('Строка удалена', 'ok')
    reloadRows()
    loadTables()
  } catch (e) {
    toast(e.message || 'Не удалось удалить', 'error')
  }
}

// ----- SQL-консоль -----
const sql = ref('')
const writeMode = ref(false)
const sqlLoading = ref(false)
const sqlError = ref('')
const sqlResult = ref(null)

async function runSql() {
  if (!sql.value.trim() || sqlLoading.value) return
  sqlError.value = ''
  if (writeMode.value) {
    const ok = await askConfirm('Выполнить изменяющий запрос?', `${sql.value.trim().slice(0, 600)}\n\nЗапрос изменит данные в рабочей базе. Действие записывается в журнал.`, { okText: 'Выполнить', danger: true })
    if (!ok) return
  }
  sqlLoading.value = true
  sqlResult.value = null
  try {
    sqlResult.value = await runDbSql({ sql: sql.value, write: writeMode.value, confirm: writeMode.value })
    if (writeMode.value) { loadTables(); if (table.value) reloadRows() }
  } catch (e) {
    sqlError.value = e.message || 'Запрос не выполнен'
  } finally {
    sqlLoading.value = false
  }
}

onMounted(() => {
  document.title = 'База данных · SHAD'
  loadTables()
})
</script>

<style scoped>
.db-grid { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 16px; align-items: start; }
.db-tables { display: grid; gap: 8px; position: sticky; top: calc(var(--header-h, 64px) + 16px); max-height: calc(100vh - 120px); overflow: auto; }
.db-tables ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 1px; }
.db-tables button { display: flex; width: 100%; gap: 8px; align-items: center; padding: 6px 10px; border: 0; border-radius: 8px; background: none; color: var(--muted); font-size: 13px; text-align: left; cursor: pointer; }
.db-tables button:hover { background: var(--surface); color: var(--text); }
.db-tables button.active { background: var(--surface-2); color: var(--text); }
.db-main { min-width: 0; display: grid; gap: 12px; }
.db-filter { gap: 8px; align-items: center; }
.db-table { overflow: auto; max-height: 70vh; }
.db-table table { font-size: 12.5px; }
.db-table th, .db-table td { padding: 7px 10px; white-space: nowrap; max-width: 320px; overflow: hidden; text-overflow: ellipsis; }
.db-table thead th { position: sticky; top: 0; background: var(--surface); z-index: 1; text-transform: none; letter-spacing: 0; }
.db-table td { font-family: var(--mono); }
.nullv { color: var(--muted); font-style: italic; }
.sort { border: 0; background: none; color: var(--text); font: inherit; font-weight: 600; cursor: pointer; padding: 0; display: inline-flex; gap: 4px; }
.pk { font-size: 10px; }
.coltype { font-size: 10.5px; color: var(--muted); font-weight: 400; }
.pad { padding: 14px; margin: 0; }
.db-edit { width: min(720px, 94vw); }
.edit-fields { display: grid; gap: 12px; max-height: 60vh; overflow: auto; padding-right: 4px; }
.edit-field { display: grid; gap: 4px; }
.sql-editor { min-height: 180px; }
.sql .row { gap: 12px; align-items: center; flex-wrap: wrap; }
@media (max-width: 800px) {
  .db-grid { grid-template-columns: minmax(0, 1fr); }
  .db-tables { position: static; max-height: 220px; }
}
</style>
