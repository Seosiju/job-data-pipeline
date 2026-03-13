"""
crawler.py - Selenium 기반 잡코리아 크롤러
"""

import time
import random
import logging
from urllib.parse import quote

from selenium import webdriver
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

    def crawl_list_pages(self, keyword: str = None) -> list[str]:
        """
        Phase 1: 검색 결과 목록 페이지 크롤링

        Args:
            keyword: 검색 키워드 (None이면 config.SEARCH_KEYWORD 사용)

        Returns:
            list[str]: 각 페이지의 HTML 소스 리스트
        """
        if keyword is None:
            keyword = self.config.SEARCH_KEYWORD

        html_pages = []
        encoded_keyword = quote(keyword)

        logger.info(f"목록 크롤링 시작 - 키워드: {keyword}, 최대 페이지: {self.config.MAX_PAGES}")

        try:
            for page in range(1, self.config.MAX_PAGES + 1):
                url = BASE_URL.format(keyword=encoded_keyword, page=page)
                logger.info(f"페이지 {page}/{self.config.MAX_PAGES} 접속 중...")

                # Referer 설정 (봇 우회 보완)
                if page > 1:
                    prev_url = BASE_URL.format(keyword=encoded_keyword, page=page - 1)
                    self.driver.execute_cdp_cmd(
                        "Network.setExtraHTTPHeaders",
                        {"headers": {"Referer": prev_url}}
                    )

                self.driver.get(url)

                # 카드가 로딩될 때까지 대기
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, '[data-sentry-component="CardJob"]')
                        )
                    )
                    logger.debug(f"페이지 {page} 로딩 완료")
                    self.consecutive_failures = 0
                except Exception:
                    self.consecutive_failures += 1
                    logger.warning(f"페이지 {page} 로딩 타임아웃 (연속 실패: {self.consecutive_failures})")

                    if self.consecutive_failures >= self.max_failures:
                        self._apply_cooldown()
                    break

                time.sleep(2)  # 동적 렌더링 완료 대기
                html_pages.append(self.driver.page_source)

                # 다음 페이지 전 랜덤 딜레이
                if page < self.config.MAX_PAGES:
                    self._random_delay()

        except Exception as e:
            logger.error(f"목록 크롤링 중 에러: {e}", exc_info=True)

        logger.info(f"목록 크롤링 완료 - 수집된 페이지: {len(html_pages)}")
        return html_pages

    def crawl_detail_page(self, url: str) -> str:
        """
        Phase 2: 상세 페이지 크롤링

        Args:
            url: 상세 페이지 URL

        Returns:
            str: 페이지의 HTML 소스
        """
        try:
            # Referer 설정 (목록 페이지에서 온 것처럼)
            self.driver.execute_cdp_cmd(
                "Network.setExtraHTTPHeaders",
                {"headers": {"Referer": "https://www.jobkorea.co.kr/Search/"}}
            )

            self.driver.get(url)

            # 기업 정보 섹션 로딩 대기
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[class*="inner-wrap"], [class*="company-info"]')
                    )
                )
                self.consecutive_failures = 0
            except Exception:
                self.consecutive_failures += 1
                logger.warning(f"상세 페이지 로딩 타임아웃: {url}")

                if self.consecutive_failures >= self.max_failures:
                    self._apply_cooldown()

            time.sleep(1)  # 동적 렌더링 완료 대기
            return self.driver.page_source

        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"상세 페이지 크롤링 에러: {url} - {e}")
            return ""


# 하위 호환성을 위한 함수 (기존 코드 지원)
def crawl_pages(keyword: str, max_pages: int = 5) -> list[str]:
    """기존 함수 시그니처 유지 (하위 호환성)"""
    config = Config()
    config.SEARCH_KEYWORD = keyword
    config.MAX_PAGES = max_pages

    with JobKoreaCrawler(config) as crawler:
        return crawler.crawl_list_pages()
