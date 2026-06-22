<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Sortable from 'sortablejs'
import { api } from '../api'

const router = useRouter()
const spas = ref([])
const newName = ref('')
const error = ref('')
const editingId = ref(null)
const editForm = ref({ name: '', address: '', staff_members: [] })
const grid = ref(null)
let sortable = null

async function load() {
  try {
    spas.value = await api.listSpas()
    await nextTick()
    initSortable()
  } catch (e) {
    error.value = e.message
  }
}

// --- 拖曳改變養身館順序 (C3)，由把手觸發，插入位置以虛線標示 ---
function destroySortable() {
  sortable?.destroy()
  sortable = null
}
function initSortable() {
  destroySortable()
  if (!grid.value) return
  sortable = Sortable.create(grid.value, {
    draggable: '.spa-card',
    handle: '.spa-drag',
    animation: 150,
    ghostClass: 'spa-ghost', // 插入位置的明確標示
    onEnd,
  })
}
async function onEnd(evt) {
  const spaId = Number(evt.item.dataset.spaId)
  const newIndex = evt.newIndex
  // 還原 DOM，交由後端資料重新渲染為唯一事實來源
  const refNode = evt.from.children[evt.oldIndex] || null
  evt.from.insertBefore(evt.item, refNode)
  try {
    await api.moveSpa(spaId, { position: newIndex })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
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
  editForm.value = {
    name: spa.name,
    address: spa.address,
    // 複製一份幹部清單供編輯（含聯絡資訊），避免直接改到列表資料
    staff_members: (spa.staff_members || []).map((m) => ({
      name: m.name,
      contact: m.contact || '',
    })),
  }
}

function addStaff() {
  editForm.value.staff_members.push({ name: '', contact: '' })
}
function removeStaff(idx) {
  editForm.value.staff_members.splice(idx, 1)
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
onBeforeUnmount(destroySortable)
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

    <ul class="spa-grid" ref="grid">
      <li
        v-for="spa in spas"
        :key="spa.id"
        class="spa-card"
        :data-spa-id="spa.id"
      >
        <template v-if="editingId === spa.id">
          <div class="edit-form">
            <label>名稱<input v-model="editForm.name" /></label>
            <label>地址<input v-model="editForm.address" placeholder="選填" /></label>
            <div class="staff-edit">
              <span class="staff-edit-title">幹部（可多位）</span>
              <div
                v-for="(m, idx) in editForm.staff_members"
                :key="idx"
                class="staff-row"
              >
                <div class="staff-fields">
                  <label class="staff-field">
                    <span>幹部名稱</span>
                    <input v-model="m.name" placeholder="選填" />
                  </label>
                  <label class="staff-field">
                    <span>聯絡資訊</span>
                    <input v-model="m.contact" placeholder="選填" />
                  </label>
                </div>
                <button
                  class="staff-del"
                  type="button"
                  title="移除此幹部"
                  @click="removeStaff(idx)"
                >
                  ✕
                </button>
              </div>
              <button class="ghost staff-add" type="button" @click="addStaff">
                ＋ 新增幹部
              </button>
            </div>
            <div class="actions">
              <button @click="saveEdit(spa.id)">儲存</button>
              <button class="ghost" @click="editingId = null">取消</button>
            </div>
          </div>
        </template>
        <template v-else>
          <span class="spa-drag" title="拖曳調整養身館順序">⠿</span>
          <div class="spa-body" @click="open(spa)">
            <h3>{{ spa.name }}</h3>
            <p v-if="spa.address" class="meta">📍 {{ spa.address }}</p>
            <p
              v-for="m in spa.staff_members"
              :key="m.id"
              class="meta"
            >
              👤 {{ m.name }}<span v-if="m.contact" class="staff-contact">．{{ m.contact }}</span>
            </p>
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
  position: relative;
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
/* 拖曳把手：只由此處觸發排序，避免與點擊開啟、編輯/刪除按鈕衝突 */
.spa-drag {
  position: absolute;
  top: 8px;
  right: 10px;
  cursor: grab;
  color: #9fb3c8;
  font-size: 1rem;
  line-height: 1;
  user-select: none;
}
.spa-drag:active { cursor: grabbing; }
/* 拖曳時的插入位置標示（虛線框） */
.spa-ghost {
  outline: 2px dashed #2680c2;
  outline-offset: -2px;
  background: #e3f0fb;
  opacity: 0.6;
}
.spa-body { cursor: pointer; padding-right: 18px; }
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
.staff-contact { color: #627d98; }
/* 幹部編輯區（可多位，各含聯絡資訊） */
.staff-edit { display: flex; flex-direction: column; gap: 6px; }
.staff-edit-title { font-size: 0.85rem; color: #486581; }
/* 每位幹部：第一行「幹部名稱＋輸入框」、第二行「聯絡資訊＋輸入框」，移除鈕在右側 */
.staff-row { display: flex; gap: 6px; align-items: stretch; }
.staff-fields { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.edit-form .staff-field { flex-direction: row; align-items: center; gap: 8px; }
.edit-form .staff-field > span { flex: 0 0 auto; width: 4.5em; color: #486581; }
.edit-form .staff-field > input { flex: 1; min-width: 0; padding: 6px 10px; border: 1px solid #cbd2d9; border-radius: 6px; }
.staff-del {
  flex: 0 0 auto;
  background: #fbeae5;
  color: #cf1124;
  border: none;
  border-radius: 6px;
  padding: 6px 10px;
}
.staff-add { align-self: flex-start; font-size: 0.85rem; padding: 6px 12px; }
</style>
