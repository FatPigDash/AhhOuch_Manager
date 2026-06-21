<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import html2canvas from 'html2canvas'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const schedule = ref(null)
const storeCards = ref([])
const error = ref('')

const manualInput = reactive({})   // { [entryId]: 輸入字串 }
const autoStartInput = reactive({}) // { [entryId]: 上班時間 }
const computedShifts = reactive({}) // { [entryId]: [slot,...] }

const showPublish = ref(false)
const publishText = ref('')
const publishNode = ref(null)
const copied = ref(false)
const targets = ref([])
const sendMsg = ref('')

async function load() {
  try {
    schedule.value = await api.getSchedule(props.id)
    await restoreShiftGrids()
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
  try { storeCards.value = await api.listStoreCards() } catch (e) { error.value = e.message }
}
function goBack() { router.push({ name: 'schedule-list' }) }

// 標題 (S6)
function saveTitle() {
  api.updateSchedule(props.id, { title: schedule.value.title }).catch((e) => (error.value = e.message))
}

// 出勤人員 (S7/S8)
function isAttending(cardId) {
  return schedule.value.entries.some((e) => e.store_card_id === cardId)
}
async function toggleAttend(card) {
  const entry = schedule.value.entries.find((e) => e.store_card_id === card.id)
  try {
    if (entry) await api.deleteEntry(entry.id)
    else await api.addEntry(schedule.value.id, card.id)
    await load()
  } catch (e) { error.value = e.message }
}

// 時段共用
async function saveSlots(entry, slots) {
  try {
    const updated = await api.updateEntry(entry.id, { slots })
    entry.slots = updated.slots
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
  saveSlots(entry, next)
}

// 發布 (S11)
async function openPublish() {
  copied.value = false
  sendMsg.value = ''
  try {
    publishText.value = (await api.schedulePublishText(props.id)).text
    targets.value = (await api.listTargets()).filter((t) => t.enabled)
    showPublish.value = true
  } catch (e) { error.value = e.message }
}
// 發布目標按鈕顯示「平台 名稱」，如「Telegram 111」。
const PLATFORM_LABEL = { telegram: 'Telegram', x: 'X' }
function platformLabel(p) { return PLATFORM_LABEL[p] || p || '' }
async function sendToTarget(t) {
  // 發送前先確認，避免不小心點到就發出去。
  if (!confirm(`確定要發布到「${platformLabel(t.platform)} ${t.name}」嗎？`)) return
  sendMsg.value = `發布到「${t.name}」中…`
  try {
    // 走 HTML 發布端點：已發布過資訊的美容師，名字會自動加上超連結。
    await api.publishSchedule(props.id, { target_id: t.id })
    sendMsg.value = `✓ 已發布到「${t.name}」`
  } catch (e) { sendMsg.value = `✗ ${e.message}` }
}
async function copyText() {
  try {
    await navigator.clipboard.writeText(publishText.value)
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
      a.download = `班表_${(schedule.value.title || '未命名').split('\n')[0]}.png`
      a.click()
      URL.revokeObjectURL(a.href)
    })
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

    <!-- 標題 (S6) -->
    <div class="panel">
      <label class="field">
        <span>標題（可多行）</span>
        <textarea v-model="schedule.title" rows="3" @blur="saveTitle" placeholder="例：今日班表 / 歡迎預約"></textarea>
      </label>
    </div>

    <!-- 出勤欄位 (S7) -->
    <div class="panel">
      <h2>出勤人員</h2>
      <p v-if="storeCards.length === 0" class="hint">尚無資訊卡片，請先到「資訊卡片」建立。</p>
      <div class="attend-list">
        <button
          v-for="card in storeCards"
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
        <div class="modal-actions">
          <button class="ghost" @click="copyText">{{ copied ? '✓ 已複製文字' : '📋 複製純文字' }}</button>
          <button class="primary" @click="downloadImage">🖼 下載排版圖片</button>
        </div>

        <div v-if="targets.length" class="auto-publish">
          <span class="ap-label">自動發布到：</span>
          <button v-for="t in targets" :key="t.id" class="chip-btn" @click="sendToTarget(t)">📤 {{ platformLabel(t.platform) }} {{ t.name }}</button>
        </div>
        <p v-if="targets.length" class="hint center">自動發布時，曾發布過資訊的美容師名字會自動連到該則資訊訊息（僅自動發布有效）。</p>
        <p v-if="sendMsg" class="hint center">{{ sendMsg }}</p>

        <p class="hint center">產生後手動貼到群組；草稿已自動保存，可再次編輯發布。</p>
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
.modal-actions { display: flex; gap: 10px; margin: 16px 0 6px; }
.modal-actions button { flex: 1; padding: 9px; border: none; border-radius: 8px; }
.auto-publish { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 6px; padding-top: 10px; border-top: 1px solid #f0f2f5; }
.ap-label { font-size: 0.85rem; color: #627d98; }
.chip-btn { border: 1px solid #2680c2; color: #0a558c; background: #e3f0fb; border-radius: 999px; padding: 5px 12px; font-size: 0.85rem; }
</style>
