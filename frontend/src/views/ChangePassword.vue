<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useUserStore } from '@/stores/user'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const userStore = useUserStore()
const ui = useUiStore()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)

async function submit() {
  if (newPassword.value.length < 6) { ui.toast('新密码长度至少 6 位', 'error'); return }
  if (newPassword.value !== confirmPassword.value) { ui.toast('两次输入的新密码不一致', 'error'); return }
  loading.value = true
  try {
    await api.post('/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value
    })
    userStore.$patch({ user: { ...(userStore.user || {}), must_change_pwd: false } })
    localStorage.setItem('cd_user', JSON.stringify(userStore.user))
    ui.toast('密码已修改')
    router.push(userStore.isAdmin ? '/admin/dashboard' : '/home')
  } catch (e: any) {
    ui.toast(e.message || '修改失败', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <div class="login-card">
      <div class="login-logo"><div class="logo">装</div></div>
      <h1>修改初始密码</h1>
      <p class="sub">首次登录或密码重置后，请先设置新密码再继续</p>

      <form @submit.prevent="submit">
        <div class="field">
          <label>原密码</label>
          <input v-model="oldPassword" type="password" class="input" autocomplete="current-password" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="newPassword" type="password" class="input" autocomplete="new-password" />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input v-model="confirmPassword" type="password" class="input" autocomplete="new-password" />
        </div>
        <button class="btn btn-primary btn-lg login-btn" type="submit" :disabled="loading">
          {{ loading ? '提交中…' : '确认修改' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.login-bg { position: absolute; inset: 0; background: radial-gradient(900px 500px at 12% -8%, rgba(96,165,250,.28), transparent 60%), radial-gradient(800px 500px at 100% 110%, rgba(59,130,246,.22), transparent 60%), linear-gradient(160deg, #f2f7ff 0%, #f7fafd 55%, #eef4fd 100%); }
.login-card { position: relative; z-index: 2; width: 400px; max-width: calc(100vw - 32px); background: rgba(255,255,255,.86); backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,.9); border-radius: 22px; padding: 44px 40px 34px; box-shadow: var(--shadow-lg); }
.login-logo { display: flex; justify-content: center; margin-bottom: 18px; }
.login-logo .logo { width: 56px; height: 56px; border-radius: 16px; background: linear-gradient(135deg, #60a5fa, #3b82f6); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 28px; }
h1 { text-align: center; font-size: 20px; }
.sub { text-align: center; color: var(--sub); font-size: 13px; margin: 8px 0 24px; }
.field { margin-bottom: 14px; }
.field label { display: block; font-size: 13px; color: var(--sub); margin-bottom: 6px; }
.login-btn { width: 100%; margin-top: 6px; }
</style>
