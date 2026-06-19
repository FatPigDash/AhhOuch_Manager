"""SQLite 連線與初始化。

init_db()：建立資料夾與資料表、對既有 DB 補欄位（輕量遷移）、植入預設資料
（五個預設看板於建立養身館時產生；預設評分模板於此植入）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

from . import config

# check_same_thread=False：FastAPI 多執行緒存取同一 SQLite 連線需求。
engine = create_engine(
    config.database_url(),
    echo=False,
    connect_args={"check_same_thread": False},
)

# 既有 DB 補欄位用：{資料表: {欄位: "型別 預設值"}}
_COLUMN_MIGRATIONS: dict[str, dict[str, str]] = {
    "customercard": {
        "nationality": "TEXT DEFAULT ''",
        "intro_text": "TEXT DEFAULT ''",
        "intro_collapsed": "INTEGER DEFAULT 0",
    },
}


def _migrate() -> None:
    """為既有資料表補上模型新增的欄位（SQLite 不支援 create_all 自動 ALTER）。"""
    with engine.connect() as conn:
        for table, columns in _COLUMN_MIGRATIONS.items():
            existing = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            if not existing:
                continue  # 資料表不存在（全新 DB 由 create_all 直接建好正確結構）
            for col, ddl in columns.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        conn.commit()


def _seed_defaults() -> None:
    """植入預設評分模板（若尚無任何模板）(C18)。"""
    from .models import RatingTemplate, RatingTemplateItem

    with Session(engine) as session:
        if session.exec(select(RatingTemplate)).first() is not None:
            return
        template = RatingTemplate(name="預設", position=0)
        session.add(template)
        session.commit()
        session.refresh(template)
        for i, name in enumerate(config.DEFAULT_RATING_ITEMS):
            session.add(
                RatingTemplateItem(template_id=template.id, name=name, position=i)
            )
        session.commit()


def init_db() -> None:
    """建立資料夾與所有資料表、補欄位、植入預設資料。"""
    config.ensure_data_dirs()
    from . import models  # noqa: F401  匯入以註冊 SQLModel 表格

    SQLModel.metadata.create_all(engine)
    _migrate()
    _seed_defaults()


def get_session() -> Session:
    """FastAPI 依賴注入用的 Session 產生器。"""
    with Session(engine) as session:
        yield session
