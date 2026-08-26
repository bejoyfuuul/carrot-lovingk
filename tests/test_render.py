"""출력 형식 검증."""

import json

import pytest

from naver_blog_crawler.models import Image, Post
from naver_blog_crawler.render import (
    folder_name,
    render,
    suggest_filename,
    to_html,
    to_json,
    to_markdown,
)


@pytest.fixture
def post():
    return Post(
        url="https://blog.naver.com/someone/223456789",
        blog_id="someone",
        log_no="223456789",
        title='따옴표 "있는" 제목',
        author="글쓴이",
        published_at="2026. 1. 2. 10:00",
        category="일상",
        tags=["여행", "사진"],
        markdown="첫 문단\n\n![](https://img.example/1.jpg)",
        text="첫 문단",
        html='<p>첫 문단</p><figure><img src="https://img.example/1.jpg" alt=""></figure>',
        images=[Image(url="https://img.example/1.jpg")],
    )


def test_마크다운에_출처가_앞머리로_붙는다(post):
    body = to_markdown(post)
    assert body.startswith("---\n")
    assert "source: https://blog.naver.com/someone/223456789" in body
    assert "tags: [" in body
    assert "# 따옴표" in body


def test_앞머리의_따옴표가_YAML을_깨지_않는다(post):
    body = to_markdown(post)
    front = body.split("---")[1]
    # 값 전체를 감싸는 따옴표는 정확히 두 개여야 합니다.
    title_line = [l for l in front.splitlines() if l.startswith("title:")][0]
    assert title_line.count('"') == 2


def test_JSON은_한글을_그대로_담는다(post):
    data = json.loads(to_json(post))
    assert data["author"] == "글쓴이"
    assert data["tags"] == ["여행", "사진"]
    assert data["images"][0]["url"] == "https://img.example/1.jpg"


def test_파일이름에_쓸_수_없는_문자를_지운다():
    post = Post(url="u", blog_id="b", log_no="1", title='a/b:c*d?e"f')
    assert suggest_filename(post) == "abcdef.md"


def test_제목이_없으면_글번호로_이름을_짓는다():
    post = Post(url="u", blog_id="someone", log_no="223456789", title="")
    assert suggest_filename(post, "json") == "someone_223456789.json"


def test_알_수_없는_형식은_거절한다(post):
    with pytest.raises(ValueError):
        render(post, "pdf")


# --- HTML -------------------------------------------------------------------


def test_HTML은_스스로_완결된_문서다(post):
    body = to_html(post)
    assert body.startswith("<!doctype html>")
    assert '<html lang="ko">' in body
    # 인터넷 없이도 보이도록 스타일이 문서 안에 들어 있어야 합니다.
    assert "<style>" in body
    assert "http-equiv" not in body or "src=\"http" not in body.split("<article>")[0]


def test_HTML에_제목과_본문과_출처가_들어간다(post):
    body = to_html(post)
    assert "<title>따옴표 &#x27;있는&#x27; 제목</title>" in body or "따옴표" in body
    assert "<p>첫 문단</p>" in body
    assert post.url in body


def test_HTML_제목의_특수문자가_태그로_새지_않는다():
    post = Post(url="u", blog_id="b", log_no="1", title="<script>나쁜거</script>", html="")
    body = to_html(post)
    assert "<script>나쁜거" not in body
    assert "&lt;script&gt;" in body


# --- 폴더 이름 ---------------------------------------------------------------


def test_폴더_이름은_발행일과_제목이다(post):
    post.published_at = "2013. 7. 24. 19:06"
    post.title = "캐논 렌즈"
    assert folder_name(post) == "2013-07-24_캐논 렌즈"


def test_한자리_월일도_두자리로_맞춘다(post):
    post.published_at = "2013. 7. 4. 9:06"
    post.title = "글"
    assert folder_name(post) == "2013-07-04_글"


def test_발행일을_모르면_제목만_쓴다(post):
    post.published_at = ""
    post.title = "제목만"
    assert folder_name(post) == "제목만"


def test_제목도_발행일도_없으면_글번호를_쓴다():
    post = Post(url="u", blog_id="someone", log_no="223456789")
    assert folder_name(post) == "someone_223456789"


def test_폴더_이름에_경로_구분자가_남지_않는다(post):
    # 콜론은 윈도우 금지 문자이고, 슬래시는 폴더가 쪼개집니다.
    post.title = "a/b:c*d?e"
    post.published_at = "2013. 7. 24."
    name = folder_name(post)
    assert "/" not in name and ":" not in name
    assert name == "2013-07-24_abcde"
