"""客人 API（養身館 / 看板 / 卡片 / 心得 / 評分模板）。

對應需求 C1–C22。
M1 範圍：養身館 CRUD (C1/C2/C3)、看板增減/改名 (C4/C5/C6)、卡片基礎 (C7/C8/C11)。
心得、評分模板、簡介內容、拖曳排序於後續 Phase 加入。
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import config
from ..database import get_session
from ..models import (
    Board,
    CardImage,
    CardReview,
    CustomerCard,
    RatingTemplate,
    RatingTemplateItem,
    ReviewScore,
    Spa,
    SpaStaff,
)
from ..services import image_service

router = APIRouter(prefix="/api/customer", tags=["customer"])


# --------------------------------------------------------------------------
# 輸入結構（請求 body）。回應直接用資料表模型即可序列化。
# --------------------------------------------------------------------------
from pydantic import BaseModel


class StaffMemberIn(BaseModel):
    name: str
    contact: str = ""  # 聯絡資訊


class SpaCreate(BaseModel):
    name: str
    address: str = ""


class SpaUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    # 提供時整批覆蓋幹部清單（含聯絡資訊）；None 表示不更動 (C2)
    staff_members: list[StaffMemberIn] | None = None


class SpaMove(BaseModel):
    position: int  # 在養身館列表中的新排序索引（0 起算）


class BoardCreate(BaseModel):
    name: str


class BoardUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    sort_mode: str | None = None  # "unicode" | "manual"


class BoardMove(BaseModel):
    position: int  # 在所屬養身館中的新排序索引（0 起算）


class SortModeUpdate(BaseModel):
    mode: str  # "unicode"（預設/標題）| "manual"（手動）


class CardCreate(BaseModel):
    title: str


class CardUpdate(BaseModel):
    title: str | None = None
    nationality: str | None = None
    intro_text: str | None = None
    intro_collapsed: bool | None = None


class CardMove(BaseModel):
    board_id: int  # 目標看板（可為原看板）
    position: int  # 在目標看板中的插入位置（0 起算）


class PasteImage(BaseModel):
    data_url: str  # data:image/...;base64,xxx 或純 base64


class TemplateCreate(BaseModel):
    name: str


class TemplateUpdate(BaseModel):
    name: str


class ItemSpec(BaseModel):
    name: str
    item_type: str = "score"  # "score" | "yesno"


class TemplateReplace(BaseModel):
    """整批覆蓋模板（名稱 + 全部項目），供前端「儲存」草稿用。"""
    name: str
    items: list[ItemSpec] = []


class ItemCreate(BaseModel):
    name: str
    item_type: str = "score"  # "score" | "yesno"


class ItemUpdate(BaseModel):
    name: str | None = None
    item_type: str | None = None  # "score" | "yesno"


class ItemMove(BaseModel):
    direction: str  # "up" | "down"


class ReviewCreate(BaseModel):
    template_id: int | None = None  # 指定模板；省略則沿用前一則或預設第一組 (C20/C22)


class ReviewUpdate(BaseModel):
    date: str | None = None
    text: str | None = None


class ScoreUpdate(BaseModel):
    score: int | None = None
    note: str | None = None
    yesno_value: str | None = None  # "" | "有" | "無"


class ReviewApplyTemplate(BaseModel):
    template_id: int  # 切換套用的模板，重新快照項目


# --------------------------------------------------------------------------
# 共用工具
# --------------------------------------------------------------------------
def _get_or_404(session: Session, model, obj_id: int, label: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"找不到{label} (id={obj_id})")
    return obj


def _natural_key(s: str) -> list:
    """Natural sort key：數字段依數值排序，其餘依字元碼排序。"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def _cover_url(session: Session, card_id: int) -> str | None:
    """卡片封面 URL：取 is_cover 者，否則第一張圖，皆無則 None (C8)。"""
    images = session.exec(
        select(CardImage)
        .where(CardImage.card_id == card_id)
        .order_by(CardImage.position)
    ).all()
    if not images:
        return None
    cover = next((im for im in images if im.is_cover), images[0])
    return image_service.image_url(cover.filename)


def _next_position(session: Session, model, **filters) -> int:
    """取得某容器內下一個排序位置（現有最大值 + 1）。"""
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    items = session.exec(stmt).all()
    return (max((i.position for i in items), default=-1)) + 1


# --------------------------------------------------------------------------
# 養身館 (C1/C2/C3)
# --------------------------------------------------------------------------
def _staff_members(session: Session, spa_id: int) -> list[dict]:
    """取得某養身館的幹部清單（含聯絡資訊），依顯示順序 (C2)。"""
    members = session.exec(
        select(SpaStaff)
        .where(SpaStaff.spa_id == spa_id)
        .order_by(SpaStaff.position, SpaStaff.id)
    ).all()
    return [m.model_dump() for m in members]


def _spa_with_staff(session: Session, spa: Spa) -> dict:
    return {**spa.model_dump(), "staff_members": _staff_members(session, spa.id)}


@router.get("/spas")
def list_spas(session: Session = Depends(get_session)) -> list[dict]:
    # 依手動排序位置；位置相同時以建立時間為次序 (C3)
    spas = session.exec(select(Spa).order_by(Spa.position, Spa.created_at)).all()
    return [_spa_with_staff(session, s) for s in spas]


@router.post("/spas", status_code=201)
def create_spa(data: SpaCreate, session: Session = Depends(get_session)) -> dict:
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="養身館名稱不可空白")
    spa = Spa(
        name=name,
        address=data.address,
        position=_next_position(session, Spa),  # 新養身館排在列表最後
    )
    session.add(spa)
    session.commit()
    session.refresh(spa)

    # 自動建立五個預設看板 (C6)
    for pos, board_name in enumerate(config.DEFAULT_BOARDS):
        session.add(Board(spa_id=spa.id, name=board_name, position=pos))
    session.commit()
    session.refresh(spa)  # 第二次 commit 後物件會過期，重新載入再回傳
    return _spa_with_staff(session, spa)


@router.get("/spas/{spa_id}")
def get_spa(spa_id: int, session: Session = Depends(get_session)) -> dict:
    """單一養身館頁面所需資料：養身館 + 看板（各含卡片）(C3/C4/C7/C8)。"""
    spa = _get_or_404(session, Spa, spa_id, "養身館")
    boards = session.exec(
        select(Board).where(Board.spa_id == spa_id).order_by(Board.position)
    ).all()

    board_list = []
    for board in boards:
        cards = session.exec(
            select(CustomerCard)
            .where(CustomerCard.board_id == board.id)
            .order_by(CustomerCard.position)
        ).all()
        # 預設模式依標題自然排序（數字段依數值、其餘依碼點）(C10)
        if board.sort_mode == "unicode":
            cards = sorted(cards, key=lambda c: _natural_key(c.title))
        card_dicts = [
            {**c.model_dump(), "cover_image": _cover_url(session, c.id)} for c in cards
        ]
        board_list.append({**board.model_dump(), "cards": card_dicts})

    return {
        **spa.model_dump(),
        "staff_members": _staff_members(session, spa_id),
        "boards": board_list,
    }


@router.patch("/spas/{spa_id}")
def update_spa(
    spa_id: int, data: SpaUpdate, session: Session = Depends(get_session)
) -> dict:
    spa = _get_or_404(session, Spa, spa_id, "養身館")
    if data.name is not None:
        new_name = data.name.strip()
        if not new_name:
            raise HTTPException(status_code=422, detail="養身館名稱不可空白")
        spa.name = new_name
    if data.address is not None:
        spa.address = data.address
    session.add(spa)

    # 整批覆蓋幹部清單：先清掉舊的，再依序建立新的（空白名稱略過）(C2)
    if data.staff_members is not None:
        for old in session.exec(
            select(SpaStaff).where(SpaStaff.spa_id == spa_id)
        ).all():
            session.delete(old)
        pos = 0
        for m in data.staff_members:
            name = m.name.strip()
            if not name:
                continue
            session.add(
                SpaStaff(
                    spa_id=spa_id,
                    name=name,
                    contact=m.contact.strip(),
                    position=pos,
                )
            )
            pos += 1

    session.commit()
    session.refresh(spa)
    return _spa_with_staff(session, spa)


@router.delete("/spas/{spa_id}", status_code=204)
def delete_spa(spa_id: int, session: Session = Depends(get_session)) -> None:
    spa = _get_or_404(session, Spa, spa_id, "養身館")
    # 手動串接刪除：卡片 → 看板 → 幹部 → 養身館
    boards = session.exec(select(Board).where(Board.spa_id == spa_id)).all()
    for board in boards:
        cards = session.exec(
            select(CustomerCard).where(CustomerCard.board_id == board.id)
        ).all()
        for card in cards:
            _delete_card_cascade(session, card)
        session.delete(board)
    for member in session.exec(
        select(SpaStaff).where(SpaStaff.spa_id == spa_id)
    ).all():
        session.delete(member)
    session.delete(spa)
    session.commit()


@router.post("/spas/{spa_id}/move")
def move_spa(
    spa_id: int, data: SpaMove, session: Session = Depends(get_session)
) -> dict:
    """調整養身館在列表中的順序 (C3)。"""
    spa = _get_or_404(session, Spa, spa_id, "養身館")
    siblings = [
        s
        for s in session.exec(
            select(Spa).order_by(Spa.position, Spa.created_at)
        ).all()
        if s.id != spa_id
    ]
    pos = max(0, min(data.position, len(siblings)))
    siblings.insert(pos, spa)
    for i, s in enumerate(siblings):
        if s.position != i:
            s.position = i
            session.add(s)
    session.commit()
    return {"ok": True}


# --------------------------------------------------------------------------
# 看板 (C4/C5/C6)
# --------------------------------------------------------------------------
@router.post("/spas/{spa_id}/boards", status_code=201)
def create_board(
    spa_id: int, data: BoardCreate, session: Session = Depends(get_session)
) -> Board:
    _get_or_404(session, Spa, spa_id, "養身館")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="看板名稱不可空白")
    board = Board(
        spa_id=spa_id,
        name=name,
        position=_next_position(session, Board, spa_id=spa_id),
    )
    session.add(board)
    session.commit()
    session.refresh(board)
    return board


@router.patch("/boards/{board_id}")
def update_board(
    board_id: int, data: BoardUpdate, session: Session = Depends(get_session)
) -> Board:
    board = _get_or_404(session, Board, board_id, "看板")
    if data.name is not None:
        new_name = data.name.strip()
        if not new_name:
            raise HTTPException(status_code=422, detail="看板名稱不可空白")
        board.name = new_name
    if data.position is not None:
        board.position = data.position
    if data.sort_mode is not None:
        if data.sort_mode not in ("unicode", "manual"):
            raise HTTPException(status_code=422, detail="排序方式須為 unicode 或 manual")
        board.sort_mode = data.sort_mode
    session.add(board)
    session.commit()
    session.refresh(board)
    return board


@router.post("/boards/{board_id}/move")
def move_board(
    board_id: int, data: BoardMove, session: Session = Depends(get_session)
) -> dict:
    """調整看板在所屬養身館中的左右順序 (C5)。"""
    board = _get_or_404(session, Board, board_id, "看板")
    siblings = [
        b
        for b in session.exec(
            select(Board)
            .where(Board.spa_id == board.spa_id)
            .order_by(Board.position)
        ).all()
        if b.id != board_id
    ]
    pos = max(0, min(data.position, len(siblings)))
    siblings.insert(pos, board)
    for i, b in enumerate(siblings):
        if b.position != i:
            b.position = i
            session.add(b)
    session.commit()
    return {"ok": True}


@router.post("/boards/{board_id}/sort-mode")
def set_sort_mode(
    board_id: int, data: SortModeUpdate, session: Session = Depends(get_session)
) -> dict:
    """切換看板排序方式 (C10)，並處理手動排序的保存／還原。

    - 切到 "unicode"（預設/標題）：先把目前的 position 存進 manual_position
      作為手動排序快照，再依標題標準 Unicode 重新編號 position（整個看板套用預設邏輯）。
    - 切到 "manual"（手動）：依 manual_position 快照重新編號 position，
      還原上次的手動排序。
    """
    if data.mode not in ("unicode", "manual"):
        raise HTTPException(status_code=422, detail="排序方式須為 unicode 或 manual")
    board = _get_or_404(session, Board, board_id, "看板")
    if board.sort_mode == data.mode:
        return {"ok": True}  # 模式未變更，不更動排序

    cards = session.exec(
        select(CustomerCard)
        .where(CustomerCard.board_id == board_id)
        .order_by(CustomerCard.position)
    ).all()

    if data.mode == "unicode":
        # 1) 保存目前手動排序快照
        for c in cards:
            c.manual_position = c.position
        # 2) 依標題自然排序重新編號
        for i, c in enumerate(sorted(cards, key=lambda c: _natural_key(c.title))):
            c.position = i
            session.add(c)
    else:  # manual：依快照還原，重新編號避免重複/空洞
        for i, c in enumerate(
            sorted(cards, key=lambda c: (c.manual_position, c.id))
        ):
            c.position = i
            session.add(c)

    board.sort_mode = data.mode
    session.add(board)
    session.commit()
    return {"ok": True}


@router.delete("/boards/{board_id}", status_code=204)
def delete_board(board_id: int, session: Session = Depends(get_session)) -> None:
    board = _get_or_404(session, Board, board_id, "看板")
    cards = session.exec(
        select(CustomerCard).where(CustomerCard.board_id == board_id)
    ).all()
    for card in cards:
        _delete_card_cascade(session, card)
    session.delete(board)
    session.commit()


# --------------------------------------------------------------------------
# 美容師卡片（基礎，C7/C8/C11）
# --------------------------------------------------------------------------
@router.post("/boards/{board_id}/cards", status_code=201)
def create_card(
    board_id: int, data: CardCreate, session: Session = Depends(get_session)
) -> CustomerCard:
    _get_or_404(session, Board, board_id, "看板")
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="卡片標題不可空白")
    pos = _next_position(session, CustomerCard, board_id=board_id)
    card = CustomerCard(
        board_id=board_id,
        title=title,
        position=pos,
        manual_position=pos,  # 新卡片的手動排序快照與目前位置一致
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@router.patch("/cards/{card_id}")
def update_card(
    card_id: int, data: CardUpdate, session: Session = Depends(get_session)
) -> CustomerCard:
    card = _get_or_404(session, CustomerCard, card_id, "卡片")
    if data.title is not None:
        new_title = data.title.strip()
        if not new_title:
            raise HTTPException(status_code=422, detail="卡片標題不可空白")
        card.title = new_title
    if data.nationality is not None:
        card.nationality = data.nationality
    if data.intro_text is not None:
        card.intro_text = data.intro_text
    if data.intro_collapsed is not None:
        card.intro_collapsed = data.intro_collapsed
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def _delete_card_cascade(session: Session, card: CustomerCard) -> None:
    """刪除卡片及其圖片（含檔案）、心得與評分。"""
    for img in session.exec(
        select(CardImage).where(CardImage.card_id == card.id)
    ).all():
        image_service.delete_image_file(img.filename)
        session.delete(img)
    reviews = session.exec(
        select(CardReview).where(CardReview.card_id == card.id)
    ).all()
    for review in reviews:
        for score in session.exec(
            select(ReviewScore).where(ReviewScore.review_id == review.id)
        ).all():
            session.delete(score)
        session.delete(review)
    session.delete(card)


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, session: Session = Depends(get_session)) -> None:
    card = _get_or_404(session, CustomerCard, card_id, "卡片")
    _delete_card_cascade(session, card)
    session.commit()


# --------------------------------------------------------------------------
# 卡片詳情（簡介 + 心得，C12–C22）
# --------------------------------------------------------------------------
def _serialize_review(session: Session, review: CardReview) -> dict:
    scores = session.exec(
        select(ReviewScore)
        .where(ReviewScore.review_id == review.id)
        .order_by(ReviewScore.position)
    ).all()
    return {**review.model_dump(), "scores": [s.model_dump() for s in scores]}


@router.get("/cards/{card_id}")
def get_card(card_id: int, session: Session = Depends(get_session)) -> dict:
    """卡片完整內容：基本欄位 + 圖片 + 多組心得（含評分）。"""
    card = _get_or_404(session, CustomerCard, card_id, "卡片")
    images = session.exec(
        select(CardImage)
        .where(CardImage.card_id == card_id)
        .order_by(CardImage.position)
    ).all()
    image_list = [
        {**im.model_dump(), "url": image_service.image_url(im.filename)}
        for im in images
    ]
    reviews = session.exec(
        select(CardReview)
        .where(CardReview.card_id == card_id)
        .order_by(CardReview.position)
    ).all()
    review_list = [_serialize_review(session, r) for r in reviews]
    board = session.get(Board, card.board_id)
    spa = session.get(Spa, board.spa_id) if board else None
    return {
        **card.model_dump(),
        "spa_id": board.spa_id if board else None,  # 供前端返回養身館頁
        "spa_name": spa.name if spa else None,
        "cover_image": _cover_url(session, card_id),
        "images": image_list,
        "reviews": review_list,
    }


# --------------------------------------------------------------------------
# 簡介圖片（上傳 / 貼上 / 封面 / 刪除，C13）
# --------------------------------------------------------------------------
def _add_image(session: Session, card_id: int, filename: str) -> CardImage:
    existing = session.exec(
        select(CardImage).where(CardImage.card_id == card_id)
    ).all()
    image = CardImage(
        card_id=card_id,
        filename=filename,
        is_cover=(len(existing) == 0),  # 第一張自動設為封面
        position=_next_position(session, CardImage, card_id=card_id),
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
    _get_or_404(session, CustomerCard, card_id, "卡片")
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
    _get_or_404(session, CustomerCard, card_id, "卡片")
    try:
        filename = image_service.save_data_url(data.data_url)
    except Exception:
        raise HTTPException(status_code=422, detail="貼上的內容不是有效的圖片")
    return _add_image(session, card_id, filename)


@router.post("/images/{image_id}/cover")
def set_cover(image_id: int, session: Session = Depends(get_session)) -> dict:
    image = _get_or_404(session, CardImage, image_id, "圖片")
    for other in session.exec(
        select(CardImage).where(CardImage.card_id == image.card_id)
    ).all():
        other.is_cover = other.id == image_id
        session.add(other)
    session.commit()
    return {"ok": True}


@router.delete("/images/{image_id}", status_code=204)
def delete_image(image_id: int, session: Session = Depends(get_session)) -> None:
    image = _get_or_404(session, CardImage, image_id, "圖片")
    card_id, was_cover = image.card_id, image.is_cover
    image_service.delete_image_file(image.filename)
    session.delete(image)
    session.commit()
    # 若刪掉的是封面，將剩餘第一張設為封面
    if was_cover:
        remaining = session.exec(
            select(CardImage)
            .where(CardImage.card_id == card_id)
            .order_by(CardImage.position)
        ).first()
        if remaining:
            remaining.is_cover = True
            session.add(remaining)
            session.commit()


# --------------------------------------------------------------------------
# 評分模板（C17/C18/C20）
# --------------------------------------------------------------------------
def _serialize_template(session: Session, template: RatingTemplate) -> dict:
    items = session.exec(
        select(RatingTemplateItem)
        .where(RatingTemplateItem.template_id == template.id)
        .order_by(RatingTemplateItem.position)
    ).all()
    return {**template.model_dump(), "items": [i.model_dump() for i in items]}


@router.get("/templates")
def list_templates(session: Session = Depends(get_session)) -> list[dict]:
    templates = session.exec(
        select(RatingTemplate).order_by(RatingTemplate.position)
    ).all()
    return [_serialize_template(session, t) for t in templates]


@router.post("/templates", status_code=201)
def create_template(
    data: TemplateCreate, session: Session = Depends(get_session)
) -> dict:
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="模板名稱不可空白")
    template = RatingTemplate(
        name=name, position=_next_position(session, RatingTemplate)
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return _serialize_template(session, template)


@router.patch("/templates/{template_id}")
def rename_template(
    template_id: int, data: TemplateUpdate, session: Session = Depends(get_session)
) -> dict:
    template = _get_or_404(session, RatingTemplate, template_id, "模板")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="模板名稱不可空白")
    template.name = name
    session.add(template)
    session.commit()
    session.refresh(template)
    return _serialize_template(session, template)


@router.put("/templates/{template_id}")
def replace_template(
    template_id: int, data: TemplateReplace, session: Session = Depends(get_session)
) -> dict:
    """整批覆蓋模板：更新名稱並以新的項目清單取代全部既有項目。

    不影響既有心得（心得在建立時已快照項目）；之後用此模板建立的新心得才會套用。
    """
    template = _get_or_404(session, RatingTemplate, template_id, "模板")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="模板名稱不可空白")
    for it in data.items:
        if not it.name.strip():
            raise HTTPException(status_code=422, detail="項目名稱不可空白")
        if it.item_type not in ("score", "yesno"):
            raise HTTPException(status_code=422, detail="項目類型須為 score 或 yesno")
    template.name = name
    session.add(template)
    # 刪除既有項目，再依新清單重建
    for old in session.exec(
        select(RatingTemplateItem).where(
            RatingTemplateItem.template_id == template_id
        )
    ).all():
        session.delete(old)
    session.flush()
    for i, it in enumerate(data.items):
        session.add(RatingTemplateItem(
            template_id=template_id,
            name=it.name.strip(),
            item_type=it.item_type,
            position=i,
        ))
    session.commit()
    session.refresh(template)
    return _serialize_template(session, template)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(
    template_id: int, session: Session = Depends(get_session)
) -> None:
    template = _get_or_404(session, RatingTemplate, template_id, "模板")
    for item in session.exec(
        select(RatingTemplateItem).where(
            RatingTemplateItem.template_id == template_id
        )
    ).all():
        session.delete(item)
    session.delete(template)
    session.commit()


@router.post("/templates/{template_id}/items", status_code=201)
def add_template_item(
    template_id: int, data: ItemCreate, session: Session = Depends(get_session)
) -> dict:
    _get_or_404(session, RatingTemplate, template_id, "模板")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="項目名稱不可空白")
    if data.item_type not in ("score", "yesno"):
        raise HTTPException(status_code=422, detail="項目類型須為 score 或 yesno")
    item = RatingTemplateItem(
        template_id=template_id,
        name=name,
        item_type=data.item_type,
        position=_next_position(session, RatingTemplateItem, template_id=template_id),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item.model_dump()


@router.patch("/template-items/{item_id}")
def rename_template_item(
    item_id: int, data: ItemUpdate, session: Session = Depends(get_session)
) -> dict:
    item = _get_or_404(session, RatingTemplateItem, item_id, "項目")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="項目名稱不可空白")
        item.name = name
    if data.item_type is not None:
        if data.item_type not in ("score", "yesno"):
            raise HTTPException(status_code=422, detail="項目類型須為 score 或 yesno")
        item.item_type = data.item_type
    session.add(item)
    session.commit()
    session.refresh(item)
    return item.model_dump()


@router.post("/template-items/{item_id}/move")
def move_template_item(
    item_id: int, data: ItemMove, session: Session = Depends(get_session)
) -> dict:
    """調整模板項目的上下順序。"""
    if data.direction not in ("up", "down"):
        raise HTTPException(status_code=422, detail="方向須為 up 或 down")
    item = _get_or_404(session, RatingTemplateItem, item_id, "項目")
    siblings = session.exec(
        select(RatingTemplateItem)
        .where(RatingTemplateItem.template_id == item.template_id)
        .order_by(RatingTemplateItem.position)
    ).all()
    idx = next((i for i, x in enumerate(siblings) if x.id == item_id), None)
    if idx is None:
        return {"ok": True}
    if data.direction == "up" and idx > 0:
        other = siblings[idx - 1]
    elif data.direction == "down" and idx < len(siblings) - 1:
        other = siblings[idx + 1]
    else:
        return {"ok": True}  # 已在邊界
    item.position, other.position = other.position, item.position
    session.add(item)
    session.add(other)
    session.commit()
    return {"ok": True}


class CopyToTarget(BaseModel):
    target_id: int


@router.post("/templates/{source_id}/copy-to")
def copy_template_to(
    source_id: int, data: CopyToTarget, session: Session = Depends(get_session)
) -> dict:
    """將來源模板的所有項目複製並覆蓋套用到目標模板。"""
    if source_id == data.target_id:
        raise HTTPException(status_code=422, detail="來源與目標模板不能相同")
    source = _get_or_404(session, RatingTemplate, source_id, "來源模板")
    _get_or_404(session, RatingTemplate, data.target_id, "目標模板")
    # 刪除目標既有項目
    for it in session.exec(
        select(RatingTemplateItem).where(RatingTemplateItem.template_id == data.target_id)
    ).all():
        session.delete(it)
    # 從來源複製
    for it in session.exec(
        select(RatingTemplateItem)
        .where(RatingTemplateItem.template_id == source_id)
        .order_by(RatingTemplateItem.position)
    ).all():
        session.add(RatingTemplateItem(
            template_id=data.target_id,
            name=it.name,
            item_type=it.item_type,
            position=it.position,
        ))
    session.commit()
    return _serialize_template(session, session.get(
        RatingTemplate, data.target_id
    ))


@router.delete("/template-items/{item_id}", status_code=204)
def delete_template_item(
    item_id: int, session: Session = Depends(get_session)
) -> None:
    item = _get_or_404(session, RatingTemplateItem, item_id, "項目")
    session.delete(item)
    session.commit()


# --------------------------------------------------------------------------
# 心得（多組，C16/C19/C21/C22）
# --------------------------------------------------------------------------
def _template_items(session: Session, template_id: int) -> list[RatingTemplateItem]:
    return session.exec(
        select(RatingTemplateItem)
        .where(RatingTemplateItem.template_id == template_id)
        .order_by(RatingTemplateItem.position)
    ).all()


def _first_template(session: Session) -> RatingTemplate | None:
    return session.exec(
        select(RatingTemplate).order_by(RatingTemplate.position)
    ).first()


@router.post("/cards/{card_id}/reviews", status_code=201)
def create_review(
    card_id: int, data: ReviewCreate, session: Session = Depends(get_session)
) -> dict:
    """新增一組心得。

    內容預設來源 (C20/C22)：
      - 指定 template_id → 用該模板的項目建立空白評分。
      - 未指定且已有前一則心得 → 沿用前一則的模板、評分值、補充文字與心得文字。
      - 未指定且無前一則 → 用預設第一組模板。
    """
    _get_or_404(session, CustomerCard, card_id, "卡片")
    prev = session.exec(
        select(CardReview)
        .where(CardReview.card_id == card_id)
        .order_by(CardReview.position.desc())
    ).first()

    review = CardReview(
        card_id=card_id,
        position=_next_position(session, CardReview, card_id=card_id),
    )

    if data.template_id is not None:
        template = _get_or_404(session, RatingTemplate, data.template_id, "模板")
        review.template_id = template.id
        session.add(review)
        session.commit()
        session.refresh(review)
        for i, item in enumerate(_template_items(session, template.id)):
            session.add(
                ReviewScore(
                    review_id=review.id, item_name=item.name,
                    item_type=item.item_type, score=0, position=i
                )
            )
    elif prev is not None:
        # 沿用前一則內容 (C22)
        review.template_id = prev.template_id
        review.text = prev.text
        review.date = prev.date
        session.add(review)
        session.commit()
        session.refresh(review)
        prev_scores = session.exec(
            select(ReviewScore)
            .where(ReviewScore.review_id == prev.id)
            .order_by(ReviewScore.position)
        ).all()
        for s in prev_scores:
            session.add(
                ReviewScore(
                    review_id=review.id,
                    item_name=s.item_name,
                    item_type=s.item_type,
                    score=s.score,
                    yesno_value=s.yesno_value,
                    note=s.note,
                    position=s.position,
                )
            )
    else:
        template = _first_template(session)
        if template is not None:
            review.template_id = template.id
        session.add(review)
        session.commit()
        session.refresh(review)
        if template is not None:
            for i, item in enumerate(_template_items(session, template.id)):
                session.add(
                    ReviewScore(
                        review_id=review.id, item_name=item.name,
                        item_type=item.item_type, score=0, position=i
                    )
                )

    session.commit()
    return _serialize_review(session, review)


@router.patch("/reviews/{review_id}")
def update_review(
    review_id: int, data: ReviewUpdate, session: Session = Depends(get_session)
) -> dict:
    review = _get_or_404(session, CardReview, review_id, "心得")
    if data.date is not None:
        review.date = data.date
    if data.text is not None:
        review.text = data.text
    session.add(review)
    session.commit()
    session.refresh(review)
    return _serialize_review(session, review)


@router.post("/reviews/{review_id}/template")
def apply_template(
    review_id: int,
    data: ReviewApplyTemplate,
    session: Session = Depends(get_session),
) -> dict:
    """切換心得套用的模板：以新模板項目重新建立評分（清掉舊評分）。"""
    review = _get_or_404(session, CardReview, review_id, "心得")
    template = _get_or_404(session, RatingTemplate, data.template_id, "模板")
    for s in session.exec(
        select(ReviewScore).where(ReviewScore.review_id == review_id)
    ).all():
        session.delete(s)
    review.template_id = template.id
    session.add(review)
    for i, item in enumerate(_template_items(session, template.id)):
        session.add(
            ReviewScore(
                review_id=review.id, item_name=item.name,
                item_type=item.item_type, score=0, position=i
            )
        )
    session.commit()
    session.refresh(review)
    return _serialize_review(session, review)


@router.post("/reviews/{review_id}/sync")
def sync_review_template(
    review_id: int, session: Session = Depends(get_session)
) -> dict:
    """將心得更新為其所屬模板的最新項目。

    相同名稱（且類型相同）的項目會保留原有評分與補充文字；
    模板新增的項目以空白加入；模板已移除的項目從心得刪除。
    """
    review = _get_or_404(session, CardReview, review_id, "心得")
    if review.template_id is None:
        raise HTTPException(status_code=422, detail="此心得未綁定模板")
    template = session.get(RatingTemplate, review.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="模板已刪除，無法更新")
    items = _template_items(session, template.id)
    old_scores = {
        s.item_name: s
        for s in session.exec(
            select(ReviewScore).where(ReviewScore.review_id == review_id)
        ).all()
    }
    for s in old_scores.values():
        session.delete(s)
    session.flush()
    for i, item in enumerate(items):
        prev = old_scores.get(item.name)
        keep = prev is not None and prev.item_type == item.item_type
        session.add(ReviewScore(
            review_id=review.id,
            item_name=item.name,
            item_type=item.item_type,
            score=prev.score if keep else 0,
            yesno_value=prev.yesno_value if keep else "",
            note=prev.note if prev is not None else "",
            position=i,
        ))
    session.commit()
    return _serialize_review(session, review)


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, session: Session = Depends(get_session)) -> None:
    review = _get_or_404(session, CardReview, review_id, "心得")
    for s in session.exec(
        select(ReviewScore).where(ReviewScore.review_id == review_id)
    ).all():
        session.delete(s)
    session.delete(review)
    session.commit()


@router.patch("/scores/{score_id}")
def update_score(
    score_id: int, data: ScoreUpdate, session: Session = Depends(get_session)
) -> dict:
    score = _get_or_404(session, ReviewScore, score_id, "評分項目")
    if data.score is not None:
        if not 0 <= data.score <= 10:
            raise HTTPException(status_code=422, detail="分數須介於 0~10")
        score.score = data.score
    if data.note is not None:
        score.note = data.note
    if data.yesno_value is not None:
        if data.yesno_value not in ("", "有", "無"):
            raise HTTPException(status_code=422, detail="有/無值須為空字串、有 或 無")
        score.yesno_value = data.yesno_value
    session.add(score)
    session.commit()
    session.refresh(score)
    return score.model_dump()


def _renumber(session: Session, board_id: int) -> None:
    """將某看板內卡片的 position 重新整理為連續 0,1,2…（依現有 position）。"""
    cards = session.exec(
        select(CustomerCard)
        .where(CustomerCard.board_id == board_id)
        .order_by(CustomerCard.position)
    ).all()
    for i, c in enumerate(cards):
        if c.position != i:
            c.position = i
            session.add(c)


@router.post("/cards/{card_id}/move")
def move_card(
    card_id: int, data: CardMove, session: Session = Depends(get_session)
) -> dict:
    """同／跨看板移動卡片並重排位置 (C9)。

    position 為卡片在目標看板中的插入索引（0 起算）。
    """
    card = _get_or_404(session, CustomerCard, card_id, "卡片")
    target_board = _get_or_404(session, Board, data.board_id, "看板")
    source_board_id = card.board_id

    card.board_id = data.board_id

    # 目標看板現有卡片（排除被移動者）
    others = [
        c
        for c in session.exec(
            select(CustomerCard)
            .where(CustomerCard.board_id == data.board_id)
            .order_by(CustomerCard.position)
        ).all()
        if c.id != card_id
    ]

    if target_board.sort_mode == "unicode":
        # unicode 模式：drop 位置無意義，依自然排序決定最終順序
        all_cards = others + [card]
        ordered = sorted(all_cards, key=lambda c: _natural_key(c.title))
    else:
        # 手動模式：依前端傳入的 drop 位置插入
        pos = max(0, min(data.position, len(others)))
        others.insert(pos, card)
        ordered = others

    for i, c in enumerate(ordered):
        c.position = i
        c.manual_position = i  # 同步快照，避免切換排序模式時位置錯亂
        session.add(c)

    # 來源看板若不同，重排其剩餘卡片位置
    if source_board_id != data.board_id:
        _renumber(session, source_board_id)

    session.commit()
    return {"ok": True}
