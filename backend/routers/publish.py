"""社群發布 API (P1)：發布目標設定 + 一鍵發布文字。

通用骨架：可新增多個發布目標（平台/權杖/目標 ID），對任一目標送出純文字。
平台實作見 services/publish_service.py。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import PublishTarget
from ..services import publish_service

router = APIRouter(prefix="/api/publish", tags=["publish"])


class TargetCreate(BaseModel):
    name: str
    platform: str = ""
    token: str = ""
    target_id: str = ""
    enabled: bool = True


class TargetUpdate(BaseModel):
    name: str | None = None
    platform: str | None = None
    token: str | None = None
    target_id: str | None = None
    enabled: bool | None = None


class SendRequest(BaseModel):
    target_id: int  # PublishTarget 的資料庫 id
    text: str


def _get_or_404(session: Session, obj_id: int) -> PublishTarget:
    obj = session.get(PublishTarget, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"找不到發布目標 (id={obj_id})")
    return obj


def _public(t: PublishTarget) -> dict:
    """回傳時遮蔽權杖，僅顯示是否已設定與末四碼。"""
    d = t.model_dump()
    tok = d.pop("token", "")
    d["token_set"] = bool(tok)
    d["token_hint"] = ("…" + tok[-4:]) if tok else ""
    return d


@router.get("/platforms")
def platforms() -> dict:
    return {"platforms": list(publish_service.SUPPORTED_PLATFORMS)}


@router.get("/targets")
def list_targets(session: Session = Depends(get_session)) -> list[dict]:
    targets = session.exec(
        select(PublishTarget).order_by(PublishTarget.created_at)
    ).all()
    return [_public(t) for t in targets]


@router.post("/targets", status_code=201)
def create_target(
    data: TargetCreate, session: Session = Depends(get_session)
) -> dict:
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="名稱不可空白")
    target = PublishTarget(
        name=name,
        platform=data.platform,
        token=data.token,
        target_id=data.target_id,
        enabled=data.enabled,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return _public(target)


@router.patch("/targets/{tid}")
def update_target(
    tid: int, data: TargetUpdate, session: Session = Depends(get_session)
) -> dict:
    target = _get_or_404(session, tid)
    if data.name is not None:
        if not data.name.strip():
            raise HTTPException(status_code=422, detail="名稱不可空白")
        target.name = data.name.strip()
    if data.platform is not None:
        target.platform = data.platform
    if data.token is not None and data.token != "":
        # 空字串視為「不更動權杖」，避免前端不回傳完整權杖時被清空
        target.token = data.token
    if data.target_id is not None:
        target.target_id = data.target_id
    if data.enabled is not None:
        target.enabled = data.enabled
    session.add(target)
    session.commit()
    session.refresh(target)
    return _public(target)


@router.delete("/targets/{tid}", status_code=204)
def delete_target(tid: int, session: Session = Depends(get_session)) -> None:
    target = _get_or_404(session, tid)
    session.delete(target)
    session.commit()


@router.post("/send")
def send(data: SendRequest, session: Session = Depends(get_session)) -> dict:
    target = _get_or_404(session, data.target_id)
    if not target.enabled:
        raise HTTPException(status_code=422, detail="此發布目標已停用")
    ok, message = publish_service.send_text(
        target.platform, target.token, target.target_id, data.text
    )
    if not ok:
        raise HTTPException(status_code=502, detail=f"發布失敗：{message}")
    return {"ok": True, "message": message}
