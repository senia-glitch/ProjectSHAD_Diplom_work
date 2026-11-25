<template>
  <div class="site-blocks">
    <template v-for="block in blocks" :key="block.id ?? block._key">
      <!-- Первый экран: заголовок, текст, кнопки и короткий список преимуществ -->
      <section v-if="block.kind === 'hero'" class="sb-hero">
        <div class="sb-hero-copy">
          <p class="sb-eyebrow">SHAD Tutoring</p>
          <h1>{{ block.title }}</h1>
          <MarkdownView v-if="block.body" class="sb-lead" :source="block.body" />
          <div class="sb-actions">
            <component :is="preview ? 'span' : 'router-link'" to="/register" class="btn primary">Создать аккаунт <UiIcon name="arrowRight" /></component>
            <component :is="preview ? 'span' : 'router-link'" to="/login" class="btn ghost">Войти</component>
          </div>
        </div>
        <div v-if="block.items.length" class="sb-hero-note">
          <ul>
            <li v-for="(item, i) in block.items" :key="i">
              <UiIcon name="check" />
              <div><strong v-if="item.title">{{ item.title }}</strong><MarkdownView v-if="item.body" :source="item.body" /></div>
            </li>
          </ul>
        </div>
      </section>

      <section v-else-if="block.kind === 'features' || block.kind === 'steps'" class="sb-section">
        <h2 v-if="block.title">{{ block.title }}</h2>
        <MarkdownView v-if="block.body" class="sb-lead" :source="block.body" />
        <div class="sb-grid" :class="{ 'sb-grid--steps': block.kind === 'steps' }">
          <article v-for="(item, i) in block.items" :key="i" class="sb-card">
            <span v-if="block.kind === 'steps'" class="sb-num">{{ i + 1 }}</span>
            <h3 v-if="item.title">{{ item.title }}</h3>
            <MarkdownView v-if="item.body" :source="item.body" />
          </article>
        </div>
      </section>

      <section v-else-if="block.kind === 'faq'" class="sb-section">
        <h2 v-if="block.title">{{ block.title }}</h2>
        <MarkdownView v-if="block.body" class="sb-lead" :source="block.body" />
        <div class="sb-faq">
          <details v-for="(item, i) in block.items" :key="i">
            <summary>{{ item.title }}</summary>
            <MarkdownView :source="item.body" />
          </details>
        </div>
      </section>

      <section v-else-if="block.kind === 'cta'" class="sb-cta">
        <div>
          <h2 v-if="block.title">{{ block.title }}</h2>
          <MarkdownView v-if="block.body" :source="block.body" />
        </div>
        <component :is="preview ? 'span' : 'router-link'" to="/register" class="btn primary">Зарегистрироваться <UiIcon name="arrowRight" /></component>
      </section>

      <section v-else class="sb-section sb-text">
        <h2 v-if="block.title">{{ block.title }}</h2>
        <MarkdownView v-if="block.body" :source="block.body" />
      </section>
    </template>
  </div>
</template>

<script setup>
// Гостевая страница из блоков владельца. Только показ: блоки — пропсом.
// preview — для редактора: кнопки не ведут никуда.
import { UiIcon } from '../../components/index.js'
import MarkdownView from '../../components/MarkdownView.vue'

defineProps({
  blocks: { type: Array, required: true },
  preview: { type: Boolean, default: false },
})
</script>

<style scoped>
.site-blocks { display: grid; gap: 56px; }
.sb-hero { display: grid; grid-template-columns: 1.2fr 1fr; gap: 56px; align-items: center; padding: 24px 0 8px; }
.sb-eyebrow { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; font-weight: 600; color: var(--accent); margin: 0; }
.sb-hero h1 { font-size: clamp(32px, 4vw, 48px); line-height: 1.15; letter-spacing: -.035em; font-weight: 600; margin: 16px 0 20px; }
.sb-lead { color: var(--muted); font-size: 16px; max-width: 60ch; }
.sb-actions { display: flex; gap: 12px; margin-top: 28px; flex-wrap: wrap; }
.sb-hero-note { padding: 28px; border: 1px solid var(--line); border-radius: 16px; background: var(--surface); }
.sb-hero-note ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 16px; }
.sb-hero-note li { display: flex; gap: 12px; align-items: flex-start; font-size: 14px; }
.sb-hero-note li :deep(.ui-icon) { color: var(--accent); width: 18px; height: 18px; flex: none; margin-top: 2px; }
.sb-section h2, .sb-cta h2 { font-size: 24px; letter-spacing: -.02em; margin: 0 0 12px; }
.sb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 20px; }
.sb-card { padding: 22px; border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--surface); }
.sb-card h3 { font-size: 16px; margin: 0 0 8px; }
.sb-card :deep(p) { color: var(--muted); font-size: 14px; margin: 0; }
.sb-num { display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); font-weight: 600; font-size: 13px; margin-bottom: 12px; }
.sb-faq { display: grid; gap: 8px; margin-top: 16px; }
.sb-faq details { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 0 18px; }
.sb-faq summary { cursor: pointer; padding: 14px 0; font-weight: 500; }
.sb-faq details[open] { padding-bottom: 14px; }
.sb-cta { display: flex; align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap; padding: 28px 32px; border-radius: 16px; background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--line)); }
.sb-cta :deep(p) { margin: 0; color: var(--muted); }
@media (max-width: 800px) {
  .site-blocks { gap: 40px; }
  .sb-hero { grid-template-columns: minmax(0, 1fr); gap: 24px; padding-top: 0; }
  .sb-cta { padding: 22px; }
}
</style>
