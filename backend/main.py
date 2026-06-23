"""FastAPI 應用程式：REST API + 靜態前端服務。

- 啟動時建立 DATA/ 並初始化資料庫。
- /api/meta：回傳軟體名稱與版次（前端標題、關於頁用）。
- 掛載 Vue build 後的靜態檔；尚未 build 時顯示提示頁，方便 M0 先驗證後端可啟動。
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config, version
from .database import init_db
from .routers import cadre, publish


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_data_dirs()
    init_db()
    yield


app = FastAPI(title=version.app_name(), version=version.version(), lifespan=lifespan)

app.include_router(cadre.router)
app.include_router(publish.router)


@app.get("/api/meta")
def meta() -> dict:
    """軟體中繼資訊（唯一事實來源 app.toml）。"""
    return {
        "app_name": version.app_name(),
        "version": version.version(),
        "title": version.full_title(),
    }


def _mount_images() -> None:
    """將 DATA/images 掛載於 /images，供前端顯示上傳/貼上的圖片 (C13)。"""
    config.ensure_data_dirs()
    app.mount(
        "/images", StaticFiles(directory=str(config.IMAGES_DIR)), name="images"
    )


def _mount_frontend() -> None:
    """掛載 Vue build 輸出；若尚未 build 則提供提示頁。"""
    dist = config.FRONTEND_DESKTOP_DIST
    if dist.exists() and (dist / "index.html").exists():
        # html=True：未命中的路徑回退到 index.html，支援前端路由。
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse)
        def placeholder() -> str:
            return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>{version.full_title()}</title></head>
<body style="font-family:sans-serif;max-width:640px;margin:80px auto;line-height:1.7">
<h1>{version.full_title()}</h1>
<p>後端已啟動 ✅　前端尚未建置。</p>
<p>請在 <code>frontend/desktop/</code> 執行 <code>npm install &amp;&amp; npm run build</code>，
重新整理本頁即可看到 Vue 介面。</p>
<p>API 文件：<a href="/docs">/docs</a>　中繼資訊：<a href="/api/meta">/api/meta</a></p>
</body></html>"""


# 掛載順序：/images 與 API 路由都必須在 "/" 之前（StaticFiles 掛在 "/" 會吃掉其餘路徑）。
_mount_images()
_mount_frontend()
