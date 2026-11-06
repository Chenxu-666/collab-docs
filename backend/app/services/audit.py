import json

from sqlalchemy.orm import Session

from ..models import AuditLog, User


def record_audit(
    db: Session,
    user: User | None,
    action: str,
    object_type: str,
    object_id: int | None = None,
    object_name: str = "",
    detail: dict | None = None,
    ip: str = "",
):
    log = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "系统",
        action=action,
        object_type=object_type,
        object_id=object_id,
        object_name=object_name,
        detail=json.dumps(detail or {}, ensure_ascii=False),
        ip=ip or "",
    )
    db.add(log)
    db.commit()
