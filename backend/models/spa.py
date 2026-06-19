"""養身館資料模型 (C1/C2)。"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class Spa(SQLModel, table=True):
    """養身館：僅 name 必填即可建立 (C1)；含地址、幹部 (C2)。"""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    address: str = ""
    staff: str = ""  # 幹部
    created_at: datetime = Field(default_factory=datetime.now)
