// Сценарии страниц репетиторов и учеников: связи и списки.
import {
  listStudentConfigurations,
  getStudentConfiguration,
  createStudentConfigurationByCode,
  deleteStudentConfiguration,
  listTutorConfigurations,
  getTutorConfiguration,
  createTutorConfigurationByCode,
  updateTutorConfiguration as apiUpdateTutorConfiguration,
  resetTutorConfiguration as apiResetTutorConfiguration,
  deleteTutorConfiguration,
  getTutorStudents,
  acceptTutorConfiguration,
  declineTutorConfiguration,
  acceptStudentConfiguration,
  declineStudentConfiguration,
} from '../api/index.js'
import { useRosterStore } from '../store/index.js'
import { nextSeq, isCurrentSeq } from './loading.js'

export async function loadStudentConfigurations() {
  const my = nextSeq('rosterConfigurations')
  const data = await listStudentConfigurations()
  if (!isCurrentSeq('rosterConfigurations', my)) return
  useRosterStore().setConfigurations(data.configurations || [])
}

export async function loadStudentConfiguration(configId) {
  return getStudentConfiguration(configId)
}

export async function addTutorByCode({ personalNumber }) {
  const data = await createStudentConfigurationByCode({ personalNumber })
  await loadStudentConfigurations()
  return data
}

export async function loadStudentTutors() {
  // Репетиторы ученика для селекта записи: user_id, имя и шаг связи.
  // Детали подтягиваются последовательно; битые связи пропускаются,
  // сеть — исключением наверх.
  const my = nextSeq('rosterTutors')
  const data = await listStudentConfigurations()
  const out = []
  // Записываться можно только к репетиторам с действующей связью (не заявкой).
  for (const c of (data.configurations || []).filter((x) => (x.status || 'ACTIVE') === 'ACTIVE')) {
    try {
      const d = await getStudentConfiguration(c.config_id)
      out.push({
        config_id: d.config_id,
        tutor_id: d.tutor_id,
        tutor_user_id: d.tutor_user_id,
        full_name: d.tutor_full_name || d.tutor_username || `Репетитор #${d.tutor_id}`,
        slot_step_minutes: d.slot_step_minutes ?? 60,
        link_visibility_enabled: d.link_visibility_enabled ?? false,
        link_lead_time_minutes: d.link_lead_time_minutes ?? 0,
      })
    } catch (e) {
      if (!e.status) throw e
    }
  }
  if (!isCurrentSeq('rosterTutors', my)) return out
  useRosterStore().setTutors(out)
  return out
}

export async function removeStudentConfiguration(configId) {
  await deleteStudentConfiguration(configId)
  const store = useRosterStore()
  store.setConfigurations(store.configurations.filter((c) => c.config_id !== configId))
}

export async function loadTutorStudents() {
  const my = nextSeq('rosterStudents')
  const data = await getTutorStudents()
  if (!isCurrentSeq('rosterStudents', my)) return
  useRosterStore().setStudents(data.students || [])
}

export async function loadTutorConfigurations() {
  const my = nextSeq('rosterConfigurations')
  const data = await listTutorConfigurations()
  if (!isCurrentSeq('rosterConfigurations', my)) return
  useRosterStore().setConfigurations(data.configurations || [])
}

export async function loadTutorRoster() {
  await Promise.all([loadTutorStudents(), loadTutorConfigurations()])
}

export async function loadTutorConfiguration(configId) {
  return getTutorConfiguration(configId)
}

export async function addStudentByCode({ personalNumber }) {
  const data = await createTutorConfigurationByCode({ personalNumber })
  await Promise.all([loadTutorStudents(), loadTutorConfigurations()])
  return data
}

export async function updateTutorConfiguration(configId, patch) {
  await apiUpdateTutorConfiguration(configId, patch)
  const updated = await getTutorConfiguration(configId)
  const store = useRosterStore()
  store.setConfigurations(
    store.configurations.map((c) => (c.config_id === configId ? { ...c, ...updated } : c)),
  )
  return updated
}

export async function resetTutorConfiguration(configId) {
  await apiResetTutorConfiguration(configId)
  const updated = await getTutorConfiguration(configId)
  const store = useRosterStore()
  store.setConfigurations(
    store.configurations.map((c) => (c.config_id === configId ? { ...c, ...updated } : c)),
  )
  return updated
}

export async function removeTutorConfiguration(configId) {
  await deleteTutorConfiguration(configId)
  const store = useRosterStore()
  store.setConfigurations(store.configurations.filter((c) => c.config_id !== configId))
}

// Ответ на заявку о связи (вторая сторона). Отклонение удаляет заявку.
export async function answerLinkAsTutor(configId, accept) {
  if (accept) await acceptTutorConfiguration(configId)
  else await declineTutorConfiguration(configId)
  await Promise.all([loadTutorStudents(), loadTutorConfigurations()])
}

export async function answerLinkAsStudent(configId, accept) {
  if (accept) await acceptStudentConfiguration(configId)
  else await declineStudentConfiguration(configId)
  await loadStudentConfigurations()
}
