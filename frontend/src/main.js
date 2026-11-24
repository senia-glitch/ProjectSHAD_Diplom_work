// Bootstrap: собирает logic/ и ui/. Вне веток. Без бизнес-логики.
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './ui/App.vue'
import { createAppRouter } from './ui/app/index.js'
import { registerAuthProviders } from './logic/actions/index.js'
import { installLogger, logInfo } from './logic/logger/index.js'
import './ui/styles/tokens.css'
import './ui/styles/base.css'
import './ui/styles/icons.css'
import './ui/styles/pp.css'
import './ui/styles/pp-fixes.css'
import './ui/styles/icon-motion.css'

const app = createApp(App)
app.use(createPinia())
const router = createAppRouter()
app.use(router)
router.afterEach((to, from) => {
  logInfo('nav', `→ ${to.name}`, { path: to.path, from: from.path })
})

registerAuthProviders({
  onUnauthorized: () => {
    window.location.href = '/login'
  },
})
installLogger()

// Ошибки Vue-компонентов — в логгер, а не только в консоль.
app.config.errorHandler = (err, _instance, info) => {
  logInfo('error', `Vue Error: ${err?.message || err}`, { info, stack: err?.stack })
}

app.mount('#app')
