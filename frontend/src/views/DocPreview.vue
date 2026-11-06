<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const doc = ref<any>(null)
const loading = ref(true)
const err = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/documents/${route.params.id}/preview`)
    doc.value = data
  } catch (e: any) {
    err.value = e.message || '加载失败'
  } finally { loading.value = false }
})
</script>

<template>
  <div class="page-anim">
    <button class="back" @click="router.push('/docs')">← 返回文档列表</button>

    <div v-if="loading" class="empty"><div class="big">⏳</div>加载中…</div>
    <div v-else-if="err" class="empty"><div class="big">📄</div>{{ err }}</div>

    <div v-else class="card preview-card">
      <div class="head">
        <div class="doc-ico">{{ doc.ext.toUpperCase() }}</div>
        <div>
          <h2>{{ doc.title }}</h2>
          <div class="sub">{{ doc.summary || '装修资料文档' }} · 版本 v{{ doc.version }} · {{ new Date(doc.updated_at).toLocaleDateString('zh-CN') }}</div>
        </div>
      </div>
      <div class="body">
        <div v-if="doc.text" class="text">{{ doc.text }}</div>
        <div v-else class="empty"><div class="big">📄</div>该文档暂无文字内容（可能是扫描件或图片型 PDF）</div>
      </div>
      <div class="note">🔒 只读预览 · 原始文件仅管理员可下载</div>
    </div>
  </div>
</template>

<style scoped>
.back { color: var(--primary); font-size: 14px; border: none; background: none; cursor: pointer; margin-bottom: 16px; }
.back:hover { text-decoration: underline; }
.preview-card { overflow: hidden; }
.head { display: flex; align-items: center; gap: 16px; padding: 22px 26px; border-bottom: 1px solid var(--border); }
.doc-ico { width: 50px; height: 50px; border-radius: 12px; background: var(--primary-soft); color: var(--primary); font-weight: 700; font-size: 12px; display: flex; align-items: center; justify-content: center; }
.head h2 { font-size: 20px; }
.sub { color: var(--sub); font-size: 13px; margin-top: 6px; }
.body { padding: 26px; }
.text { white-space: pre-wrap; line-height: 2; color: var(--text-2); font-size: 15px; }
.note { padding: 14px 26px; background: var(--bg-soft); color: var(--sub); font-size: 12.5px; border-top: 1px solid var(--border); }
</style>
