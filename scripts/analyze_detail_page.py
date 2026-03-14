"""
analyze_detail_page.py - 상세 페이지 HTML 구조 분석용 스크립트

사용법:
    python scripts/analyze_detail_page.py

DB에서 detail_url을 가져와 HTML을 저장하고 구조를 분석합니다.
"""

import sys
from pathlib import Path

from bs4 import BeautifulSoup
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from crawler import JobKoreaCrawler
from database import get_engine


def get_sample_detail_url():
    """DB에서 샘플 detail_url 가져오기"""
    config = Config()
    engine = get_engine(config)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT jp.detail_url, c.name
            FROM job_postings jp
            JOIN companies c ON jp.company_id = c.id
            WHERE jp.detail_url IS NOT NULL AND jp.detail_url != ''
            LIMIT 1
        """))
        row = result.fetchone()
        if row:
            return row[0], row[1]
        return None, None


def analyze_html_structure(html: str):
    """HTML 구조에서 기업 정보 관련 요소 탐색"""
    soup = BeautifulSoup(html, "html.parser")

    print("\n" + "=" * 60)
    print("🔍 기업 정보 관련 요소 탐색")
    print("=" * 60)

    # 1. 기업규모 관련 키워드 탐색
    keywords = ["기업규모", "사원수", "설립", "홈페이지", "대기업", "중견기업", "중소기업"]
    for keyword in keywords:
        elements = soup.find_all(string=lambda t: t and keyword in t)
        if elements:
            print(f"\n📌 '{keyword}' 발견: {len(elements)}개")
            for el in elements[:3]:
                parent = el.find_parent()
                if parent:
                    print(f"   - 부모 태그: {parent.name}, 클래스: {parent.get('class', [])}")

    # 2. 기업 정보 섹션 탐색 (일반적인 패턴)
    info_sections = soup.select('[class*="company"], [class*="corp"], [class*="info"]')
    print(f"\n📌 기업 정보 관련 섹션: {len(info_sections)}개")
    for section in info_sections[:5]:
        print(f"   - {section.name}.{section.get('class', [])}")

    # 3. dl/dt/dd 구조 탐색 (기업 정보에 흔히 사용)
    dl_elements = soup.find_all("dl")
    print(f"\n📌 dl 요소: {len(dl_elements)}개")

    # 4. 테이블 구조 탐색
    tables = soup.find_all("table")
    print(f"\n📌 table 요소: {len(tables)}개")


def main():
    config = Config()
    config.HEADLESS = False  # 디버깅을 위해 브라우저 표시

    detail_url, company_name = get_sample_detail_url()

    if not detail_url:
        print("❌ DB에 detail_url이 없습니다. 먼저 main.py를 실행하세요.")
        return

    print(f"🏢 회사: {company_name}")
    print(f"🔗 URL: {detail_url}")

    with JobKoreaCrawler(config) as crawler:
        html = crawler.crawl_detail_page(detail_url)

        if html:
            # HTML 파일로 저장
            output_path = PROJECT_ROOT / "output" / "sample_detail.html"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\n✅ HTML 저장: {output_path}")

            # 구조 분석
            analyze_html_structure(html)


if __name__ == "__main__":
    main()
