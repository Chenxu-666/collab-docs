<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const users = ref<any[]>([])
const pending = ref<any[]>([])
const tab = ref<'users' | 'pending'>('pending')

const showBatch = ref(false)
const batchText = ref('')
const creating = ref(false)

const showAdmin = ref(false)
const adminForm = ref({ username: '', password: '', display_name: '' })

async function load() {
  try {
    const [u, p] = await Promise.all([api.get('/accounts'), api.get('/accounts/pending')])
    users.value = u.data
    pending.value = p.data
  } catch (e: any) { ui.toast(e.message, 'error') }
}

async function approve(u: any) {
  try { await api.post(`/accounts/${u.id}/approve`); ui.toast(`已通过「${u.username}」的注册申请`); await load() }
  catch (e: any) { ui.toast(e.message, 'error') }
}
async function reject(u: any) {
  const reason = prompt('拒绝原因（可选）：') || ''
  try { await api.post(`/accounts/${u.id}/reject`, { reason }); ui.toast('已拒绝'); await load() }
  catch (e: any) { ui.toast(e.message, 'error') }
}

async function toggleStatus(u: any) {
  try {
    await api.patch(`/accounts/${u.id}`, { status: u.status === 'active' ? 'disabled' : 'active' })
    ui.toast(u.status === 'active' ? '已停用' : '已启用')
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}
async function resetPwd(u: any) {
  try { await api.patch(`/accounts/${u.id}`, { reset_password: true }); ui.toast(`已重置，初始密码为 ${u.username}@123`) }
  catch (e: any) { ui.toast(e.message, 'error') }
}

async function doBatch() {
  const items = batchText.value.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
    const [username, display_name] = l.split(/[,，]/).map((s) => s.trim())
    return { username, display_name: display_name || username }
  })
  if (!items.length) { ui.toast('请输入账号清单', 'error'); return }
  creating.value = true
  try {
    const { data } = await api.post('/accounts/batch', { items })
    const list = (data.created || []).map((c: any) => `${c.username} / ${c.initial_password}`).join('\n')
    ui.toast(`创建成功 ${data.created.length} 个账号`)
    showBatch.value = false; batchText.value = ''
    if (data.created.length) alert('账号初始密码清单：\n\n' + list)
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') } finally { creating.value = false }
}

async function createAdmin() {
  if (!adminForm.value.username || adminForm.value.password.length < 6) { ui.toast('请填写账号且密码至少 6 位', 'error'); return }
  try {
    await api.post('/accounts/admin', adminForm.value)
    ui.toast('内容管理员账号创建成功')
    showAdmin.value = false
    adminForm.value = { username: '', password: '', display_name: '' }
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}

const roleLabel: Record<string, string> = { super_admin: '超级管理员', admin: '内容管理员', user: '普通用户' }
const roleClass: Record<string, string> = { super_admin: 'badge-blue', admin: 'badge-blue', user: 'badge-gray' }
const statusLabel: Record<string, string> = { active: '正常', pending: '待审批', disabled: '已停用', rejected: '已拒绝' }
const statusClass: Record<string, string> = { active: 'badge-green', pending: 'badge-amber', disabled: 'badge-red', rejected: 'badge-red' }

onMounted(load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>账号管理</h2>
        <div class="desc">注册审批 · 账号创建 · 停用 / 重置（仅超级管理员）</div>
      </div>
      <div class="toolbar">
        <button class="btn btn-ghost" @click="showAdmin = true">＋ 新建管理员</button>
        <button class="btn btn-primary" @click="showBatch = true">＋ 批量创建用户</button>
      </div>
    </div>

    <div class="album-tabs">
      <button class="album-tab" :class="{ active: tab === 'pending' }" @click="tab = 'pending'">
        待审批 <span v-if="pending.length" class="cnt">{{ pending.length }}</span>
      </button>
      <button class="album-tab" :class="{ active: tab === 'users' }" @click="tab = 'users'">全部账号</button>
    </div>

    <!-- 待审批 -->
    <div v-if="tab === 'pending'" class="card">
      <div class="tbl-wrap">
        <table class="tbl">
          <thead><tr><th>账号</th><th>昵称</th><th class="hide-m">申请时间</th><th style="width:220px">操作</th></tr></thead>
          <tbody>
            <tr v-for="u in pending" :key="u.id">
              <td><b>{{ u.username }}</b></td>
              <td>{{ u.display_name }}</td>
              <td class="hide-m" style="color:var(--sub)">{{ new Date(u.created_at).toLocaleString('zh-CN', { hour12: false }) }}</td>
              <td><div class="ops">
                <button class="btn btn-primary btn-sm" @click="approve(u)">通过</button>
                <button class="btn btn-danger btn-sm" @click="reject(u)">拒绝</button>
              </div></td>
            </tr>
            <tr v-if="!pending.length"><td colspan="4"><div class="empty"><div class="big">✅</div>暂无待审批的注册申请</div></td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 全部账号 -->
    <div v-else class="card">
      <div class="tbl-wrap">
        <table class="tbl">
          <thead><tr><th>账号</th><th>昵称</th><th>角色</th><th>状态</th><th class="hide-m">创建时间</th><th style="width:220px">操作</th></tr></thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td><b>{{ u.username }}</b></td>
              <td>{{ u.display_name }}</td>
              <td><span class="badge" :class="roleClass[u.role]">{{ roleLabel[u.role] }}</span></td>
              <td><span class="badge" :class="statusClass[u.status]">{{ statusLabel[u.status] }}</span></td>
              <td class="hide-m" style="color:var(--sub)">{{ new Date(u.created_at).toLocaleDateString('zh-CN') }}</td>
              <td>
                <div class="ops" v-if="u.role !== 'super_admin'">
                  <button class="btn btn-ghost btn-sm" @click="resetPwd(u)">重置密码</button>
                  <button class="btn btn-danger btn-sm" @click="toggleStatus(u)">{{ u.status === 'active' ? '停用' : '启用' }}</button>
                </div>
                <span v-else style="color:var(--muted);font-size:12px">系统账号</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 批量创建 -->
    <div v-if="showBatch" class="modal-mask" @click.self="showBatch = false">
      <div class="modal">
        <div class="modal-head"><b>批量创建普通用户</b><button class="icon-btn" @click="showBatch = false">✕</button></div>
        <div class="modal-body">
          <div class="field"><label>账号清单（每行：账号,昵称）</label>
            <textarea v-model="batchText" class="textarea" placeholder="zhangsan,张三&#10;lisi,李四"></textarea>
          </div>
          <div style="font-size:12.5px;color:var(--sub);line-height:1.9">· 初始密码为「账号@123」，首次登录可修改 · 角色为普通用户（只读）</div>
        </div>
        <div class="modal-foot"><button class="btn btn-ghost" @click="showBatch = false">取消</button><button class="btn btn-primary" :disabled="creating" @click="doBatch">{{ creating ? '创建中…' : '批量创建' }}</button></div>
      </div>
    </div>

    <!-- 新建管理员 -->
    <div v-if="showAdmin" class="modal-mask" @click.self="showAdmin = false">
      <div class="modal">
        <div class="modal-head"><b>新建内容管理员</b><button class="icon-btn" @click="showAdmin = false">✕</button></div>
        <div class="modal-body">
          <div class="field"><label>账号</label><input v-model="adminForm.username" class="input" /></div>
          <div class="field"><label>昵称</label><input v-model="adminForm.display_name" class="input" /></div>
          <div class="field"><label>密码（至少 6 位）</label><input v-model="adminForm.password" type="password" class="input" /></div>
        </div>
        <div class="modal-foot"><button class="btn btn-ghost" @click="showAdmin = false">取消</button><button class="btn btn-primary" @click="createAdmin">创建</button></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cnt { background: var(--danger); color: #fff; border-radius: 999px; font-size: 11px; padding: 1px 7px; margin-left: 5px; }
</style>
