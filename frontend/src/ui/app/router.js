// Маршруты и guard. Guard восстанавливает сессию до проверки доступа (§6.6).
// Из logic/ здесь только store и доступовые действия (§10).
import { createRouter, createWebHistory } from 'vue-router'
import { restoreSession } from '../../logic/actions/index.js'
import { useAuthStore } from '../../logic/store/index.js'

const TestingHost = () => import('../pages/testing/index.vue')

export const routes = [
  { path: '/login', name: 'login', component: () => import('../pages/login/index.vue'), meta: { public: true } },
  { path: '/register', name: 'register', component: () => import('../pages/register/index.vue'), meta: { public: true } },
  { path: '/', name: 'home', component: () => import('../pages/home/index.vue'), meta: { public: true } },
  { path: '/how-it-works', name: 'how-it-works', component: () => import('../pages/how-it-works/index.vue'), meta: { public: true } },
  { path: '/for-tutors', name: 'for-tutors', component: () => import('../pages/for-tutors/index.vue'), meta: { public: true } },
  { path: '/faq', name: 'faq', component: () => import('../pages/faq/index.vue'), meta: { public: true } },
  { path: '/profile', name: 'profile', component: () => import('../pages/profile/index.vue') },
  { path: '/notifications', name: 'notifications', component: () => import('../pages/notifications/index.vue') },
  { path: '/tutors', name: 'tutors', component: () => import('../pages/tutors/index.vue'), meta: { roles: ['student'] } },
  { path: '/student-settings', name: 'student-settings', component: () => import('../pages/student-settings/index.vue'), meta: { roles: ['student'] } },
  { path: '/students', name: 'students', component: () => import('../pages/students/index.vue'), meta: { roles: ['tutor'] } },
  { path: '/schedule', name: 'schedule', component: () => import('../pages/schedule/index.vue') },
  { path: '/upcoming', name: 'upcoming', component: () => import('../pages/upcoming/index.vue'), meta: { roles: ['tutor', 'student'] } },
  { path: '/lessons/:id', name: 'lesson', component: () => import('../pages/lesson/index.vue') },
  { path: '/bookings', name: 'bookings', component: () => import('../pages/bookings/index.vue'), meta: { roles: ['tutor'] } },
  { path: '/payments', name: 'payments', component: () => import('../pages/payments/index.vue'), meta: { roles: ['tutor'] } },
  {
    path: '/statistics',
    component: () => import('../pages/statistics/index.vue'),
    meta: { roles: ['tutor'] },
    children: [
      { path: '', redirect: '/statistics/overview' },
      { path: 'overview', name: 'statistics-overview', component: () => import('../pages/statistics/OverviewTab.vue') },
      { path: 'lessons', name: 'statistics-lessons', component: () => import('../pages/statistics/LessonsTab.vue') },
      { path: 'students', name: 'statistics-students', component: () => import('../pages/statistics/StudentsTab.vue') },
      { path: 'payments', name: 'statistics-payments', component: () => import('../pages/statistics/PaymentsTab.vue') },
    ],
  },
  { path: '/settings', name: 'settings', component: () => import('../pages/settings/index.vue'), meta: { roles: ['tutor'] } },
  // Тестирование: страницы модуля отрисовывает один хост, конкретная — по имени маршрута и роли.
  { path: '/testing', name: 'testing-home', component: TestingHost, meta: { roles: ['tutor', 'student'] } },
  { path: '/testing/new', name: 'testing-new', component: TestingHost, meta: { roles: ['tutor'] } },
  { path: '/testing/:id(\\d+)/edit', name: 'testing-edit', component: TestingHost, meta: { roles: ['tutor'] } },
  { path: '/testing/:id(\\d+)', name: 'testing-test', component: TestingHost, meta: { roles: ['tutor'] } },
  { path: '/testing/take/:id(\\d+)', name: 'testing-take', component: TestingHost, meta: { roles: ['student'] } },
  { path: '/testing/results', name: 'testing-results', component: TestingHost, meta: { roles: ['student'] } },
  { path: '/testing/results/:id(\\d+)', name: 'testing-result', component: TestingHost, meta: { roles: ['tutor', 'student'] } },
  // Доски: список и вход по коду, сама доска — во весь экран.
  { path: '/boards', name: 'boards', component: () => import('../pages/boards/index.vue'), meta: { roles: ['tutor', 'student'] } },
  { path: '/boards/:id([A-Za-z0-9_-]{16,40})', name: 'board', component: () => import('../pages/board/index.vue'), meta: { roles: ['tutor', 'student'] } },
  // Блог репетиторов: чтение открыто всем, управление записями — репетитору.
  { path: '/blog', name: 'blog', component: () => import('../pages/blog/index.vue'), meta: { public: true, optionalAuth: true } },
  { path: '/blog/authors/:authorId(\\d+)', name: 'blog-author', component: () => import('../pages/blog/index.vue'), meta: { public: true, optionalAuth: true } },
  { path: '/blog/posts/:id(\\d+)', name: 'blog-post', component: () => import('../pages/blog/post.vue'), meta: { public: true, optionalAuth: true } },
  { path: '/blog/manage', name: 'blog-manage', component: () => import('../pages/blog/manage.vue'), meta: { roles: ['tutor'] } },
  { path: '/blog/manage/new', name: 'blog-new', component: () => import('../pages/blog/editor.vue'), meta: { roles: ['tutor'] } },
  { path: '/blog/manage/:id(\\d+)', name: 'blog-edit', component: () => import('../pages/blog/editor.vue'), meta: { roles: ['tutor'] } },
  { path: '/admin', name: 'admin', component: () => import('../pages/admin/index.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/system', name: 'admin-system', component: () => import('../pages/admin/system/index.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/logs', name: 'admin-logs', component: () => import('../pages/admin/logs/index.vue'), meta: { roles: ['admin'] } },
]

export function createAppRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes,
  })

  router.beforeEach(async (to, from, next) => {
    const store = useAuthStore()
    if (to.meta.public) {
      // Залогиненных с /login и /register уводим на главную.
      if (to.name === 'login' || to.name === 'register') {
        if (store.isLoggedIn || (await restoreSession())) {
          if (store.user) {
            next({ name: 'home' })
            return
          }
        }
      }
      // Публичные страницы с действиями для вошедших (блог): сессию восстанавливаем, но не требуем.
      if (to.meta.optionalAuth && !store.user) await restoreSession()
      next()
      return
    }
    // §6.6: сессию восстанавливаем ДО проверки доступа.
    if (!store.isLoggedIn || !store.user) {
      if (!(await restoreSession())) {
        next({ name: 'login', query: { redirect: to.fullPath } })
        return
      }
    }
    if (to.meta.roles && !to.meta.roles.includes(store.role)) {
      next({ name: 'home' })
      return
    }
    next()
  })

  return router
}
