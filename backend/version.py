"""讀取根目錄 app.toml，提供軟體名稱／版次／伺服器設定的唯一存取點 (X3)。

凍結（PyInstaller exe）與開發環境皆可正確定位 app.toml：
- 開發：專案根目錄。
- 凍結：app.toml 透過 --add-data 打包進臨時目錄 (sys._MEIPASS)。
"""
from __future__ import annotations

import sys
import tomllib
from functools import lru_cache
from pathlib import Path


def _app_toml_path() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller：資源被解壓到 _MEIPASS
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        # 開發：backend/ 的上一層即專案根目錄
        base = Path(__file__).resolve().parent.parent
    return base / "app.toml"


@lru_cache(maxsize=1)
def _load() -> dict:
    path = _app_toml_path()
    if not path.exists():
        raise FileNotFoundError(f"找不到設定檔 app.toml：{path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def app_name() -> str:
    return str(_load().get("app_name", "App"))


def version() -> str:
    return str(_load().get("version", "0.0.0"))


def full_title() -> str:
    """例如：AhhOuch v1.0.0"""
    return f"{app_name()} v{version()}"


def server_host() -> str:
    return str(_load().get("server", {}).get("host", "127.0.0.1"))


def server_port() -> int:
    return int(_load().get("server", {}).get("port", 8000))


def build_filename() -> str:
    """打包輸出的 exe 檔名（不含副檔名），例如 AhhOuch_v1.0.0"""
    return f"{app_name()}_v{version()}"
