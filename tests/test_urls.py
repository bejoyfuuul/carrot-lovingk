"""여러 형태의 링크가 같은 글을 가리키는지 확인합니다."""

import pytest

from naver_blog_crawler.errors import InvalidURLError
from naver_blog_crawler.urls import is_short_link, parse_post_url


@pytest.mark.parametrize(
    "url",
    [
        "https://blog.naver.com/someone/223456789",
        "https://m.blog.naver.com/someone/223456789",
        "http://blog.naver.com/someone/223456789",
        "blog.naver.com/someone/223456789",
        "https://blog.naver.com/someone/223456789?fromRss=true&trackingCode=rss",
        "https://blog.naver.com/PostView.naver?blogId=someone&logNo=223456789",
        "https://m.blog.naver.com/PostView.nhn?blogId=someone&logNo=223456789&proxyReferer=",
        "https://blog.naver.com/someone?Redirect=Log&logNo=223456789",
    ],
)
def test_모든_링크_형태가_같은_글을_가리킨다(url):
    ref = parse_post_url(url)
    assert ref.blog_id == "someone"
    assert ref.log_no == "223456789"


def test_크롤링_주소는_모바일_PostView_로_통일된다():
    ref = parse_post_url("https://blog.naver.com/someone/223456789")
    assert ref.fetch_url == (
        "https://m.blog.naver.com/PostView.naver?blogId=someone&logNo=223456789"
    )
    assert ref.canonical_url == "https://blog.naver.com/someone/223456789"


def test_단축링크는_따로_구분된다():
    assert is_short_link("https://naver.me/xAbCdEfG")
    assert not is_short_link("https://blog.naver.com/someone/223456789")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "https://cafe.naver.com/something/12345",
        "https://www.google.com",
        "https://blog.naver.com/someone",  # 글이 아니라 블로그 첫 화면
    ],
)
def test_지원하지_않는_주소는_안내와_함께_거절한다(url):
    with pytest.raises(InvalidURLError) as caught:
        parse_post_url(url)
    # 사용자에게 보여줄 안내가 반드시 붙어 있어야 합니다.
    assert caught.value.hint
