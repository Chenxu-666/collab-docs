<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api'
import { useUserStore } from '@/stores/user'
import { useUiStore } from '@/stores/ui'

const userStore = useUserStore()
const ui = useUiStore()
const tab = ref<'documents' | 'images' | 'pitfalls'>('documents')
const docs = ref<any[]>([])
const images = ref<any[]>([])
const pitfalls = ref<any[]>([])

async function load() {
  try {
    if (tab.value === 'documents') docs.value = (await api.get('/documents/trash')).data
    if (tab.value === 'images') images.value = (await api.get('/images/trash')).data
    if (tab.value === 'pitfalls') pitfalls.value = (await api.get('/pitfalls/trash')).data
  } catch (e: any) { ui.toast(e.message, 'error') }
}

async function restore(type: string, id: number) {
  try {
    await api.post(`/${type}/${id}/restore`)
    ui.toast('已恢复（草稿状态，需重新发布）')
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}
async function permanent(type: string, id: number, name: string) {
  if (!confirm(`彻底删除「${name}」？此操作不可恢复！`)) return
  try {
    await api.delete(`/${type}/${id}/permanent`)
    ui.toast('已彻底删除')
    await load()
  } catch (e: any) { ui.toast(e.message, 'error') }
}

function switchTab(t: any) { tab.value = t; load() }
onMounted(load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>回收站</h2>
        <div class="desc">软删除内容可恢复；彻底删除仅超级管理员可执行</div>
      </div>
    </div>

    <div class="album-tabs">
      <button class="album-tab" :class="{ active: tab === 'documents' }" @click="switchTab('documents')">文档</button>
      <button class="album-tab" :class="{ active: tab === 'images' }" @click="switchTab('images')">图片</button>
      <button class="album-tab" :class="{ active: tab === 'pitfalls' }" @click="switchTab('pitfalls')">避坑项</button>
    </div>

    <div class="card">
      <div class="tbl-wrap">
        <table class="tbl">
          <thead><tr><th>名称</th><th>类型</th><th style="width:220px">操作</th></tr></thead>
          <tbody>
            <template v-if="tab === 'documents'">
              <tr v-for="d in docs" :key="d.id">
                <td><b>{{ d.title }}</b><span class="badge badge-gray" style="margin-left:8px">{{ d.ext }}</span></td>
                <td>文档</td>
                <td><div class="ops">
                  <button class="btn btn-soft btn-sm" @click="restore('documents', d.id)">恢复</button>
                  <button v-if="userStore.isSuperAdmin" class="btn btn-danger btn-sm" @click="permanent('documents', d.id, d.title)">彻底删除</button>
                </div></td>
              </tr>
              <tr v-if="!docs.length"><td colspan="3"><div class="empty"><div class="big">🗑</div>回收站暂无文档</div></td></tr>
            </template>
            <template v-else-if="tab === 'images'">
              <tr v-for="i in images" :key="i.id">
                <td><b>{{ i.title }}</b></td><td>图片</td>
                <td><div class="ops">
                  <button class="btn btn-soft btn-sm" @click="restore('images', i.id)">恢复</button>
                  <button v-if="userStore.isSuperAdmin" class="btn btn-danger btn-sm" @click="permanent('images', i.id, i.title)">彻底删除</button>
                </div></td>
              </tr>
              <tr v-if="!images.length"><td colspan="3"><div class="empty"><div class="big">🗑</div>回收站暂无图片</div></td></tr>
            </template>
            <template v-else>
              <tr v-for="p in pitfalls" :key="p.id">
                <td><b>{{ p.title }}</b></td><td>避坑项</td>
                <td><div class="ops">
                  <button class="btn btn-soft btn-sm" @click="restore('pitfalls', p.id)">恢复</button>
                  <button v-if="userStore.isSuperAdmin" class="btn btn-danger btn-sm" @click="permanent('pitfalls', p.id, p.title)">彻底删除</button>
                </div></td>
              </tr>
              <tr v-if="!pitfalls.length"><td colspan="3"><div class="empty"><div class="big">🗑</div>回收站暂无避坑项</div></td></tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
