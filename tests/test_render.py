"""출력 형식 검증."""

import json

import pytest

from naver_blog_crawler.models import Image, Post
from naver_blog_crawler.render import render, suggest_filename, to_json, to_markdown


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
