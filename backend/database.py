"""SQLite 連線與初始化。

init_db()：建立資料夾與資料表、對既有 DB 補欄位（輕量遷移）、清除已下架平台
殘留資料（LINE 發布目標）、植入預設資料（五個預設看板於建立養身館時產生；
預設評分模板於此植入）。
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
        "manual_position": "INTEGER DEFAULT 0",
    },
    "ratingtemplateitem": {
        "item_type": "TEXT DEFAULT 'score'",
    },
    "reviewscore": {
        "item_type": "TEXT DEFAULT 'score'",
        "yesno_value": "TEXT DEFAULT ''",
    },
}

# 既有 DB 移除欄位用：{資料表: [欄位, ...]}（模型已不再使用，需從舊 DB 清除，
# 否則殘留的 NOT NULL 欄位會讓新版的 INSERT 失敗）。SQLite 3.35+ 支援 DROP COLUMN。
_DROP_COLUMNS: dict[str, list[str]] = {
    "storecard": ["position"],  # 排序改為依名字計算，不再保存手動排序位置
    "scheduleentry": ["position"],  # 出勤時段改依名字排序，不保留手動拖曳排序
}


def _migrate() -> None:
    """為既有資料表補上/移除欄位（SQLite 不支援 create_all 自動 ALTER）。"""
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
                    # 新增的手動排序快照欄位以既有 position 回填，避免既有卡片排序遺失
                    if table == "customercard" and col == "manual_position":
                        conn.execute(
                            text("UPDATE customercard SET manual_position = position")
                        )
        for table, columns in _DROP_COLUMNS.items():
            existing = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            if not existing:
                continue
            for col in columns:
                if col in existing:
                    conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {col}"))
        conn.commit()


def _cleanup_legacy_data() -> None:
    """移除已下架平台的殘留資料：LINE 發布目標（平台選項已移除，不讓使用者看到）。"""
    with engine.connect() as conn:
        existing = {
            row[1] for row in conn.execute(text("PRAGMA table_info(publishtarget)"))
        }
        if not existing:
            return  # 資料表不存在（全新 DB 無殘留資料）
        conn.execute(text("DELETE FROM publishtarget WHERE platform = 'line'"))
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
    _cleanup_legacy_data()
    _seed_defaults()


def get_session() -> Session:
    """FastAPI 依賴注入用的 Session 產生器。"""
    with Session(engine) as session:
        yield session
