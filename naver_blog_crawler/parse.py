"""PostView HTML → Post 데이터.

네이버 블로그 본문은 에디터 세대에 따라 두 가지 구조를 씁니다.

  * 스마트에디터 ONE (2018~, 현재 대부분): ``.se-main-container`` 안에
    ``.se-component`` 블록이 나열됩니다. 블록 종류마다 뜻이 달라서
    문단/제목/인용/이미지/표/코드를 구분해 옮길 수 있습니다.
  * 구버전 에디터: ``#postViewArea`` 안에 평범한 HTML 이 들어 있습니다.
    구조 정보가 거의 없어서 문단 단위 변환으로 처리합니다.

두 경우 모두 같은 Post 를 돌려줍니다.

본문은 마크다운·순수 텍스트·HTML 세 가지로 동시에 만들어 둡니다.
하나만 만들어 두고 나중에 서로 변환하면 표나 인용처럼 구조가 있는 것이
깨지기 때문에, 원본 구조를 아는 이 자리에서 셋을 함께 만듭니다.
"""

from __future__ import annotations

import re
from html import escape

from bs4 import BeautifulSoup, NavigableString, Tag

from .errors import ParseError, PostNotFoundError, PrivatePostError
from .models import Image, Post
from .urls import PostRef

#: 네이버 에디터가 빈 줄 용도로 잔뜩 심어두는 제로폭 공백.
_ZERO_WIDTH = "\u200b\ufeff\u200c\u200d"

#: 본문이 없을 때 페이지에 나타나는 문구들.
_MISSING_MARKERS = ("존재하지 않는 게시물", "삭제된 게시물", "존재하지 않는 글")
_PRIVATE_MARKERS = ("비공개 처리", "비공개 글", "서로이웃", "이웃공개", "권한이 없")


def parse(html: str, ref: PostRef) -> Post:
    """PostView HTML 을 Post 로 만듭니다."""
    soup = BeautifulSoup(html, "lxml")
    _raise_if_unavailable(soup, ref)

    container = soup.select_one(".se-main-container")
    if container is not None:
        blocks = _parse_se_one(container)
    else:
        legacy = soup.select_one("#postViewArea, .post-view, #viewTypeSelector")
        if legacy is None:
            raise ParseError(f"본문을 찾지 못했습니다: {ref.canonical_url}")
        blocks = _parse_legacy(legacy)

    images = [
        Image(url=url, caption=caption, alt=alt)
        for url, caption, alt in _collect_images(blocks)
    ]
    markdown = _join(block.markdown for block in blocks)
    text = _join(block.text for block in blocks)
    body_html = "\n".join(block.html for block in blocks if block.html)

    if not markdown.strip() and not images:
        raise ParseError(f"본문이 비어 있습니다: {ref.canonical_url}")

    return Post(
        url=ref.canonical_url,
        blog_id=ref.blog_id,
        log_no=ref.log_no,
        title=_title(soup),
        author=_author(soup, ref),
        published_at=_published_at(soup),
        category=_category(soup),
        tags=_tags(soup),
        markdown=markdown,
        text=text,
        html=body_html,
        images=images,
    )


# --------------------------------------------------------------------------
# 블록
# --------------------------------------------------------------------------


class _Block:
    """본문 조각 하나를 세 가지 표현으로 함께 들고 다닙니다."""

    def __init__(
        self,
        markdown: str,
        text: str = "",
        html: str = "",
        image: tuple | None = None,
    ):
        self.markdown = markdown
        self.text = text if text is not None else ""
        self.html = html
        self.image = image


def _parse_se_one(container: Tag) -> list[_Block]:
    blocks: list[_Block] = []
    for component in container.find_all(
        "div", class_="se-component", recursive=True
    ):
        # 표 안에 든 컴포넌트처럼 다른 컴포넌트에 중첩된 것은 부모가 처리합니다.
        if component.find_parent("div", class_="se-component") is not None:
            continue
        blocks.extend(_component_to_blocks(component))
    return blocks


def _component_to_blocks(component: Tag) -> list[_Block]:
    kinds = set(component.get("class") or [])

    if "se-sectionTitle" in kinds:
        title = _inline(component)
        if not title:
            return []
        return [_Block(f"## {title}", _plain(component), f"<h2>{_rich(component)}</h2>")]

    if "se-quotation" in kinds:
        return _quotation(component)

    if "se-horizontalLine" in kinds:
        return [_Block("---", "", "<hr>")]

    if "se-image" in kinds or "se-imageStrip" in kinds:
        return _images(component)

    if "se-table" in kinds:
        return _table(component)

    if "se-code" in kinds or "se-codeblock" in kinds:
        body = component.get_text("\n").strip("\n")
        if not body.strip():
            return []
        return [
            _Block(
                f"```\n{body}\n```",
                body,
                f"<pre><code>{escape(body)}</code></pre>",
            )
        ]

    if "se-oglink" in kinds:
        return _oglink(component)

    if "se-video" in kinds or "se-vod" in kinds or "se-oembed" in kinds:
        return _embed(component)

    if "se-placesMap" in kinds or "se-map" in kinds:
        label = _clean(component.get_text(" "))
        if not label:
            return []
        return [
            _Block(
                f"> 📍 {label}",
                label,
                f'<p class="place">📍 {escape(label)}</p>',
            )
        ]

    if "se-material" in kinds or "se-sticker" in kinds:
        return []

    return _text_component(component)


def _text_component(component: Tag) -> list[_Block]:
    blocks: list[_Block] = []
    for module in component.find_all("div", class_="se-module-text"):
        for paragraph in module.find_all("p", class_="se-text-paragraph"):
            line = _inline(paragraph)
            if line:
                blocks.append(
                    _Block(line, _plain(paragraph), f"<p>{_rich(paragraph)}</p>")
                )
    return blocks


def _quotation(component: Tag) -> list[_Block]:
    paragraphs = component.find_all("p", class_="se-text-paragraph")
    lines = [line for p in paragraphs if (line := _inline(p))]
    plain = [line for p in paragraphs if (line := _plain(p))]
    if not lines:
        return []
    quoted = "\n".join(f"> {line}" for line in lines)
    inner = "".join(f"<p>{_rich(p)}</p>" for p in paragraphs if _inline(p))
    cite = component.select_one(".se-cite")
    if cite is not None and (source := _clean(cite.get_text(" "))):
        quoted += f"\n> \n> — {source}"
        plain.append(f"— {source}")
        inner += f"<footer>— {escape(source)}</footer>"
    return [_Block(quoted, "\n".join(plain), f"<blockquote>{inner}</blockquote>")]


def _images(component: Tag) -> list[_Block]:
    blocks: list[_Block] = []
    for module in component.find_all("div", class_="se-module-image"):
        img = module.find("img")
        if img is None:
            continue
        url = _image_url(module, img)
        if not url:
            continue
        alt = _clean(img.get("alt") or "")
        caption = ""
        section = module.find_parent("div", class_="se-section")
        if section is not None:
            figcaption = section.select_one(".se-caption, .se-module-text")
            if figcaption is not None:
                caption = _clean(figcaption.get_text(" "))
        label = caption or alt
        markdown = f"![{label}]({url})"
        if caption:
            markdown += f"\n*{caption}*"
        blocks.append(
            _Block(markdown, caption, _figure(url, caption, alt), (url, caption, alt))
        )
    return blocks


def _image_url(module: Tag, img: Tag) -> str:
    """가장 큰 이미지 주소를 고릅니다.

    ``src`` 는 흐릿한 미리보기(``?type=w80_blur``)라 쓸 수 없습니다.
    링크 데이터에 원본 주소가 들어 있으면 그걸 우선 씁니다.
    """
    link = module.find("a", class_="se-module-image-link")
    if link is not None and (data := link.get("data-linkdata")):
        if match := re.search(r'"src"\s*:\s*"([^"]+)"', data):
            return normalize_image_url(match.group(1))

    for attribute in ("data-lazy-src", "data-src", "src"):
        if url := (img.get(attribute) or "").strip():
            if "type=w80_blur" in url:
                continue
            return normalize_image_url(url)
    return ""


#: 네이버 이미지 서버가 허용하는 가장 큰 크기 값.
#: 이보다 큰 값(w1600 등)을 요청하면 404 가 돌아옵니다.
MAX_IMAGE_TYPE = "w966"

_NAVER_IMAGE_HOSTS = ("pstatic.net", "naver.net", "naver.com")


def normalize_image_url(url: str) -> str:
    """네이버 이미지 주소를 실제로 받아지는 최대 크기로 맞춥니다.

    네이버 이미지 서버는 크기 지정 쿼리 없이 원본을 주지 않습니다.
    HTML 에 적힌 '원본' 주소도 그대로 요청하면 404 가 나므로,
    항상 허용된 최대 크기를 붙여 줍니다.
    """
    url = url.strip().replace("\\/", "/")
    if not url:
        return ""
    if not any(host in url for host in _NAVER_IMAGE_HOSTS):
        return url
    return f"{url.split('?')[0]}?type={MAX_IMAGE_TYPE}"


def _table(component: Tag) -> list[_Block]:
    table = component.find("table")
    if table is None:
        return []

    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [
            _clean(cell.get_text(" ")) for cell in tr.find_all(["td", "th"])
        ]
        if any(cells):
            rows.append(cells)
    if not rows:
        return []

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]

    # 칸이 하나뿐인 표는 자료가 아니라 글 상자 꾸밈입니다. 표로 옮기면
    # 머리글 없는 1열 표가 되어 오히려 읽기 나빠지므로 인용문으로 냅니다.
    if width == 1 and len(rows) == 1:
        body = rows[0][0]
        return [_Block("\n".join(f"> {line}" for line in body.split("\n")), body)]

    header, *body = rows
    lines = [_row(header), _row(["---"] * width)]
    lines += [_row(row) for row in body]
    plain = "\n".join(" | ".join(row) for row in rows)

    html = ["<table><thead>", _html_row(header, "th"), "</thead><tbody>"]
    html += [_html_row(row, "td") for row in body]
    html.append("</tbody></table>")

    return [_Block("\n".join(lines), plain, "".join(html))]


def _row(cells: list[str]) -> str:
    escaped = [cell.replace("|", "\\|").replace("\n", " ") for cell in cells]
    return "| " + " | ".join(escaped) + " |"


def _html_row(cells: list[str], tag: str) -> str:
    body = "".join(
        f"<{tag}>{escape(cell).replace(chr(10), '<br>')}</{tag}>" for cell in cells
    )
    return f"<tr>{body}</tr>"


def _figure(url: str, caption: str, alt: str) -> str:
    src = escape(url, quote=True)
    figure = f'<figure><img src="{src}" alt="{escape(alt, quote=True)}" loading="lazy">'
    if caption:
        figure += f"<figcaption>{escape(caption)}</figcaption>"
    return figure + "</figure>"


def _oglink(component: Tag) -> list[_Block]:
    anchor = component.find("a", href=True)
    if anchor is None:
        return []
    title_tag = component.select_one(".se-oglink-title")
    href = anchor["href"]
    label = _clean(title_tag.get_text(" ")) if title_tag else href
    return [
        _Block(
            f"[{label}]({href})",
            f"{label} ({href})",
            f'<p><a href="{escape(href, quote=True)}">{escape(label)}</a></p>',
        )
    ]


def _embed(component: Tag) -> list[_Block]:
    for attribute in ("data-linkdata", "data-module"):
        if data := component.get(attribute):
            if match := re.search(r'"(?:src|url|link)"\s*:\s*"([^"]+)"', data):
                return _video(match.group(1).replace("\\/", "/"))
    iframe = component.find("iframe")
    if iframe is not None and (src := iframe.get("src")):
        return _video(src)
    return [_Block("_(동영상)_", "(동영상)", "<p><em>(동영상)</em></p>")]


def _video(url: str) -> list[_Block]:
    return [
        _Block(
            f"[동영상]({url})",
            url,
            f'<p><a href="{escape(url, quote=True)}">동영상</a></p>',
        )
    ]


# --------------------------------------------------------------------------
# 구버전 에디터
# --------------------------------------------------------------------------


def _parse_legacy(container: Tag) -> list[_Block]:
    """구조 정보가 없는 옛 HTML 을 문단 단위로 옮깁니다."""
    for junk in container.find_all(["script", "style"]):
        junk.decompose()
    _normalize_legacy_images(container)

    blocks: list[_Block] = []
    seen_images: set[int] = set()

    for node in container.find_all(["p", "div", "li", "blockquote", "hr", "img"]):
        if node.name == "img":
            if id(node) not in seen_images:
                seen_images.add(id(node))
                blocks.extend(_legacy_image(node))
            continue
        if node.name == "hr":
            blocks.append(_Block("---", "", "<hr>"))
            continue
        # 안에 또 문단이 있으면 그 자식이 처리하도록 넘깁니다.
        if node.find(["p", "div", "li", "blockquote"]) is not None:
            continue

        line = _inline(node)
        if line:
            quote = node.name == "blockquote"
            markdown = f"> {line}" if quote else line
            tag = "blockquote" if quote else "p"
            blocks.append(
                _Block(markdown, _plain(node), f"<{tag}>{_rich(node)}</{tag}>")
            )
        for img in node.find_all("img"):
            if id(img) in seen_images:
                continue
            seen_images.add(id(img))
            blocks.extend(_legacy_image(img))

    return blocks


def _normalize_legacy_images(container: Tag) -> None:
    """옛 에디터의 지연 로딩 이미지를 평범한 <img> 로 바꿔 둡니다.

    2015년 이전 글의 사진은 ``<span class="_img" thumburl="...">`` 처럼
    자바스크립트가 나중에 채우는 자리표시자로만 들어 있습니다.
    브라우저 없이 크롤링하면 이 자리표시자가 그대로 남아 사진이 통째로
    빠지므로, 파싱 전에 진짜 <img> 태그로 바꿔 놓습니다.
    """
    soup = container if isinstance(container, BeautifulSoup) else None
    for attribute in ("thumburl", "data-lazy-src", "data-src"):
        for node in container.select(f"[{attribute}]"):
            if node.name == "img":
                continue
            url = (node.get(attribute) or "").strip()
            if not url:
                continue
            replacement = (soup or BeautifulSoup("", "lxml")).new_tag("img")
            replacement["src"] = url
            replacement["alt"] = node.get("alt", "") or ""
            node.replace_with(replacement)


def _legacy_image(img: Tag) -> list[_Block]:
    url = normalize_image_url(img.get("src") or img.get("thumburl") or "")
    if not url or _is_decoration(url):
        return []
    alt = _clean(img.get("alt") or "")
    return [_Block(f"![{alt}]({url})", alt, _figure(url, "", alt), (url, "", alt))]


#: 본문과 무관한 꾸밈 이미지(프로필 사진, 이모티콘, 스킨 등)의 주소 조각.
_DECORATION_HOSTS = ("blogpfthumb", "static.blog.naver", "ssl.pstatic.net/static")


def _is_decoration(url: str) -> bool:
    return any(marker in url for marker in _DECORATION_HOSTS)


# --------------------------------------------------------------------------
# 인라인 서식
# --------------------------------------------------------------------------


#: 서식을 어떤 표현으로 옮길지.
MARKDOWN, PLAIN, HTML = "markdown", "plain", "html"


def _inline(node: Tag) -> str:
    """굵게·기울임·링크 정도만 살려서 한 줄 마크다운으로 만듭니다."""
    return _clean(_walk(node, MARKDOWN))


def _plain(node: Tag) -> str:
    """같은 내용을 서식 기호 없이 냅니다.

    마크다운 결과에서 기호만 지우는 방식은 본문에 원래 있던 ``*`` 같은
    글자까지 건드리게 되므로, 변환 단계에서 아예 기호를 넣지 않습니다.
    """
    return _clean(_walk(node, PLAIN))


def _rich(node: Tag) -> str:
    """같은 내용을 HTML 조각으로 냅니다.

    마크다운을 HTML 로 되돌리는 대신 원본에서 바로 만듭니다.
    되돌리는 방식은 본문에 원래 있던 ``*`` 나 ``#`` 같은 글자를
    서식으로 오해하기 때문입니다.
    """
    body = _walk(node, HTML).strip()
    # 문단 안의 줄바꿈은 HTML 에서 <br> 이어야 보입니다.
    return re.sub(r"\n+", "<br>", body)


def _walk(node, mode: str) -> str:
    if isinstance(node, NavigableString):
        return escape(str(node)) if mode == HTML else str(node)
    if not isinstance(node, Tag):
        return ""

    if node.name in ("script", "style"):
        return ""
    if node.name == "br":
        return "\n"
    if node.name == "img":
        return ""

    inner = "".join(_walk(child, mode) for child in node.children)
    if mode == PLAIN:
        return inner
    if mode == HTML:
        return _html_tag(node, inner)

    if node.name in ("b", "strong"):
        return _wrap(inner, "**")
    if node.name in ("i", "em"):
        return _wrap(inner, "*")
    if node.name in ("s", "strike", "del"):
        return _wrap(inner, "~~")
    if node.name == "code":
        return _wrap(inner, "`")
    if node.name == "a":
        href = (node.get("href") or "").strip()
        label = inner.strip()
        if href and href not in ("#", "javascript:void(0)") and label:
            return f"[{label}]({href})"
        return inner
    return inner


#: 살려둘 서식 태그. 나머지(span, font 등)는 내용만 남깁니다.
_KEEP_TAGS = {
    "b": "strong",
    "strong": "strong",
    "i": "em",
    "em": "em",
    "s": "del",
    "strike": "del",
    "del": "del",
    "code": "code",
    "sup": "sup",
    "sub": "sub",
}


def _html_tag(node: Tag, inner: str) -> str:
    """네이버가 붙인 스타일·클래스는 버리고 뜻이 있는 태그만 남깁니다."""
    if node.name == "a":
        href = (node.get("href") or "").strip()
        if href and href not in ("#", "javascript:void(0)") and inner.strip():
            safe = escape(href, quote=True)
            return f'<a href="{safe}" rel="noopener">{inner}</a>'
        return inner

    tag = _KEEP_TAGS.get(node.name)
    if tag and inner.strip():
        return f"<{tag}>{inner}</{tag}>"
    return inner


def _wrap(inner: str, marker: str) -> str:
    """빈 내용에 서식 기호만 남는 걸 막습니다."""
    stripped = inner.strip()
    if not stripped or not stripped.strip(_ZERO_WIDTH):
        return inner
    leading = inner[: len(inner) - len(inner.lstrip())]
    trailing = inner[len(inner.rstrip()) :]
    return f"{leading}{marker}{stripped}{marker}{trailing}"


# --------------------------------------------------------------------------
# 메타데이터
# --------------------------------------------------------------------------


def _title(soup: BeautifulSoup) -> str:
    node = soup.select_one(".se-title-text, .se_title, .htitle, .pcol1")
    if node is not None and (title := _clean(node.get_text(" "))):
        return title
    return _meta(soup, "og:title")


def _author(soup: BeautifulSoup, ref: PostRef) -> str:
    node = soup.select_one(".blog_author strong, .blog_author a, .nick")
    if node is not None and (author := _clean(node.get_text(" "))):
        return author
    return _meta(soup, "naverblog:nickname") or ref.blog_id


def _published_at(soup: BeautifulSoup) -> str:
    node = soup.select_one(".blog_date .txt, .blog_date, .se_publishDate, .se_date, .date, .pub_date")
    return _clean(node.get_text(" ")) if node is not None else ""


def _category(soup: BeautifulSoup) -> str:
    node = soup.select_one(".blog_category a, .blog_category, .category")
    return _clean(node.get_text(" ")) if node is not None else ""


def _tags(soup: BeautifulSoup) -> list[str]:
    tags: list[str] = []
    for node in soup.select(
        ".post_tag a, #tagList a, .item_tag, .tag_area a, .wrap_tag a"
    ):
        tag = _clean(node.get_text(" ")).lstrip("#").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _meta(soup: BeautifulSoup, prop: str) -> str:
    node = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
    if node is None:
        return ""
    return _clean(node.get("content") or "")


# --------------------------------------------------------------------------
# 도우미
# --------------------------------------------------------------------------


def _raise_if_unavailable(soup: BeautifulSoup, ref: PostRef) -> None:
    """본문 대신 안내 화면이 온 경우를 구분합니다."""
    if soup.select_one(".se-main-container, #postViewArea") is not None:
        return

    body = soup.get_text(" ") if soup.body else ""
    snippet = re.sub(r"\s+", " ", body)[:2000]
    for marker in _MISSING_MARKERS:
        if marker in snippet:
            raise PostNotFoundError(f"글을 찾을 수 없습니다: {ref.canonical_url}")
    for marker in _PRIVATE_MARKERS:
        if marker in snippet:
            raise PrivatePostError(f"비공개 글입니다: {ref.canonical_url}")


def _clean(value: str) -> str:
    """제로폭 문자와 군더더기 공백을 정리합니다."""
    value = value.replace("\xa0", " ")
    for char in _ZERO_WIDTH:
        value = value.replace(char, "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.split("\n")]
    return "\n".join(line for line in lines).strip()


def _join(parts) -> str:
    return "\n\n".join(part for part in parts if part and part.strip())


def _collect_images(blocks: list[_Block]) -> list[tuple]:
    seen: set[str] = set()
    result = []
    for block in blocks:
        if block.image and block.image[0] not in seen:
            seen.add(block.image[0])
            result.append(block.image)
    return result
