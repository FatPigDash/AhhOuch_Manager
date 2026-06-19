<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../api'
import StoreNav from '../components/StoreNav.vue'

const targets = ref([])
const platforms = ref([])
const error = ref('')
const form = reactive({ name: '', platform: 'line', token: '', target_id: '' })
const edit = reactive({}) // { [id]: {token, target_id, ...} 暫存編輯 }

const PLATFORM_LABEL = { line: 'LINE', telegram: 'Telegram' }

async function load() {
  try {
    targets.value = await api.listTargets()
    platforms.value = (await api.publishPlatforms()).platforms
  } catch (e) { error.value = e.message }
}
async function addTarget() {
  if (!form.name.trim()) { error.value = '請輸入名稱'; return }
  try {
    await api.createTarget({ ...form, name: form.name.trim() })
    form.name = ''; form.token = ''; form.target_id = ''
    await load()
  } catch (e) { error.value = e.message }
}
function startEdit(t) {
  edit[t.id] = { name: t.name, platform: t.platform, target_id: t.target_id, token: '', enabled: t.enabled }
}
async function saveEdit(t) {
  try {
    await api.updateTarget(t.id, edit[t.id]) // token 留空=不更動
    delete edit[t.id]
    await load()
  } catch (e) { error.value = e.message }
}
async function toggleEnabled(t) {
  try { await api.updateTarget(t.id, { enabled: !t.enabled }); await load() } catch (e) { error.value = e.message }
}
async function removeTarget(t) {
  if (!confirm(`刪除發布目標「${t.name}」？`)) return
  try { await api.deleteTarget(t.id); await load() } catch (e) { error.value = e.message }
}
function label(p) { return PLATFORM_LABEL[p] || p || '（未指定）' }

onMounted(load)
</script>

<template>
  <section>
    <StoreNav />
    <h1>發布設定</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <p class="hint">
      設定一鍵自動發布的去處（平台＋權杖＋目標 ID）。設定後可在卡片／班表的「發布」視窗直接送出文字。
      權杖需自行向平台申請；目前支援 {{ platforms.map(label).join('、') }}。
    </p>

    <div class="panel add">
      <h2>新增發布目標</h2>
      <div class="grid">
        <label>名稱<input v-model="form.name" placeholder="如：工作室 LINE 群" /></label>
        <label>平台
          <select v-model="form.platform">
            <option v-for="p in platforms" :key="p" :value="p">{{ label(p) }}</option>
          </select>
        </label>
        <label>權杖 (token)<input v-model="form.token" type="password" placeholder="channel / bot token" /></label>
        <label>目標 ID<input v-model="form.target_id" :placeholder="form.platform === 'line' ? 'LINE groupId' : 'chat_id'" /></label>
      </div>
      <button class="primary" @click="addTarget">＋ 新增</button>
    </div>

    <p v-if="targets.length === 0" class="empty">尚無發布目標。</p>
    <ul class="list">
      <li v-for="t in targets" :key="t.id" class="row">
        <template v-if="edit[t.id]">
          <div class="grid">
            <label>名稱<input v-model="edit[t.id].name" /></label>
            <label>平台
              <select v-model="edit[t.id].platform">
                <option v-for="p in platforms" :key="p" :value="p">{{ label(p) }}</option>
              </select>
            </label>
            <label>權杖（留空＝不更動）<input v-model="edit[t.id].token" type="password" :placeholder="t.token_set ? '已設定 ' + t.token_hint : '未設定'" /></label>
            <label>目標 ID<input v-model="edit[t.id].target_id" /></label>
          </div>
          <div class="actions">
            <button class="primary" @click="saveEdit(t)">儲存</button>
            <button class="ghost" @click="delete edit[t.id]">取消</button>
          </div>
        </template>
        <template v-else>
          <div class="info">
            <div class="name">
              {{ t.name }}
              <span class="badge">{{ label(t.platform) }}</span>
              <span class="badge" :class="t.enabled ? 'on' : 'off'">{{ t.enabled ? '啟用' : '停用' }}</span>
            </div>
            <div class="meta">
              權杖：{{ t.token_set ? '已設定 ' + t.token_hint : '未設定' }} ｜ 目標：{{ t.target_id || '未設定' }}
            </div>
          </div>
          <div class="actions">
            <button class="ghost" @click="toggleEnabled(t)">{{ t.enabled ? '停用' : '啟用' }}</button>
            <button class="ghost" @click="startEdit(t)">編輯</button>
            <button class="danger" @click="removeTarget(t)">刪除</button>
          </div>
        </template>
      </li>
    </ul>
  </section>
</template>

<style scoped>
h1 { margin-top: 0; }
h2 { margin: 0 0 12px; font-size: 1.05rem; }
.error { color: #cf1124; }
.hint { color: #627d98; font-size: 0.88rem; line-height: 1.6; }
.empty { color: #829ab1; }
.panel { background: #fff; border: 1px solid #e4e7eb; border-radius: 12px; padding: 16px 18px; margin: 14px 0; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.grid label { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; color: #486581; }
.grid input, .grid select { padding: 7px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.row { background: #fff; border: 1px solid #e4e7eb; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.info { flex: 1; min-width: 220px; }
.name { font-weight: 600; display: flex; align-items: center; gap: 8px; }
.meta { color: #627d98; font-size: 0.85rem; margin-top: 4px; }
.badge { font-size: 0.72rem; padding: 1px 8px; border-radius: 999px; background: #e4e7eb; color: #486581; font-weight: 500; }
.badge.on { background: #def7ec; color: #03543f; }
.badge.off { background: #fbeae5; color: #cf1124; }
.actions { display: flex; gap: 8px; }
.actions button { font-size: 0.85rem; padding: 6px 12px; border: none; border-radius: 8px; }
.primary { background: #2680c2; color: #fff; border: none; border-radius: 8px; padding: 7px 14px; }
.ghost { background: #e4e7eb; color: #334e68; }
.danger { background: #fbeae5; color: #cf1124; }
</style>
