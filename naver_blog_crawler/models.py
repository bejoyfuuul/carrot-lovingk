"""크롤링 결과를 담는 데이터 구조."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Image:
    """본문에 들어 있던 이미지 한 장."""

    url: str
    caption: str = ""
    alt: str = ""
    #: --images 로 내려받았을 때 저장된 로컬 경로(문서 기준 상대경로).
    local_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "caption": self.caption,
            "alt": self.alt,
            "local_path": self.local_path,
        }


@dataclass
class Post:
    """네이버 블로그 글 하나."""

    url: str
    blog_id: str
    log_no: str
    title: str = ""
    author: str = ""
    published_at: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    #: 마크다운으로 변환된 본문.
    markdown: str = ""
    #: 서식을 모두 걷어낸 본문.
    text: str = ""
    images: list[Image] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "blog_id": self.blog_id,
            "log_no": self.log_no,
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
            "category": self.category,
            "tags": self.tags,
            "markdown": self.markdown,
            "text": self.text,
            "images": [i.to_dict() for i in self.images],
        }
