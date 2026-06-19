"""客人端美容師卡片資料模型 (C7/C8/C10/C11)。

M1 僅含基礎欄位（標題、封面、排序位置）。簡介與心得（C12–C22）為獨立資料表，
於 M3 加入；封面圖的實際上傳（C13）於 M3 由 image_service 處理。
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class CustomerCard(SQLModel, table=True):
    """美容師卡片：僅 title 必填即可建立 (C11)；看板上僅顯示標題與封面 (C8)。"""

    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="board.id", index=True)
    title: str
    cover_image: str | None = None  # 封面圖路徑 (M3 由 image_service 設定)
    position: int = 0  # 板內手動排序位置 (C10)；看板 sort_mode="manual" 時生效
    created_at: datetime = Field(default_factory=datetime.now)
