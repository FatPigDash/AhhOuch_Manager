<script setup>
import { ref, onMounted } from 'vue'
import { api } from './api'
import { backupOverdue } from './backupMeta'

const title = ref('AhhOuch')
const showBackupReminder = ref(false)  // 每月備份提醒橫幅（M6）

onMounted(async () => {
  try {
    const meta = await api.meta()
    title.value = meta.title
    document.title = meta.title
  } catch (_) { /* 後端未連線時沿用預設標題 */ }

  // 逾一個月（或從未備份）且已有資料時，提醒匯出備份。
  try {
    if (backupOverdue()) {
      const cards = await api.listCadreCards()
      const schedules = await api.listSchedules()
      if (cards.length || schedules.length) showBackupReminder.value = true
    }
  } catch (_) { /* 提醒非關鍵，失敗則略過 */ }
})
</script>

<template>
  <header class="app-header">
    <router-link to="/" class="brand">{{ title }}</router-link>
  </header>
  <div v-if="showBackupReminder" class="backup-reminder">
    <span>📦 距離上次備份已超過一個月，建議匯出備份到雲端以防資料遺失。</span>
    <span class="reminder-actions">
      <router-link :to="{ name: 'backup' }" class="reminder-go" @click="showBackupReminder = false">前往備份</router-link>
      <button class="reminder-x" @click="showBackupReminder = false" title="關閉">✕</button>
    </span>
  </div>
  <main class="app-main">
    <router-view />
  </main>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 12px;
  padding: 14px 24px;
  background: #102a43;
  color: #fff;
}
.brand {
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
}
.backup-reminder {
  display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;
  background: #fffaeb; color: #8d6708; border-bottom: 1px solid #f7e9b8;
  padding: 10px 24px; font-size: 0.9rem;
}
.reminder-actions { display: flex; align-items: center; gap: 10px; }
.reminder-go { color: #0a558c; font-weight: 600; text-decoration: none; white-space: nowrap; }
.reminder-x { border: none; background: transparent; color: #8d6708; font-size: 0.95rem; cursor: pointer; }
.app-main {
  padding: 24px;
}
@media (max-width: 640px) { .backup-reminder { padding: 10px 14px; } }
@media (max-width: 640px) {
  .app-header { padding: 10px 14px; }
  .brand { font-size: 1.1rem; }
  .app-main { padding: 14px; }
}
</style>
