"""客人端美容師卡片資料模型 (C7/C8/C10/C11)，含簡介欄位 (C12/C14/C15)。

圖片、心得、評分為獨立資料表（image / review / template）。
封面（C8）由 CardImage.is_cover 決定，於 API 回應時計算為 cover_image，
故本表不再保存 cover_image 欄位（單一事實來源）。
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class CustomerCard(SQLModel, table=True):
    """美容師卡片：僅 title 必填即可建立 (C11)。"""

    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="board.id", index=True)
    title: str
    position: int = 0  # 板內目前顯示排序位置 (C10)
    # 手動排序快照：切到「預設」排序前保存此值，切回「手動」時據以還原 (C10)
    manual_position: int = 0
    # 簡介 (C14/C15)；收闔狀態 (C12)，預設開啟 → intro_collapsed=False
    nationality: str = ""
    intro_text: str = ""
    intro_collapsed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
