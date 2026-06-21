"""標題／結語文字模板：可儲存、選用、編輯。

標題與結語各自獨立的模板池，以 kind 區分用途：
"title"（標題）| "footer"（結語）。供班表編輯時快速套用常用文字。
"""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class TextTemplate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    kind: str = Field(index=True)  # "title" | "footer"
    name: str
    content: str = ""
    position: int = 0  # 同 kind 內的顯示順序（新增者排在最後）
