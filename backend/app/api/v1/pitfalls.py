import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.deps import get_current_user_optional, require_admin, require_super_admin
from ...db import get_db
from ...models import (
    STATUS_ARCHIVED, STATUS_DRAFT, STATUS_PUBLISHED, STATUS_TRASHED,
    Document, Image, Pitfall, User,
)
from ...services.audit import record_audit

router = APIRouter(prefix="/pitfalls", tags=["pitfalls"])

RISK_LEVELS = {"high", "medium", "low"}


def _ids(raw: str) -> list[int]:
    try:
        v = json.loads(raw or "[]")
        return [int(x) for x in v] if isinstance(v, list) else []
    except Exception:
        return []


def _pit_out(p: Pitfall, db: Session, admin: bool) -> dict:
    rel_imgs, rel_docs = [], []
    if p.related_image_ids:
        ids = _ids(p.related_image_ids)
        if ids:
            imgs = db.execute(select(Image).where(Image.id.in_(ids))).scalars().all()
            imap = {i.id: i for i in imgs}
            for iid in ids:
                img = imap.get(iid)
                if img and (admin or img.status == STATUS_PUBLISHED):
                    rel_imgs.append({"id": img.id, "title": img.title, "status": img.status})
    if p.related_document_ids:
        ids = _ids(p.related_document_ids)
        if ids:
            docs = db.execute(select(Document).where(Document.id.in_(ids))).scalars().all()
            dmap = {d.id: d for d in docs}
            for did in ids:
                d = dmap.get(did)
                if d and (admin or d.status == STATUS_PUBLISHED):
                    rel_docs.append({"id": d.id, "title": d.title, "status": d.status})
    return {
        "id": p.id, "title": p.title, "stage": p.stage, "category": p.category,
        "problem": p.problem, "advice": p.advice, "risk_level": p.risk_level,
        "source_text": p.source_text, "status": p.status, "sort_order": p.sort_order,
        "is_pinned": p.is_pinned,
        "related_images": rel_imgs, "related_documents": rel_docs,
        "created_by_name": p.creator.display_name if p.creator else "",
        "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat(),
    }


def _visible_statuses(admin: bool) -> list[str]:
    return [STATUS_DRAFT, STATUS_PUBLISHED, STATUS_ARCHIVED] if admin else [STATUS_PUBLISHED]


@router.get("")
def list_pitfalls(
    q: str = "", stage: str = "", category: str = "", risk: str = "", status: str = "",
    user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    admin = user is not None and user.role in ("admin", "super_admin")
    stmt = select(Pitfall).where(Pitfall.status.in_(_visible_statuses(admin)))
    if stage:
        stmt = stmt.where(Pitfall.stage == stage)
    if category:
        stmt = stmt.where(Pitfall.category == category)
    if risk:
        stmt = stmt.where(Pitfall.risk_level == risk)
    if status and admin:
        stmt = stmt.where(Pitfall.status == status)
    stmt = stmt.order_by(Pitfall.is_pinned.desc(), Pitfall.sort_order, Pitfall.id.desc())
    rows = db.execute(stmt).scalars().all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.title.lower() or ql in r.problem.lower() or ql in r.advice.lower()]
    return [_pit_out(r, db, admin) for r in rows]


@router.get("/trash")
def list_trash(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Pitfall).where(Pitfall.status == STATUS_TRASHED).order_by(Pitfall.updated_at.desc())).scalars().all()
    return [_pit_out(r, db, True) for r in rows]


@router.get("/{pit_id}")
def get_pitfall(pit_id: int, user: User | None = Depends(get_current_user_optional),
                db: Session = Depends(get_db)):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    admin = user is not None and user.role in ("admin", "super_admin")
    if not admin and p.status != STATUS_PUBLISHED:
        raise HTTPException(404, "避坑项不存在")
    return _pit_out(p, db, admin)


@router.post("")
def create_pitfall(body: dict, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db), request: Request = None):
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "标题不能为空")
    if len(title) > 100:
        raise HTTPException(400, "标题不超过 100 字")
    advice = (body.get("advice") or "").strip()
    if not advice:
        raise HTTPException(400, "规避建议不能为空")
    risk = body.get("risk_level", "medium")
    if risk not in RISK_LEVELS:
        risk = "medium"
    p = Pitfall(
        title=title,
        stage=(body.get("stage") or "").strip()[:50],
        category=(body.get("category") or "").strip()[:50],
        problem=(body.get("problem") or "").strip(),
        advice=advice,
        risk_level=risk,
        source_text=(body.get("source_text") or "").strip()[:500],
        related_image_ids=json.dumps([int(x) for x in body.get("related_image_ids", []) if x]),
        related_document_ids=json.dumps([int(x) for x in body.get("related_document_ids", []) if x]),
        status=STATUS_DRAFT,
        sort_order=int(body.get("sort_order", 0)),
        is_pinned=bool(body.get("is_pinned", False)),
        created_by=admin.id,
    )
    db.add(p)
    db.flush()
    record_audit(db, admin, "create", "pitfall", p.id, title,
                 ip=request.client.host if request else "")
    db.commit()
    return _pit_out(p, db, True)


@router.patch("/{pit_id}")
def update_pitfall(pit_id: int, body: dict, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db), request: Request = None):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    for k in ("title", "stage", "category", "problem", "advice", "source_text"):
        if k in body:
            setattr(p, k, (body[k] or "").strip())
    if "risk_level" in body and body["risk_level"] in RISK_LEVELS:
        p.risk_level = body["risk_level"]
    if "related_image_ids" in body:
        p.related_image_ids = json.dumps([int(x) for x in body["related_image_ids"] if x])
    if "related_document_ids" in body:
        p.related_document_ids = json.dumps([int(x) for x in body["related_document_ids"] if x])
    if "sort_order" in body:
        p.sort_order = int(body["sort_order"])
    if "is_pinned" in body:
        p.is_pinned = bool(body["is_pinned"])
    record_audit(db, admin, "edit", "pitfall", p.id, p.title,
                 ip=request.client.host if request else "")
    db.commit()
    return _pit_out(p, db, True)


def _transition(p: Pitfall, action: str, admin: User, db: Session, request: Request) -> dict:
    if action == "publish":
        p.status = STATUS_PUBLISHED
    elif action == "withdraw":
        p.status = STATUS_DRAFT
    elif action == "archive":
        p.status = STATUS_ARCHIVED
    elif action == "trash":
        p.status = STATUS_TRASHED
    elif action == "restore":
        p.status = STATUS_DRAFT
    else:
        raise HTTPException(400, "未知操作")
    record_audit(db, admin, action, "pitfall", p.id, p.title,
                 ip=request.client.host if request else "")
    db.commit()
    return _pit_out(p, db, True)


@router.post("/{pit_id}/publish")
def publish_pitfall(pit_id: int, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db), request: Request = None):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    return _transition(p, "publish", admin, db, request)


@router.post("/{pit_id}/withdraw")
def withdraw_pitfall(pit_id: int, admin: User = Depends(require_admin),
                     db: Session = Depends(get_db), request: Request = None):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    return _transition(p, "withdraw", admin, db, request)


@router.delete("/{pit_id}")
def trash_pitfall(pit_id: int, admin: User = Depends(require_admin),
                  db: Session = Depends(get_db), request: Request = None):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    return _transition(p, "trash", admin, db, request)


@router.post("/{pit_id}/restore")
def restore_pitfall(pit_id: int, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db), request: Request = None):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    return _transition(p, "restore", admin, db, request)


@router.delete("/{pit_id}/permanent")
def permanent_delete(pit_id: int, admin: User = Depends(require_super_admin),
                     db: Session = Depends(get_db), request: Request = None):
    p = db.get(Pitfall, pit_id)
    if p is None:
        raise HTTPException(404, "避坑项不存在")
    if p.status != STATUS_TRASHED:
        raise HTTPException(400, "仅回收站中的内容可彻底删除")
    name = p.title
    record_audit(db, admin, "permanent_delete", "pitfall", pit_id, name,
                 ip=request.client.host if request else "")
    db.delete(p)
    db.commit()
    return {"message": "已彻底删除"}
