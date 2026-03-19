"""
JobKorea Crawler - 잡코리아 채용공고 수집 패키지

Phase 1: 검색 결과 목록 페이지를 수집해 companies, job_postings에 저장
Phase 2: JD 상세를 거쳐 회사 페이지를 방문해 companies를 업데이트
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("jobkorea-crawler")
except PackageNotFoundError:
    __version__ = "0.0.0"  # 패키지 미설치 시 fallback

__author__ = "JobKorea Crawler Team"

# Core modules
from jobkorea.config import Config, setup_logging
from jobkorea.crawler import JobKoreaCrawler
from jobkorea.parser import parse_job_cards, parse_company_detail
from jobkorea.validators import validate_job_posting, validate_company_details
from jobkorea.database import DatabaseManager

__all__ = [
    "Config",
    "setup_logging",
    "JobKoreaCrawler",
    "parse_job_cards",
    "parse_company_detail",
    "validate_job_posting",
    "validate_company_details",
    "DatabaseManager",
]
