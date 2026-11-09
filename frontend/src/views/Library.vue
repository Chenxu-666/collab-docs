<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { publicApi } from '@/api'

const albums = ref<any[]>([])
const images = ref<any[]>([])
const activeAlbum = ref(0)
const thumbs = ref<Record<number, string>>({})

const lb = ref(false)
const lbIndex = ref(0)
const lbUrl = ref('')

const filtered = computed(() =>
  activeAlbum.value === 0 ? images.value : images.value.filter((i) => i.album_id === activeAlbum.value)
)

async function load() {
  try {
    const [a, im] = await Promise.all([publicApi.get('/albums'), publicApi.get('/images')])
    albums.value = a.data
    images.value = im.data
    images.value.forEach((img: any) => loadThumb(img))
  } catch { /* ignore */ }
}

async function loadThumb(img: any) {
  try {
    const res = await publicApi.get(`/images/${img.id}/thumb`, { responseType: 'blob' })
    thumbs.value[img.id] = URL.createObjectURL(res.data)
  } catch { /* ignore */ }
}

async function openLb(i: number) {
  lbIndex.value = i
  lb.value = true
  lbUrl.value = ''
  const img = filtered.value[i]
  try {
    const res = await publicApi.get(`/images/${img.id}/file`, { responseType: 'blob' })
    lbUrl.value = URL.createObjectURL(res.data)
  } catch { /* ignore */ }
}
function stepLb(d: number) {
  const n = (lbIndex.value + d + filtered.value.length) % filtered.value.length
  openLb(n)
}

onMounted(load)
</script>

<template>
  <div class="page-anim">
    <div class="page-head">
      <div>
        <h2>图片库</h2>
        <div class="desc">装修参考图集中展示，点击查看大图</div>
      </div>
    </div>

    <div class="album-tabs">
      <button class="album-tab" :class="{ active: activeAlbum === 0 }" @click="activeAlbum = 0">全部</button>
      <button v-for="a in albums" :key="a.id" class="album-tab"
              :class="{ active: activeAlbum === a.id }" @click="activeAlbum = a.id">{{ a.name }}</button>
    </div>

    <div class="photo-grid">
      <div v-for="(img, i) in filtered" :key="img.id" class="ph-card" @click="openLb(i)">
        <div class="ph-thumb">
          <img v-if="thumbs[img.id]" :src="thumbs[img.id]" :alt="img.title" />
          <div v-else style="color:var(--muted);font-size:13px">加载中…</div>
        </div>
        <div class="ph-info"><span class="t">{{ img.title }}</span></div>
      </div>
    </div>
    <div v-if="!filtered.length" class="empty"><div class="big">🖼️</div>该相册暂无图片</div>

    <div v-if="lb" class="lightbox" @click.self="lb = false">
      <button class="lb-close" @click="lb = false">✕</button>
      <div class="lb-stage">
        <button class="lb-arrow lb-prev" @click="stepLb(-1)">‹</button>
        <img v-if="lbUrl" class="lb-img" :src="lbUrl" :alt="filtered[lbIndex]?.title" />
        <button class="lb-arrow lb-next" @click="stepLb(1)">›</button>
      </div>
      <div class="lb-cap">
        <b>{{ filtered[lbIndex]?.title }}</b>
        <span v-if="filtered[lbIndex]?.description">{{ filtered[lbIndex]?.description }} · </span>
        <span>{{ lbIndex + 1 }} / {{ filtered.length }}</span>
      </div>
    </div>
  </div>
</template>
