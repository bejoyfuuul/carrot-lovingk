"""명령줄 동작.

특히 두 가지를 확인합니다.
  * 옵션을 하나도 모르는 사람이 주소만 줬을 때 원하는 결과가 나오는가
  * 에러가 스택트레이스가 아니라 안내로 보이는가
"""

import json

import pytest

from naver_blog_crawler import cli
from naver_blog_crawler.errors import PrivatePostError
from naver_blog_crawler.models import Post


def _post(title="테스트 글", published_at="2026. 1. 2. 10:00"):
    return Post(
        url="https://blog.naver.com/someone/223456789",
        blog_id="someone",
        log_no="223456789",
        title=title,
        author="글쓴이",
        published_at=published_at,
        markdown="본문입니다",
        text="본문입니다",
        html="<p>본문입니다</p>",
    )


@pytest.fixture
def fake_crawl(monkeypatch):
    """네트워크 없이 CLI 만 돌립니다."""

    def _install(post_factory=lambda url: _post()):
        monkeypatch.setattr(cli, "crawl", lambda url, session=None: post_factory(url))

    return _install


# --- 기본 동작 -------------------------------------------------------------


def test_주소만_주면_네_형식을_모두_폴더에_저장한다(tmp_path, fake_crawl):
    fake_crawl()

    assert cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path)]) == 0

    folder = tmp_path / "2026-01-02_테스트 글"
    assert folder.is_dir()
    assert sorted(f.name for f in folder.glob("post.*")) == [
        "post.html",
        "post.json",
        "post.md",
        "post.txt",
    ]


def test_폴더_이름은_발행일과_제목을_쓴다(tmp_path, fake_crawl):
    fake_crawl(lambda url: _post(title="캐논 렌즈", published_at="2013. 7. 24. 19:06"))

    cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path)])

    assert (tmp_path / "2013-07-24_캐논 렌즈").is_dir()


def test_같은_글을_다시_받으면_같은_폴더에_덮어쓴다(tmp_path, fake_crawl):
    fake_crawl()

    cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path)])
    cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path)])

    assert len(list(tmp_path.iterdir())) == 1


def test_저장_위치를_안_주면_output_에_저장한다(tmp_path, fake_crawl, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_crawl()

    assert cli.main(["https://blog.naver.com/a/1"]) == 0
    assert (tmp_path / "output" / "2026-01-02_테스트 글" / "post.md").exists()


def test_저장된_네_형식의_내용이_각각_맞다(tmp_path, fake_crawl):
    fake_crawl()
    cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path)])
    folder = tmp_path / "2026-01-02_테스트 글"

    assert "source: https://blog.naver.com/someone/223456789" in _read(folder, "post.md")
    assert _read(folder, "post.html").startswith("<!doctype html>")
    assert "<p>본문입니다</p>" in _read(folder, "post.html")
    assert _read(folder, "post.txt").strip().endswith("본문입니다")
    assert json.loads(_read(folder, "post.json"))["title"] == "테스트 글"


# --- 형식·출력 고르기 -------------------------------------------------------


def test_형식을_하나_고르면_그것만_저장한다(tmp_path, fake_crawl):
    fake_crawl()

    cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path), "-f", "markdown"])

    folder = tmp_path / "2026-01-02_테스트 글"
    assert [f.name for f in folder.glob("post.*")] == ["post.md"]


def test_print_는_저장하지_않고_화면에만_보여준다(tmp_path, fake_crawl, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_crawl()

    assert cli.main(["https://blog.naver.com/a/1", "--print"]) == 0
    assert "본문입니다" in capsys.readouterr().out
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "fmt,marker", [("json", '"title"'), ("text", "본문입니다"), ("html", "<!doctype html>")]
)
def test_print_형식을_고를_수_있다(fake_crawl, capsys, fmt, marker):
    fake_crawl()

    assert cli.main(["https://blog.naver.com/a/1", "--print", "-f", fmt]) == 0
    assert marker in capsys.readouterr().out


def test_출력_파일을_직접_주면_폴더를_만들지_않는다(tmp_path, fake_crawl):
    fake_crawl()
    target = tmp_path / "내글.md"

    assert cli.main(["https://blog.naver.com/a/1", "-o", str(target)]) == 0
    assert "본문입니다" in target.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [target]


def test_출력_파일의_확장자가_형식을_정한다(tmp_path, fake_crawl):
    fake_crawl()
    target = tmp_path / "내글.json"

    cli.main(["https://blog.naver.com/a/1", "-o", str(target)])

    assert json.loads(target.read_text(encoding="utf-8"))["title"] == "테스트 글"


# --- 사진 -------------------------------------------------------------------


def test_사진은_기본으로_함께_받는다(tmp_path, fake_crawl, monkeypatch):
    called = {}
    monkeypatch.setattr(
        "naver_blog_crawler.images.download_images",
        lambda post, folder, **kwargs: called.setdefault("folder", folder) and [],
    )
    fake_crawl()

    cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path)])

    assert called["folder"] == tmp_path / "2026-01-02_테스트 글"


def test_no_images_면_사진을_받지_않는다(tmp_path, fake_crawl, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("사진을 받으면 안 됩니다")

    monkeypatch.setattr("naver_blog_crawler.images.download_images", fail)
    fake_crawl()

    assert cli.main(["https://blog.naver.com/a/1", "-d", str(tmp_path), "--no-images"]) == 0


# --- 여러 글 ----------------------------------------------------------------


def test_주소_목록_파일을_주면_전부_저장한다(tmp_path, fake_crawl):
    seen = []

    def factory(url):
        seen.append(url)
        return _post(title=f"글{len(seen)}")

    fake_crawl(factory)
    listing = tmp_path / "urls.txt"
    listing.write_text(
        "# 주석은 건너뜁니다\n"
        "https://blog.naver.com/a/1\n"
        "\n"
        "https://blog.naver.com/b/2\n",
        encoding="utf-8",
    )
    out = tmp_path / "결과"

    assert cli.main([str(listing), "-d", str(out)]) == 0
    assert seen == ["https://blog.naver.com/a/1", "https://blog.naver.com/b/2"]
    assert (out / "2026-01-02_글1" / "post.md").exists()
    assert (out / "2026-01-02_글2" / "post.md").exists()


def test_한_글이_실패해도_나머지는_계속_받는다(tmp_path, fake_crawl):
    def factory(url):
        if url.endswith("/1"):
            raise PrivatePostError("비공개 글입니다")
        return _post(title="살아남은 글")

    fake_crawl(factory)
    listing = tmp_path / "urls.txt"
    listing.write_text(
        "https://blog.naver.com/a/1\nhttps://blog.naver.com/b/2\n", encoding="utf-8"
    )
    out = tmp_path / "결과"

    assert cli.main([str(listing), "-d", str(out)]) == 1
    assert (out / "2026-01-02_살아남은 글" / "post.md").exists()


# --- 사람을 대하는 방식 -----------------------------------------------------


def test_에러는_스택트레이스_대신_안내로_보여준다(fake_crawl, capsys, monkeypatch):
    def factory(url):
        raise PrivatePostError("비공개 글입니다: https://blog.naver.com/a/1")

    fake_crawl(factory)

    assert cli.main(["https://blog.naver.com/a/1"]) == 1
    errors = capsys.readouterr().err
    assert "비공개 글입니다" in errors
    assert "로그인 없이 볼 수 있는 글만 지원합니다" in errors
    assert "Traceback" not in errors


def test_인자가_없으면_주소를_물어본다(tmp_path, fake_crawl, monkeypatch):
    monkeypatch.chdir(tmp_path)
    answers = iter(["https://blog.naver.com/a/1", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    fake_crawl()

    assert cli.main([]) == 0
    assert (tmp_path / "output" / "2026-01-02_테스트 글" / "post.md").exists()


def _read(folder, name):
    return (folder / name).read_text(encoding="utf-8")
