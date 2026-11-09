<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { publicApi } from '@/api'

const router = useRouter()
const q = ref('')
const docs = ref<any[]>([])
const images = ref<any[]>([])
const pitfalls = ref<any[]>([])
const thumbs = ref<Record<number, string>>({})

async function load() {
  try {
    const [d, im, p] = await Promise.allSettled([
      publicApi.get('/documents'), publicApi.get('/images'), publicApi.get('/pitfalls')
    ])
    if (d.status === 'fulfilled') docs.value = d.value.data.slice(0, 6)
    if (im.status === 'fulfilled') { images.value = im.value.data.slice(0, 8); images.value.forEach((img: any) => loadThumb(img)) }
    if (p.status === 'fulfilled') pitfalls.value = p.value.data.filter((x: any) => x.is_pinned).slice(0, 4)
  } catch { /* ignore */ }
}

async function loadThumb(img: any) {
  try {
    const res = await publicApi.get(`/images/${img.id}/thumb`, { responseType: 'blob' })
    thumbs.value[img.id] = URL.createObjectURL(res.data)
  } catch { /* ignore */ }
}

function search() {
  router.push({ path: '/docs', query: { q: q.value } })
}

function timeAgo(t: string) {
  const diff = Date.now() - new Date(t).getTime()
  if (diff < 86400000) return '今天更新'
  if (diff < 7 * 86400000) return Math.floor(diff / 86400000) + ' 天前'
  return new Date(t).toLocaleDateString('zh-CN')
}

onMounted(load)
</script>

<template>
  <div class="page-anim">
    <!-- Hero -->
    <section class="hero">
      <h1>把装修的经验，<br>沉淀成一套<span>看得懂</span>的资料</h1>
      <p>文档、参考图片、避坑经验三类内容集中共享，手机电脑随时查看，少走弯路。</p>
      <div class="search-bar">
        <input v-model="q" class="input" placeholder="搜索预算、验收、避坑经验…" @keyup.enter="search" />
        <button class="btn btn-primary" @click="search">搜索</button>
      </div>
    </section>

    <!-- 最新文档 -->
    <section v-if="docs.length" class="block">
      <div class="block-head">
        <h2>最新文档</h2>
        <button class="more" @click="router.push('/docs')">查看全部 →</button>
      </div>
      <div class="doc-grid">
        <div v-for="d in docs" :key="d.id" class="card card-hover doc-card" @click="router.push(`/docs/${d.id}`)">
          <div class="doc-ico">{{ d.ext.toUpperCase() }}</div>
          <div class="doc-title">{{ d.title }}</div>
          <div class="doc-sum">{{ d.summary || '装修资料文档' }}</div>
          <div class="doc-meta">{{ timeAgo(d.updated_at) }}</div>
        </div>
      </div>
    </section>

    <!-- 精选图片 -->
    <section v-if="images.length" class="block">
      <div class="block-head">
        <h2>精选图片</h2>
        <button class="more" @click="router.push('/library')">进入图片库 →</button>
      </div>
      <div class="img-strip">
        <div v-for="img in images" :key="img.id" class="img-item" @click="router.push('/library')">
          <img v-if="thumbs[img.id]" :src="thumbs[img.id]" :alt="img.title" />
          <span class="img-cap">{{ img.title }}</span>
        </div>
      </div>
    </section>

    <!-- 重点避坑 -->
    <section v-if="pitfalls.length" class="block">
      <div class="block-head">
        <h2>重点避坑项</h2>
        <button class="more" @click="router.push('/pitfalls')">查看全部 →</button>
      </div>
      <div class="pit-grid">
        <div v-for="p in pitfalls" :key="p.id" class="card card-hover pit-card" @click="router.push('/pitfalls')">
          <span class="badge" :class="p.risk_level === 'high' ? 'badge-red' : p.risk_level === 'medium' ? 'badge-amber' : 'badge-green'">
            {{ p.risk_level === 'high' ? '高风险' : p.risk_level === 'medium' ? '中风险' : '低风险' }}
          </span>
          <div class="pit-title">{{ p.title }}</div>
          <div class="pit-advice">{{ p.advice }}</div>
        </div>
      </div>
    </section>

    <div v-if="!docs.length && !images.length && !pitfalls.length" class="empty">
      <div class="big">🏠</div>暂无公开内容
    </div>
  </div>
</template>

<style scoped>
.hero { text-align: center; padding: 46px 20px 34px; }
.hero h1 { font-size: 34px; line-height: 1.35; letter-spacing: .5px; }
.hero h1 span { color: var(--primary); }
.hero p { color: var(--sub); margin: 16px auto 26px; max-width: 560px; font-size: 15px; }
.search-bar { max-width: 520px; margin: 0 auto; display: flex; gap: 10px; }
.search-bar .input { height: 46px; border-radius: 12px; }
.search-bar .btn { height: 46px; padding: 0 26px; border-radius: 12px; }
.block { margin-top: 34px; }
.block-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.block-head h2 { font-size: 19px; }
.more { color: var(--primary); font-size: 13.5px; border: none; background: none; cursor: pointer; }
.more:hover { text-decoration: underline; }
.doc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.doc-card { padding: 20px; cursor: pointer; }
.doc-ico {
  width: 42px; height: 42px; border-radius: 10px; background: var(--primary-soft);
  color: var(--primary); font-weight: 700; font-size: 11px; display: flex;
  align-items: center; justify-content: center; margin-bottom: 14px;
}
.doc-title { font-weight: 600; font-size: 15.5px; margin-bottom: 6px; }
.doc-sum { color: var(--sub); font-size: 13px; line-height: 1.6; height: 42px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.doc-meta { color: var(--muted); font-size: 12px; margin-top: 12px; }
.img-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.img-item { position: relative; border-radius: 12px; overflow: hidden; cursor: pointer; aspect-ratio: 4/3; }
.img-item img { width: 100%; height: 100%; object-fit: cover; transition: transform .4s var(--ease); }
.img-item:hover img { transform: scale(1.06); }
.img-cap { position: absolute; left: 0; right: 0; bottom: 0; padding: 22px 12px 10px; color: #fff; font-size: 13px; background: linear-gradient(transparent, rgba(0,0,0,.6)); }
.pit-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.pit-card { padding: 20px; cursor: pointer; }
.pit-title { font-weight: 600; font-size: 15.5px; margin: 12px 0 8px; }
.pit-advice { color: var(--sub); font-size: 13.5px; line-height: 1.65; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
@media (max-width: 768px) {
  .hero h1 { font-size: 26px; }
  .img-strip { grid-template-columns: repeat(2, 1fr); }
}
</style>
