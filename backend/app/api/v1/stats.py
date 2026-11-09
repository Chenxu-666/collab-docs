from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.deps import require_admin
from ...db import get_db
from ...models import (
    STATUS_DRAFT, STATUS_PUBLISHED, STATUS_TRASHED,
    Album, AuditLog, Document, Image, Pitfall, User,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def overview(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc_total = db.execute(select(func.count(Document.id)).where(Document.status != STATUS_TRASHED)).scalar_one()
    doc_pub = db.execute(select(func.count(Document.id)).where(Document.status == STATUS_PUBLISHED)).scalar_one()
    doc_draft = db.execute(select(func.count(Document.id)).where(Document.status == STATUS_DRAFT)).scalar_one()
    img_total = db.execute(select(func.count(Image.id)).where(Image.status != STATUS_TRASHED)).scalar_one()
    img_pub = db.execute(select(func.count(Image.id)).where(Image.status == STATUS_PUBLISHED)).scalar_one()
    pit_total = db.execute(select(func.count(Pitfall.id)).where(Pitfall.status != STATUS_TRASHED)).scalar_one()
    pit_pub = db.execute(select(func.count(Pitfall.id)).where(Pitfall.status == STATUS_PUBLISHED)).scalar_one()
    album_count = db.execute(select(func.count(Album.id))).scalar_one()
    trash_count = (db.execute(select(func.count(Document.id)).where(Document.status == STATUS_TRASHED)).scalar_one()
                   + db.execute(select(func.count(Image.id)).where(Image.status == STATUS_TRASHED)).scalar_one()
                   + db.execute(select(func.count(Pitfall.id)).where(Pitfall.status == STATUS_TRASHED)).scalar_one())
    pending_count = db.execute(select(func.count(User.id)).where(User.status == "pending")).scalar_one()

    week_ago = datetime.now() - timedelta(days=7)
    week_edit = db.execute(select(func.count(AuditLog.id)).where(
        AuditLog.action.in_(["edit", "upload", "rollback"]), AuditLog.created_at >= week_ago)).scalar_one()
    week_publish = db.execute(select(func.count(AuditLog.id)).where(
        AuditLog.action == "publish", AuditLog.created_at >= week_ago)).scalar_one()

    return {
        "document_total": doc_total, "document_published": doc_pub, "document_draft": doc_draft,
        "image_total": img_total, "image_published": img_pub,
        "pitfall_total": pit_total, "pitfall_published": pit_pub,
        "album_count": album_count, "trash_count": trash_count, "pending_count": pending_count,
        "week_edit": week_edit, "week_publish": week_publish,
    }


@router.get("/trends")
def trends(days: int = 30, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """近 N 天发布/编辑/上传趋势（按日聚合）。"""
    days = max(1, min(days, 90))
    start = datetime.now() - timedelta(days=days)
    rows = db.execute(
        select(AuditLog.action, AuditLog.created_at).where(AuditLog.created_at >= start)
    ).all()
    # 按完整日期键聚合，避免跨年时按 "%m-%d" 字符串排序错乱。
    buckets = {}
    for i in range(days):
        d = (datetime.now() - timedelta(days=i)).date()
        buckets[d] = {"publish": 0, "edit": 0, "upload": 0}
    for action, created in rows:
        if action not in ("publish", "edit", "upload"):
            continue
        d = created.date()
        if d in buckets:
            buckets[d][action] += 1
    ordered = sorted(buckets.keys())
    labels = [d.strftime("%m-%d") for d in ordered]
    return {
        "labels": labels,
        "publish": [buckets[d]["publish"] for d in ordered],
        "edit": [buckets[d]["edit"] for d in ordered],
        "upload": [buckets[d]["upload"] for d in ordered],
    }
