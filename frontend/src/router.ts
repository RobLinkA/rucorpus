import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from '@/stores/session'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (to, _from, saved) => saved ?? (to.hash ? { el: to.hash, top: 96 } : { top: 0 }),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/search', name: 'search', component: () => import('@/views/SearchView.vue') },
    { path: '/advanced', redirect: (to) => ({ name: 'search', query: to.query }) },
    { path: '/read/:workId?', name: 'read', component: () => import('@/views/ReadView.vue') },
    { path: '/g/:id', name: 'group', component: () => import('@/views/GroupView.vue') },
    { path: '/help', name: 'help', component: () => import('@/views/HelpView.vue') },
    { path: '/citation', name: 'citation', component: () => import('@/views/CitationView.vue') },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/me/favorites', name: 'favorites', component: () => import('@/views/FavoritesView.vue'), meta: { auth: true } },
    { path: '/me/history', name: 'history', component: () => import('@/views/HistoryView.vue'), meta: { auth: true } },
    { path: '/me', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { auth: true } },
    {
      path: '/admin',
      component: () => import('@/views/admin/AdminLayout.vue'),
      meta: { editor: true },
      children: [
        { path: '', name: 'admin', component: () => import('@/views/admin/DashboardView.vue') },
        { path: 'corpora', name: 'admin-corpora', component: () => import('@/views/admin/CorporaView.vue'), meta: { admin: true } },
        { path: 'corpora/:id', name: 'admin-corpus', component: () => import('@/views/admin/CorpusEditView.vue'), meta: { admin: true } },
        { path: 'segments', name: 'admin-segments', component: () => import('@/views/admin/SegmentsView.vue') },
        { path: 'transfer', name: 'admin-transfer', component: () => import('@/views/admin/TransferView.vue') },
        { path: 'users', name: 'admin-users', component: () => import('@/views/admin/UsersView.vue'), meta: { admin: true } },
        { path: 'audit', name: 'admin-audit', component: () => import('@/views/admin/AuditView.vue'), meta: { admin: true } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('@/views/NotFoundView.vue') },
  ],
})

router.beforeEach(async (to) => {
  const session = useSession()
  await session.load()
  const needs = to.matched.some((r) => r.meta.auth || r.meta.editor || r.meta.admin)
  if (needs && !session.loggedIn) return { name: 'login', query: { next: to.fullPath } }
  if (to.matched.some((r) => r.meta.editor) && !session.canEdit) return { name: 'home' }
  if (to.matched.some((r) => r.meta.admin) && !session.isAdmin) return { name: 'admin' }
})

export default router
