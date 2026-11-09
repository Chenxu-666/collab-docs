"""accounts 模块测试：注册审批流、批量建号、创建管理员、停用保护。"""
import pytest


def test_register_approve_flow(client, super_headers):
    """完整审批流：注册→待审批→超管通过→可登录。"""
    client.post("/api/v1/auth/register", json={"username": "flowuser", "password": "abc123", "display_name": "流程用户"})
    # 待审批
    pending = client.get("/api/v1/accounts/pending", headers=super_headers).json()
    uid = [u for u in pending if u["username"] == "flowuser"][0]["id"]
    # 通过审批
    r = client.post(f"/api/v1/accounts/{uid}/approve", headers=super_headers)
    assert r.status_code == 200
    # 可登录
    login = client.post("/api/v1/auth/login", json={"username": "flowuser", "password": "abc123"})
    assert login.status_code == 200


def test_reject_records_reason(client, super_headers):
    client.post("/api/v1/auth/register", json={"username": "rejectme", "password": "abc123"})
    pending = client.get("/api/v1/accounts/pending", headers=super_headers).json()
    uid = [u for u in pending if u["username"] == "rejectme"][0]["id"]
    r = client.post(f"/api/v1/accounts/{uid}/reject", json={"reason": "信息不完整"}, headers=super_headers)
    assert r.status_code == 200
    login = client.post("/api/v1/auth/login", json={"username": "rejectme", "password": "abc123"})
    assert login.status_code == 403
    assert "信息不完整" in login.json()["detail"]


def test_approve_non_pending_400(client, super_headers):
    """已激活账号再次审批应 400。"""
    accounts = client.get("/api/v1/accounts", headers=super_headers).json()
    active_id = [u for u in accounts if u["status"] == "active"][0]["id"]
    r = client.post(f"/api/v1/accounts/{active_id}/approve", headers=super_headers)
    assert r.status_code == 400


def test_batch_create(client, super_headers):
    r = client.post("/api/v1/accounts/batch", json={"items": [
        {"username": "batch1", "display_name": "批量一"},
        {"username": "batch2", "display_name": "批量二"},
    ]}, headers=super_headers)
    assert r.status_code == 200
    assert len(r.json()["created"]) == 2
    # 初始密码为随机生成，仅在下发时可见一次
    created = r.json()["created"][0]
    assert created["initial_password"]
    assert created["initial_password"] != "batch1@123"


def test_create_admin_account(client, super_headers):
    r = client.post("/api/v1/accounts/admin", json={"username": "admin2", "password": "abc123", "display_name": "新管理员"}, headers=super_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_disable_account_cannot_login(client, super_headers):
    created = client.post("/api/v1/accounts/single", json={"username": "todisable", "display_name": "停用"}, headers=super_headers).json()
    initial_pwd = created["created"][0]["initial_password"]
    accounts = client.get("/api/v1/accounts", headers=super_headers).json()
    uid = [u for u in accounts if u["username"] == "todisable"][0]["id"]
    r = client.patch(f"/api/v1/accounts/{uid}", json={"status": "disabled"}, headers=super_headers)
    assert r.status_code == 200
    login = client.post("/api/v1/auth/login", json={"username": "todisable", "password": initial_pwd})
    assert login.status_code == 403


def test_cannot_operate_self(client, super_headers):
    """不能停用/修改当前登录账号。"""
    me = client.get("/api/v1/auth/me", headers=super_headers).json()
    r = client.patch(f"/api/v1/accounts/{me['id']}", json={"status": "disabled"}, headers=super_headers)
    assert r.status_code == 400


def test_reset_password_forces_change(client, super_headers):
    client.post("/api/v1/accounts/single", json={"username": "resetme", "display_name": "重置"}, headers=super_headers)
    accounts = client.get("/api/v1/accounts", headers=super_headers).json()
    uid = [u for u in accounts if u["username"] == "resetme"][0]["id"]
    client.patch(f"/api/v1/accounts/{uid}", json={"reset_password": True}, headers=super_headers)
    # 重置后账号被标记为需强制改密（密码已随机化，无法再按旧密码登录）
    accounts = client.get("/api/v1/accounts", headers=super_headers).json()
    u = [u for u in accounts if u["username"] == "resetme"][0]
    assert u["must_change_pwd"] is True
