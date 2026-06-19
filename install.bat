@echo off
REM AhhOuch 一鍵安裝環境與套件 (X4)
REM 雙擊本檔，或在終端機執行：install.bat
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   AhhOuch 安裝程式
echo ============================================
echo.

REM 確認 Python 是否存在
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.11 以上版本並勾選 "Add to PATH"。
    echo        下載：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/2] 升級 pip ...
python -m pip install --upgrade pip

echo.
echo [2/2] 安裝後端套件 ...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [錯誤] 套件安裝失敗，請檢查網路或上方訊息。
    pause
    exit /b 1
)

echo.
echo ============================================
echo   後端套件安裝完成。
echo   前端（Vue）請另執行：
echo     cd frontend\desktop
echo     npm install
echo ============================================
pause
