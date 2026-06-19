@echo off
REM AhhOuch 測試階段啟動 (M0)
REM 以開發模式啟動後端；若前端已 build，會一併提供 Vue 介面。
chcp 65001 >nul
cd /d "%~dp0"

echo 啟動 AhhOuch（開發模式）...
echo 啟動後會自動開啟瀏覽器；關閉本視窗即停止伺服器。
echo.
python run.py
pause
