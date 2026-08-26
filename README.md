# 네이버 블로그 크롤러

네이버 블로그 글 주소를 주면 **본문을 통째로 가져와 파일로 저장**해 주는 도구입니다.
글자만 긁어오는 게 아니라 제목, 소제목, 굵은 글씨, 인용문, 표, 사진까지 그대로 옮깁니다.

주소 하나를 주면 이렇게 만들어집니다.

```
output/
└─ 2013-07-24_캐논 카메라 렌즈 시리얼 구분법/
   ├─ post.md      마크다운 - 노션·옵시디언에 바로 붙여넣기
   ├─ post.html    브라우저로 열면 광고 없이 깔끔하게 읽힘
   ├─ post.txt     글자만 - AI에게 통째로 넘길 때
   ├─ post.json    프로그램 연동용
   └─ images/      본문 사진 (문서 안 주소도 이 파일을 가리키게 자동 변경)
```

폴더 이름은 **글 발행일 + 제목**입니다. 시간 순으로 정렬되고, 열어보지 않아도
무슨 글인지 알 수 있습니다. 같은 글을 다시 받으면 같은 폴더에 갱신되어
똑같은 글이 여러 개 쌓이지 않습니다.

## 왜 필요한가요

네이버 블로그는 화면에 보이는 주소와 실제 글이 들어 있는 주소가 다릅니다.
그래서 브라우저에서 "다른 이름으로 저장"을 하거나 일반 크롤링 도구를 쓰면
**빈 껍데기만 저장되는 경우가 많습니다.**

이 도구는 그 속사정을 대신 처리해 줍니다. 2015년 이전에 쓰인 오래된 글의
사진처럼, 그냥 가져오면 통째로 빠지는 것들까지 챙깁니다.

---

# 처음 쓰시는 분을 위한 설치 안내

컴퓨터 프로그램을 설치해 본 적이 없어도 괜찮습니다. 순서대로 따라오세요.
**맥(Mac)** 기준이고, 윈도우는 아래 [윈도우에서 쓰기](#윈도우에서-쓰기)를 보세요.

## 1단계 — 터미널 열기

`Command(⌘)` + `스페이스바`를 누르고 **터미널**이라고 친 다음 엔터를 누르세요.
검은(또는 흰) 창이 하나 뜹니다. 앞으로 명령어는 전부 여기에 입력합니다.

> 겁먹지 마세요. 아래 회색 상자 안의 글자를 **복사해서 붙여넣고 엔터**만 누르면 됩니다.

## 2단계 — 파이썬이 있는지 확인

```bash
python3 --version
```

`Python 3.9.6` 처럼 숫자가 나오면 준비된 것입니다. 다음 단계로 가세요.

`command not found` 라고 나오면 파이썬이 없는 것입니다.
<https://www.python.org/downloads/> 에서 노란색 **Download Python** 버튼을 눌러
설치한 뒤, 터미널을 껐다가 다시 켜고 이 단계를 다시 해 보세요.

## 3단계 — 이 도구 설치

```bash
pip3 install git+https://github.com/bejoyfuuul/carrot-lovingk.git
```

`Successfully installed` 라는 글자가 보이면 끝났습니다.

<details>
<summary>설치 중 <code>externally-managed-environment</code> 오류가 난다면</summary>

최근 맥·리눅스는 시스템 파이썬을 보호합니다. 아래처럼 이 도구만의
독립된 공간을 만들어 설치하세요.

```bash
python3 -m venv ~/naver-blog
~/naver-blog/bin/pip install git+https://github.com/bejoyfuuul/carrot-lovingk.git
```

이렇게 설치했다면 앞으로 `naver-blog` 대신 `~/naver-blog/bin/naver-blog` 를
쓰시면 됩니다. 매번 치기 번거로우면 딱 한 번 아래를 실행해 두세요.

```bash
echo 'alias naver-blog="~/naver-blog/bin/naver-blog"' >> ~/.zshrc
source ~/.zshrc
```
</details>

## 4단계 — 첫 글 가져오기

터미널에 이렇게만 치세요.

```bash
naver-blog
```

그러면 주소를 물어봅니다. 네이버 블로그 글을 브라우저에서 열고
**주소창의 주소를 복사해서 붙여넣은 뒤 엔터**를 누르세요.

```
네이버 블로그 글 주소를 붙여넣고 엔터를 누르세요. (그냥 엔터 = 끝)
주소> https://blog.naver.com/infotravelog/10172972504
```

다 받으면 지금 위치에 `output` 폴더가 생깁니다. 열어서 `post.html` 을
더블클릭해 보세요. 브라우저에 글이 깔끔하게 뜨면 성공입니다. 축하합니다!

---

# 실제로 쓰는 방법

## 글 하나 받기

```bash
naver-blog https://blog.naver.com/아이디/223456789
```

이게 전부입니다. `output/발행일_글제목/` 폴더에 **네 가지 형식과 사진이 모두**
저장됩니다. 옵션을 하나도 몰라도 됩니다.

## 다른 폴더에 저장하기

```bash
naver-blog https://blog.naver.com/아이디/223456789 -d 내자료
```

`output` 대신 `내자료` 폴더 아래에 저장됩니다. `-d` 는 **d**irectory(폴더)의 약자입니다.

## 여러 글을 한꺼번에 받기

메모장(맥은 텍스트편집기)에 주소를 **한 줄에 하나씩** 적고 `주소목록.txt` 로 저장하세요.

```
https://blog.naver.com/아이디/111111111
https://blog.naver.com/아이디/222222222
# 이렇게 #으로 시작하면 건너뜁니다
https://blog.naver.com/아이디/333333333
```

그리고 파일 이름을 그대로 넘기면 됩니다.

```bash
naver-blog 주소목록.txt
```

중간에 한 글이 실패해도 **나머지는 계속 받습니다.** 끝나고 몇 개가 실패했는지 알려줍니다.

## 저장하지 않고 화면으로만 보기

```bash
naver-blog https://blog.naver.com/아이디/223456789 --print
```

디스크에 아무것도 만들지 않습니다. 내용만 빠르게 확인할 때 쓰세요.

## 형식 하나만 받기

네 가지가 다 필요하지 않다면 하나만 고를 수 있습니다.

```bash
naver-blog https://blog.naver.com/아이디/223456789 -f markdown
```

| 형식 | 파일 | 이럴 때 쓰세요 |
|---|---|---|
| `markdown` | `post.md` | 노션·옵시디언에 붙여넣기, 나중에 다시 읽기 |
| `html` | `post.html` | 브라우저로 바로 읽기. 광고·메뉴 없음 |
| `text` | `post.txt` | 글자만 필요할 때, AI에게 통째로 넘길 때 |
| `json` | `post.json` | 다른 프로그램에서 자동으로 처리할 때 |

## 사진 없이 글만 받기

```bash
naver-blog https://blog.naver.com/아이디/223456789 --no-images
```

사진이 많은 글은 용량이 커질 수 있습니다. 글만 필요하면 이 옵션을 쓰세요.
문서 안의 사진 주소는 네이버 주소로 남습니다.

## 파일 하나로만 저장하기

폴더를 만들지 않고 딱 한 파일만 원한다면:

```bash
naver-blog https://blog.naver.com/아이디/223456789 -o 내글.md
```

**확장자가 형식을 정합니다.** `내글.json` 이라고 하면 JSON 으로 저장됩니다.

## 옵션 한눈에 보기

```bash
naver-blog --help
```

| 옵션 | 뜻 |
|---|---|
| (없음) | `output/` 에 네 형식 + 사진 모두 저장 |
| `-d`, `--out-dir` | 저장할 폴더 (기본값 `output`) |
| `-f`, `--format` | 이 형식 하나만 저장 (`markdown`·`html`·`text`·`json`) |
| `-p`, `--print` | 저장하지 않고 화면에 출력 |
| `--no-images` | 사진을 받지 않음 |
| `-o`, `--output` | 폴더 대신 이 파일 하나로 저장 |
| `-v`, `--version` | 버전 확인 |

---

# 받아지는 주소 / 안 받아지는 글

## 이런 주소는 모두 됩니다

```
https://blog.naver.com/아이디/223456789
https://m.blog.naver.com/아이디/223456789
https://blog.naver.com/PostView.naver?blogId=아이디&logNo=223456789
https://blog.naver.com/아이디?Redirect=Log&logNo=223456789
https://naver.me/xAbCdEfG                     ← 공유 버튼으로 만든 짧은 주소
blog.naver.com/아이디/223456789               ← https:// 를 빼먹어도 됨
```

## 이런 글은 안 됩니다

| 안 되는 것 | 이유 |
|---|---|
| 비공개 · 이웃공개 글 | 로그인이 필요합니다. 로그인 없이 볼 수 있는 글만 지원합니다. |
| 네이버 **카페** | 구조가 완전히 달라 별도 도구가 필요합니다. |
| 네이버 **뉴스 · 포스트 · 지식iN** | 위와 같습니다. |
| 블로그 **첫 화면** 주소 | 글 하나의 주소가 필요합니다. 글을 연 뒤 주소를 복사하세요. |
| 댓글 | 이 도구는 본문만 가져옵니다. |

---

# 뭔가 잘못됐을 때

이 도구는 오류가 나도 알 수 없는 영어 메시지를 쏟아내지 않습니다.
**무엇이 문제고 무엇을 하면 되는지** 한국어로 알려줍니다.

```
  ⚠  비공개 글입니다: https://blog.naver.com/아이디/223456789
     → 비공개 또는 이웃공개 글은 가져올 수 없습니다. 로그인 없이 볼 수 있는 글만 지원합니다.
```

| 화면에 나온 말 | 하실 일 |
|---|---|
| `네이버 블로그 주소가 아닙니다` | 카페·뉴스 주소일 수 있습니다. `blog.naver.com` 주소인지 확인하세요. |
| `이 주소에서는 글 번호를 찾을 수 없습니다` | 블로그 첫 화면 주소입니다. 글을 클릭해서 연 뒤 주소를 다시 복사하세요. |
| `글을 찾을 수 없습니다` | 글이 지워졌거나 주소에 오타가 있습니다. 브라우저에서 열리는지 보세요. |
| `비공개 글입니다` | 로그인이 필요한 글이라 가져올 수 없습니다. |
| `네이버에 연결하지 못했습니다` | 인터넷 연결을 확인하고 잠시 뒤 다시 해 보세요. |
| `네이버 블로그의 화면 구조가 바뀌었을 수 있습니다` | 도구를 고쳐야 하는 상황입니다. 아래 이슈로 링크와 함께 알려주세요. |

문제가 계속되면 [이슈로 알려주세요](https://github.com/bejoyfuuul/carrot-lovingk/issues).
**어떤 주소에서 어떤 메시지가 나왔는지**만 적어 주시면 됩니다.

---

# 윈도우에서 쓰기

1. `윈도우키` + `R` → `cmd` 입력 → 엔터로 명령 프롬프트를 엽니다.
2. <https://www.python.org/downloads/> 에서 파이썬을 설치합니다.
   설치 첫 화면의 **Add Python to PATH** 체크박스를 **꼭 켜세요.**
3. 명령 프롬프트를 껐다 켠 뒤 아래를 실행합니다.

```
pip install git+https://github.com/bejoyfuuul/carrot-lovingk.git
```

사용법은 맥과 완전히 같습니다. `python3` 대신 `python` 을 쓰는 것만 다릅니다.

---

# 파이썬 코드에서 쓰기

```python
from naver_blog_crawler import crawl

post = crawl("https://blog.naver.com/아이디/223456789")

print(post.title)          # 글 제목
print(post.author)         # 글쓴이
print(post.published_at)   # 2013. 7. 24. 19:06
print(post.category)       # 분류
print(post.tags)           # ['여행', '사진']
print(post.markdown)       # 서식이 살아 있는 본문
print(post.text)           # 서식 없는 본문
print(post.html)           # 본문 HTML 조각
for image in post.images:
    print(image.url)
```

## 폴더로 저장하기

CLI 와 똑같은 구조로 저장합니다.

```python
from naver_blog_crawler import crawl_to_folder

folder = crawl_to_folder(
    "https://blog.naver.com/아이디/223456789",
    out_dir="output",       # 기본값
    with_images=True,       # 기본값
)
print(folder)   # output/2013-07-24_캐논 카메라 렌즈 시리얼 구분법
```

형식을 골라서 받을 수도 있습니다.

```python
crawl_to_folder(url, formats=["markdown", "json"])
```

## 파일 하나로 저장하기

```python
from naver_blog_crawler import crawl_to_file

path = crawl_to_file(url, "내글.md", fmt="markdown", with_images=True)
```

## 이미 가져온 글을 저장하기

한 번 가져온 글을 여러 번 저장하거나, 저장 전에 손보고 싶을 때 씁니다.

```python
from naver_blog_crawler import crawl, save_post

post = crawl(url)
post.title = post.title.replace("[공지] ", "")
save_post(post, out_dir="정리한자료")
```

## 여러 글 받기

연결을 재사용하면 훨씬 빠릅니다.

```python
import requests
from naver_blog_crawler import crawl_to_folder

with requests.Session() as session:
    for url in urls:
        crawl_to_folder(url, session=session)
```

## 오류 다루기

모든 오류는 `NaverBlogError` 를 상속합니다. 한꺼번에 잡을 수 있습니다.

```python
from naver_blog_crawler import crawl, NaverBlogError, PrivatePostError

try:
    post = crawl(url)
except PrivatePostError:
    print("비공개 글은 건너뜁니다")
except NaverBlogError as error:
    print(error.message)   # 사용자에게 그대로 보여줄 수 있는 한국어 설명
    print(error.hint)      # 무엇을 하면 되는지에 대한 안내
```

| 오류 | 언제 |
|---|---|
| `InvalidURLError` | 주소가 네이버 블로그 글이 아님 |
| `PostNotFoundError` | 글이 없거나 삭제됨 |
| `PrivatePostError` | 비공개·이웃공개 글 |
| `NetworkError` | 연결 실패 (3번 재시도 후) |
| `ParseError` | 네이버 화면 구조가 바뀜 |

---

# 개발자용

## 구조

| 파일 | 하는 일 |
|---|---|
| `urls.py` | 여러 형태의 링크를 하나의 표준 주소로 정리 |
| `fetch.py` | HTTP 요청, 재시도, 단축 링크 펼치기 |
| `parse.py` | HTML → `Post`. 에디터 두 세대를 모두 처리 |
| `render.py` | `Post` → 마크다운 / HTML / 텍스트 / JSON, 폴더 이름 규칙 |
| `images.py` | 사진 저장 및 마크다운·HTML 안의 주소 치환 |
| `cli.py` | 명령줄 진입점 |
| `errors.py` | 한국어 안내가 붙은 예외들 |

## 알아둘 만한 것

- **본문은 `m.blog.naver.com/PostView.naver` 에서 가져옵니다.** 겉으로 보이는
  `blog.naver.com` 페이지는 iframe 껍데기라 본문이 없습니다.
- **에디터가 두 세대입니다.** 2018년 이후 글은 `.se-main-container` 안에
  의미가 붙은 블록(`.se-component`)이 들어 있어 구조를 살릴 수 있고,
  그 이전 글은 `#viewTypeSelector` 안에 평범한 HTML 만 있습니다.
- **옛 글의 사진은 `<img>` 가 아닙니다.** `<span thumburl="...">` 형태의
  자리표시자로만 들어 있어, 그냥 파싱하면 사진이 전부 빠집니다.
- **네이버 이미지 서버는 크기 지정 없이 원본을 주지 않습니다.** HTML 에 적힌
  '원본' 주소도 그대로 요청하면 404 입니다. 허용되는 최대 크기인
  `?type=w966` 을 붙여야 하고, 그보다 큰 값은 다시 404 가 됩니다.
- **본문은 세 표현을 한자리에서 함께 만듭니다.** 마크다운만 만들어 두고
  나중에 HTML 로 변환하면, 본문에 원래 있던 `*` 나 `#` 같은 글자를 서식으로
  오해합니다. 원본 구조를 아는 `parse.py` 안에서 마크다운·텍스트·HTML 을
  동시에 만드는 이유입니다.
- **폴더 이름에 콜론을 쓰지 않습니다.** 윈도우에서 금지 문자이고,
  맥 Finder 는 콜론을 `/` 로 보여줍니다. 시각이 필요하면 `19-30-45` 형태로 씁니다.
- **브라우저를 쓰지 않습니다.** Selenium 이나 Playwright 없이 순수 HTTP 로
  동작합니다. 비개발자에게 브라우저 설치는 큰 장벽이기 때문입니다.

## 개발 환경

```bash
git clone https://github.com/bejoyfuuul/carrot-lovingk.git
cd carrot-lovingk
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

테스트는 **네트워크 없이** 돌아갑니다. `tests/fixtures/` 에 실제 블로그
HTML 을 저장해 두고 파서를 검증하기 때문에, 결과가 항상 같고 빠릅니다.
네이버가 화면 구조를 바꾸면 이 테스트가 먼저 깨지도록 하는 것이 목적입니다.

## 예의를 지켜 주세요

공개된 글만 가져오고, 여러 글을 받을 때는 과하게 몰아치지 마세요.
가져온 글의 저작권은 원저작자에게 있습니다. 개인적인 보관·정리 용도로 쓰시고,
다시 게시할 때는 반드시 출처를 밝히세요. 저장되는 마크다운 파일에는
`source:` 항목으로 원글 주소가 자동으로 남습니다.

## 라이선스

MIT
