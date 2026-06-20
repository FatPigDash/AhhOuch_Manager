<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import html2canvas from 'html2canvas'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const card = ref(null)
const error = ref('')
const fileInput = ref(null)
const showPublish = ref(false)
const lightboxUrl = ref(null)
const variant = ref('full') // full | short
const publishNode = ref(null)
const copied = ref(false)
const targets = ref([])
const sendMsg = ref('')

const introText = computed(() =>
  card.value ? (variant.value === 'full' ? card.value.full_intro : card.value.short_intro) : ''
)

async function load() {
  try { card.value = await api.getStoreCard(props.id) } catch (e) { error.value = e.message }
}
function goBack() { router.push({ name: 'store-list' }) }

async function saveCard(fields) {
  try { await api.updateStoreCard(props.id, fields) } catch (e) { error.value = e.message }
}
function saveName() {
  const n = card.value.name.trim()
  if (n) saveCard({ name: n })
}

// --- 圖片 (S3) ---
async function onFiles(e) {
  for (const file of e.target.files) {
    try { await api.uploadStoreImage(props.id, file) } catch (err) { error.value = err.message }
  }
  e.target.value = ''
  await load()
}
function onPaste(e) {
  const items = e.clipboardData?.items || []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = async () => {
        try { await api.pasteStoreImage(props.id, reader.result); await load() }
        catch (err) { error.value = err.message }
      }
      reader.readAsDataURL(item.getAsFile())
      e.preventDefault()
      return
    }
  }
}
async function setCover(img) {
  try { await api.setStoreCover(img.id); await load() } catch (e) { error.value = e.message }
}
async function removeImage(img) {
  if (!confirm('刪除這張圖片？')) return
  try { await api.deleteStoreImage(img.id); await load() } catch (e) { error.value = e.message }
}

// --- 發布 (S5) ---
async function openPublish() {
  showPublish.value = true
  copied.value = false
  sendMsg.value = ''
  try { targets.value = (await api.listTargets()).filter((t) => t.enabled) } catch (_) { /* 忽略 */ }
}
async function sendToTarget(t) {
  sendMsg.value = `發布到「${t.name}」中…`
  try {
    const { text } = await api.publishText(props.id, variant.value)
    await api.sendPublish(t.id, text)
    sendMsg.value = `✓ 已發布到「${t.name}」`
  } catch (e) { sendMsg.value = `✗ ${e.message}` }
}
async function copyText() {
  try {
    const { text } = await api.publishText(props.id, variant.value)
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch (e) { error.value = '複製失敗：' + e.message }
}
async function downloadImage() {
  if (!publishNode.value) return
  try {
    const canvas = await html2canvas(publishNode.value, { backgroundColor: '#ffffff', scale: 2 })
    canvas.toBlob((blob) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${card.value.name}_${variant.value === 'full' ? '完整' : '簡短'}.png`
      a.click()
      URL.revokeObjectURL(a.href)
    })
  } catch (e) { error.value = '產生圖片失敗：' + e.message }
}

onMounted(() => {
  load()
  window.addEventListener('paste', onPaste)
})
onBeforeUnmount(() => window.removeEventListener('paste', onPaste))
</script>

<template>
  <section v-if="card" class="detail">
    <div class="page-head">
      <button class="back" @click="goBack">← 返回列表</button>
      <input class="title-input" v-model="card.name" @blur="saveName" />
      <button class="primary publish-btn" @click="openPublish">📤 發布</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="panel">
      <div class="panel-body">
        <div class="images">
          <div v-for="img in card.images" :key="img.id" class="img-cell" :class="{ cover: img.is_cover }" style="cursor:zoom-in" @click="lightboxUrl = img.url">
            <img :src="img.url" alt="" />
            <span v-if="img.is_cover" class="cover-badge">封面</span>
            <div class="img-actions" @click.stop>
              <button v-if="!img.is_cover" @click="setCover(img)" title="設為封面">★</button>
              <button @click="removeImage(img)" title="刪除">✕</button>
            </div>
          </div>
          <div v-if="card.images.length === 0" class="img-empty">尚無圖片（非必填）</div>
        </div>
        <div class="img-add">
          <button class="ghost" @click="fileInput.click()">⬆ 上傳圖片</button>
          <span class="hint">或在本頁按 Ctrl+V 貼上剪貼簿圖片</span>
          <input ref="fileInput" type="file" accept="image/*" multiple hidden @change="onFiles" />
        </div>

        <label class="field">
          <span>完整介紹</span>
          <textarea v-model="card.full_intro" rows="4" @blur="saveCard({ full_intro: card.full_intro })"></textarea>
        </label>
        <label class="field">
          <span>簡短介紹</span>
          <textarea v-model="card.short_intro" rows="2" @blur="saveCard({ short_intro: card.short_intro })"></textarea>
        </label>
      </div>
    </div>

    <!-- 燈箱 -->
    <div v-if="lightboxUrl" class="lightbox-backdrop" @click.self="lightboxUrl = null">
      <div class="lightbox-box">
        <button class="lightbox-close" @click="lightboxUrl = null">✕</button>
        <img :src="lightboxUrl" alt="" />
      </div>
    </div>

    <!-- 發布視窗 (S5) -->
    <div v-if="showPublish" class="modal-backdrop" @click.self="showPublish = false">
      <div class="modal">
        <header class="modal-head">
          <h2>發布到群組</h2>
          <button class="x" @click="showPublish = false">✕</button>
        </header>

        <div class="variant-pills">
          <span class="label">介紹版本</span>
          <button class="pill" :class="{ active: variant === 'full' }" @click="variant = 'full'">
            <span v-if="variant === 'full'">✓</span> 完整介紹
          </button>
          <button class="pill" :class="{ active: variant === 'short' }" @click="variant = 'short'">
            <span v-if="variant === 'short'">✓</span> 簡短介紹
          </button>
        </div>

        <!-- 排版圖片來源（html2canvas 會擷取此區） -->
        <div class="publish-preview" ref="publishNode">
          <img v-if="card.cover_image" :src="card.cover_image" class="pub-cover" alt="" />
          <div class="pub-name">{{ card.name }}</div>
          <div class="pub-intro">{{ introText || '（尚未填寫此版本介紹）' }}</div>
        </div>

        <div class="modal-actions">
          <button class="ghost" @click="copyText">{{ copied ? '✓ 已複製文字' : '📋 複製純文字' }}</button>
          <button class="primary" @click="downloadImage">🖼 下載排版圖片</button>
        </div>

        <div v-if="targets.length" class="auto-publish">
          <span class="ap-label">自動發布到：</span>
          <button v-for="t in targets" :key="t.id" class="chip-btn" @click="sendToTarget(t)">📤 {{ t.name }}</button>
        </div>
        <p v-if="sendMsg" class="hint center">{{ sendMsg }}</p>

        <p class="hint center">產生後手動貼到群組；或設定發布目標後一鍵自動發布。</p>
      </div>
    </div>
  </section>
  <p v-else-if="error" class="error">{{ error }}</p>
</template>

<style scoped>
.detail { max-width: 760px; }
.page-head { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.back { background: #e4e7eb; border: none; border-radius: 8px; padding: 6px 12px; color: #334e68; }
.title-input { flex: 1; font-size: 1.4rem; font-weight: 700; border: 1px solid transparent; border-radius: 8px; padding: 4px 8px; }
.title-input:hover, .title-input:focus { border-color: #cbd2d9; outline: none; }
.publish-btn { white-space: nowrap; }
.error { color: #cf1124; }
.hint { color: #829ab1; font-size: 0.85rem; }
.hint.center { text-align: center; }

.panel { background: #fff; border: 1px solid #e4e7eb; border-radius: 12px; }
.panel-body { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.images { display: flex; flex-wrap: wrap; gap: 10px; }
.img-cell { position: relative; width: 120px; height: 120px; border-radius: 8px; overflow: hidden; border: 2px solid #e4e7eb; }
.img-cell.cover { border-color: #2680c2; }
.img-cell img { width: 100%; height: 100%; object-fit: cover; }
.cover-badge { position: absolute; top: 4px; left: 4px; background: #2680c2; color: #fff; font-size: 0.7rem; padding: 1px 6px; border-radius: 999px; }
.img-actions { position: absolute; bottom: 4px; right: 4px; display: flex; gap: 4px; }
.img-actions button { border: none; border-radius: 6px; background: rgba(0,0,0,0.55); color: #fff; width: 24px; height: 24px; }
.img-empty { color: #9fb3c8; font-size: 0.85rem; padding: 8px 0; }
.img-add { display: flex; align-items: center; gap: 10px; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; color: #486581; }
.field textarea { padding: 8px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; resize: vertical; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(16,42,67,0.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: #fff; border-radius: 14px; width: 420px; max-width: 92vw; max-height: 90vh; overflow-y: auto; padding: 18px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.modal-head h2 { margin: 0; font-size: 1.15rem; }
.modal-head .x { border: none; background: #e4e7eb; border-radius: 8px; width: 30px; height: 30px; }
.variant-pills { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.variant-pills .label { font-size: 0.85rem; color: #627d98; }
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border: 1px solid #cbd2d9; border-radius: 999px; background: #fff; color: #627d98; }
.pill.active { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }
.publish-preview { border: 1px solid #e4e7eb; border-radius: 12px; padding: 16px; background: #fff; }
.pub-cover { width: 100%; max-height: 260px; object-fit: cover; border-radius: 8px; margin-bottom: 10px; }
.pub-name { font-size: 1.3rem; font-weight: 700; margin-bottom: 6px; }
.pub-intro { white-space: pre-wrap; line-height: 1.6; color: #243b53; }
.modal-actions { display: flex; gap: 10px; margin: 16px 0 6px; }
.modal-actions button { flex: 1; padding: 9px; border: none; border-radius: 8px; }
.auto-publish { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 6px; padding-top: 10px; border-top: 1px solid #f0f2f5; }
.ap-label { font-size: 0.85rem; color: #627d98; }
.chip-btn { border: 1px solid #2680c2; color: #0a558c; background: #e3f0fb; border-radius: 999px; padding: 5px 12px; font-size: 0.85rem; }
button.ghost { background: #e4e7eb; color: #334e68; }
button.primary { background: #2680c2; color: #fff; }

.lightbox-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.82); display: flex; align-items: center; justify-content: center; z-index: 100; }
.lightbox-box { position: relative; max-width: 90vw; max-height: 90vh; }
.lightbox-box img { display: block; max-width: 90vw; max-height: 90vh; border-radius: 8px; object-fit: contain; }
.lightbox-close { position: absolute; top: -14px; right: -14px; width: 32px; height: 32px; border-radius: 50%; border: none; background: #fff; color: #334e68; font-size: 1rem; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 1; }
.lightbox-close:hover { background: #cf1124; color: #fff; }
</style>
