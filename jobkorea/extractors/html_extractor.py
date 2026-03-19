"""
html_extractor.py - JD 상세 페이지에서 텍스트 추출

잡코리아 JD 상세 페이지 구조:
- 메인 페이지: https://www.jobkorea.co.kr/Recruit/GI_Read/{gno}
- iframe 콘텐츠: https://www.jobkorea.co.kr/Recruit/GI_Read_Comt_Ifrm?Gno={gno}

iframe 내부에 실제 채용 상세 내용이 있으며,
일부는 HTML 텍스트, 일부는 이미지로 구성됨.
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


@dataclass
class JDExtractionResult:
    """JD 텍스트 추출 결과"""
    text: str
    char_count: int
    is_text_based: bool  # True: HTML 텍스트 기반, False: 이미지 기반 (OCR 필요)
    image_urls: list[str]
    error: Optional[str] = None


# 텍스트 기반 여부 판단 임계값 (최소 글자 수)
MIN_TEXT_THRESHOLD = 100


def extract_gno_from_url(detail_url: str) -> Optional[str]:
    """
    detail_url에서 Gno(공고 번호) 추출

    예: https://www.jobkorea.co.kr/Recruit/GI_Read/48534714?... -> 48534714
    """
    match = re.search(r'GI_Read/(\d+)', detail_url)
    return match.group(1) if match else None


def extract_jd_text(
    detail_url: str,
    driver: Optional[webdriver.Chrome] = None,
    wait_time: float = 2.0,
) -> JDExtractionResult:
    """
    JD 상세 페이지에서 텍스트 추출

    Args:
        detail_url: 공고 상세 URL (GI_Read 형식)
        driver: 기존 Selenium WebDriver (없으면 새로 생성)
        wait_time: 페이지 로딩 대기 시간 (초)

    Returns:
        JDExtractionResult: 추출 결과
    """
    gno = extract_gno_from_url(detail_url)
    if not gno:
        return JDExtractionResult(
            text="",
            char_count=0,
            is_text_based=False,
            image_urls=[],
            error=f"Invalid URL format: {detail_url}"
        )

    # iframe URL 생성
    iframe_url = f"https://www.jobkorea.co.kr/Recruit/GI_Read_Comt_Ifrm?Gno={gno}"

    # WebDriver 생성 (필요시)
    own_driver = False
    if driver is None:
        own_driver = True
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

    try:
        driver.get(iframe_url)
        time.sleep(wait_time)

        # 렌더링된 텍스트 추출
        body = driver.find_element(By.TAG_NAME, "body")
        visible_text = body.text.strip()

        # 이미지 URL 추출
        images = driver.find_elements(By.CSS_SELECTOR, "img")
        image_urls = [
            img.get_attribute("src")
            for img in images
            if img.get_attribute("src")
        ]

        # 텍스트 기반 여부 판단
        is_text_based = len(visible_text) >= MIN_TEXT_THRESHOLD

        return JDExtractionResult(
            text=visible_text,
            char_count=len(visible_text),
            is_text_based=is_text_based,
            image_urls=image_urls,
        )

    except Exception as e:
        logger.error(f"JD 텍스트 추출 실패: {detail_url} - {e}")
        return JDExtractionResult(
            text="",
            char_count=0,
            is_text_based=False,
            image_urls=[],
            error=str(e)
        )

    finally:
        if own_driver:
            driver.quit()


def extract_jd_text_batch(
    detail_urls: list[str],
    headless: bool = True,
    wait_time: float = 1.5,
    progress_callback=None,
) -> dict[str, JDExtractionResult]:
    """
    여러 JD에서 텍스트 일괄 추출

    Args:
        detail_urls: 공고 상세 URL 리스트
        headless: 헤드리스 모드 여부
        wait_time: 각 페이지 로딩 대기 시간
        progress_callback: 진행 콜백 함수 (current, total, url)

    Returns:
        dict: {detail_url: JDExtractionResult}
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    results = {}

    try:
        for i, url in enumerate(detail_urls):
            if progress_callback:
                progress_callback(i + 1, len(detail_urls), url)

            result = extract_jd_text(url, driver=driver, wait_time=wait_time)
            results[url] = result

    finally:
        driver.quit()

    return results
