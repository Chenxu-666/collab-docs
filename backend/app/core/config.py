import logging
import os
from pathlib import Path


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

DATABASE_URL = _get("DATABASE_URL", "sqlite:///./collab_docs.db")
# Railway MySQL 插件的 MYSQL_URL 形如 mysql://...，SQLAlchemy 需显式指定 pymysql 驱动
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
_DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-in-production-1234567890"
JWT_SECRET = _get("JWT_SECRET", _DEV_JWT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(_get("JWT_EXPIRE_MINUTES", "10080"))

FILE_ROOT = Path(_get("FILE_ROOT", str(BASE_DIR / "data" / "files")))
FILE_ROOT.mkdir(parents=True, exist_ok=True)

ONLYOFFICE_URL = _get("ONLYOFFICE_URL", "").rstrip("/")
ONLYOFFICE_SECRET = _get("ONLYOFFICE_SECRET", "onlyoffice-shared-secret")
APP_BASE_URL = _get("APP_BASE_URL", "http://localhost:8000").rstrip("/")

CORS_ORIGINS = [o.strip() for o in _get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

# 登录限流：窗口内失败 N 次 → 锁定
RATE_LIMIT_MAX_ATTEMPTS = int(_get("RATE_LIMIT_MAX_ATTEMPTS", "5"))
RATE_LIMIT_WINDOW = int(_get("RATE_LIMIT_WINDOW", "300"))
RATE_LIMIT_LOCK = int(_get("RATE_LIMIT_LOCK", "900"))

# 生产环境安全校验
ENV = _get("ENV", "dev")
if ENV == "prod":
    if JWT_SECRET == _DEV_JWT_SECRET:
        raise RuntimeError("生产环境(ENV=prod)必须通过环境变量 JWT_SECRET 设置强随机密钥")
    if len(JWT_SECRET) < 32:
        raise RuntimeError("生产环境 JWT_SECRET 长度不得少于 32 字符")
else:
    if JWT_SECRET == _DEV_JWT_SECRET:
        logging.getLogger("app.config").warning("JWT_SECRET 使用默认开发值，生产环境务必设置强随机密钥")
