"""社群發布派送服務 (P1)。

依平台把純文字推送到目標。LINE / Telegram 為實際實作（用標準函式庫 urllib，
免額外套件）；填入有效權杖與目標 ID 後即可運作。排版圖片由前端 html2canvas
產生供手動張貼，API 自動發布此階段先支援文字。

回傳 (ok, message)；ok=False 時 message 為錯誤說明（供前端顯示）。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

SUPPORTED_PLATFORMS = ("line", "telegram")


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

    if platform == "line":
        return _post_json(
            "https://api.line.me/v2/bot/message/push",
            {"to": target_id, "messages": [{"type": "text", "text": text}]},
            {"Authorization": f"Bearer {token}"},
        )
    if platform == "telegram":
        return _post_json(
            f"https://api.telegram.org/bot{token}/sendMessage",
            {"chat_id": target_id, "text": text},
            {},
        )
    return False, f"尚未支援的平台：{platform or '(未指定)'}"
