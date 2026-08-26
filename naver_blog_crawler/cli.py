"""명령줄 도구.

인자 없이 실행하면 주소를 물어보는 대화형 모드로 들어갑니다.
컴퓨터에 익숙하지 않은 분이 옵션을 외우지 않고도 쓸 수 있게 하려는 것입니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from . import __version__, crawl
from .errors import NaverBlogError
from .images import download_images
from .render import FORMATS, render, suggest_filename

DESCRIPTION = "네이버 블로그 글을 마크다운·텍스트·JSON 으로 저장합니다."

EPILOG = """\
예시:
  naver-blog https://blog.naver.com/아이디/223456789
      글을 마크다운으로 화면에 보여줍니다.

  naver-blog https://blog.naver.com/아이디/223456789 -o 내글.md
      파일로 저장합니다.

  naver-blog https://blog.naver.com/아이디/223456789 --images
      사진까지 함께 내려받습니다.

  naver-blog 주소목록.txt --out-dir 결과
      파일에 한 줄에 하나씩 적어둔 여러 글을 한꺼번에 저장합니다.

  naver-blog
      주소를 직접 물어봅니다.
"""


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    targets = _targets(args.source)
    if not targets:
        print("가져올 주소가 없습니다.", file=sys.stderr)
        return 1

    # 여러 글을 받을 땐 연결을 재사용하는 편이 훨씬 빠릅니다.
    session = requests.Session()
    out_dir = Path(args.out_dir) if args.out_dir else None
    to_stdout = out_dir is None and args.output is None and len(targets) == 1

    failures = 0
    for index, url in enumerate(targets, start=1):
        if len(targets) > 1:
            print(f"[{index}/{len(targets)}] {url}", file=sys.stderr)
        try:
            _handle(url, args, out_dir, to_stdout, session)
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


def _handle(url, args, out_dir, to_stdout, session) -> None:
    post = crawl(url, session=session)

    directory = out_dir or (Path(args.output).parent if args.output else Path("."))
    if args.images:
        directory.mkdir(parents=True, exist_ok=True)
        failed = download_images(post, directory, session=session)
        if failed:
            print(
                f"  사진 {len(failed)}장은 받지 못해 원래 주소를 남겨두었습니다.",
                file=sys.stderr,
            )

    body = render(post, args.format)

    if to_stdout:
        print(body)
        return

    if args.output:
        target = Path(args.output)
    else:
        target = directory / suggest_filename(post, args.format)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    print(f"  저장했습니다: {target}", file=sys.stderr)


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
        return [line.strip() for line in lines if line.strip() and not line.startswith("#")]

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
        "-o",
        "--output",
        help="저장할 파일 이름 (생략하면 글 제목으로 저장하거나 화면에 출력)",
    )
    parser.add_argument(
        "-d",
        "--out-dir",
        help="저장할 폴더 (여러 글을 받을 때 씁니다)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        default="markdown",
        help="출력 형식 (기본값: markdown)",
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="본문 사진도 함께 내려받고 문서의 주소를 로컬 경로로 바꿉니다",
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
