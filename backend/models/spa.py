"""養身館資料模型 (C1/C2)。"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class Spa(SQLModel, table=True):
    """養身館：僅 name 必填即可建立 (C1)；含地址 (C2)。

    幹部改為一對多（見 SpaStaff），可有多位且各自帶聯絡資訊。
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
    address: str = ""
    position: int = 0  # 列表中的排序位置（可拖曳調整 C3）
    created_at: datetime = Field(default_factory=datetime.now)


class SpaStaff(SQLModel, table=True):
    """養身館的幹部 (C2)：隸屬某養身館，可有多位，各含聯絡資訊。"""

    id: int | None = Field(default=None, primary_key=True)
    spa_id: int = Field(foreign_key="spa.id", index=True)
    name: str
    contact: str = ""  # 聯絡資訊
    position: int = 0  # 顯示順序
