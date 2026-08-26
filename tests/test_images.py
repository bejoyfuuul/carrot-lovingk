"""이미지 저장과 본문 주소 치환."""

from naver_blog_crawler import images as images_module
from naver_blog_crawler.errors import NetworkError
from naver_blog_crawler.models import Image, Post

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPG = b"\xff\xd8\xff\xe0" + b"0" * 32


def _post():
    return Post(
        url="u",
        blog_id="b",
        log_no="1",
        markdown="![](https://img.example/a.png?type=w966)\n\n글\n\n![](https://img.example/b.png?type=w966)",
        images=[
            Image(url="https://img.example/a.png?type=w966"),
            Image(url="https://img.example/b.png?type=w966"),
        ],
    )


def test_사진을_저장하고_본문_주소를_로컬_경로로_바꾼다(tmp_path, monkeypatch):
    monkeypatch.setattr(images_module, "download", lambda url, session=None: PNG)
    post = _post()

    failed = images_module.download_images(post, tmp_path)

    assert failed == []
    saved = sorted(p.name for p in (tmp_path / "images").iterdir())
    assert len(saved) == 2
    assert "https://img.example" not in post.markdown
    for name in saved:
        assert f"(images/{name})" in post.markdown
    assert all(image.local_path for image in post.images)


def test_확장자는_주소가_아니라_실제_내용을_따른다(tmp_path, monkeypatch):
    # 네이버는 .png 로 끝나는 주소로 JPEG 를 주기도 합니다.
    monkeypatch.setattr(images_module, "download", lambda url, session=None: JPG)
    post = _post()

    images_module.download_images(post, tmp_path)

    assert all(p.suffix == ".jpg" for p in (tmp_path / "images").iterdir())


def test_사진_하나가_실패해도_나머지는_저장한다(tmp_path, monkeypatch):
    def flaky(url, session=None):
        if url.endswith("a.png?type=w966"):
            raise NetworkError("연결 실패")
        return PNG

    monkeypatch.setattr(images_module, "download", flaky)
    post = _post()

    failed = images_module.download_images(post, tmp_path)

    assert failed == ["https://img.example/a.png?type=w966"]
    # 실패한 사진은 원래 주소가 남아 있어야 글에서 사라지지 않습니다.
    assert "https://img.example/a.png?type=w966" in post.markdown
    assert len(list((tmp_path / "images").iterdir())) == 1


def test_사진이_없으면_폴더를_만들지_않는다(tmp_path):
    post = Post(url="u", blog_id="b", log_no="1", markdown="글만 있음")
    assert images_module.download_images(post, tmp_path) == []
    assert not (tmp_path / "images").exists()
