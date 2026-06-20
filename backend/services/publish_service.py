"""社群發布派送服務 (P1)。

依平台把純文字推送到目標。Telegram 為實際實作（用標準函式庫 urllib，
免額外套件）；填入有效權杖與目標 ID 後即可運作。X 目前僅列為可選平台，
自動發送尚未支援（發文需 OAuth 授權），選用時請手動複製貼上。排版圖片由前端
html2canvas 產生供手動張貼，API 自動發布此階段先支援文字。

平台順序即為前端下拉選單順序，第一個為預設值（Telegram）。

回傳 (ok, message)；ok=False 時 message 為錯誤說明（供前端顯示）。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

# 順序＝下拉選單順序，第一個為預設。x 僅列為選項，send_text 不實作（會回「尚未支援」）。
SUPPORTED_PLATFORMS = ("telegram", "x")


def _post_json(url: str, payload: dict, headers: dict) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        return False, f"HTTP {e.code}：{body[:300]}"
    except urllib.error.URLError as e:
        return False, f"連線失敗：{e.reason}"


def send_text(platform: str, token: str, target_id: str, text: str) -> tuple[bool, str]:
    platform = (platform or "").lower()
    if not token or not target_id:
        return False, "尚未設定權杖或目標 ID"

    if platform == "telegram":
        return _post_json(
            f"https://api.telegram.org/bot{token}/sendMessage",
            {"chat_id": target_id, "text": text},
            {},
        )
    if platform == "x":
        return False, "X 自動發送尚未支援，請手動複製文字貼到 X"
    return False, f"尚未支援的平台：{platform or '(未指定)'}"
