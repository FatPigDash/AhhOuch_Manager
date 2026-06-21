"""店家 API（美容師資訊卡片 / 班表 / 草稿）。

對應需求 S1–S12。
M4 範圍：資訊卡片 CRUD (S2/S4)、圖片(上傳/貼上/封面，S3)、發布純文字 (S5)。
發布的「排版圖片」由前端以 html2canvas 產生（PoC 6.2 選定方案 A）。
班表與草稿 (S6–S12) 於 M5 加入。
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    PublishTarget,
    Schedule,
    ScheduleEntry,
    StoreCard,
    StoreCardImage,
    TextTemplate,
)
from ..services import image_service, publish_service, shift_calculator
from ..services.time_utils import normalize_time

router = APIRouter(prefix="/api/store", tags=["store"])


# --------------------------------------------------------------------------
# 輸入結構
# --------------------------------------------------------------------------
class StoreCardCreate(BaseModel):
    name: str


class StoreCardUpdate(BaseModel):
    name: str | None = None
    full_intro: str | None = None
    short_intro: str | None = None
    info_link: str | None = None


class PasteImage(BaseModel):
    data_url: str


class PublishCard(BaseModel):
    target_id: int            # PublishTarget 的資料庫 id
    image_ids: list[int] = []  # 要發布的圖片 id（複選；空＝不附圖）
    text: str = ""             # 已組好的發布文字（名字 + 勾選的介紹）


class ScheduleCreate(BaseModel):
    title: str = ""


class ScheduleUpdate(BaseModel):
    title: str | None = None
    footer: str | None = None  # 結語，發布時置於最下方
    date: str | None = None  # ISO "YYYY-MM-DD"，空字串＝清除日期


class PublishSchedule(BaseModel):
    target_id: int  # PublishTarget 的資料庫 id


class EntryCreate(BaseModel):
    store_card_id: int


class EntryUpdate(BaseModel):
    time_mode: str | None = None  # "manual" | "auto"
    auto_start: str | None = None
    slots: list[str] | None = None  # 顯示用時段清單（會正規化）


# --------------------------------------------------------------------------
# 共用工具
# --------------------------------------------------------------------------
def _get_or_404(session: Session, model, obj_id: int, label: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"找不到{label} (id={obj_id})")
    return obj


def _next_position(session: Session, model, **filters) -> int:
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    items = session.exec(stmt).all()
    return (max((i.position for i in items), default=-1)) + 1


def _images(session: Session, card_id: int) -> list[StoreCardImage]:
    return session.exec(
        select(StoreCardImage)
        .where(StoreCardImage.store_card_id == card_id)
        .order_by(StoreCardImage.position)
    ).all()


def _cover_url(session: Session, card_id: int) -> str | None:
    imgs = _images(session, card_id)
    if not imgs:
        return None
    cover = next((im for im in imgs if im.is_cover), imgs[0])
    return image_service.image_url(cover.filename)


def _serialize_card(session: Session, card: StoreCard) -> dict:
    images = [
        {**im.model_dump(), "url": image_service.image_url(im.filename)}
        for im in _images(session, card.id)
    ]
    return {
        **card.model_dump(),
        "cover_image": _cover_url(session, card.id),
        "images": images,
    }


# --------------------------------------------------------------------------
# 資訊卡片 CRUD (S2/S4)
# --------------------------------------------------------------------------
_DIGITS_RE = re.compile(r"(\d+)")


def _name_sort_key(name: str) -> list[tuple[int, int, str]]:
    """名字排序鍵（預設排序，不提供手動排序）。

    將名字切成「數字段」與「非數字段」交錯比較：
    - 數字段比數值 → 純數字 / #純數字 自然排序（#5 < #21 < #199）。
    - 非數字段比 Unicode 碼位 → 中文 / 英文 / 日文 標準 Unicode 排序。
    元素統一為 (型別旗標, 數值, 字串)，避免 int 與 str 直接比較出錯。
    """
    key: list[tuple[int, int, str]] = []
    for i, part in enumerate(_DIGITS_RE.split(name)):
        if i % 2 == 1:            # 奇數索引為數字段
            key.append((0, int(part), ""))
        elif part:                # 非空的非數字段
            key.append((1, 0, part))
    return key


@router.get("/cards")
def list_cards(session: Session = Depends(get_session)) -> list[dict]:
    # 預設排序、不提供手動排序：數字採自然排序、其餘採標準 Unicode 排序。
    # 以 Python 排序，確保結果不受 SQLite collation 影響。
    cards = session.exec(select(StoreCard)).all()
    cards.sort(key=lambda c: _name_sort_key(c.name))
    return [_serialize_card(session, c) for c in cards]


@router.post("/cards", status_code=201)
def create_card(
    data: StoreCardCreate, session: Session = Depends(get_session)
) -> dict:
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="名字不可空白")
    card = StoreCard(name=name)
    session.add(card)
    session.commit()
    session.refresh(card)
    return _serialize_card(session, card)


@router.get("/cards/{card_id}")
def get_card(card_id: int, session: Session = Depends(get_session)) -> dict:
    card = _get_or_404(session, StoreCard, card_id, "資訊卡片")
    return _serialize_card(session, card)


@router.patch("/cards/{card_id}")
def update_card(
    card_id: int, data: StoreCardUpdate, session: Session = Depends(get_session)
) -> dict:
    card = _get_or_404(session, StoreCard, card_id, "資訊卡片")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="名字不可空白")
        card.name = name
    if data.full_intro is not None:
        card.full_intro = data.full_intro
    if data.short_intro is not None:
        card.short_intro = data.short_intro
    if data.info_link is not None:
        card.info_link = data.info_link.strip()
    session.add(card)
    session.commit()
    session.refresh(card)
    return _serialize_card(session, card)


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, session: Session = Depends(get_session)) -> None:
    card = _get_or_404(session, StoreCard, card_id, "資訊卡片")
    for im in _images(session, card_id):
        image_service.delete_image_file(im.filename)
        session.delete(im)
    session.delete(card)
    session.commit()


# --------------------------------------------------------------------------
# 圖片（上傳 / 貼上 / 封面 / 刪除，S3）
# --------------------------------------------------------------------------
def _add_image(session: Session, card_id: int, filename: str) -> dict:
    existing = _images(session, card_id)
    image = StoreCardImage(
        store_card_id=card_id,
        filename=filename,
        is_cover=(len(existing) == 0),
        position=_next_position(session, StoreCardImage, store_card_id=card_id),
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return {**image.model_dump(), "url": image_service.image_url(image.filename)}


@router.post("/cards/{card_id}/images", status_code=201)
async def upload_image(
    card_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    _get_or_404(session, StoreCard, card_id, "資訊卡片")
    data = await file.read()
    try:
        filename = image_service.save_image_bytes(data)
    except Exception:
        raise HTTPException(status_code=422, detail="檔案不是有效的圖片")
    return _add_image(session, card_id, filename)


@router.post("/cards/{card_id}/images/paste", status_code=201)
def paste_image(
    card_id: int, data: PasteImage, session: Session = Depends(get_session)
) -> dict:
    _get_or_404(session, StoreCard, card_id, "資訊卡片")
    try:
        filename = image_service.save_data_url(data.data_url)
    except Exception:
        raise HTTPException(status_code=422, detail="貼上的內容不是有效的圖片")
    return _add_image(session, card_id, filename)


@router.post("/images/{image_id}/cover")
def set_cover(image_id: int, session: Session = Depends(get_session)) -> dict:
    image = _get_or_404(session, StoreCardImage, image_id, "圖片")
    for other in _images(session, image.store_card_id):
        other.is_cover = other.id == image_id
        session.add(other)
    session.commit()
    return {"ok": True}


@router.delete("/images/{image_id}", status_code=204)
def delete_image(image_id: int, session: Session = Depends(get_session)) -> None:
    image = _get_or_404(session, StoreCardImage, image_id, "圖片")
    card_id, was_cover = image.store_card_id, image.is_cover
    image_service.delete_image_file(image.filename)
    session.delete(image)
    session.commit()
    if was_cover:
        remaining = session.exec(
            select(StoreCardImage)
            .where(StoreCardImage.store_card_id == card_id)
            .order_by(StoreCardImage.position)
        ).first()
        if remaining:
            remaining.is_cover = True
            session.add(remaining)
            session.commit()


# --------------------------------------------------------------------------
# 發布純文字 (S5)；排版圖片由前端 html2canvas 產生
# --------------------------------------------------------------------------
@router.get("/cards/{card_id}/publish-text")
def publish_text(
    card_id: int, variant: str = "full", session: Session = Depends(get_session)
) -> dict:
    """產生可貼到群組的純文字。variant: full=完整介紹、short=簡短介紹 (S5)。"""
    card = _get_or_404(session, StoreCard, card_id, "資訊卡片")
    if variant not in ("full", "short"):
        raise HTTPException(status_code=422, detail="variant 須為 full 或 short")
    intro = card.full_intro if variant == "full" else card.short_intro
    lines = [card.name]
    if intro.strip():
        lines.append(intro.strip())
    return {"variant": variant, "text": "\n".join(lines)}


@router.post("/cards/{card_id}/publish")
def publish_card(
    card_id: int, data: PublishCard, session: Session = Depends(get_session)
) -> dict:
    """自動發布卡片到發布目標：可附使用者勾選的圖片 + 文字（S5/P1）。

    發布成功且取得訊息連結時，自動把連結寫回卡片 info_link（覆寫舊值），
    供之後發布班表時把名字做成超連結。
    """
    card = _get_or_404(session, StoreCard, card_id, "資訊卡片")
    target = _get_or_404(session, PublishTarget, data.target_id, "發布目標")
    if not target.enabled:
        raise HTTPException(status_code=422, detail="此發布目標已停用")

    # 僅接受屬於此卡片的圖片；依卡片內既有順序（position）發送。
    imgs = _images(session, card_id)
    valid_ids = {im.id for im in imgs}
    missing = [iid for iid in data.image_ids if iid not in valid_ids]
    if missing:
        raise HTTPException(status_code=422, detail=f"圖片不屬於此卡片 (id={missing[0]})")
    wanted = set(data.image_ids)
    selected = [
        (im.filename, image_service.read_image_bytes(im.filename))
        for im in imgs
        if im.id in wanted
    ]

    text = data.text.strip()
    if not selected and not text:
        raise HTTPException(status_code=422, detail="沒有要發布的內容")

    ok, message, link = publish_service.send_card(
        target.platform, target.token, target.target_id, selected, text
    )
    if not ok:
        raise HTTPException(status_code=502, detail=f"發布失敗：{message}")
    if link:
        card.info_link = link
        session.add(card)
        session.commit()
    return {"ok": True, "message": message, "link": link}


# ==========================================================================
# 班表 (S6–S12)
# ==========================================================================
def _entry_slots(entry: ScheduleEntry) -> list[str]:
    try:
        return json.loads(entry.slots_json)
    except (ValueError, TypeError):
        return []


# datetime.weekday(): 週一=0 … 週日=6
_WEEKDAY_TW = "一二三四五六日"


def _format_date(iso: str) -> str:
    """把 ISO 日期 "2026-06-21" 格式化為 "2026/06/21 (日)"；空或無法解析則回原值/空字串。"""
    iso = (iso or "").strip()
    if not iso:
        return ""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return iso
    return f"{d.year}/{d.month:02d}/{d.day:02d} ({_WEEKDAY_TW[d.weekday()]})"


def _serialize_entry(session: Session, entry: ScheduleEntry) -> dict:
    card = session.get(StoreCard, entry.store_card_id)
    return {
        **entry.model_dump(),
        "slots": _entry_slots(entry),
        "name": card.name if card else "(已刪除卡片)",
        "short_intro": card.short_intro if card else "",
        "cover_image": _cover_url(session, card.id) if card else None,
    }


def _serialize_schedule(session: Session, schedule: Schedule) -> dict:
    entries = session.exec(
        select(ScheduleEntry)
        .where(ScheduleEntry.schedule_id == schedule.id)
        .order_by(ScheduleEntry.id)
    ).all()
    serialized = [_serialize_entry(session, e) for e in entries]
    # 出勤時段沿用與出勤人員相同的名字排序（數字自然 + 其餘 Unicode）。
    serialized.sort(key=lambda e: _name_sort_key(e["name"]))
    return {
        **schedule.model_dump(),
        "entries": serialized,
    }


@router.get("/schedules")
def list_schedules(session: Session = Depends(get_session)) -> list[dict]:
    schedules = session.exec(
        select(Schedule).order_by(Schedule.updated_at.desc())
    ).all()
    # 列表僅需基本資訊與人數
    out = []
    for s in schedules:
        count = len(
            session.exec(
                select(ScheduleEntry).where(ScheduleEntry.schedule_id == s.id)
            ).all()
        )
        out.append({**s.model_dump(), "entry_count": count})
    return out


@router.post("/schedules", status_code=201)
def create_schedule(
    data: ScheduleCreate, session: Session = Depends(get_session)
) -> dict:
    schedule = Schedule(title=data.title)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return _serialize_schedule(session, schedule)


@router.get("/schedules/{schedule_id}")
def get_schedule(
    schedule_id: int, session: Session = Depends(get_session)
) -> dict:
    schedule = _get_or_404(session, Schedule, schedule_id, "班表")
    return _serialize_schedule(session, schedule)


@router.patch("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: int, data: ScheduleUpdate, session: Session = Depends(get_session)
) -> dict:
    schedule = _get_or_404(session, Schedule, schedule_id, "班表")
    if data.title is not None:
        schedule.title = data.title
    if data.footer is not None:
        schedule.footer = data.footer
    if data.date is not None:
        schedule.date = data.date.strip()
    schedule.updated_at = datetime.now()
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return _serialize_schedule(session, schedule)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: int, session: Session = Depends(get_session)
) -> None:
    schedule = _get_or_404(session, Schedule, schedule_id, "班表")
    for e in session.exec(
        select(ScheduleEntry).where(ScheduleEntry.schedule_id == schedule_id)
    ).all():
        session.delete(e)
    session.delete(schedule)
    session.commit()


@router.post("/schedules/{schedule_id}/entries", status_code=201)
def add_entry(
    schedule_id: int, data: EntryCreate, session: Session = Depends(get_session)
) -> dict:
    """把一張資訊卡片加入出勤名單 (S7/S8)。同一人不重複加入。"""
    _get_or_404(session, Schedule, schedule_id, "班表")
    _get_or_404(session, StoreCard, data.store_card_id, "資訊卡片")
    existing = session.exec(
        select(ScheduleEntry)
        .where(ScheduleEntry.schedule_id == schedule_id)
        .where(ScheduleEntry.store_card_id == data.store_card_id)
    ).first()
    if existing:
        return _serialize_entry(session, existing)
    entry = ScheduleEntry(
        schedule_id=schedule_id,
        store_card_id=data.store_card_id,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _serialize_entry(session, entry)


@router.patch("/entries/{entry_id}")
def update_entry(
    entry_id: int, data: EntryUpdate, session: Session = Depends(get_session)
) -> dict:
    entry = _get_or_404(session, ScheduleEntry, entry_id, "出勤人員")
    if data.time_mode is not None:
        if data.time_mode not in ("manual", "auto"):
            raise HTTPException(status_code=422, detail="time_mode 須為 manual 或 auto")
        entry.time_mode = data.time_mode
    if data.auto_start is not None:
        entry.auto_start = data.auto_start
    if data.slots is not None:
        # 正規化每個時段（保留無法解析的原字串，避免使用者輸入意外被丟棄）
        cleaned = [normalize_time(s) or s.strip() for s in data.slots if s.strip()]
        entry.slots_json = json.dumps(cleaned, ensure_ascii=False)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _serialize_entry(session, entry)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int, session: Session = Depends(get_session)) -> None:
    entry = _get_or_404(session, ScheduleEntry, entry_id, "出勤人員")
    session.delete(entry)
    session.commit()


@router.get("/shift-slots")
def shift_slots(start: str) -> dict:
    """自動換算班次清單 (S10)：每班 1.5h、含端點共 9 班。"""
    return {"start": normalize_time(start), "slots": shift_calculator.shift_slots(start)}


@router.get("/schedules/{schedule_id}/publish-text")
def schedule_publish_text(
    schedule_id: int, session: Session = Depends(get_session)
) -> dict:
    """產生班表發布純文字 (S11)：標題列 + 各人員（編號、簡短介紹、時段）。"""
    schedule = _get_or_404(session, Schedule, schedule_id, "班表")
    entries = session.exec(
        select(ScheduleEntry)
        .where(ScheduleEntry.schedule_id == schedule_id)
        .order_by(ScheduleEntry.id)
    ).all()
    # 沿用與出勤人員相同的名字排序，發布文字順序與編輯畫面一致。
    pairs = [
        (card, entry)
        for entry in entries
        if (card := session.get(StoreCard, entry.store_card_id)) is not None
    ]
    pairs.sort(key=lambda p: _name_sort_key(p[0].name))
    blocks: list[str] = []
    date_str = _format_date(schedule.date)
    if date_str:
        blocks.append(date_str)
    if schedule.title.strip():
        blocks.append(schedule.title.strip())
    for card, entry in pairs:
        lines = [card.name]
        if card.short_intro.strip():
            lines.append(card.short_intro.strip())
        slots = _entry_slots(entry)
        if slots:
            lines.append("、".join(slots))
        blocks.append("\n".join(lines))
    if schedule.footer.strip():
        blocks.append(schedule.footer.strip())
    return {"text": "\n\n".join(blocks)}


def _schedule_pairs(session: Session, schedule_id: int):
    """取出班表的 (卡片, 出勤紀錄) 配對，並依名字排序（與編輯/發布文字一致）。"""
    entries = session.exec(
        select(ScheduleEntry)
        .where(ScheduleEntry.schedule_id == schedule_id)
        .order_by(ScheduleEntry.id)
    ).all()
    pairs = [
        (card, entry)
        for entry in entries
        if (card := session.get(StoreCard, entry.store_card_id)) is not None
    ]
    pairs.sort(key=lambda p: _name_sort_key(p[0].name))
    return pairs


def _schedule_html(session: Session, schedule: Schedule) -> str:
    """產生班表發布 HTML（Telegram parse_mode=HTML 用）。

    名字若有 info_link 就包成超連結 <a href>，連到該美容師先前發布的資訊訊息；
    其餘文字一律 HTML 跳脫，避免 < > & 破壞格式。結構與純文字版 (S11) 相同。
    """
    blocks: list[str] = []
    date_str = _format_date(schedule.date)
    if date_str:
        blocks.append(html.escape(date_str))
    if schedule.title.strip():
        blocks.append(html.escape(schedule.title.strip()))
    for card, entry in _schedule_pairs(session, schedule.id):
        name = html.escape(card.name)
        if card.info_link.strip():
            name = f'<a href="{html.escape(card.info_link.strip(), quote=True)}">{name}</a>'
        lines = [name]
        if card.short_intro.strip():
            lines.append(html.escape(card.short_intro.strip()))
        slots = _entry_slots(entry)
        if slots:
            lines.append(html.escape("、".join(slots)))
        blocks.append("\n".join(lines))
    if schedule.footer.strip():
        blocks.append(html.escape(schedule.footer.strip()))
    return "\n\n".join(blocks)


@router.post("/schedules/{schedule_id}/publish")
def publish_schedule(
    schedule_id: int, data: PublishSchedule, session: Session = Depends(get_session)
) -> dict:
    """自動發布班表到發布目標：以 HTML 送出，名字自動連到該美容師資訊訊息 (S11/P1)。"""
    schedule = _get_or_404(session, Schedule, schedule_id, "班表")
    target = _get_or_404(session, PublishTarget, data.target_id, "發布目標")
    if not target.enabled:
        raise HTTPException(status_code=422, detail="此發布目標已停用")
    html_text = _schedule_html(session, schedule)
    if not html_text.strip():
        raise HTTPException(status_code=422, detail="班表沒有可發布的內容")
    ok, message = publish_service.send_text(
        target.platform, target.token, target.target_id, html_text, parse_mode="HTML"
    )
    if not ok:
        raise HTTPException(status_code=502, detail=f"發布失敗：{message}")
    return {"ok": True, "message": message}


# --------------------------------------------------------------------------
# 標題／結語文字模板（可儲存、選用、編輯）
# --------------------------------------------------------------------------
_TEMPLATE_KINDS = {"title", "footer"}


class TextTemplateCreate(BaseModel):
    kind: str  # "title" | "footer"
    name: str
    content: str = ""


class TextTemplateUpdate(BaseModel):
    name: str | None = None
    content: str | None = None


@router.get("/text-templates")
def list_text_templates(
    kind: str, session: Session = Depends(get_session)
) -> list[dict]:
    """列出某類別（title/footer）的所有文字模板，依 position、id 排序。"""
    if kind not in _TEMPLATE_KINDS:
        raise HTTPException(status_code=422, detail="未知的模板類別")
    rows = session.exec(
        select(TextTemplate)
        .where(TextTemplate.kind == kind)
        .order_by(TextTemplate.position, TextTemplate.id)
    ).all()
    return [t.model_dump() for t in rows]


@router.post("/text-templates", status_code=201)
def create_text_template(
    data: TextTemplateCreate, session: Session = Depends(get_session)
) -> dict:
    if data.kind not in _TEMPLATE_KINDS:
        raise HTTPException(status_code=422, detail="未知的模板類別")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="模板名稱不可空白")
    # 新模板排在同類別最後
    last = session.exec(
        select(TextTemplate)
        .where(TextTemplate.kind == data.kind)
        .order_by(TextTemplate.position.desc())
    ).first()
    position = (last.position + 1) if last else 0
    tpl = TextTemplate(
        kind=data.kind, name=name, content=data.content, position=position
    )
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl.model_dump()


@router.patch("/text-templates/{template_id}")
def update_text_template(
    template_id: int, data: TextTemplateUpdate, session: Session = Depends(get_session)
) -> dict:
    tpl = _get_or_404(session, TextTemplate, template_id, "文字模板")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="模板名稱不可空白")
        tpl.name = name
    if data.content is not None:
        tpl.content = data.content
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl.model_dump()


@router.delete("/text-templates/{template_id}", status_code=204)
def delete_text_template(
    template_id: int, session: Session = Depends(get_session)
) -> None:
    tpl = _get_or_404(session, TextTemplate, template_id, "文字模板")
    session.delete(tpl)
    session.commit()
