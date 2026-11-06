"""pytest 全局配置：隔离测试数据库与文件目录，避免污染开发数据。

关键点：必须在 import app 之前设置 DATABASE_URL / FILE_ROOT，
因为 db.py 在 import 时即创建 engine，config.py 在 import 时读取环境变量。
"""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="dreamhouse_qa_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["FILE_ROOT"] = str(_TMP / "files")
os.environ["JWT_SECRET"] = "qa-test-secret"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_if_empty

# 测试种子账号（来自 seed.py）
SUPER_USERNAME = "001"
SUPER_PASSWORD = "WENjing970217"
ADMIN_USERNAME = "002"
ADMIN_PASSWORD = "WENjing521"


@pytest.fixture(autouse=True)
def _reset_db():
    """每个测试用例前重建数据库并注入种子数据。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    # 不使用 with（避免触发 lifespan 二次 seed），由 _reset_db 负责建库
    return TestClient(app)


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"登录失败: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def super_headers(client):
    return _login(client, SUPER_USERNAME, SUPER_PASSWORD)


@pytest.fixture
def admin_headers(client):
    return _login(client, ADMIN_USERNAME, ADMIN_PASSWORD)


@pytest.fixture
def user_headers(client, super_headers):
    """创建一个已审批的普通用户并登录。"""
    r = client.post(
        "/api/v1/accounts/single",
        json={"username": "qa_user", "display_name": "测试用户"},
        headers=super_headers,
    )
    assert r.status_code == 200, f"创建普通用户失败: {r.text}"
    return _login(client, "qa_user", "qa_user@123")
