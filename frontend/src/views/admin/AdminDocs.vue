<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const ui = useUiStore()

const docs = ref<any[]>([])
const folders = ref<any[]>([])
const q = ref('')
const statusFilter = ref('')
const loading = ref(true)

const showUpload = ref(false)
const upFile = ref<File | null>(null)
const upFolder = ref('')
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const showVer = ref(false)
const versions = ref<any[]>([])
const verDoc = ref<any>(null)

const showEdit = ref(false)
const editDoc = ref<any>(null)
const editTitle = ref('')
const editSummary = ref('')
const editFolder = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/documents', { params: { q: q.value, status: statusFilter.value } })
    docs.value = data
  } catch (e: any) { ui.toast(e.message, 'error') } finally { loading.value = false }
}

onMounted(async () => {
  await load()
  try { folders.value = (await api.get('/documents/folders')).data } catch { /* ignore */ }
})

function fmtSize(n: number) {
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(0) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}
function timeOf(t: string) { return new Date(t).toLocaleString('zh-CN', { hour12: false }) }
const statusLabel: Record<string, string> = { draft: '草稿', published: '已发布', archived: '已归档', trashed: '回收站' }
const statusClass: Record<string, string> = { draft: 'badge-gray', published: 'badge-green', archived: 'badge-amber', trashed: 'badge-red' }

function onPickFile(e: Event) {
  const t = e.target as HTMLInputElement
  if (t.files?.length) upFile.value = t.files[0]
}
async function doUpload() {
  if (!upFile.value) { ui.toast('请先选择文件', 'error'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', upFile.value)
    if (upFolder.value) fd.append('folder_id', upFolder.value)
    await api.post('/documents', fd, { timeout: 0 })
    ui.toast('上传成功（草稿状态，发布后公开）')
    showUpload.value = false
    upFile.value = null
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') } finally { uploading.value = false }
}

async function openVersions(d: any) {
  verDoc.value = d
  showVer.value = true
  try { versions.value = (await api.get(`/documents/${d.id}/versions`)).data } catch { /* ignore */ }
}
async function rollback(v: any) {
  try {
    await api.post(`/documents/${verDoc.value.id}/versions/${v.version_no}/rollback`)
    ui.toast('已回滚（生成新版本）')
    await openVersions(verDoc.value); await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}
async function download(d: any) {
  try {
    const res = await api.get(`/documents/${d.id}/download`, { responseType: 'blob', timeout: 0 })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url; a.download = `${d.title}.${d.ext}`; a.click(); URL.revokeObjectURL(url)
    ui.toast('下载成功，已写入审计日志')
  } catch (e: any) { ui.toast(e.message, 'error') }
}

async function act(d: any, action: string) {
  const map: Record<string, string> = { publish: '发布', withdraw: '撤回', trash: '删除' }
  if (action === 'trash' && !confirm(`确认删除文档「${d.title}」？删除后进入回收站，用户端将不可见。`)) return
  try {
    const method = action === 'trash' ? 'delete' : 'post'
    const url = action === 'trash' ? `/documents/${d.id}` : `/documents/${d.id}/${action}`
    await api[method](url)
    ui.toast(`${map[action]}成功`)
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}

function openEdit(d: any) {
  editDoc.value = d
  editTitle.value = d.title
  editSummary.value = d.summary || ''
  editFolder.value = d.folder_id
  showEdit.value = true
}
async function saveEdit() {
  try {
    await api.patch(`/documents/${editDoc.value.id}`, { title: editTitle.value, summary: editSummary.value, folder_id: editFolder.value })
    ui.toast('已保存')
    showEdit.value = false
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>文档管理</h2>
        <div class="desc">上传 / 编辑 / 版本 / 发布 / 撤回 / 回收站</div>
      </div>
      <div class="toolbar">
        <button class="btn btn-primary" @click="showUpload = true">＋ 上传文档</button>
      </div>
    </div>

    <div class="card">
      <div class="toolbar" style="padding:14px 18px;border-bottom:1px solid var(--border)">
        <input v-model="q" class="input" style="max-width:220px" placeholder="搜索文档…" @input="load" />
        <select v-model="statusFilter" class="select" style="max-width:140px" @change="load">
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="published">已发布</option>
          <option value="archived">已归档</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table class="tbl">
          <thead>
            <tr><th>文档</th><th class="hide-m">大小</th><th>版本</th><th>状态</th><th class="hide-m">更新时间</th><th style="width:300px">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in docs" :key="d.id">
              <td>
                <div style="display:flex;align-items:center;gap:12px">
                  <span class="file-ico">{{ d.ext.toUpperCase() }}</span>
                  <div>
                    <div style="font-weight:500">{{ d.title }}</div>
                    <div class="hide-m" style="font-size:12px;color:var(--sub)">{{ d.owner_name || '—' }}</div>
                  </div>
                </div>
              </td>
              <td class="hide-m">{{ fmtSize(d.size) }}</td>
              <td><span class="badge badge-blue">v{{ d.current_version }}</span><span v-if="d.published_version_no" class="badge badge-green" style="margin-left:4px">发布 v{{ d.published_version_no }}</span></td>
              <td><span class="badge" :class="statusClass[d.status]">{{ statusLabel[d.status] }}</span></td>
              <td class="hide-m" style="color:var(--sub)">{{ timeOf(d.updated_at) }}</td>
              <td>
                <div class="ops">
                  <button class="btn btn-soft btn-sm" @click="router.push(`/admin/docs/${d.id}/edit`)">编辑</button>
                  <button class="btn btn-ghost btn-sm" @click="openEdit(d)">信息</button>
                  <button class="btn btn-ghost btn-sm" @click="openVersions(d)">版本</button>
                  <button class="btn btn-ghost btn-sm" @click="download(d)">下载</button>
                  <button v-if="d.status !== 'published'" class="btn btn-soft btn-sm" @click="act(d, 'publish')">发布</button>
                  <button v-else class="btn btn-ghost btn-sm" @click="act(d, 'withdraw')">撤回</button>
                  <button class="btn btn-danger btn-sm" @click="act(d, 'trash')">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && !docs.length"><td colspan="6"><div class="empty"><div class="big">📄</div>暂无文档</div></td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 上传 -->
    <div v-if="showUpload" class="modal-mask" @click.self="showUpload = false">
      <div class="modal">
        <div class="modal-head"><b>上传文档</b><button class="icon-btn" @click="showUpload = false">✕</button></div>
        <div class="modal-body">
          <div class="up-zone" @click="fileInput?.click()">
            <span class="big">📄</span>
            <div>{{ upFile ? upFile.name : '点击选择文件上传' }}</div>
            <div class="fmt">支持 docx / pdf，单文件 ≤ 100MB</div>
          </div>
          <input ref="fileInput" type="file" accept=".docx,.pdf" style="display:none" @change="onPickFile" />
          <div class="field" style="margin-top:16px">
            <label>文档分类</label>
            <select v-model="upFolder" class="select">
              <option value="">未分类</option>
              <option v-for="f in folders" :key="f.id" :value="f.id">{{ f.name }}</option>
            </select>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-ghost" @click="showUpload = false">取消</button>
          <button class="btn btn-primary" :disabled="uploading || !upFile" @click="doUpload">{{ uploading ? '上传中…' : '确认上传' }}</button>
        </div>
      </div>
    </div>

    <!-- 版本历史 -->
    <div v-if="showVer" class="modal-mask" @click.self="showVer = false">
      <div class="modal">
        <div class="modal-head"><b>版本历史 · {{ verDoc?.title }}</b><button class="icon-btn" @click="showVer = false">✕</button></div>
        <div class="modal-body" style="max-height:380px;overflow-y:auto">
          <div v-for="(v, i) in versions" :key="v.id" style="display:flex;align-items:center;gap:14px;padding:12px 4px;border-bottom:1px dashed var(--border)">
            <span class="badge badge-blue" style="flex:none">v{{ v.version_no }}</span>
            <div style="flex:1;min-width:0">
              <div style="font-weight:500">{{ v.operator_name || '系统' }}</div>
              <div style="font-size:12px;color:var(--sub)">{{ timeOf(v.created_at) }} · {{ fmtSize(v.file_size) }}</div>
            </div>
            <span v-if="i === 0" class="badge badge-green">当前</span>
            <button v-else class="btn btn-ghost btn-sm" @click="rollback(v)">回滚</button>
          </div>
        </div>
        <div class="modal-foot"><button class="btn btn-ghost" @click="showVer = false">关闭</button></div>
      </div>
    </div>

    <!-- 编辑信息 -->
    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <div class="modal">
        <div class="modal-head"><b>文档信息</b><button class="icon-btn" @click="showEdit = false">✕</button></div>
        <div class="modal-body">
          <div class="field"><label>标题</label><input v-model="editTitle" class="input" /></div>
          <div class="field"><label>摘要</label><textarea v-model="editSummary" class="textarea" style="min-height:70px"></textarea></div>
          <div class="field"><label>分类</label>
            <select v-model="editFolder" class="select">
              <option :value="null">未分类</option>
              <option v-for="f in folders" :key="f.id" :value="f.id">{{ f.name }}</option>
            </select>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-ghost" @click="showEdit = false">取消</button>
          <button class="btn btn-primary" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-ico { width: 38px; height: 38px; border-radius: 10px; flex: none; display: inline-flex; align-items: center; justify-content: center; background: var(--primary-soft); color: var(--primary); font-size: 10px; font-weight: 700; }
</style>
