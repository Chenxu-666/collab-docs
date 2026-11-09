<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '@/api'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const albums = ref<any[]>([])
const images = ref<any[]>([])
const activeAlbum = ref(0)
const thumbs = ref<Record<number, string>>({})
const statusFilter = ref('')

const showUpload = ref(false)
const upFiles = ref<File[]>([])
const upAlbum = ref<number | null>(null)
const uploading = ref(false)
const imgInput = ref<HTMLInputElement | null>(null)

const showAlbum = ref(false)
const newAlbumName = ref('')

const editTarget = ref<any>(null)
const showEdit = ref(false)
const editTitle = ref('')
const editDesc = ref('')

const lb = ref(false)
const lbIndex = ref(0)
const lbUrl = ref('')

const filtered = computed(() => images.value.filter((i) => (activeAlbum.value === 0 || i.album_id === activeAlbum.value)))

async function load() {
  try {
    const [a, im] = await Promise.all([
      api.get('/albums'), api.get('/images', { params: { status: statusFilter.value } })
    ])
    albums.value = a.data
    images.value = im.data
    images.value.forEach((img: any) => loadThumb(img))
  } catch (e: any) { ui.toast(e.message, 'error') }
}
async function loadThumb(img: any) {
  try {
    const res = await api.get(`/images/${img.id}/thumb`, { responseType: 'blob' })
    thumbs.value[img.id] = URL.createObjectURL(res.data)
  } catch { /* ignore */ }
}

function onPickFiles(e: Event) {
  const t = e.target as HTMLInputElement
  upFiles.value = Array.from(t.files || [])
}
async function doUpload() {
  if (!upFiles.value.length) { ui.toast('请先选择图片', 'error'); return }
  const fd = new FormData()
  upFiles.value.forEach((f) => fd.append('files', f))
  if (upAlbum.value) fd.append('album_id', String(upAlbum.value))
  uploading.value = true
  try {
    const { data } = await api.post('/images', fd, { timeout: 0 })
    if (data.failed && data.failed.length) {
      const msgs = data.failed.map((f: any) => `${f.name}：${f.reason}`).join('；')
      ui.toast(`部分图片上传失败（${msgs}）`, 'error')
    } else if (data.created && data.created.length) {
      ui.toast(`已上传 ${data.created.length} 张图片（草稿状态）`)
    } else {
      ui.toast('没有图片被成功上传', 'error')
    }
    showUpload.value = false; upFiles.value = []
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') } finally { uploading.value = false }
}

async function createAlbum() {
  if (!newAlbumName.value.trim()) { ui.toast('请输入相册名称', 'error'); return }
  try {
    await api.post('/albums', { name: newAlbumName.value.trim() })
    ui.toast('相册创建成功')
    showAlbum.value = false; newAlbumName.value = ''
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}

function openEdit(img: any) {
  editTarget.value = img; editTitle.value = img.title; editDesc.value = img.description || ''
  showEdit.value = true
}
async function saveEdit() {
  try {
    await api.patch(`/images/${editTarget.value.id}`, { title: editTitle.value, description: editDesc.value })
    ui.toast('已保存')
    showEdit.value = false
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}

async function act(img: any, action: string) {
  if (action === 'trash' && !confirm(`确认删除图片「${img.title}」？将进入回收站。`)) return
  try {
    const method = action === 'trash' ? 'delete' : 'post'
    const url = action === 'trash' ? `/images/${img.id}` : `/images/${img.id}/${action}`
    await api[method](url)
    ui.toast(action === 'publish' ? '已发布' : action === 'withdraw' ? '已撤回' : '已删除')
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}

async function openLb(i: number) {
  lbIndex.value = i; lb.value = true; lbUrl.value = ''
  const img = filtered.value[i]
  try { lbUrl.value = URL.createObjectURL((await api.get(`/images/${img.id}/file`, { responseType: 'blob' })).data) } catch { /* ignore */ }
}
function stepLb(d: number) {
  const n = (lbIndex.value + d + filtered.value.length) % filtered.value.length
  openLb(n)
}

const statusLabel: Record<string, string> = { draft: '草稿', published: '已发布', archived: '已归档', trashed: '回收站' }

onMounted(load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>图片库管理</h2>
        <div class="desc">相册 / 批量上传 / 发布 / 撤回 / 删除</div>
      </div>
      <div class="toolbar">
        <button class="btn btn-ghost" @click="showAlbum = true">＋ 新建相册</button>
        <button class="btn btn-primary" @click="showUpload = true">＋ 上传图片</button>
      </div>
    </div>

    <div class="toolbar" style="margin-bottom:16px">
      <div class="album-tabs" style="margin:0">
        <button class="album-tab" :class="{ active: activeAlbum === 0 }" @click="activeAlbum = 0">全部</button>
        <button v-for="a in albums" :key="a.id" class="album-tab" :class="{ active: activeAlbum === a.id }" @click="activeAlbum = a.id">{{ a.name }}</button>
      </div>
      <select v-model="statusFilter" class="select" style="max-width:130px;margin-left:auto" @change="load">
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="published">已发布</option>
      </select>
    </div>

    <div class="photo-grid">
      <div v-for="(img, i) in filtered" :key="img.id" class="ph-card">
        <div class="ph-thumb" @click="openLb(i)">
          <img v-if="thumbs[img.id]" :src="thumbs[img.id]" :alt="img.title" />
          <div v-else style="color:var(--muted);font-size:13px">加载中…</div>
        </div>
        <div class="ph-info">
          <span class="t">{{ img.title }}</span>
          <span class="badge" :class="img.status === 'published' ? 'badge-green' : 'badge-gray'" style="flex:none">{{ statusLabel[img.status] }}</span>
        </div>
        <div class="ph-ops">
          <button @click="openEdit(img)">编辑</button>
          <button v-if="img.status !== 'published'" @click="act(img, 'publish')">发布</button>
          <button v-else @click="act(img, 'withdraw')">撤回</button>
          <button class="del" @click="act(img, 'trash')">删除</button>
        </div>
      </div>
    </div>
    <div v-if="!filtered.length" class="empty"><div class="big">🖼️</div>暂无图片</div>

    <!-- 灯箱 -->
    <div v-if="lb" class="lightbox" @click.self="lb = false">
      <button class="lb-close" @click="lb = false">✕</button>
      <div class="lb-stage">
        <button class="lb-arrow lb-prev" @click="stepLb(-1)">‹</button>
        <img v-if="lbUrl" class="lb-img" :src="lbUrl" :alt="filtered[lbIndex]?.title" />
        <button class="lb-arrow lb-next" @click="stepLb(1)">›</button>
      </div>
      <div class="lb-cap"><b>{{ filtered[lbIndex]?.title }}</b><span>{{ lbIndex + 1 }} / {{ filtered.length }}</span></div>
    </div>

    <!-- 上传 -->
    <div v-if="showUpload" class="modal-mask" @click.self="showUpload = false">
      <div class="modal">
        <div class="modal-head"><b>上传图片</b><button class="icon-btn" @click="showUpload = false">✕</button></div>
        <div class="modal-body">
          <div class="up-zone" @click="imgInput?.click()">
            <span class="big">🖼️</span>
            <div>{{ upFiles.length ? `已选择 ${upFiles.length} 张` : '点击选择（支持批量）' }}</div>
            <div class="fmt">jpg / png / webp / gif，单张 ≤ 20MB</div>
          </div>
          <input ref="imgInput" type="file" accept=".jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif" multiple style="display:none" @change="onPickFiles" />
          <div class="field" style="margin-top:16px"><label>归属相册</label>
            <select v-model="upAlbum" class="select">
              <option :value="null">未分类</option>
              <option v-for="a in albums" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-ghost" @click="showUpload = false">取消</button>
          <button class="btn btn-primary" :disabled="!upFiles.length || uploading" @click="doUpload">{{ uploading ? '上传中…' : '确认上传' }}</button>
        </div>
      </div>
    </div>

    <!-- 新建相册 -->
    <div v-if="showAlbum" class="modal-mask" @click.self="showAlbum = false">
      <div class="modal" style="width:400px">
        <div class="modal-head"><b>新建相册</b><button class="icon-btn" @click="showAlbum = false">✕</button></div>
        <div class="modal-body"><div class="field"><label>相册名称</label><input v-model="newAlbumName" class="input" placeholder="如：客厅参考" /></div></div>
        <div class="modal-foot"><button class="btn btn-ghost" @click="showAlbum = false">取消</button><button class="btn btn-primary" @click="createAlbum">创建</button></div>
      </div>
    </div>

    <!-- 编辑图片 -->
    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <div class="modal">
        <div class="modal-head"><b>编辑图片</b><button class="icon-btn" @click="showEdit = false">✕</button></div>
        <div class="modal-body">
          <div class="field"><label>标题</label><input v-model="editTitle" class="input" /></div>
          <div class="field"><label>描述</label><textarea v-model="editDesc" class="textarea" style="min-height:70px"></textarea></div>
        </div>
        <div class="modal-foot"><button class="btn btn-ghost" @click="showEdit = false">取消</button><button class="btn btn-primary" @click="saveEdit">保存</button></div>
      </div>
    </div>
  </div>
</template>
