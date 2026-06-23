# AhhOuch_Manager 開發報告

> **本文件用途**：作為專案的「單一銜接文件」。之後開新對話只要先讀本檔，即可掌握
> 專案目標、最終架構、關鍵慣例、開發歷程、目前進度與待辦，無需重讀整個對話。
>
> 相關文件：
> - [`AhhOuch 需求.md`](./AhhOuch%20需求.md) — 原始需求（不可變的目標）
> - [`AhhOuch 開發計畫.md`](./AhhOuch%20開發計畫.md) — 開發前的總體規劃與需求對照表（修訂歷程已移至本報告 §12）
> - 版本修訂紀錄（依版次）— 已整合於本報告 §5 附錄（原獨立檔 `CHANGELOG.md` 已移除）
>
> 報告產生日期：2026-06-20（最後更新：2026-06-23，§12 增列 11.36：**系統拆分——移除客人系統、原「店家」更名為「幹部」(cadre)**；前次為 11.32–11.35 客人端精修）
> ｜ 對應版本：app.toml 1.7.0／git V2.0.0（自 §5 的 0.6.0 後持續精修發版，使用者以 `app.toml` 控版次） ｜ 狀態：**M0–M8 全部完成；2026-06-23 起拆分為「幹部」單一系統（客人系統已移除）**

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

- 版本 **1.6.0**（使用者持續用 `app.toml` 控版次；會自行 prettier 格式化與 git commit）。
  自 §5 完成 M0–M8（0.6.0）後，店家系統與社群發布持續精修並多次發版：
  git **V0.6.0 → V1.0.0 → V1.1.0「店家系統」→ V1.2.0 → V1.3.0 → V1.4.0 → V1.5.0**。
- **git 已提交至 `V1.5.0`**，其中**已含** §12 的 **11.26**（卡片自動發布複選內容＋發圖）、
  **11.27**（班表名字超連結）、**11.28**（班表日期欄位）、**11.29**（班表結語欄位）、
  **11.30**（標題／結語文字模板），以及 **11.31**（出勤時段時間序排列）的早期版本
  （僅自動換算依換算清單、手動依時鐘時間）。
- **git 已提交至 `V2.0.0`**（含 §12 的 11.31「最大空檔旋轉」排序，以及 11.32–11.35 的客人端看板/簡介/養身館精修；版次由使用者以 `app.toml` 控管）。
- **目前 working tree 尚未提交**——本次對話的**系統拆分：移除客人系統、原「店家」更名為「幹部」（cadre）**（§12 的 **11.36**）。涉及前後端全區、資料庫結構（表／欄位更名＋整表移除客人表）與前後端檔名變更：
  - 後端：刪 `routers/customer.py` 與客人 6 模型；`store.py`→`cadre.py`（`/api/cadre`、`CadreCard*`、表 `cadrecard*`、欄 `cadre_card_id`）；`config.py` 移除客人預設資料；`database.py` 新增 `_migrate_legacy_split()`。
  - 前端：刪 `Spa*`/`CardDetail` views；`StoreNav`→`CadreNav`、`StoreCard*View`→`CadreCard*View`；`router.js` 改 `/cadre/*`（`/` 導向 `cadre-list`）；`App.vue` 移除「客人／店家」切換鈕；`api.js` 移除客人方法、店家方法改 `cadre`。
  - ⚠ **含資料庫結構與後端變更**：改碼後**需重啟後端**，首次啟動 `_migrate_legacy_split()`（在 `create_all` 前）自動遷移既有 DB（已驗證遷移與資料保留；備份於 `DATA/ahhouch.db.bak-before-cadre-split`）。
  - **GitHub**：儲存庫已確認為 `FatPigDash/AhhOuch_Manager`（private），本機 `origin` remote 亦正確指向，**無需改名**。
- 開發驗證輔助：`preview_server.py`(8030，獨立 `.preview_data`，不干擾使用者 8000) 供不破壞使用者資料的預覽；`.claude/launch.json` 提供 `ahhouch`(8000)／`ahhouch-frontend`(Vite 5173)／`ahhouch-preview`(8030) 三組設定。

## 9. 待辦／待確認（不阻擋現況）

1. **社群自動發布實際串接**：平台已定為 **Telegram(預設)＋X**（LINE 已移除，§12 的 11.18）。
   Telegram 可實際推送**文字＋圖片（單張 sendPhoto／多張相簿，§12 的 11.26）**，使用者申請 Bot、
   填金鑰+群組 ID 即可；**X 自動發送尚未實作**（發文需 OAuth 授權，目前僅列為選項、選用時手動複製
   貼上），日後若要自動發 X 需補 OAuth 串接（§9-1）。
   - **班表名字超連結（§12 的 11.27）**只在「自動發布」訊息有效，且群組須為**超級群組/公開群組**
     （基本群組無訊息連結）。實際生效需使用者填真權杖、且該群組支援「複製訊息連結」。
2. **資料備份／匯出匯入**：尚未實作（§9-3）。
3. **班表發布是否需自訂樣式**：目前固定用需求範例格式（§9-4）。
4. **圖片貼上主要來源**：截圖 vs 複製檔案，兩者皆支援，主要用法待確認（§9-2）。
5. 多語系（繁中/日/英）相容性整體覆測；日文若改後端 Pillow 產圖需內嵌日文字型。

## 10. 啟動／打包／驗證 速查

```powershell
# 安裝
pip install -r requirements.txt        # 或雙擊 install.bat
cd frontend\desktop; npm install

# 方式 A（日常）：後端提供已建置前端 → http://localhost:8000
cd frontend\desktop; npm run build
cd ..\..; .\run_dev.bat

# 方式 B（前端開發，熱更新 → http://localhost:5173）
python run.py                          # 終端 1（後端，改碼需手動重啟）
cd frontend\desktop; npm run dev       # 終端 2（前端）

# 打包單一 exe → 打包輸出/AhhOuch_v<版次>.exe
python build.py
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
> - 11.5 / 11.7 / 11.14 / 11.15 / 11.16 → M4（店家資訊卡片）
> - 11.21 / 11.22 / 11.23 / 11.24 / 11.25 / 11.28 / 11.29 / 11.30 / 11.31 → M5（班表）
> - 11.18 / 11.19 / 11.20 → M6（社群發布）
> - 11.26 / 11.27 → M4＋M6（卡片自動發布內容選擇、名字超連結；亦影響 M5 班表發布）
> - 11.8 / 11.17 → 開發環境（Vite 代理、README、預覽設定）
> - 11.36 → 架構拆分（移除客人系統、店家→幹部更名；影響全專案後端／前端／資料庫）
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
