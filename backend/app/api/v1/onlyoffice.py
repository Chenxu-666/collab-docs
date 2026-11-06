import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import APP_BASE_URL, ONLYOFFICE_SECRET, ONLYOFFICE_URL
from ...core.deps import get_current_user
from ...core.security import sign_content_token
from ...db import get_db
from ...models import Document, DocumentVersion, User
from ...services.audit import record_audit

router = APIRouter(prefix="/onlyoffice", tags=["onlyoffice"])


def _is_editor(user: User) -> bool:
    return user.role in ("admin", "super_admin")


def _build_config(user: User, doc: Document) -> dict:
    key = f"{doc.id}:v{doc.current_version}"
    content_url = (
        f"{APP_BASE_URL}/api/v1/documents/{doc.id}/content"
        f"?token={sign_content_token(doc.id, doc.current_version)}&version={doc.current_version}"
    )
    mode = "edit" if _is_editor(user) else "view"
    config = {
        "document": {
            "fileType": "docx",
            "key": key,
            "title": f"{doc.name}.docx",
            "url": content_url,
        },
        "documentType": "word",
        "editorConfig": {
            "callbackUrl": f"{APP_BASE_URL}/api/v1/onlyoffice/callback",
            "lang": "zh-CN",
            "mode": mode,
            "user": {"id": str(user.id), "name": user.display_name},
        },
        "permissions": {
            "edit": mode == "edit",
            "download": True,
            "review": True,
        },
    }
    return config


@router.get("/documents/{doc_id}/editor-config")
def editor_config(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None or doc.status == "trashed":
        raise HTTPException(404, "文档不存在")
    config = _build_config(user, doc)
    if not ONLYOFFICE_URL:
        return {"available": False, "mode": "edit" if _is_editor(user) else "view",
                "doc": {"id": doc.id, "name": doc.title, "version": doc.current_version}}
    return {"available": True, "onlyoffice_url": ONLYOFFICE_URL,
            "mode": "edit" if _is_editor(user) else "view", "config": config}


@router.post("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    status = body.get("status")
    # status 2 = 保存，6 = 强制保存；其余为关闭/无变化等
    if status not in (2, 6):
        return {"error": 0}

    key = body.get("key", "")
    url = body.get("url", "")
    if not url or ":" not in key:
        return {"error": 1}

    doc_id = int(key.split(":")[0])
    doc = db.get(Document, doc_id)
    if doc is None:
        return {"error": 1}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "collab-docs"})
        data = urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        return {"error": 1}

    new_no = doc.current_version + 1
    from ...storage.backend import storage
    storage.save(f"documents/{doc_id}/versions/v{new_no}.docx", data)
    operator_name = ""
    users = body.get("users") or []
    if users:
        operator_name = users[0].get("name", "")
    operator = None
    if operator_name:
        operator = db.execute(select(User).where(User.display_name == operator_name)).scalar_one_or_none()
    db.add(DocumentVersion(document_id=doc_id, version_no=new_no,
                          file_path=f"documents/{doc_id}/versions/v{new_no}.docx",
                          file_size=len(data), operator_id=operator.id if operator else None))
    doc.current_version = new_no
    from datetime import datetime
    doc.updated_at = datetime.now()
    record_audit(db, operator, "edit", "document", doc_id, f"{doc.title}.{doc.ext}",
                 detail={"version": new_no, "source": "onlyoffice"})
    db.commit()
    return {"error": 0}
