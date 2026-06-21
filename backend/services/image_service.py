"""圖片儲存服務 (S3/C13)。

支援兩種來源：
  - 檔案上傳（bytes）
  - 剪貼簿貼上（base64 / data URL）—— 對應 PoC 6.1
以 Pillow 驗證確為圖片後存入 DATA/images/，回傳檔名（DB 僅存檔名）。
"""
from __future__ import annotations

import base64
import uuid
from io import BytesIO

from PIL import Image

from .. import config

_EXT_BY_FORMAT = {
    "JPEG": "jpg",
    "PNG": "png",
    "GIF": "gif",
    "WEBP": "webp",
    "BMP": "bmp",
}


def save_image_bytes(data: bytes) -> str:
    """驗證並存檔，回傳檔名。非圖片會丟出例外。"""
    img = Image.open(BytesIO(data))
    img.load()  # 觸發實際解碼以驗證
    fmt = (img.format or "PNG").upper()
    ext = _EXT_BY_FORMAT.get(fmt, "png")
    config.ensure_data_dirs()
    filename = f"{uuid.uuid4().hex}.{ext}"
    img.save(config.IMAGES_DIR / filename)
    return filename


def save_data_url(data_url: str) -> str:
    """處理剪貼簿貼上的 base64（可含 data:image/...;base64, 前綴）。"""
    payload = data_url.split(",", 1)[1] if "," in data_url else data_url
    return save_image_bytes(base64.b64decode(payload))


def delete_image_file(filename: str) -> None:
    path = config.IMAGES_DIR / filename
    if path.exists():
        path.unlink()


def image_path(filename: str):
    """圖片在磁碟上的完整路徑。"""
    return config.IMAGES_DIR / filename


def read_image_bytes(filename: str) -> bytes:
    """讀取圖片原始位元組（供自動發布上傳用）。"""
    return image_path(filename).read_bytes()


def image_url(filename: str) -> str:
    """前端可存取的 URL（由 main.py 將 DATA/images 掛載於 /images）。"""
    return f"/images/{filename}"
