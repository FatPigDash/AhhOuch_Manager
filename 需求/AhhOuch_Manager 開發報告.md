# AhhOuch_Manager 開發報告

> **本文件用途**：作為專案的「單一銜接文件」。之後開新對話只要先讀本檔，即可掌握
> 專案目標、最終架構、關鍵慣例、開發歷程、目前進度與待辦，無需重讀整個對話。
>
> 相關文件：
> - [`AhhOuch 需求.md`](./AhhOuch%20需求.md) — 原始需求（不可變的目標）
> - [`AhhOuch 開發計畫.md`](./AhhOuch%20開發計畫.md) — 桌面版時期的總體規劃與需求對照表
> - [`AhhOuch_Manager 幹部系統手機版開發計畫.md`](./AhhOuch_Manager%20幹部系統手機版開發計畫.md) — 手機版轉型開發計畫（M1–M6）
> - [`AhhOuch_Manager 多人使用需求.md`](./AhhOuch_Manager%20多人使用需求.md) — 系統拆分方向文件
>
> 報告產生日期：2026-06-20（最後更新：2026-06-29）
> ｜ 對應版本：app.toml 2.9.0 ｜ 狀態：**M0–M6 全數完成、需求全項驗收通過；手機版 PWA 上線運作中**

---

## 1. 專案一句話

養身館**幹部**用的資訊管理 PWA：管理美容師資訊卡片與班表，產生內容發布到社群群組。

> 原本另含「客人」角色；2026-06-23 已拆為獨立產品，**本專案僅保留「幹部」系統**（程式碼識別字＝`cadre`）。
> 初期各幹部手機獨立使用（Local-First），資料存在各自手機，開發者不持有資料。

## 2. 技術選型（現行架構）

| 項目 | 選擇 |
| --- | --- |
| 前端 | Vue 3 + Vite、vue-router(hash)、SortableJS(拖曳)、html2canvas(發布圖片) |
| 資料層 | **IndexedDB（Local-First）**，各幹部手機獨立儲存 |
| 圖片處理 | `imageUtil.js`（canvas 縮圖 + JPEG 壓縮）；full ≤1600px / thumb ≤400px |
| 發布 | Web Share API（LINE 等）＋ Telegram 直連（前端直呼 `api.telegram.org`） |
| 備份 | fflate(ZIP) + Web Crypto AES-GCM 選擇性加密，副檔名 `.ahbk` |
| PWA | vite-plugin-pwa（autoUpdate + Service Worker），離線可用 |
| 托管 | **GitHub Pages**（`https://FatPigDash.github.io/AhhOuch_Manager/`） |
| CI/CD | GitHub Actions（push main → 自動 build + deploy，2-3 分鐘生效） |

> **歷史架構（已停用但程式碼仍存於 repo）**：後端 Python 3.11+ / FastAPI + Uvicorn / SQLModel / SQLite / PyInstaller `--onefile` → 單一免安裝 exe。前端已完全不依賴後端，後端程式碼保留於 `backend/` 供參考，不再使用。

## 3. 目錄結構（現行）

```
AhhOuch_Manager_Edit/
├─ app.toml              ★唯一事實來源：軟體名稱+版次（連動前端標題）
├─ .github/workflows/
│  └─ deploy.yml         GitHub Actions：push main → build + deploy GitHub Pages
├─ frontend/
│  └─ desktop/
│     ├─ index.html       PWA 入口（apple-mobile-web-app 標籤）
│     ├─ vite.config.js   Vite + PWA 設定（讀 app.toml 版次、manifest、workbox）
│     ├─ package.json     依賴：vue, vue-router, sortablejs, html2canvas, fflate
│     ├─ public/          PWA 圖示（icon-192, icon-512, apple-touch-icon）
│     ├─ scripts/         create-icons.mjs（產生 PWA 圖示）
│     └─ src/
│        ├─ main.js       Vue 進入點
│        ├─ App.vue       全域佈局（品牌頁首、備份提醒橫幅、教學連結）
│        ├─ router.js     hash 路由（cadre-list/card/schedules/schedule/backup/publish-settings/guide）
│        ├─ db.js         IndexedDB 完整資料層（cards/images/schedules/entries/text_templates/publish_targets）
│        ├─ api.js        業務 API 封裝（全部呼叫 db.js，無任何 fetch）
│        ├─ telegram.js   Telegram Bot API 直連（sendMessage/sendPhoto/sendMediaGroup/edit*）
│        ├─ share.js      Web Share API 封裝（share/canShare/urlsToFiles）
│        ├─ imageUtil.js   圖片最佳化（processImage → full+thumb JPEG）
│        ├─ crypto.js     AES-GCM 選擇性加密（備份用）
│        ├─ backup.js     ZIP 打包/還原（exportBackup/importBackup）
│        ├─ backupMeta.js  備份時間記錄（localStorage，每月提醒判斷）
│        ├─ style.css     全域樣式
│        ├─ components/
│        │  ├─ CadreNav.vue       頁籤導覽（資訊卡片｜班表｜發布設定｜備份）
│        │  └─ TextTemplateBar.vue 標題/結語文字模板列
│        └─ views/
│           ├─ CadreCardListView.vue   資訊卡片列表（卡片/列表切換、批次發布）
│           ├─ CadreCardDetailView.vue 資訊卡片編輯（多圖/封面/介紹/發布）
│           ├─ ScheduleListView.vue    班表列表（草稿/已發布徽章）
│           ├─ ScheduleEditView.vue    班表編輯（日期/標題/出勤/時段/結語/發布）
│           ├─ PublishSettingsView.vue  Telegram 發布目標設定（金鑰/群組/教學彈窗）
│           ├─ BackupView.vue          備份與還原（ZIP 下載/匯入/加密）
│           └─ GuideView.vue           軟體教學＋使用聲明
├─ backend/              （歷史遺留，前端已不依賴；保留供參考）
│  ├─ main.py / config.py / database.py / version.py
│  ├─ models/            cadre, schedule, text_template, publish
│  ├─ routers/           cadre.py, publish.py
│  └─ services/          image_service, shift_calculator, time_utils, publish_service
├─ run.py / build.py / run_dev.bat / install.bat / requirements.txt / preview_server.py
├─ README.md             PWA 架構說明（幹部加入主畫面教學、開發者部署流程）
├─ DATA/                 （桌面版用；PWA 版資料存手機 IndexedDB）
├─ 打包輸出/             （桌面版 exe；已不使用）
└─ 需求/                 需求文件、開發計畫、本報告
```

## 4. 關鍵慣例與設計決策（**銜接前必讀**）

1. **版本/名稱只改根目錄 `app.toml`**。`vite.config.js` 在 build 時讀取 `app.toml` 的 `version` 並透過 `define: { __APP_VERSION__ }` 注入前端。**勿在他處硬編碼。**
2. **資料層 = IndexedDB（`db.js`）**：DB 名 `ahhouch_db` version 2，6 個 object stores：`cards`、`images`（index: `by_card`）、`schedules`、`entries`（index: `by_schedule`）、`text_templates`（index: `by_kind`）、`publish_targets`。每個操作開獨立 transaction。
3. **圖片**以 Blob 存 IndexedDB（`full` + `thumb` 兩份）。讀取時用 `URL.createObjectURL(blob)` 產生 Object URL。上傳時統一經 `imageUtil.processImage()` 壓縮縮圖。上傳第一張圖片時**自動設為封面**（`db.addImage` 檢查 `cover_image_id`），後續以 ★ 按鈕手動切換。
4. **發布管道**：三種並存——
   - **Web Share API**（`share.js`）：分享至 LINE 等，由手機原生分享選單處理。
   - **Telegram 直連**（`telegram.js`）：前端直呼 `api.telegram.org`，用 `URLSearchParams`/`FormData` 避免 CORS preflight。支援覆蓋（editMessage）與全新發布（sendMessage），覆蓋失敗時自動降級全新。
   - **備援**：複製純文字 / 下載排版圖片（html2canvas）。
5. **備份**（`backup.js` + `crypto.js`）：ZIP（fflate）格式，副檔名 `.ahbk`，可選 AES-GCM 加密。匯入為整批覆蓋（單一 IndexedDB transaction 原子性）。`backupMeta.js` 以 localStorage 記錄上次備份時間，逾 30 天顯示提醒橫幅。
6. **部署**：`git push origin main` → GitHub Actions 自動 build + deploy → 幹部重新整理頁面即取得最新版。
7. **hash 路由**：GitHub Pages 靜態托管免伺服器端 rewrite，重新整理不會 404。
8. **編輯 UX**：文字欄位為「草稿＋[儲存]」模式，未存離開會警示。圖片維持即時存檔。
9. **排序**：資訊卡片依 `_name_sort_key`（數字自然排序 + Unicode 碼點），不提供手動排序。班表出勤人員依資訊卡片列表順序排列。
10. **文字模板**（`TextTemplateBar.vue`）：標題與結語各自獨立模板池，可儲存/選用/管理。

## 5. 開發歷程與結果

### 第一階段：桌面版（M0–M8，已完成，現為歷史遺留）

> 此階段建立了 FastAPI+Vue 桌面 exe 版本，完成客人＋店家全功能。2026-06-23 系統拆分後，客人系統移除、店家更名為幹部。桌面版程式碼仍存於 `backend/`，但前端已不依賴。

- **M0** 專案骨架與打包流水線（FastAPI+Vue、app.toml/version.py、build.py/PyInstaller）
- **M1** 客人：養身館與看板（CRUD、五預設看板、卡片標題+封面）
- **M2** 拖曳與排序（SortableJS、看板排序模式）
- **M3** 卡片完整內容（簡介多圖、心得日曆評分、評分模板）
- **M4** 店家：美容師資訊卡片（CRUD、多圖封面、完整/簡短介紹、發布 modal）
- **M5** 店家：班表（多行標題、出勤人員、時段手動/自動換算、發布格式）
- **M6** 社群 API 串接（LINE/Telegram 通用骨架）
- **M7** 手機版（同一套 RWD 響應式）
- **M8** 收尾與驗收（整合測試、打包 exe）

### 第二階段：手機版 PWA 轉型（M1–M6，全數完成）

> 依 [`AhhOuch_Manager 幹部系統手機版開發計畫.md`](./AhhOuch_Manager%20幹部系統手機版開發計畫.md) 執行，從「FastAPI + SQLite + exe」轉為「Vue 3 PWA + IndexedDB + GitHub Pages」。

- **M1 資料層移植**（§12 的 11.38）：新增 `db.js`（IndexedDB 完整資料層），`api.js` 全面改為呼叫 `db.js`，無任何 fetch。移除 Telegram 自動發布 UI（M1 清理，後於 11.45 還原為前端直連）。修正手機版面（CadreNav flex-wrap、CadreCardDetailView 手機斷點等）。
- **M2 PWA 化 + GitHub Pages**（§12 的 11.39）：vite-plugin-pwa（autoUpdate + Service Worker）、manifest、PWA 圖示、iOS meta tags。GitHub Actions workflow 自動 deploy。部署網址 `https://FatPigDash.github.io/AhhOuch_Manager/`。
- **M3 圖片功能**（§12 的 11.40）：`imageUtil.js` 匯入最佳化+縮圖（full ≤1600px / thumb ≤400px JPEG），支撐 2000 張容量。新增拍照按鈕（`<input capture>`）與剪貼簿貼上按鈕。
- **M4 發布（Web Share API）**（§12 的 11.41）：`share.js` 封裝。卡片可選是否附照片、完整/簡短介紹。班表分享格式化文字。降級提示（不支援 Web Share 時顯示備援）。
- **M5 草稿管理**（§12 的 11.42）：班表即時存草稿＋發布狀態徽章（草稿灰/已發布綠）。`markSchedulePublished` 記錄發布時間。
- **M6 備份與收尾**（§12 的 11.43）：`backup.js`（fflate ZIP）+ `crypto.js`（AES-GCM 選擇性加密）。`BackupView.vue` 匯出/匯入。每月提醒橫幅。語系相容（繁中/日/英不破版）。整體驗收通過（§12 的 11.44）。

### 補做與後續精修（全數已完成）

- **Telegram 自動發布還原**（§12 的 11.45）：純前端直連 `api.telegram.org`，不需後端。`telegram.js` 移植 sendMessage/sendPhoto/sendMediaGroup，修正 CORS preflight 問題（改用 URLSearchParams/FormData）。`PublishSettingsView.vue` 還原，簡化為 Telegram 專用。DB 升版 v1→v2，新增 `publish_targets` store。
- **卡片發布強化**（§12 的 11.46–11.49）：info_link_label 標籤、覆蓋/全新發布模式、批次發布（多張卡片×多目標×連結回填）、被刪訊息自動降級全新。
- **班表改善**（§12 的 11.50–11.51）：出勤排序依資訊卡片順序、預設自動換算、發布名字超連結（HTML parse_mode）、班表 Telegram 訊息連結與覆蓋模式。
- **備份 UI 簡化**（§12 的 11.52）：移除 Web Share 備份按鈕（iOS 手勢限制），改單一下載鈕+雲端上傳說明。
- **教學頁重寫**（§12 的 11.53, 11.55）：GuideView 全面重寫為 7 段實際操作說明＋CSS 模擬圖，刪除假 AI 圖片。新增「回到主頁」按鈕。
- **UI 一致化**（§12 的 11.54, 11.56, 11.57）：首圖自動封面、卡片/列表切換改 tab 底線風格、發布設定教學彈窗快速複製按鈕。

### 5 附錄：版本修訂紀錄（依版次）

> 版本號集中於 `app.toml`（唯一事實來源）。格式參考 [Keep a Changelog](https://keepachangelog.com/)；最新版本在最上方。

#### [2.9.0] — 2026-06-29
- 發布設定教學彈窗新增快速複製按鈕（§12 的 11.57）。
- 待修改檔案移除完成事項。

#### [2.8.0] — 2026-06-27
- 教學頁新增「回到主頁」按鈕（§12 的 11.55）。
- 資訊卡片列表切換按鈕改 tab 底線風格（§12 的 11.56）。

#### [2.6.0] — 2026-06-27
- GuideView 軟體教學全面重寫（§12 的 11.53）。
- 美容師卡片首圖自動設為封面（§12 的 11.54）。

#### [2.5.0] — 2026-06-26
- 備份 UI 簡化：移除分享按鈕，改單一下載鈕＋雲端上傳說明（§12 的 11.52）。

#### [2.4.0] — 2026-06-26
- 班表新增 Telegram 訊息連結與覆蓋發布模式（§12 的 11.51）。

#### [2.3.0] — 2026-06-26
- 美容師卡片資訊連結加「發布設定名稱」標籤（§12 的 11.46）。
- 卡片發布確認視窗選擇覆蓋或全新（§12 的 11.47）。
- 批次發布美容師卡片（§12 的 11.48）。
- 發布時原訊息被刪除自動降級全新（§12 的 11.49）。
- 班表出勤排序依資訊卡片順序、預設自動換算、發布名字超連結（§12 的 11.50）。

#### [2.2.0] — 2026-06-26
- M3–M6 一口氣完成（§12 的 11.40–11.43）。
- Telegram 自動發布還原為前端直連（§12 的 11.45）。

#### [2.1.0] — 2026-06-25
- 架構轉型完成：M1 IndexedDB 移植（§12 的 11.38）＋ M2 PWA 化 + GitHub Pages（§12 的 11.39）。
- 修正 CI build（package.json vite-plugin-pwa 漏 commit）。

#### [2.0.0] — 2026-06-23
- 系統拆分：移除客人系統、店家→幹部全面更名（§12 的 11.36）。

#### [1.7.0] — 2026-06-23
- 養身館列表拖曳排序（§12 的 11.34）。
- 養身館多幹部與聯絡資訊（§12 的 11.35）。

#### [1.5.0] — 2026-06-21
- 出勤時段 pill 時間序排列（§12 的 11.31）。
- 其他 M4–M6 範圍精修（§12 的 11.14–11.30, 11.37）。

#### [1.0.0 以前]
- 桌面版 M0–M8 全功能完成（見§5 第一階段）。含 M1–M3 客人模式精修（§12 的 11.1–11.13）。

## 6. 決策紀錄

| 決策 | 結論 | 來源 |
| --- | --- | --- |
| 整體架構 | Vue 3 PWA + IndexedDB + GitHub Pages（Local-First，無後端） | 手機版開發計畫 |
| 系統範圍 | 僅幹部系統，客人系統拆為獨立產品 | §12 的 11.36 |
| 手機版做法 | 同一套響應式（RWD），非另建 app | 桌面版 M7 |
| 資料存放 | 各幹部手機獨立（IndexedDB），開發者不持有 | 手機版開發計畫 |
| 發布方式 | Web Share API + Telegram 前端直連並存 | §12 的 11.41, 11.45 |
| 備份格式 | ZIP（fflate）＋選擇性 AES-GCM 加密，副檔名 `.ahbk` | §12 的 11.43 |
| 備份匯入 | 整批覆蓋（單一 transaction） | §12 的 11.43 |
| 備份提醒 | 應用內橫幅（逾 30 天或從未備份） | §12 的 11.43 |
| 班表自動換算 | 含端點，每班 1.5h 共 8 班次，跨午夜回繞 | 桌面版 M5 |
| 發布圖片產生 | html2canvas（前端） | 桌面版 PoC 6.2 |
| 卡片排序 | 數字自然排序 + Unicode 碼點，不提供手動排序 | §12 的 11.14 |
| 班表出勤排序 | 依資訊卡片列表順序 | §12 的 11.50 |
| 圖片最佳化 | full ≤1600px / thumb ≤400px JPEG，支撐 2000 張 | §12 的 11.40 |
| Telegram CORS | 改用 URLSearchParams/FormData 避免 preflight | §12 的 11.45 |
| 卡片發布覆蓋 | 優先覆蓋（editMessage）、被刪自動降級全新 | §12 的 11.47, 11.49 |

## 7. 需求驗收對照

> 以手機版開發計畫的需求對照表（§12 的 11.44）為準，全項驗收通過。

| # | 需求 | 狀態 |
| --- | --- | --- |
| A1 | PWA、iOS 加入主畫面 | ✅ M2 |
| A2 | iOS 優先、Android 兼容、手機/平板 | ✅ M2 |
| A3 | 無需開發者電腦/伺服器 | ✅ M1（IndexedDB Local-First） |
| C1 | 每位美容師獨立卡片，名稱可文字/編號 | ✅ M1 |
| C2 | 多圖上傳、設封面 | ✅ M1/M3 |
| C3 | 完整介紹／簡短介紹 | ✅ M1 |
| C4 | 卡片發布、可選是否附照片 | ✅ M4（Web Share + Telegram 直連） |
| C5 | 發布可選完整／簡短 | ✅ M4 |
| S1–S4 | 班表標題/出勤/時段（手動＋自動換算） | ✅ M1 |
| S5 | 班表發布含標題/編號/簡介/時段 | ✅ M4 |
| S6/S7 | 發布後留草稿、可改後再發布 | ✅ M5（即時存草稿＋發布狀態徽章） |
| D1/D2 | 資料全存本機、開發者不持有 | ✅ M1 |
| D3 | 相簿選取／拍照／剪貼簿貼上 | ✅ M3 |
| D4 | 帳號備份（匯出/匯入跨裝置） | ✅ M6（含選擇性加密、每月提醒） |
| D5 | 圖片 2000 張容量基準 | ✅ M3（匯入最佳化＋縮圖） |

> **待實機驗證項**（桌面 Chromium 已驗證程式路徑與降級邏輯，以下留待真機）：
> - Web Share 攜圖至 LINE（iOS Safari / Android Chrome）
> - iOS/Android PWA 儲存持久性與 2000 張實測
> - `capture` 開相機與 `clipboard.read()` 讀圖

## 8. 目前狀態

**全功能上線中（2026-06-29）**：M0–M6 全數完成，需求對照表全項驗收通過。PWA 已部署至 `https://FatPigDash.github.io/AhhOuch_Manager/`，幹部可直接使用。

- **技術架構**：Vue 3 PWA + IndexedDB + GitHub Pages。前端完全不依賴後端。
- **當前版本**：app.toml `2.9.0`
- **功能完整度**：資訊卡片（CRUD、多圖、封面、介紹）、班表（日期、標題模板、出勤、時段、結語模板、草稿管理）、發布（Web Share + Telegram 直連 + 批次發布 + 覆蓋模式）、備份（ZIP + 加密 + 每月提醒）、教學頁、PWA 離線支援。
- **git 歷程**：V0.6.0（桌面版完成） → V1.x（桌面版精修） → V2.0.0（系統拆分） → V2.1.0（PWA 轉型） → V2.2.0–V2.9.0（手機版完整功能＋精修）。
- **部署**：GitHub Actions workflow 自動 build + deploy，push main 後 2-3 分鐘生效。
- **本機開發**：`cd frontend/desktop && npm run dev`（Vite HMR，存檔即更新）。

## 9. 待辦

> 目前無未完成的里程碑。以下為可能的後續方向：

1. **待實機驗證**：Web Share 攜圖至 LINE、iOS/Android PWA 儲存持久性與 2000 張實測、`capture` 開相機與 `clipboard.read()` 讀圖。
2. **美容師卡片新增「當日班表」欄位**（`待修改.md` 第 3 項）。
3. **後端程式碼清理**：`backend/` 目錄對 PWA 已無作用，可考慮移除或歸檔。
4. **桌面版遺留檔案清理**：`build.py`、`run.py`、`run_dev.bat`、`install.bat`、`requirements.txt`、`preview_server.py`、`打包輸出/`、`DATA/` 等對 PWA 已無作用。

## 10. 啟動／部署 速查

```powershell
# 本機開發（Vite HMR，存檔即更新，不需 build）
cd frontend\desktop
npm install          # 首次安裝
npm run dev          # http://localhost:5173

# 部署給幹部（push 後 GitHub Actions 自動 build + deploy，2-3 分鐘生效）
git push origin main

# 幹部使用網址
# https://FatPigDash.github.io/AhhOuch_Manager/

# 修改版次／名稱（唯一事實來源）
# 編輯 app.toml → version = "x.x.x"
```

## 11. 給下一個對話的銜接指引

> **想確認目前實際進度／狀況，權威來源依序為**：
> ① 本報告（**§5 開發歷程 ＋ §12 精修條目，需合併看**）— 人類可讀的現狀；
> ② `git log` 與本報告 **§5 附錄（版本修訂紀錄）** — 版本歷程；
> ③ **程式碼本身**（最終事實）。若文件與程式碼衝突，**以程式碼為準**，並回頭修正文件。

1. 先讀本報告 §4（慣例）、§8（狀態）、§9（待辦），即可接手。
2. **資料模型變更** → 改 `db.js` 的 IndexedDB schema。若需 DB 升版（新增 object store），改 `DB_VERSION` 並在 `onupgradeneeded` 處理。新增欄位於既有 store 時，通常只需在業務函式中處理（IndexedDB 為 schemaless object store），不需升版。
3. **改版次／名稱** → 只動 `app.toml`。`vite.config.js` 會在 build 時自動讀取。
4. **發布管道調整** → Telegram 邏輯在 `telegram.js`，Web Share 在 `share.js`，發布設定存 IndexedDB `publish_targets`。
5. **備份格式變更** → 注意 `backup.js` 的 manifest 結構與 `db.js` 的 `dumpAll`/`restoreAll`，需向後相容。
6. 要做 UI 變更 → `npm run dev` 在瀏覽器確認；手機版用瀏覽器響應式檢視（≤640px）測試。
7. 動到使用者需求行為前 → 對照需求文件，並把修訂歷程補在 **本報告 §12**。

---

## 12. 開發中修訂歷程

> 此區為開發過程中的逐項調整紀錄。保留原 `11.x` 子編號以維持各條目彼此的交叉引用。
>
> **這些調整皆已實作並套用至現行程式（＝目前實際行為），非待辦。**
>
> 依時間分為兩大階段：
> - **11.1–11.37**：桌面版時期的精修（FastAPI + SQLite 架構下完成，部分邏輯已移植至 PWA 版）
> - **11.38–11.57**：PWA 轉型後的開發（IndexedDB + GitHub Pages 架構）
>
> 讀法：先看 §5 找到對應階段，再查本節條目，即可掌握該功能的**最新實際行為**。

### 2026-06-20 — 客人模式 UX 調整（M1–M3 範圍精修）

本批調整集中於**客人端卡片詳情頁與看板排序**的使用體驗，皆對應既有需求 C10／C17／C19，未變更整體里程碑規劃。

> ⚠ 以下 11.1–11.13 為桌面版客人系統的精修紀錄。客人系統已於 11.36 移除，這些條目僅作歷史參考。部分設計理念（Natural Sort、草稿模式等）已沿用至幹部系統。

#### 11.1 看板排序切換需二次確認（C10）
- 每個看板各自保有排序方式（預設＝標題 Unicode／手動）。
- **切換時跳出確認視窗**：
  - 切到「預設(標題)」→ 確認後保存目前手動排序為快照、再依標題 Unicode 重排整個看板。
  - 切到「手動」→ 確認後依快照**還原**先前的手動排序。
- 資料：`CustomerCard` 新增 `manual_position`（手動排序快照欄位，遷移時以既有 `position` 回填）。
- API：新增 `POST /api/customer/boards/{id}/sort-mode`（處理快照／還原與重排）。

#### 11.2 評分項目新增「有/無」類型（C17/C19）
- 評分模板項目除原本的「分數(0~10)」外，新增「**有/無**」類型（例：項目「筋膜刀」選有或無）。
- 心得評分列依項目類型呈現：分數型＝滑桿＋**可直接輸入的數字框**；有/無型＝「有」「無」兩按鈕（再點同一個可取消）。
- 類型以**並排 pill（選中打勾）**呈現，取代原本單鍵切換，較直覺。
- 資料：`RatingTemplateItem` 新增 `item_type`（score|yesno）；`ReviewScore` 新增 `item_type`（快照）與 `yesno_value`。

#### 11.3 評分模板改為「草稿＋儲存」編輯模式（C17）
- 進入「⚙ 評分模板」編輯時**隱藏心得區**，並以**下拉選單**一次只編輯一個模板（不再一次列出全部）。
- 項目可新增／刪除／改名／改類型／**上下排序**／**從其他模板載入項目**，皆為本地草稿，按 **[儲存]** 才寫入；未儲存即離開會**跳警示**。
- **儲存不影響既有心得**；之後用此模板新增的心得才採用新版項目。
- 心得端偵測所屬模板已更新時顯示提示與 **[更新為最新項目]** 按鈕（同名項目評分保留、新增項目空白、移除項目刪除）。
- API：新增 `PUT /api/customer/templates/{id}`（整批覆蓋名稱＋項目）、`POST /api/customer/reviews/{id}/sync`（心得同步至模板最新項目）。

#### 11.4 心得與簡介改為「草稿＋儲存」編輯模式（C12–C22）
- **心得**：日期／分數／有無／補充說明／心得文字改為本地暫存，新增 **[儲存心得]** 按鈕；未儲存離開跳警示。
- **簡介**：國籍／文字說明改為本地暫存，新增 **[儲存簡介]** 按鈕；未儲存離開跳警示（圖片上傳/貼上/封面/刪除維持即時生效）。
- 三區塊（簡介／模板／心得）未儲存狀態合併為單一離開提示；新增/刪除/切換模板等會重載的結構操作會先確認以免覆蓋未儲存內容。

### 2026-06-20 — 看板卡片封面高度調整與美容師簡介燈箱

#### 11.5 美容師資訊卡片封面高度加倍（店家 StoreCardListView）

- 美容師資訊卡片列表頁的封面高度從 `130px` 改為 `260px`，讓封面圖呈現更多畫面。

#### 11.6 看板卡片封面高度與顯示方式調整（客人 SpaBoardView）

- 封面由固定高度改為**隨圖片原始比例自動撐高**（`height: auto`），避免圖片被裁切。
- 設定 `min-height: 90px`，確保無封面圖的卡片仍有最低高度可顯示標題。
- 封面圖加上 `max-height: calc(100vh - 280px)` 上限。
- **標題列改至封面圖下方獨立區塊**（白底深色字），不再疊在圖片上。
- ⚠ **已知問題（→ 已於 §11.9 解決）**。

### 2026-06-20 — 看板卡片標題顯示修正

#### 11.9 看板卡片標題移至封面圖上方（客人 SpaBoardView）

- 將 `card-body`（標題＋刪除鈕）**搬至封面圖上方**，恆可見。
- 封面圖維持等比縮放，不裁切。解決了標題被圖片推出可見區的根本問題。

#### 11.7 美容師簡介頁圖片燈箱（客人 CardDetailView）

- 點擊圖片可彈出燈箱大圖視窗。同樣修改也套用至幹部美容師資訊卡片頁。

### 2026-06-20 — 看板卡片視覺對比強化

#### 11.10 卡片底色與看板底色改為高對比色系

- 卡片暖米白/金（`#fffbf0`、`#d4a84b`）vs 看板冷藍灰（`#e9eef3`），冷暖對比鮮明。

### 2026-06-20 — 看板排序 Bug 修正

#### 11.11 預設排序改為 Natural Sort（C10）

- 新增 `_natural_key(s)` 函式，數字段轉 `int` 比數值。`3 < 11 < 12`（數值順序）。

#### 11.12 跨看板拖曳不破壞排序（C9/C10）

- unicode 模式：忽略 drop index，整體依 natural sort 重排。
- 手動模式：維持依 drop index 插入。
- 重排後同步 `manual_position = position`。

#### 11.8 其他
- Vite 代理新增 `/images`，README 補充說明。

### 2026-06-20 — 心得區塊標題

#### 11.13 心得標題改為「養身館名稱 卡片標題 心得」

### 2026-06-21 — 店家模式 UX 與資料模型調整（M4 範圍精修）

#### 11.14 美容師資訊卡片預設排序改為「數字自然＋其餘 Unicode」，不提供手動排序

- 純數字 / `#`純數字 → 數值排序（`#5 < #21 < #61 < #199`）。
- 中文 / 英文 / 日文 → Unicode 碼點排序。
- 以 `_name_sort_key` 排序，前端無手動排序 UI。

#### 11.15 店家資訊卡片詳情頁改「草稿＋儲存／取消」

- 名字／完整介紹／簡短介紹改為本地草稿＋按 [儲存] 才寫回。
- 未儲存就離開跳確認。圖片維持即時存檔。
- 按「發布」時若有未儲存變更，先提示並儲存再發布。

#### 11.16 移除 `StoreCard.position` 欄位

#### 11.17 移除壞掉的 launch.json 預覽設定

### 2026-06-21 — 社群發布平台調整（M6 範圍精修）

#### 11.18 發布平台改為「Telegram(預設)＋X」，移除 LINE

- **Telegram** 為實際實作，填金鑰＋群組 ID 即可推送。
- **X** 僅列為可選平台，自動發送尚未實作。
- 遺留 LINE 資料於啟動清除。

> ⚠ PWA 轉型後，X 選項已移除（`PublishSettingsView` 簡化為 Telegram 專用）。

#### 11.19 發布設定頁用語白話化＋欄位說明＋[?] 教學彈窗

- 欄位改用白話標題（「機器人金鑰」「要發到哪個群組」）並加說明。
- 兩個教學彈窗：金鑰申請流程、群組編號取得方式。

#### 11.20 發布目標按鈕顯示「平台 名稱」＋發送前二次確認

### 2026-06-21 — 班表 UX 與資料模型調整（M5 範圍精修）

#### 11.21 出勤時段沿用出勤人員的名字排序

- 序列化與發布文字皆依 `_name_sort_key` 排序，發布順序與畫面一致。

#### 11.22 移除 `ScheduleEntry.position` 欄位

#### 11.23 出勤時段預設改為「自動換算」

#### 11.24 換算班次紀錄保留（載入時依 `auto_start` 重算還原）

#### 11.25 編輯班表頁頂部列凍結（sticky）

### 2026-06-21 — 自動發布內容選擇、班表名字超連結與班表日期

#### 11.26 美容師卡片自動發布改為「複選內容＋挑圖＋預覽」流程

- 複選 checkbox：`圖片`／`完整介紹`／`簡短介紹`。
- 圖片挑選格（複選）。即時預覽。
- Telegram 圖片發送：單張 `sendPhoto`、多張 `sendMediaGroup`。

#### 11.27 班表發布：美容師名字超連結到資訊訊息

- `StoreCard`/`CadreCard` 的 `info_link` 欄位。
- 卡片發布成功後自動擷取 Telegram 訊息連結回填。
- 班表以 HTML `parse_mode` 送出，名字以 `<a href>` 包裹。
- 限制：超連結只在自動發布有效，群組須為超級群組/公開群組。

#### 11.28 班表新增日期欄位，發布時置頂

- `Schedule.date`（ISO），小日曆點選，格式如 `2026/06/21 (日)`。

### 2026-06-21 — 班表結語欄位與文字模板

#### 11.29 班表新增「結語」欄位，發布時置底

#### 11.30 標題與結語可儲存／選用／編輯文字模板

- `TextTemplate` 模型（`kind: title|footer`）。
- `TextTemplateBar.vue` 可重用元件：套用／另存／管理。

### 2026-06-21 — 出勤時段時間序排列

#### 11.31 出勤時段 pill 一律依時間序排列，含跨午夜班次

- **最大空檔旋轉法**：各時段視為 24 小時圓環上的點，找最大空檔後連續排列。
- 所有時段異動經 `saveSlots` 統一排序後存回。

### 2026-06-23 — 客人模式看板/簡介 UX 與養身館資料模型調整

#### 11.32 看板畫面新增垂直捲軸，卡片以原始高度顯示

#### 11.33 美容師簡介與心得文字框隨內容自動長高

#### 11.34 養身館列表支援拖曳排序＋插入提示

#### 11.35 養身館支援多位幹部，各含聯絡資訊

### 2026-06-23 — 系統拆分：移除客人系統、店家→幹部全面更名

#### 11.36 移除客人系統、店家→幹部全面更名

- **移除客人系統**：刪除 6 個客人模型、3 個客人 view、所有客人 API。
- **更名**：`StoreCard→CadreCard`、`storecard→cadrecard`、`/api/store→/api/cadre`、`StoreCardDetailView→CadreCardDetailView` 等全面更名。
- **移除角色切換鈕**：`App.vue` 只剩單一系統，`/` 直接進幹部列表。
- **資料庫遷移**：`_migrate_legacy_split()` 處理表更名、欄位更名、客人表移除（在 `create_all` 之前執行）。

### 2026-06-24 — 美容師資訊編輯頁面 UX 精修

#### 11.37 美容師資訊編輯頁：頁面標示、文字框自動長高、修正編輯時畫面跳動

- 標題列下方加副標題「美容師資訊編輯頁面」。
- `v-autoresize` 指令套用於完整介紹／簡短介紹 textarea。
- 修正編輯時畫面跳動（`updated` hook 加值變更判斷 + scrollTo 雙重保險）。

### 2026-06-25 — 架構轉型：FastAPI+exe → Local-First PWA（M1–M2）

#### 11.38 M1：幹部系統資料層移植 — FastAPI → IndexedDB（Local-First）

**目標**：前端 App 完全離線可用，不依賴開發者電腦啟動後端。

**新增 `frontend/desktop/src/db.js`**（IndexedDB 完整資料層）：
- DB 名 `ahhouch_db` version 1，object stores：`cards`、`images`（index: `by_card`）、`schedules`、`entries`（index: `by_schedule`）、`text_templates`（index: `by_kind`）。
- 每個操作開獨立 transaction；多 store 原子操作用 `txDone(t)` 等待 transaction 完成。
- 圖片以 Blob 存 IndexedDB，讀取時用 `URL.createObjectURL(blob)` 產生 Object URL。
- 移植原後端邏輯：`normalizeTime`、`calcShiftSlots`、`cardPublishText`、`schedulePublishText`。

**改寫 `api.js`**：所有 method 改為呼叫 `db.js`，無任何 `fetch`。

**清理前端 UI**：移除 `PublishSettingsView.vue`、Telegram 發布 UI、`info_link` 欄位（後於 11.45 還原）。

**P0 手機版面修正**：CadreNav flex-wrap、CadreCardDetailView 手機斷點。

#### 11.39 M2：PWA 化與 GitHub Pages 自動部署

**PWA 設定**：`vite-plugin-pwa`（`registerType: autoUpdate`、`generateSW`）、manifest、iOS meta tags、PWA 圖示。

**GitHub Pages 自動部署**：`.github/workflows/deploy.yml`，push main → checkout → npm ci → build → deploy-pages。

**部署網址**：`https://FatPigDash.github.io/AhhOuch_Manager/`

**修正 CI build**：package.json 的 vite-plugin-pwa 漏 commit，補提交後 CI 成功。

### 2026-06-26 — 手機版里程碑完成：M3–M6 ＋ Telegram 自動發布還原

#### 11.40 M3：圖片功能（手機版）

**`imageUtil.js`**（圖片最佳化）：`processImage(File|Blob)` → `{ full, thumb }`，以 canvas 等比縮放 + JPEG 重新編碼。full ≤1600px（0.85）、thumb ≤400px（0.7）。JPEG 無透明度，先鋪白底。

**`db.js`**：`addImage` 改為先 `processImage` 再存，images 記錄新增 `thumb` 欄位。

**`CadreCardDetailView.vue`**：圖片網格用 `thumb_url`，燈箱用完整圖。新增「📷 拍照」與「📋 貼上」按鈕。新增 `busy` 處理中狀態。

#### 11.41 M4：班表與卡片發布（Web Share API）

**`share.js`**：`canShare()`、`canShareFiles()`、`share()`、`urlsToFiles()`。

**`CadreCardDetailView.vue`**：發布視窗新增「📤 分享至 LINE 等」主按鈕。新增「連同照片一起發出」核取方塊。降級提示。

**`ScheduleEditView.vue`**：發布視窗新增分享按鈕，分享格式化文字。

#### 11.42 M5：草稿管理

**`db.js`**：schedule 記錄新增 `published_at`。新增 `markSchedulePublished(id)`。

**`ScheduleEditView.vue`**：發布成功後記錄發布時間。

**`ScheduleListView.vue`**：狀態徽章（綠色「已發布」/ 灰色「草稿」）。

#### 11.43 M6：備份與收尾

**`crypto.js`**：Web Crypto AES-GCM 256，PBKDF2 金鑰導出。加密檔格式：`AOB1` magic + salt + iv + ciphertext。

**`backup.js`**：fflate ZIP，結構：`manifest.json` + `images/`。`exportBackup(password?)` / `importBackup(file, password?)`。

**`db.js`**：新增 `dumpAll()` / `restoreAll(data)`。

**`backupMeta.js`**：`localStorage` 記 `ahhouch_last_backup_at`，`backupOverdue()` 判斷逾 30 天。

**`BackupView.vue`** + 路由 + CadreNav「備份」分頁。

**`App.vue`**：每月提醒橫幅。

**語系相容**：日期用固定格式，繁中/日/英不破版。

#### 11.44 整體驗收（需求對照表）

M0–M6 全數完成，需求對照表全項驗收通過。詳見 §7。

#### 11.45 補做：Telegram 自動發布還原（純前端直連 api.telegram.org）

**`telegram.js`**：移植 sendMessage/sendPhoto/sendMediaGroup。修正 CORS preflight：改用 `URLSearchParams`（`application/x-www-form-urlencoded`）和 `FormData`（`multipart/form-data`）。

**`db.js`**：DB 升版 v1→v2，新增 `publish_targets` object store。納入備份 `ALL_STORES`。

**`PublishSettingsView.vue`** 還原，簡化為 Telegram 專用。保留教學彈窗。

**`CadreCardDetailView.vue` / `ScheduleEditView.vue`**：發布視窗新增「發送到 Telegram」區。Web Share 並存。

### 2026-06-24 — 美容師資訊編輯頁面 UX 精修（同 11.37，時間線重疊）

### 2026-06-26 — 美容師卡片發布強化、批次發布、班表改善

#### 11.46 美容師卡片資訊連結：加入「發布設定名稱」欄位（`info_link_label`）

- `db.js` cards 新增 `info_link_label` 欄位。
- `CadreCardDetailView.vue` 發布視窗顯示對應目標名稱。

#### 11.47 美容師卡片發布：確認視窗選擇覆蓋或全新、優先覆蓋為預設

- `telegram.js` 新增 `editCard`（editMessageText / editMessageMedia）。
- 確認視窗新增 radio：「✏ 覆蓋舊訊息」與「＋ 發布全新訊息」。
- 新增 `parseMsgId` / `buildTgLink` 輔助函式。

#### 11.48 批次發布美容師卡片

- `CadreCardListView.vue` 新增批次模式：工具列「☑ 批次發布」→ 勾選多張 → 浮動操作列。
- 批次發布 Modal 三階段：設定（介紹版本/圖片模式/目標多選/訊息模式）→ 執行中（進度列+即時狀態）→ 完成（摘要）。
- 連結回填（info_link / info_link_label）。

#### 11.49 發布時若原 Telegram 訊息被手動刪除，自動改發全新訊息

- `telegram.js` 新增 `isMessageNotFoundError(e)`。
- 單張與批次發布的 edit 分支皆 try/catch 自動降級。

#### 11.50 班表改善：出勤排序依資訊卡片、預設自動換算、發布名字超連結

- 出勤預設 `time_mode: 'auto'`。
- 出勤排序改依資訊卡片列表順序。
- 發布文字雙輸出：`text`（純文字）與 `html`（Telegram HTML，名字 `<a href>`）。

#### 11.51 班表新增 Telegram 訊息連結與發布覆蓋模式

- schedules 新增 `tg_link` / `tg_link_label`。
- `telegram.js` 新增 `sendScheduleText` / `editScheduleText`。
- 班表發布確認視窗加入覆蓋/全新選項。

#### 11.52 備份 UI 簡化：移除分享按鈕、改單一下載鈕並附雲端上傳說明

- 移除 Web Share 備份（iOS 手勢時序限制導致 `NotAllowedError`）。
- 單一「⬇ 下載備份檔」＋ iOS/Android 雲端上傳操作說明。

### 2026-06-27 — 軟體教學頁全面重寫

#### 11.53 GuideView 軟體教學重寫

- 移除假 AI 圖片（`public/img/` 目錄已刪除），改為 CSS 模擬圖。
- 教學分頁改為 7 段實際操作說明。
- 修正備份副檔名 `.ahhouch` → `.ahbk`。

#### 11.54 美容師卡片：第一張圖片自動設為封面

- `db.js` `addImage`：若 `cover_image_id` 為 null，自動設為封面。

#### 11.55 教學及聲明頁新增「回到主頁」按鈕

- `.guide-topbar` 左側「← 回到主頁」按鈕。

#### 11.56 資訊卡片列表：切換按鈕改為 tab 底線風格

- `.view-toggle` 改為 `border-bottom` + active `border-bottom-color` 設計，與教學頁一致。

### 2026-06-29 — 發布設定教學彈窗新增快速複製按鈕

#### 11.57 發布設定教學彈窗：指令與網址新增快速複製按鈕

- `copyText(text)` 函式 + `navigator.clipboard.writeText()`。
- `/newbot`、`/revoke`、`getUpdates` 網址旁各加「複製」按鈕。
