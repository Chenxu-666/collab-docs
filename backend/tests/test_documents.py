"""documents 模块测试：上传、状态机流转、版本、回收站、预览、下载。

覆盖状态机：draft → published → withdraw → draft；trash → restore → draft。
"""
import io

from app.services.docx import make_minimal_docx


def _upload(client, headers, title="测试文档.docx", content=None):
    data = content if content is not None else make_minimal_docx("测试内容\n第二行")
    return client.post("/api/v1/documents",
                       files={"file": (title, data, "application/octet-stream")},
                       headers=headers)


def test_upload_creates_draft(client, admin_headers):
    r = _upload(client, admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "draft"
    assert body["current_version"] == 1


def test_upload_invalid_ext_400(client, admin_headers):
    r = client.post("/api/v1/documents",
                    files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
                    headers=admin_headers)
    assert r.status_code == 400
    assert "格式" in r.json()["detail"]


def test_publish_then_visible_to_guest(client, admin_headers):
    """发布后游客可见；发布版本号被锁定。"""
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.post(f"/api/v1/documents/{doc_id}/publish", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "published"
    assert r.json()["published_version_no"] == 1
    # 游客可见
    visible = [d["id"] for d in client.get("/api/v1/documents").json()]
    assert doc_id in visible


def test_withdraw_hidden_from_guest(client, admin_headers):
    """撤回后游客立即不可见，管理端保留。"""
    doc_id = _upload(client, admin_headers).json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/publish", headers=admin_headers)
    r = client.post(f"/api/v1/documents/{doc_id}/withdraw", headers=admin_headers)
    assert r.json()["status"] == "draft"
    visible = [d["id"] for d in client.get("/api/v1/documents").json()]
    assert doc_id not in visible


def test_archive(client, admin_headers):
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.post(f"/api/v1/documents/{doc_id}/archive", headers=admin_headers)
    assert r.json()["status"] == "archived"


def test_trash_and_restore_returns_draft(client, admin_headers):
    """删除进回收站；恢复后回 draft，不自动公开。"""
    doc_id = _upload(client, admin_headers).json()["id"]
    client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    # 进入回收站
    trash = client.get("/api/v1/documents/trash", headers=admin_headers).json()
    assert doc_id in [d["id"] for d in trash]
    # 恢复
    r = client.post(f"/api/v1/documents/{doc_id}/restore", headers=admin_headers)
    assert r.json()["status"] == "draft"
    # 游客不可见（未重新发布）
    assert doc_id not in [d["id"] for d in client.get("/api/v1/documents").json()]


def test_permanent_delete_requires_trash(client, super_headers, admin_headers):
    """非回收站内容不可彻底删除。"""
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.delete(f"/api/v1/documents/{doc_id}/permanent", headers=super_headers)
    assert r.status_code == 400


def test_rollback_creates_new_version(client, admin_headers):
    """回滚生成新版本号并更新 current_version。"""
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.post(f"/api/v1/documents/{doc_id}/versions/1/rollback", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["current_version"] == 2


def test_list_versions(client, admin_headers):
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.get(f"/api/v1/documents/{doc_id}/versions", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["version_no"] == 1


def test_download_admin_ok(client, admin_headers):
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.get(f"/api/v1/documents/{doc_id}/download", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.content) > 0


def test_download_guest_401(client, admin_headers):
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.get(f"/api/v1/documents/{doc_id}/download")
    assert r.status_code == 401


def test_preview_extracts_text(client, admin_headers):
    """公开预览返回提取的纯文本。"""
    doc_id = _upload(client, admin_headers, content=make_minimal_docx("预算编制原则\n量价分离")).json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/publish", headers=admin_headers)
    r = client.get(f"/api/v1/documents/{doc_id}/preview")
    assert r.status_code == 200
    assert "预算编制原则" in r.json()["text"]


def test_update_metadata(client, admin_headers):
    doc_id = _upload(client, admin_headers).json()["id"]
    r = client.patch(f"/api/v1/documents/{doc_id}", json={"title": "改名后的文档", "summary": "摘要"},
                     headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "改名后的文档"
    assert r.json()["summary"] == "摘要"


def test_document_not_found_404(client, admin_headers):
    r = client.get("/api/v1/documents/99999/preview", headers=admin_headers)
    assert r.status_code == 404
