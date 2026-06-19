<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Sortable from 'sortablejs'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const spa = ref(null)
const error = ref('')
const boardRow = ref(null)
const boardsContainer = ref(null)
let sortables = []
const newBoardName = ref('')
// 各看板正在輸入的新卡片標題：{ [boardId]: title }
const newCardTitle = ref({})
const editingBoardId = ref(null)
const editingBoardName = ref('')

async function load() {
  destroySortables()
  try {
    spa.value = await api.getSpa(props.id)
    await nextTick()
    initSortables()
  } catch (e) {
    error.value = e.message
  }
}

// --- 拖曳 (C9) ---
function destroySortables() {
  sortables.forEach((s) => s.destroy())
  sortables = []
}

function initSortables() {
  if (!boardRow.value) return
  // 卡片拖曳 (C9)
  boardRow.value.querySelectorAll('.card-list').forEach((el) => {
    const manual = el.dataset.sortMode === 'manual'
    sortables.push(
      Sortable.create(el, {
        group: 'cards',          // 同群組 → 同／跨看板皆可拖曳
        animation: 150,
        ghostClass: 'card-ghost', // 插入位置的明確標示
        sort: manual,            // 預設(Unicode) 模式不可板內重排，仍可跨板拖入/拖出
        onEnd,
      })
    )
  })
  // 看板拖曳排序 (C5)：只由標題列的把手觸發，避免與卡片拖曳衝突
  if (boardsContainer.value) {
    sortables.push(
      Sortable.create(boardsContainer.value, {
        group: 'boards',
        draggable: '.board-col',
        handle: '.board-drag',
        animation: 150,
        ghostClass: 'board-ghost',
        onEnd: onBoardEnd,
      })
    )
  }
}

async function onEnd(evt) {
  const item = evt.item
  const cardId = Number(item.dataset.cardId)
  const toBoardId = Number(evt.to.dataset.boardId)
  const newIndex = evt.newIndex
  // 先把 DOM 還原，讓 Vue（依後端資料）重新渲染為唯一事實來源，避免與 Sortable 衝突
  const refNode = evt.from.children[evt.oldIndex] || null
  evt.from.insertBefore(item, refNode)
  try {
    await api.moveCard(cardId, { board_id: toBoardId, position: newIndex })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
  }
}

// --- 按住空白處左右拖曳捲動整個看板畫面（Trello 式 panning）---
let isPanning = false
let panStartX = 0
let panStartScroll = 0

function onPanStart(e) {
  if (e.button !== 0 || !boardRow.value) return
  // 只在空白區域啟動：避開卡片、看板把手、輸入框與按鈕，以免干擾原有操作
  if (e.target.closest('.card, .board-drag, .board-head h3, input, textarea, button, a')) return
  isPanning = true
  panStartX = e.clientX
  panStartScroll = boardRow.value.scrollLeft
  boardRow.value.classList.add('panning')
}
function onPanMove(e) {
  if (!isPanning || !boardRow.value) return
  boardRow.value.scrollLeft = panStartScroll - (e.clientX - panStartX)
}
function onPanEnd() {
  if (!isPanning) return
  isPanning = false
  boardRow.value?.classList.remove('panning')
}

async function onBoardEnd(evt) {
  const boardId = Number(evt.item.dataset.boardId)
  const newIndex = evt.newIndex
  // 還原 DOM，交由後端資料重新渲染
  const refNode = evt.from.children[evt.oldIndex] || null
  evt.from.insertBefore(evt.item, refNode)
  try {
    await api.moveBoard(boardId, { position: newIndex })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
  }
}

async function setSort(board, mode) {
  if (board.sort_mode === mode) return
  try {
    await api.updateBoard(board.id, { sort_mode: mode })
    await load()
  } catch (e) { error.value = e.message }
}

async function addBoard() {
  const name = newBoardName.value.trim()
  if (!name) return
  try {
    await api.createBoard(props.id, { name })
    newBoardName.value = ''
    await load()
  } catch (e) { error.value = e.message }
}

function startBoardEdit(board) {
  editingBoardId.value = board.id
  editingBoardName.value = board.name
}
async function saveBoardName(board) {
  const name = editingBoardName.value.trim()
  if (!name) return
  try {
    await api.updateBoard(board.id, { name })
    editingBoardId.value = null
    await load()
  } catch (e) { error.value = e.message }
}
async function removeBoard(board) {
  if (!confirm(`刪除看板「${board.name}」？板內卡片會一併刪除。`)) return
  try {
    await api.deleteBoard(board.id)
    await load()
  } catch (e) { error.value = e.message }
}

async function addCard(board) {
  const title = (newCardTitle.value[board.id] || '').trim()
  if (!title) return
  try {
    await api.createCard(board.id, { title })
    newCardTitle.value[board.id] = ''
    await load()
  } catch (e) { error.value = e.message }
}

function openCard(card) {
  router.push({ name: 'card-detail', params: { id: card.id } })
}
async function removeCard(card) {
  if (!confirm(`刪除卡片「${card.title}」？`)) return
  try {
    await api.deleteCard(card.id)
    await load()
  } catch (e) { error.value = e.message }
}

onMounted(() => {
  load()
  document.addEventListener('pointermove', onPanMove)
  document.addEventListener('pointerup', onPanEnd)
})
onBeforeUnmount(() => {
  destroySortables()
  document.removeEventListener('pointermove', onPanMove)
  document.removeEventListener('pointerup', onPanEnd)
})
</script>

<template>
  <section v-if="spa">
    <div class="page-head">
      <button class="back" @click="router.push('/')">← 養身館列表</button>
      <h1>{{ spa.name }}</h1>
      <span v-if="spa.address" class="meta">📍 {{ spa.address }}</span>
      <span v-if="spa.staff" class="meta">👤 {{ spa.staff }}</span>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="board-row" ref="boardRow" @pointerdown="onPanStart">
      <div class="boards" ref="boardsContainer">
      <div v-for="board in spa.boards" :key="board.id" class="board board-col" :data-board-id="board.id">
        <header class="board-head">
          <span class="board-drag" title="拖曳調整看板順序">⠿</span>
          <template v-if="editingBoardId === board.id">
            <input
              v-model="editingBoardName"
              @keyup.enter="saveBoardName(board)"
              @blur="saveBoardName(board)"
              autofocus
            />
          </template>
          <template v-else>
            <h3 @click="startBoardEdit(board)" title="點擊改名">{{ board.name }}</h3>
            <span class="count">{{ board.cards.length }}</span>
            <button class="board-del" @click="removeBoard(board)" title="刪除看板">✕</button>
          </template>
        </header>

        <div class="sort-pills" role="group" aria-label="排序方式">
          <span class="sort-label">排序方式</span>
          <button
            class="pill"
            :class="{ active: board.sort_mode === 'unicode' }"
            @click="setSort(board, 'unicode')"
          >
            <span v-if="board.sort_mode === 'unicode'" class="check">✓</span>預設(標題)
          </button>
          <button
            class="pill"
            :class="{ active: board.sort_mode === 'manual' }"
            @click="setSort(board, 'manual')"
          >
            <span v-if="board.sort_mode === 'manual'" class="check">✓</span>手動
          </button>
        </div>

        <ul class="card-list" :data-board-id="board.id" :data-sort-mode="board.sort_mode">
          <li
            v-for="card in board.cards"
            :key="card.id"
            class="card"
            :data-card-id="card.id"
            @click="openCard(card)"
          >
            <div class="cover" :class="{ placeholder: !card.cover_image }">
              <img v-if="card.cover_image" :src="card.cover_image" alt="" />
              <span v-else>無封面</span>
            </div>
            <div class="card-body">
              <span class="card-title">{{ card.title }}</span>
              <button class="card-del" @click.stop="removeCard(card)" title="刪除卡片">✕</button>
            </div>
          </li>
        </ul>

        <form class="add-card" @submit.prevent="addCard(board)">
          <input
            v-model="newCardTitle[board.id]"
            placeholder="＋ 新增卡片（輸入標題）"
          />
        </form>
      </div>
      </div>

      <!-- 新增看板（置於拖曳區外，固定在最右側） -->
      <div class="board add-board">
        <form @submit.prevent="addBoard">
          <input v-model="newBoardName" placeholder="新增看板名稱" />
          <button type="submit">＋ 新增看板</button>
        </form>
      </div>
    </div>
  </section>
  <p v-else-if="error" class="error">{{ error }}</p>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.page-head h1 { margin: 0; }
.back {
  background: #e4e7eb;
  border: none;
  border-radius: 8px;
  padding: 6px 12px;
  color: #334e68;
}
.meta { color: #486581; font-size: 0.9rem; }
.error { color: #cf1124; }

.board-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 12px;
  cursor: grab;             /* 提示可按住空白處拖曳捲動 */
}
.board-row.panning {
  cursor: grabbing;
  user-select: none;        /* 拖曳捲動時不選取文字 */
}
.boards {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.board {
  flex: 0 0 260px;
  background: #e9eef3;
  border-radius: 12px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 200px);
}
.board-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.board-drag {
  cursor: grab;
  color: #9fb3c8;
  font-size: 1rem;
  line-height: 1;
  user-select: none;
}
.board-drag:active { cursor: grabbing; }
.board-head h3 { margin: 0; font-size: 1rem; cursor: pointer; flex: 1; }
.board-head input { width: 100%; padding: 4px 8px; border: 1px solid #9fb3c8; border-radius: 6px; }
.count { background: #cbd2d9; border-radius: 999px; padding: 0 8px; font-size: 0.8rem; }
.board-del { background: none; border: none; color: #829ab1; font-size: 0.9rem; }
.board-del:hover { color: #cf1124; }

.sort-pills {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.sort-label {
  font-size: 0.78rem;
  color: #627d98;
  margin-right: 2px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 10px;
  font-size: 0.78rem;
  border: 1px solid #cbd2d9;
  border-radius: 999px;
  background: #fff;
  color: #627d98;
}
.pill.active {
  border-color: #2680c2;
  background: #e3f0fb;
  color: #0a558c;
  font-weight: 600;
}
.pill .check { font-size: 0.72rem; }
.board-ghost {
  outline: 2px dashed #2680c2;
  outline-offset: -2px;
  opacity: 0.6;
}
.card-list { list-style: none; margin: 0 0 8px; padding: 0; min-height: 12px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  overflow: hidden;
  cursor: grab;
}
.card:active { cursor: grabbing; }
/* 拖曳時的插入位置標示 (C9) */
.card-ghost {
  outline: 2px dashed #2680c2;
  outline-offset: -2px;
  background: #e3f0fb;
  opacity: 0.9;
}
.card-ghost > * { visibility: hidden; }
.cover {
  height: 90px;
  background: #f0f4f8;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover img { width: 100%; height: 100%; object-fit: cover; }
.cover.placeholder span { color: #9fb3c8; font-size: 0.8rem; }
.card-body {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
}
.card-title { flex: 1; cursor: pointer; font-size: 0.95rem; }
.card-body input { flex: 1; padding: 4px 6px; border: 1px solid #9fb3c8; border-radius: 6px; }
.card-del { background: none; border: none; color: #cbd2d9; }
.card-del:hover { color: #cf1124; }

.add-card input {
  width: 100%;
  padding: 8px;
  border: 1px dashed #9fb3c8;
  border-radius: 8px;
  background: transparent;
}
.add-board { background: #dde4ea; justify-content: flex-start; }
.add-board input { width: 100%; padding: 8px; border: 1px solid #cbd2d9; border-radius: 8px; margin-bottom: 8px; }
.add-board button { width: 100%; padding: 8px; border: none; border-radius: 8px; background: #2680c2; color: #fff; }
</style>
