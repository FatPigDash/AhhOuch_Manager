"""評分模板 (C17/C18/C20)。

多組模板、可命名、項目可增刪改。預設模板項目見 config.DEFAULT_RATING_ITEMS。
"""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class RatingTemplate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    position: int = 0


class RatingTemplateItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="ratingtemplate.id", index=True)
    name: str
    position: int = 0
    # 項目類型："score"（0~10 滑桿）| "yesno"（有/無）
    item_type: str = "score"
