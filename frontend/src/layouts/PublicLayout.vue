<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const menuOpen = ref(false)

const navs = [
  { key: 'home', label: '首页' },
  { key: 'docs', label: '文档' },
  { key: 'library', label: '图片库' },
  { key: 'pitfalls', label: '避坑清单' }
]

const active = computed(() => route.name as string)

function go(key: string) {
  menuOpen.value = false
  router.push('/' + key)
}
</script>

<template>
  <div class="pub-layout">
    <header class="pub-header">
      <div class="pub-inner">
        <div class="brand" @click="router.push('/home')">
          <div class="logo">装</div>
          <div class="brand-txt">
            <b>装修共享网站</b>
            <span>把经验沉淀成看得懂的资料</span>
          </div>
        </div>
        <nav class="pub-nav" :class="{ open: menuOpen }">
          <a v-for="n in navs" :key="n.key" class="nav-link"
             :class="{ active: active === n.key }" @click="go(n.key)">{{ n.label }}</a>
        </nav>
        <div class="pub-actions">
          <template v-if="userStore.isLoggedIn">
            <span class="who">你好，{{ userStore.user?.display_name }}</span>
            <button v-if="userStore.isAdmin" class="btn btn-primary btn-sm" @click="router.push('/admin/dashboard')">进入管理端</button>
            <button class="btn btn-ghost btn-sm" @click="userStore.logout(); router.push('/home')">退出</button>
          </template>
          <template v-else>
            <button class="btn btn-ghost btn-sm" @click="router.push('/login')">登录</button>
            <button class="btn btn-primary btn-sm" @click="router.push('/register')">注册</button>
          </template>
          <button class="hamburger pub-ham" @click="menuOpen = !menuOpen">☰</button>
        </div>
      </div>
    </header>

    <main class="pub-main">
      <router-view />
    </main>

    <footer class="pub-footer">
      装修共享网站 · 文档 / 图片 / 避坑经验 集中共享
    </footer>
  </div>
</template>

<style scoped>
.pub-layout { min-height: 100vh; display: flex; flex-direction: column; }
.pub-header {
  position: sticky; top: 0; z-index: 50; background: rgba(255,255,255,.9);
  backdrop-filter: blur(10px); border-bottom: 1px solid var(--border);
}
.pub-inner { max-width: 1240px; margin: 0 auto; padding: 0 24px; height: 66px; display: flex; align-items: center; gap: 20px; }
.brand { display: flex; align-items: center; gap: 11px; cursor: pointer; flex: none; }
.brand .logo {
  width: 40px; height: 40px; border-radius: 12px; flex: none;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  color: #fff; display: flex; align-items: center; justify-content: center; font-size: 20px;
  box-shadow: var(--shadow-primary);
}
.brand-txt b { display: block; font-size: 16px; }
.brand-txt span { font-size: 11.5px; color: var(--sub); }
.pub-nav { display: flex; gap: 6px; flex: 1; }
.nav-link {
  padding: 8px 16px; border-radius: 10px; color: var(--text-2); font-size: 14.5px;
  cursor: pointer; transition: all var(--dur) var(--ease);
}
.nav-link:hover { background: var(--primary-soft); color: var(--primary); }
.nav-link.active { background: var(--primary-soft); color: var(--primary); font-weight: 600; }
.pub-actions { display: flex; align-items: center; gap: 10px; flex: none; }
.who { font-size: 13px; color: var(--sub); }
.pub-ham { display: none; }
.pub-main { flex: 1; width: 100%; max-width: 1240px; margin: 0 auto; padding: 28px 24px; }
.pub-footer { text-align: center; padding: 26px; color: var(--muted); font-size: 13px; border-top: 1px solid var(--border); }
@media (max-width: 768px) {
  .pub-inner { height: 58px; padding: 0 14px; }
  .pub-nav {
    position: absolute; top: 58px; left: 0; right: 0; background: #fff;
    flex-direction: column; padding: 10px 14px; border-bottom: 1px solid var(--border);
    display: none; box-shadow: var(--shadow-md);
  }
  .pub-nav.open { display: flex; }
  .pub-ham { display: inline-flex; }
  .who { display: none; }
  .brand-txt span { display: none; }
  .pub-main { padding: 20px 14px; }
}
</style>
