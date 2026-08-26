"""Post 를 사람이 쓸 형식으로 바꿉니다: 마크다운 / HTML / 순수 텍스트 / JSON."""

from __future__ import annotations

import json
import re
from html import escape

from .models import Post

#: 실제로 파일로 떨어지는 형식들.
FORMATS = ("markdown", "html", "text", "json")

#: 형식별 파일 확장자.
EXTENSIONS = {"markdown": "md", "html": "html", "text": "txt", "json": "json"}

#: 파일·폴더 이름에 쓸 수 없거나 쓰면 곤란한 문자들.
#: 콜론은 윈도우에서 금지 문자이고, 맥 Finder 는 이를 ``/`` 로 보여줍니다.
_UNSAFE = r'[\\/:*?"<>|\n\r\t]'


def render(post: Post, fmt: str = "markdown") -> str:
    if fmt == "markdown":
        return to_markdown(post)
    if fmt == "html":
        return to_html(post)
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


def to_html(post: Post) -> str:
    """브라우저로 열면 바로 읽히는 한 장짜리 문서.

    네이버 원본 HTML 과 달리 광고·메뉴·스크립트가 없고, 스타일은 전부
    문서 안에 들어 있어 인터넷 없이도 그대로 보입니다.
    """
    meta = " · ".join(
        escape(part) for part in (post.author, post.published_at, post.category) if part
    )
    tags = ""
    if post.tags:
        tags = (
            '<p class="tags">'
            + " ".join(f"<span>#{escape(tag)}</span>" for tag in post.tags)
            + "</p>"
        )

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(post.title)}</title>
<style>{_CSS}</style>
</head>
<body>
<article>
<header>
<h1>{escape(post.title)}</h1>
<p class="meta">{meta}</p>
{tags}
<p class="source"><a href="{escape(post.url, quote=True)}" rel="noopener">네이버에서 원글 보기</a></p>
</header>
{post.html}
</article>
</body>
</html>
"""


#: 읽기에만 집중한 최소한의 스타일. 밝은/어두운 화면 모두를 따릅니다.
_CSS = """
:root { color-scheme: light dark; --fg:#1a1a1a; --muted:#6b6b6b; --bg:#fff;
        --line:#e2e2e2; --accent:#03c75a; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8e8e8; --muted:#9a9a9a; --bg:#16181a; --line:#2f3336; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",
                   "Malgun Gothic","Noto Sans KR",sans-serif;
       line-height:1.75; font-size:17px; }
article { max-width:44rem; margin:0 auto; padding:3rem 1.25rem 6rem; }
header { border-bottom:1px solid var(--line); padding-bottom:1.5rem;
         margin-bottom:2.5rem; }
h1 { font-size:1.9rem; line-height:1.35; margin:0 0 .75rem; }
h2 { font-size:1.3rem; margin:2.5rem 0 .75rem; }
.meta, .source, .tags { color:var(--muted); font-size:.9rem; margin:.35rem 0; }
.tags span { margin-right:.4rem; }
a { color:inherit; text-decoration:underline; text-underline-offset:2px; }
header a { color:var(--accent); }
p { margin:0 0 1.15rem; }
figure { margin:2rem 0; }
img { max-width:100%; height:auto; display:block; border-radius:6px; }
figcaption { color:var(--muted); font-size:.875rem; text-align:center;
             margin-top:.6rem; }
blockquote { margin:2rem 0; padding:.25rem 0 .25rem 1.25rem;
             border-left:3px solid var(--accent); }
blockquote p:last-child { margin-bottom:0; }
blockquote footer { color:var(--muted); font-size:.9rem; }
hr { border:0; border-top:1px solid var(--line); margin:2.5rem 0; }
pre { background:rgba(127,127,127,.12); padding:1rem; border-radius:6px;
      overflow-x:auto; font-size:.9rem; }
code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.92em; }
table { border-collapse:collapse; width:100%; margin:2rem 0;
        display:block; overflow-x:auto; font-size:.94rem; }
th, td { border:1px solid var(--line); padding:.6rem .8rem; text-align:left;
         vertical-align:top; }
th { background:rgba(127,127,127,.08); font-weight:600; }
.place { color:var(--muted); }
"""


def suggest_filename(post: Post, fmt: str = "markdown") -> str:
    """단일 파일로 저장할 때 쓸, 제목 기반 파일 이름."""
    return f"{_safe(post.title) or f'{post.blog_id}_{post.log_no}'}.{EXTENSIONS[fmt]}"


def folder_name(post: Post) -> str:
    """글 하나가 들어갈 폴더 이름: ``발행일_제목``.

    발행일을 앞에 두면 폴더가 시간 순으로 정렬되고, 제목이 붙어 있어
    열어보지 않아도 무슨 글인지 알 수 있습니다. 같은 글을 다시 받으면
    같은 폴더에 덮어쓰므로 중복이 쌓이지 않습니다.
    """
    title = _safe(post.title)
    date = _date_prefix(post.published_at)
    parts = [part for part in (date, title) if part]
    return "_".join(parts) if parts else f"{post.blog_id}_{post.log_no}"


def _date_prefix(published_at: str) -> str:
    """``2013. 7. 24. 19:06`` → ``2013-07-24``."""
    match = re.search(r"(\d{4})\D{1,3}(\d{1,2})\D{1,3}(\d{1,2})", published_at or "")
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _safe(name: str) -> str:
    """파일·폴더 이름으로 안전하게 다듬습니다."""
    name = re.sub(_UNSAFE, "", name or "")
    name = re.sub(r"\s+", " ", name).strip()
    # 맥·윈도우 모두 이름이 점으로 끝나면 곤란합니다.
    return name.strip(". ")[:80].strip(". ")


def _yaml(value: str) -> str:
    """YAML 앞머리에 안전하게 넣을 수 있도록 따옴표를 씌웁니다."""
    return '"' + (value or "").replace('"', "'").replace("\n", " ") + '"'
