"""audit 模块测试：审计记录、只增不删、访问控制、过滤。"""


def test_upload_records_audit(client, admin_headers):
    client.post("/api/v1/documents", files={"file": ("审计测试.docx", b"x", "application/octet-stream")}, headers=admin_headers)
    logs = client.get("/api/v1/audit-logs", headers=admin_headers).json()
    actions = [l["action"] for l in logs]
    assert "upload" in actions


def test_guest_cannot_read_audit(client):
    r = client.get("/api/v1/audit-logs")
    assert r.status_code == 401


def test_user_cannot_read_audit(client, user_headers):
    r = client.get("/api/v1/audit-logs", headers=user_headers)
    assert r.status_code == 403


def test_audit_append_only(client, admin_headers):
    """删除操作后，历史审计日志仍保留（只增不删）。"""
    doc_id = client.post("/api/v1/documents", files={"file": ("留痕.docx", b"x", "application/octet-stream")}, headers=admin_headers).json()["id"]
    client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    logs = client.get("/api/v1/audit-logs", headers=admin_headers).json()
    actions = [l["action"] for l in logs]
    assert "upload" in actions  # 上传记录仍在


def test_login_failed_recorded(client, admin_headers):
    client.post("/api/v1/auth/login", json={"username": "001", "password": "bad"})
    logs = client.get("/api/v1/audit-logs", headers=admin_headers).json()
    assert any(l["action"] == "login_failed" for l in logs)


def test_filter_by_action(client, admin_headers):
    client.post("/api/v1/documents", files={"file": ("过滤.docx", b"x", "application/octet-stream")}, headers=admin_headers)
    logs = client.get("/api/v1/audit-logs", params={"action": "upload"}, headers=admin_headers).json()
    assert all(l["action"] == "upload" for l in logs)
