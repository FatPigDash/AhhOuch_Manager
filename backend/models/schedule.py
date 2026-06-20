"""班表資料模型 (S6–S12)。

班表本身即「草稿」：建立後持久保存，可反覆編輯與再發布 (S12)。
每位出勤人員為一筆 ScheduleEntry，來源為店家資訊卡片 (S7/S8)。
時段清單以 JSON 字串保存於 slots_json，API 以字串陣列進出 (S9/S10)。
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class Schedule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = ""  # 標題，可多行 (S6)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScheduleEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    schedule_id: int = Field(foreign_key="schedule.id", index=True)
    store_card_id: int = Field(foreign_key="storecard.id", index=True)
    time_mode: str = "auto"  # "manual" | "auto"；新出勤人員預設自動換算
    auto_start: str = ""        # 自動換算的上班開始時間 (S10)
    slots_json: str = "[]"      # 顯示用時段清單（JSON 字串）
    # 出勤時段固定依名字排序（同出勤人員），不保留手動拖曳排序。
