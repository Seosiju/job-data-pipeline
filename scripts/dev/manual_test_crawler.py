"""
잡코리아 크롤링 Phase 1 - 수동 점검 크롤러
=========================================
목적: 1페이지만 크롤링하여 데이터 품질 확인
출력: output/test_result.csv

사용법:
    pip install -r requirements.txt
    python scripts/manual_test_crawler.py
"""

import os
import time
import random
import csv
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ============================================================
# 설정
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SEARCH_KEYWORD = os.getenv("SEARCH_KEYWORD", "데이터분석가")
MAX_PAGES = int(os.getenv("MAX_PAGES", "1"))
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

# 전체 컬럼 모두 활성화
COLUMNS = [
    "title",        # 공고 제목
    "company",      # 회사명
    "location",     # 근무지역
    "industry",     # 업종
    "job_category", # 직무 카테고리
    "salary",       # 급여 정보
    "experience",   # 경력 조건
    "benefits",     # 복리후생
    "badge",        # 뱃지
    "apply_type",   # 지원 방식
    "posted_date",  # 등록일
    "deadline",     # 마감일
    "detail_url",   # 상세 URL
]

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "test_result.csv"


# ============================================================
# 브라우저 초기화
# ============================================================
def create_driver():
    """봇 탐지 우회가 적용된 Chrome WebDriver 생성"""
    options = Options()
    # headless 모드 (화면 없이 실행). 디버깅 시 아래 줄을 주석 처리하면 브라우저가 보임
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

    # selenium-stealth 적용
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


# ============================================================
# 파싱
# ============================================================
def parse_job_cards(html_source):
    """
    HTML에서 채용공고 카드를 파싱하여 리스트로 반환.

    각 카드(CardJob 컴포넌트)에서 다음을 추출:
      - title: size18 Typography 텍스트
      - company: size16 Typography 텍스트
      - location: emoji-place2 옆 텍스트
      - experience: size13 Typography (경력 정보)
      - detail_url: 첫 번째 <a> 태그의 href
    """
    soup = BeautifulSoup(html_source, "html.parser")
    cards = soup.find_all("div", attrs={"data-sentry-component": "CardJob"})

    print(f"  발견된 카드 수: {len(cards)}")
    jobs = []

    for i, card in enumerate(cards, 1):
        try:
            job = extract_card_data(card)
            jobs.append(job)
            print(f"  [{i}] {job['company']} - {job['title']}")
        except Exception as e:
            print(f"  [{i}] 파싱 실패: {e}")

    return jobs


def extract_card_data(card):
    """개별 카드에서 데이터 추출"""
    job = {}

    # 1) 공고 제목 (size18 Typography)
    title_el = card.select_one(
        '[class*="Typography_variant_size18"]'
    )
    job["title"] = title_el.get_text(strip=True) if title_el else ""

    # 2) 회사명 (size16 Typography)
    company_el = card.select_one(
        '[class*="Typography_variant_size16"]'
    )
    job["company"] = company_el.get_text(strip=True) if company_el else ""

    # 3) 근무지역 (emoji-place2 아이콘 옆 텍스트)
    location_chip = card.select_one('[class*="emoji--basicemoji-place2"]')
    if location_chip:
        chip_parent = location_chip.find_parent(
            attrs={"data-sentry-component": "GrayChip"}
        )
        if chip_parent:
            loc_text = chip_parent.select_one(
                '[class*="Typography_variant_size14"]'
            )
            job["location"] = loc_text.get_text(strip=True) if loc_text else ""
        else:
            job["location"] = ""
    else:
        job["location"] = ""

    # 4) 경력 조건 (size13 Typography - 첫 번째 flex-shrink_0)
    exp_el = card.select_one(
        '[class*="Typography_variant_size13"][class*="flex-shrink_0"]'
    )
    job["experience"] = exp_el.get_text(strip=True) if exp_el else ""

    # 5) 상세 URL
    link_el = card.select_one('a[href*="/Recruit/GI_Read/"]')
    if link_el:
        href = link_el.get("href", "")
        if href.startswith("/"):
            href = "https://www.jobkorea.co.kr" + href
        job["detail_url"] = href
    else:
        job["detail_url"] = ""

    # ========================================================
    # 전체 컬럼 추출 로직 활성화
    # ========================================================

    # 업종 (briefcase 아이콘 옆 GrayChip)
    industry_chip = card.select_one('[class*="emoji--basicemoji-briefcase"]')
    if industry_chip:
        chip_parent = industry_chip.find_parent(
            attrs={"data-sentry-component": "GrayChip"}
        )
        if chip_parent:
            text = chip_parent.select_one(
                '[class*="Typography_variant_size14"]'
            )
            raw = text.get_text(strip=True) if text else ""
            # "은행·금융, 데이터분석가" → 쉼표 기준 분리
            parts = [p.strip() for p in raw.split(",")]
            job["industry"] = parts[0] if parts else ""
            job["job_category"] = ", ".join(parts[1:]) if len(parts) > 1 else ""

    # 급여 (money_bill 아이콘 옆 텍스트)
    salary_chip = card.select_one('[class*="emoji--basicemoji-money_bill"]')
    if salary_chip:
        chip_parent = salary_chip.find_parent(
            attrs={"data-sentry-component": "GrayChip"}
        )
        if chip_parent:
            sal_text = chip_parent.select_one(
                '[class*="Typography_variant_size14"]'
            )
            job["salary"] = sal_text.get_text(strip=True) if sal_text else ""
    else:
        job["salary"] = ""

    # 뱃지 (BadgeItem 컴포넌트)
    badge_el = card.select_one('[data-sentry-component="BadgeItem"] span')
    job["badge"] = badge_el.get_text(strip=True) if badge_el else ""

    # 지원 방식 (즉시 지원 / 홈페이지 지원)
    apply_btn = card.select_one(
        '[class*="_16czznu"] [class*="Typography_variant_size12"]'
    )
    job["apply_type"] = apply_btn.get_text(strip=True) if apply_btn else ""

    # 등록일, 마감일 (size13 Typography 중 날짜 형식)
    date_spans = card.select(
        '[class*="Typography_variant_size13"][class*="Typography_weight_regular"]'
    )
    dates = [s.get_text(strip=True) for s in date_spans if "등록" in s.get_text() or "마감" in s.get_text() or "채용" in s.get_text()]
    job["posted_date"] = dates[0] if len(dates) > 0 else ""
    job["deadline"] = dates[1] if len(dates) > 1 else ""

    # 복리후생
    benefit_spans = [s.get_text(strip=True) for s in date_spans]
    benefit_texts = [t for t in benefit_spans if "지원" in t or "제도" in t or "보험" in t]
    job["benefits"] = ", ".join(benefit_texts) if benefit_texts else ""

    return job


# ============================================================
# CSV 저장
# ============================================================
def save_to_csv(jobs, filepath):
    """수집된 데이터를 CSV로 저장"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for job in jobs:
            row = {col: job.get(col, "") for col in COLUMNS}
            writer.writerow(row)

    print(f"\n✅ CSV 저장 완료: {filepath}")
    print(f"   총 {len(jobs)}건 저장됨")


# ============================================================
# 메인 실행
# ============================================================
def main():
    print("=" * 60)
    print("잡코리아 크롤링 Phase 1 - 테스트")
    print(f"검색어: {SEARCH_KEYWORD}")
    print(f"페이지 수: {MAX_PAGES}")
    print(f"딜레이: {DELAY_MIN}~{DELAY_MAX}초")
    print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    driver = create_driver()
    all_jobs = []

    try:
        for page in range(1, MAX_PAGES + 1):
            url = BASE_URL.format(keyword=SEARCH_KEYWORD, page=page)
            print(f"\n📄 페이지 {page} 접속 중...")
            print(f"   URL: {url}")

            driver.get(url)

            # 페이지 로딩 대기 (CardJob 컴포넌트가 나타날 때까지)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[data-sentry-component="CardJob"]')
                    )
                )
                print("   ✅ 페이지 로딩 완료")
            except Exception:
                print("   ⚠️ 페이지 로딩 타임아웃 (15초) - 현재 HTML로 진행")

            # 추가 대기 (동적 렌더링 완료를 위해)
            time.sleep(2)

            # HTML 파싱
            html = driver.page_source
            jobs = parse_job_cards(html)
            all_jobs.extend(jobs)

            # 다음 페이지 전 딜레이
            if page < MAX_PAGES:
                delay = random.uniform(DELAY_MIN, DELAY_MAX)
                print(f"\n⏳ 다음 페이지까지 {delay:.1f}초 대기...")
                time.sleep(delay)

    except Exception as e:
        print(f"\n❌ 크롤링 중 에러 발생: {e}")
        # 에러 발생 시에도 수집된 데이터는 저장
        if all_jobs:
            print("   수집된 데이터까지만 저장합니다.")

    finally:
        driver.quit()
        print("\n🔒 브라우저 종료")

    # CSV 저장
    if all_jobs:
        save_to_csv(all_jobs, OUTPUT_FILE)

        # 결과 미리보기
        print("\n" + "=" * 60)
        print("📊 결과 미리보기 (상위 5건)")
        print("=" * 60)
        for i, job in enumerate(all_jobs[:5], 1):
            print(f"\n  [{i}]")
            for col in COLUMNS:
                value = job.get(col, "")
                # URL은 길어서 50자까지만 표시
                if col == "detail_url" and len(value) > 50:
                    value = value[:50] + "..."
                print(f"    {col}: {value}")
    else:
        print("\n❌ 수집된 데이터가 없습니다.")

    print(f"\n종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
