<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const card = ref(null)
const templates = ref([])
const error = ref('')
const showTemplates = ref(false)
const fileInput = ref(null)
const newTemplateName = ref('')
const newItemName = ref({}) // { [templateId]: name }

async function load() {
  try {
    card.value = await api.getCard(props.id)
  } catch (e) { error.value = e.message }
}
async function loadTemplates() {
  try { templates.value = await api.listTemplates() } catch (e) { error.value = e.message }
}

function goBack() {
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

// --- 圖片 (C13) ---
async function onFiles(e) {
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
      const blob = item.getAsFile()
      const reader = new FileReader()
      reader.onload = async () => {
        try { await api.pasteImage(props.id, reader.result); await load() }
        catch (err) { error.value = err.message }
      }
      reader.readAsDataURL(blob)
      e.preventDefault()
      return
    }
  }
}
async function setCover(img) {
  try { await api.setCover(img.id); await load() } catch (e) { error.value = e.message }
}
async function removeImage(img) {
  if (!confirm('刪除這張圖片？')) return
  try { await api.deleteImage(img.id); await load() } catch (e) { error.value = e.message }
}

// --- 心得 (C16/C19/C21/C22) ---
async function addReview() {
  try { await api.createReview(props.id, {}); await load() } catch (e) { error.value = e.message }
}
async function removeReview(r) {
  if (!confirm('刪除這組心得？')) return
  try { await api.deleteReview(r.id); await load() } catch (e) { error.value = e.message }
}
function saveReview(r, field) {
  api.updateReview(r.id, { [field]: r[field] }).catch((e) => (error.value = e.message))
}
async function changeTemplate(r) {
  if (!confirm('切換模板會以新模板項目重建評分，目前的分數會清空，確定？')) {
    await load(); return
  }
  try { await api.applyReviewTemplate(r.id, r.template_id); await load() }
  catch (e) { error.value = e.message }
}
function saveScore(s) {
  api.updateScore(s.id, { score: s.score, note: s.note }).catch((e) => (error.value = e.message))
}
function templateName(id) {
  const t = templates.value.find((x) => x.id === id)
  return t ? t.name : '（已刪除的模板）'
}

// --- 模板管理 (C17) ---
async function addTemplate() {
  const name = newTemplateName.value.trim()
  if (!name) return
  try { await api.createTemplate(name); newTemplateName.value = ''; await loadTemplates() }
  catch (e) { error.value = e.message }
}
async function renameTemplate(t) {
  const name = t.name.trim()
  if (!name) return
  try { await api.renameTemplate(t.id, name) } catch (e) { error.value = e.message }
}
async function removeTemplate(t) {
  if (!confirm(`刪除模板「${t.name}」？`)) return
  try { await api.deleteTemplate(t.id); await loadTemplates() } catch (e) { error.value = e.message }
}
async function addItem(t) {
  const name = (newItemName.value[t.id] || '').trim()
  if (!name) return
  try { await api.addTemplateItem(t.id, name); newItemName.value[t.id] = ''; await loadTemplates() }
  catch (e) { error.value = e.message }
}
async function renameItem(item) {
  const name = item.name.trim()
  if (!name) return
  try { await api.renameTemplateItem(item.id, name) } catch (e) { error.value = e.message }
}
async function removeItem(item) {
  try { await api.deleteTemplateItem(item.id); await loadTemplates() } catch (e) { error.value = e.message }
}

onMounted(() => {
  load()
  loadTemplates()
  window.addEventListener('paste', onPaste)
})
onBeforeUnmount(() => window.removeEventListener('paste', onPaste))
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
        <button class="ghost" @click="toggleIntro">
          {{ card.intro_collapsed ? '＋ 展開' : '－ 收闔' }}
        </button>
      </header>

      <div v-show="!card.intro_collapsed" class="panel-body">
        <div class="images">
          <div v-for="img in card.images" :key="img.id" class="img-cell" :class="{ cover: img.is_cover }">
            <img :src="img.url" alt="" />
            <span v-if="img.is_cover" class="cover-badge">封面</span>
            <div class="img-actions">
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
          <input v-model="card.nationality" @blur="saveCard({ nationality: card.nationality })" />
        </label>
        <label class="field">
          <span>文字說明</span>
          <textarea v-model="card.intro_text" rows="4" @blur="saveCard({ intro_text: card.intro_text })"></textarea>
        </label>
      </div>
    </div>

    <!-- 心得 (C16–C22) -->
    <div class="panel">
      <header class="panel-head">
        <h2>心得</h2>
        <div class="head-actions">
          <button class="ghost" @click="showTemplates = !showTemplates">⚙ 評分模板</button>
          <button class="primary" @click="addReview">＋ 新增心得</button>
        </div>
      </header>

      <!-- 模板管理面板 (C17/C18) -->
      <div v-if="showTemplates" class="templates">
        <div class="tpl-add">
          <input v-model="newTemplateName" placeholder="新增模板名稱" @keyup.enter="addTemplate" />
          <button class="primary" @click="addTemplate">＋ 模板</button>
        </div>
        <div v-for="t in templates" :key="t.id" class="tpl">
          <div class="tpl-head">
            <input class="tpl-name" v-model="t.name" @blur="renameTemplate(t)" />
            <button class="danger" @click="removeTemplate(t)">刪除模板</button>
          </div>
          <ul class="tpl-items">
            <li v-for="item in t.items" :key="item.id">
              <input v-model="item.name" @blur="renameItem(item)" />
              <button class="x" @click="removeItem(item)">✕</button>
            </li>
          </ul>
          <div class="item-add">
            <input v-model="newItemName[t.id]" placeholder="新增項目" @keyup.enter="addItem(t)" />
            <button class="ghost" @click="addItem(t)">＋ 項目</button>
          </div>
        </div>
      </div>

      <p v-if="card.reviews.length === 0" class="empty">尚無心得，點「＋ 新增心得」開始記錄。</p>

      <div v-for="r in card.reviews" :key="r.id" class="review">
        <div class="review-head">
          <label class="field inline">
            <span>日期</span>
            <input type="date" v-model="r.date" @change="saveReview(r, 'date')" />
          </label>
          <label class="field inline">
            <span>套用模板</span>
            <select v-model="r.template_id" @change="changeTemplate(r)">
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
            <input type="range" min="0" max="10" v-model.number="s.score" @change="saveScore(s)" />
            <span class="score-val">{{ s.score }}</span>
            <input class="score-note" v-model="s.note" placeholder="補充說明" @blur="saveScore(s)" />
          </div>
          <p v-if="r.scores.length === 0" class="hint">此模板尚無項目。</p>
        </div>

        <label class="field">
          <span>心得文字</span>
          <textarea v-model="r.text" rows="3" @blur="saveReview(r, 'text')"></textarea>
        </label>
      </div>
    </div>
  </section>
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
.head-actions { display: flex; gap: 8px; }
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

.templates { padding: 14px 18px; background: #f5f7fa; border-bottom: 1px solid #f0f2f5; }
.tpl-add, .item-add { display: flex; gap: 8px; margin-bottom: 10px; }
.tpl-add input, .item-add input { padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 8px; }
.tpl { background: #fff; border: 1px solid #e4e7eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.tpl-head { display: flex; gap: 8px; margin-bottom: 8px; }
.tpl-name { flex: 1; font-weight: 600; padding: 4px 8px; border: 1px solid #cbd2d9; border-radius: 6px; }
.tpl-items { list-style: none; margin: 0 0 8px; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.tpl-items li { display: flex; gap: 6px; }
.tpl-items input { flex: 1; padding: 4px 8px; border: 1px solid #e4e7eb; border-radius: 6px; }
.tpl-items .x { border: none; background: #fbeae5; color: #cf1124; border-radius: 6px; padding: 0 8px; }

.review { border: 1px solid #e4e7eb; border-radius: 10px; padding: 14px; margin: 14px 18px; }
.review-head { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.scores { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.score-row { display: grid; grid-template-columns: 84px 160px 28px 1fr; align-items: center; gap: 10px; }
.score-name { font-size: 0.9rem; }
.score-val { font-weight: 700; color: #2680c2; text-align: center; }
.score-note { padding: 4px 8px; border: 1px solid #cbd2d9; border-radius: 6px; }

button.ghost { background: #e4e7eb; color: #334e68; border: none; border-radius: 8px; padding: 6px 12px; }
button.primary { background: #2680c2; color: #fff; border: none; border-radius: 8px; padding: 6px 12px; }
button.danger { background: #fbeae5; color: #cf1124; border: none; border-radius: 8px; padding: 6px 12px; }
button.danger.small, button.danger { font-size: 0.85rem; }
</style>
