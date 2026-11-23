<template>
  <div v-if="!slot.dates.length" class="pick-empty">Нажмите + возле «По дате», чтобы добавить даты</div>
  <div v-for="d in slot.dates" :key="d.key" class="nest">
    <div class="add-part">
      <span class="nest-title">Дата:</span>
      <input v-model="d.date" type="date" class="add-part-select" />
      <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать дату" @click="removeFormDate(d.key)">−</button>
    </div>
                    <div class="add-part add-part--sub">
                      <span class="nest-title">Время</span>
                      <button type="button" class="icon-btn icon-btn--xs icon-btn--add" title="Добавить время" @click="addDateTime(d)">+</button>
                    </div>
                    <div v-for="t in d.times" :key="t.key" class="add-part add-part--sub">
      <input v-model="t.start" type="time" class="time-in" />
      <input v-model="t.end" type="time" class="time-in" />
      <button type="button" class="icon-btn icon-btn--xs icon-btn--remove" title="Убрать время" @click="removeDateTime(d, t.key)">−</button>
    </div>
  </div>
</template>

<script setup>
// Редактор режима «по дате» одной формы. Работает вложенными мутациями
// объекта слота (слот — пропса LessonCreator), поэтому эмитов нет:
// добавляются/убираются только вложенные элементы, сам слот не заменяется.
const props = defineProps({
  slot: { type: Object, required: true },
})

let rowSeq = 0

function addDateTime(dateObj) {
  dateObj.times.push({ key: ++rowSeq, start: '', end: '' })
}

function removeDateTime(dateObj, timeKey) {
  dateObj.times = dateObj.times.filter((t) => t.key !== timeKey)
}

function removeFormDate(dateKey) {
  props.slot.dates = props.slot.dates.filter((d) => d.key !== dateKey)
}
</script>
