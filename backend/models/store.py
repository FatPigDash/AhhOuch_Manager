"""店家端資料模型：美容師資訊卡片與其圖片 (S2/S3/S4)。"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class StoreCard(SQLModel, table=True):
    """美容師資訊卡片：名字自輸(文字或編號)，完整/簡短介紹 (S2/S4)。"""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    full_intro: str = ""   # 完整介紹 (S4)
    short_intro: str = ""  # 簡短介紹 (S4)
    created_at: datetime = Field(default_factory=datetime.now)
    # 排序固定為名字（數字自然 + 其餘 Unicode），不再保存手動排序位置。


class StoreCardImage(SQLModel, table=True):
    """資訊卡片圖片：多張、可設封面、非必填 (S3)。"""

    id: int | None = Field(default=None, primary_key=True)
    store_card_id: int = Field(foreign_key="storecard.id", index=True)
    filename: str
    is_cover: bool = False
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
