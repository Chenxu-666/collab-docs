from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.deps import get_current_user_optional, require_admin, require_super_admin
from ...core.security import sign_content_token, verify_content_token
from ...db import get_db
from ...models import (
    STATUS_ARCHIVED, STATUS_DRAFT, STATUS_PUBLISHED, STATUS_TRASHED,
    Document, DocumentVersion, User,
)
from ...services.audit import record_audit
from ...services.docx import extract_pdf_text, extract_text, make_minimal_docx
from ...storage.backend import storage

router = APIRouter(prefix="/documents", tags=["documents"])

# doc/wps 需要真实转换服务（LibreOffice/OnlyOffice），当前未接入，暂不支持上传，
# 避免生成误导性的“转换说明”占位文档。
ALLOWED_EXT = {"docx", "pdf"}


def _doc_out(d: Document) -> dict:
    return {
        "id": d.id, "title": d.title, "ext": d.ext, "current_version": d.current_version,
        "published_version_no": d.published_version_no, "status": d.status, "size": d.size,
        "summary": d.summary, "folder_id": d.folder_id,
        "created_at": d.created_at.isoformat(), "updated_at": d.updated_at.isoformat(),
        "owner_name": d.owner.display_name if d.owner else "",
    }


def _ver_out(v: DocumentVersion) -> dict:
    return {
        "id": v.id, "version_no": v.version_no, "file_size": v.file_size,
        "created_at": v.created_at.isoformat(),
        "operator_name": v.operator.display_name if v.operator else "",
    }


def _allocate_version(db: Session, doc: Document) -> int:
    """原子分配下一个版本号，避免并发回滚/回调产生重复版本。"""
    db.refresh(doc, with_for_update=True)
    return doc.current_version + 1


@router.get("")
def list_documents(
    q: str = "", ext: str = "", folder_id: int | None = None, status: str = "",
    user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    admin = user is not None and user.role in ("admin", "super_admin")
    stmt = select(Document)
    if admin:
        stmt = stmt.where(Document.status != STATUS_TRASHED)
    else:
        stmt = stmt.where(Document.status == STATUS_PUBLISHED)
    if ext:
        stmt = stmt.where(Document.ext == ext)
    if folder_id:
        stmt = stmt.where(Document.folder_id == folder_id)
    if status and admin:
        stmt = stmt.where(Document.status == status)
    stmt = stmt.order_by(Document.updated_at.desc())
    rows = db.execute(stmt).scalars().all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.title.lower() or ql in (r.summary or "").lower()]
    return [_doc_out(r) for r in rows]


@router.get("/trash")
def list_trash(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Document).where(Document.status == STATUS_TRASHED)
                      .order_by(Document.updated_at.desc())).scalars().all()
    return [_doc_out(r) for r in rows]


@router.get("/folders")
def list_folders(user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    from ...models import Folder
    rows = db.execute(select(Folder).order_by(Folder.sort_order, Folder.id)).scalars().all()
    return [{"id": f.id, "name": f.name, "sort_order": f.sort_order} for f in rows]


@router.post("/folders")
def create_folder(body: dict, admin: User = Depends(require_admin),
                  db: Session = Depends(get_db), request: Request = None):
    from ...models import Folder
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "分类名称不能为空")
    f = Folder(name=name, sort_order=0)
    db.add(f)
    db.flush()
    record_audit(db, admin, "create", "folder", f.id, name, ip=request.client.host if request else "")
    db.commit()
    return {"id": f.id, "name": f.name, "sort_order": f.sort_order}


@router.post("")
def upload_document(
    file: UploadFile = File(...),
    folder_id: int | None = Form(default=None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    filename = file.filename or "未命名"
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
    else:
        name, ext = filename, "docx"
    ext = ext.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "仅支持 docx / pdf 格式（doc/wps 请先另存为 docx）")
    raw = file.file.read()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(400, "文件超过 100MB 上限")
    if ext == "docx":
        try:
            import zipfile
            from io import BytesIO
            with zipfile.ZipFile(BytesIO(raw)) as z:
                z.read("word/document.xml")
        except Exception:
            raise HTTPException(400, "不是有效的 docx 文件")
    else:  # pdf
        if not raw[:5].startswith(b"%PDF-"):
            raise HTTPException(400, "不是有效的 PDF 文件")

    if folder_id is not None:
        from ...models import Folder
        if db.get(Folder, folder_id) is None:
            raise HTTPException(400, "指定的分类不存在")

    doc = Document(
        title=name, ext=ext, folder_id=folder_id, current_version=1,
        status=STATUS_DRAFT, size=len(raw), owner_id=admin.id, summary="",
    )
    db.add(doc)
    db.flush()

    storage.save(f"documents/{doc.id}/original.{ext}", raw)

    # v1 工作副本：docx 与 pdf 均直接使用原内容，保证预览/下载一致。
    v1_bytes = raw
    work_ext = "pdf" if ext == "pdf" else "docx"
    storage.save(f"documents/{doc.id}/versions/v1.{work_ext}", v1_bytes)
    db.add(DocumentVersion(document_id=doc.id, version_no=1,
                          file_path=f"documents/{doc.id}/versions/v1.{work_ext}",
                          file_size=len(v1_bytes), operator_id=admin.id))

    if ext == "docx":
        doc.summary = extract_text(raw)[:200]
    else:
        doc.summary = extract_pdf_text(raw)[:200]

    record_audit(db, admin, "upload", "document", doc.id, f"{name}.{ext}",
                 detail={"size": len(raw)}, ip=request.client.host if request else "")
    db.commit()
    return _doc_out(doc)


@router.get("/{doc_id}/versions")
def list_versions(doc_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    rows = db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_no.desc())
    ).scalars().all()
    return [_ver_out(v) for v in rows]


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    version: int | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    doc = db.get(Document, doc_id)
    if doc is None or doc.status == STATUS_TRASHED:
        raise HTTPException(404, "文档不存在")
    if version is None:
        version = doc.current_version
    v = db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc_id, DocumentVersion.version_no == version
        )
    ).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "版本不存在")
    record_audit(db, admin, "download", "document", doc_id, f"{doc.title}.{doc.ext}",
                 detail={"version": version}, ip=request.client.host if request else "")
    data = storage.read(v.file_path)
    fext = v.file_path.rsplit(".", 1)[-1] if "." in v.file_path else "docx"
    fname = f"{doc.title}-v{version}.{fext}"
    mime = "application/pdf" if fext == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(content=data, media_type=mime,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"})


@router.get("/{doc_id}/preview")
def preview_document(doc_id: int, user: User | None = Depends(get_current_user_optional),
                     db: Session = Depends(get_db)):
    """公开只读预览：返回提取后的纯文本。管理员可预览任意非回收站版本。"""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    admin = user is not None and user.role in ("admin", "super_admin")
    if not admin and doc.status != STATUS_PUBLISHED:
        raise HTTPException(404, "文档不存在或未发布")
    # 普通用户只能看已发布版本；管理员默认预览当前工作版本。
    version = doc.current_version if admin else (doc.published_version_no or doc.current_version)
    v = db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc_id, DocumentVersion.version_no == version
        )
    ).scalar_one_or_none()
    text = ""
    if v is not None:
        data = storage.read(v.file_path)
        text = extract_pdf_text(data) if doc.ext == "pdf" else extract_text(data)
    return {"id": doc.id, "title": doc.title, "ext": doc.ext, "status": doc.status,
            "summary": doc.summary, "version": version, "text": text,
            "updated_at": doc.updated_at.isoformat()}


@router.get("/{doc_id}/content")
def get_content(doc_id: int, token: str = "", version: int | None = None,
                db: Session = Depends(get_db)):
    """OnlyOffice 服务器拉取文件（短期 token，无需登录）。"""
    try:
        payload = verify_content_token(token)
    except Exception:
        raise HTTPException(403, "无效的访问令牌")
    if payload.get("doc_id") != doc_id:
        raise HTTPException(403, "令牌与文档不匹配")
    token_version = int(payload.get("version", 1))
    if version is not None and version != token_version:
        raise HTTPException(403, "版本与令牌不匹配")
    v = token_version
    doc = db.get(Document, doc_id)
    if doc is None or doc.status == STATUS_TRASHED:
        raise HTTPException(404, "文档不存在")
    if payload.get("access") == "published" and doc.status != STATUS_PUBLISHED:
        raise HTTPException(404, "文档不存在或未发布")
    for ext in ("docx", "pdf"):
        path = f"documents/{doc_id}/versions/v{v}.{ext}"
        if storage.exists(path):
            mime = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return Response(content=storage.read(path), media_type=mime)
    raise HTTPException(404, "文件不存在")


@router.post("/{doc_id}/versions/{version_no}/rollback")
def rollback(doc_id: int, version_no: int, admin: User = Depends(require_admin),
             db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    src = db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc_id, DocumentVersion.version_no == version_no
        )
    ).scalar_one_or_none()
    if src is None:
        raise HTTPException(404, "版本不存在")
    data = storage.read(src.file_path)
    fext = src.file_path.rsplit(".", 1)[-1] if "." in src.file_path else "docx"

    new_no = _allocate_version(db, doc)
    storage.save(f"documents/{doc_id}/versions/v{new_no}.{fext}", data)
    db.add(DocumentVersion(document_id=doc_id, version_no=new_no,
                          file_path=f"documents/{doc_id}/versions/v{new_no}.{fext}",
                          file_size=len(data), operator_id=admin.id))
    doc.current_version = new_no
    doc.updated_at = datetime.now()
    record_audit(db, admin, "rollback", "document", doc_id, f"{doc.title}.{doc.ext}",
                 detail={"from_version": version_no, "to_version": new_no},
                 ip=request.client.host if request else "")
    db.commit()
    return {"message": "已回滚（生成新版本）", "current_version": new_no}


@router.patch("/{doc_id}")
def update_document(doc_id: int, body: dict, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    if "title" in body and body["title"].strip():
        doc.title = body["title"].strip()
    if "folder_id" in body:
        from ...models import Folder
        if body["folder_id"] is not None and db.get(Folder, body["folder_id"]) is None:
            raise HTTPException(400, "指定的分类不存在")
        doc.folder_id = body["folder_id"]
    if "summary" in body:
        doc.summary = (body["summary"] or "")[:500]
    doc.updated_at = datetime.now()
    record_audit(db, admin, "edit", "document", doc_id, f"{doc.title}.{doc.ext}",
                 detail={"type": "meta"}, ip=request.client.host if request else "")
    db.commit()
    return _doc_out(doc)


def _transition(doc: Document, action: str, admin: User, db: Session, request: Request) -> dict:
    if action == "publish":
        if doc.current_version < 1:
            raise HTTPException(400, "无可发布版本")
        doc.published_version_no = doc.current_version
        doc.status = STATUS_PUBLISHED
    elif action == "withdraw":
        doc.status = STATUS_DRAFT
    elif action == "archive":
        doc.status = STATUS_ARCHIVED
    elif action == "trash":
        doc.status = STATUS_TRASHED
    elif action == "restore":
        doc.status = STATUS_DRAFT
    else:
        raise HTTPException(400, "未知操作")
    doc.updated_at = datetime.now()
    record_audit(db, admin, action, "document", doc.id, f"{doc.title}.{doc.ext}",
                 ip=request.client.host if request else "")
    db.commit()
    return _doc_out(doc)


@router.post("/{doc_id}/publish")
def publish_document(doc_id: int, admin: User = Depends(require_admin),
                     db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    return _transition(doc, "publish", admin, db, request)


@router.post("/{doc_id}/withdraw")
def withdraw_document(doc_id: int, admin: User = Depends(require_admin),
                      db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    return _transition(doc, "withdraw", admin, db, request)


@router.post("/{doc_id}/archive")
def archive_document(doc_id: int, admin: User = Depends(require_admin),
                     db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    return _transition(doc, "archive", admin, db, request)


@router.delete("/{doc_id}")
def trash_document(doc_id: int, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    return _transition(doc, "trash", admin, db, request)


@router.post("/{doc_id}/restore")
def restore_document(doc_id: int, admin: User = Depends(require_admin),
                     db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    return _transition(doc, "restore", admin, db, request)


@router.delete("/{doc_id}/permanent")
def permanent_delete(doc_id: int, admin: User = Depends(require_super_admin),
                     db: Session = Depends(get_db), request: Request = None):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    if doc.status != STATUS_TRASHED:
        raise HTTPException(400, "仅回收站中的内容可彻底删除")
    name = f"{doc.title}.{doc.ext}"
    record_audit(db, admin, "permanent_delete", "document", doc_id, name,
                 ip=request.client.host if request else "")
    # 收集需要清理的物理文件路径，数据库提交后再删除，失败不阻塞删除结果。
    rel_paths = {f"documents/{doc.id}/original.{doc.ext}"}
    for v in doc.versions:
        rel_paths.add(v.file_path)
    db.delete(doc)
    db.commit()
    for rel in rel_paths:
        try:
            storage.delete(rel)
        except Exception:
            pass
    return {"message": "已彻底删除"}
