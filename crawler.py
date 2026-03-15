"""
crawler.py - Selenium 기반 잡코리아 크롤러
"""

import time
import random
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from config import Config

logger = logging.getLogger(__name__)


BASE_URL = (
    "https://www.jobkorea.co.kr/Search/"
    "?stext={keyword}"
    "&FeatureCode=WRK"
    "&Page_No={page}"
    "&careerType=1,4"
    "&tabType=recruit"
)


class JobKoreaCrawler:
    """드라이버 생명주기를 관리하는 크롤러"""

    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        self.consecutive_failures = 0
        self.max_failures = 5
        self.last_page_diagnostics: dict[str, str | bool | None] | None = None

    def __enter__(self):
        """Context Manager 진입: 드라이버 생성"""
        self.driver = self._create_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료: 드라이버 정리"""
        if self.driver:
            self.driver.quit()
            logger.info("브라우저 종료")
        return False

    def _create_driver(self):
        """봇 탐지 우회가 적용된 Chrome WebDriver 생성"""
        options = Options()

        if self.config.HEADLESS:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        stealth(
            driver,
            languages=["ko-KR", "ko"],
            vendor="Google Inc.",
            platform="MacIntel",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        logger.info("Chrome WebDriver 생성 완료")
        return driver

    def _random_delay(self):
        """랜덤 딜레이 적용"""
        delay = random.uniform(self.config.DELAY_MIN, self.config.DELAY_MAX)
        logger.debug(f"대기 중: {delay:.1f}초")
        time.sleep(delay)

    def _apply_cooldown(self):
        """쿨다운 적용 (봇 탐지 의심 시)"""
        cooldown = random.uniform(60, 120)
        logger.warning(f"연속 실패 감지 - 쿨다운 적용: {cooldown:.0f}초 대기")
        time.sleep(cooldown)
        self.consecutive_failures = 0

    def _set_referer(self, referer: str):
        """다음 요청의 Referer 헤더 설정"""
        self.driver.execute_cdp_cmd(
            "Network.setExtraHTTPHeaders",
            {"headers": {"Referer": referer}}
        )

    def _get_diagnostic_dir(self) -> Path:
        """페이지 실패 진단 산출물 저장 디렉터리 반환"""
        diagnostic_dir = Path(__file__).resolve().parent / self.config.LOG_DIR / "page_diagnostics"
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        return diagnostic_dir

    def _safe_driver_attr(self, attr_name: str, default: str = "") -> str:
        """드라이버 속성 접근을 안전하게 감싼다."""
        try:
            value = getattr(self.driver, attr_name)
            return value or default
        except Exception:
            return default

    def _safe_page_source(self) -> str:
        """page_source 접근을 안전하게 감싼다."""
        return self._safe_driver_attr("page_source", "")

    def _format_wait_locator(self, wait_locator: tuple | None) -> str | None:
        """대기 selector를 사람이 읽을 수 있는 문자열로 변환한다."""
        if not wait_locator:
            return None
        return f"{wait_locator[0]}: {wait_locator[1]}"

    def _build_page_diagnostics(
        self,
        page_name: str,
        requested_url: str,
        wait_locator: tuple | None = None,
        error: Exception | None = None,
        html_path: Path | None = None,
        meta_path: Path | None = None,
    ) -> dict[str, str | bool | None]:
        """현재 브라우저 상태를 구조화된 진단 정보로 정리한다."""
        return {
            "page_name": page_name,
            "requested_url": requested_url,
            "final_url": self._safe_driver_attr("current_url") or None,
            "title": self._safe_driver_attr("title") or None,
            "wait_locator": self._format_wait_locator(wait_locator),
            "wait_timed_out": isinstance(error, TimeoutException),
            "error": str(error) if error else None,
            "html_path": str(html_path) if html_path else None,
            "meta_path": str(meta_path) if meta_path else None,
        }

    def get_last_page_diagnostics(self) -> dict[str, str | bool | None] | None:
        """최근 페이지 로딩의 진단 정보 사본 반환"""
        if self.last_page_diagnostics is None:
            return None
        return dict(self.last_page_diagnostics)

    def _capture_failure_diagnostics(
        self,
        page_name: str,
        requested_url: str,
        error: Exception,
        wait_locator: tuple | None = None,
    ) -> dict[str, str | bool | None] | None:
        """실패 시점의 최종 URL/제목/HTML을 저장한다."""
        if not self.driver:
            return None

        safe_page_name = "".join(
            char if char.isalnum() else "_"
            for char in page_name.lower()
        ).strip("_") or "page"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{safe_page_name}"
        diagnostic_dir = self._get_diagnostic_dir()

        page_source = self._safe_page_source()

        html_path = diagnostic_dir / f"{base_name}.html"
        meta_path = diagnostic_dir / f"{base_name}.txt"

        try:
            html_path.write_text(page_source, encoding="utf-8")
        except Exception as write_error:
            logger.warning("진단용 HTML 저장 실패: %s", write_error)
            html_path = None

        diagnostics = self._build_page_diagnostics(
            page_name=page_name,
            requested_url=requested_url,
            wait_locator=wait_locator,
            error=error,
            html_path=html_path,
            meta_path=meta_path,
        )

        try:
            meta_lines = [
                f"page_name: {page_name}",
                f"requested_url: {diagnostics['requested_url']}",
                f"current_url: {diagnostics['final_url'] or ''}",
                f"title: {diagnostics['title'] or ''}",
                f"wait_locator: {diagnostics['wait_locator'] or ''}",
                f"wait_timed_out: {diagnostics['wait_timed_out']}",
                f"error: {error}",
            ]
            meta_path.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")
        except Exception as write_error:
            logger.warning("진단용 메타데이터 저장 실패: %s", write_error)

        self.last_page_diagnostics = diagnostics
        logger.error(
            "%s 진단 정보 - requested_url=%s current_url=%s title=%s wait_locator=%s wait_timed_out=%s html=%s meta=%s",
            page_name,
            requested_url,
            diagnostics["final_url"] or "<empty>",
            diagnostics["title"] or "<empty>",
            diagnostics["wait_locator"] or "<empty>",
            diagnostics["wait_timed_out"],
            str(html_path) if html_path else "<not-saved>",
            str(meta_path),
        )

        return diagnostics

    def _load_page_with_retry(
        self,
        url: str,
        wait_locator: tuple,
        page_name: str,
        wait_seconds: int,
        render_delay: int,
        referer: str = None,
    ) -> str:
        """
        페이지 로딩 + 대기 + 재시도를 공통 처리

        Args:
            url: 접속할 URL
            wait_locator: 로딩 완료 판단용 locator
            page_name: 로깅용 페이지 이름
            wait_seconds: WebDriverWait 초
            render_delay: 렌더링 추가 대기
            referer: 선택적 referer 헤더

        Returns:
            str: 최종 HTML 소스

        Raises:
            Exception: 모든 재시도 실패 시 마지막 예외 재전파
        """
        last_error = None
        self.last_page_diagnostics = None

        for attempt in range(1, self.config.RETRY_ATTEMPTS + 1):
            try:
                if referer:
                    self._set_referer(referer)

                self.driver.get(url)
                WebDriverWait(self.driver, wait_seconds).until(
                    EC.presence_of_element_located(wait_locator)
                )

                time.sleep(render_delay)
                self.consecutive_failures = 0
                self.last_page_diagnostics = self._build_page_diagnostics(
                    page_name=page_name,
                    requested_url=url,
                    wait_locator=wait_locator,
                )
                return self.driver.page_source

            except Exception as e:
                last_error = e
                self.consecutive_failures += 1
                logger.warning(
                    f"{page_name} 로딩 실패 (시도 {attempt}/{self.config.RETRY_ATTEMPTS}): {url} - {e}"
                )

                if attempt < self.config.RETRY_ATTEMPTS:
                    backoff = (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.info(f"{page_name} 재시도 전 {backoff:.1f}초 대기")
                    time.sleep(backoff)

        if self.consecutive_failures >= self.max_failures:
            self._apply_cooldown()

        self._capture_failure_diagnostics(page_name, url, last_error, wait_locator=wait_locator)
        raise last_error

    def iter_list_pages(self, keyword: str = None):
        """
        목록 페이지를 순차적으로 yield하는 제너레이터

        Args:
            keyword: 검색 키워드 (None이면 config.SEARCH_KEYWORD 사용)

        Yields:
            tuple[int, str]: (페이지 번호, HTML 소스)
        """
        if keyword is None:
            keyword = self.config.SEARCH_KEYWORD

        encoded_keyword = quote(keyword)
        logger.info(f"목록 크롤링 시작 - 키워드: {keyword}, 최대 페이지: {self.config.MAX_PAGES}")

        for page in range(1, self.config.MAX_PAGES + 1):
            url = BASE_URL.format(keyword=encoded_keyword, page=page)
            referer = None

            if page > 1:
                referer = BASE_URL.format(keyword=encoded_keyword, page=page - 1)

            logger.info(f"페이지 {page}/{self.config.MAX_PAGES} 접속 중...")

            try:
                html = self._load_page_with_retry(
                    url=url,
                    wait_locator=(By.CSS_SELECTOR, '[data-sentry-component="CardJob"]'),
                    page_name="목록 페이지",
                    wait_seconds=15,
                    render_delay=2,
                    referer=referer,
                )
            except Exception as e:
                logger.error(f"목록 페이지 크롤링 중단: {url} - {e}")
                break

            yield page, html

            if page < self.config.MAX_PAGES:
                self._random_delay()

    def crawl_list_pages(self, keyword: str = None) -> list[str]:
        """
        Phase 1: 검색 결과 목록 페이지 크롤링

        Args:
            keyword: 검색 키워드 (None이면 config.SEARCH_KEYWORD 사용)

        Returns:
            list[str]: 각 페이지의 HTML 소스 리스트
        """
        html_pages = [html for _, html in self.iter_list_pages(keyword)]

        logger.info(f"목록 크롤링 완료 - 수집된 페이지: {len(html_pages)}")
        return html_pages

    def crawl_detail_page(self, url: str) -> str:
        """
        하위 호환성을 위한 회사 페이지 크롤링 래퍼

        Args:
            url: 회사 페이지 URL

        Returns:
            str: 페이지의 HTML 소스
        """
        return self.crawl_company_page(url)

    def crawl_job_detail_page(self, url: str) -> str:
        """
        Phase 2: JD 상세 페이지 크롤링

        Args:
            url: JD 상세 페이지 URL

        Returns:
            str: 페이지의 HTML 소스
        """
        try:
            return self._load_page_with_retry(
                url=url,
                wait_locator=(
                    By.CSS_SELECTOR,
                    '[data-sentry-component="CompanyName"], #details-section, #company-section',
                ),
                page_name="JD 상세 페이지",
                wait_seconds=15,
                render_delay=1,
                referer="https://www.jobkorea.co.kr/Search/",
            )

        except Exception as e:
            logger.error(f"JD 상세 페이지 크롤링 에러: {url} - {e}")
            return ""

    def crawl_company_page(self, url: str, referer: str = None) -> str:
        """
        Phase 2: 회사 상세 페이지 크롤링

        Args:
            url: 회사 페이지 URL
            referer: 선택적 referer URL

        Returns:
            str: 페이지의 HTML 소스
        """
        try:
            return self._load_page_with_retry(
                url=url,
                wait_locator=(
                    By.CSS_SELECTOR,
                    '.company-infomation-row.basic-infomation, '
                    'table.table-basic-infomation-primary, '
                    '.corpInfo, '
                    '.company-header .add-ons .home a.button-home',
                ),
                page_name="회사 페이지",
                wait_seconds=10,
                render_delay=1,
                referer=referer or "https://www.jobkorea.co.kr/Search/",
            )

        except Exception as e:
            logger.error(f"회사 페이지 크롤링 에러: {url} - {e}")
            return ""


# 하위 호환성을 위한 함수 (기존 코드 지원)
def crawl_pages(keyword: str, max_pages: int = 5) -> list[str]:
    """기존 함수 시그니처 유지 (하위 호환성)"""
    config = Config()
    config.SEARCH_KEYWORD = keyword
    config.MAX_PAGES = max_pages

    with JobKoreaCrawler(config) as crawler:
        return crawler.crawl_list_pages()
