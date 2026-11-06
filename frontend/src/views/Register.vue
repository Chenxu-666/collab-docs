<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const userStore = useUserStore()
const ui = useUiStore()

const username = ref('')
const password = ref('')
const confirm = ref('')
const displayName = ref('')
const loading = ref(false)
const done = ref(false)

async function submit() {
  if (!username.value.trim()) { ui.toast('请输入账号', 'error'); return }
  if (password.value.length < 6) { ui.toast('密码至少 6 位', 'error'); return }
  if (password.value !== confirm.value) { ui.toast('两次输入的密码不一致', 'error'); return }
  loading.value = true
  try {
    await userStore.register(username.value.trim(), password.value, displayName.value.trim())
    done.value = true
  } catch (e: any) {
    ui.toast(e.message || '注册失败', 'error')
  } finally { loading.value = false }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <div class="login-card">
      <template v-if="!done">
        <div class="login-logo"><div class="logo">装</div></div>
        <h1>注册账号</h1>
        <p class="sub">注册后需超级管理员审批通过方可使用</p>

        <form @submit.prevent="submit">
          <div class="field">
            <label>账号</label>
            <input v-model="username" class="input" placeholder="3-32 位字母/数字/下划线" autocomplete="username" />
          </div>
          <div class="field">
            <label>昵称</label>
            <input v-model="displayName" class="input" placeholder="展示用昵称（可选）" />
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="password" type="password" class="input" placeholder="至少 6 位" autocomplete="new-password" />
          </div>
          <div class="field">
            <label>确认密码</label>
            <input v-model="confirm" type="password" class="input" placeholder="再次输入密码" autocomplete="new-password" />
          </div>
          <button class="btn btn-primary btn-lg login-btn" type="submit" :disabled="loading">
            {{ loading ? '提交中…' : '提交注册申请' }}
          </button>
        </form>
        <div class="reg-row">已有账号？<router-link to="/login">返回登录</router-link></div>
      </template>

      <template v-else>
        <div style="text-align:center;padding:20px 0">
          <div style="font-size:56px;margin-bottom:16px">✅</div>
          <h1 style="margin-bottom:10px">申请已提交</h1>
          <p style="color:var(--sub);line-height:1.8">你的注册申请已提交，请等待超级管理员审批。<br>审批通过后即可登录查看装修资料。</p>
          <button class="btn btn-primary" style="margin-top:22px;width:100%" @click="router.push('/login')">返回登录</button>
        </div>
      </template>
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
  padding: 40px 40px 34px; box-shadow: var(--shadow-lg);
  animation: scaleIn .4s var(--ease);
}
.login-logo { display: flex; justify-content: center; margin-bottom: 18px; }
.login-logo .logo {
  width: 56px; height: 56px; border-radius: 16px;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 28px; box-shadow: var(--shadow-primary);
}
h1 { text-align: center; font-size: 20px; }
.sub { text-align: center; color: var(--sub); font-size: 13px; margin: 8px 0 24px; }
.login-btn { width: 100%; margin-top: 4px; }
.reg-row { text-align: center; font-size: 13px; color: var(--sub); margin-top: 18px; }
.reg-row a { color: var(--primary); }
</style>
