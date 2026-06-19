"""社群發布目標設定 (P1)。

每筆代表一個「可一鍵發布的去處」：平台 + 權杖 + 目標 ID（如 LINE 群組 ID）。
權杖以明文存於本機 SQLite（單機單人情境）；日後多使用者需加密與權限控管。
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class PublishTarget(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str                      # 顯示名稱，如「工作室 LINE 群」
    platform: str = ""             # "line" | "telegram" | ...（空=尚未指定）
    token: str = ""                # channel access token / bot token
    target_id: str = ""            # 推送目標（LINE groupId / Telegram chat_id）
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
