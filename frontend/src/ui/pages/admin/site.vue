<template>
  <AdminShell title="Гостевая страница" lead="То, что видит человек до входа: блоки по порядку, тексты в Markdown.">
    <template #actions>
      <a class="btn ghost" href="/" target="_blank" rel="noopener">Открыть как гость ↗</a>
      <select v-model="newKind" aria-label="Вид нового блока">
        <option v-for="(meta, kind) in KINDS" :key="kind" :value="kind">{{ meta.label }}</option>
      </select>
      <button type="button" class="btn primary" :disabled="busy" @click="addBlock">Добавить блок</button>
    </template>

    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-else-if="loading" class="skeleton tall" aria-hidden="true"></div>
    <p v-else-if="!blocks.length" class="muted">Блоков нет — гость увидит пустую страницу. Добавьте первый блок.</p>

    <div class="site-editor">
      <section v-for="(b, index) in blocks" :key="b._key" class="panel block-card" :class="{ hidden: !b.visible, open: openKey === b._key }">
        <header class="block-head">
          <button type="button" class="block-toggle" :aria-expanded="openKey === b._key" @click="openKey = openKey === b._key ? null : b._key">
            <span class="pill pill-violet">{{ KINDS[b.kind].label }}</span>
            <strong class="grow">{{ b.title || 'Без заголовка' }}</strong>
            <span v-if="!b.visible" class="pill pill-gray">скрыт</span>
            <span v-if="b._dirty" class="pill pill-amber">не сохранён</span>
          </button>
          <span class="row-actions">
            <button type="button" class="ibtn" aria-label="Выше" data-tip="Выше" :disabled="busy || index === 0 || !b.id" @click="move(index, -1)">↑</button>
            <button type="button" class="ibtn" aria-label="Ниже" data-tip="Ниже" :disabled="busy || index === blocks.length - 1 || !b.id" @click="move(index, 1)">↓</button>
            <button type="button" class="ibtn danger" aria-label="Удалить блок" data-tip="Удалить" :disabled="busy" @click="remove(b, index)"><UiIcon name="trash" /></button>
          </span>
        </header>

        <form v-if="openKey === b._key" class="stack-sm block-form" @submit.prevent="save(b)" @input="b._dirty = true">
          <p class="muted small">{{ KINDS[b.kind].hint }}</p>
          <label>Заголовок <input v-model="b.title" type="text" maxlength="200" /></label>
          <label>Текст (Markdown) <textarea v-model="b.body" rows="4" maxlength="20000"></textarea></label>
          <fieldset v-if="KINDS[b.kind].items" class="items">
            <legend>{{ KINDS[b.kind].items }}</legend>
            <div v-for="(item, i) in b.items" :key="i" class="item">
              <div class="item-head">
                <span class="muted small">№ {{ i + 1 }}</span>
                <button type="button" class="more" @click="b.items.splice(i, 1); b._dirty = true">Убрать</button>
              </div>
              <input v-model="item.title" type="text" maxlength="200" :placeholder="KINDS[b.kind].itemTitle" :aria-label="`${KINDS[b.kind].itemTitle} ${i + 1}`" />
              <textarea v-if="KINDS[b.kind].itemBody" v-model="item.body" rows="2" maxlength="5000" :placeholder="KINDS[b.kind].itemBody" :aria-label="`${KINDS[b.kind].itemBody} ${i + 1}`"></textarea>
            </div>
            <button type="button" class="btn ghost small" :disabled="b.items.length >= 24" @click="b.items.push({ title: '', body: '' }); b._dirty = true">+ Пункт</button>
          </fieldset>
          <label class="check"><input v-model="b.visible" type="checkbox" /> Показывать гостям</label>
          <div class="row">
            <button type="submit" class="btn primary" :disabled="busy">{{ b.id ? 'Сохранить' : 'Создать' }}</button>
            <button type="button" class="btn ghost" :disabled="busy" @click="reset(b, index)">Отменить изменения</button>
          </div>
        </form>
      </section>
    </div>

    <details class="preview" open>
      <summary>Предпросмотр — как увидит гость (только включённые блоки, с несохранёнными правками)</summary>
      <div class="preview-frame">
        <SiteBlocks :blocks="previewBlocks" preview />
      </div>
    </details>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AdminShell from './AdminShell.vue'
import SiteBlocks from '../../blocks/site/SiteBlocks.vue'
import { UiIcon } from '../../components/index.js'
import { loadAdminSiteBlocks, removeSiteBlock, reorderSiteBlocks, saveSiteBlock } from '../../../logic/actions/index.js'
import { askConfirm, toast } from '../../legacy/testing/kit.js'

// Виды блоков: что в них редактируется и как они выглядят у гостя.
const KINDS = {
  hero: { label: 'Первый экран', hint: 'Крупный заголовок, текст и кнопки «Создать аккаунт» / «Войти». Пункты — короткий список преимуществ справа.', items: 'Преимущества', itemTitle: 'Преимущество', itemBody: '' },
  features: { label: 'Возможности', hint: 'Карточки возможностей в сетке.', items: 'Карточки', itemTitle: 'Название', itemBody: 'Описание (Markdown)' },
  steps: { label: 'Шаги', hint: 'Нумерованные шаги «как начать».', items: 'Шаги', itemTitle: 'Шаг', itemBody: 'Пояснение (Markdown)' },
  faq: { label: 'Вопросы', hint: 'Раскрывающиеся вопросы и ответы.', items: 'Вопросы', itemTitle: 'Вопрос', itemBody: 'Ответ (Markdown)' },
  text: { label: 'Текст', hint: 'Заголовок и свободный текст в Markdown.', items: '', itemTitle: '', itemBody: '' },
  cta: { label: 'Призыв', hint: 'Выделенная плашка с кнопкой «Зарегистрироваться».', items: '', itemTitle: '', itemBody: '' },
}

let keySeq = 0
const blocks = ref([])
const saved = new Map()
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const openKey = ref(null)
const newKind = ref('text')

const toEditable = (b) => ({ ...b, items: (b.items || []).map((i) => ({ ...i })), _key: b.id ? `b${b.id}` : `n${++keySeq}`, _dirty: false })
const payload = (b) => ({ kind: b.kind, title: b.title, body: b.body, visible: b.visible, items: b.kind in KINDS && KINDS[b.kind].items ? b.items : [] })
const previewBlocks = computed(() => blocks.value.filter((b) => b.visible).map((b) => ({ ...payload(b), _key: b._key, items: KINDS[b.kind].items ? b.items : [] })))

function remember(list) {
  saved.clear()
  for (const b of list) saved.set(b.id, JSON.parse(JSON.stringify(b)))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const list = await loadAdminSiteBlocks()
    remember(list)
    blocks.value = list.map(toEditable)
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить блоки'
  } finally {
    loading.value = false
  }
}

function addBlock() {
  const b = toEditable({ id: null, kind: newKind.value, title: '', body: '', items: KINDS[newKind.value].items ? [{ title: '', body: '' }] : [], visible: true })
  b._dirty = true
  blocks.value.push(b)
  openKey.value = b._key
}

async function save(b) {
  busy.value = true
  try {
    const result = await saveSiteBlock(b.id, payload(b))
    saved.set(result.id, JSON.parse(JSON.stringify(result)))
    Object.assign(b, toEditable(result), { _key: b._key })
    toast('Блок сохранён', 'ok')
  } catch (e) {
    toast(e.message || 'Не удалось сохранить блок', 'error')
  } finally {
    busy.value = false
  }
}

function reset(b, index) {
  if (!b.id) { blocks.value.splice(index, 1); return }
  Object.assign(b, toEditable(saved.get(b.id)), { _key: b._key })
}

async function remove(b, index) {
  if (b.id && !(await askConfirm('Удалить блок?', `«${b.title || KINDS[b.kind].label}» исчезнет с гостевой страницы.`, { okText: 'Удалить', danger: true }))) return
  if (!b.id) { blocks.value.splice(index, 1); return }
  busy.value = true
  try {
    await removeSiteBlock(b.id)
    blocks.value.splice(index, 1)
    saved.delete(b.id)
    toast('Блок удалён', 'ok')
  } catch (e) {
    toast(e.message || 'Не удалось удалить блок', 'error')
  } finally {
    busy.value = false
  }
}

async function move(index, delta) {
  const list = [...blocks.value]
  const [item] = list.splice(index, 1)
  list.splice(index + delta, 0, item)
  if (list.some((b) => !b.id)) { toast('Сначала сохраните новые блоки', 'error'); return }
  busy.value = true
  try {
    await reorderSiteBlocks(list.map((b) => b.id))
    blocks.value = list
  } catch (e) {
    toast(e.message || 'Не удалось изменить порядок', 'error')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  document.title = 'Гостевая страница · SHAD'
  load()
})
</script>

<style scoped>
.site-editor { display: grid; gap: 10px; margin-bottom: 24px; }
.block-card { padding: 12px 14px; }
.block-card.hidden { opacity: .75; }
.block-card.open { border-color: var(--accent); }
.block-head { display: flex; align-items: center; gap: 10px; }
.block-toggle { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; border: 0; background: none; color: var(--text); font: inherit; text-align: left; cursor: pointer; padding: 4px 0; }
.block-toggle strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.block-form { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line); }
.items { border: 1px dashed var(--line-strong); border-radius: 12px; padding: 10px 12px 12px; display: grid; gap: 10px; }
.items legend { font-size: 13px; color: var(--muted); padding: 0 6px; }
.item { display: grid; gap: 6px; }
.item-head { display: flex; justify-content: space-between; align-items: center; }
.preview summary { cursor: pointer; color: var(--muted); font-size: 14px; margin-bottom: 12px; }
.preview-frame { border: 1px solid var(--line); border-radius: 16px; padding: 28px; background: var(--bg); }
</style>
