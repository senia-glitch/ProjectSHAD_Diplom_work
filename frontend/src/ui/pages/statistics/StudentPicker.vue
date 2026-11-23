<template>
  <div class="students-pop">
    <div class="pop-head">
      <span class="pop-title">Ученики</span>
      <button type="button" class="btn btn--sm btn--gry" @click="emit('all')">Все</button>
    </div>
    <div class="pick-list">
      <label v-for="s in students" :key="s.student_id" class="pick">
        <input
          type="checkbox" :checked="selected.includes(s.student_id)"
          @change="emit('toggle', s.student_id)"
        />
        {{ s.full_name }}
      </label>
      <span v-if="!students.length" class="pick-empty">Нет учеников</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  students: { type: Array, default: () => [] },
  selected: { type: Array, default: () => [] },
})
const emit = defineEmits(['toggle', 'all'])
</script>

<style scoped>
.students-pop {
  position: absolute; top: calc(100% + 8px); left: 0; z-index: 120;
  background: var(--color-white); border: 1px solid var(--color-gray-200);
  border-radius: 12px; box-shadow: var(--shadow-md); padding: 12px;
  width: 260px; animation: pop-in 150ms ease-out;
}
.pop-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.pop-title { font-size: 13px; font-weight: 600; color: var(--color-gray-800); }
.pick-list { display: flex; flex-direction: column; gap: 2px; max-height: 240px; overflow-y: auto; }
.pick {
  display: flex; align-items: center; gap: 8px; font-size: 13px;
  color: var(--color-gray-800); cursor: pointer; padding: 6px 8px; border-radius: 8px;
  transition: background 120ms ease-out;
}
.pick:hover { background: var(--color-gray-100); }
.pick input { width: auto; }
@keyframes pop-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to { opacity: 1; transform: none; }
}
</style>
