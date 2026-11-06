<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const ui = useUiStore()
const sideOpen = ref(false)

const navItems = computed(() => {
  const items = [
    { key: 'dashboard', ico: '⌂', label: '工作台', to: '/admin/dashboard' },
    { key: 'admin-docs', ico: '▤', label: '文档管理', to: '/admin/docs' },
    { key: 'admin-library', ico: '▦', label: '图片库', to: '/admin/library' },
    { key: 'admin-pitfalls', ico: '⚠', label: '避坑项', to: '/admin/pitfalls' },
    { key: 'recycle', ico: '🗑', label: '回收站', to: '/admin/recycle' },
    { key: 'stats', ico: '📊', label: '统计看板', to: '/admin/stats' },
    { key: 'logs', ico: '📋', label: '审计日志', to: '/admin/logs' }
  ]
  if (userStore.isSuperAdmin) {
    items.push({ key: 'accounts', ico: '👥', label: '账号管理', to: '/admin/accounts' })
  }
  return items
})

const crumbMap: Record<string, string> = {
  dashboard: '工作台', 'admin-docs': '文档管理', 'admin-library': '图片库',
  'admin-pitfalls': '避坑项', recycle: '回收站', stats: '统计看板',
  logs: '审计日志', accounts: '账号管理', editor: '在线协同编辑'
}
const crumb = computed(() => crumbMap[route.name as string] || '')

const avatarText = computed(() => (userStore.isSuperAdmin ? '超' : '管'))
const roleLabel = computed(() => (userStore.isSuperAdmin ? '超级管理员' : '内容管理员'))

function go(to: string) {
  sideOpen.value = false
  router.push(to)
}
function toggleSide() { sideOpen.value = !sideOpen.value }
function logout() {
  userStore.logout()
  router.push('/login')
}
function switchToUser() {
  userStore.switchToUserView()
  ui.toast('已切换到用户视角（预览模式）', 'info')
  router.push('/home')
}
function backToAdmin() {
  userStore.backToAdmin()
  ui.toast('已返回管理端', 'info')
  router.push('/admin/dashboard')
}
</script>

<template>
  <div class="layout">
    <transition name="fade"><div v-if="sideOpen" class="mask" @click="toggleSide"></div></transition>
    <aside class="sidebar" :class="{ open: sideOpen }">
      <div class="brand">
        <div class="logo">装</div>
        <b>装修共享·管理端</b>
      </div>
      <nav class="nav">
        <div v-for="n in navItems" :key="n.key" class="nav-item"
             :class="{ active: route.name === n.key }" @click="go(n.to)">
          <span class="ico">{{ n.ico }}</span>{{ n.label }}
          <span v-if="n.key === 'accounts'" class="pending-dot"></span>
        </div>
      </nav>
      <div class="side-foot">
        <div class="user-chip">
          <div class="avatar">{{ avatarText }}</div>
          <div class="meta"><b>{{ userStore.user?.display_name }}</b><span>{{ roleLabel }}</span></div>
          <button class="icon-btn" title="退出登录" @click="logout">⏻</button>
        </div>
      </div>
    </aside>

    <div class="main">
      <div class="topbar">
        <button class="hamburger" @click="toggleSide">☰</button>
        <span class="crumb">{{ crumb }}</span>
        <div v-if="userStore.isUserView" class="view-banner">
          👁 当前为用户视角预览 <button @click="backToAdmin">返回管理端</button>
        </div>
        <template v-else>
          <button class="switch-btn" @click="router.push('/home')">⇱ 查看公开首页</button>
          <button class="switch-btn" @click="switchToUser">⇄ 用户视角</button>
        </template>
      </div>
      <div class="content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.pending-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--danger);
  margin-left: auto;
}
</style>
