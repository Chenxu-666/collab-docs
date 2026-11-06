import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...core.ratelimit import login_limiter, register_limiter
from ...core.security import create_access_token, hash_password, verify_password
from ...db import get_db
from ...models import ROLE_USER, USER_PENDING, User
from ...schemas import ChangePasswordRequest, LoginRequest, RegisterRequest, UserOut
from ...services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


def _user_out(u: User) -> dict:
    return UserOut.model_validate(u).model_dump(mode="json")


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db), request: Request = None):
    ip = request.client.host if request else "unknown"
    key = f"login:{ip}:{body.username}"
    locked, remain = login_limiter.is_locked(key)
    if locked:
        raise HTTPException(429, f"登录失败次数过多，请 {remain} 秒后再试")
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        login_limiter.record_failure(key)
        record_audit(db, None, "login_failed", "account", object_name=body.username,
                     detail={"reason": "bad_credentials"},
                     ip=ip)
        raise HTTPException(401, "账号或密码错误")
    if user.status == USER_PENDING:
        raise HTTPException(403, "账号正在等待管理员审批，请耐心等待")
    if user.status == "rejected":
        raise HTTPException(403, f"注册申请已被拒绝：{user.rejected_reason or '请联系管理员'}")
    if user.status == "disabled":
        raise HTTPException(403, "账号已停用，请联系管理员")
    login_limiter.reset(key)
    token = create_access_token(user.id, user.role)
    record_audit(db, user, "login", "account", user.id, user.username,
                 ip=ip)
    return {
        "access_token": token,
        "must_change_pwd": user.must_change_pwd,
        "user": _user_out(user),
    }


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db), request: Request = None):
    """公开自助注册：生成待审批账号，由超级管理员审批后启用。"""
    ip = request.client.host if request else "unknown"
    locked, remain = register_limiter.is_locked(f"register:{ip}")
    if locked:
        raise HTTPException(429, f"操作过于频繁，请 {remain} 秒后再试")
    username = body.username.strip()
    if not _USERNAME_RE.match(username):
        raise HTTPException(400, "账号需为 3-32 位字母、数字、下划线、点或横线")
    if len(body.password) < 6:
        raise HTTPException(400, "密码长度至少 6 位")
    exists = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if exists:
        raise HTTPException(409, "该账号已存在")
    display_name = body.display_name.strip() or username
    u = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(body.password),
        role=ROLE_USER,
        status=USER_PENDING,
        must_change_pwd=False,
    )
    db.add(u)
    db.flush()
    record_audit(db, None, "register", "account", u.id, username,
                 detail={"display_name": display_name},
                 ip=request.client.host if request else "")
    return {"message": "注册成功，请等待超级管理员审批"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    if len(body.new_password) < 6:
        raise HTTPException(400, "新密码长度至少 6 位")
    user.password_hash = hash_password(body.new_password)
    user.must_change_pwd = False
    db.commit()
    return {"message": "密码已修改"}
