# AhhOuch

養身館用的資訊管理軟體，分為**店家**（發布美容師資訊與班表）與**客人**（記錄各養身館美容師資訊與心得）兩種角色。

- 後端：Python + FastAPI（提供 REST API 與靜態網頁）
- 前端：Vue 3（Vite 建置為靜態檔，由後端提供）
- 資料庫：SQLite（單一檔案，置於 `DATA/`）
- 打包：PyInstaller 單一免安裝 exe

---

## 1. 安裝環境與套件

> 需先安裝 [Python 3.11+](https://www.python.org/downloads/)（安裝時勾選 **Add to PATH**）與 [Node.js 18+](https://nodejs.org/)。

**後端套件（擇一）**

- 雙擊 `install.bat`，或在終端機執行：

  ```bat
  pip install -r requirements.txt

  或是指令
  python -m pip install -r requirements.txt
  ```

**前端套件**

```bat
cd frontend\desktop
npm install
```

---

## 2. 測試階段啟動

**方式 A — 一鍵啟動（建議日常使用）**

後端直接提供已建置的 Vue 介面，瀏覽器開 `http://localhost:8000`。

**首次啟動，或修改了前端程式碼之後，需先重新建置前端：**

```bat
cd frontend\desktop
npm run build
```

cd "D:\Fat Pig Project\AhhOuch_Edit\frontend\desktop"

**建置完成後，回到專案根目錄再啟動後端：**

```powershell
cd ..\..
.\run_dev.bat
```

> `cd ..\..` 會從 `frontend\desktop` 回到專案根目錄（`AhhOuch_Edit\`）。
> PowerShell 需加 `.\` 前綴才能執行當前目錄的 `.bat` 檔；`run_dev.bat` 必須在根目錄執行，否則找不到 `run.py`。

啟動後會自動開啟瀏覽器（`http://localhost:8000`）。

**方式 B — 前後端分離（前端開發時用，支援熱更新）**

開兩個終端機：

```bat
REM 終端機 1：後端
用方法A執行
```

```bat
REM 終端機 2：前端（http://localhost:5173，/api 自動代理到後端）
cd frontend\desktop
npm run dev
```

---

## 3. 打包成單一執行檔

```bat
python build.py
```

- 會自動建置前端、以 PyInstaller 產生單一 exe，並**清除打包過程檔**。
- 產出位置：**`打包輸出/`** 資料夾，檔名為 `AhhOuch_v<版次>.exe`（如 `AhhOuch_v1.0.0.exe`）。
- 已建置過前端、想略過前端建置：`python build.py --no-front`。

打包後的 exe 為免安裝，雙擊即啟動並開啟瀏覽器；資料會寫入 exe 旁的 `DATA/`。

---

## 4. 修改軟體名稱與版次

**唯一需要修改的檔案：`app.toml`（專案根目錄）。**

```toml
app_name = "AhhOuch"
version  = "1.0.0"
```

此檔為唯一事實來源，連動：前端標題、關於頁、以及打包後的 exe 檔名。**請勿在其他檔案硬編碼名稱或版次。**

---

## 5. 資料與輸出位置

| 項目             | 位置                               |
| ---------------- | ---------------------------------- |
| 資料庫與上傳圖片 | `DATA/`（`ahhouch.db`、`images/`） |
| 打包後的 exe     | `打包輸出/`                        |

> 開發模式下 `DATA/` 位於專案根目錄；打包後的 exe 則在 exe 所在目錄建立 `DATA/`。

---

## 6. 目錄結構

```
AhhOuch_Edit/
├─ run.py              進入點（也是打包進入點）
├─ app.toml            ★ 軟體名稱與版次（單點修改）
├─ requirements.txt    後端套件清單
├─ install.bat         一鍵安裝後端套件
├─ run_dev.bat         測試啟動
├─ build.py            打包腳本（輸出到 打包輸出/、清過程檔）
├─ backend/            FastAPI 後端
│  ├─ main.py  version.py  config.py  database.py
│  ├─ models/  routers/  services/
├─ frontend/
│  ├─ desktop/         電腦版（Vue 3 + Vite，優先開發）
│  └─ mobile/          手機版（預留，M7）
├─ DATA/               軟體輸出（資料庫、圖片）
└─ 打包輸出/           打包後的 exe
```
