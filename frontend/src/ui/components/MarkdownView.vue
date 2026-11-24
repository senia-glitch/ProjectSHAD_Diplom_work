<template>
  <div ref="box" class="markdown-view"></div>
</template>

<script setup>
// Безопасный Markdown (общий рендерер модуля тестирования): текст экранируется,
// ссылки и медиа — только http(s) по внешним адресам.
import { onMounted, ref, watch } from 'vue'
import { markdownBlock } from '../legacy/testing/kit.js'

const props = defineProps({
  source: { type: String, default: '' },
  clamp: { type: Boolean, default: false },
})
const emit = defineEmits(['cut'])
const box = ref(null)

function render() {
  if (!box.value) return
  const node = markdownBlock(props.source || '', props.clamp ? 'clamp' : '')
  box.value.replaceChildren(node)
  if (props.clamp) {
    requestAnimationFrame(() => {
      const cut = node.scrollHeight > node.clientHeight + 4
      node.classList.toggle('is-cut', cut)
      emit('cut', cut)
    })
  }
}

onMounted(render)
watch(() => [props.source, props.clamp], render)
</script>
