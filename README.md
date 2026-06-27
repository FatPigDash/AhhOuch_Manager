# AhhOuch_Manager

養身館**幹部**用的資訊管理 PWA：建立美容師資訊卡片、編排班表，並分享到群組。

- 架構：Vue 3 + Vite + IndexedDB（Local-First，無後端伺服器）
- 托管：GitHub Pages（免費靜態托管，HTTPS）
- 安裝：手機瀏覽器開啟網址 → 「加入主畫面」即可當 App 使用

**使用網址：** https://FatPigDash.github.io/AhhOuch_Manager/

---

## 給幹部：如何安裝到手機

**iOS（iPhone / iPad）**

1. 用 Safari 開啟上方網址
2. 點下方中間的「分享」按鈕（方框加箭頭圖示）
3. 選「加入主畫面」
4. 點「新增」

**Android**

1. 用 Chrome 開啟上方網址
2. 點右上角三點選單
3. 選「新增到主畫面」或「安裝應用程式」

安裝後資料存在手機本機，不會上傳到任何伺服器。

---

## 給開發者：版本更新流程

修改程式碼後，執行以下指令即完成部署：

```powershell
git add .
git commit -m "說明這次改了什麼"

用這個指令其他人就會套用更新版本
git push origin main
```

GitHub Actions 會自動 build 並部署到 GitHub Pages，約 **2-3 分鐘**後生效。  
幹部重新整理頁面就會看到最新版本，不需要任何額外操作。

部署狀態可在此查看：https://github.com/FatPigDash/AhhOuch_Manager/actions

---

## 本機開發

需先安裝 [Node.js 18+](https://nodejs.org/)。

```powershell
先設定路徑
cd frontend\desktop

執行指令
npm install      # 首次安裝套件
npm run dev      # 啟動開發伺服器（http://localhost:5173）
```

---

## 版次管理

修改 `app.toml` 中的版次號：

```toml
app_name = "AhhOuch_Manager"
version  = "2.1.0"
```

---

## 目錄結構

```
AhhOuch_Manager_Edit/
├─ app.toml                  軟體名稱與版次
├─ .github/workflows/
│  └─ deploy.yml             GitHub Actions 自動部署設定
└─ frontend/
   └─ desktop/               PWA 主體（Vue 3 + Vite）
      ├─ src/
      │  ├─ db.js            IndexedDB 資料層
      │  ├─ api.js           API 介面（Local-First）
      │  ├─ router.js        Vue Router（hash 模式）
      │  ├─ views/           頁面元件
      │  └─ components/      共用元件
      ├─ public/             PWA 圖示
      ├─ index.html
      └─ vite.config.js      含 PWA 設定（manifest、Service Worker）
```
