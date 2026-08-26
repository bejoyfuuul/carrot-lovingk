"""사용자에게 그대로 보여줄 수 있는 한국어 에러들.

비개발자가 쓰는 도구라서, 예외 메시지가 곧 안내문이 되도록 만들었습니다.
CLI는 스택트레이스 대신 이 메시지만 출력합니다.
"""


class NaverBlogError(Exception):
    """이 패키지가 내는 모든 에러의 부모."""

    hint: str = ""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        if hint:
            self.hint = hint


class InvalidURLError(NaverBlogError):
    hint = "주소창의 링크를 그대로 복사해서 붙여넣어 주세요. 예: https://blog.naver.com/아이디/223456789"


class PostNotFoundError(NaverBlogError):
    hint = "글이 삭제되었거나 주소가 잘못되었을 수 있습니다. 브라우저에서 링크가 열리는지 확인해 주세요."


class PrivatePostError(NaverBlogError):
    hint = "비공개 또는 이웃공개 글은 가져올 수 없습니다. 로그인 없이 볼 수 있는 글만 지원합니다."


class NetworkError(NaverBlogError):
    hint = "인터넷 연결을 확인한 뒤 잠시 후 다시 시도해 주세요."


class ParseError(NaverBlogError):
    hint = (
        "네이버 블로그의 화면 구조가 바뀌었을 수 있습니다. "
        "이 메시지와 함께 링크를 알려주시면 도구를 고칠 수 있습니다."
    )
