"""onlyoffice 模块测试：编辑器配置接口。"""
from app.services.docx import make_minimal_docx


def _upload(client, headers):
    return client.post("/api/v1/documents",
                       files={"file": ("协同文档.docx", make_minimal_docx("协同内容"), "application/octet-stream")},
                       headers=headers).json()["id"]


def test_editor_config_unavailable(client, admin_headers):
    """未配置 ONLYOFFICE 时应降级为不可用提示，不崩溃。"""
    doc_id = _upload(client, admin_headers)
    r = client.get(f"/api/v1/onlyoffice/documents/{doc_id}/editor-config", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["available"] is False
    assert r.json()["doc"]["name"] == "协同文档"


def test_editor_config_enabled(client, admin_headers, monkeypatch):
    """ONLYOFFICE 启用后编辑器配置应正常返回（title 字段）。"""
    from app.api.v1 import onlyoffice as oo
    monkeypatch.setattr(oo, "ONLYOFFICE_URL", "http://onlyoffice:8888")
    doc_id = _upload(client, admin_headers)
    r = client.get(f"/api/v1/onlyoffice/documents/{doc_id}/editor-config", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["available"] is True
    assert r.json()["config"]["document"]["title"] == "协同文档.docx"


def test_editor_config_guest_401(client):
    r = client.get("/api/v1/onlyoffice/documents/1/editor-config")
    assert r.status_code == 401
