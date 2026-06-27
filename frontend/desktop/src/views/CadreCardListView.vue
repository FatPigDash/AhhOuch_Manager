<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import CadreNav from "../components/CadreNav.vue";
import { sendCard, editCard, isMessageNotFoundError } from "../telegram";
import { urlsToFiles } from "../share";

const router = useRouter();
const cards = ref([]);
const newName = ref("");
const error = ref("");

// ── 顯示模式 ──────────────────────────────────────────────
const VIEW_KEY = "cadreCardViewMode";
const viewMode = ref(localStorage.getItem(VIEW_KEY) || "grid");
function setView(mode) {
  viewMode.value = mode;
  localStorage.setItem(VIEW_KEY, mode);
}

// ── 批次模式 ──────────────────────────────────────────────
const batchMode = ref(false);
const selectedIds = ref(new Set());

const selectedCards = computed(() =>
  cards.value.filter((c) => selectedIds.value.has(c.id))
);
const allSelected = computed(
  () =>
    cards.value.length > 0 && cards.value.every((c) => selectedIds.value.has(c.id))
);

function toggleBatch() {
  batchMode.value = !batchMode.value;
  selectedIds.value = new Set();
}
function toggleSelect(card) {
  const ids = new Set(selectedIds.value);
  if (ids.has(card.id)) ids.delete(card.id);
  else ids.add(card.id);
  selectedIds.value = ids;
}
function selectAll() {
  selectedIds.value = new Set(cards.value.map((c) => c.id));
}
function deselectAll() {
  selectedIds.value = new Set();
}

// ── 批次發布 Modal ────────────────────────────────────────
const showBatchModal = ref(false);
const batchStage = ref("config"); // 'config' | 'running' | 'done'
const batchVariant = ref("full");
const batchPhotoMode = ref("cover"); // 'none' | 'cover'
const batchTargets = ref([]);
const batchTargetIds = ref(new Set());
const batchMsgMode = ref("auto"); // 'auto'（優先覆蓋）| 'new'（全部全新）
const batchResults = ref([]);
const batchProgress = ref({ current: 0, total: 0 });
const batchSending = ref(false);

// 設定階段摘要：預算每張卡片 × 每個目標，計算覆蓋/全新數量
const batchPreview = computed(() => {
  const tids = [...batchTargetIds.value];
  if (!tids.length || !selectedCards.value.length) return { editCount: 0, newCount: 0 };
  let editCount = 0, newCount = 0;
  for (const card of selectedCards.value) {
    for (const tid of tids) {
      const target = batchTargets.value.find((t) => t.id === tid);
      if (!target) continue;
      if (
        batchMsgMode.value === "auto" &&
        card.info_link &&
        card.info_link_label === target.name
      ) {
        editCount++;
      } else {
        newCount++;
      }
    }
  }
  return { editCount, newCount };
});

async function openBatchModal() {
  if (!selectedCards.value.length) return;
  batchStage.value = "config";
  batchResults.value = [];
  batchProgress.value = { current: 0, total: 0 };
  batchVariant.value = "full";
  batchPhotoMode.value = "cover";
  batchMsgMode.value = "auto";
  try {
    const all = await api.listTargets();
    batchTargets.value = all.filter((t) => t.enabled);
    // 預設全選目標
    batchTargetIds.value = new Set(batchTargets.value.map((t) => t.id));
  } catch (e) {
    batchTargets.value = [];
    batchTargetIds.value = new Set();
  }
  showBatchModal.value = true;
}
function toggleBatchTarget(id) {
  const ids = new Set(batchTargetIds.value);
  if (ids.has(id)) ids.delete(id);
  else ids.add(id);
  batchTargetIds.value = ids;
}

// 從 t.me 連結解析出 message_id
function parseMsgId(link) {
  if (!link) return null;
  const m = link.match(/\/(\d+)$/);
  return m ? Number(m[1]) : null;
}
// 依 chat_id + message_id 組出連結
function buildTgLink(chatId, messageId) {
  if (!chatId || !messageId) return "";
  const id = String(chatId).replace(/^-100/, "");
  return `https://t.me/c/${id}/${messageId}`;
}

async function runBatch() {
  const targets = batchTargets.value.filter((t) => batchTargetIds.value.has(t.id));
  if (!targets.length) return;

  // 展開結果列表（卡片 × 目標）
  const rows = [];
  for (const card of selectedCards.value) {
    for (const target of targets) {
      rows.push({
        cardId: card.id,
        cardName: card.name,
        coverImage: card.cover_image,
        targetId: target.id,
        targetName: target.name,
        status: "waiting",
        mode: null,
        msg: "",
      });
    }
  }
  batchResults.value = rows;
  batchProgress.value = { current: 0, total: rows.length };
  batchStage.value = "running";
  batchSending.value = true;

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    row.status = "running";
    batchResults.value = [...rows]; // 觸發響應式更新

    const target = targets.find((t) => t.id === row.targetId);
    const card = selectedCards.value.find((c) => c.id === row.cardId);

    try {
      // 取完整卡片資料（publishText 需要 full_intro 等欄位）
      const fullCard = await api.getCadreCard(row.cardId);
      const { text } = await api.publishText(row.cardId, batchVariant.value);

      // 準備圖片
      let files = [];
      if (batchPhotoMode.value === "cover" && fullCard.cover_image) {
        files = await urlsToFiles([fullCard.cover_image], fullCard.name || "card");
      } else if (batchPhotoMode.value === "all" && fullCard.images.length) {
        const urls = fullCard.images
          .slice(0, 10)
          .map((i) => i.url)
          .filter(Boolean);
        files = await urlsToFiles(urls, fullCard.name || "card");
      }

      // 判斷覆蓋 or 全新
      const shouldEdit =
        batchMsgMode.value === "auto" &&
        card.info_link &&
        card.info_link_label === target.name;

      if (shouldEdit) {
        const msgId = parseMsgId(card.info_link);
        try {
          await editCard(target.token, target.target_id, msgId, files, text);
          row.mode = "edit";
          row.status = "done";
          row.msg = "✓ 已覆蓋";
        } catch (editErr) {
          if (isMessageNotFoundError(editErr)) {
            // 原訊息已被刪除，自動改為發布新訊息
            row.msg = "自動改為全新…";
            const { messageId } = await sendCard(target.token, target.target_id, files, text);
            row.mode = "new";
            row.status = "done";
            row.msg = "✓ 已發布（原訊息已刪除）";
            const link = buildTgLink(target.target_id, messageId);
            if (link) {
              try {
                await api.updateCadreCard(row.cardId, { info_link: link, info_link_label: target.name });
                const idx = cards.value.findIndex((c) => c.id === row.cardId);
                if (idx !== -1) cards.value[idx] = { ...cards.value[idx], info_link: link, info_link_label: target.name };
              } catch (_) {}
            }
          } else {
            throw editErr;
          }
        }
      } else {
        const { messageId } = await sendCard(target.token, target.target_id, files, text);
        row.mode = "new";
        row.status = "done";
        row.msg = "✓ 已發布";
        // 回填連結至卡片
        const link = buildTgLink(target.target_id, messageId);
        if (link) {
          try {
            await api.updateCadreCard(row.cardId, {
              info_link: link,
              info_link_label: target.name,
            });
            // 同步更新列表中的卡片資料
            const idx = cards.value.findIndex((c) => c.id === row.cardId);
            if (idx !== -1) {
              cards.value[idx] = {
                ...cards.value[idx],
                info_link: link,
                info_link_label: target.name,
              };
            }
          } catch (_) {}
        }
      }
    } catch (e) {
      row.status = "error";
      row.msg = e.message || "發生未知錯誤";
    }

    batchProgress.value.current = i + 1;
    batchResults.value = [...rows];
  }

  batchSending.value = false;
  batchStage.value = "done";
}

const batchDoneSummary = computed(() => {
  const done = batchResults.value.filter((r) => r.status === "done").length;
  const err = batchResults.value.filter((r) => r.status === "error").length;
  return { done, err };
});

// ── 基本操作 ──────────────────────────────────────────────
async function load() {
  try {
    cards.value = await api.listCadreCards();
  } catch (e) {
    error.value = e.message;
  }
}
async function addCard() {
  const name = newName.value.trim();
  if (!name) return;
  try {
    await api.createCadreCard(name);
    newName.value = "";
    await load();
  } catch (e) {
    error.value = e.message;
  }
}
async function removeCard(card) {
  if (!confirm(`刪除資訊卡片「${card.name}」？`)) return;
  try {
    await api.deleteCadreCard(card.id);
    await load();
  } catch (e) {
    error.value = e.message;
  }
}
function open(card) {
  router.push({ name: "cadre-card", params: { id: card.id } });
}
onMounted(load);
</script>

<template>
  <section>
    <CadreNav />
    <h1>美容師資訊卡片</h1>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- ── 工具列 ── -->
    <div class="toolbar">
      <!-- 一般模式：新增列 -->
      <form v-if="!batchMode" class="add-bar" @submit.prevent="addCard">
        <input v-model="newName" placeholder="輸入名字或編號即可建立" maxlength="100" />
        <button type="submit">＋ 新增資訊卡片</button>
      </form>

      <!-- 批次模式：已選張數 + 全選/取消全選 -->
      <div v-else class="batch-bar">
        <span class="batch-count">已選 {{ selectedIds.size }} 張</span>
        <button class="ghost-sm" @click="allSelected ? deselectAll() : selectAll()">
          {{ allSelected ? "取消全選" : "全選" }}
        </button>
      </div>

      <div class="toolbar-right">
        <!-- 顯示模式切換 -->
        <div class="view-toggle" aria-label="切換顯示模式">
          <button :class="{ active: viewMode === 'grid' }" title="格狀卡片" @click="setView('grid')">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor"/>
              <rect x="11" y="1" width="6" height="6" rx="1.5" fill="currentColor"/>
              <rect x="1" y="11" width="6" height="6" rx="1.5" fill="currentColor"/>
              <rect x="11" y="11" width="6" height="6" rx="1.5" fill="currentColor"/>
            </svg>
            <span>卡片</span>
          </button>
          <button :class="{ active: viewMode === 'list' }" title="列表" @click="setView('list')">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <rect x="1" y="2" width="16" height="3" rx="1.5" fill="currentColor"/>
              <rect x="1" y="7.5" width="16" height="3" rx="1.5" fill="currentColor"/>
              <rect x="1" y="13" width="16" height="3" rx="1.5" fill="currentColor"/>
            </svg>
            <span>列表</span>
          </button>
        </div>

        <!-- 批次發布切換按鈕 -->
        <button
          class="batch-toggle-btn"
          :class="{ active: batchMode }"
          @click="toggleBatch"
          title="批次發布模式"
        >
          ☑ 批次發布
        </button>
      </div>
    </div>

    <p v-if="cards.length === 0" class="empty">尚無資訊卡片，請先新增。</p>

    <!-- ── 格狀卡片 ── -->
    <ul v-if="viewMode === 'grid'" class="grid">
      <li v-for="card in cards" :key="card.id" class="card" :class="{ selected: selectedIds.has(card.id) }">
        <!-- 批次模式勾選框 -->
        <button v-if="batchMode" class="batch-check" @click.stop="toggleSelect(card)">
          <span class="check-icon">{{ selectedIds.has(card.id) ? '✓' : '' }}</span>
        </button>

        <div class="body" @click="batchMode ? toggleSelect(card) : open(card)">
          <div class="cover" :class="{ placeholder: !card.cover_image }">
            <img v-if="card.cover_image" :src="card.cover_image" alt="" />
            <span v-else>無封面</span>
          </div>
          <h3>{{ card.name }}</h3>
          <p v-if="card.short_intro" class="meta">{{ card.short_intro }}</p>
        </div>
        <div v-if="!batchMode" class="actions">
          <button class="ghost" @click.stop="open(card)">編輯／發布</button>
          <button class="danger" @click.stop="removeCard(card)">刪除</button>
        </div>
      </li>
    </ul>

    <!-- ── 列表視圖 ── -->
    <ul v-else class="list-view">
      <li
        v-for="card in cards"
        :key="card.id"
        class="list-row"
        :class="{ selected: selectedIds.has(card.id) }"
        @click="batchMode ? toggleSelect(card) : undefined"
      >
        <!-- 批次模式勾選框 -->
        <div v-if="batchMode" class="list-check" @click.stop="toggleSelect(card)">
          <span class="check-icon">{{ selectedIds.has(card.id) ? '✓' : '' }}</span>
        </div>

        <div class="list-thumb" :class="{ placeholder: !card.cover_image }" @click.stop="!batchMode && open(card)">
          <img v-if="card.cover_image" :src="card.cover_image" alt="" />
          <span v-else>無封面</span>
        </div>
        <div class="list-info" @click.stop="!batchMode && open(card)">
          <h3>{{ card.name }}</h3>
          <p v-if="card.short_intro" class="meta">{{ card.short_intro }}</p>
          <p v-else class="meta empty-intro">尚未填寫簡介</p>
        </div>
        <div v-if="!batchMode" class="list-actions">
          <button class="ghost" @click.stop="open(card)">編輯／發布</button>
          <button class="danger" @click.stop="removeCard(card)">刪除</button>
        </div>
      </li>
    </ul>

    <!-- ── 浮動批次操作列 ── -->
    <div v-if="batchMode" class="batch-fab">
      <span class="fab-count">已選 {{ selectedIds.size }} 張</span>
      <button
        class="fab-publish"
        :disabled="selectedIds.size === 0"
        @click="openBatchModal"
      >
        📤 發布選取的卡片
      </button>
      <button class="fab-cancel" @click="toggleBatch">✕ 退出批次模式</button>
    </div>

    <!-- ── 批次發布 Modal ── -->
    <div v-if="showBatchModal" class="modal-backdrop" @click.self="!batchSending && (showBatchModal = false)">
      <div class="modal">

        <!-- 標題列 -->
        <header class="modal-head">
          <h2>
            <span v-if="batchStage === 'config'">批次發布設定</span>
            <span v-else-if="batchStage === 'running'">
              發布中… {{ batchProgress.current }}/{{ batchProgress.total }}
            </span>
            <span v-else>發布完成</span>
          </h2>
          <button v-if="!batchSending" class="x" @click="showBatchModal = false">✕</button>
        </header>

        <!-- ──── 階段一：設定 ──── -->
        <template v-if="batchStage === 'config'">
          <!-- 介紹版本 -->
          <div class="cfg-row">
            <span class="cfg-label">介紹版本</span>
            <div class="pill-group">
              <button class="pill" :class="{ active: batchVariant === 'full' }" @click="batchVariant = 'full'">
                <span v-if="batchVariant === 'full'">✓ </span>完整介紹
              </button>
              <button class="pill" :class="{ active: batchVariant === 'short' }" @click="batchVariant = 'short'">
                <span v-if="batchVariant === 'short'">✓ </span>簡短介紹
              </button>
            </div>
          </div>

          <!-- 圖片模式 -->
          <div class="cfg-row">
            <span class="cfg-label">附上圖片</span>
            <div class="pill-group">
              <button class="pill" :class="{ active: batchPhotoMode === 'cover' }" @click="batchPhotoMode = 'cover'">
                <span v-if="batchPhotoMode === 'cover'">✓ </span>僅封面圖
              </button>
              <button class="pill" :class="{ active: batchPhotoMode === 'all' }" @click="batchPhotoMode = 'all'">
                <span v-if="batchPhotoMode === 'all'">✓ </span>所有圖片
              </button>
              <button class="pill" :class="{ active: batchPhotoMode === 'none' }" @click="batchPhotoMode = 'none'">
                <span v-if="batchPhotoMode === 'none'">✓ </span>不附圖片
              </button>
            </div>
          </div>
          <p v-if="batchPhotoMode === 'all'" class="cfg-hint">
            每張卡片最多附 10 張圖片（Telegram 上限）。
          </p>

          <!-- 發送目標 -->
          <div class="cfg-row col">
            <span class="cfg-label">發送目標</span>
            <p v-if="!batchTargets.length" class="cfg-hint">尚無啟用的 Telegram 目標，請至「發布設定」新增。</p>
            <div v-else class="target-list">
              <label v-for="t in batchTargets" :key="t.id" class="target-item">
                <input
                  type="checkbox"
                  :checked="batchTargetIds.has(t.id)"
                  @change="toggleBatchTarget(t.id)"
                />
                <span>{{ t.name }}</span>
              </label>
            </div>
          </div>

          <!-- 訊息模式 -->
          <div class="cfg-row col">
            <span class="cfg-label">訊息模式</span>
            <label class="mode-option">
              <input type="radio" v-model="batchMsgMode" value="auto" />
              <span class="mode-label">優先覆蓋</span>
              <span class="mode-desc">有既有連結且來源相符者覆蓋，其餘發布全新</span>
            </label>
            <label class="mode-option">
              <input type="radio" v-model="batchMsgMode" value="new" />
              <span class="mode-label">全部全新</span>
              <span class="mode-desc">一律發布新訊息，忽略既有連結</span>
            </label>
          </div>

          <!-- 摘要 -->
          <div v-if="batchTargetIds.size" class="batch-summary">
            共 {{ selectedCards.length }} 張卡片 × {{ batchTargetIds.size }} 個目標
            <template v-if="batchPreview.editCount || batchPreview.newCount">
              ：<span class="sum-edit">{{ batchPreview.editCount }} 覆蓋</span>、
              <span class="sum-new">{{ batchPreview.newCount }} 全新</span>
            </template>
          </div>

          <div class="modal-actions">
            <button
              class="primary"
              :disabled="!batchTargetIds.size"
              @click="runBatch"
            >
              📤 開始批次發布
            </button>
            <button class="ghost" @click="showBatchModal = false">取消</button>
          </div>
        </template>

        <!-- ──── 階段二：執行中 ──── -->
        <template v-else-if="batchStage === 'running' || batchStage === 'done'">
          <!-- 進度列 -->
          <div class="progress-bar-wrap">
            <div
              class="progress-bar"
              :style="{ width: batchProgress.total ? (batchProgress.current / batchProgress.total * 100) + '%' : '0%' }"
            ></div>
          </div>

          <!-- 結果列表 -->
          <ul class="result-list">
            <li v-for="(row, i) in batchResults" :key="i" class="result-row">
              <div class="result-thumb" :class="{ placeholder: !row.coverImage }">
                <img v-if="row.coverImage" :src="row.coverImage" alt="" />
                <span v-else>無</span>
              </div>
              <div class="result-info">
                <span class="result-name">{{ row.cardName }}</span>
                <span class="result-target">→ {{ row.targetName }}</span>
              </div>
              <div class="result-status">
                <span v-if="row.status === 'waiting'" class="status-wait">⏳ 等待</span>
                <span v-else-if="row.status === 'running'" class="status-run">📡 發送中…</span>
                <span v-else-if="row.status === 'done'" class="status-done">
                  {{ row.msg }}
                  <span class="mode-tag">{{ row.mode === 'edit' ? '覆蓋' : '全新' }}</span>
                </span>
                <span v-else class="status-err" :title="row.msg">✗ 失敗</span>
              </div>
            </li>
          </ul>

          <!-- 失敗詳情（完成後顯示） -->
          <template v-if="batchStage === 'done'">
            <div class="done-summary">
              <span class="sum-done">✓ 成功 {{ batchDoneSummary.done }} 張</span>
              <span v-if="batchDoneSummary.err" class="sum-err">✗ 失敗 {{ batchDoneSummary.err }} 張</span>
            </div>
            <ul v-if="batchDoneSummary.err" class="err-list">
              <li v-for="(row, i) in batchResults.filter(r => r.status === 'error')" :key="i">
                {{ row.cardName }} → {{ row.targetName }}：{{ row.msg }}
              </li>
            </ul>
            <div class="modal-actions">
              <button class="primary" @click="showBatchModal = false">關閉</button>
            </div>
          </template>
        </template>

      </div>
    </div>
  </section>
</template>

<style scoped>
h1 { margin-top: 0; }
.error { color: #cf1124; }
.empty { color: #829ab1; }

/* ── 工具列 ── */
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.add-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  min-width: 240px;
}
.add-bar input {
  flex: 1;
  min-width: 160px;
  max-width: 360px;
  padding: 8px 12px;
  border: 1px solid #cbd2d9;
  border-radius: 8px;
}
.add-bar button {
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: #2680c2;
  color: #fff;
  white-space: nowrap;
  cursor: pointer;
}
.add-bar button:hover { background: #1a6aad; }

.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}
.batch-count { font-size: 0.9rem; font-weight: 600; color: #334e68; }
.ghost-sm {
  padding: 5px 12px;
  border: none;
  border-radius: 8px;
  background: #e4e7eb;
  color: #334e68;
  font-size: 0.85rem;
  cursor: pointer;
}
.ghost-sm:hover { background: #cbd2d9; }

.toolbar-right {
  display: flex;
  align-items: stretch;
  gap: 8px;
  flex-shrink: 0;
}

/* 顯示模式切換 */
.view-toggle {
  display: flex;
  background: #f0f4f8;
  border-bottom: 2px solid #e1e8ed;
  align-self: stretch;
}
.view-toggle button {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 10px 16px;
  border: none;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  background: none;
  color: #627d98;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.view-toggle button:hover { background: #e1e8ed; color: #334e68; }
.view-toggle button.active { background: #fff; color: #102a43; border-bottom-color: #102a43; }

/* 批次模式切換按鈕 */
.batch-toggle-btn {
  display: flex;
  align-items: center;
  align-self: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid #cbd2d9;
  border-radius: 8px;
  background: #fff;
  color: #627d98;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.batch-toggle-btn:hover { background: #f0f4f8; color: #334e68; }
.batch-toggle-btn.active { background: #e3f0fb; color: #0a558c; border-color: #2680c2; }

/* ── 格狀卡片 ── */
.grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.18s, border-color 0.18s;
  position: relative;
}
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.card.selected { border-color: #2680c2; box-shadow: 0 0 0 2px #b3d4f0; }

/* 格狀勾選框 */
.batch-check {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 2px solid #2680c2;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}
.card.selected .batch-check { background: #2680c2; }
.check-icon { font-size: 0.8rem; color: #fff; font-weight: 700; }

.body { cursor: pointer; }
.cover {
  height: 260px;
  background: #f0f4f8;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover img { width: 100%; height: 100%; object-fit: cover; }
.cover.placeholder span { color: #9fb3c8; font-size: 0.85rem; }
.card h3 { margin: 10px 14px 4px; }
.meta { margin: 0 14px 10px; color: #486581; font-size: 0.9rem; }
.actions {
  display: flex;
  gap: 8px;
  padding: 0 14px 14px;
  margin-top: auto;
}
.actions button { font-size: 0.85rem; padding: 6px 10px; border: none; border-radius: 8px; cursor: pointer; }

/* ── 列表視圖 ── */
.list-view { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.list-row {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: box-shadow 0.18s, border-color 0.18s;
}
.list-row:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.list-row.selected { border-color: #2680c2; box-shadow: 0 0 0 2px #b3d4f0; }

/* 列表勾選框 */
.list-check {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 2px solid #2680c2;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
}
.list-row.selected .list-check { background: #2680c2; }

.list-thumb {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  background: #f0f4f8;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}
.list-thumb img { width: 100%; height: 100%; object-fit: cover; }
.list-thumb.placeholder span { color: #9fb3c8; font-size: 0.72rem; text-align: center; line-height: 1.3; }
.list-info { flex: 1; min-width: 0; cursor: pointer; }
.list-info h3 { margin: 0 0 3px; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.list-info .meta { margin: 0; font-size: 0.85rem; color: #486581; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.list-info .empty-intro { color: #9fb3c8; }
.list-actions { display: flex; gap: 8px; flex-shrink: 0; }
.list-actions button { font-size: 0.85rem; padding: 6px 10px; border: none; border-radius: 8px; cursor: pointer; white-space: nowrap; }

/* 共用按鈕顏色 */
.ghost { background: #e4e7eb; color: #334e68; }
.ghost:hover { background: #cbd2d9; }
.danger { background: #fbeae5; color: #cf1124; }
.danger:hover { background: #f8d0c9; }

/* ── 浮動批次操作列 ── */
.batch-fab {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  background: #1f2933;
  color: #fff;
  border-radius: 999px;
  padding: 10px 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.28);
  z-index: 40;
  white-space: nowrap;
}
.fab-count { font-size: 0.9rem; color: #9fb3c8; }
.fab-publish {
  padding: 8px 18px;
  border: none;
  border-radius: 999px;
  background: #2680c2;
  color: #fff;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s;
}
.fab-publish:hover:not(:disabled) { background: #1a6aad; }
.fab-publish:disabled { opacity: 0.4; cursor: not-allowed; }
.fab-cancel {
  padding: 6px 14px;
  border: none;
  border-radius: 999px;
  background: rgba(255,255,255,0.1);
  color: #9fb3c8;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s;
}
.fab-cancel:hover { background: rgba(255,255,255,0.18); color: #fff; }

/* ── 批次發布 Modal ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(16,42,67,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 16px;
}
.modal {
  background: #fff;
  border-radius: 16px;
  width: 500px;
  max-width: 95vw;
  max-height: 88vh;
  overflow-y: auto;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.modal-head h2 { margin: 0; font-size: 1.1rem; }
.modal-head .x { border: none; background: #e4e7eb; border-radius: 8px; width: 30px; height: 30px; cursor: pointer; font-size: 1rem; }

/* 設定列 */
.cfg-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.cfg-row.col { flex-direction: column; align-items: flex-start; gap: 6px; }
.cfg-label { font-size: 0.85rem; font-weight: 600; color: #486581; min-width: 72px; }
.cfg-hint { font-size: 0.82rem; color: #829ab1; margin: 0; }
.pill-group { display: flex; gap: 6px; }
.pill {
  padding: 4px 14px;
  border: 1px solid #cbd2d9;
  border-radius: 999px;
  background: #fff;
  color: #627d98;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.pill.active { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }

/* 目標勾選 */
.target-list { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.target-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #334e68;
  cursor: pointer;
}
.target-item input { accent-color: #2680c2; width: 16px; height: 16px; }

/* 訊息模式 */
.mode-option { display: flex; align-items: baseline; gap: 7px; cursor: pointer; }
.mode-option input[type=radio] { flex-shrink: 0; accent-color: #2680c2; }
.mode-label { font-size: 0.9rem; font-weight: 600; color: #1f2933; }
.mode-desc { font-size: 0.8rem; color: #829ab1; }

/* 摘要 */
.batch-summary {
  font-size: 0.85rem;
  color: #627d98;
  padding: 8px 12px;
  background: #f7f9fb;
  border-radius: 8px;
}
.sum-edit { color: #1a6aad; font-weight: 600; }
.sum-new { color: #2f855a; font-weight: 600; }

/* Modal 操作按鈕 */
.modal-actions { display: flex; gap: 10px; }
.modal-actions button { padding: 9px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; }
.primary { background: #2680c2; color: #fff; }
.primary:hover:not(:disabled) { background: #1a6aad; }
.primary:disabled { opacity: 0.4; cursor: not-allowed; }

/* 進度列 */
.progress-bar-wrap {
  height: 6px;
  background: #e4e7eb;
  border-radius: 999px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: #2680c2;
  border-radius: 999px;
  transition: width 0.3s ease;
}

/* 結果列表 */
.result-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; max-height: 340px; overflow-y: auto; }
.result-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: #f7f9fb; border-radius: 8px; }
.result-thumb {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  background: #e4e7eb;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  font-size: 0.65rem;
  color: #9fb3c8;
}
.result-thumb img { width: 100%; height: 100%; object-fit: cover; }
.result-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.result-name { font-size: 0.9rem; font-weight: 600; color: #1f2933; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-target { font-size: 0.78rem; color: #829ab1; }
.result-status { flex-shrink: 0; font-size: 0.82rem; display: flex; align-items: center; gap: 5px; }
.status-wait { color: #9fb3c8; }
.status-run { color: #2680c2; }
.status-done { color: #2f855a; }
.status-err { color: #cf1124; }
.mode-tag { font-size: 0.72rem; padding: 1px 7px; border-radius: 999px; background: #e4e7eb; color: #486581; }

/* 完成摘要 */
.done-summary { display: flex; gap: 14px; font-size: 0.9rem; font-weight: 600; }
.sum-done { color: #2f855a; }
.sum-err { color: #cf1124; }
.err-list { list-style: disc; padding-left: 1.2em; margin: 0; font-size: 0.82rem; color: #cf1124; line-height: 1.8; }
</style>
