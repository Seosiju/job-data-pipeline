"""
config.py - 환경변수 기반 설정 통합 관리
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent


def setup_logging(log_level: str = "INFO", log_dir: str = "log") -> logging.Logger:
    """로깅 시스템 초기화"""
    log_path = PROJECT_ROOT / log_dir
    log_path.mkdir(exist_ok=True)

    # 로그 포맷
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()

    # 파일 핸들러 (전체 로그)
    file_handler = logging.FileHandler(
        log_path / "crawler.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 에러 전용 파일 핸들러
    error_handler = logging.FileHandler(
        log_path / "error.log",
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


class Config:
    """환경변수 기반 설정 관리"""

    # DB 설정
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5433")
    DB_NAME: str = os.getenv("DB_NAME", "jobkorea")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "jobkorea123")

    # 크롤링 설정 - 다중 키워드 지원
    SEARCH_KEYWORDS: list = os.getenv(
        "SEARCH_KEYWORDS",
        "데이터분석가"
    ).split(",")

    # 단일 키워드 (하위 호환성)
    SEARCH_KEYWORD: str = os.getenv("SEARCH_KEYWORD", "데이터분석가")

    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "5"))
    DELAY_MIN: int = int(os.getenv("REQUEST_DELAY_MIN", "2"))
    DELAY_MAX: int = int(os.getenv("REQUEST_DELAY_MAX", "5"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "log")

    @property
    def database_url(self) -> str:
        """SQLAlchemy용 데이터베이스 URL 반환"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def validate(self) -> list[str]:
        """설정값 검증, 경고 메시지 리스트 반환"""
        warnings = []

        if self.MAX_PAGES > 100:
            warnings.append(f"MAX_PAGES가 매우 큽니다: {self.MAX_PAGES} (권장: 100 이하)")

        if self.DELAY_MIN >= self.DELAY_MAX:
            warnings.append(
                f"DELAY_MIN({self.DELAY_MIN})이 DELAY_MAX({self.DELAY_MAX})보다 크거나 같습니다"
            )

        if not self.SEARCH_KEYWORDS or self.SEARCH_KEYWORDS == [""]:
            warnings.append("SEARCH_KEYWORDS가 비어있습니다")

        return warnings
