"""SQLite 連線與初始化。

init_db()：建立資料夾與資料表、把舊版「店家」系統的資料表更名為「幹部」、
移除已拆分出去的「客人」系統殘留資料表、對既有 DB 補欄位（輕量遷移）、
清除已下架平台殘留資料（LINE 發布目標）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from . import config

# check_same_thread=False：FastAPI 多執行緒存取同一 SQLite 連線需求。
engine = create_engine(
    config.database_url(),
    echo=False,
    connect_args={"check_same_thread": False},
)

# 舊版「店家」系統更名為「幹部」：資料表 storecard→cadrecard 等（保留既有資料）。
_TABLE_RENAMES: dict[str, str] = {
    "storecard": "cadrecard",
    "storecardimage": "cadrecardimage",
}

# 隨之更名的欄位：store_card_id → cadre_card_id。
_COLUMN_RENAMES: dict[str, dict[str, str]] = {
    "cadrecardimage": {"store_card_id": "cadre_card_id"},
    "scheduleentry": {"store_card_id": "cadre_card_id"},
}

# 「客人」系統已拆分為獨立軟體，移除其在本 DB 的殘留資料表。
_DROP_TABLES: tuple[str, ...] = (
    "cardimage",
    "cardreview",
    "reviewscore",
    "customercard",
    "board",
    "spastaff",
    "spa",
    "ratingtemplateitem",
    "ratingtemplate",
)

# 既有 DB 補欄位用：{資料表: {欄位: "型別 預設值"}}（於更名後執行，故用新表名）。
_COLUMN_MIGRATIONS: dict[str, dict[str, str]] = {
    "cadrecard": {
        "info_link": "TEXT DEFAULT ''",  # 美容師資訊訊息連結（自動發布時擷取）
    },
    "schedule": {
        "date": "TEXT DEFAULT ''",  # 班表日期（ISO YYYY-MM-DD）
        "footer": "TEXT DEFAULT ''",  # 結語（發布時置於最下方）
    },
}


def _table_names(conn) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
    }


def _migrate_legacy_split() -> None:
    """店家→幹部更名、移除客人系統殘留表。

    必須在 create_all 之前執行：先把 storecard 更名為 cadrecard，
    create_all 才不會另外建一個空的 cadrecard 而導致更名失敗。
    """
    with engine.connect() as conn:
        existing = _table_names(conn)
        # 1) 資料表更名（來源在、目標不在時才更名，可重複執行）
        for old, new in _TABLE_RENAMES.items():
            if old in existing and new not in existing:
                conn.execute(text(f"ALTER TABLE {old} RENAME TO {new}"))
        existing = _table_names(conn)
        # 2) 欄位更名
        for table, cols in _COLUMN_RENAMES.items():
            if table not in existing:
                continue
            colnames = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            for old, new in cols.items():
                if old in colnames and new not in colnames:
                    conn.execute(
                        text(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")
                    )
        # 3) 移除客人系統殘留表
        for table in _DROP_TABLES:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.commit()


def _migrate_columns() -> None:
    """為既有資料表補上缺少的欄位（SQLite 不支援 create_all 自動 ALTER）。"""
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


def init_db() -> None:
    """建立資料夾與所有資料表、更名舊表、移除客人殘留表、補欄位。"""
    config.ensure_data_dirs()
    from . import models  # noqa: F401  匯入以註冊 SQLModel 表格

    _migrate_legacy_split()  # 必須在 create_all 之前
    SQLModel.metadata.create_all(engine)
    _migrate_columns()
    _cleanup_legacy_data()


def get_session() -> Session:
    """FastAPI 依賴注入用的 Session 產生器。"""
    with Session(engine) as session:
        yield session
