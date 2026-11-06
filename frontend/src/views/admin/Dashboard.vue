<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const stats = ref<any>({})
const activities = ref<any[]>([])

const actionLabel: Record<string, string> = {
  upload: '上传', edit: '编辑', download: '下载', delete: '删除', rollback: '回滚',
  account_op: '账号操作', publish: '发布', withdraw: '撤回', create: '新增',
  register: '注册', account_approve: '审批通过', account_reject: '审批拒绝', trash: '删除'
}
const actionBadge: Record<string, string> = {
  upload: 'badge-blue', edit: 'badge-blue', create: 'badge-green', publish: 'badge-green',
  download: 'badge-gray', delete: 'badge-red', trash: 'badge-red', rollback: 'badge-amber',
  account_op: 'badge-blue', account_approve: 'badge-green', account_reject: 'badge-red', register: 'badge-blue', withdraw: 'badge-amber'
}

onMounted(async () => {
  try {
    const [s, a] = await Promise.all([api.get('/stats/overview'), api.get('/audit-logs')])
    stats.value = s.data
    activities.value = a.data.slice(0, 8)
  } catch { /* ignore */ }
})

function timeOf(t: string) {
  const d = new Date(t), now = new Date(), diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + ' 分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + ' 小时前'
  return d.toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>你好，{{ userStore.user?.display_name }} 👋</h2>
        <div class="desc">装修共享网站 · 管理端工作台</div>
      </div>
    </div>

    <div class="stat-grid">
      <div class="card stat" @click="router.push('/admin/docs')">
        <div class="k"><span class="dot"></span>文档</div>
        <div class="v">{{ stats.document_total || 0 }}</div>
        <div class="t">已发布 {{ stats.document_published || 0 }} · 草稿 {{ stats.document_draft || 0 }}</div>
        <span class="go">管理文档 →</span>
      </div>
      <div class="card stat" @click="router.push('/admin/library')">
        <div class="k"><span class="dot" style="background:#10b981;box-shadow:0 0 0 4px #ecfdf5"></span>图片</div>
        <div class="v">{{ stats.image_total || 0 }}</div>
        <div class="t">已发布 {{ stats.image_published || 0 }} · {{ stats.album_count || 0 }} 个相册</div>
        <span class="go">管理图片 →</span>
      </div>
      <div class="card stat" @click="router.push('/admin/pitfalls')">
        <div class="k"><span class="dot" style="background:#f59e0b;box-shadow:0 0 0 4px #fffbeb"></span>避坑项</div>
        <div class="v">{{ stats.pitfall_total || 0 }}</div>
        <div class="t">已发布 {{ stats.pitfall_published || 0 }}</div>
        <span class="go">管理避坑 →</span>
      </div>
      <div class="card stat" @click="router.push('/admin/recycle')">
        <div class="k"><span class="dot" style="background:#ef4444;box-shadow:0 0 0 4px #fef2f2"></span>回收站</div>
        <div class="v">{{ stats.trash_count || 0 }}</div>
        <div class="t">本周编辑 {{ stats.week_edit || 0 }} 次</div>
        <span class="go">查看回收站 →</span>
      </div>
      <div v-if="userStore.isSuperAdmin" class="card stat" @click="router.push('/admin/accounts')">
        <div class="k"><span class="dot" style="background:#8b5cf6;box-shadow:0 0 0 4px #f5f3ff"></span>待审批</div>
        <div class="v">{{ stats.pending_count || 0 }}</div>
        <div class="t">注册申请待处理</div>
        <span class="go">去审批 →</span>
      </div>
    </div>

    <div class="card">
      <div style="padding:16px 20px;border-bottom:1px solid var(--border);font-weight:600">最近动态</div>
      <table class="tbl">
        <tbody>
          <tr v-for="a in activities" :key="a.id">
            <td style="width:110px"><span class="badge" :class="actionBadge[a.action] || 'badge-gray'">{{ actionLabel[a.action] || a.action }}</span></td>
            <td>{{ a.object_name || '—' }}</td>
            <td class="hide-m" style="width:140px;color:var(--sub)">{{ a.username }}</td>
            <td style="width:110px;text-align:right;color:var(--muted)">{{ timeOf(a.created_at) }}</td>
          </tr>
          <tr v-if="!activities.length"><td colspan="4"><div class="empty"><div class="big">📋</div>暂无动态</div></td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
