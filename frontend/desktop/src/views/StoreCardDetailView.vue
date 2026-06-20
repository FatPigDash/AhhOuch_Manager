<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import html2canvas from 'html2canvas'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const card = ref(null)
const saved = ref(null)   // 最後一次已儲存的文字欄位快照，用於判斷是否有未儲存變更
const error = ref('')
const savedMsg = ref('')
const fileInput = ref(null)
const showPublish = ref(false)
const lightboxUrl = ref(null)
const variant = ref('full') // full | short
const publishNode = ref(null)
const copied = ref(false)
const targets = ref([])
const sendMsg = ref('')

// 發布目標按鈕顯示「平台 名稱」，如「Telegram 111」。
const PLATFORM_LABEL = { telegram: 'Telegram', x: 'X' }
function platformLabel(p) { return PLATFORM_LABEL[p] || p || '' }

const introText = computed(() =>
  card.value ? (variant.value === 'full' ? card.value.full_intro : card.value.short_intro) : ''
)

// 是否有尚未儲存的文字欄位變更（名字 / 完整介紹 / 簡短介紹）。
const dirty = computed(() =>
  !!card.value && !!saved.value && (
    card.value.name !== saved.value.name ||
    card.value.full_intro !== saved.value.full_intro ||
    card.value.short_intro !== saved.value.short_intro
  )
)

function snapshot() {
  saved.value = {
    name: card.value.name,
    full_intro: card.value.full_intro,
    short_intro: card.value.short_intro,
  }
}

async function load() {
  try {
    card.value = await api.getStoreCard(props.id)
    snapshot()
  } catch (e) { error.value = e.message }
}
function goBack() { router.push({ name: 'store-list' }) }

// 儲存：把目前文字欄位一次寫回後端。
async function save() {
  const name = card.value.name.trim()
  if (!name) { error.value = '名字不可空白'; return }
  try {
    await api.updateStoreCard(props.id, {
      name,
      full_intro: card.value.full_intro,
      short_intro: card.value.short_intro,
    })
    card.value.name = name
    snapshot()
    error.value = ''
    savedMsg.value = '✓ 已儲存'
    setTimeout(() => (savedMsg.value = ''), 2000)
  } catch (e) { error.value = e.message }
}

// 取消：回到列表（若有未儲存變更，由路由守衛跳出確認）。
function cancel() { goBack() }

// --- 圖片 (S3) ---
// 圖片為即時存檔；只刷新圖片欄位，保留尚未儲存的文字編輯。
async function reloadImages() {
  try {
    const fresh = await api.getStoreCard(props.id)
    card.value.images = fresh.images
    card.value.cover_image = fresh.cover_image
  } catch (e) { error.value = e.message }
}
async function onFiles(e) {
  for (const file of e.target.files) {
    try { await api.uploadStoreImage(props.id, file) } catch (err) { error.value = err.message }
  }
  e.target.value = ''
  await reloadImages()
}
function onPaste(e) {
  const items = e.clipboardData?.items || []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = async () => {
        try { await api.pasteStoreImage(props.id, reader.result); await reloadImages() }
        catch (err) { error.value = err.message }
      }
      reader.readAsDataURL(item.getAsFile())
      e.preventDefault()
      return
    }
  }
}
async function setCover(img) {
  try { await api.setStoreCover(img.id); await reloadImages() } catch (e) { error.value = e.message }
}
async function removeImage(img) {
  if (!confirm('刪除這張圖片？')) return
  try { await api.deleteStoreImage(img.id); await reloadImages() } catch (e) { error.value = e.message }
}

// --- 發布 (S5) ---
async function openPublish() {
  // 發布內容取自後端已儲存的資料；若有未儲存變更，先儲存再發布。
  if (dirty.value) {
    if (!confirm('發布前需先儲存目前的變更，要儲存並繼續嗎？')) return
    await save()
    if (dirty.value) return  // 儲存失敗（如名字空白）則中止
  }
  showPublish.value = true
  copied.value = false
  sendMsg.value = ''
  try { targets.value = (await api.listTargets()).filter((t) => t.enabled) } catch (_) { /* 忽略 */ }
}
async function sendToTarget(t) {
  // 發送前先確認，避免不小心點到就發出去。
  if (!confirm(`確定要發布到「${platformLabel(t.platform)} ${t.name}」嗎？`)) return
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

// 路由切換離開（返回列表 / 取消 / 切換頁面）：有未儲存變更時跳確認。
onBeforeRouteLeave(() => {
  if (dirty.value) {
    return window.confirm('尚未儲存變更，確定要離開嗎？未儲存的內容將會遺失。')
  }
  return true
})

// 瀏覽器關閉 / 重新整理：有未儲存變更時由瀏覽器跳原生確認。
function onBeforeUnload(e) {
  if (dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  load()
  window.addEventListener('paste', onPaste)
  window.addEventListener('beforeunload', onBeforeUnload)
})
onBeforeUnmount(() => {
  window.removeEventListener('paste', onPaste)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<template>
  <section v-if="card" class="detail">
    <div class="page-head">
      <button class="back" @click="goBack">← 返回列表</button>
      <input class="title-input" v-model="card.name" />
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
          <textarea v-model="card.full_intro" rows="4"></textarea>
        </label>
        <label class="field">
          <span>簡短介紹</span>
          <textarea v-model="card.short_intro" rows="2"></textarea>
        </label>
      </div>
    </div>

    <!-- 底部動作列：左下發布、右下取消／儲存 -->
    <div class="action-bar">
      <button class="primary publish-btn" @click="openPublish">📤 發布</button>
      <div class="action-right">
        <span v-if="savedMsg" class="saved-msg">{{ savedMsg }}</span>
        <span v-else-if="dirty" class="dirty-msg">● 尚未儲存</span>
        <button class="ghost" @click="cancel">取消</button>
        <button class="primary" :disabled="!dirty" @click="save">💾 儲存</button>
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
          <button v-for="t in targets" :key="t.id" class="chip-btn" @click="sendToTarget(t)">📤 {{ platformLabel(t.platform) }} {{ t.name }}</button>
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
.action-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; }
.action-right { display: flex; align-items: center; gap: 10px; }
.saved-msg { color: #2f855a; font-size: 0.85rem; }
.dirty-msg { color: #b7791f; font-size: 0.85rem; }
.action-bar button { padding: 8px 18px; border: none; border-radius: 8px; }
.action-bar button:disabled { opacity: 0.5; cursor: not-allowed; }
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
