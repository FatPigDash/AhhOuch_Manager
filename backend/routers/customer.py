"""客人 API（養身館 / 看板 / 卡片 / 心得 / 評分模板）。

對應需求 C1–C22。
M1 範圍：養身館 CRUD (C1/C2/C3)、看板增減/改名 (C4/C5/C6)、卡片基礎 (C7/C8/C11)。
心得、評分模板、簡介內容、拖曳排序於後續 Phase 加入。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import config
from ..database import get_session
from ..models import Board, CustomerCard, Spa

router = APIRouter(prefix="/api/customer", tags=["customer"])


# --------------------------------------------------------------------------
# 輸入結構（請求 body）。回應直接用資料表模型即可序列化。
# --------------------------------------------------------------------------
from pydantic import BaseModel


class SpaCreate(BaseModel):
    name: str
    address: str = ""
    staff: str = ""


class SpaUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    staff: str | None = None


class BoardCreate(BaseModel):
    name: str


class BoardUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    sort_mode: str | None = None  # "unicode" | "manual"


class BoardMove(BaseModel):
    position: int  # 在所屬養身館中的新排序索引（0 起算）


class CardCreate(BaseModel):
    title: str


class CardUpdate(BaseModel):
    title: str | None = None


class CardMove(BaseModel):
    board_id: int  # 目標看板（可為原看板）
    position: int  # 在目標看板中的插入位置（0 起算）


# --------------------------------------------------------------------------
# 共用工具
# --------------------------------------------------------------------------
def _get_or_404(session: Session, model, obj_id: int, label: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"找不到{label} (id={obj_id})")
    return obj


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
@router.get("/spas")
def list_spas(session: Session = Depends(get_session)) -> list[Spa]:
    return session.exec(select(Spa).order_by(Spa.created_at)).all()


@router.post("/spas", status_code=201)
def create_spa(data: SpaCreate, session: Session = Depends(get_session)) -> Spa:
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="養身館名稱不可空白")
    spa = Spa(name=name, address=data.address, staff=data.staff)
    session.add(spa)
    session.commit()
    session.refresh(spa)

    # 自動建立五個預設看板 (C6)
    for pos, board_name in enumerate(config.DEFAULT_BOARDS):
        session.add(Board(spa_id=spa.id, name=board_name, position=pos))
    session.commit()
    session.refresh(spa)  # 第二次 commit 後物件會過期，重新載入再回傳
    return spa


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
        # 預設模式依標題標準 Unicode 排序（Python str 比較即為碼點順序）(C10)
        if board.sort_mode == "unicode":
            cards = sorted(cards, key=lambda c: c.title)
        board_list.append({**board.model_dump(), "cards": cards})

    return {**spa.model_dump(), "boards": board_list}


@router.patch("/spas/{spa_id}")
def update_spa(
    spa_id: int, data: SpaUpdate, session: Session = Depends(get_session)
) -> Spa:
    spa = _get_or_404(session, Spa, spa_id, "養身館")
    if data.name is not None:
        new_name = data.name.strip()
        if not new_name:
            raise HTTPException(status_code=422, detail="養身館名稱不可空白")
        spa.name = new_name
    if data.address is not None:
        spa.address = data.address
    if data.staff is not None:
        spa.staff = data.staff
    session.add(spa)
    session.commit()
    session.refresh(spa)
    return spa


@router.delete("/spas/{spa_id}", status_code=204)
def delete_spa(spa_id: int, session: Session = Depends(get_session)) -> None:
    spa = _get_or_404(session, Spa, spa_id, "養身館")
    # 手動串接刪除：卡片 → 看板 → 養身館
    boards = session.exec(select(Board).where(Board.spa_id == spa_id)).all()
    for board in boards:
        cards = session.exec(
            select(CustomerCard).where(CustomerCard.board_id == board.id)
        ).all()
        for card in cards:
            session.delete(card)
        session.delete(board)
    session.delete(spa)
    session.commit()


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


@router.delete("/boards/{board_id}", status_code=204)
def delete_board(board_id: int, session: Session = Depends(get_session)) -> None:
    board = _get_or_404(session, Board, board_id, "看板")
    cards = session.exec(
        select(CustomerCard).where(CustomerCard.board_id == board_id)
    ).all()
    for card in cards:
        session.delete(card)
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
    card = CustomerCard(
        board_id=board_id,
        title=title,
        position=_next_position(session, CustomerCard, board_id=board_id),
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
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, session: Session = Depends(get_session)) -> None:
    card = _get_or_404(session, CustomerCard, card_id, "卡片")
    session.delete(card)
    session.commit()


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
    _get_or_404(session, Board, data.board_id, "看板")
    source_board_id = card.board_id

    # 目標看板現有卡片（排除被移動者），依 position 排序
    target_cards = [
        c
        for c in session.exec(
            select(CustomerCard)
            .where(CustomerCard.board_id == data.board_id)
            .order_by(CustomerCard.position)
        ).all()
        if c.id != card_id
    ]
    pos = max(0, min(data.position, len(target_cards)))
    target_cards.insert(pos, card)

    card.board_id = data.board_id
    for i, c in enumerate(target_cards):
        c.position = i
        session.add(c)

    # 來源看板若不同，重排其剩餘卡片位置
    if source_board_id != data.board_id:
        _renumber(session, source_board_id)

    session.commit()
    return {"ok": True}
