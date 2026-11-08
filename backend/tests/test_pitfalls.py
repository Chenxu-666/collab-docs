"""pitfalls 模块测试：创建校验、状态机、游客可见性、输入健壮性。"""


def test_create_requires_title(client, admin_headers):
    r = client.post("/api/v1/pitfalls", json={"advice": "建议"}, headers=admin_headers)
    assert r.status_code == 400
    assert "标题" in r.json()["detail"]


def test_create_requires_advice(client, admin_headers):
    r = client.post("/api/v1/pitfalls", json={"title": "只有标题"}, headers=admin_headers)
    assert r.status_code == 400


def test_create_success(client, admin_headers):
    r = client.post("/api/v1/pitfalls", json={
        "title": "闭水试验别省时间", "advice": "至少48小时", "risk_level": "high",
        "stage": "验收", "category": "防水",
    }, headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "draft"
    assert body["risk_level"] == "high"


def test_invalid_risk_falls_to_medium(client, admin_headers):
    r = client.post("/api/v1/pitfalls", json={"title": "风险非法", "advice": "建议", "risk_level": "critical"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["risk_level"] == "medium"


def test_title_too_long_400(client, admin_headers):
    r = client.post("/api/v1/pitfalls", json={"title": "长" * 101, "advice": "建议"}, headers=admin_headers)
    assert r.status_code == 400


def test_publish_visible_to_guest(client, admin_headers):
    pit_id = client.post("/api/v1/pitfalls", json={"title": "发布项", "advice": "建议"}, headers=admin_headers).json()["id"]
    client.post(f"/api/v1/pitfalls/{pit_id}/publish", headers=admin_headers)
    visible = [p["id"] for p in client.get("/api/v1/pitfalls").json()]
    assert pit_id in visible


def test_draft_hidden_from_guest(client, admin_headers):
    pit_id = client.post("/api/v1/pitfalls", json={"title": "草稿项", "advice": "建议"}, headers=admin_headers).json()["id"]
    visible = [p["id"] for p in client.get("/api/v1/pitfalls").json()]
    assert pit_id not in visible


def test_trash_restore(client, admin_headers):
    pit_id = client.post("/api/v1/pitfalls", json={"title": "回收项", "advice": "建议"}, headers=admin_headers).json()["id"]
    client.delete(f"/api/v1/pitfalls/{pit_id}", headers=admin_headers)
    trash = [p["id"] for p in client.get("/api/v1/pitfalls/trash", headers=admin_headers).json()]
    assert pit_id in trash
    r = client.post(f"/api/v1/pitfalls/{pit_id}/restore", headers=admin_headers)
    assert r.json()["status"] == "draft"


def test_related_ids_non_numeric_should_400(client, admin_headers):
    """输入健壮性：非数字关联 ID 应返回 400 而非 500。"""
    r = client.post("/api/v1/pitfalls", json={
        "title": "关联校验", "advice": "建议",
        "related_image_ids": ["abc"],
    }, headers=admin_headers)
    assert r.status_code == 400
