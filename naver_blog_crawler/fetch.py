"""HTTP 담당. 네트워크 예외를 전부 한국어 에러로 바꿔서 올려보냅니다."""

from __future__ import annotations

import time

import requests

from .errors import NetworkError, PostNotFoundError
from .urls import PostRef, is_short_link, parse_post_url

#: 네이버는 브라우저가 아닌 요청을 막는 경우가 있어 평범한 크롬처럼 보이게 합니다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://m.blog.naver.com/",
}

TIMEOUT = 20
RETRIES = 3
#: 재시도 간격(초). 실패할수록 조금씩 길게 기다립니다.
BACKOFF = 1.5


def resolve(url: str) -> PostRef:
    """사용자가 준 링크를 PostRef 로 만듭니다. 단축 링크는 펼칩니다."""
    if is_short_link(url):
        url = _expand_short_link(url)
    return parse_post_url(url)


def fetch_html(ref: PostRef, session: requests.Session | None = None) -> str:
    """PostView HTML 원문을 가져옵니다."""
    response = _get(ref.fetch_url, session=session)
    if response.status_code == 404:
        raise PostNotFoundError(f"글을 찾을 수 없습니다: {ref.canonical_url}")
    if response.status_code >= 400:
        raise NetworkError(
            f"네이버가 응답을 거부했습니다 (HTTP {response.status_code})."
        )
    # 대부분 UTF-8 이지만 아주 오래된 글은 EUC-KR 로 옵니다.
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def download(url: str, session: requests.Session | None = None) -> bytes:
    """이미지 등 바이너리 파일 하나를 받습니다."""
    return _get(url, session=session, stream=False).content


def _expand_short_link(url: str) -> str:
    if "://" not in url:
        url = "https://" + url.lstrip("/")
    final = _get(url).url
    if "blog.naver.com" not in final:
        raise PostNotFoundError(
            f"단축 링크가 블로그 글이 아닌 곳으로 연결됩니다: {final}"
        )
    return final


def _get(url: str, session: requests.Session | None = None, **kwargs):
    """재시도가 붙은 GET. 마지막 실패만 사용자에게 보고합니다."""
    http = session or requests
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return http.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        except requests.Timeout as exc:
            last = exc
        except requests.ConnectionError as exc:
            last = exc
        except requests.RequestException as exc:
            last = exc
            break
        time.sleep(BACKOFF * (attempt + 1))

    raise NetworkError(f"네이버에 연결하지 못했습니다: {url}") from last
