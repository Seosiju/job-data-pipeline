"""
crawler.py - Selenium 기반 잡코리아 크롤러
"""

import os
import time
import random
from urllib.parse import quote

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

DELAY_MIN = int(os.getenv("REQUEST_DELAY_MIN", "2"))
DELAY_MAX = int(os.getenv("REQUEST_DELAY_MAX", "5"))

BASE_URL = (
    "https://www.jobkorea.co.kr/Search/"
    "?stext={keyword}"
    "&FeatureCode=WRK"
    "&Page_No={page}"
    "&careerType=1,4"
    "&tabType=recruit"
)


def create_driver():
    """봇 탐지 우회가 적용된 Chrome WebDriver 생성"""
    options = Options()
    # headless 모드 (백그라운드 실행). 디버깅 시 주석처리하면 브라우저가 보임
    # options.add_argument("--headless=new")
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

    return driver


def crawl_pages(keyword, max_pages=5):
    """
    검색어 기반으로 여러 페이지를 크롤링하여 HTML 소스 리스트 반환.

    Returns:
        list[str]: 각 페이지의 HTML 소스 리스트
    """
    driver = create_driver()
    html_pages = []

    try:
        for page in range(1, max_pages + 1):
            url = BASE_URL.format(keyword=keyword, page=page)
            print(f"\n📄 페이지 {page}/{max_pages} 접속 중...")
            print(f"   URL: {url}")

            driver.get(url)

            # 카드가 로딩될 때까지 대기
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[data-sentry-component="CardJob"]')
                    )
                )
                print("   ✅ 페이지 로딩 완료")
            except Exception:
                print("   ⚠️ 페이지 로딩 타임아웃 - 카드가 없을 수 있음 (마지막 페이지?)")
                # 카드가 없으면 마지막 페이지로 판단하고 종료
                break

            time.sleep(2)  # 동적 렌더링 완료 대기
            html_pages.append(driver.page_source)

            # 다음 페이지 전 랜덤 딜레이
            if page < max_pages:
                delay = random.uniform(DELAY_MIN, DELAY_MAX)
                print(f"   ⏳ {delay:.1f}초 대기...")
                time.sleep(delay)

    except Exception as e:
        print(f"\n❌ 크롤링 중 에러: {e}")

    finally:
        driver.quit()
        print("\n🔒 브라우저 종료")

    return html_pages
