"""進入點：啟動 FastAPI（同時是 PyInstaller 打包的進入點）。

凍結後雙擊 exe 即啟動本機伺服器並自動開啟瀏覽器。
"""
from __future__ import annotations

import threading
import webbrowser

import uvicorn

from backend import version
from backend.main import app


def _open_browser(url: str) -> None:
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()


def main() -> None:
    host = version.server_host()
    port = version.server_port()
    # 綁定 127.0.0.1 時用 localhost 開瀏覽器較直覺。
    browse_host = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
    _open_browser(f"http://{browse_host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
