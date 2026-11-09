<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const pitfalls = ref<any[]>([])
const q = ref('')
const statusFilter = ref('')
const riskFilter = ref('')

const showForm = ref(false)
const form = ref<any>({})
const editingId = ref<number | null>(null)
const saving = ref(false)

const docs = ref<any[]>([])
const images = ref<any[]>([])

const riskLabel: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险' }
const riskClass: Record<string, string> = { high: 'badge-red', medium: 'badge-amber', low: 'badge-green' }
const statusLabel: Record<string, string> = { draft: '草稿', published: '已发布', archived: '已归档', trashed: '回收站' }
const statusClass: Record<string, string> = { draft: 'badge-gray', published: 'badge-green', archived: 'badge-amber' }

async function load() {
  try {
    const { data } = await api.get('/pitfalls', { params: { q: q.value, status: statusFilter.value, risk: riskFilter.value } })
    pitfalls.value = data
  } catch (e: any) { ui.toast(e.message, 'error') }
}

onMounted(async () => {
  await load()
  try {
    docs.value = (await api.get('/documents')).data
    images.value = (await api.get('/images')).data
  } catch { /* ignore */ }
})

function openCreate() {
  editingId.value = null
  form.value = { title: '', stage: '', category: '', problem: '', advice: '', risk_level: 'medium', source_text: '', is_pinned: false, related_image_ids: [], related_document_ids: [] }
  showForm.value = true
}
function openEdit(p: any) {
  editingId.value = p.id
  form.value = { title: p.title, stage: p.stage, category: p.category, problem: p.problem, advice: p.advice, risk_level: p.risk_level, source_text: p.source_text, is_pinned: p.is_pinned, related_image_ids: p.related_images.map((x: any) => x.id), related_document_ids: p.related_documents.map((x: any) => x.id) }
  showForm.value = true
}

async function save() {
  if (!form.value.title?.trim()) { ui.toast('标题不能为空', 'error'); return }
  if (!form.value.advice?.trim()) { ui.toast('规避建议不能为空', 'error'); return }
  saving.value = true
  try {
    if (editingId.value) {
      await api.patch(`/pitfalls/${editingId.value}`, form.value)
    } else {
      await api.post('/pitfalls', form.value)
    }
    ui.toast('已保存（草稿状态）')
    showForm.value = false
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') } finally { saving.value = false }
}

async function act(p: any, action: string) {
  if (action === 'trash' && !confirm(`确认删除避坑项「${p.title}」？将进入回收站。`)) return
  try {
    const method = action === 'trash' ? 'delete' : 'post'
    const url = action === 'trash' ? `/pitfalls/${p.id}` : `/pitfalls/${p.id}/${action}`
    await api[method](url)
    ui.toast(action === 'publish' ? '已发布' : action === 'withdraw' ? '已撤回' : '已删除')
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>避坑项管理</h2>
        <div class="desc">逐条录入 · 发布 / 撤回 · 置顶 · 关联资料</div>
      </div>
      <div class="toolbar"><button class="btn btn-primary" @click="openCreate">＋ 新增避坑项</button></div>
    </div>

    <div class="card">
      <div class="toolbar" style="padding:14px 18px;border-bottom:1px solid var(--border)">
        <input v-model="q" class="input" style="max-width:220px" placeholder="搜索…" @input="load" />
        <select v-model="statusFilter" class="select" style="max-width:130px" @change="load">
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="published">已发布</option>
        </select>
        <select v-model="riskFilter" class="select" style="max-width:130px" @change="load">
          <option value="">全部等级</option>
          <option value="high">高风险</option>
          <option value="medium">中风险</option>
          <option value="low">低风险</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table class="tbl">
          <thead><tr><th>标题</th><th>阶段/分类</th><th>风险</th><th>状态</th><th style="width:250px">操作</th></tr></thead>
          <tbody>
            <tr v-for="p in pitfalls" :key="p.id">
              <td>
                <div style="font-weight:500">{{ p.title }}</div>
                <div style="font-size:12px;color:var(--sub)">{{ (p.advice || '').slice(0, 40) }}…</div>
              </td>
              <td><span class="badge badge-gray">{{ p.stage || '未分类' }}</span> <span class="badge badge-gray">{{ p.category || '未分类' }}</span></td>
              <td><span class="badge" :class="riskClass[p.risk_level]">{{ riskLabel[p.risk_level] }}</span></td>
              <td>
                <span class="badge" :class="statusClass[p.status]">{{ statusLabel[p.status] }}</span>
                <span v-if="p.is_pinned" class="badge badge-blue" style="margin-left:4px">置顶</span>
              </td>
              <td>
                <div class="ops">
                  <button class="btn btn-soft btn-sm" @click="openEdit(p)">编辑</button>
                  <button v-if="p.status !== 'published'" class="btn btn-soft btn-sm" @click="act(p, 'publish')">发布</button>
                  <button v-else class="btn btn-ghost btn-sm" @click="act(p, 'withdraw')">撤回</button>
                  <button class="btn btn-danger btn-sm" @click="act(p, 'trash')">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="!pitfalls.length"><td colspan="5"><div class="empty"><div class="big">⚠</div>暂无避坑项</div></td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 表单 -->
    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal" style="width:640px">
        <div class="modal-head"><b>{{ editingId ? '编辑避坑项' : '新增避坑项' }}</b><button class="icon-btn" @click="showForm = false">✕</button></div>
        <div class="modal-body">
          <div class="field"><label>标题（必填）</label><input v-model="form.title" class="input" maxlength="100" /></div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
            <div class="field"><label>装修阶段</label>
              <select v-model="form.stage" class="select"><option value="">未分类</option><option>水电</option><option>泥木</option><option>油漆</option><option>木工</option><option>软装</option><option>验收</option><option>材料</option></select>
            </div>
            <div class="field"><label>分类</label><input v-model="form.category" class="input" placeholder="如：防水" /></div>
            <div class="field"><label>风险等级</label>
              <select v-model="form.risk_level" class="select"><option value="high">高风险</option><option value="medium">中风险</option><option value="low">低风险</option></select>
            </div>
          </div>
          <div class="field"><label>问题描述</label><textarea v-model="form.problem" class="textarea" placeholder="描述踩坑的经过与后果"></textarea></div>
          <div class="field"><label>规避建议（必填）</label><textarea v-model="form.advice" class="textarea" placeholder="给出可执行的规避建议"></textarea></div>
          <div class="field"><label>参考来源</label><input v-model="form.source_text" class="input" placeholder="如：团队经验总结" /></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="field"><label>关联图片</label>
              <select v-model="form.related_image_ids" class="select" multiple style="height:90px">
                <option v-for="i in images" :key="i.id" :value="i.id">{{ i.title }}</option>
              </select>
            </div>
            <div class="field"><label>关联文档</label>
              <select v-model="form.related_document_ids" class="select" multiple style="height:90px">
                <option v-for="d in docs" :key="d.id" :value="d.id">{{ d.title }}</option>
              </select>
            </div>
          </div>
          <label style="display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer">
            <input v-model="form.is_pinned" type="checkbox" /> 置顶显示
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn btn-ghost" @click="showForm = false">取消</button>
          <button class="btn btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
