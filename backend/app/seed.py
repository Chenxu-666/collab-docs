import io
import json

from PIL import Image as PILImage, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.security import hash_password
from .models import (
    ROLE_ADMIN, ROLE_SUPER_ADMIN, STATUS_DRAFT, STATUS_PUBLISHED,
    Album, Document, DocumentVersion, Folder, Image, Pitfall, User,
)
from .services.docx import make_minimal_docx
from .storage.backend import storage


def _gradient_img(title: str, c1: tuple, c2: tuple) -> bytes:
    w, h = 480, 360
    img = PILImage.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / h
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 32)
    except Exception:
        font = ImageFont.load_default()
    d.text((28, 150), title, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def seed_if_empty(db: Session):
    if db.execute(select(User).limit(1)).scalar_one_or_none():
        return

    # 账号：超级管理员 001 / 内容管理员 002
    super_admin = User(username="001", display_name="陈总",
                       password_hash=hash_password("WENjing970217"),
                       role=ROLE_SUPER_ADMIN, status="active")
    admin = User(username="002", display_name="内容管理员",
                 password_hash=hash_password("WENjing521"),
                 role=ROLE_ADMIN, status="active")
    db.add_all([super_admin, admin])
    db.flush()

    # 分类与相册
    folders = [Folder(name=n, sort_order=i) for i, n in enumerate(
        ["预算清单", "施工验收", "设计软装", "材料选购"])]
    albums = [Album(name=n, sort_order=i) for i, n in enumerate(
        ["客厅参考", "厨卫参考", "水电现场"])]
    db.add_all(folders + albums)
    db.flush()

    # 示例文档（装修主题）
    doc_data = [
        ("全屋装修预算模板", "预算清单", 2, STATUS_PUBLISHED,
         "统一装修预算编制口径，覆盖基础工程、主材、家具软装与不可预见费四大类。\n\n一、预算编制原则\n以“量价分离”为原则：先核工程量，再按市场价估算单价，最后合计。\n\n二、预算明细示例\n水电改造 120㎡ ¥85/㎡ ¥10200\n墙面乳胶漆 320㎡ ¥22/㎡ ¥7040\n地砖铺贴 96㎡ ¥48/㎡ ¥4608"),
        ("水电改造验收标准", "施工验收", 3, STATUS_PUBLISHED,
         "水电改造验收标准\n\n一、强弱电分离\n强弱电间距不小于 500mm，交叉处包锡纸屏蔽。\n\n二、水路打压\n冷热水管打压 0.8MPa，30 分钟无渗漏。\n\n三、回路设计\n大功率电器单独回路，卫生间厨房分别设回路。"),
        ("客厅软装搭配指南", "设计软装", 1, STATUS_DRAFT,
         "客厅软装搭配指南（草稿）\n\n一、主色不超过三种，遵循 6:3:1 配比。\n二、灯光分区：主灯 + 落地灯 + 氛围灯。"),
        ("全屋定制板材选购说明", "材料选购", 2, STATUS_PUBLISHED,
         "全屋定制板材选购说明\n\n一、环保等级\n优先 E0 级或 ENF 级板材，索要检测报告。\n\n二、封边工艺\n激光封边优于热熔胶封边，注意防潮与甲醛释放。"),
    ]
    for title, folder_name, ver, status, text in doc_data:
        data = make_minimal_docx(text)
        folder = next(f for f in folders if f.name == folder_name)
        d = Document(title=title, ext="docx", folder_id=folder.id, current_version=ver,
                     published_version_no=ver if status == STATUS_PUBLISHED else None,
                     status=status, size=len(data), owner_id=admin.id,
                     summary=text.split("\n")[1][:80])
        db.add(d)
        db.flush()
        storage.save(f"documents/{d.id}/original.docx", data)
        for v in range(1, ver + 1):
            storage.save(f"documents/{d.id}/versions/v{v}.docx", data)
            db.add(DocumentVersion(document_id=d.id, version_no=v,
                                  file_path=f"documents/{d.id}/versions/v{v}.docx",
                                  file_size=len(data),
                                  operator_id=super_admin.id if v % 2 else admin.id))

    # 示例图片（装修主题）
    photo_data = [
        ("客厅现代简约风", "客厅参考", (127, 156, 245), (76, 110, 245), STATUS_PUBLISHED),
        ("暖色原木风客厅", "客厅参考", (246, 173, 85), (237, 137, 54), STATUS_PUBLISHED),
        ("奶油风餐厅一角", "客厅参考", (244, 190, 175), (233, 150, 122), STATUS_PUBLISHED),
        ("卫生间干湿分离", "厨卫参考", (104, 211, 145), (56, 161, 105), STATUS_PUBLISHED),
        ("厨房动线设计", "厨卫参考", (163, 217, 165), (95, 158, 110), STATUS_PUBLISHED),
        ("水电开槽走线", "水电现场", (183, 148, 244), (107, 70, 193), STATUS_PUBLISHED),
        ("强弱电分离布管", "水电现场", (160, 174, 192), (74, 85, 104), STATUS_DRAFT),
        ("防水闭水试验", "水电现场", (203, 213, 224), (113, 128, 150), STATUS_PUBLISHED),
    ]
    for title, alb_name, c1, c2, status in photo_data:
        alb = next(a for a in albums if a.name == alb_name)
        raw = _gradient_img(title, c1, c2)
        img = Image(title=title, album_id=alb.id, file_path="", thumb_path="",
                    description=f"{title}参考图", alt_text=title,
                    file_size=len(raw), uploaded_by=admin.id, status=status)
        db.add(img)
        db.flush()
        storage.save(f"images/{img.id}/original.png", raw)
        img.file_path = f"images/{img.id}/original.png"
        img.thumb_path = storage.make_thumb(f"images/{img.id}/original.png", f"images/{img.id}/thumb.webp")

    # 示例避坑项
    pit_data = [
        ("防水闭水试验别省这 48 小时", "验收", "防水", "high",
         "卫生间防水做完后必须做闭水试验，观察楼下无渗漏再贴砖，否则返工代价极高。",
         "闭水试验至少 48 小时，蓄水高度 2-3cm，提前通知楼下邻居配合观察。", STATUS_PUBLISHED, True),
        ("插座预留宁多勿少", "水电", "电路", "medium",
         "入住后才发现插座不够，只能拉插线板，既不安全又不美观。",
         "沙发旁、床头、餐边柜、厨房台面多留 1~2 个带 USB 的插座。", STATUS_PUBLISHED, True),
        ("瓷砖收货务必当场验收", "材料", "主材", "medium",
         "色号、批号不一致会导致同一空间出现色差，退换货麻烦。",
         "收货时核对色号、批号、数量与破损，同一空间尽量用同一批次。", STATUS_PUBLISHED, False),
        ("木地板与瓷砖交接处预留伸缩缝", "木工", "地面", "low",
         "木地板热胀冷缩会起拱，硬碰硬交接后期容易出问题。",
         "交接处用收口条而非硬碰硬，预留 8-10mm 伸缩缝。", STATUS_DRAFT, False),
    ]
    for i, (title, stage, category, risk, problem, advice, status, pinned) in enumerate(pit_data):
        db.add(Pitfall(
            title=title, stage=stage, category=category, risk_level=risk,
            problem=problem, advice=advice, source_text="团队经验总结",
            related_image_ids=json.dumps([]), related_document_ids=json.dumps([]),
            status=status, sort_order=i, is_pinned=pinned, created_by=admin.id))

    db.commit()
