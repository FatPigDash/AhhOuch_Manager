"""卡片簡介圖片 (C13)。

實體檔存於 DATA/images/，DB 僅存檔名；is_cover 標記封面（C8）。
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class CardImage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="customercard.id", index=True)
    filename: str  # DATA/images/ 內的檔名
    is_cover: bool = False
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
