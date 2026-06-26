<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import html2canvas from 'html2canvas'
import { api } from '../api'
import { canShare, share } from '../share'
import { sendText as tgSendText } from '../telegram'
import TextTemplateBar from '../components/TextTemplateBar.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const schedule = ref(null)
const cadreCards = ref([])
const error = ref('')

const manualInput = reactive({})   // { [entryId]: 輸入字串 }
const autoStartInput = reactive({}) // { [entryId]: 上班時間 }
const computedShifts = reactive({}) // { [entryId]: [slot,...] }

const showPublish = ref(false)
const publishText = ref('')
const publishHtml = ref('')
const publishNode = ref(null)
const copied = ref(false)
const shareNotice = ref('')
const shareSupported = canShare()
const targets = ref([])      // Telegram 發布目標（啟用中）
const tgNotice = ref('')
const tgSending = ref(false)

async function load() {
  try {
    schedule.value = await api.getSchedule(props.id)
    await restoreShiftGrids()
    // 載入後讓既有時段 pill 即依時間序顯示；僅前端排序，下次變更才寫回 DB。
    for (const entry of schedule.value.entries) {
      entry.slots = sortedSlots(entry.slots)
    }
  } catch (e) { error.value = e.message }
}
// 換算紀錄保留：已存過上班時間（auto_start）的人員，載入時依該時間重算出班次格，
// 讓下次編輯不必再按一次「換算班次」就能直接從紀錄勾選。
async function restoreShiftGrids() {
  for (const entry of schedule.value.entries) {
    if (!entry.auto_start) continue
    autoStartInput[entry.id] = entry.auto_start  // 同步輸入框，顯示上次的上班時間
    try {
      const { slots } = await api.shiftSlots(entry.auto_start)
      computedShifts[entry.id] = slots
    } catch (_) { /* 換算失敗就略過，使用者可再手動換算 */ }
  }
}
async function loadCards() {
  try { cadreCards.value = await api.listCadreCards() } catch (e) { error.value = e.message }
}
function goBack() { router.push({ name: 'schedule-list' }) }

// 標題 (S6)
function saveTitle() {
  api.updateSchedule(props.id, { title: schedule.value.title }).catch((e) => (error.value = e.message))
}

// 結語：發布時置於最下方，編輯方式與標題相同
function saveFooter() {
  api.updateSchedule(props.id, { footer: schedule.value.footer }).catch((e) => (error.value = e.message))
}

// 套用文字模板：以模板內容覆蓋欄位並立即存檔。
function applyTitleTemplate(content) {
  schedule.value.title = content
  saveTitle()
}
function applyFooterTemplate(content) {
  schedule.value.footer = content
  saveFooter()
}

// 日期：用原生小日曆挑選，存 ISO（YYYY-MM-DD）；顯示/發布格式為 2026/06/21 (日)。
const WEEKDAY_TW = ['日', '一', '二', '三', '四', '五', '六'] // JS getDay(): 0=週日
function formatDate(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  const wd = WEEKDAY_TW[new Date(y, m - 1, d).getDay()]
  const p = (n) => String(n).padStart(2, '0')
  return `${y}/${p(m)}/${p(d)} (${wd})`
}
function saveDate() {
  api.updateSchedule(props.id, { date: schedule.value.date || '' }).catch((e) => (error.value = e.message))
}

// 出勤人員 (S7/S8)
function isAttending(cardId) {
  return schedule.value.entries.some((e) => e.cadre_card_id === cardId)
}
async function toggleAttend(card) {
  const entry = schedule.value.entries.find((e) => e.cadre_card_id === card.id)
  try {
    if (entry) await api.deleteEntry(entry.id)
    else await api.addEntry(schedule.value.id, card.id)
    await load()
  } catch (e) { error.value = e.message }
}

// 時段共用
// 時段 pill 一律依時間序排列，規則只看 pill 的時間本身，不分手動輸入或自動換算模式。
// 跨午夜班次處理：把各時段視為 24 小時圓環上的點，找出最大的空檔（含跨午夜回繞），
// 班次即從該空檔之後的時段開始連續排列。例：{19:30,20:00,22:30,01:30} 最大空檔在
// 01:30→19:30，故排成 19:30、20:00、22:30、01:30（傍晚連到凌晨）。
function sortedSlots(slots) {
  const toMin = (s) => {
    const [h, m] = String(s).split(':').map(Number)
    return (Number.isFinite(h) ? h : 0) * 60 + (Number.isFinite(m) ? m : 0)
  }
  const arr = slots.slice().sort((a, b) => toMin(a) - toMin(b))  // 先依時鐘分鐘排序
  const n = arr.length
  if (n <= 1) return arr
  // 找最大間隔，班次從間隔之後那一格開始（旋轉）
  let startIdx = 0
  let maxGap = -1
  for (let i = 0; i < n; i++) {
    const cur = toMin(arr[i])
    const next = toMin(arr[(i + 1) % n]) + (i + 1 === n ? 1440 : 0)  // 最後一格回繞 +24h
    const gap = next - cur
    if (gap > maxGap) { maxGap = gap; startIdx = (i + 1) % n }
  }
  return arr.slice(startIdx).concat(arr.slice(0, startIdx))
}
async function saveSlots(entry, slots) {
  try {
    const updated = await api.updateEntry(entry.id, { slots: sortedSlots(slots) })
    // 後端會把手動輸入正規化（如 1830→18:30），正規化後時間序可能改變 → 再排一次並補存
    const reordered = sortedSlots(updated.slots)
    if (reordered.join('|') !== updated.slots.join('|')) {
      entry.slots = (await api.updateEntry(entry.id, { slots: reordered })).slots
    } else {
      entry.slots = updated.slots
    }
  } catch (e) { error.value = e.message }
}
function removeSlot(entry, idx) {
  const next = entry.slots.slice()
  next.splice(idx, 1)
  saveSlots(entry, next)
}

// 時段模式
async function setMode(entry, mode) {
  if (entry.time_mode === mode) return
  entry.time_mode = mode
  try { await api.updateEntry(entry.id, { time_mode: mode }) } catch (e) { error.value = e.message }
}

// 手動輸入 (S9)
function addManualSlot(entry) {
  const v = (manualInput[entry.id] || '').trim()
  if (!v) return
  saveSlots(entry, [...entry.slots, v])
  manualInput[entry.id] = ''
}

// 自動換算 (S10)
async function computeShifts(entry) {
  const start = (autoStartInput[entry.id] ?? '').trim() || entry.auto_start
  if (!start) return
  try {
    const { slots } = await api.shiftSlots(start)
    computedShifts[entry.id] = slots
    await api.updateEntry(entry.id, { auto_start: start })
    entry.auto_start = start
  } catch (e) { error.value = e.message }
}
function toggleShift(entry, slot) {
  const has = entry.slots.includes(slot)
  const next = has ? entry.slots.filter((s) => s !== slot) : [...entry.slots, slot]
  saveSlots(entry, next)  // 排序由 saveSlots 統一處理（依時間序，含跨午夜）
}

// 發布 (S11)
async function openPublish() {
  copied.value = false
  shareNotice.value = ''
  tgNotice.value = ''
  try {
    const payload = await api.schedulePublishText(props.id)
    publishText.value = payload.text
    publishHtml.value = payload.html
    try { targets.value = (await api.listTargets()).filter(t => t.enabled) } catch (_) { targets.value = [] }
    showPublish.value = true
  } catch (e) { error.value = e.message }
}
// 發送班表文字到 Telegram（純前端直連），成功後標記已發布。
async function sendToTelegram(target) {
  tgNotice.value = ''
  tgSending.value = true
  try {
    await tgSendText(target.token, target.target_id, publishHtml.value || publishText.value, { parse_mode: 'HTML' })
    tgNotice.value = `✓ 已發送到「${target.name}」`
    await markPublished()
  } catch (e) {
    tgNotice.value = `發送到「${target.name}」失敗：${e.message}`
  } finally { tgSending.value = false }
}
// S6：成功發布（分享／複製／下載任一）後記錄發布時間，草稿列表即標示「已發布」。
async function markPublished() {
  try {
    const at = await api.markSchedulePublished(props.id)
    schedule.value.published_at = at
  } catch (_) { /* 記錄發布時間失敗不影響發布本身 */ }
}
// S5：透過 Web Share API 發布班表文字至 LINE 等。
async function shareSchedule() {
  shareNotice.value = ''
  try {
    const title = (schedule.value.title || '班表').split('\n')[0]
    const result = await share({ title, text: publishText.value })
    if (result === 'unsupported') {
      shareNotice.value = '此裝置不支援系統分享，請改用「複製純文字」或「下載排版圖片」。'
    } else if (result === 'shared') {
      await markPublished()
    }
  } catch (e) { shareNotice.value = '分享失敗：' + e.message }
}
async function copyText() {
  try {
    await navigator.clipboard.writeText(publishText.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
    await markPublished()
  } catch (e) { error.value = '複製失敗：' + e.message }
}
async function downloadImage() {
  if (!publishNode.value) return
  try {
    const canvas = await html2canvas(publishNode.value, { backgroundColor: '#ffffff', scale: 2 })
    canvas.toBlob((blob) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `班表_${(schedule.value.title || '未命名').split('\n')[0]}.png`
      a.click()
      URL.revokeObjectURL(a.href)
    })
    await markPublished()
  } catch (e) { error.value = '產生圖片失敗：' + e.message }
}

onMounted(() => { load(); loadCards() })
</script>

<template>
  <section v-if="schedule" class="edit">
    <div class="page-head">
      <button class="back" @click="goBack">← 返回班表列表</button>
      <h1>編輯班表</h1>
      <button class="primary publish-btn" @click="openPublish">📤 發布</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- 日期：發布時置於最上方 -->
    <div class="panel">
      <label class="field">
        <span>日期</span>
        <div class="date-row">
          <input type="date" v-model="schedule.date" @change="saveDate" />
          <span v-if="schedule.date" class="date-preview">{{ formatDate(schedule.date) }}</span>
          <span v-else class="hint">未選擇日期（發布時不顯示日期）</span>
        </div>
      </label>
    </div>

    <!-- 標題 (S6) -->
    <div class="panel">
      <label class="field">
        <span>標題（可多行）</span>
        <TextTemplateBar kind="title" :current-text="schedule.title" @apply="applyTitleTemplate" />
        <textarea v-model="schedule.title" rows="3" @blur="saveTitle" placeholder="例：今日班表 / 歡迎預約"></textarea>
      </label>
    </div>

    <!-- 出勤欄位 (S7) -->
    <div class="panel">
      <h2>出勤人員</h2>
      <p v-if="cadreCards.length === 0" class="hint">尚無資訊卡片，請先到「資訊卡片」建立。</p>
      <div class="attend-list">
        <button
          v-for="card in cadreCards"
          :key="card.id"
          class="attend-pill"
          :class="{ on: isAttending(card.id) }"
          @click="toggleAttend(card)"
        >
          <span v-if="isAttending(card.id)">✓</span> {{ card.name }}
        </button>
      </div>
    </div>

    <!-- 出勤時段 (S8/S9/S10) -->
    <div class="panel" v-if="schedule.entries.length">
      <h2>出勤時段</h2>
      <div v-for="entry in schedule.entries" :key="entry.id" class="entry">
        <div class="entry-head">
          <div>
            <span class="entry-name">{{ entry.name }}</span>
            <span v-if="entry.short_intro" class="entry-intro">{{ entry.short_intro }}</span>
          </div>
          <div class="mode-pills">
            <button class="pill" :class="{ active: entry.time_mode === 'manual' }" @click="setMode(entry, 'manual')">
              <span v-if="entry.time_mode === 'manual'">✓</span> 手動輸入
            </button>
            <button class="pill" :class="{ active: entry.time_mode === 'auto' }" @click="setMode(entry, 'auto')">
              <span v-if="entry.time_mode === 'auto'">✓</span> 自動換算
            </button>
          </div>
        </div>

        <!-- 顯示區：已加入的時段 -->
        <div class="slots">
          <span v-for="(slot, idx) in entry.slots" :key="idx" class="slot-chip">
            {{ slot }}<button class="chip-x" @click="removeSlot(entry, idx)">✕</button>
          </span>
          <span v-if="entry.slots.length === 0" class="hint">尚無時段</span>
        </div>

        <!-- 手動輸入 (S9) -->
        <div v-if="entry.time_mode === 'manual'" class="manual">
          <input
            v-model="manualInput[entry.id]"
            placeholder="輸入時間（如 1830 會自動轉成 18:30）"
            @keyup.enter="addManualSlot(entry)"
          />
          <button class="ghost" @click="addManualSlot(entry)">＋</button>
        </div>

        <!-- 自動換算 (S10) -->
        <div v-else class="auto">
          <div class="auto-row">
            <input
              v-model="autoStartInput[entry.id]"
              :placeholder="entry.auto_start || '上班時間（如 1800）'"
              @keyup.enter="computeShifts(entry)"
            />
            <button class="ghost" @click="computeShifts(entry)">換算班次</button>
          </div>
          <div v-if="computedShifts[entry.id]" class="shift-grid">
            <label v-for="slot in computedShifts[entry.id]" :key="slot" class="shift-box">
              <input type="checkbox" :checked="entry.slots.includes(slot)" @change="toggleShift(entry, slot)" />
              {{ slot }}
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- 結語：發布時置於最下方 -->
    <div class="panel">
      <label class="field">
        <span>結語（可多行）</span>
        <TextTemplateBar kind="footer" :current-text="schedule.footer" @apply="applyFooterTemplate" />
        <textarea v-model="schedule.footer" rows="3" @blur="saveFooter" placeholder="例：歡迎來電預約 / 感謝您的支持"></textarea>
      </label>
    </div>

    <!-- 發布視窗 (S11) -->
    <div v-if="showPublish" class="modal-backdrop" @click.self="showPublish = false">
      <div class="modal">
        <header class="modal-head">
          <h2>發布班表</h2>
          <button class="x" @click="showPublish = false">✕</button>
        </header>
        <div class="publish-preview" ref="publishNode">
          <pre class="pub-text">{{ publishText }}</pre>
        </div>

        <button v-if="shareSupported" class="primary share-main" @click="shareSchedule">
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

        <p class="hint center">{{ shareSupported ? '「分享」會開啟系統選單。草稿已自動保存，可再次編輯發布。' : '產生後手動貼到群組；草稿已自動保存，可再次編輯發布。' }}</p>
      </div>
    </div>
  </section>
  <p v-else-if="error" class="error">{{ error }}</p>
</template>

<style scoped>
.edit { max-width: 760px; }
/* 紅框區域凍結：捲動時固定在畫面頂端。背景補滿 app-main 上方留白，內容不會透出。 */
.page-head { display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 10; margin: -24px 0 12px; padding: 16px 0 12px; background: #f5f7fa; box-shadow: 0 4px 6px -4px rgba(16, 42, 67, 0.18); }
@media (max-width: 640px) {
  .page-head { margin: -14px 0 12px; padding: 12px 0 10px; }  /* 手機 app-main 留白較小 */
}
.page-head h1 { margin: 0; flex: 1; font-size: 1.4rem; }
.back { background: #e4e7eb; border: none; border-radius: 8px; padding: 6px 12px; color: #334e68; }
.publish-btn { white-space: nowrap; }
.error { color: #cf1124; }
.hint { color: #829ab1; font-size: 0.85rem; }
.hint.center { text-align: center; }

.panel { background: #fff; border: 1px solid #e4e7eb; border-radius: 12px; padding: 16px 18px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 12px; font-size: 1.1rem; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; color: #486581; }
.field textarea { padding: 8px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; resize: vertical; }
.date-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.date-row input[type="date"] { padding: 7px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; }
.date-preview { font-weight: 700; color: #102a43; }

.attend-list { display: flex; flex-wrap: wrap; gap: 8px; }
.attend-pill { padding: 6px 14px; border: 1px solid #cbd2d9; border-radius: 999px; background: #fff; color: #486581; }
.attend-pill.on { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }

.entry { border: 1px solid #e4e7eb; border-radius: 10px; padding: 12px 14px; margin-bottom: 12px; }
.entry-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.entry-name { font-weight: 700; margin-right: 8px; }
.entry-intro { color: #627d98; font-size: 0.9rem; }
.mode-pills { display: flex; gap: 6px; }
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 3px 12px; border: 1px solid #cbd2d9; border-radius: 999px; background: #fff; color: #627d98; font-size: 0.8rem; }
.pill.active { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }

.slots { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; min-height: 24px; }
.slot-chip { display: inline-flex; align-items: center; gap: 4px; background: #102a43; color: #fff; border-radius: 999px; padding: 3px 6px 3px 12px; font-size: 0.9rem; }
.chip-x { border: none; background: rgba(255,255,255,0.25); color: #fff; border-radius: 999px; width: 18px; height: 18px; line-height: 1; }

.manual { display: flex; gap: 8px; }
.manual input { flex: 1; padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 8px; }
.auto-row { display: flex; gap: 8px; margin-bottom: 8px; }
.auto-row input { flex: 1; padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 8px; }
.shift-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.shift-box { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #cbd2d9; border-radius: 8px; padding: 4px 10px; font-size: 0.9rem; background: #f5f7fa; }

button.ghost { background: #e4e7eb; color: #334e68; border: none; border-radius: 8px; padding: 6px 12px; }
button.primary { background: #2680c2; color: #fff; border: none; border-radius: 8px; padding: 6px 12px; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(16,42,67,0.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: #fff; border-radius: 14px; width: 460px; max-width: 92vw; max-height: 90vh; overflow-y: auto; padding: 18px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.modal-head h2 { margin: 0; font-size: 1.15rem; }
.modal-head .x { border: none; background: #e4e7eb; border-radius: 8px; width: 30px; height: 30px; }
.publish-preview { border: 1px solid #e4e7eb; border-radius: 12px; padding: 16px; background: #fff; }
.pub-text { white-space: pre-wrap; font-family: inherit; font-size: 1rem; line-height: 1.6; color: #1f2933; margin: 0; }
.share-main { display: block; width: 100%; padding: 11px; margin: 16px 0 6px; font-size: 1rem; }
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
</style>
