import re
import zlib
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape


def _unescape(s: str) -> str:
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&apos;", "'"))


def extract_text(data: bytes) -> str:
    """从 docx 字节流提取纯文本（用于公开只读预览，降级方案）。"""
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
    except Exception:
        return ""
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    lines = []
    for p in paras:
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, flags=re.S)
        line = "".join(_unescape(t) for t in texts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_pdf_text(data: bytes) -> str:
    """从 PDF 提取文本；优先 pypdf，缺失时退化为流式解压的尽力提取。扫描件无文本层返回空串。"""
    try:
        from pypdf import PdfReader  # 可选依赖
        return "\n".join((page.extract_text() or "") for page in PdfReader(BytesIO(data)).pages).strip()
    except Exception:
        return _extract_pdf_text_fallback(data)


def _extract_pdf_text_fallback(data: bytes) -> str:
    """无 pypdf 时的尽力提取：解压 FlateDecode 流并抽取文本括号内容。"""
    try:
        chunks = []
        for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, flags=re.S):
            raw = m.group(1)
            raw = raw.split(b"endstream")[0]
            try:
                raw = zlib.decompress(raw.strip(b"\r\n"))
            except Exception:
                continue
            # 抽取 (text) 形式的内容，简单去转义
            for t in re.findall(rb"\((.*?)\)", raw):
                s = t.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
                s = re.sub(rb"\\[0-7]{1,3}", b"", s)
                try:
                    chunks.append(s.decode("utf-8", "ignore"))
                except Exception:
                    pass
        text = "\n".join(chunks).strip()
        return text if len(text) > 1 else ""
    except Exception:
        return ""


def make_minimal_docx(text: str) -> bytes:
    """构造一个最小可被 Office 打开的 docx 文件（用于种子数据/演示）。"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    paras = "".join(
        f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(line)}</w:t></w:r></w:p>"
        for line in text.split("\n")
    )
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>{paras}<w:sectPr/></w:body></w:document>"""

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
    return buf.getvalue()
