"""auth 模块测试：登录、注册、改密码、身份识别。

覆盖 FR：登录鉴权、待审批/拒绝/停用账号拦截、公开自助注册。
"""
from app.models import USER_PENDING, USER_REJECTED, User


def test_login_success_super_admin(client):
    """AAA：管理员登录成功返回 token 与用户信息。"""
    r = client.post("/api/v1/auth/login", json={"username": "001", "password": "WENjing970217"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["username"] == "001"
    assert body["user"]["role"] == "super_admin"


def test_login_wrong_password_401(client):
    r = client.post("/api/v1/auth/login", json={"username": "001", "password": "wrong-pass"})
    assert r.status_code == 401


def test_login_unknown_user_401(client):
    r = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "whatever"})
    assert r.status_code == 401


def test_login_pending_403(client, super_headers):
    """待审批账号无法登录，返回明确原因。"""
    client.post("/api/v1/auth/register", json={"username": "pendinguser", "password": "123456", "display_name": "待审批"})
    r = client.post("/api/v1/auth/login", json={"username": "pendinguser", "password": "123456"})
    assert r.status_code == 403
    assert "审批" in r.json()["detail"]


def test_login_rejected_403(client, super_headers):
    """被拒绝账号登录返回拒绝原因。"""
    client.post("/api/v1/auth/register", json={"username": "rejecteduser", "password": "123456"})
    # 找到待审批账号并拒绝
    pending = client.get("/api/v1/accounts/pending", headers=super_headers).json()
    uid = [u for u in pending if u["username"] == "rejecteduser"][0]["id"]
    client.post(f"/api/v1/accounts/{uid}/reject", json={"reason": "身份不符"}, headers=super_headers)
    r = client.post("/api/v1/auth/login", json={"username": "rejecteduser", "password": "123456"})
    assert r.status_code == 403
    assert "身份不符" in r.json()["detail"]


def test_login_disabled_403(client, super_headers):
    """停用账号登录返回 403。"""
    created = client.post("/api/v1/accounts/single", json={"username": "disableduser", "display_name": "停用"}, headers=super_headers).json()
    initial_pwd = created["created"][0]["initial_password"]
    accounts = client.get("/api/v1/accounts", headers=super_headers).json()
    uid = [u for u in accounts if u["username"] == "disableduser"][0]["id"]
    client.patch(f"/api/v1/accounts/{uid}", json={"status": "disabled"}, headers=super_headers)
    r = client.post("/api/v1/auth/login", json={"username": "disableduser", "password": initial_pwd})
    assert r.status_code == 403


def test_register_creates_pending(client):
    """公开注册成功后账号处于待审批状态。"""
    r = client.post("/api/v1/auth/register", json={"username": "newbie", "password": "abc123", "display_name": "新同学"})
    assert r.status_code == 200
    # 待审批账号无法直接登录
    r2 = client.post("/api/v1/auth/login", json={"username": "newbie", "password": "abc123"})
    assert r2.status_code == 403


def test_register_duplicate_409(client):
    client.post("/api/v1/auth/register", json={"username": "dupuser", "password": "abc123"})
    r = client.post("/api/v1/auth/register", json={"username": "dupuser", "password": "abc123"})
    assert r.status_code == 409


def test_register_invalid_username_400(client):
    r = client.post("/api/v1/auth/register", json={"username": "a", "password": "abc123"})
    assert r.status_code == 400


def test_register_short_password_400(client):
    r = client.post("/api/v1/auth/register", json={"username": "shortpw", "password": "123"})
    assert r.status_code == 400


def test_me_requires_token_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "002"


def test_change_password_success(client, user_headers):
    """改密成功后旧密码失效、新密码可登录。"""
    r = client.post("/api/v1/auth/change-password",
                    json={"old_password": "qa_user@123", "new_password": "newpass123"},
                    headers=user_headers)
    assert r.status_code == 200
    old = client.post("/api/v1/auth/login", json={"username": "qa_user", "password": "qa_user@123"})
    assert old.status_code == 401
    new = client.post("/api/v1/auth/login", json={"username": "qa_user", "password": "newpass123"})
    assert new.status_code == 200


def test_change_password_wrong_old_400(client, admin_headers):
    r = client.post("/api/v1/auth/change-password",
                    json={"old_password": "wrong", "new_password": "newpass123"},
                    headers=admin_headers)
    assert r.status_code == 400
