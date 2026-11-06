from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.deps import require_admin
from ...db import get_db
from ...models import AuditLog, User
from ...schemas import AuditOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_logs(
    q: str = "",
    action: str = "",
    object_type: str = "",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(500)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if object_type:
        stmt = stmt.where(AuditLog.object_type == object_type)
    rows = db.execute(stmt).scalars().all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.username.lower() or ql in r.object_name.lower()]
    return rows
