"""
conftest.py - pytest fixtures
"""

import os
import pytest
from pathlib import Path
import importlib

# 프로젝트 루트를 path에 추가
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


FIXTURES_DIR = Path(__file__).parent / "fixtures"

# 테스트용 기본 환경변수 (실제 .env 오염 방지)
TEST_ENV_DEFAULTS = {
    "DB_HOST": "localhost",
    "DB_PORT": "5433",
    "DB_NAME": "jobkorea",
    "DB_USER": "postgres",
    "DB_PASSWORD": "jobkorea123",
    "SEARCH_KEYWORD": "데이터분석가",
    "SEARCH_KEYWORDS": "데이터분석가",
    "MAX_PAGES": "5",
    "HEADLESS": "true",
    "REQUEST_DELAY_MIN": "2",
    "REQUEST_DELAY_MAX": "5",
    "RETRY_ATTEMPTS": "3",
    "CONSECUTIVE_DUPLICATE_THRESHOLD": "20",
    "STALE_AFTER_DAYS": "7",
    "LOG_LEVEL": "INFO",
    "LOG_DIR": "log",
}


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """모든 테스트에서 환경변수를 격리하여 .env 오염 방지"""
    # 기존 환경변수 제거 후 테스트용 기본값 설정
    for key in TEST_ENV_DEFAULTS:
        monkeypatch.setenv(key, TEST_ENV_DEFAULTS[key])

    yield

    # config 모듈 캐시 정리 (다음 테스트를 위해)
    if "config" in sys.modules:
        del sys.modules["config"]


@pytest.fixture
def sample_list_html():
    """목록 페이지 샘플 HTML"""
    html_path = FIXTURES_DIR / "sample_list.html"
    return html_path.read_text(encoding="utf-8")


@pytest.fixture
def sample_detail_html():
    """상세 페이지 샘플 HTML"""
    html_path = FIXTURES_DIR / "sample_detail.html"
    return html_path.read_text(encoding="utf-8")


@pytest.fixture
def empty_html():
    """빈 HTML"""
    return "<html><body></body></html>"


@pytest.fixture
def mock_env(monkeypatch):
    """테스트용 환경변수 설정 (Config reload 포함)"""
    monkeypatch.setenv("DB_HOST", "testhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "testdb")
    monkeypatch.setenv("DB_USER", "testuser")
    monkeypatch.setenv("DB_PASSWORD", "testpass")
    monkeypatch.setenv("SEARCH_KEYWORD", "테스트키워드")
    monkeypatch.setenv("SEARCH_KEYWORDS", "테스트키워드")
    monkeypatch.setenv("MAX_PAGES", "3")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("CONSECUTIVE_DUPLICATE_THRESHOLD", "7")
    monkeypatch.setenv("STALE_AFTER_DAYS", "14")

    # Config 모듈 reload하여 새 환경변수 적용
    if "config" in sys.modules:
        del sys.modules["config"]


@pytest.fixture
def reload_config():
    """Config 모듈을 reload하여 현재 환경변수 반영"""
    if "config" in sys.modules:
        del sys.modules["config"]
    import config
    return config.Config()


@pytest.fixture
def test_db_config():
    """테스트용 DB 설정 (실제 테스트 DB 사용 시)"""
    from config import Config
    config = Config()
    # 테스트 DB 사용 시 여기서 설정 오버라이드
    return config
