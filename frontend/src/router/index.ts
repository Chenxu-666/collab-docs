import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { public: true } },
    { path: '/register', name: 'register', component: () => import('@/views/Register.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/layouts/PublicLayout.vue'),
      children: [
        { path: '', redirect: '/home' },
        { path: 'home', name: 'home', component: () => import('@/views/Home.vue') },
        { path: 'docs', name: 'docs', component: () => import('@/views/Docs.vue') },
        { path: 'docs/:id', name: 'doc-preview', component: () => import('@/views/DocPreview.vue') },
        { path: 'library', name: 'library', component: () => import('@/views/Library.vue') },
        { path: 'pitfalls', name: 'pitfalls', component: () => import('@/views/Pitfalls.vue') }
      ]
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: () => import('@/views/admin/Dashboard.vue') },
        { path: 'docs', name: 'admin-docs', component: () => import('@/views/admin/AdminDocs.vue') },
        { path: 'docs/:id/edit', name: 'editor', component: () => import('@/views/admin/DocEditor.vue') },
        { path: 'library', name: 'admin-library', component: () => import('@/views/admin/AdminLibrary.vue') },
        { path: 'pitfalls', name: 'admin-pitfalls', component: () => import('@/views/admin/AdminPitfalls.vue') },
        { path: 'recycle', name: 'recycle', component: () => import('@/views/admin/Recycle.vue') },
        { path: 'logs', name: 'logs', component: () => import('@/views/admin/Logs.vue') },
        { path: 'stats', name: 'stats', component: () => import('@/views/admin/Stats.vue') },
        { path: 'accounts', name: 'accounts', component: () => import('@/views/admin/Accounts.vue'), meta: { superOnly: true } }
      ]
    },
    { path: '/:pathMatch(.*)*', redirect: '/home' }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('cd_token')
  const user = JSON.parse(localStorage.getItem('cd_user') || 'null')
  if (to.meta.requiresAdmin) {
    if (!token) return { name: 'login', query: { redirect: to.fullPath } }
    if (user?.role !== 'admin' && user?.role !== 'super_admin') return { name: 'home' }
  }
  if (to.meta.superOnly && user?.role !== 'super_admin') return { name: 'dashboard' }
  if (to.name === 'login' && token) return { name: 'home' }
})

export default router
