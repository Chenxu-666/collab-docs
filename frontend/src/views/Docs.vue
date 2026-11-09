<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { publicApi } from '@/api'

const route = useRoute()
const router = useRouter()
const docs = ref<any[]>([])
const folders = ref<any[]>([])
const q = ref((route.query.q as string) || '')
const folderId = ref<number | null>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const { data } = await publicApi.get('/documents', { params: { q: q.value, folder_id: folderId.value || undefined } })
    docs.value = data
  } catch { /* ignore */ } finally { loading.value = false }
}

onMounted(async () => {
  await load()
  try {
    const { data } = await publicApi.get('/documents/folders')
    folders.value = data
  } catch { /* ignore */ }
})

function fmtSize(n: number) {
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(0) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}
function timeOf(t: string) { return new Date(t).toLocaleDateString('zh-CN') }

watch(folderId, load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>文档</h2>
        <div class="desc">已发布的装修资料文档，点击查看</div>
      </div>
    </div>

    <div class="filters">
      <input v-model="q" class="input" style="max-width:280px" placeholder="搜索文档…" @input="load" />
      <div class="tabs">
        <button class="tab" :class="{ active: folderId === null }" @click="folderId = null">全部</button>
        <button v-for="f in folders" :key="f.id" class="tab" :class="{ active: folderId === f.id }" @click="folderId = f.id">{{ f.name }}</button>
      </div>
    </div>

    <div class="list">
      <div v-for="d in docs" :key="d.id" class="card card-hover item" @click="router.push(`/docs/${d.id}`)">
        <div class="doc-ico">{{ d.ext.toUpperCase() }}</div>
        <div class="item-main">
          <div class="t">{{ d.title }}</div>
          <div class="s">{{ d.summary || '装修资料文档' }}</div>
        </div>
        <div class="item-side">
          <div class="meta">{{ fmtSize(d.size) }}</div>
          <div class="meta">{{ timeOf(d.updated_at) }}</div>
        </div>
      </div>
      <div v-if="!loading && !docs.length" class="empty"><div class="big">📄</div>暂无公开文档</div>
    </div>
  </div>
</template>

<style scoped>
.filters { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 20px; }
.tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.tab { padding: 7px 16px; border-radius: 999px; border: 1px solid var(--border-strong); background: #fff; color: var(--sub); font-size: 13px; cursor: pointer; }
.tab.active { background: var(--primary); border-color: var(--primary); color: #fff; }
.list { display: flex; flex-direction: column; gap: 12px; }
.item { display: flex; align-items: center; gap: 16px; padding: 16px 18px; cursor: pointer; }
.doc-ico { width: 44px; height: 44px; border-radius: 11px; background: var(--primary-soft); color: var(--primary); font-weight: 700; font-size: 11px; display: flex; align-items: center; justify-content: center; flex: none; }
.item-main { flex: 1; min-width: 0; }
.item-main .t { font-weight: 600; font-size: 15.5px; }
.item-main .s { color: var(--sub); font-size: 13px; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-side { text-align: right; flex: none; }
.meta { color: var(--muted); font-size: 12.5px; }
</style>
