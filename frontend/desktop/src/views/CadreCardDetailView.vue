<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import html2canvas from 'html2canvas'
import { api } from '../api'
import { canShare, canShareFiles, share, urlsToFiles } from '../share'
import { sendCard as tgSendCard } from '../telegram'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

// 文字框自動長高：高度貼齊內容、完整顯示，移除垂直捲軸。
function resizeTextarea(el) {
  // 量測前先把高度歸零會讓文字框瞬間縮短，導致頁面捲動位置被瀏覽器夾回頂端；
  // 先記住目前捲動位置，調整完高度後立刻還原，避免編輯時畫面跳到上方。
  const x = window.scrollX
  const y = window.scrollY
  el.style.height = 'auto'
  // scrollHeight 不含邊框；box-sizing: border-box 時需補上邊框，否則內容會被裁掉幾像素。
  const s = getComputedStyle(el)
  const border = s.boxSizing === 'border-box'
    ? parseFloat(s.borderTopWidth) + parseFloat(s.borderBottomWidth)
    : 0
  el.style.height = `${el.scrollHeight + border}px`
  el._lastResizeValue = el.value
  window.scrollTo(x, y)
}
const vAutoresize = {
  mounted(el) {
    el.addEventListener('input', () => resizeTextarea(el))
    nextTick(() => resizeTextarea(el))
  },
  updated(el) {
    // 只有「這個欄位自己的內容」真的改變時才重新量高。
    // 否則編輯其他欄位（如簡短介紹、資訊訊息連結）也會觸發 updated，
    // 連帶把較高的完整介紹框瞬間縮回去再撐開，造成畫面往上跳。
    if (el.value !== el._lastResizeValue) nextTick(() => resizeTextarea(el))
  },
}

const card = ref(null)
const saved = ref(null)   // 最後一次已儲存的文字欄位快照，用於判斷是否有未儲存變更
const error = ref('')
const savedMsg = ref('')
const fileInput = ref(null)
const cameraInput = ref(null)
const busy = ref(false)        // 圖片處理中（壓縮/縮圖需要時間）
const showPublish = ref(false)
const lightboxUrl = ref(null)
const variant = ref('full') // full | short
const publishNode = ref(null)
const copied = ref(false)
const includePhotos = ref(true)   // C4：是否連同照片一起發出
const shareNotice = ref('')       // 分享狀態提示（降級／取消等）
const shareSupported = canShare()
const targets = ref([])           // Telegram 發布目標（啟用中）
const tgNotice = ref('')          // Telegram 發送狀態
const tgSending = ref(false)

const introText = computed(() =>
  card.value ? (variant.value === 'full' ? card.value.full_intro : card.value.short_intro) : ''
)

// 是否有尚未儲存的文字欄位變更（名字 / 完整介紹 / 簡短介紹）。
const dirty = computed(() =>
  !!card.value && !!saved.value && (
    card.value.name !== saved.value.name ||
    card.value.full_intro !== saved.value.full_intro ||
    card.value.short_intro !== saved.value.short_intro ||
    card.value.info_link !== saved.value.info_link
  )
)

function snapshot() {
  saved.value = {
    name: card.value.name,
    full_intro: card.value.full_intro,
    short_intro: card.value.short_intro,
    info_link: card.value.info_link,
  }
}

async function load() {
  try {
    card.value = await api.getCadreCard(props.id)
    snapshot()
  } catch (e) { error.value = e.message }
}
function goBack() { router.push({ name: 'cadre-list' }) }

// 儲存：把目前文字欄位一次寫回後端。
async function save() {
  const name = card.value.name.trim()
  if (!name) { error.value = '名字不可空白'; return }
  try {
    await api.updateCadreCard(props.id, {
      name,
      full_intro: card.value.full_intro,
      short_intro: card.value.short_intro,
      info_link: card.value.info_link,
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
    const fresh = await api.getCadreCard(props.id)
    card.value.images = fresh.images
    card.value.cover_image = fresh.cover_image
  } catch (e) { error.value = e.message }
}
// 相簿選圖 / 拍照（手機）/ 檔案上傳 — 共用同一處理流程。
async function onFiles(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  busy.value = true
  try {
    for (const file of files) {
      try { await api.uploadCadreImage(props.id, file) } catch (err) { error.value = err.message }
    }
    await reloadImages()
  } finally { busy.value = false }
}
// 桌面：在本頁按 Ctrl+V 貼上剪貼簿圖片。
async function onPaste(e) {
  const items = e.clipboardData?.items || []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      busy.value = true
      try { await api.uploadCadreImage(props.id, file); await reloadImages() }
      catch (err) { error.value = err.message }
      finally { busy.value = false }
      return
    }
  }
}
// 手機：以按鈕讀取剪貼簿圖片（iOS Safari / Android Chrome 支援 navigator.clipboard.read）。
async function pasteFromClipboard() {
  if (!navigator.clipboard?.read) {
    error.value = '此瀏覽器不支援讀取剪貼簿，請改用「上傳圖片」或在桌面按 Ctrl+V。'
    return
  }
  busy.value = true
  try {
    const items = await navigator.clipboard.read()
    let added = false
    for (const item of items) {
      const type = item.types.find(t => t.startsWith('image/'))
      if (type) {
        const blob = await item.getType(type)
        await api.uploadCadreImage(props.id, blob)
        added = true
      }
    }
    if (added) { await reloadImages(); error.value = '' }
    else error.value = '剪貼簿中沒有圖片。'
  } catch (err) {
    error.value = '讀取剪貼簿失敗：' + err.message
  } finally { busy.value = false }
}
async function setCover(img) {
  try { await api.setCadreCover(img.id); await reloadImages() } catch (e) { error.value = e.message }
}
async function removeImage(img) {
  if (!confirm('刪除這張圖片？')) return
  try { await api.deleteCadreImage(img.id); await reloadImages() } catch (e) { error.value = e.message }
}

// --- 發布 (S5) ---
async function openPublish() {
  if (dirty.value) {
    if (!confirm('發布前需先儲存目前的變更，要儲存並繼續嗎？')) return
    await save()
    if (dirty.value) return
  }
  showPublish.value = true
  copied.value = false
  shareNotice.value = ''
  tgNotice.value = ''
  try { targets.value = (await api.listTargets()).filter(t => t.enabled) } catch (_) { targets.value = [] }
}
// 發送到 Telegram（純前端直連）。沿用發布視窗的介紹版本與「連同照片」選項。
async function sendToTelegram(target) {
  tgNotice.value = ''
  tgSending.value = true
  try {
    const { text } = await api.publishText(props.id, variant.value)
    let files = []
    if (includePhotos.value && card.value.images.length) {
      files = await urlsToFiles(card.value.images.map(i => i.url), card.value.name || 'card')
    }
    await tgSendCard(target.token, target.target_id, files, text)
    tgNotice.value = `✓ 已發送到「${target.name}」`
  } catch (e) {
    tgNotice.value = `發送到「${target.name}」失敗：${e.message}`
  } finally { tgSending.value = false }
}
// C4/C5：透過 Web Share API 發布卡片（文字＋可選照片）至 LINE 等。
async function shareCard() {
  shareNotice.value = ''
  try {
    const { text } = await api.publishText(props.id, variant.value)
    let files = []
    if (includePhotos.value && card.value.images.length) {
      files = await urlsToFiles(card.value.images.map(i => i.url), card.value.name || 'card')
      // §6.2 降級：裝置不支援檔案分享時，退為純文字並提示。
      if (files.length && !canShareFiles(files)) {
        files = []
        shareNotice.value = '此裝置無法透過系統分享圖片，已改為分享純文字；圖片可用「下載排版圖片」另存後手動傳送。'
      }
    }
    const result = await share({ title: card.value.name, text, files })
    if (result === 'unsupported') {
      shareNotice.value = '此裝置不支援系統分享，請改用「複製純文字」或「下載排版圖片」。'
    }
  } catch (e) { shareNotice.value = '分享失敗：' + e.message }
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
    <p class="page-subtitle">美容師資訊編輯頁面</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="panel">
      <div class="panel-body">
        <div class="images">
          <div v-for="img in card.images" :key="img.id" class="img-cell" :class="{ cover: img.is_cover }" style="cursor:zoom-in" @click="lightboxUrl = img.url">
            <img :src="img.thumb_url || img.url" alt="" />
            <span v-if="img.is_cover" class="cover-badge">封面</span>
            <div class="img-actions" @click.stop>
              <button v-if="!img.is_cover" @click="setCover(img)" title="設為封面">★</button>
              <button @click="removeImage(img)" title="刪除">✕</button>
            </div>
          </div>
          <div v-if="card.images.length === 0" class="img-empty">尚無圖片（非必填）</div>
        </div>
        <div class="img-add">
          <button class="ghost" :disabled="busy" @click="fileInput.click()">⬆ 上傳圖片</button>
          <button class="ghost" :disabled="busy" @click="cameraInput.click()">📷 拍照</button>
          <button class="ghost" :disabled="busy" @click="pasteFromClipboard">📋 貼上</button>
          <span v-if="busy" class="hint">處理圖片中…</span>
          <span v-else class="hint">桌面亦可按 Ctrl+V 貼上</span>
          <input ref="fileInput" type="file" accept="image/*" multiple hidden @change="onFiles" />
          <input ref="cameraInput" type="file" accept="image/*" capture="environment" hidden @change="onFiles" />
        </div>

        <label class="field">
          <span>完整介紹</span>
          <textarea v-model="card.full_intro" v-autoresize rows="4"></textarea>
        </label>
        <label class="field">
          <span>簡短介紹</span>
          <textarea v-model="card.short_intro" v-autoresize rows="2"></textarea>
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

        <!-- C4：是否連同照片一起發出 -->
        <label v-if="card.images.length" class="photo-toggle">
          <input type="checkbox" v-model="includePhotos" />
          連同照片一起發出（{{ card.images.length }} 張）
        </label>

        <!-- 排版圖片來源（html2canvas 會擷取此區） -->
        <div class="publish-preview" ref="publishNode">
          <img v-if="card.cover_image" :src="card.cover_image" class="pub-cover" alt="" />
          <div class="pub-name">{{ card.name }}</div>
          <div class="pub-intro">{{ introText || '（尚未填寫此版本介紹）' }}</div>
        </div>

        <button v-if="shareSupported" class="primary share-main" @click="shareCard">
          📤 分享至 LINE 等
        </button>
        <p v-if="shareNotice" class="hint center notice">{{ shareNotice }}</p>

        <!-- 一鍵發送到 Telegram（依「發布設定」的目標） -->
        <div v-if="targets.length" class="tg-section">
          <span class="tg-label">發送到 Telegram</span>
          <button v-for="t in targets" :key="t.id" class="tg-btn" :disabled="tgSending" @click="sendToTelegram(t)">
            ✈ {{ t.name }}
          </button>
        </div>
        <p v-if="tgNotice" class="hint center notice">{{ tgNotice }}</p>

        <div class="modal-actions">
          <button class="ghost" @click="copyText">{{ copied ? '✓ 已複製文字' : '📋 複製純文字' }}</button>
          <button class="ghost" @click="downloadImage">🖼 下載排版圖片</button>
        </div>

        <p class="hint center">{{ shareSupported ? '「分享」會開啟系統選單；亦可改用複製文字或下載圖片手動貼到群組。' : '此裝置不支援系統分享，請用複製文字或下載圖片手動貼到群組。' }}</p>
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
.page-subtitle { margin: 4px 0 0; color: #627d98; font-size: 0.9rem; }
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
.img-add { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.img-add button:disabled { opacity: 0.5; cursor: not-allowed; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; color: #486581; }
.field textarea { padding: 8px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; resize: none; overflow-y: hidden; line-height: 1.5; }
.field input { padding: 8px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; }

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
.photo-toggle { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 0.9rem; color: #334e68; }
.photo-toggle input { width: 16px; height: 16px; }
.share-main { display: block; width: 100%; padding: 11px; border: none; border-radius: 8px; margin: 16px 0 6px; font-size: 1rem; }
.notice { color: #b7791f; }
.tg-section { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 6px; padding-top: 10px; border-top: 1px solid #f0f2f5; }
.tg-label { font-size: 0.85rem; color: #627d98; }
.tg-btn { border: 1px solid #2680c2; color: #0a558c; background: #e3f0fb; border-radius: 999px; padding: 5px 14px; font-size: 0.9rem; }
.tg-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-actions { display: flex; gap: 10px; margin: 10px 0 6px; }
.modal-actions button { flex: 1; padding: 9px; border: none; border-radius: 8px; }
.auto-publish { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 6px; padding-top: 10px; border-top: 1px solid #f0f2f5; }
.ap-label { font-size: 0.85rem; color: #627d98; }
.chip-btn { border: 1px solid #2680c2; color: #0a558c; background: #e3f0fb; border-radius: 999px; padding: 5px 12px; font-size: 0.85rem; }

/* 自動發布：選擇內容視窗 */
.ap-section-label { font-size: 0.85rem; color: #627d98; margin: 12px 0 6px; }
.ap-choices { display: flex; flex-wrap: wrap; gap: 16px; }
.ap-check { display: inline-flex; align-items: center; gap: 6px; font-size: 0.95rem; color: #243b53; }
.ap-check input { width: 16px; height: 16px; }
.ap-check input:disabled + * { color: #9fb3c8; }
.ap-img-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.ap-img-cell { position: relative; width: 80px; height: 80px; padding: 0; border: 2px solid #cbd2d9; border-radius: 8px; overflow: hidden; cursor: pointer; background: none; }
.ap-img-cell.on { border-color: #2680c2; }
.ap-img-cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ap-img-cell:not(.on) img { opacity: 0.55; }
.ap-img-tick { position: absolute; top: 3px; right: 3px; width: 20px; height: 20px; border-radius: 50%; background: #2680c2; color: #fff; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; }
.ap-preview { border: 1px solid #e4e7eb; border-radius: 12px; padding: 12px; background: #f7f9fb; }
.ap-preview-imgs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.ap-preview-imgs img { width: 96px; height: 96px; object-fit: cover; border-radius: 8px; }
.ap-preview-text { white-space: pre-wrap; line-height: 1.6; color: #243b53; margin: 0; font-family: inherit; font-size: 0.95rem; }
button.ghost { background: #e4e7eb; color: #334e68; }
button.primary { background: #2680c2; color: #fff; }

@media (max-width: 640px) {
  .detail { max-width: 100%; }
  .page-head { gap: 8px; }
  .title-input { font-size: 1.1rem; min-width: 0; }
  .img-add { flex-wrap: wrap; }
  .img-add .hint { width: 100%; }
  .action-bar { flex-wrap: wrap; gap: 10px; }
  .action-right { flex-wrap: wrap; }
  .action-bar button { flex: 1; min-width: 80px; }
}

.lightbox-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.82); display: flex; align-items: center; justify-content: center; z-index: 100; }
.lightbox-box { position: relative; max-width: 90vw; max-height: 90vh; }
.lightbox-box img { display: block; max-width: 90vw; max-height: 90vh; border-radius: 8px; object-fit: contain; }
.lightbox-close { position: absolute; top: -14px; right: -14px; width: 32px; height: 32px; border-radius: 50%; border: none; background: #fff; color: #334e68; font-size: 1rem; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 1; }
.lightbox-close:hover { background: #cf1124; color: #fff; }
</style>
