<template>
  <div class="lesson">
    <button type="button" class="lesson-row" @click="emit('toggle', lesson.lesson_id)">
      <span class="lesson-time">{{ lesson.start }}–{{ lesson.end }}</span>
      <span class="lesson-dur">{{ lesson.minutes }} мин</span>
      <span class="type-chip">{{ lesson.is_group ? 'группа' : 'инд.' }}</span>
      <span class="lesson-who">{{ names }}</span>
      <span class="lesson-sum">{{ formatMoney(lesson.total) }}</span>
      <PaymentStatus :lesson="lesson" />
      <span class="st" :class="stClass">{{ stLabel }}</span>
    </button>
    <div v-if="expanded" class="lesson-detail">
      <div class="detail-pay-head">
        <span>Оплата</span>
      </div>
      <div v-for="s in lesson.students" :key="s.student_id" class="detail-line detail-line--pay">
        <span>{{ s.student_name }} · {{ formatMoney(s.amount) }}<span v-if="s.estimated" title="Цена из текущего тарифа"> ≈</span></span>
        <button
          type="button" class="pay-toggle" :class="s.paid ? 'pay-toggle--on' : ''"
          :title="s.paid ? 'Оплачено — нажать чтобы снять отметку' : 'Не оплачено — нажать чтобы отметить'"
          @click.stop="emit('toggle-pay', { lessonId: lesson.lesson_id, studentUserId: s.student_user_id, paid: !s.paid })"
        >{{ s.paid ? 'Оплачено' : 'Не оплачено' }}</button>
      </div>
      <div v-if="lesson.descriptions" class="detail-notes">{{ lesson.descriptions }}</div>
      <div v-if="lesson.links && lesson.links.length" class="detail-links">
        <a v-for="(x, i) in lesson.links" :key="i" :href="safeUrl(x.url)" target="_blank" rel="noopener">{{ x.alias || x.url }}</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatMoney, safeUrl } from '../../../logic/utils/index.js'
import PaymentStatus from './PaymentStatus.vue'

const props = defineProps({
  lesson: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle', 'toggle-pay'])

const STATUS_META = {
  SCHEDULED: { label: 'запланирован', cls: 'st--plan' },
  ONGOING: { label: 'идёт', cls: 'st--plan' },
  FINISHED: { label: 'проведён', cls: 'st--fact' },
  CANCELLED: { label: 'отменён', cls: 'st--cancel' },
  NO_SHOW: { label: 'неявка', cls: 'st--noshow' },
}

const names = computed(() => {
  const list = (props.lesson.students || []).map((s) => s.student_name)
  if (!list.length) return '—'
  if (list.length === 1) return list[0]
  return `${list[0]} +${list.length - 1}`
})
const stLabel = computed(() => STATUS_META[props.lesson.status]?.label || props.lesson.status)
const stClass = computed(() => STATUS_META[props.lesson.status]?.cls || 'st--fact')
</script>

<style scoped>
.lesson { border-bottom: 1px solid var(--color-gray-100); }
.lesson:last-child { border-bottom: none; }
.lesson-row {
  display: grid; grid-template-columns: 110px 70px 70px 1fr 90px auto auto; gap: 8px;
  align-items: center; width: 100%; padding: 9px 4px;
  background: none; border: none; cursor: pointer; text-align: left;
  font-size: 13px; color: var(--color-gray-800);
}
.lesson-row:hover { background: var(--color-gray-50); }
.lesson-time { font-variant-numeric: tabular-nums; color: var(--color-gray-600); }
.lesson-dur { color: var(--color-gray-600); font-variant-numeric: tabular-nums; }
.type-chip {
  display: inline-block; font-size: 11px; font-weight: 500; padding: 1px 7px;
  border-radius: 10px; background: var(--color-gray-100); color: var(--color-gray-700);
  justify-self: start;
}
.lesson-who { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lesson-sum { font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
.st { display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 10px; justify-self: end; }
.st--fact { background: var(--color-gray-100); color: var(--color-gray-700); }
.st--plan { background: var(--color-accent-50); color: var(--color-accent-dark); }
.st--cancel { background: var(--rule-nobody-bg); color: var(--rule-nobody-text); }
.st--noshow { background: var(--rule-only-bg); color: var(--rule-only-text); }
.lesson-detail { display: flex; flex-direction: column; gap: 6px; padding: 4px 4px 12px 118px; }
.detail-pay-head { display: flex; align-items: center; justify-content: space-between; font-size: 12px; font-weight: 600; color: var(--color-gray-600); }
.detail-line { display: flex; justify-content: space-between; font-size: 13px; color: var(--color-gray-700); font-variant-numeric: tabular-nums; }
.detail-line--pay { align-items: center; }
.pay-toggle {
  border: 1px solid var(--color-gray-300); background: var(--color-white);
  color: var(--color-gray-600); font-size: 11px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px; cursor: pointer; white-space: nowrap;
  transition: background 120ms ease-out, color 120ms ease-out, border-color 120ms ease-out;
}
.pay-toggle:hover { border-color: var(--color-success); color: var(--color-success); }
.pay-toggle--on { background: var(--rule-everyone-bg); border-color: transparent; color: var(--rule-everyone-text); }
.pay-toggle--on:hover { border-color: var(--color-danger); color: var(--color-danger); background: var(--color-white); }
.detail-notes { font-size: 13px; color: var(--color-gray-700); white-space: pre-wrap; }
.detail-links { display: flex; gap: 8px; flex-wrap: wrap; font-size: 13px; }
</style>
