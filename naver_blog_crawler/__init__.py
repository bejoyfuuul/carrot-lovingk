"""네이버 블로그 글을 마크다운·텍스트·JSON 으로 가져오는 도구.

가장 짧은 사용법::

    from naver_blog_crawler import crawl

    post = crawl("https://blog.naver.com/someone/223456789")
    print(post.title)
    print(post.markdown)
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import requests

from .errors import (
    InvalidURLError,
    NaverBlogError,
    NetworkError,
    ParseError,
    PostNotFoundError,
    PrivatePostError,
)
from .models import Image, Post
from .render import FORMATS

__all__ = [
    "crawl",
    "crawl_to_folder",
    "crawl_to_file",
    "save_post",
    "FORMATS",
    "Post",
    "Image",
    "NaverBlogError",
    "InvalidURLError",
    "PostNotFoundError",
    "PrivatePostError",
    "NetworkError",
    "ParseError",
    "__version__",
]

__version__ = "0.2.0"


def crawl(url: str, session: requests.Session | None = None) -> Post:
    """블로그 글 주소 하나를 받아 Post 로 돌려줍니다."""
    from . import fetch as _fetch
    from . import parse as _parse

    ref = _fetch.resolve(url)
    html = _fetch.fetch_html(ref, session=session)
    return _parse.parse(html, ref)


def crawl_to_file(
    url: str,
    path: str | Path,
    fmt: str = "markdown",
    with_images: bool = False,
    session: requests.Session | None = None,
) -> Path:
    """글 하나를 지정한 경로에 한 가지 형식으로 저장합니다."""
    from . import images as _images
    from . import render as _render

    post = crawl(url, session=session)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # 이미지를 먼저 받아야 본문의 주소가 로컬 경로로 바뀐 채로 저장됩니다.
    if with_images:
        _images.download_images(post, target.parent, session=session)

    target.write_text(_render.render(post, fmt), encoding="utf-8")
    return target


def crawl_to_folder(
    url: str,
    out_dir: str | Path = "output",
    formats: Sequence[str] = FORMATS,
    with_images: bool = True,
    session: requests.Session | None = None,
) -> Path:
    """글 하나를 자기 폴더에 여러 형식으로 저장하고 그 폴더를 돌려줍니다.

    ``out_dir/발행일_제목/`` 아래에 ``post.md``, ``post.html``,
    ``post.json``, ``post.txt`` 와 ``images/`` 가 만들어집니다.
    """
    from . import render as _render

    post = crawl(url, session=session)
    return save_post(post, out_dir, formats, with_images, session=session)


def save_post(
    post: Post,
    out_dir: str | Path = "output",
    formats: Sequence[str] = FORMATS,
    with_images: bool = True,
    session: requests.Session | None = None,
) -> Path:
    """이미 가져온 Post 를 폴더 구조로 저장합니다."""
    from . import images as _images
    from . import render as _render

    folder = Path(out_dir) / _render.folder_name(post)
    folder.mkdir(parents=True, exist_ok=True)

    # 사진을 먼저 받아야 본문의 주소가 로컬 경로로 바뀐 채로 저장됩니다.
    if with_images:
        _images.download_images(post, folder, session=session)

    for fmt in formats:
        target = folder / f"post.{_render.EXTENSIONS[fmt]}"
        target.write_text(_render.render(post, fmt), encoding="utf-8")

    return folder
