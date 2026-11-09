from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.deps import get_current_user_optional, require_admin, require_super_admin
from ...db import get_db
from ...models import (
    STATUS_ARCHIVED, STATUS_DRAFT, STATUS_PUBLISHED, STATUS_TRASHED,
    Album, Image, User,
)
from ...services.audit import record_audit
from ...storage.backend import storage

router = APIRouter(tags=["library"])

ALLOWED_IMG = {"jpg", "jpeg", "png", "webp", "gif"}


def _img_out(i: Image) -> dict:
    return {
        "id": i.id, "title": i.title, "album_id": i.album_id, "file_size": i.file_size,
        "description": i.description, "status": i.status,
        "created_at": i.created_at.isoformat(),
        "uploader_name": i.uploader.display_name if i.uploader else "",
    }


@router.get("/albums")
def list_albums(user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    admin = user is not None and user.role in ("admin", "super_admin")
    rows = db.execute(select(Album).order_by(Album.sort_order, Album.id)).scalars().all()
    out = []
    for a in rows:
        # 用户端仅显示含已发布图片的相册
        if not admin:
            has_pub = db.execute(
                select(Image.id).where(Image.album_id == a.id, Image.status == STATUS_PUBLISHED).limit(1)
            ).scalar_one_or_none()
            if has_pub is None:
                continue
        out.append({"id": a.id, "name": a.name, "sort_order": a.sort_order})
    return out


@router.post("/albums")
def create_album(body: dict, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db), request: Request = None):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "相册名称不能为空")
    a = Album(name=name, sort_order=0)
    db.add(a)
    db.flush()
    record_audit(db, admin, "create", "album", a.id, name, ip=request.client.host if request else "")
    db.commit()
    return {"id": a.id, "name": a.name, "sort_order": a.sort_order}


@router.patch("/albums/{album_id}")
def rename_album(album_id: int, body: dict, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db), request: Request = None):
    a = db.get(Album, album_id)
    if a is None:
        raise HTTPException(404, "相册不存在")
    if (body.get("name") or "").strip():
        a.name = body["name"].strip()
    record_audit(db, admin, "edit", "album", a.id, a.name, ip=request.client.host if request else "")
    db.commit()
    return {"id": a.id, "name": a.name, "sort_order": a.sort_order}


@router.get("/images")
def list_images(album_id: int | None = None, status: str = "",
                user: User | None = Depends(get_current_user_optional),
                db: Session = Depends(get_db)):
    admin = user is not None and user.role in ("admin", "super_admin")
    stmt = select(Image)
    if admin:
        stmt = stmt.where(Image.status != STATUS_TRASHED)
    else:
        stmt = stmt.where(Image.status == STATUS_PUBLISHED)
    if album_id:
        stmt = stmt.where(Image.album_id == album_id)
    if status and admin:
        stmt = stmt.where(Image.status == status)
    stmt = stmt.order_by(Image.sort_order, Image.created_at.desc())
    return [_img_out(i) for i in db.execute(stmt).scalars().all()]


@router.get("/images/trash")
def list_trash(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Image).where(Image.status == STATUS_TRASHED)
                      .order_by(Image.updated_at.desc())).scalars().all()
    return [_img_out(i) for i in rows]


@router.post("/images")
async def upload_images(
    files: list[UploadFile] = File(...),
    album_id: int | None = Form(default=None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    created = []
    failed = []
    if album_id is not None and db.get(Album, album_id) is None:
        failed.append({"name": "", "reason": "指定的相册不存在"})
        return {"created": created, "failed": failed}
    for f in files:
        fn = f.filename or "未命名"
        title = fn.rsplit(".", 1)[0] if "." in fn else fn
        ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else "png"
        if ext not in ALLOWED_IMG:
            failed.append({"name": fn, "reason": "不支持的格式"})
            continue
        raw = await f.read()
        if len(raw) > 20 * 1024 * 1024:
            failed.append({"name": fn, "reason": "超过 20MB"})
            continue
        img = Image(title=title, album_id=album_id, file_path="", thumb_path="",
                    file_size=len(raw), uploaded_by=admin.id, status=STATUS_DRAFT)
        db.add(img)
        db.flush()
        storage.save(f"images/{img.id}/original.{ext}", raw)
        thumb_rel = storage.make_thumb(f"images/{img.id}/original.{ext}", f"images/{img.id}/thumb.webp")
        img.file_path = f"images/{img.id}/original.{ext}"
        img.thumb_path = thumb_rel
        record_audit(db, admin, "upload", "image", img.id, title,
                     ip=request.client.host if request else "")
        created.append(_img_out(img))
    db.commit()
    return {"created": created, "failed": failed}


@router.get("/images/{img_id}/thumb")
def get_thumb(img_id: int, user: User | None = Depends(get_current_user_optional),
              db: Session = Depends(get_db)):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    admin = user is not None and user.role in ("admin", "super_admin")
    if not admin and img.status != STATUS_PUBLISHED:
        raise HTTPException(404, "图片不存在")
    rel = img.thumb_path or img.file_path
    data = storage.read(rel)
    ext = rel.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/webp")
    return Response(content=data, media_type=mime)


@router.get("/images/{img_id}/file")
def get_file(img_id: int, user: User | None = Depends(get_current_user_optional),
             db: Session = Depends(get_db)):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    admin = user is not None and user.role in ("admin", "super_admin")
    if not admin and img.status != STATUS_PUBLISHED:
        raise HTTPException(404, "图片不存在")
    data = storage.read(img.file_path)
    ext = img.file_path.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")
    return Response(content=data, media_type=mime)


@router.patch("/images/{img_id}")
def update_image(img_id: int, body: dict, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db), request: Request = None):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    if "title" in body and body["title"].strip():
        img.title = body["title"].strip()
    if "description" in body:
        img.description = (body["description"] or "")[:500]
    if "album_id" in body:
        if body["album_id"] is not None and db.get(Album, body["album_id"]) is None:
            raise HTTPException(400, "指定的相册不存在")
        img.album_id = body["album_id"]
    if "sort_order" in body:
        img.sort_order = int(body["sort_order"])
    img.updated_at = datetime.now()
    record_audit(db, admin, "edit", "image", img_id, img.title,
                 ip=request.client.host if request else "")
    db.commit()
    return _img_out(img)


def _transition(img: Image, action: str, admin: User, db: Session, request: Request) -> dict:
    if action == "publish":
        img.status = STATUS_PUBLISHED
    elif action == "withdraw":
        img.status = STATUS_DRAFT
    elif action == "trash":
        img.status = STATUS_TRASHED
    elif action == "restore":
        img.status = STATUS_DRAFT
    else:
        raise HTTPException(400, "未知操作")
    img.updated_at = datetime.now()
    record_audit(db, admin, action, "image", img.id, img.title,
                 ip=request.client.host if request else "")
    db.commit()
    return _img_out(img)


@router.post("/images/{img_id}/publish")
def publish_image(img_id: int, admin: User = Depends(require_admin),
                  db: Session = Depends(get_db), request: Request = None):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    return _transition(img, "publish", admin, db, request)


@router.post("/images/{img_id}/withdraw")
def withdraw_image(img_id: int, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db), request: Request = None):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    return _transition(img, "withdraw", admin, db, request)


@router.delete("/images/{img_id}")
def trash_image(img_id: int, admin: User = Depends(require_admin),
                db: Session = Depends(get_db), request: Request = None):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    return _transition(img, "trash", admin, db, request)


@router.post("/images/{img_id}/restore")
def restore_image(img_id: int, admin: User = Depends(require_admin),
                  db: Session = Depends(get_db), request: Request = None):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    return _transition(img, "restore", admin, db, request)


@router.delete("/images/{img_id}/permanent")
def permanent_delete(img_id: int, admin: User = Depends(require_super_admin),
                     db: Session = Depends(get_db), request: Request = None):
    img = db.get(Image, img_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    if img.status != STATUS_TRASHED:
        raise HTTPException(400, "仅回收站中的内容可彻底删除")
    name = img.title
    record_audit(db, admin, "permanent_delete", "image", img_id, name,
                 ip=request.client.host if request else "")
    rel_paths = {img.file_path, img.thumb_path}
    db.delete(img)
    db.commit()
    for rel in rel_paths:
        if rel:
            try:
                storage.delete(rel)
            except Exception:
                pass
    return {"message": "已彻底删除"}
