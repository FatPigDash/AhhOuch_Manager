"""路徑常數與預設值。

集中處理「開發環境」與「凍結環境（PyInstaller exe）」的路徑差異：
- 靜態前端檔：開發在專案內；凍結時被打包進 sys._MEIPASS。
- DATA/：永遠放在「可寫入、使用者看得到」的位置——
    開發 → 專案根目錄；凍結 → exe 所在目錄（X6）。
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_dir() -> Path:
    """唯讀資源（前端靜態檔、app.toml）的根目錄。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def runtime_dir() -> Path:
    """可寫入資料的根目錄（DATA/ 的上層）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# --- 資料路徑 (X6) ---
DATA_DIR: Path = runtime_dir() / "DATA"
IMAGES_DIR: Path = DATA_DIR / "images"
DB_PATH: Path = DATA_DIR / "ahhouch.db"

# --- 前端靜態檔（Vue build 輸出）---
# desktop 優先；mobile 後期。打包時 dist 會被收進 resource_dir。
FRONTEND_DESKTOP_DIST: Path = resource_dir() / "frontend" / "desktop" / "dist"


def ensure_data_dirs() -> None:
    """啟動時建立 DATA/ 與 images/（X6）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def database_url() -> str:
    return f"sqlite:///{DB_PATH.as_posix()}"
