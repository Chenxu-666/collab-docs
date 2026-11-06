<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const ui = useUiStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function doLogin(u: string, p: string) {
  loading.value = true
  try {
    await userStore.login(u, p)
    ui.toast('登录成功，欢迎回来')
    const redirect = (route.query.redirect as string) || (userStore.isAdmin ? '/admin/dashboard' : '/home')
    router.push(redirect)
  } catch (e: any) {
    ui.toast(e.message || '登录失败', 'error')
  } finally {
    loading.value = false
  }
}
function submit() { doLogin(username.value, password.value) }
</script>

<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <div class="login-card">
      <div class="login-logo"><div class="logo">装</div></div>
      <h1>装修共享网站</h1>
      <p class="sub">把经验沉淀成看得懂的资料</p>

      <form @submit.prevent="submit">
        <div class="field">
          <label>账号</label>
          <input v-model="username" class="input" placeholder="请输入账号" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <button class="btn btn-primary btn-lg login-btn" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>

      <div class="demo-row">
        <button class="demo-btn" @click="doLogin('001', 'WENjing970217')">超级管理员 001</button>
        <button class="demo-btn" @click="doLogin('002', 'WENjing521')">管理员 002</button>
      </div>
      <div class="reg-row">还没有账号？<router-link to="/register">立即注册</router-link>（需管理员审批）</div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
}
.login-bg {
  position: absolute; inset: 0;
  background:
    radial-gradient(900px 500px at 12% -8%, rgba(96,165,250,.28), transparent 60%),
    radial-gradient(800px 500px at 100% 110%, rgba(59,130,246,.22), transparent 60%),
    linear-gradient(160deg, #f2f7ff 0%, #f7fafd 55%, #eef4fd 100%);
}
.login-card {
  position: relative; z-index: 2; width: 400px; max-width: calc(100vw - 32px);
  background: rgba(255,255,255,.86); backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,.9); border-radius: 22px;
  padding: 44px 40px 34px; box-shadow: var(--shadow-lg);
  animation: scaleIn .4s var(--ease);
}
.login-logo { display: flex; justify-content: center; margin-bottom: 18px; }
.login-logo .logo {
  width: 56px; height: 56px; border-radius: 16px;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 28px; box-shadow: var(--shadow-primary);
}
h1 { text-align: center; font-size: 20px; letter-spacing: .5px; }
.sub { text-align: center; color: var(--sub); font-size: 13px; margin: 8px 0 26px; }
.login-btn { width: 100%; margin-top: 4px; }
.demo-row { display: flex; gap: 10px; margin-top: 18px; }
.demo-btn {
  flex: 1; height: 36px; border-radius: 9px; border: 1px solid var(--border-strong);
  background: #fff; color: var(--sub); font-size: 12.5px; cursor: pointer; font-family: inherit;
  transition: all var(--dur) var(--ease);
}
.demo-btn:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-soft); }
.reg-row { text-align: center; font-size: 13px; color: var(--sub); margin-top: 18px; }
.reg-row a { color: var(--primary); }
</style>
