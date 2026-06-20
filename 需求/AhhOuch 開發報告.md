# AhhOuch 開發報告

> **本文件用途**：作為專案的「單一銜接文件」。之後開新對話只要先讀本檔，即可掌握
> 專案目標、最終架構、關鍵慣例、開發歷程、目前進度與待辦，無需重讀整個對話。
>
> 相關文件：
> - [`AhhOuch 需求.md`](./AhhOuch%20需求.md) — 原始需求（不可變的目標）
> - [`AhhOuch 開發計畫.md`](./AhhOuch%20開發計畫.md) — 開發前的總體規劃與需求對照表（修訂歷程已移至本報告 §12）
> - [`../CHANGELOG.md`](../CHANGELOG.md) — 版本修訂紀錄（依版次）
>
> 報告產生日期：2026-06-20（最後更新：2026-06-21，§12 增列 11.18–11.25 社群發布平台與班表調整）
> ｜ 對應版本：0.6.0 ｜ 狀態：**M0–M8 全部完成**

---

## 1. 專案一句話

養身館資訊管理網頁軟體，分兩種角色：
- **客人**：記錄各養身館美容師的資訊與心得（看板化管理，類 Trello）。
- **店家**：管理美容師資訊卡片與班表，產生內容發布到社群群組。

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
├─ install.bat run_dev.bat requirements.txt README.md CHANGELOG.md
├─ backend/
│  ├─ main.py            FastAPI app、掛載 /images 與靜態前端、啟動建 DATA/+init_db
│  ├─ version.py         讀 app.toml（唯一取值來源）
│  ├─ config.py          路徑（開發 vs 凍結 exe 差異）、預設看板/評分項目
│  ├─ database.py        SQLite 引擎、init_db、_migrate(補欄位)、_cleanup_legacy_data(清遺留)、_seed_defaults
│  ├─ models/            spa board card image review template store schedule publish
│  ├─ routers/           customer.py(客人) store.py(店家+班表) publish.py(社群發布)
│  └─ services/          image_service shift_calculator time_utils publish_service
├─ frontend/
│  ├─ desktop/src/
│  │  ├─ views/          SpaListView SpaBoardView CardDetailView
│  │  │                  StoreCardListView StoreCardDetailView
│  │  │                  ScheduleListView ScheduleEditView PublishSettingsView
│  │  ├─ components/StoreNav.vue   api.js  router.js  App.vue  style.css
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
3. **資料庫遷移**：SQLite 不會自動 `ALTER`，故 `database.py` 的 `_migrate()` 處理兩類：
   `_COLUMN_MIGRATIONS`（PRAGMA 比對後 **ADD COLUMN**）與 `_DROP_COLUMNS`（**DROP COLUMN**，
   SQLite 3.35+）。**新增 model 欄位時，一定要在 `_COLUMN_MIGRATIONS` 登記；移除 model 欄位
   時，要在 `_DROP_COLUMNS` 登記**（否則舊 DB 殘留的 NOT NULL 欄位會讓新版 INSERT 失敗），
   既有使用者資料才不會在升級時壞掉。
4. **封面圖**由各圖片表的 `is_cover` 計算，回應時組出 `cover_image`，卡片本身不存封面欄。
5. **圖片**存 `DATA/images/`，DB 只存檔名；支援檔案上傳與剪貼簿 base64 貼上（PoC 6.1 已驗證）。
6. **發布**：第一階段產生「排版圖片(html2canvas)＋純文字」供手動貼；第二階段 API 自動發布為骨架。
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
  ↳ 後續精修（已套用）：資訊卡片封面高度加倍 §12 的 11.5、圖片燈箱 §12 的 11.7、**資訊卡片預設排序改數字自然＋其餘 Unicode 且不提供手動排序** §12 的 11.14、**詳情頁改「草稿＋儲存/取消」並把發布鈕移左下** §12 的 11.15、移除已無用的 `StoreCard.position` 欄位 §12 的 11.16。
- **M5 店家：班表**：多行標題、出勤人員點選、出勤時段(手動 1830→18:30／自動換算)、
  發布格式、草稿(S6–S12)。**發布輸出與需求 S11 範例字字相符**。
  ↳ 後續精修（已套用）：**出勤時段沿用出勤人員的名字排序**(顯示與發布文字一致) §12 的 11.21、**移除 `ScheduleEntry.position`（不保留手動拖曳排序）** §12 的 11.22、**出勤時段預設改自動換算** §12 的 11.23、**換算紀錄保留（載入時依 `auto_start` 還原班次格）** §12 的 11.24、編輯班表頁頂部列凍結(sticky) §12 的 11.25。
- **M6 社群 API 串接（通用骨架）**：發布目標設定(平台/權杖/目標 ID)、一鍵發布，
  內含 LINE Messaging API 與 Telegram 實作(urllib，免新套件)。權杖回應遮蔽(只露末四碼)。
  實測點發布**真的打到 LINE API**，假權杖回乾淨的 HTTP 401 → 整條管線通(P1)。
  ↳ 後續精修（已套用）：**平台改為 Telegram(預設)＋X，移除 LINE**（X 列為選項但自動發送未實作；LINE 殘留資料於啟動清除）§12 的 11.18、發布設定頁用語白話化＋欄位說明＋[?] 教學彈窗 §12 的 11.19、發布目標按鈕顯示「平台 名稱」＋點 pill 發送前二次確認 §12 的 11.20。
- **M7 手機版（響應式）**：各 view 加 `@media(max-width:640px)`；看板改原生橫向捲動、
  觸控停用自訂拖曳捲動；以 375px 視窗量測驗證無水平溢出(G1)。
- **M8 收尾與驗收**：全模組整合煙霧測試通過、重新打包 `AhhOuch_v0.6.0.exe`(27.5MB)成功、
  新增 CHANGELOG.md。

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
| C1–C22 客人全功能 | ✅ |
| S1–S12 店家資訊卡片＋班表 | ✅（發布格式與範例相符） |
| X1–X6 打包/設定/環境/README/DATA | ✅ |
| P1 社群自動發布 | 🟡 **骨架完成**；真正推送待使用者申請平台帳號＋填權杖 |

## 8. 目前狀態

- 版本 **0.6.0**（使用者持續用 `app.toml` 控版次；會自行 prettier 格式化與 git commit）。
- git 已提交至 **V0.6.0**；**M7 響應式 CSS、CHANGELOG.md、frontend/mobile/README、
  本開發報告等尚未 commit**，可併入下一版。
- 已知可清除遺留：`打包輸出/AhhOuch_v1.0.0.exe`（M0 測試時版次為 1.0.0 的舊產物）。
- 開發驗證輔助：曾用臨時 `preview_server.py`(8030) 做不干擾使用者 8000 的預覽；該檔已不存在，
  `.claude/launch.json` 中指向它的 `ahhouch-preview` 壞設定已移除（§12 的 11.17），並改提供
  `ahhouch-frontend`(Vite dev、5173) 供前端預覽。

## 9. 待辦／待確認（不阻擋現況）

1. **社群自動發布實際串接**：平台已定為 **Telegram(預設)＋X**（LINE 已移除，§12 的 11.18）。
   Telegram 可實際推送，使用者申請 Bot、填金鑰+群組 ID 即可；**X 自動發送尚未實作**（發文需
   OAuth 授權，目前僅列為選項、選用時手動複製貼上），日後若要自動發 X 需補 OAuth 串接（§9-1）。
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
> ② `git log` 與 [`CHANGELOG.md`](../CHANGELOG.md) — 版本歷程；
> ③ **程式碼本身**（最終事實）。若文件與程式碼衝突，**以程式碼為準**，並回頭修正文件。

1. 先讀本報告 §4（慣例）、§8（狀態）、§9（待辦），即可接手。
2. 改後端資料模型欄位 → 記得同步更新 `database.py`：新增欄位登記 `_COLUMN_MIGRATIONS`、
   移除欄位登記 `_DROP_COLUMNS`。
3. 改版次／名稱 → 只動 `app.toml`。
4. 動到使用者需求行為前 → 對照 `AhhOuch 需求.md` 與計畫 §2 需求對照表，並把修訂歷程補在
   **本報告 §12** 或 `CHANGELOG.md`（開發計畫維持為開發前文件，不再追加歷程）。
5. 要做 UI 變更 → 可用 `run_dev.bat`(方式 A) 或方式 B 在瀏覽器確認；手機版用瀏覽器
   響應式檢視（≤640px）測試。
6. 最可能的下一步：§9 的「資料備份/匯出匯入」或「社群發布平台實際串接」。

---

## 12. 開發中修訂歷程

> 此區為開發過程中的逐項調整紀錄（原記於開發計畫 §11，現移至本報告）。
> 保留原 `11.x` 子編號以維持各條目彼此的交叉引用。
>
> **這些調整皆已實作並套用至現行程式（＝目前實際行為），非待辦。** 與里程碑的對應：
> - 11.6 / 11.9 / 11.10 → M1（看板卡片顯示）
> - 11.1 / 11.11 / 11.12 → M2（排序與拖曳）
> - 11.2 / 11.3 / 11.4 / 11.7 / 11.13 → M3（卡片完整內容）
> - 11.5 / 11.7 / 11.14 / 11.15 / 11.16 → M4（店家資訊卡片）
> - 11.21 / 11.22 / 11.23 / 11.24 / 11.25 → M5（班表）
> - 11.18 / 11.19 / 11.20 → M6（社群發布）
> - 11.8 / 11.17 → 開發環境（Vite 代理、README、預覽設定）
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
