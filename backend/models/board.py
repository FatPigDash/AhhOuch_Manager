"""看板資料模型 (C4/C5/C6)。"""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class Board(SQLModel, table=True):
    """看板：隸屬某養身館，可增減、改名、排序 (C5)。

    sort_mode 決定板內卡片的排列方式 (C10)：
      "unicode" → 依卡片標題的標準 Unicode 排序（預設）
      "manual"  → 依使用者手動拖曳的 position 排序
    """

    id: int | None = Field(default=None, primary_key=True)
    spa_id: int = Field(foreign_key="spa.id", index=True)
    name: str
    position: int = 0  # 由左至右的排序位置
    sort_mode: str = "unicode"  # "unicode" | "manual"
