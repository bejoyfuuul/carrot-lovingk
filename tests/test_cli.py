"""명령줄 동작 — 특히 '에러가 친절한가'를 확인합니다."""

import pytest

from naver_blog_crawler import cli
from naver_blog_crawler.errors import PrivatePostError
from naver_blog_crawler.models import Post


def _post(title="테스트 글"):
    return Post(
        url="https://blog.naver.com/someone/223456789",
        blog_id="someone",
        log_no="223456789",
        title=title,
        author="글쓴이",
        published_at="2026. 1. 2.",
        markdown="본문입니다",
        text="본문입니다",
    )


def test_주소_하나면_화면에_출력한다(monkeypatch, capsys):
    monkeypatch.setattr(cli, "crawl", lambda url, session=None: _post())

    assert cli.main(["https://blog.naver.com/someone/223456789"]) == 0
    assert "본문입니다" in capsys.readouterr().out


def test_출력_파일을_주면_그_이름으로_저장한다(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "crawl", lambda url, session=None: _post())
    target = tmp_path / "내글.md"

    assert cli.main(["https://blog.naver.com/someone/1", "-o", str(target)]) == 0
    assert "본문입니다" in target.read_text(encoding="utf-8")


def test_폴더를_주면_글_제목으로_저장한다(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "crawl", lambda url, session=None: _post())

    assert cli.main(["https://blog.naver.com/someone/1", "-d", str(tmp_path)]) == 0
    assert (tmp_path / "테스트 글.md").exists()


def test_주소_목록_파일을_주면_전부_저장한다(tmp_path, monkeypatch):
    seen = []

    def fake(url, session=None):
        seen.append(url)
        return _post(title=f"글{len(seen)}")

    monkeypatch.setattr(cli, "crawl", fake)
    listing = tmp_path / "urls.txt"
    listing.write_text(
        "# 주석은 건너뜁니다\n"
        "https://blog.naver.com/a/1\n"
        "\n"
        "https://blog.naver.com/b/2\n",
        encoding="utf-8",
    )

    assert cli.main([str(listing), "-d", str(tmp_path)]) == 0
    assert seen == ["https://blog.naver.com/a/1", "https://blog.naver.com/b/2"]
    assert (tmp_path / "글1.md").exists()
    assert (tmp_path / "글2.md").exists()


def test_에러는_스택트레이스_대신_안내로_보여준다(monkeypatch, capsys):
    def boom(url, session=None):
        raise PrivatePostError("비공개 글입니다: https://blog.naver.com/a/1")

    monkeypatch.setattr(cli, "crawl", boom)

    assert cli.main(["https://blog.naver.com/a/1"]) == 1
    error_output = capsys.readouterr().err
    assert "비공개 글입니다" in error_output
    assert "로그인 없이 볼 수 있는 글만 지원합니다" in error_output
    assert "Traceback" not in error_output


def test_한_글이_실패해도_나머지는_계속_받는다(tmp_path, monkeypatch):
    def flaky(url, session=None):
        if url.endswith("/1"):
            raise PrivatePostError("비공개 글입니다")
        return _post(title="살아남은 글")

    monkeypatch.setattr(cli, "crawl", flaky)
    listing = tmp_path / "urls.txt"
    listing.write_text(
        "https://blog.naver.com/a/1\nhttps://blog.naver.com/b/2\n", encoding="utf-8"
    )

    assert cli.main([str(listing), "-d", str(tmp_path)]) == 1
    assert (tmp_path / "살아남은 글.md").exists()


def test_인자가_없으면_주소를_물어본다(monkeypatch, capsys):
    answers = iter(["https://blog.naver.com/a/1", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    monkeypatch.setattr(cli, "crawl", lambda url, session=None: _post())

    assert cli.main([]) == 0
    assert "본문입니다" in capsys.readouterr().out


@pytest.mark.parametrize("fmt,marker", [("json", '"title"'), ("text", "본문입니다")])
def test_형식을_고를_수_있다(monkeypatch, capsys, fmt, marker):
    monkeypatch.setattr(cli, "crawl", lambda url, session=None: _post())

    assert cli.main(["https://blog.naver.com/a/1", "-f", fmt]) == 0
    assert marker in capsys.readouterr().out
