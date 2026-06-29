<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../api'
import CadreNav from '../components/CadreNav.vue'

const targets = ref([])
const error = ref('')
const showTokenHelp = ref(false) // 機器人金鑰（bot token）申請教學
const showChatIdHelp = ref(false) // 群組編號（chat_id）取得教學
const form = reactive({ name: '', token: '', target_id: '' })
const edit = reactive({}) // { [id]: 暫存編輯 }

function tokenLabel(t) { return t.token ? '已設定 ' + t.token.slice(0, 6) + '…' : '未設定' }

async function load() {
  try { targets.value = await api.listTargets() } catch (e) { error.value = e.message }
}
async function addTarget() {
  if (!form.name.trim()) { error.value = '請輸入名稱'; return }
  try {
    await api.createTarget({ name: form.name.trim(), token: form.token, target_id: form.target_id })
    form.name = ''; form.token = ''; form.target_id = ''
    error.value = ''
    await load()
  } catch (e) { error.value = e.message }
}
function startEdit(t) {
  edit[t.id] = { name: t.name, target_id: t.target_id, token: '', enabled: t.enabled }
}
async function saveEdit(t) {
  try {
    await api.updateTarget(t.id, edit[t.id]) // token 留空＝不更動
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

const copied = ref('')
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = text
    setTimeout(() => { if (copied.value === text) copied.value = '' }, 1500)
  } catch { /* fallback: do nothing */ }
}

onMounted(load)
</script>

<template>
  <section>
    <CadreNav />
    <h1>發布設定（Telegram）</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <p class="hint">
      設定好之後，就能在卡片／班表的「發布」視窗，一鍵把內容自動送到指定的 Telegram 群組。
      金鑰與群組編號只存在這支手機，不會上傳任何伺服器。下方每個欄位都有「?」說明。
    </p>

    <div class="panel add">
      <h2>新增發布目標</h2>
      <div class="grid">
        <label>
          <span class="ttl">名稱</span>
          <span class="desc">自己看的備註，例如「工作室主群」</span>
          <input v-model="form.name" placeholder="例如：工作室主群" />
        </label>
        <label>
          <span class="ttl-row">
            <span class="ttl">機器人金鑰</span>
            <button type="button" class="help-btn" title="如何申請機器人與取得金鑰？" @click="showTokenHelp = true">?</button>
          </span>
          <span class="desc">向 Telegram 的 @BotFather 申請的一串密碼，讓系統能用機器人發訊息</span>
          <input v-model="form.token" type="password" autocomplete="off" placeholder="貼上申請到的金鑰" />
        </label>
        <label>
          <span class="ttl-row">
            <span class="ttl">要發到哪個群組</span>
            <button type="button" class="help-btn" title="如何取得群組編號？" @click="showChatIdHelp = true">?</button>
          </span>
          <span class="desc">群組的編號（Telegram 稱為 chat_id），訊息會送到這個群組</span>
          <input v-model="form.target_id" placeholder="例如：-1001234567890" />
        </label>
      </div>
      <button class="primary" @click="addTarget">＋ 新增</button>
    </div>

    <p v-if="targets.length === 0" class="empty">尚無發布目標。</p>
    <ul class="list">
      <li v-for="t in targets" :key="t.id" class="row">
        <template v-if="edit[t.id]">
          <div class="grid">
            <label><span class="ttl">名稱</span><input v-model="edit[t.id].name" /></label>
            <label><span class="ttl">機器人金鑰（留空＝不更動）</span><input v-model="edit[t.id].token" type="password" autocomplete="off" :placeholder="tokenLabel(t)" /></label>
            <label><span class="ttl">要發到哪個群組</span><input v-model="edit[t.id].target_id" placeholder="例如：-1001234567890" /></label>
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
              <span class="badge">Telegram</span>
              <span class="badge" :class="t.enabled ? 'on' : 'off'">{{ t.enabled ? '啟用' : '停用' }}</span>
            </div>
            <div class="meta">金鑰：{{ tokenLabel(t) }} ｜ 群組：{{ t.target_id || '未設定' }}</div>
          </div>
          <div class="actions">
            <button class="ghost" @click="toggleEnabled(t)">{{ t.enabled ? '停用' : '啟用' }}</button>
            <button class="ghost" @click="startEdit(t)">編輯</button>
            <button class="danger" @click="removeTarget(t)">刪除</button>
          </div>
        </template>
      </li>
    </ul>

    <!-- 機器人金鑰申請教學 -->
    <div v-if="showTokenHelp" class="modal-backdrop" @click.self="showTokenHelp = false">
      <div class="modal">
        <header class="modal-head">
          <h2>怎麼申請機器人並取得金鑰？</h2>
          <button type="button" class="x" @click="showTokenHelp = false">✕</button>
        </header>
        <ol class="steps">
          <li>在 Telegram 搜尋並開啟官方的 <b>@BotFather</b>（有藍色認證勾勾）。</li>
          <li>對它輸入指令 <code>/newbot</code><button type="button" class="copy-btn" :class="{ copied: copied === '/newbot' }" @click="copyText('/newbot')">{{ copied === '/newbot' ? '已複製' : '複製' }}</button>，按它的指示操作。</li>
          <li>先取一個<b>機器人名稱</b>（顯示用，可中文）。</li>
          <li>再取一個<b>使用者名稱</b>，<b>必須以 <code>bot</code> 結尾</b>（例如 <code>myshop_bot</code>），且不能重複。</li>
          <li>完成後 BotFather 會回一段訊息，裡面的 <b>HTTP API token</b> 就是金鑰，格式像 <code>123456789:AAE…</code>，把它整串複製貼回上面欄位。</li>
        </ol>
        <p class="note">小提醒：金鑰等於機器人的密碼，請勿外流。若不慎外洩，可在 BotFather 用 <code>/revoke</code><button type="button" class="copy-btn" :class="{ copied: copied === '/revoke' }" @click="copyText('/revoke')">{{ copied === '/revoke' ? '已複製' : '複製' }}</button> 重新產生一組新金鑰。</p>
      </div>
    </div>

    <!-- 群組編號取得教學 -->
    <div v-if="showChatIdHelp" class="modal-backdrop" @click.self="showChatIdHelp = false">
      <div class="modal">
        <header class="modal-head">
          <h2>怎麼取得群組編號（chat_id）？</h2>
          <button type="button" class="x" @click="showChatIdHelp = false">✕</button>
        </header>
        <ol class="steps">
          <li>先到 Telegram 用 <b>@BotFather</b> 建立一個機器人，並複製它給你的「機器人金鑰」。</li>
          <li>把這個機器人<b>加入你要發送的群組</b>。</li>
          <li>在群組裡<b>隨便發一則訊息</b>（讓機器人收得到）。</li>
          <li>用瀏覽器打開這個網址（把 <code>金鑰</code> 換成你的機器人金鑰）：
            <span class="url-row">
              <code class="url">https://api.telegram.org/bot金鑰/getUpdates</code>
              <button type="button" class="copy-btn" :class="{ copied: copied === 'https://api.telegram.org/bot金鑰/getUpdates' }" @click="copyText('https://api.telegram.org/bot金鑰/getUpdates')">{{ copied === 'https://api.telegram.org/bot金鑰/getUpdates' ? '已複製' : '複製' }}</button>
            </span>
          </li>
          <li>在跳出的內容裡找到 <code>"chat":{"id":-100…}</code>，那個 <b>id</b> 就是群組編號，貼回上面欄位即可。</li>
        </ol>
        <p class="note">小提醒：群組編號通常是<b>負數</b>。若網址打開後沒看到資料，先回群組再發一則訊息，然後重新整理網址。</p>
      </div>
    </div>
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
.grid .ttl { font-weight: 600; color: #334e68; }
.grid .ttl-row { display: flex; align-items: center; gap: 6px; }
.help-btn { width: 18px; height: 18px; flex: none; padding: 0; border: none; border-radius: 50%; background: #2680c2; color: #fff; font-size: 0.72rem; font-weight: 700; line-height: 18px; text-align: center; cursor: pointer; }
.help-btn:hover { background: #186faf; }
.grid .desc { font-size: 0.75rem; font-weight: 400; color: #829ab1; line-height: 1.4; }
.grid input { padding: 7px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; }
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

.modal-backdrop { position: fixed; inset: 0; background: rgba(16,42,67,0.45); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 16px; }
.modal { background: #fff; border-radius: 14px; width: 460px; max-width: 92vw; max-height: 90vh; overflow-y: auto; padding: 18px 20px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.modal-head h2 { margin: 0; font-size: 1.1rem; }
.modal-head .x { border: none; background: #e4e7eb; border-radius: 8px; width: 30px; height: 30px; cursor: pointer; }
.steps { margin: 0; padding-left: 1.2em; color: #334e68; font-size: 0.9rem; line-height: 1.7; }
.steps li { margin-bottom: 8px; }
.steps code { background: #f0f4f8; border-radius: 4px; padding: 1px 5px; font-size: 0.85rem; color: #0a558c; }
.steps code.url { display: block; margin-top: 4px; word-break: break-all; }
.copy-btn { display: inline-flex; align-items: center; margin-left: 6px; padding: 1px 8px; border: 1px solid #cbd2d9; border-radius: 6px; background: #f0f4f8; color: #486581; font-size: 0.75rem; cursor: pointer; white-space: nowrap; vertical-align: middle; transition: background 0.15s, color 0.15s, border-color 0.15s; }
.copy-btn:hover { background: #d9e2ec; border-color: #9fb3c8; }
.copy-btn.copied { background: #def7ec; color: #03543f; border-color: #8bc5a7; }
.url-row { display: flex; align-items: flex-start; gap: 6px; margin-top: 4px; }
.url-row .url { margin-top: 0; flex: 1; }
.url-row .copy-btn { flex: none; margin-left: 0; margin-top: 2px; }
.note { margin: 12px 0 0; padding: 10px 12px; background: #fff8e6; border-radius: 8px; color: #8a6d3b; font-size: 0.85rem; line-height: 1.6; }

@media (max-width: 640px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
