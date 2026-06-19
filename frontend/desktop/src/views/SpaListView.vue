<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const spas = ref([])
const newName = ref('')
const error = ref('')
const editingId = ref(null)
const editForm = ref({ name: '', address: '', staff: '' })

async function load() {
  try {
    spas.value = await api.listSpas()
  } catch (e) {
    error.value = e.message
  }
}

async function addSpa() {
  const name = newName.value.trim()
  if (!name) return
  try {
    await api.createSpa({ name })
    newName.value = ''
    await load()
  } catch (e) {
    error.value = e.message
  }
}

function startEdit(spa) {
  editingId.value = spa.id
  editForm.value = { name: spa.name, address: spa.address, staff: spa.staff }
}

async function saveEdit(id) {
  try {
    await api.updateSpa(id, editForm.value)
    editingId.value = null
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function removeSpa(spa) {
  if (!confirm(`確定刪除「${spa.name}」？看板與卡片都會一併刪除。`)) return
  try {
    await api.deleteSpa(spa.id)
    await load()
  } catch (e) {
    error.value = e.message
  }
}

function open(spa) {
  router.push({ name: 'spa-board', params: { id: spa.id } })
}

onMounted(load)
</script>

<template>
  <section>
    <h1>養身館</h1>
    <p v-if="error" class="error">{{ error }}</p>

    <form class="add-bar" @submit.prevent="addSpa">
      <input v-model="newName" placeholder="輸入養身館名稱即可建立" maxlength="100" />
      <button type="submit">＋ 新增養身館</button>
    </form>

    <p v-if="spas.length === 0" class="empty">尚無養身館，請先新增一間。</p>

    <ul class="spa-grid">
      <li v-for="spa in spas" :key="spa.id" class="spa-card">
        <template v-if="editingId === spa.id">
          <div class="edit-form">
            <label>名稱<input v-model="editForm.name" /></label>
            <label>地址<input v-model="editForm.address" placeholder="選填" /></label>
            <label>幹部<input v-model="editForm.staff" placeholder="選填" /></label>
            <div class="actions">
              <button @click="saveEdit(spa.id)">儲存</button>
              <button class="ghost" @click="editingId = null">取消</button>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="spa-body" @click="open(spa)">
            <h3>{{ spa.name }}</h3>
            <p v-if="spa.address" class="meta">📍 {{ spa.address }}</p>
            <p v-if="spa.staff" class="meta">👤 {{ spa.staff }}</p>
          </div>
          <div class="actions">
            <button class="ghost" @click.stop="startEdit(spa)">編輯</button>
            <button class="danger" @click.stop="removeSpa(spa)">刪除</button>
          </div>
        </template>
      </li>
    </ul>
  </section>
</template>

<style scoped>
h1 { margin-top: 0; }
.error { color: #cf1124; }
.empty { color: #829ab1; }
.add-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}
.add-bar input {
  flex: 1;
  max-width: 360px;
  padding: 8px 12px;
  border: 1px solid #cbd2d9;
  border-radius: 8px;
}
.add-bar button, .actions button {
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: #2680c2;
  color: #fff;
}
.spa-grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.spa-card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.spa-body { cursor: pointer; }
.spa-body h3 { margin: 0 0 8px; }
.meta { margin: 2px 0; color: #486581; font-size: 0.9rem; }
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.actions button { font-size: 0.85rem; }
.ghost { background: #e4e7eb; color: #334e68; }
.danger { background: #fbeae5; color: #cf1124; }
.edit-form { display: flex; flex-direction: column; gap: 8px; }
.edit-form label { display: flex; flex-direction: column; font-size: 0.85rem; color: #486581; gap: 4px; }
.edit-form input { padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 6px; }
</style>
