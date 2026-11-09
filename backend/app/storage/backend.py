import shutil
from pathlib import Path

from PIL import Image as PILImage

from ..core.config import FILE_ROOT


class LocalStorage:
    def __init__(self, root: Path = FILE_ROOT):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root.resolve()):
            raise ValueError("非法路径")
        return p

    def save(self, rel: str, data: bytes) -> str:
        p = self._path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return rel

    def save_stream(self, rel: str, stream) -> str:
        p = self._path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            shutil.copyfileobj(stream, f)
        return rel

    def read(self, rel: str) -> bytes:
        return self._path(rel).read_bytes()

    def exists(self, rel: str) -> bool:
        return self._path(rel).exists()

    def delete(self, rel: str):
        p = self._path(rel)
        if p.exists():
            p.unlink()

    def make_thumb(self, src_rel: str, thumb_rel: str, size: int = 400) -> str:
        try:
            img = PILImage.open(self._path(src_rel)).convert("RGB")
            img.thumbnail((size, size))
            p = self._path(thumb_rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            img.save(p, "WEBP", quality=82)
            return thumb_rel
        except Exception:
            return src_rel


storage = LocalStorage()
