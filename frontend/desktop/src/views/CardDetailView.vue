<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { api } from '../api'

// 文字框隨內容自動長高（不出現垂直捲軸）
function autogrow(el) {
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}
const vAutogrow = {
  mounted(el) {
    el.style.overflowY = 'hidden'
    el.style.resize = 'none'
    el.addEventListener('input', () => autogrow(el))
    nextTick(() => autogrow(el))
  },
  updated(el) {
    // 載入資料或程式設值（v-model）後重新計算高度
    nextTick(() => autogrow(el))
  },
}

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const card = ref(null)
const templates = ref([])
const error = ref('')
const showTemplates = ref(false)
const tplMsg = ref('')   // 模板編輯區內的操作回饋（成功/錯誤）
let tplMsgTimer = null
function showTplMsg(msg) {
  tplMsg.value = msg
  clearTimeout(tplMsgTimer)
  tplMsgTimer = setTimeout(() => { tplMsg.value = '' }, 3500)
}
const fileInput = ref(null)
const lightboxUrl = ref(null)

// --- 簡介草稿狀態 ---
const introSnapshot = ref('')
const introMsg = ref('')
let introMsgTimer = null
function showIntroMsg(msg) {
  introMsg.value = msg
  clearTimeout(introMsgTimer)
  introMsgTimer = setTimeout(() => { introMsg.value = '' }, 3500)
}
function introState() {
  return JSON.stringify({
    nationality: card.value?.nationality ?? '',
    intro_text: card.value?.intro_text ?? '',
  })
}
const introDirty = computed(() =>
  !!card.value && introState() !== introSnapshot.value
)

// --- 心得草稿狀態 ---
const reviewsSnapshot = ref('')  // 載入時心得可編輯欄位的快照
const reviewMsg = ref('')
let reviewMsgTimer = null
function showReviewMsg(msg) {
  reviewMsg.value = msg
  clearTimeout(reviewMsgTimer)
  reviewMsgTimer = setTimeout(() => { reviewMsg.value = '' }, 3500)
}
function reviewsState() {
  return JSON.stringify((card.value?.reviews || []).map((r) => ({
    id: r.id, date: r.date, text: r.text,
    scores: r.scores.map((s) => ({
      id: s.id, score: s.score, yesno_value: s.yesno_value, note: s.note,
    })),
  })))
}
const reviewsDirty = computed(() =>
  !!card.value && reviewsState() !== reviewsSnapshot.value
)

// --- 模板編輯草稿狀態 ---
const draft = ref(null)          // { id, name, items: [{ _key, name, item_type }] }
const originalJson = ref('')     // 載入時的快照，用於判斷是否有未儲存變更
const newDraftItemName = ref('')
let draftKeyCounter = 0

async function load() {
  try {
    card.value = await api.getCard(props.id)
    introSnapshot.value = introState()      // 重設簡介快照
    reviewsSnapshot.value = reviewsState()  // 重設心得快照（不再是未儲存）
  } catch (e) { error.value = e.message }
}
async function loadTemplates() {
  try { templates.value = await api.listTemplates() } catch (e) { error.value = e.message }
}

function goBack() {
  if (!leaveGuard()) return
  if (card.value?.spa_id) router.push({ name: 'spa-board', params: { id: card.value.spa_id } })
  else router.push('/')
}

// --- 基本 / 簡介 (C12/C14/C15) ---
async function saveCard(fields) {
  try { await api.updateCard(props.id, fields) } catch (e) { error.value = e.message }
}
function saveTitle() {
  const t = card.value.title.trim()
  if (t) saveCard({ title: t })
}
async function toggleIntro() {
  card.value.intro_collapsed = !card.value.intro_collapsed
  await saveCard({ intro_collapsed: card.value.intro_collapsed })
}

// --- 簡介文字（草稿，按「儲存簡介」才寫入）---
// 圖片等結構操作會重載並捨棄未儲存的簡介文字，先確認
function guardIntro() {
  if (introDirty.value) return confirm('有未儲存的簡介變更，繼續將捨棄這些變更。確定？')
  return true
}
async function saveIntro() {
  const o = JSON.parse(introSnapshot.value)
  const patch = {}
  if (o.nationality !== card.value.nationality) patch.nationality = card.value.nationality
  if (o.intro_text !== card.value.intro_text) patch.intro_text = card.value.intro_text
  try {
    if (Object.keys(patch).length) await api.updateCard(props.id, patch)
    introSnapshot.value = introState()
    showIntroMsg('✓ 已儲存簡介')
  } catch (e) { error.value = e.message }
}

// --- 圖片 (C13) ---
async function onFiles(e) {
  if (!guardIntro()) { e.target.value = ''; return }
  for (const file of e.target.files) {
    try { await api.uploadImage(props.id, file) } catch (err) { error.value = err.message }
  }
  e.target.value = ''
  await load()
}
function onPaste(e) {
  const items = e.clipboardData?.items || []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      if (!guardIntro()) return
      const blob = item.getAsFile()
      const reader = new FileReader()
      reader.onload = async () => {
        try { await api.pasteImage(props.id, reader.result); await load() }
        catch (err) { error.value = err.message }
      }
      reader.readAsDataURL(blob)
      return
    }
  }
}
async function setCover(img) {
  if (!guardIntro()) return
  try { await api.setCover(img.id); await load() } catch (e) { error.value = e.message }
}
async function removeImage(img) {
  if (!guardIntro()) return
  if (!confirm('刪除這張圖片？')) return
  try { await api.deleteImage(img.id); await load() } catch (e) { error.value = e.message }
}

// --- 心得 (C16/C19/C21/C22) ---
// 結構操作（新增/刪除/切換模板/更新）會重載並捨棄未儲存的欄位編輯，先確認
function guardReviews() {
  if (reviewsDirty.value) return confirm('有未儲存的心得變更，繼續將捨棄這些變更。確定？')
  return true
}
async function addReview() {
  if (!guardReviews()) return
  try { await api.createReview(props.id, {}); await load() } catch (e) { error.value = e.message }
}
async function removeReview(r) {
  if (!guardReviews()) return
  if (!confirm('刪除這組心得？')) return
  try { await api.deleteReview(r.id); await load() } catch (e) { error.value = e.message }
}
async function changeTemplate(r, evt) {
  const newId = Number(evt.target.value)
  if (!guardReviews()) { evt.target.value = r.template_id; return }
  if (!confirm('切換模板會以新模板項目重建評分，目前的分數會清空，確定？')) {
    evt.target.value = r.template_id; return
  }
  try { await api.applyReviewTemplate(r.id, newId); await load() }
  catch (e) { error.value = e.message }
}
// 儲存所有心得的欄位變更（日期/分數/有無/補充/心得文字）
async function saveReviews() {
  try {
    const orig = JSON.parse(reviewsSnapshot.value)
    const origMap = Object.fromEntries(orig.map((r) => [r.id, r]))
    for (const r of card.value.reviews) {
      const o = origMap[r.id]
      const rPatch = {}
      if (!o || o.date !== r.date) rPatch.date = r.date
      if (!o || o.text !== r.text) rPatch.text = r.text
      if (Object.keys(rPatch).length) await api.updateReview(r.id, rPatch)
      const oScores = Object.fromEntries((o?.scores || []).map((s) => [s.id, s]))
      for (const s of r.scores) {
        const os = oScores[s.id]
        const sPatch = {}
        if (!os || os.score !== s.score) sPatch.score = s.score
        if (!os || os.yesno_value !== s.yesno_value) sPatch.yesno_value = s.yesno_value
        if (!os || os.note !== s.note) sPatch.note = s.note
        if (Object.keys(sPatch).length) await api.updateScore(s.id, sPatch)
      }
    }
    await load()
    showReviewMsg('✓ 已儲存心得')
  } catch (e) { error.value = e.message }
}
function templateName(id) {
  const t = templates.value.find((x) => x.id === id)
  return t ? t.name : '（已刪除的模板）'
}

// 心得使用的模板是否已與目前模板不一致（項目名稱/類型/順序）
function templateDrifted(r) {
  if (r.template_id == null) return false
  const t = templates.value.find((x) => x.id === r.template_id)
  if (!t) return false
  const a = JSON.stringify(r.scores.map((s) => [s.item_name, s.item_type || 'score']))
  const b = JSON.stringify(t.items.map((i) => [i.name, i.item_type || 'score']))
  return a !== b
}
async function syncReview(r) {
  if (!guardReviews()) return
  if (!confirm(
    `以模板「${templateName(r.template_id)}」的最新項目更新此心得？\n\n` +
    '相同名稱項目的評分會保留，新增項目為空白，移除的項目會刪除。'
  )) return
  try { await api.syncReviewTemplate(r.id); await load() }
  catch (e) { error.value = e.message }
}

// --- 評分 / 有無（僅改本地，按「儲存心得」才寫入）---
function setYesno(s, val) {
  s.yesno_value = s.yesno_value === val ? '' : val  // 再次點選同一個則取消
}

// --- 模板編輯（草稿模式，C17）---
function draftSnapshot(d) {
  return JSON.stringify({
    name: (d.name || '').trim(),
    items: d.items.map((i) => ({ name: (i.name || '').trim(), item_type: i.item_type })),
  })
}
const isDirty = computed(() =>
  !!draft.value && draftSnapshot(draft.value) !== originalJson.value
)
const saveDisabled = computed(() => {
  if (!draft.value) return true
  if (!draft.value.name.trim()) return true
  if (draft.value.id === null) return false  // 新模板永遠可存
  return !isDirty.value
})

function loadDraft(tpl) {
  draft.value = {
    id: tpl.id,
    name: tpl.name,
    items: tpl.items.map((i) => ({
      _key: ++draftKeyCounter, name: i.name, item_type: i.item_type || 'score',
    })),
  }
  originalJson.value = draftSnapshot(draft.value)
}
function newTemplateDraft() {
  draft.value = { id: null, name: '新模板', items: [] }
  originalJson.value = draftSnapshot(draft.value)
}

// 切換編輯目標前先檢查未儲存變更；回傳 true 代表可以繼續
function confirmDiscard() {
  return !isDirty.value || confirm('有未儲存的模板變更，確定捨棄？')
}

async function openTemplateEditor() {
  await loadTemplates()
  showTemplates.value = true
  if (templates.value.length) loadDraft(templates.value[0])
  else newTemplateDraft()
}
function closeTemplateEditor() {
  if (!confirmDiscard()) return
  showTemplates.value = false
  draft.value = null
  tplMsg.value = ''
}
function onSelectTemplate(evt) {
  const val = evt.target.value
  if (!confirmDiscard()) return   // 取消：select 會因 :value 綁定自動還原
  if (val === '__new__') newTemplateDraft()
  else {
    const t = templates.value.find((x) => x.id === Number(val))
    if (t) loadDraft(t)
  }
}

function draftAddItem() {
  const name = newDraftItemName.value.trim()
  if (!name) return
  draft.value.items.push({ _key: ++draftKeyCounter, name, item_type: 'score' })
  newDraftItemName.value = ''
}
function draftRemoveItem(idx) { draft.value.items.splice(idx, 1) }
function draftSetType(item, type) { item.item_type = type }
function draftMoveItem(idx, dir) {
  const items = draft.value.items
  const j = dir === 'up' ? idx - 1 : idx + 1
  if (j < 0 || j >= items.length) return
  ;[items[idx], items[j]] = [items[j], items[idx]]
}
function draftCopyFrom(evt) {
  const otherId = Number(evt.target.value)
  evt.target.value = ''
  if (!otherId) return
  const other = templates.value.find((t) => t.id === otherId)
  if (!other) return
  if (draft.value.items.length &&
      !confirm(`以「${other.name}」的項目取代目前編輯中的項目？`)) return
  draft.value.items = other.items.map((i) => ({
    _key: ++draftKeyCounter, name: i.name, item_type: i.item_type || 'score',
  }))
}

async function saveDraft() {
  const name = draft.value.name.trim()
  if (!name) { showTplMsg('⚠ 模板名稱不可空白'); return }
  if (draft.value.items.some((i) => !i.name.trim())) {
    showTplMsg('⚠ 有項目名稱空白，請填寫或刪除'); return
  }
  const payload = {
    name,
    items: draft.value.items.map((i) => ({ name: i.name.trim(), item_type: i.item_type })),
  }
  try {
    let saved
    if (draft.value.id) {
      saved = await api.replaceTemplate(draft.value.id, payload)
    } else {
      const created = await api.createTemplate(name)
      saved = await api.replaceTemplate(created.id, payload)
    }
    await loadTemplates()
    const fresh = templates.value.find((t) => t.id === saved.id)
    if (fresh) loadDraft(fresh)   // 重設快照 → 不再是 dirty
    showTplMsg('✓ 已儲存。既有心得不受影響，可在心得處點「更新」套用。')
  } catch (e) { showTplMsg(`⚠ 儲存失敗：${e.message}`) }
}

async function deleteDraftTemplate() {
  if (draft.value.id === null) {
    // 未儲存的新模板：直接捨棄
    if (templates.value.length) loadDraft(templates.value[0])
    else { showTemplates.value = false; draft.value = null }
    return
  }
  if (!confirm(`刪除模板「${draft.value.name}」？`)) return
  try {
    await api.deleteTemplate(draft.value.id)
    await loadTemplates()
    if (templates.value.length) loadDraft(templates.value[0])
    else newTemplateDraft()
    showTplMsg('✓ 已刪除模板')
  } catch (e) { showTplMsg(`⚠ 刪除失敗：${e.message}`) }
}

// --- 離開頁面 / 路由守衛 ---
function pendingChanges() {
  const pending = []
  if (showTemplates.value && isDirty.value) pending.push('模板')
  if (!showTemplates.value && reviewsDirty.value) pending.push('心得')
  if (introDirty.value) pending.push('簡介')
  return pending
}
function leaveGuard() {
  const pending = pendingChanges()
  if (pending.length) {
    return confirm(`有未儲存的${pending.join('、')}變更，確定離開？變更將不會儲存。`)
  }
  return true
}
onBeforeRouteLeave(() => leaveGuard())
function onBeforeUnload(e) {
  if (pendingChanges().length) { e.preventDefault(); e.returnValue = '' }
}

onMounted(() => {
  load()
  loadTemplates()
  window.addEventListener('paste', onPaste)
  window.addEventListener('beforeunload', onBeforeUnload)
})
onBeforeUnmount(() => {
  window.removeEventListener('paste', onPaste)
  window.removeEventListener('beforeunload', onBeforeUnload)
  clearTimeout(tplMsgTimer)
  clearTimeout(reviewMsgTimer)
  clearTimeout(introMsgTimer)
})
</script>

<template>
  <section v-if="card" class="detail">
    <div class="page-head">
      <button class="back" @click="goBack">← 返回看板</button>
      <input class="title-input" v-model="card.title" @blur="saveTitle" />
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- 簡介 (C12–C15) -->
    <div class="panel">
      <header class="panel-head">
        <h2>美容師簡介</h2>
        <div class="head-actions">
          <span v-if="introDirty" class="editing-tag">● 尚未儲存</span>
          <button class="ghost" @click="toggleIntro">
            {{ card.intro_collapsed ? '＋ 展開' : '－ 收闔' }}
          </button>
          <button class="primary" :disabled="!introDirty" @click="saveIntro">儲存簡介</button>
        </div>
      </header>

      <div v-show="!card.intro_collapsed" class="panel-body">
        <p v-if="introMsg" class="tpl-feedback is-ok">{{ introMsg }}</p>
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
          <span>國籍</span>
          <input v-model="card.nationality" />
        </label>
        <label class="field">
          <span>文字說明</span>
          <textarea v-model="card.intro_text" rows="4" v-autogrow></textarea>
        </label>
      </div>
    </div>

    <!-- 心得 / 模板編輯 (C16–C22) -->
    <div class="panel">
      <header class="panel-head">
        <h2>{{ showTemplates ? '評分模板編輯' : `${card.spa_name ?? ''} ${card.title ?? ''} 心得`.trim() }}</h2>
        <div class="head-actions">
          <template v-if="!showTemplates">
            <span v-if="reviewsDirty" class="editing-tag">● 尚未儲存</span>
            <button class="ghost" @click="openTemplateEditor">⚙ 評分模板</button>
            <button class="ghost" @click="addReview">＋ 新增心得</button>
            <button class="primary" :disabled="!reviewsDirty" @click="saveReviews">儲存心得</button>
          </template>
          <template v-else>
            <span v-if="isDirty" class="editing-tag">● 尚未儲存</span>
            <button class="ghost" @click="closeTemplateEditor">← 完成 / 關閉</button>
          </template>
        </div>
      </header>

      <!-- 模板編輯區（草稿模式）-->
      <div v-if="showTemplates" class="tpl-editor">
        <p class="tpl-hint">
          模板定義每次心得的評比項目。修改後請點「儲存」；
          <strong>儲存不會更動已建立的心得</strong>，但之後用此模板新增的心得會採用新版項目。
          既有心得若需套用更新，可在心得右上角的提示點「更新」。
        </p>
        <p v-if="tplMsg" class="tpl-feedback" :class="tplMsg.startsWith('⚠') ? 'is-error' : 'is-ok'">{{ tplMsg }}</p>

        <div class="editor-bar">
          <label class="field inline">
            <span>選擇模板</span>
            <select :value="draft ? (draft.id ?? '__new__') : ''" @change="onSelectTemplate">
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
              <option value="__new__">＋ 新增模板…</option>
            </select>
          </label>
        </div>

        <div v-if="draft" class="tpl-draft">
          <label class="field">
            <span>模板名稱</span>
            <input v-model="draft.name" placeholder="模板名稱" />
          </label>

          <p class="sub-label">評比項目</p>
          <ul class="tpl-items">
            <li v-for="(item, idx) in draft.items" :key="item._key">
              <input v-model="item.name" placeholder="項目名稱" />
              <div class="type-pills" role="group">
                <button class="type-pill" :class="{ active: item.item_type === 'score' }" @click="draftSetType(item, 'score')">
                  <span v-if="item.item_type === 'score'" class="check">✓</span>分數
                </button>
                <button class="type-pill" :class="{ active: item.item_type === 'yesno' }" @click="draftSetType(item, 'yesno')">
                  <span v-if="item.item_type === 'yesno'" class="check">✓</span>有/無
                </button>
              </div>
              <button class="move-btn" :disabled="idx === 0" @click="draftMoveItem(idx, 'up')" title="上移">↑</button>
              <button class="move-btn" :disabled="idx === draft.items.length - 1" @click="draftMoveItem(idx, 'down')" title="下移">↓</button>
              <button class="x" @click="draftRemoveItem(idx)" title="刪除項目">✕</button>
            </li>
            <li v-if="draft.items.length === 0" class="empty-item">尚無項目，請於下方新增。</li>
          </ul>
          <div class="item-add">
            <input v-model="newDraftItemName" placeholder="輸入項目名稱後按 Enter 或點＋" @keyup.enter="draftAddItem" />
            <button class="ghost" @click="draftAddItem">＋ 新增項目</button>
          </div>

          <div v-if="templates.length" class="copy-from">
            <label class="field inline">
              <span>從其他模板載入項目</span>
              <select @change="draftCopyFrom">
                <option value="">選擇來源模板…</option>
                <option
                  v-for="other in templates.filter((x) => x.id !== draft.id)"
                  :key="other.id" :value="other.id"
                >{{ other.name }}</option>
              </select>
            </label>
            <span class="hint">（僅載入到目前編輯中，按「儲存」才會生效）</span>
          </div>

          <div class="editor-actions">
            <button class="primary" :disabled="saveDisabled" @click="saveDraft">儲存</button>
            <button class="danger" @click="deleteDraftTemplate">{{ draft.id ? '刪除此模板' : '捨棄' }}</button>
          </div>
        </div>
      </div>

      <!-- 心得列表（編輯模板時隱藏）-->
      <template v-else>
        <p v-if="reviewMsg" class="tpl-feedback is-ok review-feedback">{{ reviewMsg }}</p>
        <p v-if="card.reviews.length === 0" class="empty">尚無心得，點「＋ 新增心得」開始記錄。</p>

        <div v-for="r in card.reviews" :key="r.id" class="review">
          <div v-if="templateDrifted(r)" class="drift-hint">
            <span>⚠ 模板「{{ templateName(r.template_id) }}」已更新，此心得仍為舊版項目。</span>
            <button class="ghost small" @click="syncReview(r)">更新為最新項目</button>
          </div>

          <div class="review-head">
            <label class="field inline">
              <span>日期</span>
              <input type="date" v-model="r.date" />
            </label>
            <label class="field inline">
              <span>套用模板</span>
              <select :value="r.template_id" @change="changeTemplate(r, $event)">
                <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
                <option v-if="r.template_id && !templates.find((t) => t.id === r.template_id)" :value="r.template_id">
                  {{ templateName(r.template_id) }}
                </option>
              </select>
            </label>
            <button class="danger small" @click="removeReview(r)">刪除心得</button>
          </div>

          <div class="scores">
            <div v-for="s in r.scores" :key="s.id" class="score-row">
              <span class="score-name">{{ s.item_name }}</span>
              <!-- 分數型 (0~10) -->
              <template v-if="!s.item_type || s.item_type === 'score'">
                <input class="score-slider" type="range" min="0" max="10" v-model.number="s.score" />
                <input class="score-num" type="number" min="0" max="10" v-model.number="s.score" />
              </template>
              <!-- 有/無型 -->
              <template v-else>
                <div class="yn-btns">
                  <button class="yn-btn" :class="{ 'yn-yes': s.yesno_value === '有' }" @click="setYesno(s, '有')">有</button>
                  <button class="yn-btn" :class="{ 'yn-no': s.yesno_value === '無' }" @click="setYesno(s, '無')">無</button>
                </div>
              </template>
              <input class="score-note" v-model="s.note" placeholder="補充說明" />
            </div>
            <p v-if="r.scores.length === 0" class="hint">此模板尚無項目。</p>
          </div>

          <label class="field">
            <span>心得文字</span>
            <textarea v-model="r.text" rows="3" v-autogrow></textarea>
          </label>
        </div>
      </template>
    </div>
  </section>
  <!-- 燈箱 -->
  <div v-if="lightboxUrl" class="lightbox-backdrop" @click.self="lightboxUrl = null">
    <div class="lightbox-box">
      <button class="lightbox-close" @click="lightboxUrl = null">✕</button>
      <img :src="lightboxUrl" alt="" />
    </div>
  </div>
  <p v-else-if="error" class="error">{{ error }}</p>
</template>

<style scoped>
.detail { max-width: 880px; }
.page-head { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.back { background: #e4e7eb; border: none; border-radius: 8px; padding: 6px 12px; color: #334e68; }
.title-input { flex: 1; font-size: 1.4rem; font-weight: 700; border: 1px solid transparent; border-radius: 8px; padding: 4px 8px; }
.title-input:hover, .title-input:focus { border-color: #cbd2d9; outline: none; }
.error { color: #cf1124; }
.empty, .hint { color: #829ab1; font-size: 0.85rem; }

.panel { background: #fff; border: 1px solid #e4e7eb; border-radius: 12px; margin-bottom: 20px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid #f0f2f5; }
.panel-head h2 { margin: 0; font-size: 1.1rem; }
.head-actions { display: flex; align-items: center; gap: 8px; }
.editing-tag { font-size: 0.85rem; color: #b44d12; font-weight: 600; }
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
.field.inline { flex-direction: row; align-items: center; gap: 6px; }
.field input, .field textarea, .field select { padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; }
.field textarea { resize: vertical; }

/* 模板編輯區 */
.tpl-editor { padding: 14px 18px; background: #f5f7fa; }
.tpl-hint { font-size: 0.82rem; color: #627d98; line-height: 1.6; margin: 0 0 10px; }
.tpl-feedback { font-size: 0.85rem; padding: 6px 12px; border-radius: 8px; margin-bottom: 10px; }
.tpl-feedback.is-ok { background: #e3f9e5; color: #1a7a31; }
.tpl-feedback.is-error { background: #fbeae5; color: #cf1124; }
.editor-bar { margin-bottom: 12px; }
.tpl-draft { background: #fff; border: 1px solid #e4e7eb; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.sub-label { font-size: 0.85rem; font-weight: 600; color: #486581; margin: 4px 0 0; }
.tpl-items { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.tpl-items li { display: flex; gap: 6px; align-items: center; }
.tpl-items li.empty-item { color: #9fb3c8; font-size: 0.85rem; }
.tpl-items input { flex: 1; padding: 4px 8px; border: 1px solid #e4e7eb; border-radius: 6px; }
.tpl-items .x { border: none; background: #fbeae5; color: #cf1124; border-radius: 6px; padding: 0 8px; flex-shrink: 0; }
.move-btn { background: none; border: 1px solid #cbd2d9; border-radius: 4px; padding: 1px 6px; color: #627d98; font-size: 0.8rem; cursor: pointer; flex-shrink: 0; }
.move-btn:disabled { opacity: 0.2; cursor: default; }
.item-add { display: flex; gap: 8px; }
.item-add input { flex: 1; padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 8px; }
.copy-from { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; border-top: 1px dashed #e4e7eb; padding-top: 10px; }
.copy-from select { padding: 4px 8px; border: 1px solid #cbd2d9; border-radius: 6px; }
.editor-actions { display: flex; gap: 8px; border-top: 1px solid #f0f2f5; padding-top: 12px; }
button.small { font-size: 0.8rem; padding: 4px 8px; }
.type-pills { display: inline-flex; gap: 4px; flex-shrink: 0; }
.type-pill { display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; font-size: 0.75rem; border: 1px solid #cbd2d9; border-radius: 999px; background: #fff; color: #627d98; cursor: pointer; }
.type-pill.active { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }
.type-pill .check { font-size: 0.7rem; }

/* 心得 */
.review-feedback { margin: 14px 18px 0; }
.review { border: 1px solid #e4e7eb; border-radius: 10px; padding: 14px; margin: 14px 18px; }
.drift-hint { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; background: #fffbea; border: 1px solid #f7d070; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; font-size: 0.85rem; color: #8d6b14; }
.review-head { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.scores { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.score-row { display: flex; align-items: center; gap: 10px; }
.score-name { min-width: 84px; font-size: 0.9rem; flex-shrink: 0; }
.score-slider { width: 160px; flex-shrink: 0; }
.score-num { width: 52px; padding: 2px 4px; border: 1px solid #cbd2d9; border-radius: 6px; text-align: center; font-weight: 700; color: #2680c2; flex-shrink: 0; }
.score-note { flex: 1; padding: 4px 8px; border: 1px solid #cbd2d9; border-radius: 6px; min-width: 0; }
.yn-btns { display: flex; gap: 6px; flex-shrink: 0; width: 222px; }
.yn-btn { padding: 4px 14px; border: 1px solid #cbd2d9; border-radius: 999px; background: #fff; color: #627d98; cursor: pointer; font-size: 0.9rem; }
.yn-btn.yn-yes { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }
.yn-btn.yn-no { border-color: #d64e12; background: #fbe9e7; color: #b83c23; font-weight: 600; }

button.ghost { background: #e4e7eb; color: #334e68; border: none; border-radius: 8px; padding: 6px 12px; }
button.primary { background: #2680c2; color: #fff; border: none; border-radius: 8px; padding: 6px 12px; }
button.primary:disabled { opacity: 0.45; cursor: default; }
button.danger { background: #fbeae5; color: #cf1124; border: none; border-radius: 8px; padding: 6px 12px; }
button.danger.small, button.danger { font-size: 0.85rem; }

.lightbox-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.82); display: flex; align-items: center; justify-content: center; z-index: 100; }
.lightbox-box { position: relative; max-width: 90vw; max-height: 90vh; }
.lightbox-box img { display: block; max-width: 90vw; max-height: 90vh; border-radius: 8px; object-fit: contain; }
.lightbox-close { position: absolute; top: -14px; right: -14px; width: 32px; height: 32px; border-radius: 50%; border: none; background: #fff; color: #334e68; font-size: 1rem; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 1; }
.lightbox-close:hover { background: #cf1124; color: #fff; }

@media (max-width: 640px) {
  .detail { max-width: 100%; }
  /* 評分列在窄螢幕換行：名稱+滑桿一行，補充說明獨立一行 */
  .score-row { flex-wrap: wrap; }
  .score-slider { flex: 1; width: auto; min-width: 120px; }
  .yn-btns { width: auto; }
  .score-note { flex-basis: 100%; }
}
</style>
