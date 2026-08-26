"""Post 를 사람이 쓸 형식으로 바꿉니다: 마크다운 / 순수 텍스트 / JSON."""

from __future__ import annotations

import json
import re

from .models import Post

FORMATS = ("markdown", "text", "json")

#: 파일 이름에 쓸 수 없는 문자들.
_UNSAFE = r'[\\/:*?"<>|\n\r\t]'


def render(post: Post, fmt: str = "markdown") -> str:
    if fmt == "markdown":
        return to_markdown(post)
    if fmt == "text":
        return to_text(post)
    if fmt == "json":
        return to_json(post)
    raise ValueError(f"알 수 없는 출력 형식입니다: {fmt}")


def to_markdown(post: Post) -> str:
    """제목·출처를 앞머리(front matter)로 붙인 마크다운.

    옵시디언·노션 등에 그대로 붙여넣을 수 있게 YAML 앞머리를 씁니다.
    """
    front = [
        "---",
        f"title: {_yaml(post.title)}",
        f"author: {_yaml(post.author)}",
        f"date: {_yaml(post.published_at)}",
        f"source: {post.url}",
    ]
    if post.category:
        front.append(f"category: {_yaml(post.category)}")
    if post.tags:
        front.append("tags: [" + ", ".join(_yaml(t) for t in post.tags) + "]")
    front.append("---")

    body = [f"# {post.title}"] if post.title else []
    body.append(post.markdown)
    return "\n".join(front) + "\n\n" + "\n\n".join(body).strip() + "\n"


def to_text(post: Post) -> str:
    header = [line for line in (post.title, post.author, post.published_at) if line]
    return "\n".join(header + ["", post.text]).strip() + "\n"


def to_json(post: Post) -> str:
    return json.dumps(post.to_dict(), ensure_ascii=False, indent=2) + "\n"


def suggest_filename(post: Post, fmt: str = "markdown") -> str:
    """제목을 바탕으로 안전한 파일 이름을 만듭니다."""
    extension = {"markdown": "md", "text": "txt", "json": "json"}[fmt]
    name = re.sub(_UNSAFE, "", post.title).strip().strip(".")
    name = re.sub(r"\s+", " ", name)[:80].strip()
    if not name:
        name = f"{post.blog_id}_{post.log_no}"
    return f"{name}.{extension}"


def _yaml(value: str) -> str:
    """YAML 앞머리에 안전하게 넣을 수 있도록 따옴표를 씌웁니다."""
    return '"' + (value or "").replace('"', "'").replace("\n", " ") + '"'
