"""社群發布派送服務 (P1)。

依平台把文字 / 圖片推送到目標。Telegram 為實際實作（用標準函式庫 urllib，
免額外套件）；填入有效權杖與目標 ID 後即可運作。X 目前僅列為可選平台，
自動發送尚未支援（發文需 OAuth 授權），選用時請手動複製貼上。

自動發布支援圖片：選 1 張用 sendPhoto、多張用 sendMediaGroup（相簿），文字當作圖片
的說明文字（caption）一起送；文字超過 caption 上限時，改成圖片 + 純文字兩則發送。

send_card 會回傳這次發布訊息的「訊息連結」（僅超級群組/頻道或公開群組取得得到），
供把名字做成超連結用（班表發布）。send_text 可帶 parse_mode="HTML" 送出含超連結的內文。

平台順序即為前端下拉選單順序，第一個為預設值（Telegram）。

回傳 (ok, message)；ok=False 時 message 為錯誤說明（供前端顯示）。
"""
from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
import uuid

# 順序＝下拉選單順序，第一個為預設。x 僅列為選項，send_text 不實作（會回「尚未支援」）。
SUPPORTED_PLATFORMS = ("telegram", "x")

# Telegram 限制：圖片說明文字最長 1024 字；相簿一次 2–10 張。
TELEGRAM_CAPTION_MAX = 1024
TELEGRAM_MEDIA_GROUP_MAX = 10


def _do(req: urllib.request.Request) -> tuple[bool, str, object | None]:
    """送出請求，回傳 (ok, message, result)。result 為回應 JSON 的 result 欄位（或 None）。"""
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "ignore")
        try:
            result = json.loads(raw).get("result")
        except (ValueError, AttributeError):
            result = None
        return True, "HTTP 200", result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        return False, f"HTTP {e.code}：{body[:300]}", None
    except urllib.error.URLError as e:
        return False, f"連線失敗：{e.reason}", None


def _post_json(url: str, payload: dict, headers: dict) -> tuple[bool, str, object | None]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    return _do(req)


def _post_multipart(
    url: str, fields: dict[str, str], files: list[tuple[str, str, bytes]]
) -> tuple[bool, str, object | None]:
    """送出 multipart/form-data（供圖片上傳）。files: (欄位名, 檔名, 內容)。"""
    boundary = "----AhhOuch" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    for name, filename, content in files:
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body += f"--{boundary}\r\n".encode()
        body += (
            f'Content-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\n'
        ).encode()
        body += f"Content-Type: {ctype}\r\n\r\n".encode()
        body += content
        body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    return _do(req)


def telegram_message_link(result: object) -> str | None:
    """由 Telegram 回應算出該訊息的連結。

    僅「超級群組 / 頻道」或「有 username 的公開群組」可組出連結；
    基本群組 / 私訊沒有訊息連結，回 None。sendMediaGroup 回傳陣列，取第一則。
    """
    if isinstance(result, list):
        result = result[0] if result else None
    if not isinstance(result, dict):
        return None
    msg_id = result.get("message_id")
    if not msg_id:
        return None
    chat = result.get("chat") or {}
    username = chat.get("username")
    if username:
        return f"https://t.me/{username}/{msg_id}"
    chat_id = chat.get("id")
    if chat.get("type") in ("supergroup", "channel") and isinstance(chat_id, int):
        sid = str(chat_id)
        if sid.startswith("-100"):
            return f"https://t.me/c/{sid[4:]}/{msg_id}"
    return None


def send_text(
    platform: str, token: str, target_id: str, text: str, parse_mode: str | None = None
) -> tuple[bool, str]:
    platform = (platform or "").lower()
    if not token or not target_id:
        return False, "尚未設定權杖或目標 ID"

    if platform == "telegram":
        payload = {"chat_id": target_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        ok, msg, _ = _post_json(
            f"https://api.telegram.org/bot{token}/sendMessage", payload, {}
        )
        return ok, msg
    if platform == "x":
        return False, "X 自動發送尚未支援，請手動複製文字貼到 X"
    return False, f"尚未支援的平台：{platform or '(未指定)'}"


def send_card(
    platform: str,
    token: str,
    target_id: str,
    images: list[tuple[str, bytes]],
    text: str,
) -> tuple[bool, str, str | None]:
    """發布美容師資訊卡片：images 為 (檔名, 內容) 清單，可空；text 為文字，可空。

    無圖時送純文字；有圖時文字當圖片說明文字一起送（過長則圖片+文字兩則）。
    回傳 (ok, message, link)；link 為這次發布訊息的連結（可能為 None）。
    """
    platform = (platform or "").lower()
    if not token or not target_id:
        return False, "尚未設定權杖或目標 ID", None

    if platform == "telegram":
        return _telegram_send_card(token, target_id, images, text)
    if platform == "x":
        return False, "X 自動發送尚未支援，請手動複製貼到 X", None
    return False, f"尚未支援的平台：{platform or '(未指定)'}", None


def _telegram_send_card(
    token: str, target_id: str, images: list[tuple[str, bytes]], text: str
) -> tuple[bool, str, str | None]:
    base = f"https://api.telegram.org/bot{token}"
    text = text or ""
    if len(images) > TELEGRAM_MEDIA_GROUP_MAX:
        return False, f"一次最多發送 {TELEGRAM_MEDIA_GROUP_MAX} 張圖片", None

    if not images:
        ok, msg, result = _post_json(
            f"{base}/sendMessage", {"chat_id": target_id, "text": text}, {}
        )
        return ok, msg, (telegram_message_link(result) if ok else None)

    # 文字未超過上限才當圖片說明文字；否則圖片送完再補一則純文字。
    caption_inline = bool(text) and len(text) <= TELEGRAM_CAPTION_MAX
    caption = text if caption_inline else ""

    if len(images) == 1:
        filename, content = images[0]
        fields = {"chat_id": target_id}
        if caption:
            fields["caption"] = caption
        ok, msg, result = _post_multipart(
            f"{base}/sendPhoto", fields, [("photo", filename, content)]
        )
    else:
        media = []
        files = []
        for i, (filename, content) in enumerate(images):
            key = f"file{i}"
            item = {"type": "photo", "media": f"attach://{key}"}
            if i == 0 and caption:
                item["caption"] = caption
            media.append(item)
            files.append((key, filename, content))
        ok, msg, result = _post_multipart(
            f"{base}/sendMediaGroup",
            {"chat_id": target_id, "media": json.dumps(media, ensure_ascii=False)},
            files,
        )

    if not ok:
        return ok, msg, None
    link = telegram_message_link(result)
    # 文字過長：圖片送出後補送純文字（連結仍以圖片那則為準）。
    if text and not caption_inline:
        ok2, msg2, _ = _post_json(
            f"{base}/sendMessage", {"chat_id": target_id, "text": text}, {}
        )
        if not ok2:
            return ok2, msg2, link
    return ok, msg, link
