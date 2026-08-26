import sys
from pathlib import Path

# 설치하지 않고도 테스트가 돌게 프로젝트 루트를 경로에 넣습니다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_html():
    def _load(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    return _load
