"""資料模型集中匯入點。

於此 re-export 各表，讓 database.init_db() 匯入本套件即可註冊所有 SQLModel 表格。
各 Phase 在此資料夾新增模型檔並在此處補上匯入。
"""
from .board import Board
from .card import CustomerCard
from .image import CardImage
from .publish import PublishTarget
from .review import CardReview, ReviewScore
from .schedule import Schedule, ScheduleEntry
from .spa import Spa
from .store import StoreCard, StoreCardImage
from .template import RatingTemplate, RatingTemplateItem
from .text_template import TextTemplate

__all__ = [
    "Spa",
    "Board",
    "CustomerCard",
    "CardImage",
    "CardReview",
    "ReviewScore",
    "RatingTemplate",
    "RatingTemplateItem",
    "StoreCard",
    "StoreCardImage",
    "Schedule",
    "ScheduleEntry",
    "TextTemplate",
    "PublishTarget",
]
