<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { useUserStore } from '@/stores/user'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const ui = useUiStore()

const docId = route.params.id as string
const loading = ref(true)
const cfg = ref<any>(null)
const editorRef = ref<HTMLElement | null>(null)
let editorInstance: any = null
const isEditable = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get(`/onlyoffice/documents/${docId}/editor-config`)
    cfg.value = data
    isEditable.value = data.mode === 'edit'
    if (data.available) await loadOnlyOffice(data)
  } catch (e: any) {
    ui.toast(e.message, 'error')
  } finally {
    loading.value = false
  }
})

function loadOnlyOffice(data: any): Promise<void> {
  return new Promise((resolve) => {
    const init = () => {
      const DocsAPI = (window as any).DocsAPI
      if (!DocsAPI || !editorRef.value) { resolve(); return }
      editorInstance = new DocsAPI.DocEditor(editorRef.value.id, data.config, { width: '100%', height: '100%' })
      resolve()
    }
    if ((window as any).DocsAPI) { init(); return }
    const script = document.createElement('script')
    script.setAttribute('data-oo', '1')
    script.src = `${data.onlyoffice_url}/web-apps/apps/api/documents/api.js`
    script.onload = init
    script.onerror = () => { ui.toast('OnlyOffice 编辑器加载失败', 'error'); resolve() }
    document.head.appendChild(script)
  })
}

async function download() {
  try {
    const res = await api.get(`/documents/${docId}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url; a.download = `${cfg.value?.doc?.name || '文档'}.docx`; a.click(); URL.revokeObjectURL(url)
    ui.toast('下载成功，已写入审计日志')
  } catch (e: any) { ui.toast(e.message, 'error') }
}

onBeforeUnmount(() => { if (editorInstance) { try { editorInstance.destroyEditor() } catch { /* ignore */ } } })
</script>

<template>
  <div class="page-anim">
    <div class="card editor-shell">
      <div class="editor-top">
        <span class="fn">{{ cfg?.doc?.name || '文档' }}</span>
        <div v-if="isEditable" class="co-badge" title="在线协作者">
          <span style="background:linear-gradient(135deg,#60a5fa,#3b82f6)">{{ userStore.user?.display_name?.[0] || 'A' }}</span>
        </div>
        <span v-if="isEditable" class="badge badge-amber">● 协同编辑</span>
        <span v-else class="badge badge-gray">只读预览</span>
        <div style="flex:1"></div>
        <button class="btn btn-ghost btn-sm" @click="download">下载</button>
        <button class="btn btn-ghost btn-sm" @click="router.push('/admin/docs')">返回列表</button>
      </div>

      <div class="editor-body">
        <div v-if="cfg?.available" id="oo-editor" ref="editorRef" style="flex:1;min-height:0"></div>
        <div v-else class="editor-canvas" style="flex:1">
          <div style="max-width:520px;margin:0 auto;text-align:center;padding-top:60px">
            <div style="font-size:54px;margin-bottom:18px">📝</div>
            <h3>{{ cfg?.doc?.name }}</h3>
            <p style="color:var(--sub);margin:14px 0 8px">{{ isEditable ? '在线协同编辑需部署 OnlyOffice 服务' : '在线预览需部署 OnlyOffice 服务' }}</p>
            <p style="color:var(--muted);font-size:12.5px;margin-bottom:24px;line-height:1.8">
              部署后文档将在此区域以 {{ isEditable ? '可编辑（多人实时协同）' : '只读' }} 模式呈现<br>当前可先下载文档到本地查看
            </p>
            <button class="btn btn-primary" @click="download">下载文档</button>
          </div>
        </div>

        <div class="editor-side">
          <div class="side-block">
            <h4>文档信息</h4>
            <div class="side-row"><span>当前版本</span><b>v{{ cfg?.doc?.version || 1 }}</b></div>
            <div class="side-row"><span>权限</span><b>{{ isEditable ? '可编辑' : '只读' }}</b></div>
          </div>
          <div class="side-block">
            <h4>提示</h4>
            <div style="font-size:12.5px;color:var(--sub);line-height:1.8">
              {{ isEditable ? '每次保存自动生成版本快照并写入审计日志。' : '你当前为只读权限。' }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
