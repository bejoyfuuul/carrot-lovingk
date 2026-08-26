"""저장해 둔 실제 HTML 로 파서를 검증합니다.

네트워크 없이 돌기 때문에 언제 어디서든 같은 결과가 나옵니다.
네이버가 화면 구조를 바꾸면 이 테스트가 먼저 깨지는 게 목적입니다.
"""

import pytest

from naver_blog_crawler.errors import ParseError
from naver_blog_crawler.parse import normalize_image_url, parse
from naver_blog_crawler.urls import PostRef

SE_ONE = PostRef("naverofficial", "224388099234")
LEGACY = PostRef("infotravelog", "10172972504")


@pytest.fixture
def se_one(fixture_html):
    return parse(fixture_html("se_one_naverofficial.html"), SE_ONE)


@pytest.fixture
def legacy(fixture_html):
    return parse(fixture_html("legacy_infotravelog.html"), LEGACY)


# --- 스마트에디터 ONE (현재 글) ------------------------------------------


def test_새_에디터_메타데이터를_읽는다(se_one):
    assert se_one.title.startswith("[네이버 메이트 인터뷰]")
    assert se_one.author == "naverofficial"
    assert se_one.published_at == "2026. 8. 24. 10:00"
    assert se_one.category == "네이버가 만난 사람들"
    assert se_one.url == "https://blog.naver.com/naverofficial/224388099234"


def test_새_에디터_본문의_구조를_살린다(se_one):
    assert "**네이버 메이트**는" in se_one.markdown  # 굵게
    assert "\n> " in se_one.markdown or se_one.markdown.startswith("> ")  # 인용
    assert "---" in se_one.markdown  # 구분선
    assert "![" in se_one.markdown  # 이미지


def test_새_에디터_이미지를_모두_모은다(se_one):
    assert len(se_one.images) == 4
    assert all(image.url.startswith("https://") for image in se_one.images)
    # 흐릿한 미리보기(w80_blur)를 집으면 안 됩니다.
    assert not any("blur" in image.url for image in se_one.images)


def test_한칸짜리_표는_표가_아니라_인용문이_된다(se_one):
    # 네이버 글의 머리말 상자는 1x1 표로 만들어집니다.
    # 표로 옮기면 머리글 없는 1열 표가 되어 읽기 나빠집니다.
    assert "| --- |" not in se_one.markdown.split("\n\n")[0]
    assert se_one.markdown.startswith("> ")


def test_순수_텍스트에는_마크다운_기호가_없다(se_one):
    assert "**" not in se_one.text
    assert "![" not in se_one.text
    assert "네이버 메이트" in se_one.text


# --- 구버전 에디터 (2015년 이전 글) ---------------------------------------


def test_구버전_에디터_메타데이터를_읽는다(legacy):
    assert legacy.title == "캐논 카메라 렌즈 시리얼 구분법"
    assert legacy.author == "LovingK"
    assert legacy.published_at == "2013. 7. 24. 19:06"


def test_구버전_에디터의_지연로딩_사진을_찾아낸다(legacy):
    # 옛 글의 사진은 <img> 가 아니라 <span thumburl="..."> 로만 들어 있어서
    # 그대로 파싱하면 사진이 통째로 빠집니다.
    assert len(legacy.images) == 4
    assert all("pstatic.net" in image.url for image in legacy.images)


def test_구버전_에디터_본문과_사진의_순서가_유지된다(legacy):
    body = legacy.markdown
    assert body.index("캐논 16-35 렌즈입니다") < body.index("Utsononia공장에서 생산")
    assert "![" in body


def test_프로필_사진_같은_꾸밈_이미지는_제외한다(legacy):
    assert not any("blogpfthumb" in image.url for image in legacy.images)


# --- 이미지 주소 정규화 ----------------------------------------------------


def test_네이버_이미지는_받을_수_있는_최대_크기로_바뀐다():
    # 네이버 이미지 서버는 크기 지정 없이는 원본을 주지 않습니다(404).
    assert (
        normalize_image_url("https://mblogthumb-phinf.pstatic.net/x/1.jpg?type=w80_blur")
        == "https://mblogthumb-phinf.pstatic.net/x/1.jpg?type=w966"
    )
    assert (
        normalize_image_url("https://mblogthumb-phinf.pstatic.net/x/1.jpg")
        == "https://mblogthumb-phinf.pstatic.net/x/1.jpg?type=w966"
    )


def test_네이버가_아닌_이미지는_건드리지_않는다():
    external = "https://example.com/photo.png?size=1"
    assert normalize_image_url(external) == external


# --- 실패 처리 -------------------------------------------------------------


def test_본문이_없는_페이지는_안내와_함께_실패한다():
    with pytest.raises(ParseError) as caught:
        parse("<html><body><p>안녕하세요</p></body></html>", SE_ONE)
    assert caught.value.hint
