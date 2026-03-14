"""
analyze_detail_page.py - Phase 2 상세 페이지 구조 분석용 스크립트

사용법:
    python scripts/analyze_detail_page.py --mode jd
    python scripts/analyze_detail_page.py --mode company

JD 상세 또는 저장된 회사 페이지 URL을 가져와 HTML을 저장하고 구조를 분석합니다.
"""

import argparse
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from crawler import JobKoreaCrawler
from database import get_engine
from parser import parse_company_detail, parse_company_page_url_from_job_detail


def get_sample_job_detail_target() -> tuple[str | None, str | None]:
    """DB에서 JD 분석용 샘플 detail_url 가져오기"""
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


def get_sample_company_page_target() -> tuple[str | None, str | None]:
    """DB에서 회사 페이지 분석용 샘플 company_page_url 가져오기"""
    config = Config()
    engine = get_engine(config)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.company_page_url, c.name
            FROM companies c
            WHERE c.company_page_url IS NOT NULL
              AND c.company_page_url != ''
            ORDER BY c.updated_at DESC, c.id DESC
            LIMIT 1
        """))
        row = result.fetchone()
        if row:
            return row[0], row[1]
        return None, None


def analyze_html_structure(html: str, mode: str):
    """HTML 구조에서 Phase 2 관련 요소 탐색"""
    soup = BeautifulSoup(html, "html.parser")

    print("\n" + "=" * 60)
    if mode == "jd":
        print("🔍 JD 상세 구조 분석")
    else:
        print("🔍 회사 페이지 구조 분석")
    print("=" * 60)

    if mode == "jd":
        company_page_url = parse_company_page_url_from_job_detail(html)
        print(f"\n📌 추출된 회사 페이지 URL: {company_page_url or '없음'}")

    if mode == "company":
        parsed_details = parse_company_detail(html)
        print(f"\n📌 파싱 결과 미리보기: {parsed_details}")

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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="Phase 2 JD/회사 페이지 구조를 수동 분석한다."
    )
    parser.add_argument(
        "--mode",
        choices=("jd", "company"),
        default="jd",
        help="분석할 페이지 타입",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = Config()
    config.HEADLESS = False  # 디버깅을 위해 브라우저 표시

    if args.mode == "jd":
        target_url, company_name = get_sample_job_detail_target()
        output_name = "sample_job_detail.html"
        crawl_fn_name = "crawl_job_detail_page"
    else:
        target_url, company_name = get_sample_company_page_target()
        output_name = "sample_company_page.html"
        crawl_fn_name = "crawl_company_page"

    if not target_url:
        if args.mode == "jd":
            print("❌ DB에 detail_url이 없습니다. 먼저 main.py를 실행하세요.")
        else:
            print("❌ DB에 저장된 company_page_url이 없습니다. 먼저 Phase 2를 실행하거나 --mode jd를 사용하세요.")
        return 1

    print(f"🏢 회사: {company_name}")
    print(f"🔗 URL: {target_url}")
    print(f"🧭 모드: {args.mode}")

    with JobKoreaCrawler(config) as crawler:
        crawl_fn = getattr(crawler, crawl_fn_name)
        html = crawl_fn(target_url)

        if html:
            # HTML 파일로 저장
            output_path = PROJECT_ROOT / "output" / output_name
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\n✅ HTML 저장: {output_path}")

            # 구조 분석
            analyze_html_structure(html, args.mode)
            return 0

    print("❌ HTML을 가져오지 못했습니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
