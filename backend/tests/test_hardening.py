"""针对安全加固的回归测试：生产种子、OnlyOffice 回调鉴权、版本令牌、强制改密。"""
from app import seed as seed_module
from app.db import Base, SessionLocal, engine
from app.models import DocumentVersion, User
from app.services.docx import make_minimal_docx


def _upload_draft(client, admin_headers):
    return client.post(
        "/api/v1/documents",
        files={"file": ("草稿.docx", make_minimal_docx("草稿内容"), "application/octet-stream")},
        headers=admin_headers,
    ).json()["id"]


def test_prod_seed_creates_no_default_account(client, monkeypatch):
    """生产环境空库不得自动创建公开的演示管理员。"""
    monkeypatch.setattr(seed_module, "ENV", "prod")
    monkeypatch.setattr(seed_module, "INITIAL_SUPER_ADMIN_USERNAME", "")
    monkeypatch.setattr(seed_module, "INITIAL_SUPER_ADMIN_PASSWORD", "")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_module.seed_if_empty(db)
        assert db.query(User).count() == 0
    finally:
        db.close()


def test_onlyoffice_callback_requires_token(client, admin_headers):
    """未带有效 JWT 的回调不得写入新版本。"""
    doc_id = _upload_draft(client, admin_headers)
    r = client.post("/api/v1/onlyoffice/callback", json={
        "status": 2, "key": f"{doc_id}:v1", "url": "http://localhost:8000/api/health",
    })
    assert r.status_code == 200
    assert r.json()["error"] == 1
    versions = client.get(f"/api/v1/documents/{doc_id}/versions", headers=admin_headers).json()
    assert [v["version_no"] for v in versions] == [1]


def test_normal_user_cannot_open_draft_editor(client, admin_headers, user_headers):
    """普通用户不能通过 OnlyOffice 编辑器配置读取草稿。"""
    doc_id = _upload_draft(client, admin_headers)
    r = client.get(f"/api/v1/onlyoffice/documents/{doc_id}/editor-config", headers=user_headers)
    assert r.status_code == 404


def test_content_token_version_mismatch_403(client):
    from app.core.security import sign_content_token
    token = sign_content_token(1, 1)
    r = client.get("/api/v1/documents/1/content", params={"token": token, "version": 2})
    assert r.status_code == 403


def test_must_change_pwd_blocks_api_until_changed(client, super_headers):
    """未改密账号只能改密，不能访问其他受保护接口。"""
    created = client.post("/api/v1/accounts/single",
                          json={"username": "forcepw", "display_name": "强改"},
                          headers=super_headers).json()
    initial = created["created"][0]["initial_password"]
    login = client.post("/api/v1/auth/login", json={"username": "forcepw", "password": initial})
    assert login.json()["must_change_pwd"] is True
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 403
    r = client.post("/api/v1/auth/change-password",
                    json={"old_password": initial, "new_password": "changed123"}, headers=headers)
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401  # 旧令牌已因改密失效


def test_old_token_invalid_after_password_change(client, super_headers):
    """改密后旧令牌立即失效。"""
    created = client.post("/api/v1/accounts/single",
                          json={"username": "oldtok", "display_name": "旧令"},
                          headers=super_headers).json()
    initial = created["created"][0]["initial_password"]
    login = client.post("/api/v1/auth/login", json={"username": "oldtok", "password": initial})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/auth/change-password",
                json={"old_password": initial, "new_password": "changed123"}, headers=headers)
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
