"""心得與評分 (C16/C19/C21/C22)。

一張卡片可有多組心得；每組心得套用某模板，並把模板項目「快照」成 ReviewScore，
日後模板項目增刪改不影響既有心得。分數 0~10，每項附補充文字。
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class CardReview(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="customercard.id", index=True)
    date: str = ""  # ISO yyyy-mm-dd (C16)
    template_id: int | None = None  # 套用的模板 (C20)；快照已存於 scores
    text: str = ""  # 心得文字說明 (C21)
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class ReviewScore(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="cardreview.id", index=True)
    item_name: str  # 項目名稱（自模板快照）
    score: int = 0  # 0~10 (C19)
    note: str = ""  # 補充文字 (C19)
    position: int = 0
