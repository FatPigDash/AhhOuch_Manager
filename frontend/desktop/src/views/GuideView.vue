<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeTab = ref('tutorial') // 'tutorial' | 'disclaimer'
function goHome() { router.push({ name: 'cadre-list' }) }
</script>

<template>
  <div class="guide-view">
    <div class="guide-topbar">
      <button class="back" @click="goHome">← 回到主頁</button>
      <div class="tabs">
        <button :class="{ active: activeTab === 'tutorial' }" @click="activeTab = 'tutorial'">📖 軟體教學</button>
        <button :class="{ active: activeTab === 'disclaimer' }" @click="activeTab = 'disclaimer'">⚠️ 使用聲明</button>
      </div>
    </div>

    <!-- Tutorial Section -->
    <div v-if="activeTab === 'tutorial'" class="tutorial-section">
      <p class="intro">
        歡迎使用 <strong>AhhOuch_Manager 幹部系統</strong>。本系統幫助幹部管理美容師的<strong>資訊卡片</strong>與<strong>每日班表</strong>，
        並一鍵發布到 Telegram 群組或 LINE。所有資料<strong>只存在您自己的裝置</strong>，請務必定期備份。
        以下依實際操作順序說明各項功能。
      </p>

      <!-- 0. 導覽列 -->
      <div class="nav-guide">
        <h3>📍 四大頁籤導覽</h3>
        <p>進入幹部系統後，頂端有四個頁籤，本教學即依此順序介紹：</p>
        <div class="nav-mock">
          <span class="nav-tab active">資訊卡片</span>
          <span class="nav-tab">班表</span>
          <span class="nav-tab">發布設定</span>
          <span class="nav-tab">備份</span>
        </div>
        <p class="nav-note">右上角的「教學及聲明」即為您目前所在的本頁面。</p>
      </div>

      <!-- 1. 資訊卡片列表 -->
      <div class="feature-block">
        <div class="mockup">
          <div class="m-toolbar">
            <span class="m-add-input">輸入名字或編號即可建立</span>
            <span class="m-btn xs">＋ 新增</span>
          </div>
          <div class="m-toolbar end">
            <span class="m-seg"><span class="seg on">卡片</span><span class="seg">列表</span></span>
            <span class="m-btn xs ghost">☑ 批次發布</span>
          </div>
          <div class="m-card-grid">
            <div class="m-mini-card">
              <div class="m-cover">👤</div>
              <div class="m-mini-name">小美</div>
              <div class="m-mini-meta">甜美系・可預約</div>
            </div>
            <div class="m-mini-card">
              <div class="m-cover">👤</div>
              <div class="m-mini-name">3 號</div>
              <div class="m-mini-meta">氣質鄰家</div>
            </div>
          </div>
        </div>
        <div class="text">
          <h3>1. 資訊卡片：建立與檢視</h3>
          <p><strong>快速建立：</strong>在「資訊卡片」頁，於上方欄位輸入<strong>名字或編號</strong>（例如「小美」或「3 號」），按「＋ 新增資訊卡片」即可建立一張空白卡片，後續再進去補照片與介紹。</p>
          <p><strong>兩種檢視：</strong>右上角可切換「<strong>卡片</strong>」（封面格狀牆）與「<strong>列表</strong>」（一行一位、附簡介）兩種顯示模式，系統會記住您的選擇。</p>
          <p><strong>批次發布：</strong>點「☑ 批次發布」進入勾選模式，一次選取多位人員，再透過底部的「📤 發布選取的卡片」一口氣發送（詳見第 5 節）。</p>
        </div>
      </div>

      <!-- 2. 卡片編輯 -->
      <div class="feature-block reverse">
        <div class="mockup">
          <div class="m-detail-head">
            <span class="m-back">←</span>
            <span class="m-title-input">小美</span>
          </div>
          <div class="m-thumb-row">
            <div class="m-thumb cover"><span class="m-badge">封面</span>👤</div>
            <div class="m-thumb">👤</div>
            <div class="m-thumb add">＋</div>
          </div>
          <div class="m-tool-row">
            <span class="m-btn xs ghost">⬆ 上傳</span>
            <span class="m-btn xs ghost">📷 拍照</span>
            <span class="m-btn xs ghost">📋 貼上</span>
          </div>
          <div class="m-field"><span class="m-label">完整介紹</span><span class="m-textarea"></span></div>
          <div class="m-field"><span class="m-label">簡短介紹</span><span class="m-textarea short"></span></div>
          <div class="m-detail-foot">
            <span class="m-btn xs blue">📤 發布</span>
            <span class="m-btn xs">💾 儲存</span>
          </div>
        </div>
        <div class="text">
          <h3>2. 編輯卡片內容</h3>
          <p><strong>上傳照片：</strong>點開任一張卡片後，可用「<strong>⬆ 上傳圖片</strong>」「<strong>📷 拍照</strong>」（手機）或「<strong>📋 貼上</strong>」加入多張照片，桌面也能直接按 <code>Ctrl+V</code>。在照片上按「★」可設為<strong>封面</strong>，按「✕」可刪除。</p>
          <p><strong>兩段介紹文字：</strong>填寫「<strong>完整介紹</strong>」與「<strong>簡短介紹</strong>」兩個版本，發布時可自由選用其中一種，方便對不同群組投放長／短文案。</p>
          <p><strong>記得儲存：</strong>文字修改後需按「💾 儲存」才會寫入；若未儲存就離開，系統會提醒您。照片則為即時存檔，無需另外儲存。</p>
        </div>
      </div>

      <!-- 3. 班表 -->
      <div class="feature-block">
        <div class="mockup">
          <div class="m-field"><span class="m-label">日期</span><span class="m-date">2026/06/27 (六)</span></div>
          <div class="m-field"><span class="m-label">標題</span><span class="m-textarea short"></span></div>
          <div class="m-sub">出勤人員</div>
          <div class="m-pill-row">
            <span class="m-pill on">✓ 小美</span>
            <span class="m-pill on">✓ 3 號</span>
            <span class="m-pill">小芳</span>
          </div>
          <div class="m-sub">出勤時段　<span class="m-mode">手動輸入｜<b>自動換算</b></span></div>
          <div class="m-slot-row">
            <span class="m-slot">18:00</span>
            <span class="m-slot">19:30</span>
            <span class="m-slot">21:00</span>
          </div>
        </div>
        <div class="text">
          <h3>3. 班表：安排當日出勤</h3>
          <p><strong>建立草稿：</strong>到「班表」頁按「＋ 新增班表」，先選<strong>日期</strong>（系統自動標出星期），再填<strong>標題</strong>與<strong>結語</strong>（皆可套用文字模板，省去重複打字）。</p>
          <p><strong>挑選出勤人員：</strong>系統會自動列出所有資訊卡片，點一下名字即<strong>加入／移除</strong>當日出勤名單。</p>
          <p><strong>安排時段：</strong>每位人員可選「<strong>手動輸入</strong>」（打 <code>1830</code> 自動轉成 18:30）或「<strong>自動換算班次</strong>」（輸入上班時間，系統算出整段班次格供您勾選）。班表會自動存成草稿，發布後標示「已發布」，可重複編輯再發。</p>
        </div>
      </div>

      <!-- 4. 發布設定 -->
      <div class="feature-block reverse">
        <div class="mockup">
          <div class="m-title-bar">新增發布目標</div>
          <div class="m-field"><span class="m-label">名稱</span><span class="m-input">工作室主群</span></div>
          <div class="m-field">
            <span class="m-label">機器人金鑰 <span class="m-help">?</span></span>
            <span class="m-input">••••••••••••••••</span>
          </div>
          <div class="m-field">
            <span class="m-label">要發到哪個群組 <span class="m-help">?</span></span>
            <span class="m-input">-1001234567890</span>
          </div>
          <span class="m-btn xs blue">＋ 新增</span>
        </div>
        <div class="text">
          <h3>4. 發布設定（綁定 Telegram）</h3>
          <p><strong>新增發送目標：</strong>到「發布設定」頁，填入<strong>名稱</strong>（自己看的備註）、向 <code>@BotFather</code> 申請的「<strong>機器人金鑰</strong>」，以及要發送的「<strong>群組編號</strong>」（chat_id，通常是負數）。</p>
          <p><strong>內建申請教學：</strong>金鑰與群組編號欄位旁都有藍色「<strong>?</strong>」按鈕，點開即有逐步圖文教您如何用 BotFather 申請機器人、以及如何取得群組編號，照著做即可。</p>
          <p><strong>啟用／停用：</strong>每個目標可隨時停用或刪除；只有「啟用中」的目標會出現在發布視窗。金鑰與編號<strong>只存在本機</strong>，不會上傳任何伺服器。</p>
        </div>
      </div>

      <!-- 5. 一鍵發布 -->
      <div class="feature-block">
        <div class="mockup">
          <div class="m-title-bar">發布到群組</div>
          <div class="m-pub-preview">
            <div class="m-pub-cover">🖼</div>
            <div class="m-pub-name">小美</div>
            <div class="m-pub-line w-90"></div>
            <div class="m-pub-line w-70"></div>
          </div>
          <span class="m-btn full blue">📤 分享至 LINE 等</span>
          <div class="m-tg-row">
            <span class="m-tg-label">發送到 Telegram</span>
            <span class="m-tg-chip">✈ 工作室主群</span>
          </div>
          <div class="m-tool-row">
            <span class="m-btn xs ghost">📋 複製文字</span>
            <span class="m-btn xs ghost">🖼 下載圖片</span>
          </div>
        </div>
        <div class="text">
          <h3>5. 一鍵發布到群組</h3>
          <p><strong>多種發送方式：</strong>在卡片或班表按「📤 發布」會開啟發布視窗，可選「<strong>分享至 LINE 等</strong>」（叫出系統分享選單）、「<strong>複製純文字</strong>」、「<strong>下載排版圖片</strong>」，或直接點目標「<strong>✈ 發送到 Telegram</strong>」自動送出。</p>
          <p><strong>挑選版本與照片：</strong>發送前可切換「完整／簡短介紹」，並逐張勾選要附上的照片（預設全選）。</p>
          <p><strong>覆蓋不洗版：</strong>同一張卡片或班表再次發布時，可選「<strong>覆蓋舊有訊息</strong>」直接更新群組內既有訊息，或選「<strong>發布全新訊息</strong>」。發送後系統會自動記住該則訊息連結，方便下次覆蓋。</p>
        </div>
      </div>

      <!-- 6. 備份 -->
      <div class="feature-block reverse">
        <div class="mockup">
          <div class="m-title-bar">備份與還原</div>
          <div class="m-last">上次備份：2026/06/01 09:30</div>
          <div class="m-field"><span class="m-label">密碼（選填＝加密）</span><span class="m-input">••••••</span></div>
          <span class="m-btn full blue">⬇ 下載備份檔</span>
          <div class="m-file">📁 AhhOuch備份_20260627.ahbk</div>
          <span class="m-btn full danger">⟳ 覆蓋還原</span>
        </div>
        <div class="text">
          <h3>6. 備份與還原（重要！）</h3>
          <p><strong>本機優先：</strong>您的所有資料只存在這支手機／電腦中。<strong>一旦清除瀏覽器資料、解除安裝或換機，資料將永久消失</strong>，連開發者也無法救回。系統每超過一個月會自動跳出備份提醒。</p>
          <p><strong>匯出備份：</strong>到「備份」頁按「<strong>⬇ 下載備份檔</strong>」，會產生一個 <code>.ahbk</code> 檔（可選填密碼加密）。下載後請<strong>手動上傳到自己的雲端</strong>（iOS → iCloud Drive；Android → Google Drive）。</p>
          <p><strong>還原資料：</strong>換機或重裝後，到「備份」頁「<strong>選擇備份檔</strong>」並按「⟳ 覆蓋還原」，輸入當初的密碼即可還原所有卡片、照片與班表。⚠ 還原會<strong>覆蓋</strong>目前裝置上的資料，請謹慎操作。</p>
        </div>
      </div>
    </div>

    <!-- Disclaimer Section -->
    <div v-if="activeTab === 'disclaimer'" class="disclaimer-section">
      <h2>AhhOuch_Manager 幹部系統 使用聲明與規範</h2>
      <p>歡迎使用 AhhOuch_Manager 幹部系統。為了保障所有使用者的權益、維護資訊安全，並確保本系統的穩定運行，請在開始使用前詳細閱讀並同意以下使用聲明與規範。</p>

      <h3>1. 資料存放與隱私安全</h3>
      <p>本系統致力於保護您的隱私。本系統採用「本機優先 (Local-First)」架構的網頁應用程式 (PWA)。您的所有資料（包含美容師資訊卡片、班表與圖片）<strong>完全儲存於您個人的手機或電腦裝置內，並不會上傳至任何開發者控制的雲端伺服器。</strong></p>
      <p>然而，請您理解：</p>
      <ul>
        <li><strong>資料遺失風險與備份：</strong>由於資料僅存放於您的個人裝置，<strong>若您清除瀏覽器快取、清除網站資料、或解除安裝本網頁應用程式 (PWA)，您的所有資料將會遭到永久刪除</strong>。請務必定期匯出備份檔（<code>.ahbk</code>）並上傳到自己的雲端硬碟。基於本機儲存原則，一旦資料遺失，任何人都無法（包含開發者）協助您還原資料。</li>
        <li><strong>資料自主與責任：</strong>您於本系統中建立、儲存的所有資料，其所有權與法律責任均由您個人承擔。開發者無法存取、查看或審查您的任何本機資料。</li>
      </ul>

      <h3>2. 系統使用限制與免責聲明</h3>
      <ul>
        <li><strong>本機運行限制：</strong>本系統為依賴瀏覽器運行的程式，開發者不保證系統於所有裝置環境上絕對無中斷或無錯誤。</li>
        <li><strong>開發者免責聲明：</strong>本軟體「按原樣」提供。針對因手機/電腦損毀、誤刪瀏覽器資料、操作失誤或不可抗力因素導致的資料遺失，以及使用社群發布功能所造成的任何後果，開發者概不承擔任何責任與賠償。</li>
      </ul>

      <h3>3. 內容建立與社群發布規範</h3>
      <p>雖然本系統資料完全存放在您的裝置端，但當您使用本系統的「社群發布功能」（如自動發布至 Telegram 或透過手機分享發送），您仍須遵守相關法律法規：</p>
      <ul>
        <li><strong>禁止違法行為：</strong>嚴禁利用本系統管理、儲存或發布任何違反當地法律的內容，包含但不限於：未成年人色情影像、未經同意散佈之私密影像（如復仇式色情）、暴力恐怖或其他法定違禁之圖像與資訊。</li>
        <li><strong>風險自負：</strong>若因建立或發布不當內容導致任何法律糾紛，或因違反第三方社群平台（如 Telegram、LINE）的合理使用政策（AUP）而導致您的社群帳號、機器人或群組遭封鎖，相關後果與責任由使用者完全承擔。</li>
      </ul>

      <h3>4. 規範之遵守與處置</h3>
      <p>本聲明旨在釐清「本機優先」架構下的責任歸屬。因開發者無法觸及您的本機資料，我們無權也無法主動刪除您的內容。但若發現使用者將本系統用於非法用途且衍生重大爭議，開發者保留停止專案維護或採取其他相應措施之權利。</p>

      <div class="disclaimer-footer">
        <strong>當您繼續使用本系統，即表示您已充分了解並願意遵守上述所有聲明與規範。</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.guide-view {
  max-width: 820px;
  margin: 24px auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  overflow: hidden;
}

.guide-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f0f4f8;
  border-bottom: 2px solid #e1e8ed;
  padding-left: 12px;
}
.guide-topbar .back {
  flex-shrink: 0;
  padding: 8px 14px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #627d98;
  background: none;
  border: 1.5px solid #cbd2d9;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}
.guide-topbar .back:hover { background: #e1e8ed; color: #102a43; }
.guide-topbar .tabs {
  flex: 1;
  border-bottom: none;
}

.tabs {
  display: flex;
  background: #f0f4f8;
  border-bottom: 2px solid #e1e8ed;
}
.tabs button {
  flex: 1;
  padding: 18px;
  font-size: 1.15rem;
  font-weight: bold;
  color: #627d98;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.tabs button:hover { background: #e1e8ed; }
.tabs button.active {
  color: #102a43;
  background: #fff;
  border-bottom: 3px solid #102a43;
  margin-bottom: -2px;
}

.tutorial-section { padding: 36px 30px; }
.intro {
  font-size: 1.08rem;
  color: #334e68;
  text-align: center;
  margin-bottom: 30px;
  line-height: 1.8;
}

/* 導覽列說明 */
.nav-guide {
  background: #f7f9fb;
  border: 1px solid #e4e7eb;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 44px;
}
.nav-guide h3 { margin: 0 0 8px; color: #102a43; font-size: 1.2rem; }
.nav-guide p { color: #486581; margin: 6px 0; line-height: 1.6; }
.nav-mock { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 10px; }
.nav-tab {
  padding: 6px 16px;
  border-radius: 8px;
  background: #e4e7eb;
  color: #486581;
  font-size: 0.95rem;
  font-weight: 500;
}
.nav-tab.active { background: #102a43; color: #fff; font-weight: 600; }
.nav-note { font-size: 0.9rem; color: #829ab1 !important; }

/* 功能區塊 */
.feature-block {
  display: flex;
  align-items: center;
  gap: 34px;
  margin-bottom: 50px;
  padding-bottom: 44px;
  border-bottom: 1px solid #f0f4f8;
}
.feature-block:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.feature-block.reverse { flex-direction: row-reverse; }

.text { flex: 1; }
.text h3 { font-size: 1.35rem; color: #102a43; margin-top: 0; margin-bottom: 14px; }
.text p { color: #486581; line-height: 1.75; margin-bottom: 12px; font-size: 1.02rem; }
.text code, .disclaimer-section code {
  background: #f0f4f8; color: #0a558c; border-radius: 4px;
  padding: 1px 6px; font-size: 0.9em;
}

/* ── CSS UI 模擬（依實際介面樣式繪製）── */
.mockup {
  flex: 0 0 280px;
  width: 280px;
  background: #fff;
  border: 1px solid #d9e2ec;
  border-radius: 12px;
  box-shadow: 0 6px 18px rgba(16, 42, 67, 0.10);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.m-toolbar { display: flex; align-items: center; gap: 8px; }
.m-toolbar.end { justify-content: space-between; }
.m-add-input {
  flex: 1; padding: 7px 10px; border: 1px solid #cbd2d9; border-radius: 8px;
  font-size: 0.72rem; color: #9fb3c8; background: #fff;
}
.m-seg { display: inline-flex; background: #f0f4f8; border-radius: 9px; padding: 3px; gap: 3px; }
.m-seg .seg { padding: 4px 12px; border-radius: 6px; font-size: 0.72rem; color: #627d98; }
.m-seg .seg.on { background: #fff; color: #2680c2; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }

.m-btn {
  display: inline-flex; align-items: center; justify-content: center;
  background: #2680c2; color: #fff; border-radius: 8px;
  font-size: 0.74rem; font-weight: 600; padding: 7px 12px; white-space: nowrap;
}
.m-btn.xs { padding: 6px 10px; font-size: 0.72rem; }
.m-btn.blue { background: #2680c2; }
.m-btn.ghost { background: #e4e7eb; color: #334e68; }
.m-btn.danger { background: #fbeae5; color: #cf1124; }
.m-btn.full { width: 100%; padding: 9px; font-size: 0.8rem; }

/* 卡片格狀 */
.m-card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.m-mini-card { border: 1px solid #e4e7eb; border-radius: 10px; overflow: hidden; }
.m-cover {
  height: 70px; background: #f0f4f8; display: flex; align-items: center;
  justify-content: center; font-size: 1.6rem;
}
.m-mini-name { font-size: 0.78rem; font-weight: 700; color: #102a43; margin: 6px 8px 2px; }
.m-mini-meta { font-size: 0.66rem; color: #829ab1; margin: 0 8px 8px; }

/* 卡片詳細 */
.m-detail-head { display: flex; align-items: center; gap: 8px; }
.m-back { background: #e4e7eb; color: #334e68; border-radius: 7px; padding: 3px 9px; font-size: 0.8rem; }
.m-title-input {
  flex: 1; font-size: 0.85rem; font-weight: 700; color: #102a43;
  border: 1px solid #e4e7eb; border-radius: 7px; padding: 4px 8px;
}
.m-thumb-row { display: flex; gap: 8px; }
.m-thumb {
  position: relative; width: 52px; height: 52px; border-radius: 8px; border: 2px solid #e4e7eb;
  background: #f0f4f8; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;
}
.m-thumb.cover { border-color: #2680c2; }
.m-thumb.add { border-style: dashed; color: #9fb3c8; font-size: 1.2rem; }
.m-badge {
  position: absolute; top: 2px; left: 2px; background: #2680c2; color: #fff;
  font-size: 0.52rem; padding: 1px 5px; border-radius: 999px;
}
.m-tool-row { display: flex; flex-wrap: wrap; gap: 6px; }

.m-field { display: flex; flex-direction: column; gap: 4px; }
.m-label { font-size: 0.7rem; color: #627d98; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.m-textarea { height: 38px; border: 1px solid #cbd2d9; border-radius: 8px; background: #fff; }
.m-textarea.short { height: 24px; }
.m-input {
  border: 1px solid #cbd2d9; border-radius: 8px; background: #fff; padding: 6px 10px;
  font-size: 0.72rem; color: #486581;
}
.m-date { border: 1px solid #cbd2d9; border-radius: 8px; padding: 6px 10px; font-size: 0.74rem; font-weight: 700; color: #102a43; }
.m-detail-foot { display: flex; justify-content: space-between; margin-top: 2px; }

/* 班表 */
.m-sub { font-size: 0.74rem; font-weight: 700; color: #243b53; margin-top: 2px; }
.m-mode { font-size: 0.66rem; font-weight: 500; color: #829ab1; }
.m-mode b { color: #0a558c; }
.m-pill-row, .m-slot-row { display: flex; flex-wrap: wrap; gap: 6px; }
.m-pill {
  padding: 4px 11px; border: 1px solid #cbd2d9; border-radius: 999px;
  background: #fff; color: #486581; font-size: 0.7rem;
}
.m-pill.on { border-color: #2680c2; background: #e3f0fb; color: #0a558c; font-weight: 600; }
.m-slot {
  background: #102a43; color: #fff; border-radius: 999px;
  padding: 3px 12px; font-size: 0.72rem;
}

/* 發布設定 / 視窗標題 */
.m-title-bar { font-size: 0.82rem; font-weight: 700; color: #102a43; }
.m-help {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; border-radius: 50%; background: #2680c2; color: #fff;
  font-size: 0.6rem; font-weight: 700;
}

/* 發布視窗 */
.m-pub-preview { border: 1px solid #e4e7eb; border-radius: 10px; padding: 10px; }
.m-pub-cover {
  height: 56px; background: #f0f4f8; border-radius: 7px; display: flex;
  align-items: center; justify-content: center; font-size: 1.4rem; margin-bottom: 8px;
}
.m-pub-name { font-size: 0.82rem; font-weight: 700; color: #102a43; margin-bottom: 6px; }
.m-pub-line { height: 6px; background: #e1e8ed; border-radius: 3px; margin-bottom: 5px; }
.m-pub-line.w-90 { width: 90%; }
.m-pub-line.w-70 { width: 70%; }
.m-tg-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; border-top: 1px solid #f0f2f5; padding-top: 8px; }
.m-tg-label { font-size: 0.7rem; color: #627d98; }
.m-tg-chip {
  border: 1px solid #2680c2; color: #0a558c; background: #e3f0fb;
  border-radius: 999px; padding: 4px 12px; font-size: 0.72rem;
}

/* 備份 */
.m-last { font-size: 0.7rem; color: #486581; }
.m-file {
  font-size: 0.68rem; color: #334e68; background: #f0f4f8;
  border-radius: 7px; padding: 6px 8px; word-break: break-all;
}

@media (max-width: 768px) {
  .feature-block, .feature-block.reverse { flex-direction: column; }
  .mockup { flex: 0 0 auto; width: 100%; max-width: 320px; margin: 0 auto; }
  .text { text-align: left; }
}

/* Disclaimer Styles */
.disclaimer-section {
  padding: 40px;
  color: #334e68;
  line-height: 1.7;
}
.disclaimer-section h2 { color: #102a43; border-bottom: 2px solid #f0f4f8; padding-bottom: 10px; margin-bottom: 20px; }
.disclaimer-section h3 { color: #243b53; margin-top: 24px; margin-bottom: 12px; font-size: 1.2rem; }
.disclaimer-section ul { padding-left: 24px; margin-bottom: 16px; }
.disclaimer-section li { margin-bottom: 8px; }
.disclaimer-footer { margin-top: 30px; padding: 16px; background: #fffaeb; color: #8d6708; border-radius: 8px; text-align: center; }
</style>
