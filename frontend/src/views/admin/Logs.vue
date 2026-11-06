<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const logs = ref<any[]>([])
const q = ref('')
const action = ref('')
const objectType = ref('')

const actionLabel: Record<string, string> = {
  upload: '上传', edit: '编辑', download: '下载', delete: '删除', trash: '删除', rollback: '回滚',
  account_op: '账号操作', publish: '发布', withdraw: '撤回', create: '新增', register: '注册',
  account_approve: '审批通过', account_reject: '审批拒绝', permanent_delete: '彻底删除',
  login: '登录', login_failed: '登录失败', archive: '归档', restore: '恢复'
}

async function load() {
  try {
    const { data } = await api.get('/audit-logs', { params: { q: q.value, action: action.value, object_type: objectType.value } })
    logs.value = data
  } catch (e: any) { ui.toast(e.message, 'error') }
}
function timeOf(t: string) { return new Date(t).toLocaleString('zh-CN', { hour12: false }) }

onMounted(load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>操作审计日志</h2>
        <div class="desc">不可删除 · 全量留痕 · 可追溯</div>
      </div>
    </div>

    <div class="card">
      <div class="toolbar" style="padding:14px 18px;border-bottom:1px solid var(--border)">
        <input v-model="q" class="input" style="max-width:220px" placeholder="搜索操作人 / 对象…" @input="load" />
        <select v-model="action" class="select" style="max-width:150px" @change="load">
          <option value="">全部操作</option>
          <option v-for="(label, key) in actionLabel" :key="key" :value="key">{{ label }}</option>
        </select>
        <select v-model="objectType" class="select" style="max-width:150px" @change="load">
          <option value="">全部对象</option>
          <option value="document">文档</option>
          <option value="image">图片</option>
          <option value="pitfall">避坑项</option>
          <option value="account">账号</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table class="tbl">
          <thead><tr><th>时间</th><th>操作人</th><th>操作</th><th>对象</th><th class="hide-m">IP</th></tr></thead>
          <tbody>
            <tr v-for="l in logs" :key="l.id">
              <td style="color:var(--sub);white-space:nowrap">{{ timeOf(l.created_at) }}</td>
              <td><b>{{ l.username }}</b></td>
              <td><span class="badge badge-gray">{{ actionLabel[l.action] || l.action }}</span></td>
              <td>{{ l.object_name || '—' }}</td>
              <td class="hide-m" style="color:var(--muted)">{{ l.ip }}</td>
            </tr>
            <tr v-if="!logs.length"><td colspan="5"><div class="empty"><div class="big">📋</div>暂无日志</div></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
