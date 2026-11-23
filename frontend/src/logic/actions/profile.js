// Сценарии собственного профиля.
import { getMe, patchMe } from '../api/index.js'
import { useProfileStore } from '../store/index.js'

export async function loadMyProfile() {
  const me = await getMe()
  useProfileStore().setMe(me)
  return me
}

export async function saveMyProfile(patch) {
  const me = await patchMe(patch)
  useProfileStore().setMe(me)
  return me
}
