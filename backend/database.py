"""SQLite 連線與初始化。

M0 階段僅建立引擎與資料表建立流程；各模組的資料模型（spa/board/card/
review/template/schedule…）將於後續 Phase 加入 models/ 後自動被建立。
預設資料（如五個預設看板、預設評分模板）也於對應 Phase 補上。
"""
from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine

from . import config

# check_same_thread=False：FastAPI 多執行緒存取同一 SQLite 連線需求。
engine = create_engine(
    config.database_url(),
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """建立資料夾與所有資料表。匯入 models 以註冊 SQLModel 表格。"""
    config.ensure_data_dirs()
    # 匯入後 SQLModel.metadata 才會包含各表（後續 Phase 會填充 models/）。
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """FastAPI 依賴注入用的 Session 產生器。"""
    with Session(engine) as session:
        yield session
