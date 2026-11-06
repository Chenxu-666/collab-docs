"""安全专项测试：密码哈希、路径穿越、内容令牌、鉴权边界。"""
import pytest

from app.core.security import hash_password, sign_content_token, verify_password
from app.storage.backend import storage


def test_password_hash_salted():
    """PBKDF2 加盐：相同密码两次哈希结果不同。"""
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    assert h1 != h2
    assert h1.startswith("pbkdf2$120000$")


def test_password_verify():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
    assert verify_password("wrong", h) is False


def test_password_not_plaintext():
    h = hash_password("secret123")
    assert "secret123" not in h


def test_storage_path_traversal_blocked():
    """存储接口拒绝路径穿越。"""
    with pytest.raises(ValueError):
        storage._path("../etc/passwd")


def test_content_token_mismatch_403(client):
    """内容令牌与文档不匹配时拒绝访问。"""
    token = sign_content_token(1, 1)
    r = client.get("/api/v1/documents/2/content", params={"token": token, "version": 1})
    assert r.status_code == 403


def test_content_token_invalid_403(client):
    r = client.get("/api/v1/documents/1/content", params={"token": "not-a-token", "version": 1})
    assert r.status_code == 403


def test_content_token_valid_returns_file(client):
    """合法内容令牌可拉取文档（OnlyOffice 无登录拉取）。"""
    token = sign_content_token(1, 1)
    r = client.get("/api/v1/documents/1/content", params={"token": token, "version": 1})
    assert r.status_code == 200
    assert len(r.content) > 0
