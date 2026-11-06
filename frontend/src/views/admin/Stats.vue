<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const stats = ref<any>({})
const trends = ref<any>(null)
const days = ref(30)

async function loadOverview() {
  try { stats.value = (await api.get('/stats/overview')).data } catch (e: any) { ui.toast(e.message, 'error') }
}
async function loadTrends() {
  try { trends.value = (await api.get('/stats/trends', { params: { days: days.value } })).data } catch { /* ignore */ }
}

function barHeight(v: number, arr: number[]) {
  const max = Math.max(1, ...arr)
  return Math.max(4, Math.round((v / max) * 100))
}

onMounted(async () => { await Promise.all([loadOverview(), loadTrends()]) })
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>统计看板</h2>
        <div class="desc">内容资产与发布趋势 · 口径与业务列表一致</div>
      </div>
      <div class="toolbar">
        <select v-model="days" class="select" style="max-width:130px" @change="loadTrends">
          <option :value="7">近 7 天</option>
          <option :value="30">近 30 天</option>
          <option :value="60">近 60 天</option>
        </select>
      </div>
    </div>

    <div class="stat-grid">
      <div class="card stat" style="cursor:default"><div class="k"><span class="dot"></span>文档总数</div><div class="v">{{ stats.document_total || 0 }}</div><div class="t">已发布 {{ stats.document_published || 0 }} · 草稿 {{ stats.document_draft || 0 }}</div></div>
      <div class="card stat" style="cursor:default"><div class="k"><span class="dot" style="background:#10b981;box-shadow:0 0 0 4px #ecfdf5"></span>图片总数</div><div class="v">{{ stats.image_total || 0 }}</div><div class="t">已发布 {{ stats.image_published || 0 }}</div></div>
      <div class="card stat" style="cursor:default"><div class="k"><span class="dot" style="background:#f59e0b;box-shadow:0 0 0 4px #fffbeb"></span>避坑项</div><div class="v">{{ stats.pitfall_total || 0 }}</div><div class="t">已发布 {{ stats.pitfall_published || 0 }}</div></div>
      <div class="card stat" style="cursor:default"><div class="k"><span class="dot" style="background:#8b5cf6;box-shadow:0 0 0 4px #f5f3ff"></span>本周编辑</div><div class="v">{{ stats.week_edit || 0 }}</div><div class="t">本周发布 {{ stats.week_publish || 0 }}</div></div>
    </div>

    <div class="card">
      <div style="padding:16px 20px;border-bottom:1px solid var(--border);font-weight:600">发布 / 编辑 / 上传 趋势（近 {{ days }} 天）</div>
      <div v-if="trends" class="chart">
        <div v-for="(label, i) in trends.labels" :key="label" class="bar-col" :title="label">
          <div class="bars">
            <span class="bar b-pub" :style="{ height: barHeight(trends.publish[i], trends.publish) + '%' }"></span>
            <span class="bar b-edit" :style="{ height: barHeight(trends.edit[i], trends.edit) + '%' }"></span>
            <span class="bar b-up" :style="{ height: barHeight(trends.upload[i], trends.upload) + '%' }"></span>
          </div>
          <span class="bl">{{ i % 3 === 0 ? label : '' }}</span>
        </div>
      </div>
      <div class="legend">
        <span><i class="c-pub"></i>发布</span><span><i class="c-edit"></i>编辑</span><span><i class="c-up"></i>上传</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart { display: flex; align-items: flex-end; gap: 4px; padding: 24px 20px 8px; height: 200px; overflow-x: auto; }
.bar-col { flex: 1; min-width: 18px; display: flex; flex-direction: column; justify-content: flex-end; height: 100%; }
.bars { display: flex; align-items: flex-end; gap: 2px; height: 140px; }
.bar { width: 100%; border-radius: 3px 3px 0 0; min-height: 4px; }
.b-pub { background: var(--ok); }
.b-edit { background: var(--primary); }
.b-up { background: var(--warn); }
.bl { font-size: 10px; color: var(--muted); text-align: center; margin-top: 6px; white-space: nowrap; }
.legend { display: flex; gap: 18px; padding: 10px 20px 16px; color: var(--sub); font-size: 12.5px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; }
.c-pub { background: var(--ok); } .c-edit { background: var(--primary); } .c-up { background: var(--warn); }
</style>
