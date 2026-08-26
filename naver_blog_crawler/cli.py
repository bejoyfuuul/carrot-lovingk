"""명령줄 도구.

기본 동작은 "주소만 주면 output 폴더에 통째로 보관"입니다.
옵션을 하나도 모르는 사람이 그냥 써도 원하는 결과가 나오게 하려는 것입니다.
인자 없이 실행하면 주소를 물어보는 대화형 모드로 들어갑니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from . import __version__, crawl, save_post
from .errors import NaverBlogError
from .render import EXTENSIONS, FORMATS, render, suggest_filename

#: -d 를 주지 않았을 때 저장할 곳.
DEFAULT_OUT_DIR = "output"

DESCRIPTION = "네이버 블로그 글을 마크다운·HTML·텍스트·JSON 으로 저장합니다."

EPILOG = """\
예시:
  naver-blog https://blog.naver.com/아이디/223456789
      output/발행일_글제목/ 폴더에 네 가지 형식과 사진을 모두 저장합니다.

  naver-blog https://blog.naver.com/아이디/223456789 -d 내자료
      output 대신 '내자료' 폴더에 저장합니다.

  naver-blog https://blog.naver.com/아이디/223456789 --print
      저장하지 않고 화면에 보여줍니다.

  naver-blog https://blog.naver.com/아이디/223456789 -f markdown
      네 가지를 다 만들지 않고 마크다운만 저장합니다.

  naver-blog 주소목록.txt
      파일에 한 줄에 하나씩 적어둔 여러 글을 한꺼번에 저장합니다.

  naver-blog
      주소를 직접 물어봅니다.

만들어지는 구조:
  output/
  └─ 2013-07-24_캐논 카메라 렌즈 시리얼 구분법/
     ├─ post.md      마크다운 (노션·옵시디언용)
     ├─ post.html    브라우저로 열어 읽는 용도
     ├─ post.txt     글자만
     ├─ post.json    프로그램 연동용
     └─ images/      본문 사진
"""


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    targets = _targets(args.source)
    if not targets:
        print("가져올 주소가 없습니다.", file=sys.stderr)
        return 1

    # 여러 글을 받을 땐 연결을 재사용하는 편이 훨씬 빠릅니다.
    session = requests.Session()
    formats = FORMATS if args.format is None else (args.format,)

    failures = 0
    for index, url in enumerate(targets, start=1):
        if len(targets) > 1:
            print(f"[{index}/{len(targets)}] {url}", file=sys.stderr)
        try:
            _handle(url, args, formats, session)
        except NaverBlogError as error:
            failures += 1
            _report(error)
        except KeyboardInterrupt:
            print("\n중단했습니다.", file=sys.stderr)
            return 130

    if failures:
        print(f"\n{failures}개 글을 가져오지 못했습니다.", file=sys.stderr)
        return 1
    return 0


def _handle(url, args, formats, session) -> None:
    post = crawl(url, session=session)

    if args.print_only:
        print(render(post, args.format or "markdown"))
        return

    if args.output:
        _save_single(post, Path(args.output), args, session)
        return

    folder = save_post(
        post,
        out_dir=args.out_dir or DEFAULT_OUT_DIR,
        formats=formats,
        with_images=not args.no_images,
        session=session,
    )
    print(f"  저장했습니다: {folder}{_sep()}", file=sys.stderr)


def _save_single(post, target: Path, args, session) -> None:
    """``-o`` 로 파일 이름을 직접 준 경우. 형식은 확장자를 따릅니다."""
    from .images import download_images

    fmt = args.format or _format_from_suffix(target.suffix) or "markdown"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not args.no_images and args.images_requested:
        download_images(post, target.parent, session=session)
    target.write_text(render(post, fmt), encoding="utf-8")
    print(f"  저장했습니다: {target}", file=sys.stderr)


def _format_from_suffix(suffix: str) -> str | None:
    wanted = suffix.lower().lstrip(".")
    for fmt, extension in EXTENSIONS.items():
        if extension == wanted:
            return fmt
    return None


def _targets(source: str | None) -> list[str]:
    """인자를 주소 목록으로 바꿉니다.

    인자는 주소일 수도, 주소가 줄마다 적힌 텍스트 파일일 수도 있습니다.
    아무것도 없으면 직접 물어봅니다.
    """
    if source is None:
        return _ask()

    path = Path(source)
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
        return [
            line.strip()
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        ]

    return [source]


def _ask() -> list[str]:
    print("네이버 블로그 글 주소를 붙여넣고 엔터를 누르세요. (그냥 엔터 = 끝)")
    urls: list[str] = []
    while True:
        try:
            line = input("주소> ").strip()
        except EOFError:
            break
        if not line:
            break
        urls.append(line)
    return urls


def _report(error: NaverBlogError) -> None:
    """스택트레이스 대신 무엇을 하면 되는지 알려줍니다."""
    print(f"\n  ⚠  {error.message}", file=sys.stderr)
    if error.hint:
        print(f"     → {error.hint}", file=sys.stderr)


def _sep() -> str:
    return "\\" if sys.platform == "win32" else "/"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="naver-blog",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="블로그 글 주소, 또는 주소가 한 줄에 하나씩 적힌 텍스트 파일",
    )
    parser.add_argument(
        "-d",
        "--out-dir",
        help=f"저장할 폴더 (기본값: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        default=None,
        help="이 형식 하나만 저장합니다 (기본값: 네 가지 모두)",
    )
    parser.add_argument(
        "-p",
        "--print",
        dest="print_only",
        action="store_true",
        help="저장하지 않고 화면에 보여줍니다",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="본문 사진을 내려받지 않습니다",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="폴더를 만들지 않고 이 파일 하나로 저장합니다 (형식은 확장자를 따름)",
    )
    parser.add_argument(
        "--images",
        dest="images_requested",
        action="store_true",
        help="-o 와 함께 쓸 때 사진도 함께 내려받습니다",
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
