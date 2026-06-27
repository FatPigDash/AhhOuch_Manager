<script setup>
import { ref, onMounted } from 'vue'
import CadreNav from '../components/CadreNav.vue'
import { exportBackup, importBackup, fileIsEncrypted } from '../backup'
import { canShareFiles, share } from '../share'
import { getLastBackup, setLastBackupNow } from '../backupMeta'

const busy = ref(false)
const error = ref('')
const okMsg = ref('')
const lastBackup = ref(null)

// 匯出
const exportPassword = ref('')

// 匯入
const importFile = ref(null)
const importFileEncrypted = ref(false)
const importPassword = ref('')
const fileInput = ref(null)

function fmt(iso) { return iso ? iso.replace('T', ' ').slice(0, 16) : '尚未備份' }
function refreshLast() { lastBackup.value = getLastBackup() }

function reset() { error.value = ''; okMsg.value = '' }

async function doDownload() {
  reset(); busy.value = true
  try {
    const { bytes, filename } = await exportBackup(exportPassword.value)
    const blob = new Blob([bytes], { type: 'application/octet-stream' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
    setLastBackupNow(); refreshLast()
    okMsg.value = `已產生備份檔「${filename}」${exportPassword.value ? '（已加密）' : ''}，請存到雲端硬碟。`
  } catch (e) { error.value = '匯出失敗：' + e.message }
  finally { busy.value = false }
}

async function doShare() {
  reset(); busy.value = true
  try {
    const { bytes, filename } = await exportBackup(exportPassword.value)
    const file = new File([bytes], filename, { type: 'application/octet-stream' })

    // 嘗試系統分享選單（iOS / Android 原生）
    if (canShareFiles([file])) {
      try {
        const result = await share({ title: filename, files: [file] })
        if (result === 'shared') {
          setLastBackupNow(); refreshLast()
          okMsg.value = '已開啟分享選單，請選擇「儲存到檔案」(iOS) 或「存到 Google Drive」(Android) 完成備份。'
          return
        }
        if (result === 'cancelled') return  // 使用者自行取消，不顯示錯誤
      } catch {
        // 瀏覽器拒絕（如 iOS 安全限制），改用下載
      }
    }

    // 退回下載：iOS 存到「檔案」App → 可選 iCloud Drive；Android 存到下載資料夾
    const blob = new Blob([bytes], { type: 'application/octet-stream' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
    setLastBackupNow(); refreshLast()
    okMsg.value = `備份檔已儲存！iOS 請到「檔案」App → iCloud Drive 確認；Android 請到下載資料夾查看。`
  } catch (e) { error.value = '備份失敗：' + e.message }
  finally { busy.value = false }
}

async function onPickFile(e) {
  reset()
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) return
  importFile.value = f
  importPassword.value = ''
  try { importFileEncrypted.value = await fileIsEncrypted(f) }
  catch { importFileEncrypted.value = false }
}

async function doImport() {
  reset()
  if (!importFile.value) return
  if (importFileEncrypted.value && !importPassword.value) { error.value = '此備份檔已加密，請先輸入密碼。'; return }
  if (!confirm('還原會以備份內容「覆蓋」目前手機上的所有資料（卡片、圖片、班表），且無法復原。確定要繼續嗎？')) return
  busy.value = true
  try {
    const r = await importBackup(importFile.value, importPassword.value)
    okMsg.value = `還原完成：${r.cards} 張卡片、${r.images} 張圖片、${r.schedules} 份班表。`
    importFile.value = null
    importFileEncrypted.value = false
    importPassword.value = ''
  } catch (e) { error.value = '還原失敗：' + e.message }
  finally { busy.value = false }
}

onMounted(refreshLast)
</script>

<template>
  <section class="backup">
    <CadreNav />
    <h1>備份與還原</h1>
    <p class="hint">資料只存在這支手機。建議每月匯出備份到自己的雲端硬碟（iCloud／Google Drive），換機或清除快取時才能還原。</p>
    <p class="last">上次備份：<strong>{{ fmt(lastBackup) }}</strong></p>

    <p v-if="error" class="msg error">{{ error }}</p>
    <p v-if="okMsg" class="msg ok">{{ okMsg }}</p>

    <!-- 匯出 -->
    <div class="panel">
      <h2>匯出備份</h2>
      <label class="field">
        <span>密碼（選填，留空＝不加密）</span>
        <input v-model="exportPassword" type="password" autocomplete="new-password" placeholder="設定密碼以加密備份檔" />
      </label>
      <p class="warn" v-if="exportPassword">⚠ 加密後若忘記此密碼，備份將永遠無法還原，請務必記住。</p>
      <div class="actions">
        <button class="primary" :disabled="busy" @click="doShare">📤 備份到雲端</button>
        <button class="ghost" :disabled="busy" @click="doDownload">⬇ 下載備份檔</button>
      </div>
      <p class="hint">點「📤 備份到雲端」自動儲存備份檔。iOS 會存到「檔案」App（可選 iCloud Drive）；Android 會存到下載資料夾。</p>
    </div>

    <!-- 匯入 -->
    <div class="panel">
      <h2>匯入還原</h2>
      <div class="actions">
        <button class="ghost" :disabled="busy" @click="fileInput.click()">📁 選擇備份檔</button>
        <span v-if="importFile" class="filename">{{ importFile.name }}{{ importFileEncrypted ? '（已加密）' : '' }}</span>
        <input ref="fileInput" type="file" accept=".ahbk,.zip" hidden @change="onPickFile" />
      </div>
      <label v-if="importFile && importFileEncrypted" class="field">
        <span>備份密碼</span>
        <input v-model="importPassword" type="password" autocomplete="off" placeholder="輸入匯出時設定的密碼" />
      </label>
      <button class="danger" :disabled="busy || !importFile" @click="doImport">⟳ 覆蓋還原</button>
      <p class="hint">還原會覆蓋目前所有資料，請先確認已備份現有內容。</p>
    </div>
  </section>
</template>

<style scoped>
.backup { max-width: 640px; }
h1 { margin: 0 0 6px; }
h2 { margin: 0 0 12px; font-size: 1.1rem; }
.hint { color: #829ab1; font-size: 0.85rem; }
.last { color: #486581; font-size: 0.9rem; }
.msg { padding: 8px 12px; border-radius: 8px; font-size: 0.9rem; }
.msg.error { background: #fbeae5; color: #cf1124; }
.msg.ok { background: #e3f9ec; color: #207544; }
.warn { color: #b7791f; font-size: 0.85rem; margin: 4px 0 0; }
.panel { background: #fff; border: 1px solid #e4e7eb; border-radius: 12px; padding: 16px 18px; margin-top: 16px; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; color: #486581; margin-bottom: 10px; }
.field input { padding: 8px 10px; border: 1px solid #cbd2d9; border-radius: 8px; font-size: 0.95rem; color: #1f2933; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 8px; }
.filename { font-size: 0.85rem; color: #334e68; }
button { border: none; border-radius: 8px; padding: 9px 16px; font-size: 0.95rem; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
.primary { background: #2680c2; color: #fff; }
.ghost { background: #e4e7eb; color: #334e68; }
.danger { background: #fbeae5; color: #cf1124; }
</style>
