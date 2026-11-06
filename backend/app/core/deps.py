from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ROLE_ADMIN, ROLE_SUPER_ADMIN, User
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


def _resolve_user(cred: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if cred is None:
        return None
    try:
        payload = decode_token(cred.credentials)
    except Exception:
        return None
    user = db.get(User, int(payload["sub"]))
    if user is None:
        return None
    return user


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = _resolve_user(cred, db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或登录已过期")
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号未激活或已停用")
    return user


def get_current_user_optional(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """可选鉴权：游客返回 None，登录返回 User。"""
    user = _resolve_user(cred, db)
    if user is None:
        return None
    if user.status != "active":
        return None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (ROLE_ADMIN, ROLE_SUPER_ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "当前账号无此权限")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅超级管理员可执行此操作")
    return user
