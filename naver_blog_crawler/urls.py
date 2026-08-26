"""여러 형태의 네이버 블로그 링크를 하나의 표준 주소로 정리합니다.

사용자가 붙여넣는 링크는 대략 이런 것들입니다.

    https://blog.naver.com/someone/223456789
    https://m.blog.naver.com/someone/223456789
    https://blog.naver.com/PostView.naver?blogId=someone&logNo=223456789
    https://blog.naver.com/someone?Redirect=Log&logNo=223456789
    https://naver.me/xAbCdEfG          (단축 링크 - 네트워크로 펼쳐야 함)

겉으로 보이는 blog.naver.com 페이지는 iframe 껍데기라서 본문이 없습니다.
실제 본문은 PostView.naver 안에 있고, 모바일 쪽 HTML이 더 단순해서
크롤링 대상은 항상 m.blog.naver.com/PostView.naver 로 맞춥니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from .errors import InvalidURLError

#: PostView HTML을 받아올 표준 주소 틀.
POST_VIEW = "https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

#: 사람이 보는 원본 글 주소.
CANONICAL = "https://blog.naver.com/{blog_id}/{log_no}"

_SHORT_HOSTS = {"naver.me"}
_BLOG_HOSTS = {"blog.naver.com", "m.blog.naver.com", "blog.me"}

#: 경로 첫 조각이 blogId 가 아니라 페이지 이름인 경우들.
_RESERVED_PATHS = {
    "postview.naver",
    "postview.nhn",
    "postlist.naver",
    "postlist.nhn",
    "prologue",
    "guestbook",
}

_LOG_NO_RE = re.compile(r"^\d{6,}$")


@dataclass(frozen=True)
class PostRef:
    """글 하나를 가리키는 최소 정보."""

    blog_id: str
    log_no: str

    @property
    def fetch_url(self) -> str:
        return POST_VIEW.format(blog_id=self.blog_id, log_no=self.log_no)

    @property
    def canonical_url(self) -> str:
        return CANONICAL.format(blog_id=self.blog_id, log_no=self.log_no)


def is_short_link(url: str) -> bool:
    """naver.me 단축 링크인지. 이건 네트워크로 펼쳐야 blogId 를 알 수 있습니다."""
    return _host_of(url) in _SHORT_HOSTS


def parse_post_url(url: str) -> PostRef:
    """블로그 링크에서 blogId 와 logNo 를 뽑아냅니다.

    단축 링크는 여기서 처리하지 않습니다(네트워크가 필요하므로 fetch 쪽 담당).
    """
    if not url or not url.strip():
        raise InvalidURLError("주소가 비어 있습니다.")

    raw = url.strip()
    parsed = urlparse(_with_scheme(raw))
    host = parsed.netloc.lower().split(":")[0]

    if host in _SHORT_HOSTS:
        raise InvalidURLError(
            f"단축 링크({raw})는 먼저 원래 주소로 펼쳐야 합니다.",
            hint="이 오류가 그대로 보인다면 도구의 버그입니다. 알려주세요.",
        )

    if host not in _BLOG_HOSTS:
        raise InvalidURLError(
            f"네이버 블로그 주소가 아닙니다: {raw}",
            hint=(
                "이 도구는 blog.naver.com 글만 지원합니다. "
                "카페(cafe.naver.com)·뉴스·포스트는 아직 지원하지 않습니다."
            ),
        )

    query = parse_qs(parsed.query)
    blog_id = _first(query, "blogId")
    log_no = _first(query, "logNo")

    segments = [s for s in parsed.path.split("/") if s]

    # /아이디/123456789 형태
    if not blog_id and segments and segments[0].lower() not in _RESERVED_PATHS:
        blog_id = segments[0]
    if not log_no:
        for segment in reversed(segments):
            if _LOG_NO_RE.match(segment):
                log_no = segment
                break

    if not blog_id or not log_no:
        raise InvalidURLError(
            f"이 주소에서는 글 번호를 찾을 수 없습니다: {raw}",
            hint=(
                "블로그 첫 화면이 아니라 '글 하나'의 주소가 필요합니다. "
                "글을 연 다음 주소창의 링크를 복사해 주세요."
            ),
        )

    return PostRef(blog_id=blog_id, log_no=log_no)


def _with_scheme(url: str) -> str:
    if "://" in url:
        return url
    return "https://" + url.lstrip("/")


def _host_of(url: str) -> str:
    return urlparse(_with_scheme(url.strip())).netloc.lower().split(":")[0]


def _first(query: dict[str, list[str]], key: str) -> str:
    """쿼리 파라미터를 대소문자 구분 없이 하나 꺼냅니다."""
    for name, values in query.items():
        if name.lower() == key.lower() and values:
            return values[0].strip()
    return ""
