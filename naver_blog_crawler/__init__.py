"""네이버 블로그 글을 마크다운·텍스트·JSON 으로 가져오는 도구.

가장 짧은 사용법::

    from naver_blog_crawler import crawl

    post = crawl("https://blog.naver.com/someone/223456789")
    print(post.title)
    print(post.markdown)
"""

from __future__ import annotations

from pathlib import Path

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

__all__ = [
    "crawl",
    "crawl_to_file",
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

__version__ = "0.1.0"


def crawl(url: str, session: requests.Session | None = None) -> Post:
    """블로그 글 주소 하나를 받아 Post 로 돌려줍니다."""
    from . import fetch as _fetch
    from . import parse as _parse

    ref = _fetch.resolve(url)
    html = _fetch.fetch_html(ref, session=session)
    return _parse.parse(html, ref)


def crawl_to_file(
    url: str,
    out_dir: str | Path = ".",
    fmt: str = "markdown",
    filename: str | None = None,
    with_images: bool = False,
    session: requests.Session | None = None,
) -> Path:
    """글을 가져와 파일로 저장하고 저장된 경로를 돌려줍니다."""
    from . import images as _images
    from . import render as _render

    post = crawl(url, session=session)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)

    # 이미지를 먼저 받아야 본문의 주소가 로컬 경로로 바뀐 채로 저장됩니다.
    if with_images:
        _images.download_images(post, directory, session=session)

    target = directory / (filename or _render.suggest_filename(post, fmt))
    target.write_text(_render.render(post, fmt), encoding="utf-8")
    return target
