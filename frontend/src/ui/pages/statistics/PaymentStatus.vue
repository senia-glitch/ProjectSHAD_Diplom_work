<template>
  <span v-if="pay.key === 'paid'" class="pay pay--paid" :title="`Оплачено: ${formatMoney(pay.amount)}`">
    Оплачено
  </span>
  <span v-else-if="pay.key === 'partial'" class="pay pay--partial" :title="`Оплачено ${pay.paidCount} из ${pay.totalCount}`">
    Частично
  </span>
  <span v-else-if="pay.key === 'unpaid'" class="pay pay--unpaid" title="Репетитор ещё не отметил оплату">Не оплачено</span>
  <span v-else-if="pay.key === 'pending'" class="pay pay--pending" title="Урок ещё не прошёл">Ожидает</span>
  <span v-else class="pay pay--none">—</span>
</template>

<script setup>
import { computed } from 'vue'
import { formatMoney, lessonPayment } from '../../../logic/utils/index.js'

const props = defineProps({
  lesson: { type: Object, required: true },
})

const pay = computed(() => lessonPayment(props.lesson))
</script>

<style scoped>
.pay { display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 10px; white-space: nowrap; }
.pay--paid { background: var(--rule-everyone-bg); color: var(--rule-everyone-text); }
.pay--partial { background: var(--rule-only-bg); color: var(--rule-only-text); }
.pay--unpaid { background: var(--color-gray-100); color: var(--color-gray-600); }
.pay--pending { background: var(--color-gray-100); color: var(--color-gray-600); }
.pay--none { color: var(--color-gray-400); }
</style>
