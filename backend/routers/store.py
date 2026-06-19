"""店家 API（美容師資訊卡片 / 班表 / 草稿）。

對應需求 S1–S12。M0 階段為空殼，端點將於 M4 起逐步加入。
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/store", tags=["store"])
