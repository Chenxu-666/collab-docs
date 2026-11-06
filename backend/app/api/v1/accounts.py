from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.deps import require_super_admin
from ...core.security import hash_password
from ...db import get_db
from ...models import ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER, USER_ACTIVE, USER_DISABLED, USER_PENDING, USER_REJECTED, User
from ...schemas import AccountCreate, BatchAccountCreate, UserOut
from ...services.audit import record_audit

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[UserOut])
def list_accounts(admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.execute(select(User).order_by(User.role.desc(), User.id)).scalars().all()


@router.get("/pending", response_model=list[UserOut])
def list_pending(admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.execute(
        select(User).where(User.status == USER_PENDING).order_by(User.id.desc())
    ).scalars().all()


@router.post("/{account_id}/approve")
def approve_account(account_id: int, admin: User = Depends(require_super_admin),
                    db: Session = Depends(get_db), request: Request = None):
    u = db.get(User, account_id)
    if u is None:
        raise HTTPException(404, "账号不存在")
    if u.status != USER_PENDING:
        raise HTTPException(400, "该账号不在待审批状态")
    u.status = USER_ACTIVE
    record_audit(db, admin, "account_approve", "account", u.id, u.username,
                 detail={"role": u.role}, ip=request.client.host if request else "")
    db.commit()
    return {"message": "已通过审批"}


@router.post("/{account_id}/reject")
def reject_account(account_id: int, body: dict | None = None,
                   admin: User = Depends(require_super_admin),
                   db: Session = Depends(get_db), request: Request = None):
    u = db.get(User, account_id)
    if u is None:
        raise HTTPException(404, "账号不存在")
    if u.status != USER_PENDING:
        raise HTTPException(400, "该账号不在待审批状态")
    reason = (body or {}).get("reason", "") if isinstance(body, dict) else ""
    u.status = USER_REJECTED
    u.rejected_reason = reason[:200]
    record_audit(db, admin, "account_reject", "account", u.id, u.username,
                 detail={"reason": reason}, ip=request.client.host if request else "")
    db.commit()
    return {"message": "已拒绝该申请"}


@router.post("/batch")
def batch_create(
    body: BatchAccountCreate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    created = []
    for item in body.items:
        if not item.username.strip():
            continue
        uname = item.username.strip()
        exists = db.execute(select(User).where(User.username == uname)).scalar_one_or_none()
        if exists:
            continue
        initial_pwd = uname + "@123"
        u = User(
            username=uname,
            display_name=item.display_name.strip() or uname,
            password_hash=hash_password(initial_pwd),
            role=ROLE_USER,
            status=USER_ACTIVE,
            must_change_pwd=True,
            created_by=admin.id,
        )
        db.add(u)
        db.flush()
        created.append({"username": u.username, "initial_password": initial_pwd})
    record_audit(db, admin, "account_op", "account",
                 detail={"type": "batch_create", "count": len(created)},
                 ip=request.client.host if request else "")
    db.commit()
    return {"created": created}


@router.post("/single")
def single_create(body: AccountCreate, admin: User = Depends(require_super_admin),
                  db: Session = Depends(get_db), request: Request = None):
    return batch_create(BatchAccountCreate(items=[body]), admin, db, request)


@router.post("/admin")
def create_admin(body: dict, admin: User = Depends(require_super_admin),
                 db: Session = Depends(get_db), request: Request = None):
    """超级管理员创建内容管理员账号。"""
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    display_name = (body.get("display_name") or "").strip() or username
    if not username or len(password) < 6:
        raise HTTPException(400, "账号不能为空且密码至少 6 位")
    if db.execute(select(User).where(User.username == username)).scalar_one_or_none():
        raise HTTPException(409, "账号已存在")
    u = User(username=username, display_name=display_name,
             password_hash=hash_password(password), role=ROLE_ADMIN,
             status=USER_ACTIVE, created_by=admin.id)
    db.add(u)
    db.flush()
    record_audit(db, admin, "account_op", "account", u.id, username,
                 detail={"type": "create_admin"}, ip=request.client.host if request else "")
    db.commit()
    return UserOut.model_validate(u).model_dump(mode="json")


@router.patch("/{account_id}")
def update_account(account_id: int, body: dict,
                   admin: User = Depends(require_super_admin),
                   db: Session = Depends(get_db), request: Request = None):
    u = db.get(User, account_id)
    if u is None:
        raise HTTPException(404, "账号不存在")
    if u.id == admin.id:
        raise HTTPException(400, "不能操作当前登录账号")
    if u.role == ROLE_SUPER_ADMIN:
        # 不允许停用/降级最后一个超级管理员
        others = db.execute(
            select(User).where(User.role == ROLE_SUPER_ADMIN, User.id != u.id)
        ).scalars().all()
        if not others:
            raise HTTPException(400, "不能停用最后一个超级管理员")
    if "status" in body:
        s = body["status"]
        u.status = s if s in (USER_ACTIVE, USER_DISABLED) else u.status
    if "role" in body and body["role"] in (ROLE_USER, ROLE_ADMIN):
        u.role = body["role"]
    if body.get("reset_password"):
        u.password_hash = hash_password(u.username + "@123")
        u.must_change_pwd = True
    record_audit(db, admin, "account_op", "account", account_id, u.username,
                 detail={"op": "update", "patch": {k: v for k, v in body.items() if k != "reset_password"}},
                 ip=request.client.host if request else "")
    db.commit()
    return {"message": "已更新"}
