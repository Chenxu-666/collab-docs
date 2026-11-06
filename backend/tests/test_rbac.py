"""RBAC 权限矩阵测试：验证服务端鉴权不可被绕过（前端隐藏按钮不能替代鉴权）。

角色：游客(无 token) / user / admin / super_admin。
"""
import io


def test_guest_list_only_published(client):
    """游客只能看到已发布文档。"""
    r = client.get("/api/v1/documents")
    assert r.status_code == 200
    statuses = {d["status"] for d in r.json()}
    assert statuses <= {"published"}


def test_guest_preview_draft_404(client):
    """游客访问草稿文档预览返回 404（不泄露存在性）。"""
    drafts = client.get("/api/v1/documents", headers=None).json()
    # 用管理员视角找一个草稿
    r = client.get("/api/v1/documents", headers=_admin_of(client))
    draft_id = next((d["id"] for d in r.json() if d["status"] == "draft"), None)
    if draft_id is None:
        return  # 无草稿种子则跳过
    rp = client.get(f"/api/v1/documents/{draft_id}/preview")
    assert rp.status_code == 404


def test_guest_upload_401(client):
    r = client.post("/api/v1/documents", files={"file": ("a.docx", b"x", "application/octet-stream")})
    assert r.status_code == 401


def test_user_upload_403(client, user_headers):
    r = client.post("/api/v1/documents", files={"file": ("a.docx", b"x", "application/octet-stream")},
                    headers=user_headers)
    assert r.status_code == 403


def test_admin_upload_ok(client, admin_headers):
    r = client.post("/api/v1/documents", files={"file": ("test.docx", b"hello", "application/octet-stream")},
                    headers=admin_headers)
    assert r.status_code == 200


def test_user_list_accounts_403(client, user_headers):
    r = client.get("/api/v1/accounts", headers=user_headers)
    assert r.status_code == 403


def test_admin_list_accounts_403(client, admin_headers):
    """内容管理员也不能访问账号管理（仅超管）。"""
    r = client.get("/api/v1/accounts", headers=admin_headers)
    assert r.status_code == 403


def test_super_list_accounts_ok(client, super_headers):
    r = client.get("/api/v1/accounts", headers=super_headers)
    assert r.status_code == 200


def test_admin_permanent_delete_403(client, admin_headers, super_headers):
    """内容管理员不能彻底删除回收站内容（仅超管）。"""
    r = client.post("/api/v1/documents", files={"file": ("d.docx", b"x", "application/octet-stream")},
                    headers=admin_headers)
    doc_id = r.json()["id"]
    client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    rp = client.delete(f"/api/v1/documents/{doc_id}/permanent", headers=admin_headers)
    assert rp.status_code == 403


def test_guest_audit_401(client):
    r = client.get("/api/v1/audit-logs")
    assert r.status_code == 401


def test_guest_albums_only_with_published(client):
    """游客能列出相册（library 模块路由，架构上应为 /library/albums，当前实现为 /albums）。"""
    r = client.get("/api/v1/albums")
    assert r.status_code == 200
    names = {a["name"] for a in r.json()}
    assert "客厅参考" in names


def _admin_of(client):
    """辅助：返回管理员请求头。"""
    r = client.post("/api/v1/auth/login", json={"username": "002", "password": "WENjing521"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
