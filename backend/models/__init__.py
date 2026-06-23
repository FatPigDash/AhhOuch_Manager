"""資料模型集中匯入點。

於此 re-export 各表，讓 database.init_db() 匯入本套件即可註冊所有 SQLModel 表格。
各 Phase 在此資料夾新增模型檔並在此處補上匯入。
"""
from .cadre import CadreCard, CadreCardImage
from .publish import PublishTarget
from .schedule import Schedule, ScheduleEntry
from .text_template import TextTemplate

__all__ = [
    "CadreCard",
    "CadreCardImage",
    "Schedule",
    "ScheduleEntry",
    "TextTemplate",
    "PublishTarget",
]
