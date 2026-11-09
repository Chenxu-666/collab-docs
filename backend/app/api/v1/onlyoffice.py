import asyncio
import urllib.request
from datetime import datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import APP_BASE_URL, ONLYOFFICE_URL
from ...core.deps import get_current_user
from ...core.security import (
    sign_content_token, sign_onlyoffice_payload, verify_onlyoffice_payload,
)
from ...db import get_db
from ...models import STATUS_PUBLISHED, STATUS_TRASHED, Document, DocumentVersion, User
from ...services.audit import record_audit
from ...storage.backend import storage

router = APIRouter(prefix="/onlyoffice", tags=["onlyoffice"])

_MAX_CALLBACK_DOWNLOAD = 100 * 1024 * 1024  # 100MB


def _is_editor(user: User) -> bool:
    return user.role in ("admin", "super_admin")


def _work_ext(doc: Document) -> str:
    return "pdf" if doc.ext == "pdf" else "docx"


def _doc_summary(doc: Document) -> dict:
    return {
        "id": doc.id,
        "name": doc.title,
        "version": doc.current_version,
        "ext": doc.ext,
        "work_ext": _work_ext(doc),
    }


def _build_config(user: User, doc: Document) -> dict:
    key = f"{doc.id}:v{doc.current_version}"
    access = "admin" if _is_editor(user) else "published"
    content_url = (
        f"{APP_BASE_URL}/api/v1/documents/{doc.id}/content"
        f"?token={sign_content_token(doc.id, doc.current_version, access)}"
        f"&version={doc.current_version}"
    )
    mode = "edit" if _is_editor(user) else "view"

    document = {
        "fileType": _work_ext(doc),
        "key": key,
        "title": f"{doc.title}.{_work_ext(doc)}",
        "url": content_url,
        "permissions": {
            "edit": mode == "edit",
            "download": True,
            "review": True,
        },
    }
    editor_config = {
        "callbackUrl": f"{APP_BASE_URL}/api/v1/onlyoffice/callback",
        "lang": "zh-CN",
        "mode": mode,
        "user": {"id": str(user.id), "name": user.display_name},
    }
    # 启用 JWT 时的标准结构：document / editorConfig 各自签名，config 顶层再签名。
    document["token"] = sign_onlyoffice_payload(document)
    editor_config["token"] = sign_onlyoffice_payload(editor_config)
    config = {
        "document": document,
        "documentType": "word",
        "editorConfig": editor_config,
        "token": sign_onlyoffice_payload({"document": document, "editorConfig": editor_config}),
    }
    return config


@router.get("/documents/{doc_id}/editor-config")
def editor_config(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None or doc.status == STATUS_TRASHED:
        raise HTTPException(404, "文档不存在")
    editor = _is_editor(user)
    if not editor and doc.status != STATUS_PUBLISHED:
        raise HTTPException(404, "文档不存在或未发布")
    if not ONLYOFFICE_URL:
        return {"available": False, "mode": "edit" if editor else "view",
                "doc": _doc_summary(doc)}
    return {"available": True, "onlyoffice_url": ONLYOFFICE_URL,
            "mode": "edit" if editor else "view", "config": _build_config(user, doc),
            "doc": _doc_summary(doc)}


def _callback_token(request: Request, body: dict) -> str:
    token = body.get("token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    return token


def _allowed_download_host(url: str) -> bool:
    """回调下载地址必须指向文档服务器或后端自身，防止 SSRF。"""
    try:
        host = urlsplit(url).netloc.lower()
    except Exception:
        return False
    allowed = set()
    for base in (ONLYOFFICE_URL, APP_BASE_URL):
        if base:
            try:
                allowed.add(urlsplit(base).netloc.lower())
            except Exception:
                pass
    return host in allowed and bool(allowed)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download(url: str) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request(url, headers={"User-Agent": "collab-docs"})
    with opener.open(req, timeout=30) as resp:
        data = resp.read(_MAX_CALLBACK_DOWNLOAD + 1)
    if len(data) > _MAX_CALLBACK_DOWNLOAD:
        raise ValueError("文件过大")
    return data


@router.post("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        return {"error": 1}

    # 回调必须携带有效 JWT，防止未认证写入与 SSRF。
    token = _callback_token(request, body)
    if not token:
        return {"error": 1}
    try:
        payload = verify_onlyoffice_payload(token)
    except Exception:
        return {"error": 1}

    status = body.get("status")
    key = body.get("key", "")
    url = body.get("url", "")
    if status not in (2, 6):
        return {"error": 0}

    # 校验 token 内容与请求体一致，防止重放 / 篡改。
    if payload.get("status") != status or payload.get("key") != key or payload.get("url") != url:
        return {"error": 1}

    if not url or ":" not in key:
        return {"error": 1}
    try:
        doc_id = int(key.split(":")[0])
    except ValueError:
        return {"error": 1}
    if not _allowed_download_host(url):
        return {"error": 1}

    doc = db.get(Document, doc_id)
    if doc is None or doc.status == STATUS_TRASHED:
        return {"error": 1}

    try:
        data = await asyncio.to_thread(_download, url)
    except Exception:
        return {"error": 1}

    # 仅接受“当前版本”的回调，忽略过期 / 重复保存。
    try:
        doc = db.get(Document, doc_id)
        db.refresh(doc, with_for_update=True)
    except Exception:
        return {"error": 1}
    if key != f"{doc_id}:v{doc.current_version}":
        return {"error": 1}

    new_no = doc.current_version + 1
    work_ext = _work_ext(doc)
    storage.save(f"documents/{doc_id}/versions/v{new_no}.{work_ext}", data)

    # 操作者按用户 ID 解析（回调 users 为 ID 数组或对象数组），失败不影响保存。
    operator = None
    users = payload.get("users") or body.get("users") or []
    for u in users[:1]:
        uid = u.get("id") if isinstance(u, dict) else u
        try:
            operator = db.get(User, int(uid))
        except (TypeError, ValueError):
            operator = None
    db.add(DocumentVersion(document_id=doc_id, version_no=new_no,
                          file_path=f"documents/{doc_id}/versions/v{new_no}.{work_ext}",
                          file_size=len(data), operator_id=operator.id if operator else None))
    doc.current_version = new_no
    doc.updated_at = datetime.now()
    record_audit(db, operator, "edit", "document", doc_id, f"{doc.title}.{doc.ext}",
                 detail={"version": new_no, "source": "onlyoffice"})
    db.commit()
    return {"error": 0}
