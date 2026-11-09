import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET, ONLYOFFICE_SECRET

_PBKDF2_ITERATIONS = 120000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def random_password(length: int = 16) -> str:
    """生成随机的初始密码，包含大小写字母与数字。"""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(alphabet[os.urandom(1)[0] % len(alphabet)] for _ in range(length))


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except Exception:
        return False


def _password_stamp(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:24]


def create_access_token(user_id: int, role: str, password_hash: str = "") -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "pwd": _password_stamp(password_hash) if password_hash else "",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def password_stamp_matches(payload: dict, password_hash: str) -> bool:
    """改密或重置密码后，旧令牌立即失效。"""
    return hmac.compare_digest(payload.get("pwd", ""), _password_stamp(password_hash))


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def sign_content_token(doc_id: int, version: int, access: str = "admin") -> str:
    """签发短期文档内容访问令牌（供 OnlyOffice 服务器直接拉取文件，无需登录）。"""
    payload = {
        "doc_id": doc_id,
        "version": version,
        "access": access,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_content_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def sign_onlyoffice_payload(payload: dict) -> str:
    return jwt.encode(payload, ONLYOFFICE_SECRET, algorithm="HS256")


def verify_onlyoffice_payload(token: str) -> dict:
    return jwt.decode(token, ONLYOFFICE_SECRET, algorithms=["HS256"])
