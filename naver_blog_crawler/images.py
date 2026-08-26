"""본문 이미지를 내려받고, 문서 안의 주소를 로컬 경로로 바꿉니다."""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path

import requests

from .errors import NetworkError
from .fetch import download
from .models import Post

#: 확장자를 알 수 없을 때 쓸 기본값.
_DEFAULT_EXT = ".jpg"


def download_images(
    post: Post,
    out_dir: Path,
    folder_name: str = "images",
    session: requests.Session | None = None,
) -> list[str]:
    """이미지를 ``out_dir/folder_name`` 에 저장하고 본문 주소를 바꿔칩니다.

    실패한 이미지는 건너뛰고 원래 주소를 그대로 둡니다. 사진 한 장 때문에
    글 전체를 못 가져오는 게 더 나쁘기 때문입니다.
    돌려주는 값은 저장하지 못한 이미지 주소 목록입니다.
    """
    if not post.images:
        return []

    image_dir = Path(out_dir) / folder_name
    image_dir.mkdir(parents=True, exist_ok=True)

    failed: list[str] = []
    replacements: dict[str, str] = {}

    for index, image in enumerate(post.images, start=1):
        try:
            data = download(image.url, session=session)
        except NetworkError:
            failed.append(image.url)
            continue
        if not data:
            failed.append(image.url)
            continue

        filename = _filename(image.url, index, data)
        (image_dir / filename).write_bytes(data)
        relative = f"{folder_name}/{filename}"
        image.local_path = relative
        replacements[image.url] = relative

    if replacements:
        post.markdown = _rewrite(post.markdown, replacements)

    return failed


def _rewrite(markdown: str, replacements: dict[str, str]) -> str:
    for original, local in replacements.items():
        markdown = markdown.replace(f"({original})", f"({local})")
    return markdown


def _filename(url: str, index: int, data: bytes) -> str:
    """겹치지 않는 파일 이름을 만듭니다.

    같은 글 안에 이름이 같은 사진이 여러 장 올 수 있어서
    순번과 주소 해시를 함께 붙입니다.
    """
    stem = Path(url.split("?")[0]).stem or "image"
    stem = re.sub(r"[^\w.-]", "_", stem)[:40]
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:6]
    return f"{index:02d}_{stem}_{digest}{_extension(url, data)}"


def _extension(url: str, data: bytes) -> str:
    """확장자는 주소보다 실제 내용의 시그니처를 우선합니다.

    네이버 이미지 주소는 ``.png`` 로 끝나도 실제로는 JPEG 를 주는 경우가
    있어서, 파일 앞부분의 매직 넘버로 확인합니다.
    """
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    if data.startswith(b"GIF8"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"

    suffix = Path(url.split("?")[0]).suffix.lower()
    if suffix in mimetypes.types_map:
        return suffix
    return _DEFAULT_EXT
