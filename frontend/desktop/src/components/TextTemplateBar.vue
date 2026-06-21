<script setup>
// 標題／結語的文字模板列：套用（下拉）、另存為模板、管理（改名／改內容／刪除）。
// 標題與結語各自獨立的模板池，以 kind 區分（'title' | 'footer'）。
import { ref, onMounted, nextTick } from 'vue'
import { api } from '../api'

const props = defineProps({
  kind: { type: String, required: true },        // 'title' | 'footer'
  currentText: { type: String, default: '' },    // 目前欄位內容（供「另存為模板」）
})
const emit = defineEmits(['apply'])               // 套用模板：payload 為內容字串

const templates = ref([])
const error = ref('')
const selectedId = ref('')
const showManage = ref(false)

async function load() {
  try { templates.value = await api.listTextTemplates(props.kind) }
  catch (e) { error.value = e.message }
}

// 套用：將選到的模板內容回填欄位，由父層負責存檔。
// 套用後把下拉重置回「套用模板…」（須等下一個 tick，否則同一次 change 內的重置不會反映到 DOM）。
function applySelected() {
  const t = templates.value.find((x) => x.id === Number(selectedId.value))
  if (t) emit('apply', t.content)
  nextTick(() => { selectedId.value = '' })
}

async function saveAsNew() {
  const name = (window.prompt('模板名稱：') || '').trim()
  if (!name) return
  try {
    await api.createTextTemplate({ kind: props.kind, name, content: props.currentText })
    await load()
  } catch (e) { error.value = e.message }
}

// 管理視窗內：改名／改內容（失焦存檔）、以目前欄位內容覆蓋、刪除。
async function saveTemplate(t) {
  try { await api.updateTextTemplate(t.id, { name: t.name, content: t.content }) }
  catch (e) { error.value = e.message }
}
async function overwriteWithCurrent(t) {
  t.content = props.currentText
  await saveTemplate(t)
}
async function removeTemplate(t) {
  if (!window.confirm(`確定刪除模板「${t.name}」？`)) return
  try { await api.deleteTextTemplate(t.id); await load() }
  catch (e) { error.value = e.message }
}

onMounted(load)
</script>

<template>
  <div class="tpl-bar">
    <select v-model="selectedId" @change="applySelected" class="tpl-select">
      <option value="">套用模板…</option>
      <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
    </select>
    <button class="tpl-btn" @click="saveAsNew">💾 另存為模板</button>
    <button class="tpl-btn" @click="showManage = true">⚙ 管理</button>
    <span v-if="error" class="tpl-error">{{ error }}</span>

    <div v-if="showManage" class="modal-backdrop" @click.self="showManage = false">
      <div class="modal">
        <header class="modal-head">
          <h3>管理模板</h3>
          <button class="x" @click="showManage = false">✕</button>
        </header>
        <p v-if="templates.length === 0" class="empty">尚無模板，可在編輯畫面用「另存為模板」建立。</p>
        <div v-for="t in templates" :key="t.id" class="tpl-row">
          <input class="tpl-name" v-model="t.name" @blur="saveTemplate(t)" placeholder="模板名稱" />
          <textarea class="tpl-content" v-model="t.content" rows="3" @blur="saveTemplate(t)"></textarea>
          <div class="tpl-row-actions">
            <button class="tpl-btn" @click="overwriteWithCurrent(t)">以目前內容覆蓋</button>
            <button class="tpl-btn danger" @click="removeTemplate(t)">刪除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tpl-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 6px; }
.tpl-select { padding: 5px 8px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.85rem; color: #1f2933; background: #fff; }
.tpl-btn { border: 1px solid #cbd2d9; background: #f5f7fa; color: #334e68; border-radius: 8px; padding: 5px 10px; font-size: 0.85rem; cursor: pointer; }
.tpl-btn.danger { border-color: #f5c0c0; color: #cf1124; background: #fdecec; }
.tpl-error { color: #cf1124; font-size: 0.8rem; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(16,42,67,0.45); display: flex; align-items: center; justify-content: center; z-index: 60; }
.modal { background: #fff; border-radius: 14px; width: 480px; max-width: 92vw; max-height: 90vh; overflow-y: auto; padding: 18px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.modal-head h3 { margin: 0; font-size: 1.1rem; }
.modal-head .x { border: none; background: #e4e7eb; border-radius: 8px; width: 30px; height: 30px; cursor: pointer; }
.empty { color: #829ab1; font-size: 0.9rem; }
.tpl-row { border: 1px solid #e4e7eb; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; }
.tpl-name { padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; font-weight: 600; color: #102a43; }
.tpl-content { padding: 8px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.9rem; color: #1f2933; resize: vertical; }
.tpl-row-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>
