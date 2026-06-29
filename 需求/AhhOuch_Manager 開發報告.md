# AhhOuch_Manager 開發報告

> **本文件用途**：作為專案的「單一銜接文件」。之後開新對話只要先讀本檔，即可掌握
> 專案目標、最終架構、關鍵慣例、開發歷程、目前進度與待辦，無需重讀整個對話。
>
> 相關文件：
> - [`AhhOuch 需求.md`](./AhhOuch%20需求.md) — 原始需求（不可變的目標）
> - [`AhhOuch 開發計畫.md`](./AhhOuch%20開發計畫.md) — 開發前的總體規劃與需求對照表（修訂歷程已移至本報告 §12）
> - 版本修訂紀錄（依版次）— 已整合於本報告 §5 附錄（原獨立檔 `CHANGELOG.md` 已移除）
>
> 報告產生日期：2026-06-20（最後更新：2026-06-29，§12 增列 11.57：**發布設定教學彈窗新增快速複製按鈕**；前次為 11.54–11.56）
> ｜ 對應版本：app.toml 1.7.0／git V2.0.0→M2 完成 ｜ 狀態：**架構轉型進行中：M1（資料層移植）✅、M2（PWA 化 + GitHub Pages）✅、M3–M6 待開發**

---

## 1. 專案一句話

養身館**幹部**用的資訊管理網頁軟體：管理美容師資訊卡片與班表，產生內容發布到社群群組。

> 原本另含「客人」角色（記錄各養身館美容師資訊與心得，看板化管理，類 Trello）；2026-06-23 已把兩者拆為獨立產品，**本專案僅保留原「店家」系統並更名為「幹部」**（程式碼識別字＝`cadre`），客人系統整組移除（詳見 §12 的 11.36）。

初期單機單人（開發者電腦當伺服器），架構保留多使用者／區網擴充。

## 2. 技術選型（已定案）

| 項目 | 選擇 |
| --- | --- |
| 後端 | Python 3.11+（實機 3.14）、FastAPI + Uvicorn、SQLModel/SQLite |
| 前端 | Vue 3 + Vite、vue-router(hash)、SortableJS(拖曳)、html2canvas(發布圖片) |
| 手機版 | **響應式（同一套 RWD）**，非另建 app（M7 定案） |
| 打包 | PyInstaller `--onefile` → 單一免安裝 exe |
| 伺服器 | 綁 `127.0.0.1:8000`（日後改 `0.0.0.0` 開區網） |

## 3. 最終目錄結構（實際）

```
AhhOuch_Edit/
├─ app.toml              ★唯一事實來源：軟體名稱+版次（連動前端標題、exe 檔名）
├─ run.py                進入點（也是打包進入點，啟動後自動開瀏覽器）
├─ build.py              打包：建前端→PyInstaller→輸出 打包輸出/→清過程檔
├─ install.bat run_dev.bat requirements.txt README.md
├─ backend/
│  ├─ main.py            FastAPI app、掛載 /images 與靜態前端、啟動建 DATA/+init_db
│  ├─ version.py         讀 app.toml（唯一取值來源）
│  ├─ config.py          路徑（開發 vs 凍結 exe 差異）
│  ├─ database.py        SQLite 引擎、init_db、_migrate_legacy_split(店家→幹部更名+移除客人表)、_migrate_columns(補欄位)、_cleanup_legacy_data(清遺留)
│  ├─ models/            cadre schedule text_template publish
│  ├─ routers/           cadre.py(幹部資訊卡片+班表) publish.py(社群發布)
│  └─ services/          image_service shift_calculator time_utils publish_service
├─ frontend/
│  ├─ desktop/src/
│  │  ├─ views/          CadreCardListView CadreCardDetailView
│  │  │                  ScheduleListView ScheduleEditView PublishSettingsView
│  │  ├─ components/      CadreNav.vue  TextTemplateBar.vue（標題/結語模板列）
│  │  ├─ api.js  router.js  App.vue  style.css
│  └─ mobile/            （保留作未來擴充；手機目前用響應式，非獨立 app）
├─ DATA/                 ahhouch.db + images/（gitignore；啟動自動建立）
└─ 打包輸出/             AhhOuch_v<版次>.exe（gitignore）
```

## 4. 關鍵慣例與設計決策（**銜接前必讀**）

1. **版本/名稱只改根目錄 `app.toml`**。其他檔案一律經 `backend/version.py` 取值，
   前端標題、`build.py` 輸出檔名皆連動。**勿在他處硬編碼。**
2. **路徑差異**由 `backend/config.py` 處理：
   - 唯讀資源（前端 dist、app.toml）：開發在專案內、凍結時在 `sys._MEIPASS`。
   - `DATA/`（可寫）：開發在專案根、凍結時在 exe 旁。
3. **資料庫遷移**：SQLite 不會自動 `ALTER`，由 `database.py` 處理，**執行順序固定**：
   先 `_migrate_legacy_split()`（**必須在 `create_all` 之前**：把舊「店家」表更名為「幹部」
   `storecard→cadrecard` 等、欄位 `store_card_id→cadre_card_id`、並 `DROP` 客人系統殘留表）→
   `create_all` → `_migrate_columns()`（`_COLUMN_MIGRATIONS`：PRAGMA 比對後 **ADD COLUMN**）→
   `_cleanup_legacy_data()`（清 LINE 殘留目標）。**新增 model 欄位時，一定要在
   `_COLUMN_MIGRATIONS` 登記**，既有使用者資料才不會在升級時壞掉。表／欄位更名與整表移除
   的實作見 §12 的 11.36（含「更名必須早於 `create_all`」的原因）。
4. **封面圖**由各圖片表的 `is_cover` 計算，回應時組出 `cover_image`，卡片本身不存封面欄。
5. **圖片**存 `DATA/images/`，DB 只存檔名；支援檔案上傳與剪貼簿 base64 貼上（PoC 6.1 已驗證）。
6. **發布**：第一階段產生「排版圖片(html2canvas)＋純文字」供手動貼；第二階段 API 自動發布。
   Telegram 自動發布已支援**文字＋圖片**（§12 的 11.26）與**班表名字超連結**（§12 的 11.27，
   僅自動發布訊息有效、需超級群組）。
7. **後端不會自動 reload**：改後端碼後需手動重啟伺服器（前端 Vite 5173 會熱更新）。
8. **編輯 UX（使用者後續調整）**：簡介／心得／評分模板改為「草稿＋[儲存]」模式，
   未存離開會警示（細節見本報告 §12 的 11.3／11.4）。

## 5. 開發歷程與結果（M0–M8，皆已完成並驗證）

> 每階段都以「後端 TestClient 自動測試 → 前端建置 → 瀏覽器預覽實測」三段驗證。
>
> ⚠️ 各里程碑記錄的是**完成當時**的狀態。其後有多項精修（**已套用至現行程式，即目前實際行為**），
> 下方以「↳」標註對應的 §12 條目；**目前實際狀況＝本節 ＋ §12 合併後的結果**。

- **M0 專案骨架與打包流水線**：建立 FastAPI+Vue 骨架、`app.toml`/`version.py`、
  `install.bat`/`run_dev.bat`/`build.py`/README。**最關鍵風險（打包）提早驗證**：
  能產出單一 exe、雙擊啟動、`DATA/` 自動建於 exe 旁、過程檔自動清（X1–X6）。
- **M1 客人：養身館與看板**：養身館 CRUD、看板增減/改名、建館自動五預設看板、
  卡片基礎（標題+封面）(C1–C8、C11)。
  ↳ 後續精修（已套用）：看板卡片標題移至封面圖上方、封面等比顯示、冷暖配色對比 §12 的 11.6/11.9/11.10。
- **M2 拖曳與排序**：SortableJS 同/跨看板拖曳＋插入符號(C9)、每看板可切「預設(標題)/手動」
  排序(C10)。`sort_mode` 設計在 **Board 層級**。
  ↳ 後續精修（已套用）：切換排序需二次確認＋手動快照還原 §12 的 11.1、**預設排序改 Natural Sort（3<11<12，非純 Unicode）** §12 的 11.11、跨看板拖曳不破壞排序 §12 的 11.12。
- **M3 卡片完整內容**：簡介(多圖/上傳/貼上/封面/國籍/文字/收闔)、心得(日曆/評分/多組/
  新增帶入前次)、評分模板(多組/命名/項目增刪/預設7項) (C12–C22)。含資料庫自動遷移、
  圖片服務、`/images` 靜態掛載。
  ↳ 後續精修（已套用）：評分項目新增「**有/無**」型 §12 的 11.2、評分模板與心得/簡介改「**草稿＋儲存**」模式＋模板同步 §12 的 11.3/11.4、簡介圖片燈箱 §12 的 11.7、心得標題含「館名+卡名」§12 的 11.13。
- **M4 店家：美容師資訊卡片**：資訊卡片 CRUD(名字自輸/多圖+封面/完整·簡短介紹)、
  發布 modal(完整/簡短 pill、預覽、複製文字、html2canvas 下載圖片) (S1–S5)。
  ↳ 後續精修（已套用）：資訊卡片封面高度加倍 §12 的 11.5、圖片燈箱 §12 的 11.7、**資訊卡片預設排序改數字自然＋其餘 Unicode 且不提供手動排序** §12 的 11.14、**詳情頁改「草稿＋儲存/取消」並把發布鈕移左下** §12 的 11.15、移除已無用的 `StoreCard.position` 欄位 §12 的 11.16、**自動發布改「複選內容（圖片/完整/簡短）＋挑圖＋預覽」流程，Telegram 支援發圖** §12 的 11.26、**卡片自動發布時擷取「資訊訊息連結」供班表名字超連結用** §12 的 11.27。
- **M5 店家：班表**：多行標題、出勤人員點選、出勤時段(手動 1830→18:30／自動換算)、
  發布格式、草稿(S6–S12)。**發布輸出與需求 S11 範例字字相符**。
  ↳ 後續精修（已套用）：**出勤時段沿用出勤人員的名字排序**(顯示與發布文字一致) §12 的 11.21、**移除 `ScheduleEntry.position`（不保留手動拖曳排序）** §12 的 11.22、**出勤時段預設改自動換算** §12 的 11.23、**換算紀錄保留（載入時依 `auto_start` 還原班次格）** §12 的 11.24、編輯班表頁頂部列凍結(sticky) §12 的 11.25、**自動發布改 HTML 送出、美容師名字超連結到資訊訊息** §12 的 11.27、**最上方新增日期欄位（小日曆），發布時置頂** §12 的 11.28、**下方新增結語欄位（發布置底）** §12 的 11.29、**標題／結語可儲存・選用・編輯文字模板** §12 的 11.30、**出勤時段 pill 一律依時間序排列（含跨午夜班次）** §12 的 11.31。
- **M6 社群 API 串接（通用骨架）**：發布目標設定(平台/權杖/目標 ID)、一鍵發布，
  內含 LINE Messaging API 與 Telegram 實作(urllib，免新套件)。權杖回應遮蔽(只露末四碼)。
  實測點發布**真的打到 LINE API**，假權杖回乾淨的 HTTP 401 → 整條管線通(P1)。
  ↳ 後續精修（已套用）：**平台改為 Telegram(預設)＋X，移除 LINE**（X 列為選項但自動發送未實作；LINE 殘留資料於啟動清除）§12 的 11.18、發布設定頁用語白話化＋欄位說明＋[?] 教學彈窗 §12 的 11.19、發布目標按鈕顯示「平台 名稱」＋點 pill 發送前二次確認 §12 的 11.20。
- **M7 手機版（響應式）**：各 view 加 `@media(max-width:640px)`；看板改原生橫向捲動、
  觸控停用自訂拖曳捲動；以 375px 視窗量測驗證無水平溢出(G1)。
- **M8 收尾與驗收**：全模組整合煙霧測試通過、重新打包 `AhhOuch_v0.6.0.exe`(27.5MB)成功、
  新增版本修訂紀錄（即下方 §5 附錄；原為獨立檔 `CHANGELOG.md`，後整合入本報告並移除該檔）。

### 5 附錄：版本修訂紀錄（依版次，整合自原 CHANGELOG.md）

> 本附錄以**版次**角度記錄各版本主要變更（§5 正文為里程碑角度、§12 為逐項精修角度，三者互補）。
> 版本號集中於 `app.toml`（唯一事實來源，連動前端標題與打包檔名）。
> 需求編號對照見 [`AhhOuch 開發計畫.md`](./AhhOuch%20開發計畫.md) §2（G 通用／C 客人／S 店家／X 其他／P 後期）。
> 格式參考 [Keep a Changelog](https://keepachangelog.com/)；最新版本在最上方。
>
> ⚠️ 此版次表記到 `0.6.0` ＋ M7/M8 批次；其後 **0.7.0–1.7.0** 為 §12 的逐項精修（依日期記錄），
> 版次由使用者以 `app.toml` 控管，細節改以 §12 與 `git log` 為準。

#### [0.6.0 後 — M7 手機版 ＋ M8 收尾]
**新增**
- **響應式手機版（M7 / G1）**：同一套前端以 RWD 自適應手機螢幕（`@media (max-width: 640px)`），
  手機瀏覽器開同一網址即切換手機版面；不另建獨立程式以利單點維護。
  - 標題列改為兩端對齊並可換行；內距在窄螢幕縮小。
  - 看板欄寬改為 78vw、改用瀏覽器原生橫向捲動；觸控時停用滑鼠拖曳捲動避免衝突。
  - 卡片評分列、發布設定表單在窄螢幕改為單欄／換行。
  - `frontend/mobile/` 保留作未來「與電腦截然不同流程」時的擴充點。

**收尾（M8）**
- 全模組整合煙霧測試（客人／店家／班表／發布）通過。
- 重新打包驗證：M0 流水線在含全部功能下仍能產出單一 exe（`打包輸出/AhhOuch_v0.6.0.exe`）並自動清過程檔。

#### [0.6.0]
**變更**
- 心得評分「同步模板」：可將既有心得更新為其所屬模板的最新項目，**同名項目評分保留**、
  新增項目留白、移除項目刪除（`/reviews/{id}/sync`）。
- 卡片詳情（`CardDetailView`）操作流程調整：簡介／心得／模板改為「草稿 + 儲存」模式並加未存變更提醒。

#### [0.5.0]
**新增**
- 看板排序「手動／預設」切換時保存與還原**手動排序快照**（`manual_position`）：切到預設（標題 Unicode）
  後再切回手動，可還原原本的手動順序（C10）。
- 看板排序模式切換端點（`/boards/{id}/sort-mode`）。

#### [0.4.0]
**變更**
- 介面優化：卡片詳情、看板、店家資訊卡片與列表視圖的版面與互動調整。
- 圖片燈箱（點圖放大檢視）。

#### [0.3.0] — 調整美容師卡片
**新增**
- 評分項目新增「有／無」型（`item_type` = `score` | `yesno`）：除 0~10 分外可記錄有無（C17/C19 延伸）。
- 評分模板項目可調整類型、排序、跨模板複製。

**變更**
- 心得與評分資料結構調整（`reviewscore.item_type` / `yesno_value`、`ratingtemplateitem.item_type`），
  既有資料庫由 `database._migrate()` 自動補欄位、不丟資料。
- 開發代理新增 `/images`（Vite dev 模式圖片可正常顯示）。

#### [0.2.0]
**新增（一次性大幅擴充，涵蓋 M1–M6 主體）**
- **客人**：養身館 CRUD（C1–C3）、看板增減／改名／拖曳排序與預設五看板（C4–C6）、
  美容師卡片（C7/C8/C11）、SortableJS 同／跨看板拖曳與插入符號（C9）、Unicode／手動排序（C10）。
- **客人卡片完整內容**：簡介（圖片上傳／剪貼簿貼上／封面／國籍／文字／收闔，C12–C15）、
  心得（圖像化日曆、評分 0~10＋補充文字、多組、新增帶入前次內容，C16/C19/C21/C22）、
  評分模板（多組／命名／項目增刪、預設七項，C17/C18/C20）。
- **店家**：美容師資訊卡片（名字自輸、多圖＋封面、完整／簡短介紹，S2–S4）、
  發布（產生排版圖片＋純文字、勾選完整／簡短，S5）。
- **店家班表**：標題多行（S6）、出勤人員點選（S7/S8）、出勤時段（手動 24 時制自動轉換 S9、
  自動換算每班 1.5h／含端點共 9 班 S10）、發布格式（S11）、草稿留存可再編輯（S12）。
- **社群發布骨架（P1）**：發布目標設定（平台／權杖／目標 ID）、一鍵發布文字，
  內含 LINE Messaging API 與 Telegram 實作（填入權杖即可用）。
- 服務層：圖片服務、班表換算、時間正規化、發布派送。

#### [0.1.0]
**新增（M0 專案骨架與打包流水線）**
- FastAPI（後端）＋ Vue 3 / Vite（前端）可啟動骨架，後端提供靜態前端與 REST API。
- 單點設定 `app.toml`（名稱／版次，連動打包檔名，X3）；`version.py` 唯一取值來源。
- 安裝與啟動：`requirements.txt` / `install.bat`（X4）、`run_dev.bat`、`README.md`（X5）。
- 打包：`build.py` 產生單一免安裝 exe 至 `打包輸出/` 並自動清過程檔（X1/X2）。
- 資料輸出統一於 `DATA/`（SQLite ＋ 上傳圖片，X6），啟動自動建立。
- 客人模組基礎模型與路由雛形。

## 6. 本次對話中拍板的決策

| 決策 | 結論 |
| --- | --- |
| 卡片排序模式放哪 | **Board 層級**（每看板一個切換，非每卡片） |
| 班表自動換算邊界(§9-5) | **含第 12 小時整點，每班 1.5h 共 9 班**，跨午夜回繞 |
| 發布圖片產生方式(PoC 6.2) | **方案 A：html2canvas（前端）** |
| M6 社群平台 | **先做通用骨架**，平台最終由使用者決定、需自備權杖 |
| M7 手機版做法 | **同一套響應式**（單點維護），非另建 mobile app |

> 使用者另自行追加的功能（細項見本報告 §12）：評分「有/無」型項目、模板上下排序/跨模板載入/
> 心得同步至最新模板、手動排序快照(切預設↔手動可還原)、預設排序改 Natural Sort
> (3<11<12)、跨看板拖曳不破壞排序、圖片燈箱、卡片配色與封面顯示調整、心得標題含館名+卡名。

## 7. 需求驗收對照

| 群組 | 狀態 |
| --- | --- |
| G1 電腦＋手機介面 | ✅ 響應式 |
| G2/G3 資料獨立・本機伺服器 | ✅（保留多使用者擴充） |
| C1–C22 客人全功能 | ⬛ 已拆分至獨立產品；本專案已移除（§12 的 11.36） |
| S1–S12 幹部資訊卡片＋班表 | ✅（發布格式與範例相符；原「店家」已更名為「幹部」） |
| X1–X6 打包/設定/環境/README/DATA | ✅ |
| P1 社群自動發布 | 🟡 **骨架完成**；真正推送待使用者申請平台帳號＋填權杖 |

## 8. 目前狀態

**架構轉型進行中（2026-06-25）**：已完成 M1（IndexedDB 資料層）＋ M2（PWA 化 + GitHub Pages），前端 App 已可完全離線運作、並部署至 `https://FatPigDash.github.io/AhhOuch_Manager/`。

- **技術架構**：已從「FastAPI + SQLite + exe」轉為「Vue 3 PWA + IndexedDB + GitHub Pages」。後端（FastAPI）仍存在於 repo，但前端已完全不依賴它。
- **git 歷程**：V0.6.0 → V1.0.0 → V1.5.0 → V2.0.0（系統拆分）→ M1（IndexedDB）→ M2（PWA + GitHub Pages）→ 修正 CI（package.json 漏 commit）。
- **部署**：GitHub Actions workflow（`.github/workflows/deploy.yml`）自動 build + deploy，push main 後 2-3 分鐘生效。Repo 已改為 public（GitHub Pages 免費方案需要）。
- **本機開發**：`cd frontend/desktop && npm run dev`（Vite HMR，存檔即更新，不需 `npm run build`）。
- **Telegram 自動發布**：已從前端移除（M1 清理）；M4 改用 Web Share API 接手發布功能。

## 9. 待辦（依開發計畫里程碑順序）

> 架構轉型後，待辦改為依 [`AhhOuch_Manager 幹部系統手機版開發計畫.md`](./AhhOuch_Manager%20幹部系統手機版開發計畫.md) M3–M6 排列。

1. **M3 圖片功能（手機版）**：從手機相簿選圖或拍照（`<input type="file">`）、剪貼簿貼上（Clipboard API）、多圖管理、封面設定、大圖縮圖最佳化；驗證 2000 張容量。
2. **M4 發布（Web Share API）**：格式化班表／卡片文字，呼叫 `navigator.share()` 傳至 LINE；使用者可選擇是否連同照片發出；驗證 iOS Safari / Android Chrome 相容性並規劃降級方案。
3. **M5 草稿管理**：班表發布後自動留存草稿；草稿列表；點選草稿進入同款編輯介面修改後再發布。
4. **M6 備份與收尾**：匯出全部資料（卡片＋圖片＋班表）為備份檔；匯入還原（換機流程）；每月提醒備份；語系相容性（繁中／日／英）整體覆測。

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
> ① 本報告（**§5 里程碑 ＋ §12 精修，需合併看**）— 人類可讀的現狀；
> ② `git log` 與本報告 **§5 附錄（版本修訂紀錄）** — 版本歷程；
> ③ **程式碼本身**（最終事實）。若文件與程式碼衝突，**以程式碼為準**，並回頭修正文件。

1. 先讀本報告 §4（慣例）、§8（狀態）、§9（待辦），即可接手。
2. 改後端資料模型欄位 → 記得同步更新 `database.py`：新增欄位登記 `_COLUMN_MIGRATIONS`、
   移除欄位登記 `_DROP_COLUMNS`。
3. 改版次／名稱 → 只動 `app.toml`。
4. 動到使用者需求行為前 → 對照 `AhhOuch 需求.md` 與計畫 §2 需求對照表，並把修訂歷程補在
   **本報告 §12**（逐項）或 **§5 附錄**（依版次）（開發計畫維持為開發前文件，不再追加歷程）。
5. 要做 UI 變更 → 可用 `run_dev.bat`(方式 A) 或方式 B 在瀏覽器確認；手機版用瀏覽器
   響應式檢視（≤640px）測試。
6. 最可能的下一步：§9 的「資料備份/匯出匯入」或「社群發布平台實際串接」。

---

## 12. 開發中修訂歷程

> 此區為開發過程中的逐項調整紀錄（原記於開發計畫 §11，現移至本報告）。
> 保留原 `11.x` 子編號以維持各條目彼此的交叉引用。
>
> **這些調整皆已實作並套用至現行程式（＝目前實際行為），非待辦。** 與里程碑的對應：
> - 11.6 / 11.9 / 11.10 / 11.32 → M1（看板卡片顯示）
> - 11.1 / 11.11 / 11.12 / 11.34 → M2（排序與拖曳）
> - 11.2 / 11.3 / 11.4 / 11.7 / 11.13 / 11.33 → M3（卡片完整內容）
> - 11.34 / 11.35 → M1（養身館列表排序、多幹部與聯絡資訊，C2/C3）
> - 11.5 / 11.7 / 11.14 / 11.15 / 11.16 / 11.37 → M4（店家／幹部資訊卡片；11.37＝美容師資訊編輯頁 UX 精修）
> - 11.21 / 11.22 / 11.23 / 11.24 / 11.25 / 11.28 / 11.29 / 11.30 / 11.31 → M5（班表）
> - 11.18 / 11.19 / 11.20 → M6（社群發布）
> - 11.26 / 11.27 → M4＋M6（卡片自動發布內容選擇、名字超連結；亦影響 M5 班表發布）
> - 11.8 / 11.17 → 開發環境（Vite 代理、README、預覽設定）
> - 11.36 → 架構拆分（移除客人系統、店家→幹部更名；影響全專案後端／前端／資料庫）
> - 11.38 → M1 架構轉型（FastAPI → IndexedDB，Local-First）
> - 11.39 → M2 PWA 化 + GitHub Pages 自動部署
> - 11.46 / 11.47 → M4（美容師卡片資訊連結欄位：加「發布設定名稱」標籤、覆蓋模式、發布後連結回填）
> - 11.48 → M4（批次發布美容師卡片，含選卡片、選圖片模式、選目標、優先覆蓋模式、連結回填）
> - 11.49 → M4＋M6（發布時若原 Telegram 訊息被手動刪除，自動改發全新訊息）
> - 11.50 → M5（班表：出勤人員排序改依資訊卡片順序、新增人員預設自動換算、發布時名字加 info_link 超連結）
> - 11.51 → M5（班表新增 Telegram 訊息連結欄位與覆蓋發布模式）
> - 11.52 → M6（備份 UI 簡化：移除分享按鈕、改單一下載鈕並附雲端上傳說明）
> - 11.53 → 軟體教學頁（GuideView 全面重寫：補全準確說明、改為 CSS 模擬圖、刪除假 AI 圖片、修正備份副檔名）
> - 11.54 → M4（美容師卡片：上傳第一張圖片時自動設為封面，後續以 ★ 按鈕手動切換）
> - 11.55 → 軟體教學頁（GuideView 新增「回到主頁」按鈕，以 tab 橫列方式排於頁籤左側）
> - 11.56 → M4（資訊卡片列表：卡片／列表切換按鈕外觀改為 tab 底線風格，與教學頁一致）
> - 11.57 → M6（發布設定教學彈窗：指令與網址新增快速複製按鈕）
>
> 讀法：先看 §5 里程碑的「↳」指引找到對應條目，即可掌握該功能的**最新實際行為**。

### 2026-06-20 — 客人模式 UX 調整（M1–M3 範圍精修）

本批調整集中於**客人端卡片詳情頁與看板排序**的使用體驗，皆對應既有需求 C10／C17／C19，未變更整體里程碑規劃。

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

- 美容師資訊卡片列表頁（`StoreCardListView.vue`）的封面高度從 `130px` 改為 `260px`，讓封面圖呈現更多畫面。

#### 11.6 看板卡片封面高度與顯示方式調整（客人 SpaBoardView）

- 封面由固定高度改為**隨圖片原始比例自動撐高**（`height: auto`），避免圖片被裁切。
- 設定 `min-height: 90px`，確保無封面圖的卡片仍有最低高度可顯示標題。
- 封面圖加上 `max-height: calc(100vh - 280px)` 上限，防止單張圖片撐滿整個看板欄位而擠掉標題。
- **標題列改至封面圖下方獨立區塊**（白底深色字），不再疊在圖片上。
- ⚠ **已知問題（→ 已於 §11.9 解決）**：調整後標題列實際顯示仍不穩定——圖片較高時標題會被擠出 card-list 可見範圍之外，需捲動才能看到。根本原因是 card-list 的可見高度受 board `max-height` 限制，而 `card-body` 沒有固定位置，容易被推出畫面。**最終解法見 §11.9：將標題列移至封面圖上方，圖片往下撐不影響標題可見性。**

### 2026-06-20 — 看板卡片標題顯示修正（§11.6 已知問題的後續處理）

#### 11.9 看板卡片標題移至封面圖上方（客人 SpaBoardView）

**問題背景**：§11.6 記錄的已知問題——圖片較高時，圖片下方的標題列會被推出 card-list 可見範圍，實際上看不到。

**嘗試方案（均失敗）**：
1. `card-body` 加灰底與 `border-top` 強調視覺獨立性 → 標題仍因圖片太高而消失於捲動範圍外。
2. 封面圖改為 `height: 220px; object-fit: cover; object-position: top` 固定高度 → 破壞了 §11.6 特意保留的「不裁切」設計。
3. 封面圖改為 `width: 100%; height: auto`（移除 `max-height`）純等比縮放 → 同問題：標題在圖片下方，高圖仍把標題推出可見區。

**最終方案（已採用）**：將 `card-body`（標題＋刪除鈕）**搬至 `<template>` 的封面圖上方**，結構調整為：
```
<li class="card">
  <div class="card-body">標題 ✕</div>   ← 永遠在最頂端
  <div class="cover">封面圖</div>        ← 圖片往下撐，不影響標題
</li>
```
- 封面圖維持 `width: 100%; height: auto` 等比縮放，不裁切。
- `card-body` 位於最上方，恆可見，分隔線改為 `border-bottom`。
- 解決了標題被圖片推出可見區的根本問題。

#### 11.7 美容師簡介頁圖片燈箱（客人 CardDetailView）

- 點擊美容師簡介頁的圖片可彈出燈箱大圖視窗（`CardDetailView.vue`）。
- 點擊圖片以外的暗色區域，或點右上角 **✕** 按鈕，可關閉燈箱。
- 同樣修改也套用至店家美容師資訊卡片頁（`StoreCardDetailView.vue`）。

### 2026-06-20 — 看板卡片視覺對比強化（客人 SpaBoardView）

#### 11.10 卡片底色與看板底色改為高對比色系

**問題**：卡片各區塊（`.card-body` `#f0f4f8`、`.cover` `#f0f4f8`）與看板背景（`#e9eef3`）同屬冷藍灰色系，視覺邊界不明顯。

**修改內容**（`SpaBoardView.vue`）：

- 卡片底色（`.card`）：`#fffbf0`（暖米白）
- 卡片標題區（`.card-body`）：`#fffbf0`，底線改為 `#e8c97a`
- 封面佔位符區（`.cover`）：`#fdf3dc`（淺暖黃）
- 卡片邊框：`2px solid #d4a84b`（暖金色粗邊框），取代原先細邊框
- 卡片陰影：移除（`box-shadow: none`），改由粗邊框提供邊界感

**效果**：看板冷藍灰（`#e9eef3`）vs 卡片暖米白/金（`#fffbf0`、`#d4a84b`），冷暖對比鮮明，卡片輪廓一目了然。

### 2026-06-20 — 看板排序 Bug 修正（`backend/routers/customer.py`）

#### 11.11 預設排序改為 Natural Sort（C10）

**問題**：預設（標題）排序使用 Python 字串比較（lexicographic），導致含多位數字的標題排序反直覺——例如 `"3"`、`"11"`、`"12"` 被排成 `11、12、3`（首字元 `"1" < "3"`），而非預期的 `3、11、12`。

**修改內容**（`backend/routers/customer.py`）：
- 新增 `_natural_key(s)` 函式：以 `re.split(r"(\d+)", s)` 拆分字串，數字段轉為 `int` 再比較，其餘段依碼點排序。
- 將 `get_spa` 中的 `sorted(cards, key=lambda c: c.title)` 改為 `sorted(cards, key=lambda c: _natural_key(c.title))`。
- `set_sort_mode("unicode")` 的重排邏輯同步改用 `_natural_key`，確保切換排序時的位置編號與顯示一致。

**效果**：`3 < 11 < 12`（數值順序）；中英文混合標題的非數字段仍依碼點排序，行為一致。

#### 11.12 跨看板拖曳不破壞排序（C9/C10）

**問題**：卡片跨看板拖曳後，目標看板的排序可能被破壞，原因有二：
1. `move_card` 把目標看板的卡片依 `position` 欄位排序後插入，但前端傳來的 drop index 是依**標題**顯示順序計算的（unicode 模式），兩者順序不一致，導致位置計算錯誤。
2. `move_card` 只更新 `position`，不更新 `manual_position`，導致之後切換到手動模式時，移入的卡片快照位置為舊板資料而非現況。

**修改內容**（`backend/routers/customer.py`，`move_card`）：
- 目標看板為 **unicode 模式**：忽略 drop index，直接將卡片加入後整體依 natural sort 重排，保證排序永遠正確。
- 目標看板為 **手動模式**：維持原本依 drop index 插入的邏輯。
- 不論哪種模式，每張卡片在重排後同步設定 `manual_position = position`，確保日後切換排序模式時快照正確。

#### 11.8 其他
- 前端開發伺服器（5173）`vite.config.js` 代理新增 `/images`，修正分離模式下圖片無法顯示。
- `README.md` 補充方式 A 的明確路徑說明（前端改碼需重新 `npm run build`、PowerShell 以 `.\run_dev.bat` 啟動）。

### 2026-06-20 — 心得區塊標題加入養身館名稱與卡片標題

#### 11.13 心得標題改為「養身館名稱 卡片標題 心得」（客人 CardDetailView）

**需求**：卡片詳情頁心得區塊的 `<h2>` 原本固定顯示「心得」，改為同時顯示所屬養身館名稱與卡片標題，格式為 `養身館名稱 卡片標題 心得`（例：「舒活養身館 #5 心得」）。

**修改內容**：

- `backend/routers/customer.py`，`get_card`：取得所屬看板後，再多查一次 `Spa`，在回傳 dict 中新增 `spa_name` 欄位。
- `frontend/desktop/src/views/CardDetailView.vue`，心得 panel 的 `<h2>`：原本 `'心得'` 改為 `` `${card.spa_name ?? ''} ${card.title ?? ''} 心得`.trim() ``；評分模板編輯模式下仍顯示「評分模板編輯」，不受影響。

### 2026-06-21 — 店家模式 UX 與資料模型調整（M4 範圍精修）

本批調整集中於**店家端美容師資訊卡片**的排序、詳情頁編輯體驗與相關資料模型清理，未變更整體里程碑規劃。

#### 11.14 美容師資訊卡片預設排序改為「數字自然＋其餘 Unicode」，不提供手動排序（店家 StoreCardListView）

**需求**：資訊卡片頁面所有美容師卡片一律**預設排序、不提供手動排序**；名字會有純數字、`#`純數字、中文、英文、日文等型態。

**規則**：
- 純數字 / `#`純數字 → **數值（自然）排序**（`#5 < #21 < #61 < #199`），全形數字（如 `１２`）亦當數值。
- 中文 / 英文 / 日文 → **標準 Unicode（碼點）排序**。

**修改內容**（`backend/routers/store.py`，`list_cards`）：
- 原 `order_by(StoreCard.position)`（建立順序）改為以 Python `_name_sort_key(name)` 排序。
- `_name_sort_key`：以 `re.split(r"(\d+)", name)` 拆成數字段／非數字段交錯；數字段轉 `int` 比數值、非數字段比碼點，元素統一為 `(型別旗標, 數值, 字串)` 避免 `int`／`str` 直接比較出錯。
- 以 Python 排序而非 SQL `order_by`，確保結果不受 SQLite collation 影響。
- 前端 `StoreCardListView.vue` 本就無手動排序 UI，故「不提供手動排序」無需改動介面。
- 與客人端 §11.11 的 Natural Sort 同源，店家端額外把 `#` 前綴數字也納入數值排序。

#### 11.15 店家資訊卡片詳情頁改「草稿＋儲存／取消」並調整按鈕版面（店家 StoreCardDetailView）

**版面**：
- 「📤 發布」由右上角移至**左下角**。
- 右下角新增 **[取消]** 與 **[💾 儲存]**，旁顯示狀態（`● 尚未儲存` ／ `✓ 已儲存`）。

**編輯模式**：
- 名字／完整介紹／簡短介紹由原「失焦即自動存（`@blur`）」改為**本地草稿＋按 [儲存] 才寫回後端**；「儲存」在無變更時禁用、名字空白會擋下並提示。
- **未儲存就離開的確認**：返回列表／取消／路由切換由 `onBeforeRouteLeave` 跳確認；瀏覽器關閉／重新整理由 `beforeunload` 跳原生確認。
- 圖片維持即時存檔，並改用只刷新圖片欄位的 `reloadImages()`，避免重載覆蓋尚未儲存的文字編輯。
- 按「發布」時若有未儲存變更，先提示並儲存再發布（發布內容取自後端已存資料）。
- 與客人端 §11.4 的「草稿＋儲存」模式一致化。

#### 11.16 移除 `StoreCard.position` 欄位（資料模型清理）

- 因 §11.14 改為依名字計算排序，`StoreCard.position` 已不再使用 → 從 `backend/models/store.py` 移除，`create_card` 不再寫入。
- `StoreCardImage.position`（圖片排序）保留。
- **遷移**：`backend/database.py` 新增 `_DROP_COLUMNS`，啟動時對既有 DB 執行 `ALTER TABLE storecard DROP COLUMN position`（SQLite 3.35+ 支援）。此步**必要**——否則舊 DB 殘留的 NOT NULL `position` 欄位會讓新版不帶該欄位的 INSERT 失敗。

#### 11.17 移除壞掉的 launch.json 預覽設定

- `.claude/launch.json` 移除指向不存在的 `preview_server.py` 之 `ahhouch-preview`（8030）設定；新增可用的 `ahhouch-frontend`（Vite dev、5173，`/api`・`/images` 代理到 8000 後端）以供前端預覽。

### 2026-06-21 — 社群發布平台調整（M6 範圍精修）

本批調整集中於**社群發布的平台選項、發布設定頁的易用性與發布動作的防呆**，未變更整體里程碑規劃。

#### 11.18 發布平台改為「Telegram(預設)＋X」，移除 LINE（店家 PublishSettingsView／publish_service）

**需求演進**：平台先擴充為 Telegram、X、LINE 三者並以 **Telegram 為預設**；隨後決定**移除 LINE**，最終為 **Telegram(預設)＋X 兩個**。

**規則**：
- **平台順序＝下拉選單順序，第一個為預設**（Telegram）。
- **Telegram** 為實際實作（`urllib` 打 `sendMessage`），填金鑰＋群組 ID 即可推送。
- **X** 僅列為**可選平台**，**自動發送尚未實作**——選 X 按自動發送會回固定訊息「X 自動發送尚未支援，請手動複製文字貼到 X」（發文需 OAuth 授權，不同於 Telegram 的 bot token 模式）。

**修改內容**：
- `backend/services/publish_service.py`：`SUPPORTED_PLATFORMS` 由 `("line","telegram")` 經 `("telegram","x","line")` 最終為 `("telegram","x")`；`send_text` 移除 LINE 分支、新增 X 分支（回未支援訊息）。
- `backend/models/publish.py`：`PublishTarget.platform` 預設值由 `""` 改為 `"telegram"`。
- `backend/routers/publish.py`：`TargetCreate.platform` 預設值改為 `"telegram"`。
- `frontend/desktop/src/views/PublishSettingsView.vue`：表單預設平台 `telegram`；`PLATFORM_LABEL` 為 `{ telegram:'Telegram', x:'X' }`（去除 line）。
- **遺留資料清除**：`backend/database.py` 新增 `_cleanup_legacy_data()`，於 `init_db()` 的 `_migrate()` 後執行 `DELETE FROM publishtarget WHERE platform='line'`（表不存在則跳過），任何既有 DB 下次啟動即自動清掉殘留的 LINE 目標，使用者不會看到。

#### 11.19 發布設定頁用語白話化＋欄位說明＋[?] 教學彈窗（店家 PublishSettingsView）

**問題**：原欄位名「權杖 (token)」「目標 ID」對初次使用者太專業、看不懂。

**修改內容**（`PublishSettingsView.vue`）：
- 欄位改用白話標題並在下方加一行灰色說明：名稱→「自己看的備註」、平台→「發送到哪個平台」、權杖→**「機器人金鑰」**、目標 ID→**「要發到哪個群組」**（技術名詞如 `chat_id`、`@BotFather` 保留在說明括號裡，方便對照官方文件）。
- 群組編號 placeholder 改成實例 `例如：-1001234567890`；列表顯示由「權杖／目標」改為「金鑰／群組」。
- 「機器人金鑰」與「要發到哪個群組」標題後各加一顆藍色圓形 **[?]** 按鈕（`type="button"` 防誤送出），點擊彈出教學視窗：
  - **金鑰教學**：@BotFather → `/newbot` → 命名 → 取 `bot` 結尾使用者名稱 → 複製 HTTP API token；提醒金鑰勿外流、可 `/revoke` 重產。
  - **群組編號教學**：建立 bot → 加進群組 → 發訊息 → 開 `getUpdates` 網址 → 找 `"chat":{"id":-100…}`；提醒群組編號常為負數、沒資料就重發訊息再重整。
- 兩個彈窗皆 `@click.self` **點視窗外（背景遮罩）自動關閉**，另有右上 ✕。此頁原無 modal，連同 `.help-btn` 一起新增整組樣式。
- ⚠ 目前 [?] 與長說明僅在「新增發布目標」表單；編輯既有目標的對應欄位尚未加。

#### 11.20 發布目標按鈕顯示「平台 名稱」＋發送前二次確認（店家 StoreCardDetailView／ScheduleEditView）

- **顯示平台**：卡片／班表發布視窗的「自動發布到」pill 由 `📤 {{ t.name }}` 改為 `📤 {{ platformLabel(t.platform) }} {{ t.name }}`（例：`📤 Telegram 111`）。兩個 view 各加 `platformLabel()`（`telegram→Telegram`、`x→X`）。
- **二次確認**：`sendToTarget` 開頭加 `confirm("確定要發布到「Telegram 111」嗎？")`，按取消即不送出，避免誤觸 pill 直接發出去。

### 2026-06-21 — 班表 UX 與資料模型調整（M5 範圍精修）

本批調整集中於**班表編輯頁的排序一致性、預設模式、換算紀錄保留與頂部列凍結**，未變更整體里程碑規劃。

#### 11.21 出勤時段沿用出勤人員的名字排序（店家 ScheduleEditView／store.py）

**需求**：出勤人員已依名字排序（同 §11.14 的 `_name_sort_key`）；將同一套邏輯套用到下方「出勤時段」，讓兩區順序一致（如 `#21 → #61 → #133 → #199`）。

**修改內容**（`backend/routers/store.py`）：
- `_serialize_schedule`：序列化後的 entries 依 `_name_sort_key(e["name"])` 排序再回傳（編輯畫面照名字排）。
- `schedule_publish_text`：發布文字也用同排序，**發布順序與畫面一致**（不再是加入順序）。
- 重用 store.py 既有的 `_name_sort_key`，不另寫一份，避免規則分歧。

#### 11.22 移除 `ScheduleEntry.position` 欄位（不保留手動拖曳排序）

- 因 §11.21 改為依名字排序，且此處**不保留手動拖曳排序**功能，`ScheduleEntry.position` 已無用 → 從 `backend/models/schedule.py` 移除，`add_entry` 不再寫入。
- `_serialize_schedule`／`schedule_publish_text` 的 `.order_by(ScheduleEntry.position)` 改為 `.order_by(ScheduleEntry.id)`（只作穩定基準，最終仍以名字排序為準）。
- **遷移**：`backend/database.py` 的 `_DROP_COLUMNS` 新增 `"scheduleentry": ["position"]`，既有 DB 啟動時執行 `ALTER TABLE scheduleentry DROP COLUMN position`。
- `_next_position` 函式保留（`StoreCardImage` 圖片排序仍在用）。

#### 11.23 出勤時段預設改為「自動換算」（店家 schedule 模型）

- `backend/models/schedule.py`：`ScheduleEntry.time_mode` 預設值由 `"manual"` 改為 `"auto"`，新加入的出勤人員進編輯畫面即為「✓ 自動換算」。
- 僅影響**之後新加入**的人員；既有人員保留原模式（預設值只作用於新資料）。

#### 11.24 換算班次紀錄保留（店家 ScheduleEditView）

**需求**：輸入上班時間換算班次後保留紀錄，下次編輯能直接從紀錄勾選，不必再按一次「換算班次」。

**作法**：班次格是由上班時間（`auto_start`，本就持久化於 DB）決定的固定計算，故**不另存班次清單**，而在載入時重算還原。
- `frontend/desktop/src/views/ScheduleEditView.vue`：`load()` 後呼叫新增的 `restoreShiftGrids()`——逐一檢查每位人員，若有 `auto_start` 就呼叫 `shiftSlots` 還原班次格（`computedShifts`）並回填輸入框。每次重載（含切換出勤人員後）皆自動還原，已勾選時段維持勾選。

#### 11.25 編輯班表頁頂部列凍結（店家 ScheduleEditView）

- `ScheduleEditView.vue` 的 `.page-head`（返回／標題／發布）改 `position: sticky; top:0; z-index:10`，捲動時固定在畫面頂端。
- 背景設頁面底色 `#f5f7fa`、以 `margin-top:-24px` 補滿 `app-main` 上方留白避免內容透出，並加淡陰影呈現浮起層次；手機版另調負邊距／內距。
- ⚠ 店家資訊卡片詳情頁（`StoreCardDetailView.vue`）有相同的 `.page-head`＋底部發布列，目前未凍結。

### 2026-06-21 — 自動發布內容選擇、班表名字超連結與班表日期（M4／M5／M6 範圍精修）

本批調整集中於**店家自動發布的內容選擇、把美容師名字做成連到資訊訊息的超連結，以及班表日期欄位**。涉及前後端與資料模型，未變更整體里程碑規劃。

> ⚠ 三項皆**改動了資料庫結構或後端碼**（§11.27 加 `StoreCard.info_link`、§11.28 加 `Schedule.date`、新增端點），依 §4-7 慣例，**後端需手動重啟**才會套用 migration 與新端點。

#### 11.26 美容師卡片自動發布改為「複選內容＋挑圖＋預覽」流程（店家 StoreCardDetailView／store.py／publish_service／image_service）

**需求**：美容師資訊卡片使用自動發布時，彈出視窗讓使用者**複選**要發布哪些資訊（`圖片`／`完整介紹`／`簡短介紹`），選擇後出現**預覽**讓使用者確認。
**使用者定案**：①「圖片」由使用者**自行挑選**要發哪幾張；②圖片**帶文字說明**（caption）一起送。

**前端行為**（`StoreCardDetailView.vue`）：
- 點「自動發布到：」pill **不再直接送出**（取代 §11.20 的二次確認直送），改開「選擇要發布的資訊」視窗。
- 複選 checkbox：`圖片`／`完整介紹`／`簡短介紹`（可任意組合）。預設：有圖就勾圖並預選**封面**、勾完整介紹。
- 勾「圖片」後出現**圖片挑選格**，可點選要發哪幾張（複選、可多選）。
- **即時預覽**：顯示選到的圖片縮圖 ＋ 組合文字（名字 ＋ 勾選的介紹）。
- `canAutoSend`：至少有一張選到的圖、或一個有內容的介紹，才可按「✓ 確認發布」。

**後端**：
- `routers/store.py` 新增 `POST /api/store/cards/{id}/publish`（body：`target_id`／`image_ids`／`text`）；只接受**屬於該卡片**的圖片、依卡片內順序發送，回 `{ok, message, link}`。
- `services/publish_service.py` 新增 `send_card`：Telegram 圖片發送——**單張用 `sendPhoto`、多張用 `sendMediaGroup`（相簿，2–10 張）**；文字當圖片說明文字（caption），**超過 1024 字自動拆成「圖片 ＋ 純文字」兩則**。multipart 以 `urllib` 手刻（免新套件）。
- `services/image_service.py` 新增 `read_image_bytes`／`image_path`（讀圖片原始位元組供上傳）。

#### 11.27 班表發布：美容師名字超連結到先前發布的資訊訊息（store.py／publish_service／StoreCardDetailView／ScheduleEditView）

**需求**：每位美容師都會先把資訊發布到 Telegram 群組；之後發布班表時，希望**美容師名字做成超連結**，點了直接跳到先前那則資訊訊息。
**使用者定案**：美容師卡片**新增網址欄位**；卡片自動發布時**自動擷取該則訊息的連結**寫入欄位，多次發布以**最新覆蓋**；班表發布時**自動抓取**該連結。

**資料**：`StoreCard` 新增 `info_link`（`database.py` 的 `_COLUMN_MIGRATIONS` 補欄）。

**後端**：
- 卡片自動發布成功後，`publish_service.telegram_message_link` 由 Telegram 回應算出訊息連結並覆寫 `card.info_link`：
  - 有 `username`（公開群組／頻道）→ `https://t.me/<username>/<msg_id>`。
  - 超級群組／頻道（`-100…`）→ `https://t.me/c/<去掉-100>/<msg_id>`。
  - 基本群組／私訊 → `None`（無訊息連結）。
- `send_card` 改回傳 `(ok, message, link)` 三元組；`send_text` 新增 `parse_mode` 參數。
- 班表新增 `POST /api/store/schedules/{id}/publish`（`target_id`）：以 `_schedule_html` 用 `parse_mode=HTML` 送出，名字若有 `info_link` 包成 `<a href>`、其餘文字一律 `html.escape`（純文字版 `publish-text` 維持不變，供複製/下載圖片）。

**前端**：
- `StoreCardDetailView.vue` 新增可編輯的「資訊訊息連結」欄（自動填入＋可手動貼上 Telegram「複製訊息連結」；納入 dirty／save／snapshot），「確認發布」後用回應的 `link` 同步畫面。
- `ScheduleEditView.vue` 發布 pill 改走 `publishSchedule`，並加說明 hint。

**限制（重要）**：超連結**只在「自動發布」訊息有效**（下載圖片／複製純文字皆無連結）；群組須為**超級群組/公開群組**（基本群組無訊息連結，`link=None` 時名字維持純文字、不做超連結）。

#### 11.28 班表新增日期欄位，發布時置於最上方（schedule 模型／store.py／ScheduleEditView）

**需求**：編輯班表**最上方**新增日期欄位，格式如 `2026/06/21 (日)`，可用**小日曆**點選哪一天；發布時把日期資訊放在**最上方**。

**資料**：`Schedule` 新增 `date`（ISO `YYYY-MM-DD`，`_COLUMN_MIGRATIONS` 補欄）。

**後端**（`routers/store.py`）：
- 新增 `_format_date`：ISO → `2026/06/21 (日)`；星期幾由 `datetime.weekday()`（週一=0）對應 `"一二三四五六日"`；空字串或無法解析則回原值。
- `publish-text`（純文字）與 `_schedule_html`（HTML）皆把日期當**第一個 block 置頂**（標題之上）。
- `ScheduleUpdate` 收 `date`；序列化用 `model_dump` 自動帶出。

**前端**（`ScheduleEditView.vue`）：
- 最上方新增「日期」panel：原生 `<input type="date">` 提供**小日曆**挑選，旁邊即時顯示 `formatDate`（JS `getDay()` 0=週日，對 `['日','一',…]`）。
- `@change` 以 `updateSchedule({ date })` 即時存回後端。

### 2026-06-21 — 班表結語欄位與標題/結語文字模板（M5 範圍精修）

本批調整集中於**班表編輯頁新增「結語」欄位，以及標題／結語可儲存、選用、編輯文字模板**。涉及前後端與資料模型（新增 `Schedule.footer` 欄位、`TextTemplate` 表），未變更整體里程碑規劃。

> ⚠ 兩項皆**改動了資料庫結構**（§11.29 加 `Schedule.footer`、§11.30 新增 `texttemplate` 表）與後端碼（新增端點），依 §4-7 慣例，**後端需手動重啟**才會套用 migration 與新端點。

#### 11.29 班表新增「結語」欄位，發布時置於最下方（schedule 模型／store.py／ScheduleEditView）

**需求**：編輯班表在「出勤時段」**下方**新增「結語」欄位，與「標題」相同的多行文字輸入框；發布時把結語放在**最下方**。

**資料**：`Schedule` 新增 `footer`（多行字串，`_COLUMN_MIGRATIONS` 補欄 `schedule.footer`）。

**後端**（`routers/store.py`）：
- `ScheduleUpdate` 收 `footer`；`update_schedule` 寫入；序列化用 `model_dump` 自動帶出。
- `publish-text`（純文字）與 `_schedule_html`（HTML）皆在所有出勤人員區塊之後，把結語當**最後一個 block** 附上（HTML 版 `html.escape`）；空白結語不輸出。

**前端**（`ScheduleEditView.vue`）：
- 「出勤時段」panel 下方新增「結語（可多行）」panel：`<textarea rows="3">`＋`@blur` 以 `updateSchedule({ footer })` 存回（與標題 §11 同款）。

#### 11.30 標題與結語可儲存／選用／編輯文字模板（新增 TextTemplate 模型／store.py／TextTemplateBar／api.js／ScheduleEditView）

**需求**：標題與結語讓使用者可以**儲存、選用、編輯模板**。
**使用者定案**：①標題與結語**各自獨立**的模板池（套用標題模板不影響結語）；②操作介面放在**欄位旁的下拉選單＋按鈕**（非獨立管理頁）。

**資料**：新增 `TextTemplate` 模型（`backend/models/text_template.py`，於 `models/__init__.py` 註冊）：`kind`（`title`｜`footer`，分池）、`name`、`content`、`position`。**新表由 `create_all` 自動建立，毋須登記 `_COLUMN_MIGRATIONS`。**

**後端**（`routers/store.py`，新增 4 端點）：
- `GET /api/store/text-templates?kind=` 依 kind 列出（依 `position`、`id` 排序）。
- `POST /api/store/text-templates`（`kind`／`name`／`content`）建立，`position` 接同類別最後。
- `PATCH /api/store/text-templates/{id}`（`name`／`content`）更新。
- `DELETE /api/store/text-templates/{id}` 刪除。
- 驗證：未知 `kind` 或名稱空白回 `422`、查無回 `404`。

**前端**：
- 新增可重用元件 `components/TextTemplateBar.vue`（props：`kind`／`current-text`，emit：`apply`）：下拉「套用模板」、`💾 另存為模板`（`prompt` 取名、以目前欄位內容建模板）、`⚙ 管理` 彈窗（每列可改名／改內容失焦存檔、「以目前內容覆蓋」、刪除）。**套用後下拉以 `nextTick` 重置回「套用模板…」**——同一次 `change` 內同步重置 `<select>` 的 v-model 不會反映到 DOM，須延後一個 tick。
- `api.js` 新增 `listTextTemplates`／`createTextTemplate`／`updateTextTemplate`／`deleteTextTemplate`。
- `ScheduleEditView.vue`：標題與結語 panel 各放一條 `<TextTemplateBar :kind>`，`@apply` 以模板內容**覆蓋**欄位並立即存檔（`applyTitleTemplate`／`applyFooterTemplate`）。

### 2026-06-21 — 出勤時段時間序排列（M5 範圍精修）

本批調整集中於**班表「出勤時段」的時間 pill 一律依時間序顯示**，為**純前端邏輯**（無資料庫／後端／端點變更）。

#### 11.31 出勤時段 pill 一律依時間序排列，並正確處理跨午夜班次（店家 ScheduleEditView）

**需求**：出勤時段的時間 pill 要照**時間序**顯示，而非使用者點選／輸入的順序；**規則只看 pill 的時間本身，不分手動輸入或自動換算模式**，且需正確處理**跨午夜班次**。

**作法**（`frontend/desktop/src/views/ScheduleEditView.vue`，`sortedSlots`）：
- **最大空檔旋轉法**：把各時段視為 24 小時圓環上的點，依時鐘分鐘排序後，找出最大的相鄰空檔（含跨午夜回繞 +24h）；班次即從該空檔**之後**的時段開始連續排列。一段班次＝圓環上一段連續時間，最大空檔＝下班空窗。
  - 例：`{19:30, 22:30, 01:30, 20:00}` 最大空檔在 `01:30→19:30`（18h）→ 排成 `19:30、20:00、22:30、01:30`（傍晚連到凌晨）。
  - 純白天班（無跨午夜，如 `12:00,07:00,15:00,09:30`）→ 單純升冪 `07:00,09:30,12:00,15:00`，不會誤旋轉。
- **集中於 `saveSlots`**：所有時段異動（手動新增 `addManualSlot`、勾選 `toggleShift`、刪除 `removeSlot`）都經 `saveSlots` 統一排序後存回；後端會把手動輸入正規化（如 `1830→18:30`），正規化後時間序若改變則**再排一次並補存**（自動勾選的值已正規化，一次到位）。
- `load()` 載入時也先排一次，讓既有資料即依時間序顯示（僅前端排序，下次異動才寫回 DB）。
- **演進**：本功能歷經數版調整——先只處理自動換算模式（依換算清單 `computedShifts` 順序）、再擴及手動輸入（依時鐘時間），最後改為**與模式無關的最大空檔規則**（即現行行為），以正確涵蓋手動輸入的跨午夜班次。早期版本已隨 `V1.5.0` 提交，最終版本見現行 working tree（§8）。

**邊界**：規則假設「一段班次是連續時間、中間有明顯的下班空窗」；若時段近乎平均分布到繞滿整圈（無明顯空檔），起點以最大空檔為準——對正常班表為合理結果。

**驗證**（dev server 實機）：截圖回報的 `19:30,22:30,01:30,20:00` → `19:30,20:00,22:30,01:30`；於其上互動加入 `21:00`、`00:00` → `19:30,20:00,21:00,22:30,00:00,01:30`（正確插入並存回後端）；純白天 `12:00,07:00,15:00,09:30` → `07:00,09:30,12:00,15:00`（不誤旋轉）。

### 2026-06-23 — 客人模式看板/簡介 UX 與養身館資料模型調整（M1–M3 範圍精修）

本批集中於**客人端的看板捲動、簡介/心得輸入體驗，以及養身館列表的排序與幹部資料模型**。其中 11.34／11.35 **變更資料庫結構**（新增 `Spa.position`、新增 `spastaff` 表、移除 `Spa.staff` 欄位），首次啟動會由 `database.py` 的 `_migrate()` 自動完成遷移（既有資料保留），**改碼後需重啟後端**才會套用。

#### 11.32 看板畫面新增垂直捲軸，卡片以原始高度顯示（客人 SpaBoardView）

**需求**：原本整個看板被限制在單一螢幕高度內（`.board` 設 `max-height: calc(100vh - 200px)`、`.card-list` 內部 `overflow-y:auto`），導致每張卡片被壓縮。改為整頁可垂直捲動、卡片以原始高度呈現。

**作法**（`frontend/desktop/src/views/SpaBoardView.vue`，純 CSS）：
- 移除 `.board` 的 `max-height`，讓看板欄依內容自然撐高。
- 移除 `.card-list` 的 `overflow-y:auto`，取消欄內捲軸。
- 整頁改由瀏覽器垂直捲軸捲動；水平捲動（看板之間）與按住空白處左右拖曳捲動維持不變。手機版（≤640px）原即 `max-height:none`，不受影響。

**驗證**（dev server 實機）：`.board` 計算後 `max-height:none`、`.card-list` `overflow-y:visible` 不再內部捲動、整頁 `scrollHeight > 視窗高`，卡片封面圖完整顯示無壓縮；無 console 錯誤。

#### 11.33 美容師簡介與心得文字框隨內容自動長高，不出現垂直捲軸（客人 CardDetailView）

**需求**：「美容師簡介」的文字說明、以及「心得」的心得文字，輸入框要隨內容增長自動長高，不要使用垂直捲軸。

**作法**（`frontend/desktop/src/views/CardDetailView.vue`）：
- 新增區域自訂指令 `v-autogrow`：`input` 時將 `height` 先設 `auto` 再設為 `scrollHeight`，並關閉 `overflow-y`（hidden）與 `resize`（none）；`updated` 鉤子於載入資料或程式設值後重算高度（`nextTick`）。
- 套用於「文字說明」（`card.intro_text`）與每則「心得文字」（`r.text`，`v-for` 共用同一指令）。

**驗證**（dev server 實機）：以實際內容測試，`overflow-y:hidden`、內容不裁切；簡介加 5 行 336→432px、心得加 4 行 68→106px，皆自動長高。乾淨載入與正常操作 0 錯誤（開發期 console 曾見的 `invokeDirectiveHook` 錯誤為 HMR 熱更新時舊 vnode 缺少新指令的假象，非執行階段問題）。

#### 11.34 養身館列表支援拖曳排序＋插入提示（新增 `Spa.position`／move 端點／SpaListView）

**需求**：養身館卡片之間可拖曳改變順序，並有插入位置提示。

**作法**：
- **後端**：`Spa` 新增 `position` 欄位（`models/spa.py`）；`database.py` 的 `_COLUMN_MIGRATIONS` 登記 `spa.position`，並於補欄位時以相關子查詢依 `created_at` 回填 0,1,2…（保留既有列表順序）。`routers/customer.py`：`list_spas` 改 `ORDER BY position, created_at`、`create_spa` 以 `_next_position` 把新養身館排到最後、新增 `POST /spas/{id}/move`（沿用看板 `move_board` 的重新編號邏輯）。`api.js` 新增 `moveSpa`。
- **前端**（`SpaListView.vue`）：引入 SortableJS，卡片右上角加拖曳把手 `⠿`（`handle:.spa-drag`，避免與點擊開啟、編輯/刪除衝突），拖曳時以虛線藍框 `.spa-ghost` 標示插入位置（與看板插入提示一致）；`onEnd` 還原 DOM 後呼叫 `moveSpa` 再 `load()`。

**驗證**（dev server 實機）：遷移後 `position` 回填 0,1,2,3；`move` 端點把第 1 間移到位置 2 → 222/333/111/4752745、再還原正確；前端 Sortable 實例掛上且選項正確（`draggable:.spa-card`/`handle:.spa-drag`/`ghostClass:spa-ghost`），把手與虛線插入提示樣式正確。（拖曳手勢本身無法用合成事件模擬——桌面 SortableJS 走原生 HTML5 DnD，與既有看板拖曳同限制。）

#### 11.35 養身館支援多位幹部，各含聯絡資訊（新增 `SpaStaff` 表／移除 `Spa.staff`／SpaListView／SpaBoardView）

**需求**：每張養身館卡片可有多位幹部，且每位幹部新增「聯絡資訊」欄位。

**作法**：
- **資料模型**（`models/spa.py`）：移除 `Spa` 的單一字串 `staff`，新增一對多 `SpaStaff`（`spa_id` FK／`name`／`contact` 聯絡資訊／`position`）；`models/__init__.py` 匯出 `SpaStaff`。
- **遷移**（`database.py`）：`_backfill_spa_staff()` 先把舊的 `spa.staff` 非空值搬進 `spastaff`（保留既有幹部），再由 `_DROP_COLUMNS["spa"]=["staff"]` 移除 `staff` 欄位——**順序不可顛倒**，否則殘留的 NOT NULL 欄位會讓新版 INSERT 失敗。
- **API**（`routers/customer.py`）：新增 `StaffMemberIn`；`list_spas`／`get_spa`／`create_spa` 回傳含 `staff_members`；`update_spa` 以「整批覆蓋」更新幹部清單（空白名稱略過、未提供 `staff_members` 則不動）；`delete_spa` 一併清除幹部。
- **前端**：`SpaListView.vue` 編輯表單改為可多列的幹部清單，每位幹部分兩行——第一行「幹部名稱＋輸入框」、第二行「聯絡資訊＋輸入框」（兩輸入框提示詞皆「選填」），含「＋ 新增幹部」與每列移除 ✕；卡片顯示逐位列出 `👤 名字．聯絡資訊`。`SpaBoardView.vue` 看板頁頂同步改為列出多位幹部與聯絡資訊。

**驗證**（dev server 實機）：遷移後 `spa.staff` 欄位移除、`spastaff` 表建立、舊幹部「nty」自動搬入；後端可多筆新增（含聯絡資訊、UTF-8 正確）、空白名稱略過、省略時不更動；前端端到端：編輯→既有幹部預填→新增第二位→儲存→列表與看板頁皆正確顯示兩位幹部與聯絡資訊；編輯表單兩輸入框各為「標籤＋輸入框」同一行、兩行上下排列。測試資料已還原。

### 2026-06-23 — 系統拆分：移除客人系統、原「店家」更名為「幹部」（全專案架構調整）

依 [`AhhOuch 多人使用需求.md`](./AhhOuch%20多人使用需求.md) 的拆分方向（為營利把「客人」系統獨立成另一套免費／付費產品），**本專案資料夾自此只保留原「店家」系統，並全面更名為「幹部」**（英文識別字＝`cadre`），客人系統整組移除。使用者定案：①更名做到底——程式碼識別字／API 路徑／資料庫表名一起改；②客人系統的資料表一併刪除。

> ⚠ 本批**大幅改動資料庫結構（表／欄位更名＋整表移除）、後端碼、API 路徑與前後端檔名**。改碼後**需重啟後端**，首次啟動由 `database.py` 的 `_migrate_legacy_split()` 自動遷移既有 DB（**在 `create_all` 之前**執行）。遷移前已備份 `DATA/ahhouch.db` → `DATA/ahhouch.db.bak-before-cadre-split`。

#### 11.36 移除客人系統、店家→幹部全面更名（backend 全區／frontend 全區／database 遷移）

**移除（客人系統）**：
- 後端：刪除 `routers/customer.py` 與 6 個客人模型 `models/{board,card,image,review,spa,template}.py`。
- 前端：刪除 `views/{SpaListView,SpaBoardView,CardDetailView}.vue`。
- `api.js` 移除所有 `/api/customer/*` 方法；`config.py` 移除客人專用的 `DEFAULT_BOARDS`、`DEFAULT_RATING_ITEMS`。
- `database.py` 移除 `_seed_defaults`（植入預設評分模板）與客人相關的 `_DROP_COLUMNS`／`_COLUMN_MIGRATIONS` 項目。

**更名（店家 → 幹部／cadre）**：
- 模型（`models/cadre.py`，原 `store.py`）：`StoreCard→CadreCard`、`StoreCardImage→CadreCardImage`；資料表 `storecard→cadrecard`、`storecardimage→cadrecardimage`；外鍵欄位 `store_card_id→cadre_card_id`。`models/schedule.py` 的 `ScheduleEntry.store_card_id→cadre_card_id`（FK 指向 `cadrecard.id`）。`models/__init__.py` 同步更新匯出。
- 路由（`routers/cadre.py`，原 `store.py`）：前綴 `/api/store→/api/cadre`、`tags=["cadre"]`、內部 `StoreCard*` 識別字全面改 `CadreCard*`。`main.py` 改 `include_router(cadre.router)`、移除 `customer` 匯入。
- 前端：`components/CadreNav.vue`（原 `StoreNav.vue`）、`views/CadreCardListView.vue`／`CadreCardDetailView.vue`（原 `StoreCard*View.vue`）；`router.js` 路由改 `/cadre/*`、route name `store-*→cadre-*`、`/` 改 `redirect` 到 `cadre-list`；`api.js` 的 `*StoreCard*` 方法改 `*CadreCard*`、URL 改 `/api/cadre/*`、`addEntry` body 改 `cadre_card_id`。`ScheduleEditView.vue` 的 `storeCards→cadreCards`、`e.store_card_id→e.cadre_card_id`。
- **移除頂部「客人／店家」角色切換鈕**（`App.vue`）：只剩單一系統，頁首僅留品牌字樣，`/` 直接進幹部資訊卡片列表。
- `README.md` 改寫為單一「幹部」系統說明。

**資料庫遷移**（`database.py`，新結構）：
- 新增 `_migrate_legacy_split()`，**必須在 `create_all` 之前**執行——否則 `create_all` 會先建一張空的 `cadrecard`，使後續「`storecard` 更名為 `cadrecard`」因目標已存在而失敗：
  - `_TABLE_RENAMES`：`storecard→cadrecard`、`storecardimage→cadrecardimage`（來源在、目標不在時才更名，可重複執行）。
  - `_COLUMN_RENAMES`：`cadrecardimage`／`scheduleentry` 的 `store_card_id→cadre_card_id`。
  - `_DROP_TABLES`：移除客人殘留表 `cardimage, cardreview, reviewscore, customercard, board, spastaff, spa, ratingtemplateitem, ratingtemplate`。
- `_migrate_columns()`（原 `_migrate` 的補欄位部分）改於更名後執行，僅保留 `cadrecard.info_link`、`schedule.date／footer` 的 ADD COLUMN 防呆。`_cleanup_legacy_data()`（清 LINE 目標）維持。
- **既有幹部資料完整保留**（DB 副本驗證：原 `storecard` 2 筆→`cadrecard` 2 筆、`storecardimage` 1 筆、`scheduleentry` 2 筆皆保留並換欄名；客人表全數刪除）。

**驗證**（三段）：
- 後端：DB 副本跑遷移 → 表名／欄名正確、客人表已刪、資料筆數保留；`TestClient` 對 `/api/cadre/cards`、`/schedules`、`/publish/targets`、`/text-templates` 皆回 `200`、卡片數＝2。
- 前端：`npm run build` 成功（44 模組轉換）。
- 瀏覽器（`preview_server.py` 8030，以真實 DB 副本作 `.preview_data/preview.db`）：首頁無角色切換鈕、`/`→`#/cadre`、資訊卡片/班表/發布頁皆正常、**主控台 0 錯誤、無失敗請求**；班表出勤以 `cadre_card_id` 連動正確（兩張卡片皆顯示 ✓ 出勤、entries 正確解析名字與時段）。
- 正式 `DATA/ahhouch.db` 將於下次正式啟動時自動套用同一遷移（已備份）。

**GitHub**：儲存庫名稱經 API 認證查詢確認已是 `FatPigDash/AhhOuch_Manager`（private），本機 `origin` remote 亦正確指向，**無需改名**。

### 2026-06-25 — 架構轉型：FastAPI+exe → Local-First PWA（M1–M2）

本批為**架構層級的轉型**，將整個幹部系統從「FastAPI 後端 + 集中式 SQLite + PyInstaller exe」改為「Vue 3 PWA + IndexedDB 本機儲存 + GitHub Pages 靜態托管」。依 [`AhhOuch_Manager 幹部系統手機版開發計畫.md`](./AhhOuch_Manager%20幹部系統手機版開發計畫.md) 執行。

> ⚠ 本批**不動後端**（FastAPI 開發者本機仍可用）；**前端全面改為本機優先（Local-First）**，IndexedDB 取代所有 `/api/*` 呼叫。移除了 Telegram 自動發布相關 UI，改由 M4 的 Web Share API 接手（M4 尚未開發）。

#### 11.38 M1：幹部系統資料層移植 — FastAPI → IndexedDB（Local-First）

**目標**：前端 App 完全離線可用，不依賴開發者電腦啟動後端。

**新增 `frontend/desktop/src/db.js`**（IndexedDB 完整資料層）：
- DB 名 `ahhouch_db` version 1，object stores：`cards`、`images`（index: `by_card`）、`schedules`、`entries`（index: `by_schedule`）、`text_templates`（index: `by_kind`）。
- 每個操作開獨立 transaction（避免 IndexedDB async/await 自動 commit 問題）；多 store 原子操作用 `txDone(t)` 等待 transaction 完成。
- 圖片以 Blob 存 IndexedDB，讀取時用 `URL.createObjectURL(blob)` 產生 Object URL 供 `<img src>` 使用。
- 移植原後端邏輯：`normalizeTime("1830")→"18:30"`、`calcShiftSlots(start)` 8 班次換算、`cardPublishText` / `schedulePublishText` 格式化文字產生。

**改寫 `frontend/desktop/src/api.js`**（全面本機化）：
- 所有 method 改為呼叫 `db.js`，無任何 `fetch` 呼叫。
- `meta()` 回傳靜態標題；`shiftSlots()` 呼叫 `db.calcShiftSlots()`。
- `publishCard` / `publishSchedule` 留空 stub（M4 Web Share API 接手）。
- 移除：`publishPlatforms`、`listTargets`、`createTarget`、`updateTarget`、`deleteTarget`、`sendPublish`。

**清理前端 UI（移除 Telegram 自動發布相關）**：
- `CadreNav.vue`：移除「發布設定」tab，只剩「資訊卡片 ｜ 班表」。
- `router.js`：移除 `publish-settings` 路由；hash 模式保留（GitHub Pages 靜態托管免 rewrite）。
- `CadreCardDetailView.vue`：移除 Telegram 自動發布 UI（選目標、挑圖、預覽、發送），移除 `info_link` 欄位。
- `ScheduleEditView.vue`：移除班表自動發布到 Telegram UI。
- `views/PublishSettingsView.vue`：整檔刪除（發布設定頁不再需要）。

**P0 手機版面修正**（同批）：
- `CadreNav.vue`：加 `flex-wrap: wrap` 修正 tab 在窄螢幕溢出。
- `CadreCardDetailView.vue`：加 `@media(max-width:640px)` 修正 action-bar、img-add、title-input。
- `CadreCardListView.vue`：`.add-bar` 加 `flex-wrap: wrap`，input 加 `min-width`，button 加 `white-space: nowrap`。

**驗證**（Vite dev server 5173，preview_eval）：
- 頁面載入顯示「AhhOuch_Manager v2.1.0」，只有「資訊卡片 ｜ 班表」兩 tab。
- IndexedDB 寫入/讀取：建立卡片 #101、#202，`listCards()` 正確回傳兩筆。
- 重新整理後資料持久保留（IndexedDB 不因重整消失）。

#### 11.39 M2：PWA 化與 GitHub Pages 自動部署

**目標**：幹部可透過手機瀏覽器開啟網址後「加入主畫面」，離線使用；開發者 push 後自動更新。

**PWA 設定（`frontend/desktop/vite.config.js`）**：
- 加入 `vite-plugin-pwa`（devDependencies）：`registerType: autoUpdate`、`generateSW` 策略、`globPatterns` 快取所有靜態資源（js/css/html/png/svg/woff2）。
- manifest：`name: AhhOuch_Manager`、`short_name: AhhOuch`、`display: standalone`、`theme_color: #102a43`、`start_url: ./`、`scope: ./`。
- Build 產出：`dist/manifest.webmanifest` + `dist/sw.js` + `dist/workbox-*.js`，離線可用。

**iOS meta tags（`frontend/desktop/index.html`）**：
- `apple-mobile-web-app-capable: yes`、`apple-mobile-web-app-status-bar-style: black-translucent`、`apple-mobile-web-app-title: AhhOuch`。
- `<link rel="apple-touch-icon" href="apple-touch-icon.png">`。

**PWA 圖示（`frontend/desktop/public/`）**：
- `scripts/create-icons.mjs`：純 Node.js 腳本（無額外套件），產生深藍色（`#102a43`）實心 PNG：`icon-192.png`（192×192）、`icon-512.png`（512×512）、`apple-touch-icon.png`（180×180）。

**GitHub Pages 自動部署（`.github/workflows/deploy.yml`）**：
- `on: push: branches: [main]`；permissions 最小化（`contents: read`、`pages: write`、`id-token: write`）。
- 步驟：checkout → setup-node 20 → `npm ci`（`frontend/desktop/`）→ `npm run build` → upload-pages-artifact（`dist/`）→ deploy-pages。
- push main 後約 2–3 分鐘自動更新 GitHub Pages；幹部重新整理頁面即取得最新版。

**部署網址**：`https://FatPigDash.github.io/AhhOuch_Manager/`

**README 改寫**（`README.md`）：移除舊版 FastAPI+exe 安裝說明，改為：幹部加入主畫面教學（iOS/Android）、開發者部署流程（`git push` 一行）、本機開發（`npm run dev`）、目錄結構說明。

**修正：CI build 失敗（`vite-plugin-pwa` 缺漏）**：
- 根因：`vite-plugin-pwa` 已加入 devDependencies，但 package.json 修改從未被 commit；CI 上的 package.json 無此套件，`npm ci` 未安裝，vite.config.js 載入失敗。
- 修正：commit package.json 並同步 package-lock.json（含 `vite-plugin-pwa 1.3.0` 及其依賴樹）；移除 workflow 的 npm 快取設定（快取導致 lockfile 誤判）。
- 教訓：排查 CI 失敗時應先確認 `git status` 有無未提交的 package.json 變更，再查 lockfile 與 workflow。

**驗證**：GitHub Actions 成功跑完（綠色勾勾）；`https://FatPigDash.github.io/AhhOuch_Manager/` 可開啟。

### 2026-06-26 — 手機版里程碑完成：M3–M6 ＋ Telegram 自動發布還原

承上批 M1–M2，本批一口氣完成手機版剩餘里程碑 **M3–M6** 並依使用者要求**還原 Telegram 自動發布**（純前端直連）。完成後 M0–M6 全數結案、需求對照表全項驗收通過（見 §11.44）。

**本批範圍與決策**：
- **M3 圖片**：匯入最佳化＋縮圖（支撐 2000 張）、拍照、剪貼簿貼上。
- **M4 發布**：Web Share API（班表＋卡片，卡片可選照片、§6.2 降級）。
- **M5 草稿**：班表發布狀態追蹤（即時存草稿＋已發布徽章）。
- **M6 備份**：ZIP（fflate）＋選擇性加密（AES-GCM）＋每月提醒橫幅＋語系相容＋整體驗收。決策經使用者確認：ZIP 格式、選擇性加密、應用內提醒、語系僅相容、匯入整批覆蓋。
- **補做**：Telegram 自動發布以純前端直連 `api.telegram.org` 還原（與 Web Share 並存），不需後端。
- **共通驗證方式**：Vite dev server 實機 `preview_eval`（桌面 Chromium）逐項驗證資料層與 UI 端到端，每批 `npm run build` 通過，測試資料皆清為基線（#101／#202）。屬真機才能覆蓋者（§6.2/§6.3/§6.4）列為待實機驗證。

> 各里程碑細節見下列 §11.40–§11.45。

#### 11.40 M3：圖片功能（手機版）— 匯入最佳化＋縮圖、拍照、剪貼簿貼上按鈕

**目標**：手機端三種圖片來源（相簿選取／直接拍照／剪貼簿貼上）齊備，並做大圖縮圖最佳化以支撐「預設 2000 張圖片」容量基準（計畫 §6.3 / 需求 C2、D3、D5）。

**新增 `frontend/desktop/src/imageUtil.js`（圖片最佳化）**：
- `processImage(File|Blob)` → `{ full, thumb }`：以 `createImageBitmap`（`imageOrientation:'from-image'` 依 EXIF 自動轉正；不支援時退回 `HTMLImageElement`）解碼，再用 canvas 等比縮放後 `toBlob` 重新編碼為 JPEG。
- 兩份輸出：`full` 最長邊 ≤ 1600px（quality 0.85，供燈箱／發布排版）、`thumb` 最長邊 ≤ 400px（quality 0.7，供列表與編輯頁網格）。
- JPEG 無透明度，繪製前先鋪白底，避免透明 PNG 轉檔後出現黑背景。
- 任一步驟失敗則退回原圖，確保上傳不因最佳化中斷。

**`db.js`**：
- `addImage` 改為先 `processImage` 再存：images 記錄新增 `thumb` 欄位（DB 仍 version 1，僅新增物件欄位、不需升級）。回傳含 `thumb_url`。
- `getCard` 每張圖回傳 `thumb_url`（舊資料無 `thumb` 時退回完整圖）；`listCards` 封面改用縮圖。

**`CadreCardDetailView.vue`**：
- 圖片網格 `<img>` 改用 `thumb_url`（燈箱仍開完整圖 `url`）。
- 圖片操作列新增「📷 拍照」（`<input capture="environment">`，手機直接開相機）與「📋 貼上」（`navigator.clipboard.read()`，手機版讀剪貼簿圖片；不支援時提示改用上傳／Ctrl+V）；保留桌面 Ctrl+V 貼上。
- 新增 `busy` 狀態：壓縮／縮圖期間按鈕停用並顯示「處理圖片中…」。

**`api.js`**：移除已無用的 `pasteCadreImage` 與 `dataUrlToBlob`（貼上改以 Blob 直送 `uploadCadreImage`，最佳化統一在 `db.addImage` 完成）。

**驗證**（Vite dev server 實機 preview_eval）：
- 最佳化：來源 PNG 2400×1600（3209 KB）→ `full` 1600×1067 JPEG（18 KB）、`thumb` 400×267 JPEG（2 KB），長邊上限與比例正確。
- 端到端：經 UI 同一路徑 `api.uploadCadreImage` 上傳→設封面→網格顯示縮圖（`blob:` URL）、封面藍框與「封面」標記正確；刪除後歸零。測試資料已清除。
- 三顆按鈕（上傳／拍照／貼上）與提示文字渲染正確（截圖佐證）。
- `npm run build` 成功（44 模組、PWA 產出）。
- 註：iOS Safari／Android Chrome 之 `capture` 開相機與 `clipboard.read()` 讀圖屬 §6.4 待實機驗證項，桌面 Chromium 已驗證程式路徑與降級提示。

#### 11.41 M4：班表與卡片發布（Web Share API）

**目標**：班表與單張卡片可一鍵透過手機原生分享選單發送至 LINE 等；卡片可選擇是否連同照片發出、用完整或簡短介紹（需求 C4、C5、S5）。開發者不維護任何發布端點（計畫 §4.3）。

**新增 `frontend/desktop/src/share.js`（Web Share 封裝）**：
- `canShare()` / `canShareFiles(files)`：偵測 `navigator.share` 與 `navigator.canShare({ files })` 支援度。
- `share({ title, text, files })`：統一入口，回傳 `'shared'`／`'cancelled'`（使用者取消，`AbortError`）／`'unsupported'`。
- `urlsToFiles(urls, baseName)`：把圖片 Object URL `fetch` 回 Blob 再包成 `File[]` 供 `share({ files })` 使用（副檔名 jpeg→jpg）。
- 注意：`navigator.share` 必須在使用者手勢中直接呼叫，故各視窗的分享按鈕直接呼叫此處函式。

**`CadreCardDetailView.vue`（卡片發布）**：
- 發布視窗新增「📤 分享至 LINE 等」主按鈕；原「複製純文字／下載排版圖片」降為次要備援。
- 新增「連同照片一起發出（N 張）」核取方塊（C4，預設勾選）；介紹版本沿用既有完整／簡短切換（C5）。
- §6.2 降級：勾選照片但 `canShareFiles` 為否時，退為純文字分享並提示「圖片可用『下載排版圖片』另存後手動傳送」；`navigator.share` 不存在時提示改用備援。
- `shareSupported` 在 setup 取一次，無 Web Share 的裝置不顯示分享鈕、只留備援。

**`ScheduleEditView.vue`（班表發布）**：
- 發布視窗同樣新增「📤 分享至 LINE 等」主按鈕，分享 `schedulePublishText` 產生的格式化文字（標題／日期／各人編號＋簡短介紹＋時段／結語）；標題取首行作為分享 title。備援與降級提示同上。

**`api.js`**：移除已無用的 `publishCard`／`publishSchedule` 空 stub（發布改由各視窗以 `share.js` 在使用者手勢中直接呼叫）。

**驗證**（Vite dev server 實機 preview_eval；桌面 Chromium 無原生 `navigator.share`，故以 stub 注入後 SPA 內導航讓元件重新掛載擷取支援度）：
- `share.js` 單元：桌面 `canShare()=false`、`urlsToFiles` 產出正確 `File`（名稱／type）、`canShareFiles` 不報錯回 false、`share()` 在無支援時回 `'unsupported'`。
- 卡片端到端：發布視窗顯示分享主鈕、照片核取方塊「連同照片一起發出（1 張）」、兩個備援鈕；點分享 → `navigator.share` 收到 `{ title:'#101', text:'#101', files:['#101_1.jpg'] }`；取消勾選照片後再分享 → `files` 為空（純文字）。
- 班表端到端：分享 payload `{ title:'M4測試班表', text:'M4測試班表\\n\\n#101' }`，格式正確（截圖佐證）。
- `npm run build` 成功（PWA 產出）。測試資料已清除。
- 註：實際彈出系統分享選單、攜帶圖片至 LINE 屬 §6.2 待實機驗證項（iOS 15+ Safari／Android Chrome），桌面已驗證 payload 組裝與降級邏輯。

#### 11.42 M5：草稿管理（S6/S7）— 發布狀態追蹤

**背景**：本架構下班表在編輯時即時寫入 IndexedDB（每次改動立刻存），且新增與編輯共用同一 `ScheduleEditView`，故「自動存草稿」（S6 前半）與「修改草稿介面同初次編輯」（S7）本就成立。M5 補足的是**發布狀態的可見性**——讓「發布後留存草稿、可再次編輯發布」有明確標示，能分辨哪些班表已發布、何時發布。

**`db.js`**：
- schedule 記錄新增 `published_at`（DB 仍 version 1，僅新增物件欄位）；`createSchedule` 初始為 `null`、`getSchedule`／`listSchedules` 一併回傳。
- 新增 `markSchedulePublished(id)`：設 `published_at = now()`，**刻意不動 `updated_at`**——發布未改內容，草稿列表的「更新」時間只反映內容編輯。

**`api.js`**：新增 `markSchedulePublished`。

**`ScheduleEditView.vue`**：發布視窗三個輸出動作（分享成功 `'shared'`／複製純文字成功／下載排版圖片成功）任一完成後呼叫 `markPublished()` 記錄發布時間並更新本地 `published_at`；記錄失敗不影響發布本身。

**`ScheduleListView.vue`**：每列標題後加狀態徽章——`published_at` 有值顯示綠色「已發布」並於 meta 加「發布 {時間}」，否則顯示灰色「草稿」。

**驗證**（Vite dev server 實機 preview_eval）：
- 資料層：新班表 `published_at=null`→`markSchedulePublished` 後列表與 `getSchedule` 皆帶發布時間。
- 列表 UI：草稿（灰）與已發布（綠＋發布時間）兩種徽章正確渲染（截圖佐證）。
- 端到端：開啟草稿→發布視窗點「下載排版圖片」→該草稿即翻為「已發布」（走真實 UI 路徑 `markPublished`）。
- `npm run build` 成功。測試資料已清除。

#### 11.43 M6：備份與收尾 — ZIP 備份（選擇性加密）＋每月提醒＋語系相容＋驗收

**目標**：幹部可匯出全部本機資料為單一備份檔上傳自有雲端，換機／清快取後匯入還原（D4、計畫 §4.4／§6.5）。決策（經使用者確認）：備份格式 **ZIP（fflate）**、**選擇性加密**（opt-in 密碼）、**應用內提醒橫幅**、語系**僅相容不破版**、匯入採**整批覆蓋**。

**新增 `frontend/desktop/src/crypto.js`（選擇性加密）**：
- Web Crypto AES-GCM 256，金鑰以 PBKDF2（SHA-256，150k 迭代）由密碼導出。
- 加密檔格式：`magic "AOB1"(4) | salt(16) | iv(12) | ciphertext`；明文備份為標準 ZIP（開頭 `PK`）。`isEncrypted()` 以 magic 自動辨識。
- 密碼錯誤時 AES-GCM 驗證失敗 → 丟「密碼錯誤或檔案毀損」。

**新增 `frontend/desktop/src/backup.js`（打包／還原）**：
- 依賴 `fflate`（async `zip`/`unzip`）。ZIP 結構：`manifest.json`（卡片/班表/出勤/文字模板＋圖片索引）＋ `images/<id>.<ext>`（完整圖）＋ `images/<id>_t.<ext>`（縮圖）。圖片為 JPEG 已壓縮 → 以 `level:0` store 不再壓。
- `exportBackup(password?)`：`db.dumpAll()` → 組 zip → 有密碼則 `encryptBytes` → 回 `{ bytes, filename: AhhOuch備份_YYYY-MM-DD.ahbk }`。
- `importBackup(file, password?)`：讀 bytes → `isEncrypted` 則解密 → unzip → 驗 `manifest.app` → 重建圖片 Blob → `db.restoreAll`（整批覆蓋，單一交易）。`fileIsEncrypted(file)` 供 UI 先判斷是否需密碼。

**`db.js`**：新增 `dumpAll()`（各 store `getAll`）與 `restoreAll(data)`（清空全部 store 後保留原 id 寫回，單一交易確保原子性）。

**新增 `frontend/desktop/src/backupMeta.js`**：以 `localStorage` 記 `ahhouch_last_backup_at`；`backupOverdue()` 判斷從未備份或逾 30 天。

**新增 `views/BackupView.vue` ＋ 路由 `/cadre/backup` ＋ `CadreNav` 加「備份」分頁**：
- 匯出：選填密碼（留空＝明文，有設顯示「忘記密碼將無法還原」警告）；「📤 分享備份檔」（Web Share files，可存 iCloud/Drive；不支援時提示改下載）與「⬇ 下載備份檔」；成功後 `setLastBackupNow()`。
- 匯入：選檔（`.ahbk,.zip`）→ 自動偵測加密並要求密碼 → 「覆蓋還原」前 `confirm` 警告會覆蓋現有資料 → 顯示還原筆數摘要。

**`App.vue`（每月提醒橫幅）**：載入時若 `backupOverdue()` 且已有資料（卡片或班表），於頁首下方顯示黃色提醒橫幅，含「前往備份」連結與關閉鈕。

**語系相容**：`index.html` `lang="zh-Hant"`、`charset=UTF-8` 既有正確；全 App 日期用固定格式（硬編碼週別陣列，非 `toLocaleString`），繁中／日／英系統手機顯示一致、不破版——無需改碼。

**驗證**（Vite dev server 實機 preview_eval）：
- 匯出：明文開頭 `PK`、加密開頭 `AOB1`、`isEncrypted` 判斷正確。
- 往返：清空→匯入明文→卡片/圖片/班表筆數還原、封面保留、圖片 Blob 完好（600×400＋縮圖）。
- 加密：`fileIsEncrypted` 偵測 true；**錯誤密碼丟例外且未還原**（cards 仍 0）；正確密碼還原成功。
- UI：備份頁兩面板與四鈕齊備、導覽列新增「備份」分頁、每月提醒橫幅在逾期且有資料時顯示、`setLastBackupNow` 後 `backupOverdue` 轉 false。
- `npm run build` 成功（PWA 產出）。測試資料已還原為基線（#101／#202）。

#### 11.44 整體驗收（需求對照表 Traceability）

| # | 需求 | 狀態 |
| --- | --- | --- |
| A1 | PWA、iOS 加入主畫面 | ✅ M2 |
| A2 | iOS 優先、Android 兼容、手機/平板 | ✅ M2 |
| A3 | 無需開發者電腦/伺服器 | ✅ M1（IndexedDB Local-First） |
| C1 | 每位美容師獨立卡片，名稱可文字/編號 | ✅ M1 |
| C2 | 多圖上傳、設封面 | ✅ M1/M3 |
| C3 | 完整介紹／簡短介紹 | ✅ M1 |
| C4 | 卡片發布、可選是否附照片 | ✅ M4（Web Share，§6.2 降級） |
| C5 | 發布可選完整／簡短 | ✅ M4 |
| S1–S4 | 班表標題/出勤/時段（手動＋自動換算） | ✅ M1 |
| S5 | 班表發布含標題/編號/簡介/時段 | ✅ M4 |
| S6/S7 | 發布後留草稿、可改後再發布、同款編輯介面 | ✅ M5（即時存草稿＋發布狀態徽章） |
| D1/D2 | 資料全存本機、開發者不持有 | ✅ M1 |
| D3 | 相簿選取／拍照／剪貼簿貼上 | ✅ M3 |
| D4 | 帳號備份（匯出/匯入跨裝置） | ✅ M6（含選擇性加密、每月提醒） |
| D5 | 圖片 2000 張容量基準 | ✅ M3（匯入最佳化＋縮圖大幅降容） |

**待實機驗證項**（非桌面可完整覆蓋，留待真機）：§6.2 Web Share 攜圖至 LINE、§6.3 iOS/Android PWA 儲存持久性與 2000 張實測、§6.4 `capture` 開相機與 `clipboard.read()` 讀圖。桌面 Chromium 已驗證所有程式路徑與降級邏輯。

> M0–M6 全數完成，需求對照表全項驗收通過。

#### 11.45 補做：Telegram 自動發布還原（純前端直連 api.telegram.org）

**背景**：M1 移除了原本「後端 FastAPI 跑 bot 推送」的 Telegram 自動發布（因與「無開發者伺服器」決策衝突），改以 M4 的 Web Share API。使用者希望保留 Telegram 一鍵自動發布，故以**純前端直連**方式還原——PWA 直接呼叫 `api.telegram.org`，bot token／chat_id 存手機本機，**仍不需任何後端**。Web Share（LINE）並存。

**新增 `frontend/desktop/src/telegram.js`**：移植自原 `publish_service.py` 的 Telegram 邏輯——無圖 `sendMessage`、1 張 `sendPhoto`、多張 `sendMediaGroup`，文字未超過 1024 當圖片說明文字、過長則圖片送完補純文字。
- **關鍵踩雷與修正（CORS preflight）**：原以 `application/json` POST 會觸發 CORS 預檢（OPTIONS），而 Telegram Bot API 不回應 preflight，瀏覽器直連即失敗（`GET getMe` 可、`POST sendMessage` 不可）。改用 CORS 安全清單內的內容型別免預檢：一般呼叫用 `URLSearchParams`（`application/x-www-form-urlencoded`）、含圖片用 `FormData`（`multipart/form-data`）。修正後 `sendMessage`／`sendPhoto`／`sendMediaGroup` 皆能直連成功。

**`db.js`**：DB 升版 **v1→v2**，新增 `publish_targets` object store 與 `listTargets/createTarget/updateTarget/deleteTarget`（`updateTarget` 沿用「token 留空＝不更動」）。`publish_targets` 納入備份 `ALL_STORES`（換機可一併還原發布設定）。

**`views/PublishSettingsView.vue`（還原）＋ 路由 `/cadre/publish-settings` ＋ `CadreNav` 加「發布設定」分頁**：移植原設定頁，簡化為 Telegram 專用（移除未實作的 X）；保留 @BotFather 金鑰與 chat_id 取得的圖文教學彈窗；token 改存本機、列表顯示遮罩、編輯留空不更動。

**`CadreCardDetailView.vue` / `ScheduleEditView.vue`**：發布視窗新增「發送到 Telegram」區，列出啟用中的目標為按鈕；卡片沿用「介紹版本＋連同照片」選項以 `telegram.sendCard` 送出（圖片經 `share.js` 的 `urlsToFiles` 轉 File），班表以 `telegram.sendText` 送出並於成功後 `markPublished`。Web Share「分享至 LINE 等」與複製/下載備援保留。

**驗證**（Vite dev server 實機 preview_eval）：
- DB v2 升級、目標 CRUD（含 token 留空不更動、提供則更新）正確。
- **Telegram 直連**：修正前 `POST` 因 preflight 失敗（重現問題）；修正後 `sendText` 與 `sendCard`（多圖 multipart）皆抵達 API，假 token 回 `Unauthorized`（即請求成功送達，真 token 即可發出）。
- UI：發布設定頁、導覽新增分頁、卡片與班表發布視窗皆顯示「發送到 Telegram」目標按鈕；點擊端到端送出，失敗時顯示錯誤提示且班表不誤標已發布。
- `npm run build` 成功（新增 fflate 之外無新依賴；Telegram 用瀏覽器內建 fetch）。測試資料已清除為基線。

> 後端的 Telegram 程式碼（`backend/publish*`）對 PWA 已不再使用，可日後另行清理。

### 2026-06-24 — 美容師資訊編輯頁面 UX 精修（M4 範圍）

#### 11.37 美容師資訊編輯頁：頁面標示、文字框自動長高、修正編輯時畫面跳動（`CadreCardDetailView.vue`）

僅改前端單一檔 `frontend/desktop/src/views/CadreCardDetailView.vue`，不動後端與資料庫。

**(1) 頁面用途標示**：標題列下方加副標題「**美容師資訊編輯頁面**」（`.page-subtitle`），明確指出本頁在編輯美容師資訊卡片。

**(2) 完整介紹／簡短介紹文字框自動長高、完整顯示、移除垂直捲軸**：
- 新增 `v-autoresize` 指令套用於兩個 `<textarea>`（完整介紹、簡短介紹）。量高邏輯：先 `height:auto` 再設成 `scrollHeight`，使框高貼齊內容、完整呈現。
- CSS 將 textarea 改為 `resize:none; overflow-y:hidden`（保留 `rows` 為初始最小高度），徹底移除垂直捲軸。
- 修正 `box-sizing:border-box` 下 `scrollHeight` **不含邊框**會裁掉上下各 1px 的問題：量高時補回上下邊框寬度（`getComputedStyle` 取 `borderTopWidth/borderBottomWidth`）。

**(3) 修正：編輯任一文字框時畫面跳到上方**（(2) 上線後回報的副作用）：
- **主因**：`v-autoresize` 的 `updated` hook 只要元件重繪就會觸發，因此編輯**簡短介紹**或**資訊訊息連結**時，也會連帶對較高的**完整介紹**框重新量高——它會先被縮回 `auto`（瞬間變矮）再撐開，使頁面內容上移、捲動位置被瀏覽器夾回頂端；內容越長跳得越明顯。
- **修正**：在 `updated` 加上「只有**這個欄位自己**的內容真的改變（比對 `el._lastResizeValue`）才重新量高」的判斷，編輯其他欄位時完整介紹框完全不被觸發。
- **輔助**：`resizeTextarea` 量高前先記下 `window.scrollX/Y`、調整後立即 `window.scrollTo` 還原，作為正在編輯之文字框的雙重保險。

**驗證**：Vite 轉換／編譯通過、主控台 0 錯誤；於瀏覽器預覽以原生 DOM 實測自動長高（`border-box`／`content-box` 皆 `hasScroll:false`，內容完整無捲軸）與捲動位置保留邏輯。完整實機操作（實際渲染卡片）需後端＋登入＋既有卡片資料，未一併拉起，但編譯與核心機制均已確認。

---

### 2026-06-26 — 美容師卡片發布強化、批次發布、班表改善

#### 11.46 美容師卡片資訊連結：加入「發布設定名稱」欄位（`info_link_label`）

**背景**：美容師卡片發布到 Telegram 後，`info_link` 欄位會回填訊息連結；但當卡片對應多個發布目標時，使用者無法辨識該連結對應哪個群組。

**`db.js`**：IndexedDB `cards` object store 新增 `info_link_label` 欄位（字串）；`getCard` 與 `listCards` 一併回傳（`listCards` 同時補回 `info_link`，供後續批次發布判斷覆蓋或全新）。`updateCadreCard` 支援更新該欄位。

**`CadreCardDetailView.vue`**：
- 發布視窗新增「發布設定名稱」唯讀文字框（顯示 `info_link_label`），與「資訊訊息連結」欄位並列，讓使用者清楚知道連結對應哪個目標。
- 新增 `onLinkInput` 方法處理連結清空時自動清除標籤（避免 Vue 模板行內 `if` 語法解析錯誤）。
- 發布成功後同步將目標名稱存入 `info_link_label`（DB + 本地 reactive）。

**驗證**：`npm run build` 成功。

#### 11.47 美容師卡片發布：確認視窗選擇覆蓋或全新、優先覆蓋為預設

**背景**：使用者希望能修改既有 Telegram 訊息（避免舊連結失效、保留已分享連結的點擊流量），而非每次都發全新訊息。

**`telegram.js`**：新增 `editCard(token, chatId, messageId, files, text)` 函式，依圖片數量分別呼叫：
- 0 張 → `editMessageText`（HTML parse_mode）
- 1 張 → `editMessageMedia`（`InputMediaPhoto` 重新上傳）
- 多張 → 先嘗試逐張 `editMessageMedia` 更新、若訊息為相簿群組則改 fallback 為純文字 `editMessageText`（Telegram 不允許修改多圖 media group 的媒體）

**`CadreCardDetailView.vue` 的 `sendToTelegram`**：
- 新增 `publishMode`（`ref('new')`），已有連結時預設為 `'edit'`（優先覆蓋）。
- 確認視窗新增兩個 radio 選項：「✏ 覆蓋舊訊息」與「＋ 發布全新訊息」。
- `publishMode === 'edit'` 時呼叫 `tgEditCard`，連結保持不變；`'new'` 時呼叫 `tgSendCard` 並將新連結＋標籤回填（`info_link` / `info_link_label`）。

新增 `parseMsgId(link)` 與 `buildTgLink(chatId, messageId)` 輔助函式，從 `t.me` 連結解析 message_id 並反組連結。

**驗證**：`npm run build` 成功。

#### 11.48 批次發布美容師卡片

**目標**：讓幹部從列表頁勾選多張卡片，一次發布到多個 Telegram 目標，並將連結自動回填至各卡片。

**`CadreCardListView.vue`（全新重寫，含批次功能）**：

*批次模式切換*：工具列右側加「☑ 批次發布」按鈕，啟動後工具列切換為「已選 N 張 ＋ 全選/取消全選」。格狀與列表兩種視圖皆出現藍框勾選框，已選卡片藍色邊框高亮。

*浮動操作列*：固定於畫面底部，顯示已選張數、「📤 發布選取的卡片」與「✕ 退出」。

*批次發布 Modal — 三階段*：
- **設定**：介紹版本（完整／簡短）pill 選擇、圖片模式（僅封面圖／**所有圖片**（最多 10 張）／不附圖片）、目標多選 checkbox（預設全選）、訊息模式（**優先覆蓋** — 有既有連結且標籤相符者覆蓋、其餘全新；**全部全新** — 忽略既有連結）。設定完成後顯示摘要（X 覆蓋、Y 全新）。
- **執行中**：進度列 ＋ 每張卡片狀態即時更新（等待 → 📡 發送中… → ✓ 已覆蓋/已發布/已發布（原訊息已刪除）／✗ 失敗）。
- **完成**：成功/失敗計數摘要 ＋ 失敗詳細訊息 ＋ 關閉按鈕。

*連結回填*：全新模式發布成功後，自動將 `info_link` 與 `info_link_label` 存回 IndexedDB，並同步更新列表頁 reactive 資料（影響下次 Modal 的覆蓋判斷）。

**驗證**：`npm run build` 成功（54 模組）。

#### 11.49 發布時若原 Telegram 訊息被手動刪除，自動改發全新訊息

**背景**：使用者在 Telegram 手動刪除了已發布的訊息後，系統仍儲存舊連結；下次用「優先覆蓋」模式發布時會因訊息不存在而回傳 API 錯誤，應自動降級為全新發布。

**`telegram.js`**：新增並匯出 `isMessageNotFoundError(e)` 輔助函式，偵測錯誤訊息中是否含 `"message to edit not found"`、`"message_id_invalid"` 或 `"message not found"`（不分大小寫）。

**`CadreCardDetailView.vue`**（單張卡片發布）：
- Import `isMessageNotFoundError`。
- `sendToTelegram` 的 edit 分支以 `try/catch` 包住 `tgEditCard`；捕捉到「訊息不存在」時，顯示「原訊息不存在，自動改為發布新訊息…」，接著呼叫 `tgSendCard` 並將新連結回填（`info_link` / `info_link_label`）。

**`CadreCardListView.vue`**（批次發布）：
- Import `isMessageNotFoundError`。
- `runBatch` 的 edit 路徑同樣以 `try/catch` 包住 `editCard`；捕捉到「訊息不存在」時，自動切換為 `sendCard`，結果標示「✓ 已發布（原訊息已刪除）」並回填連結。

**驗證**：`npm run build` 成功。

#### 11.50 班表改善：出勤排序依資訊卡片、預設自動換算、發布名字超連結

**對應需求**：`待修改.md` 第三點「班表」的三個子項。

**(1) 出勤時段預設改為「自動換算」**：`db.js` `addEntry` 新建出勤記錄時 `time_mode` 改預設 `'auto'`（原為 `'manual'`）；`getSchedule` 的 `enriched` 未設 `time_mode` 時回退也改為 `'auto'`。

**(2) 出勤人員排序改依資訊卡片列表順序**：`db.js` `getSchedule` 原依 entry 的 `sort_order` 排列；改為從各 `cadreCard` 取 `sort_order ?? id` 後按資訊卡片順序排列（`enriched.sort` + `delete e._sort_order`）。`getSchedule` 同時將 `info_link` 納入 `enriched` 回傳，供發布文字使用。

**(3) 發布時出勤人員名字加 info_link 超連結（HTML 格式）**：
- `db.js` `schedulePublishText` 改為雙輸出：`text`（純文字，供複製/分享 LINE）與 `html`（Telegram HTML parse_mode 格式）。HTML 版若 entry 有 `info_link`，名字欄位以 `<a href="...">...</a>` 包裹。特殊字元（`&`、`<`、`>`）由 `escapeHtml` 處理。
- `telegram.js` `sendText` 新增 `opts = {}` 參數，支援 `parse_mode`。
- `api.js` `schedulePublishText` 改為直接回傳 DB 的 `{ text, html }` 物件（原本有額外 `.then` 包裝）。
- `ScheduleEditView.vue` 新增 `publishHtml ref`；`openPublish` 時同時取回 `text` 與 `html`；Telegram 發布時以 `publishHtml`（若有）搭配 `{ parse_mode: 'HTML' }` 送出；複製/分享 LINE 依然使用純文字 `publishText`。

**驗證**：`npm run build` 成功（54 模組，PWA 產出）。

#### 11.51 班表新增 Telegram 訊息連結與發布覆蓋模式

**背景與需求**：將美容師資訊卡片的「資訊訊息連結回填」與「覆蓋/新發布」功能，同樣移植到班表功能中，以便於後續修改更新同一則班表訊息。

**修改內容**：
- **資料庫 (`db.js`)**：`schedules` Object Store 新增 `tg_link` 與 `tg_link_label` 欄位；在 `createSchedule`、`getSchedule` 及 `updateSchedule` 均支援與回傳這兩個欄位。
- **發布 API (`telegram.js`)**：新增 `sendScheduleText`（發布純文字並回傳 `messageId`）與 `editScheduleText`（覆蓋現有文字訊息）。
- **班表編輯視圖 (`ScheduleEditView.vue`)**：
  - 結語下方新增「Telegram 訊息連結」與對應的標籤徽章顯示，支援發布後自動填入或手動編輯。
  - 發布確認視窗的 Telegram 發送區塊加入「確認流程」，當班表已有連結時，可選擇「覆蓋舊有訊息（預設）」或「發布全新訊息」。
  - 在執行發送時，會依選項自動呼叫 `editScheduleText` 或 `sendScheduleText`。若覆蓋時發生「原訊息已被刪除」錯誤，會運用 `isMessageNotFoundError` 捕捉並自動降級發布新訊息。

**驗證**：功能正常，`npm run build` 成功。

#### 11.52 備份 UI 簡化：移除分享按鈕、改為單一下載鈕並附雲端上傳說明

**背景**：

原有兩個按鈕——「📤 備份到雲端」（呼叫 Web Share API）與「⬇ 下載備份檔」（直接下載）。經排查，iOS Safari 的嚴格手勢時序限制（`NotAllowedError`）導致「備份到雲端」在 `await exportBackup()` 完成後呼叫 `navigator.share()` 時被拒絕，實際會自動退回下載行為——與「下載備份檔」功能完全重複。故決定：**移除「備份到雲端」按鈕及 `doShare()` 函式，僅保留單一「⬇ 下載備份檔」按鈕，並補充雲端上傳的操作說明文字。**

**修改 `views/BackupView.vue`**：

- 移除 `import { canShareFiles, share } from '../share'`（不再使用）。
- 刪除 `doShare()` 函式（含所有 Web Share API 邏輯）。
- 「📤 備份到雲端」按鈕改為主要樣式的「⬇ 下載備份檔」（唯一匯出入口）。
- 提示文字改為逐步操作說明：
  - 📱 **iOS**：下載後點選檔案 → 「儲存到檔案」→ 選 **iCloud Drive**
  - 🤖 **Android**：到「下載」資料夾 → 長按檔案 → 上傳到 **Google Drive**
- 下載成功訊息也同步改為白話操作指引（iOS / Android 分別說明）。

**修改 `App.vue`**（每月備份提醒橫幅）：

- 原文：「建議匯出備份到雲端以防資料遺失」
- 改為：「請下載備份檔並上傳到雲端（iOS → iCloud Drive；Android → Google Drive）」——與備份頁說明一致，讓使用者在提醒橫幅就能明白具體步驟。

**確認（背景知識）**：
- iOS iCloud 備份（手機設定層級）**不可靠地保護**瀏覽器 IndexedDB 資料——Apple 明確將瀏覽器本地儲存列為「可清除快取」，換機或清除網站資料皆會遺失，在 App 內匯出備份檔存至 iCloud Drive 是唯一可靠的跨裝置還原途徑。
- Android 可透過 Google Drive API 做自動直連上傳（需 OAuth 授權），但因使用者評估後認為手動備份已足夠，暫不實作。

**驗證**：`npm run build` 成功。

### 2026-06-27 — 軟體教學頁全面重寫

#### 11.53 GuideView 軟體教學重寫：補正說明內容、改用 CSS 模擬圖、刪除假 AI 圖片、修正備份副檔名

**背景**：原教學頁由 Gemini 生成，存在四類問題：
1. **捏造欄位**——說卡片可填「身高、體重、三圍」，實際不存在。
2. **班表模型錯誤**——示意圖顯示「上班／休假」切換，實際介面為「出勤人員 pill ＋ 出勤時段（手動輸入／自動換算班次）」。
3. **備份副檔名錯誤**——教學與使用聲明均寫成 `.ahhouch`，實際為 `.ahbk`。
4. **假 AI 圖片**——`public/img/` 下有 4 張英文 AI 生圖（"Sarah J. Anderson, Product Designer"、英文月曆），與本軟體無關且從未被程式碼引用。

**修改內容**（`frontend/desktop/src/views/GuideView.vue`，完整重寫教學分頁）：

*內容*：教學分頁改依**實際操作順序**重寫為 7 段——
0. 四大頁籤導覽（資訊卡片／班表／發布設定／備份）
1. 資訊卡片：建立與檢視（輸入名字/編號建立、卡片/列表切換、批次發布）
2. 編輯卡片內容（上傳/拍照/貼上/Ctrl+V、設封面、完整＋簡短兩段介紹、記得儲存）
3. 班表（日期自動顯示星期、標題/結語模板、出勤人員 pill、手動輸入 1830→18:30／自動換算班次、草稿/已發布）
4. 發布設定（名稱/機器人金鑰/群組編號、內建 [?] BotFather 申請教學、啟用/停用）
5. 一鍵發布（分享至 LINE／複製文字／下載圖片／發送 Telegram、選版本與照片、覆蓋不洗版）
6. 備份與還原（本機優先警告、`.ahbk` 加密匯出、覆蓋還原、每月提醒）

*模擬圖*：移除所有假圖（`public/img/` 整個目錄已刪除），改為**純 CSS 繪製的 UI 示意圖**，使用與真實介面相同的配色（`#102a43`、`#2680c2`）、按鈕文字與元件結構；行動版 (`max-width: 768px`) 自動改為垂直堆疊。

*使用聲明分頁*：補正備份檔副檔名由 `.ahhouch` 改為正確的 `.ahbk`。

**檔案異動**：
- `frontend/desktop/src/views/GuideView.vue` — 整個教學分頁重寫
- `frontend/desktop/public/img/tutorial_backup.png`、`tutorial_card.png`、`tutorial_publish.png`、`tutorial_schedule.png` — 刪除（4 張 AI 假圖）
- `frontend/desktop/public/img/`（目錄）— 已清空後刪除

**驗證**（Vite dev server `#/guide`，`preview_eval` 實機）：7 個 `h3` 標題正確、6 個 `.mockup` 區塊渲染、頁面含 `.ahbk`、不含 `.ahhouch`、不含「三圍」；行動版（`flex-direction: column`、無橫向溢出）正常。

#### 11.54 美容師卡片：第一張圖片自動設為封面

**背景**：原 `addImage()` 函式上傳圖片後一律回傳 `is_cover: false`，新建卡片上傳第一張圖片後封面區塊仍顯示「無封面」，需要使用者手動點 ★ 才能設定封面，操作步驟多餘。

**修改 `frontend/desktop/src/db.js`（`addImage` 函式）**：

- 圖片寫入 `images` store 後，額外開一筆 `cards` readwrite transaction，讀取該卡片的 `cover_image_id`。
- 若 `cover_image_id` 為 null（尚無封面），自動將剛寫入的圖片 ID 設為 `cover_image_id` 並回存 card，同時把回傳的 `is_cover` 設為 `true`。
- 若已有封面，跳過，維持原行為（不覆蓋）。

**行為說明**：

| 情境 | 結果 |
|------|------|
| 上傳**第一張**圖片（尚無封面） | 自動設為封面，顯示「封面」標籤 |
| 上傳**第二張以後**圖片 | 不影響現有封面 |
| 點擊非封面圖片的 **★ 按鈕** | 手動切換封面（現有功能不變） |
| 刪除封面圖 | 封面清空，需手動以 ★ 重新指定 |

**檔案異動**：`frontend/desktop/src/db.js` — `addImage` 函式新增封面自動設定邏輯。

#### 11.55 教學及聲明頁（GuideView）新增「回到主頁」按鈕

**背景**：`GuideView` 是從主頁右上角按鈕開啟的獨立頁面（`#/guide`），但頁面內無法導回主頁，使用者只能依賴瀏覽器上一頁按鈕。

**修改 `frontend/desktop/src/views/GuideView.vue`**：

- `<script setup>` 引入 `useRouter`，新增 `goHome()` 函式（`router.push({ name: 'cadre-list' })`）。
- 原 `.tabs` div 外包一層 `.guide-topbar`，左側加入「← 回到主頁」按鈕，右側保留原有的「📖 軟體教學」／「⚠️ 使用聲明」兩頁籤。
- 新增 `.guide-topbar`（flex 橫排、與 tab 列同底色）、`.guide-topbar .back`（圓角邊框按鈕、hover 高亮）、`.guide-topbar .tabs`（覆寫 `border-bottom: none`，底線改由 `.guide-topbar` 統一提供）等 CSS 規則。

**檔案異動**：`frontend/desktop/src/views/GuideView.vue`。

#### 11.56 資訊卡片列表：切換按鈕（卡片／列表）改為 tab 底線風格

**背景**：原「卡片／列表」切換按鈕為膠囊型（圓角容器 + 白底陰影 active），與教學頁 tab 底線設計不一致，視覺語言混亂。

**修改 `frontend/desktop/src/views/CadreCardListView.vue`**：

- `.view-toggle`：移除 `gap`、`border-radius`、`padding`；改加 `border-bottom: 2px solid #e1e8ed` 與 `align-self: stretch`（讓容器撐滿列高，底線才能貼齊）。
- `.view-toggle button`：移除 `border-radius`；加 `border-bottom: 3px solid transparent`、`margin-bottom: -2px`（蓋住容器底線）、`font-weight: 600`；padding 加大為 `10px 16px`。
- `.view-toggle button.active`：改為 `background: #fff; color: #102a43; border-bottom-color: #102a43`，移除原有 `box-shadow`。
- `.toolbar-right`：`align-items` 由 `center` 改為 `stretch`，讓 `.view-toggle` 能撐高。
- `.batch-toggle-btn`：新增 `align-self: center`，避免被 `stretch` 拉高。

**視覺效果**：切換按鈕現在與教學頁頁籤（`#102a43` 底線、白底 active）外觀一致，統一全站 tab 設計語言。

**檔案異動**：`frontend/desktop/src/views/CadreCardListView.vue` — `.view-toggle`、`.toolbar-right`、`.batch-toggle-btn` CSS 規則。

### 2026-06-29 — 發布設定教學彈窗新增快速複製按鈕（M6 範圍精修）

#### 11.57 發布設定教學彈窗：指令與網址新增快速複製按鈕（PublishSettingsView）

**需求**：§11.19 新增的兩個教學彈窗中，指令（`/newbot`、`/revoke`）和網址（`https://api.telegram.org/bot金鑰/getUpdates`）需要使用者手動選取複製，不夠方便。

**修改內容**（`frontend/desktop/src/views/PublishSettingsView.vue`）：

- `<script setup>` 新增 `copied` ref 與 `copyText(text)` 函式：呼叫 `navigator.clipboard.writeText()` 複製到剪貼簿，成功後按鈕文字暫時變為「已複製」（1.5 秒後恢復）。
- **機器人金鑰教學彈窗**：`/newbot` 指令與 `/revoke` 指令旁各加一顆「複製」按鈕。
- **群組編號教學彈窗**：`https://api.telegram.org/bot金鑰/getUpdates` 網址旁加一顆「複製」按鈕，以 `.url-row`（flex 橫排）包裹網址與按鈕，避免按鈕換行。
- 新增 CSS：`.copy-btn`（小型邊框按鈕、hover 高亮）、`.copy-btn.copied`（淺綠底表示已複製）、`.url-row`（flex 橫排容器）。

**檔案異動**：`frontend/desktop/src/views/PublishSettingsView.vue` — `copyText` 函式、三處複製按鈕、`.copy-btn` / `.url-row` CSS 規則。

