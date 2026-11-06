<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import api from '@/api'

const pitfalls = ref<any[]>([])
const q = ref('')
const stage = ref('')
const category = ref('')
const risk = ref('')
const detail = ref<any>(null)

const stages = ['水电', '泥木', '油漆', '木工', '软装', '验收', '材料']
const cats = ['防水', '电路', '地面', '主材', '设计', '其他']
const riskLabel: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险' }
const riskClass: Record<string, string> = { high: 'badge-red', medium: 'badge-amber', low: 'badge-green' }

async function load() {
  try {
    const { data } = await api.get('/pitfalls', { params: { q: q.value, stage: stage.value, category: category.value, risk: risk.value } })
    pitfalls.value = data
  } catch { /* ignore */ }
}
function clear() { q.value = ''; stage.value = ''; category.value = ''; risk.value = ''; load() }

onMounted(load)
watch([stage, category, risk], load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>避坑清单</h2>
        <div class="desc">装修过程中的经验教训，按阶段与风险等级筛选</div>
      </div>
    </div>

    <div class="filters">
      <input v-model="q" class="input" style="max-width:240px" placeholder="搜索避坑项…" @input="load" />
      <select v-model="stage" class="select" style="max-width:130px">
        <option value="">全部阶段</option>
        <option v-for="s in stages" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="category" class="select" style="max-width:130px">
        <option value="">全部分类</option>
        <option v-for="c in cats" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="risk" class="select" style="max-width:130px">
        <option value="">全部等级</option>
        <option value="high">高风险</option>
        <option value="medium">中风险</option>
        <option value="low">低风险</option>
      </select>
      <button v-if="q || stage || category || risk" class="btn btn-ghost btn-sm" @click="clear">清空筛选</button>
    </div>

    <div class="pit-list">
      <div v-for="p in pitfalls" :key="p.id" class="card card-hover pit" @click="detail = p">
        <div class="pit-top">
          <span class="badge" :class="riskClass[p.risk_level]">{{ riskLabel[p.risk_level] }}</span>
          <span v-if="p.is_pinned" class="badge badge-blue">置顶</span>
          <span class="badge badge-gray">{{ p.stage || '未分类' }}</span>
          <span class="badge badge-gray">{{ p.category || '未分类' }}</span>
        </div>
        <div class="pit-title">{{ p.title }}</div>
        <div class="pit-advice">💡 {{ p.advice }}</div>
      </div>
      <div v-if="!pitfalls.length" class="empty">
        <div class="big">⚠</div>
        <div>没有符合条件的避坑项</div>
        <button v-if="q || stage || category || risk" class="btn btn-ghost btn-sm" style="margin-top:14px" @click="clear">清空筛选</button>
      </div>
    </div>

    <!-- 详情 -->
    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="modal" style="width:560px">
        <div class="modal-head"><b>{{ detail.title }}</b><button class="icon-btn" @click="detail = null">✕</button></div>
        <div class="modal-body">
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
            <span class="badge" :class="riskClass[detail.risk_level]">{{ riskLabel[detail.risk_level] }}</span>
            <span class="badge badge-gray">{{ detail.stage || '未分类' }}</span>
            <span class="badge badge-gray">{{ detail.category || '未分类' }}</span>
          </div>
          <div class="sec"><b>问题描述</b><p>{{ detail.problem || '—' }}</p></div>
          <div class="sec"><b>规避建议</b><p>{{ detail.advice }}</p></div>
          <div class="sec" v-if="detail.source_text"><b>参考来源</b><p>{{ detail.source_text }}</p></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
.pit-list { display: flex; flex-direction: column; gap: 12px; }
.pit { padding: 18px 20px; cursor: pointer; }
.pit-top { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 12px; }
.pit-title { font-weight: 600; font-size: 16px; }
.pit-advice { color: var(--sub); font-size: 14px; line-height: 1.7; margin-top: 8px; }
.sec { margin-bottom: 16px; }
.sec b { font-size: 13px; color: var(--sub); display: block; margin-bottom: 6px; }
.sec p { line-height: 1.8; color: var(--text-2); white-space: pre-wrap; }
</style>
