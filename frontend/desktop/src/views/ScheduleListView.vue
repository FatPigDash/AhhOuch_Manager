<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import StoreNav from '../components/StoreNav.vue'

const router = useRouter()
const schedules = ref([])
const error = ref('')

async function load() {
  try { schedules.value = await api.listSchedules() } catch (e) { error.value = e.message }
}
async function addSchedule() {
  try {
    const s = await api.createSchedule('')
    router.push({ name: 'schedule-edit', params: { id: s.id } })
  } catch (e) { error.value = e.message }
}
async function removeSchedule(s) {
  if (!confirm('刪除這份班表草稿？')) return
  try { await api.deleteSchedule(s.id); await load() } catch (e) { error.value = e.message }
}
function open(s) { router.push({ name: 'schedule-edit', params: { id: s.id } }) }
function firstLine(title) { return (title || '').split('\n')[0] || '（未命名班表）' }
function fmtDate(s) { return (s || '').replace('T', ' ').slice(0, 16) }

onMounted(load)
</script>

<template>
  <section>
    <StoreNav />
    <div class="head">
      <h1>班表</h1>
      <button class="primary" @click="addSchedule">＋ 新增班表</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <p class="hint">發布後會留存為草稿，可再次編輯與發布。</p>

    <p v-if="schedules.length === 0" class="empty">尚無班表，點「＋ 新增班表」開始。</p>

    <ul class="list">
      <li v-for="s in schedules" :key="s.id" class="row">
        <div class="info" @click="open(s)">
          <div class="title">{{ firstLine(s.title) }}</div>
          <div class="meta">{{ s.entry_count }} 位出勤 ｜ 更新 {{ fmtDate(s.updated_at) }}</div>
        </div>
        <div class="actions">
          <button class="ghost" @click.stop="open(s)">編輯</button>
          <button class="danger" @click.stop="removeSchedule(s)">刪除</button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.head { display: flex; align-items: center; justify-content: space-between; }
h1 { margin: 0; }
.error { color: #cf1124; }
.hint { color: #829ab1; font-size: 0.85rem; }
.empty { color: #829ab1; }
.list { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid #e4e7eb; border-radius: 10px; padding: 12px 16px; }
.info { cursor: pointer; flex: 1; }
.title { font-weight: 600; }
.meta { color: #627d98; font-size: 0.85rem; margin-top: 2px; }
.actions { display: flex; gap: 8px; }
.actions button { font-size: 0.85rem; padding: 6px 12px; border: none; border-radius: 8px; }
.primary { background: #2680c2; color: #fff; border: none; border-radius: 8px; padding: 8px 14px; }
.ghost { background: #e4e7eb; color: #334e68; }
.danger { background: #fbeae5; color: #cf1124; }
</style>
