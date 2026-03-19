"""
test_config.py - Config 클래스 단위 테스트
"""

import logging

import pytest


class TestConfig:
    """Config 클래스 테스트"""

    def test_default_values(self, reload_config):
        """기본값이 올바르게 설정되는지 확인 (isolate_env fixture가 기본값 설정)"""
        config = reload_config

        # 기본값 확인 (conftest.py의 TEST_ENV_DEFAULTS 값)
        assert config.DB_HOST == "localhost"
        assert config.DB_PORT == "5433"
        assert config.DB_NAME == "jobkorea"
        assert config.SEARCH_KEYWORD == "데이터분석가"
        assert config.SEARCH_LOCATIONS == []
        assert config.SEARCH_EXPERIENCE_TYPES == []
        assert config.SEARCH_EMPLOYMENT_TYPES == []
        assert config.MAX_PAGES == 5
        assert config.RETRY_ATTEMPTS == 3
        assert config.CONSECUTIVE_DUPLICATE_THRESHOLD == 20
        assert config.STALE_AFTER_DAYS == 7
        assert isinstance(config.HEADLESS, bool)

    def test_database_url_format(self, reload_config):
        """database_url이 올바른 형식으로 생성되는지 확인"""
        config = reload_config

        url = config.database_url
        assert url.startswith("postgresql://")
        assert config.DB_HOST in url
        assert config.DB_PORT in url
        assert config.DB_NAME in url

    def test_database_url_components(self, reload_config):
        """database_url에 모든 구성요소가 포함되는지 확인"""
        config = reload_config

        expected = f"postgresql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
        assert config.database_url == expected

    def test_env_override(self, mock_env):
        """환경변수로 설정을 오버라이드할 수 있는지 확인"""
        # mock_env fixture가 환경변수를 설정하고 config 모듈 캐시 정리
        import sys
        if "jobkorea.config" in sys.modules:
            del sys.modules["jobkorea.config"]

        from jobkorea.config import Config
        config = Config()

        assert config.DB_HOST == "testhost"
        assert config.DB_PORT == "5432"
        assert config.DB_NAME == "testdb"
        assert config.SEARCH_KEYWORD == "테스트키워드"
        assert config.SEARCH_LOCATIONS == ["서울", "인천"]
        assert config.SEARCH_EXPERIENCE_TYPES == ["신입", "경력무관"]
        assert config.SEARCH_EMPLOYMENT_TYPES == ["정규직", "계약직", "인턴"]
        assert config.MAX_PAGES == 3
        assert config.RETRY_ATTEMPTS == 5
        assert config.CONSECUTIVE_DUPLICATE_THRESHOLD == 7
        assert config.STALE_AFTER_DAYS == 14
        assert config.HEADLESS is False

    def test_delay_values(self, reload_config):
        """딜레이 설정이 유효한지 확인"""
        config = reload_config

        assert config.DELAY_MIN >= 0
        assert config.DELAY_MAX >= config.DELAY_MIN

    def test_setup_logging_uses_warning_level_for_console(self, tmp_path):
        """콘솔 로그는 WARNING 이상만 출력"""
        from jobkorea.config import setup_logging

        root_logger = logging.getLogger()
        original_handlers = list(root_logger.handlers)
        original_level = root_logger.level

        try:
            logger = setup_logging("DEBUG", str(tmp_path))
            console_handlers = [
                handler
                for handler in logger.handlers
                if isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, logging.FileHandler)
            ]

            assert len(console_handlers) == 1
            assert console_handlers[0].level == logging.WARNING
        finally:
            for handler in list(root_logger.handlers):
                handler.close()
            root_logger.handlers.clear()
            root_logger.handlers.extend(original_handlers)
            root_logger.setLevel(original_level)
