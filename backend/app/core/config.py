import logging
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
# 本地开发支持 backend/.env；真实进程环境变量优先，避免覆盖部署平台配置。
load_dotenv(BASE_DIR / ".env", override=False)


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)

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
_DEV_ONLYOFFICE_SECRET = "dev-only-onlyoffice-secret-change-me-1234567890"
ONLYOFFICE_SECRET = _get("ONLYOFFICE_SECRET", _DEV_ONLYOFFICE_SECRET)
APP_BASE_URL = _get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
INITIAL_SUPER_ADMIN_USERNAME = _get("INITIAL_SUPER_ADMIN_USERNAME", "")
INITIAL_SUPER_ADMIN_PASSWORD = _get("INITIAL_SUPER_ADMIN_PASSWORD", "")
INITIAL_SUPER_ADMIN_NAME = _get("INITIAL_SUPER_ADMIN_NAME", "超级管理员")

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
    if ONLYOFFICE_URL and (ONLYOFFICE_SECRET == _DEV_ONLYOFFICE_SECRET or len(ONLYOFFICE_SECRET) < 32):
        raise RuntimeError("生产环境启用 OnlyOffice 时必须设置长度不少于 32 字符的 ONLYOFFICE_SECRET")
else:
    if JWT_SECRET == _DEV_JWT_SECRET:
        logging.getLogger("app.config").warning("JWT_SECRET 使用默认开发值，生产环境务必设置强随机密钥")
