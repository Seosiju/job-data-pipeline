"""
main.py - 잡코리아 크롤링 실행 진입점
=========================================
사용법:
    python main.py

전체 흐름:
    1. PostgreSQL 테이블 생성
    2. 잡코리아 검색 결과 크롤링 (전체 페이지)
    3. HTML 파싱 → 데이터 추출
    4. DB 저장 (companies + job_postings)
    5. 결과 요약 출력
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import text

from crawler import crawl_pages
from parser import parse_job_cards
from database import get_engine, create_tables, get_or_create_company, insert_job_posting

load_dotenv()

SEARCH_KEYWORD = os.getenv("SEARCH_KEYWORD", "데이터분석가")
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))


def main():
    print("=" * 60)
    print("잡코리아 크롤링 - 본 실행")
    print(f"검색어: {SEARCH_KEYWORD}")
    print(f"최대 페이지: {MAX_PAGES}")
    print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. DB 준비
    print("\n📦 데이터베이스 준비...")
    engine = get_engine()
    create_tables(engine)

    # 2. 크롤링
    print("\n🕷️ 크롤링 시작...")
    html_pages = crawl_pages(SEARCH_KEYWORD, MAX_PAGES)
    print(f"\n   수집된 페이지 수: {len(html_pages)}")

    # 3. 파싱 + DB 저장
    print("\n💾 데이터 파싱 및 DB 저장...")
    total_saved = 0
    total_skipped = 0

    with engine.connect() as conn:
        for page_num, html in enumerate(html_pages, 1):
            print(f"\n--- 페이지 {page_num} 파싱 ---")
            jobs = parse_job_cards(html)

            for job in jobs:
                company_name = job.get("company", "")
                if not company_name:
                    continue

                # 회사 등록/조회
                company_id = get_or_create_company(
                    conn,
                    company_name,
                    industry=job.get("industry", "")
                )

                # 공고 저장
                try:
                    insert_job_posting(conn, company_id, job)
                    total_saved += 1
                except Exception as e:
                    total_skipped += 1

            conn.commit()

    # 4. 결과 요약
    print("\n" + "=" * 60)
    print("📊 크롤링 결과 요약")
    print("=" * 60)

    with engine.connect() as conn:
        company_count = conn.execute(text("SELECT COUNT(*) FROM companies")).fetchone()[0]
        job_count = conn.execute(text("SELECT COUNT(*) FROM job_postings")).fetchone()[0]

        print(f"  등록된 회사 수: {company_count}개")
        print(f"  등록된 공고 수: {job_count}건")
        print(f"  이번 실행 저장: {total_saved}건")
        print(f"  중복 건너뜀:   {total_skipped}건")

        # 상위 5건 미리보기
        print("\n📋 최근 공고 5건:")
        rows = conn.execute(text("""
            SELECT jp.title, c.name, jp.location, jp.experience
            FROM job_postings jp
            JOIN companies c ON jp.company_id = c.id
            ORDER BY jp.crawled_at DESC
            LIMIT 5
        """)).fetchall()

        for i, row in enumerate(rows, 1):
            print(f"  [{i}] {row[1]} - {row[0]} ({row[2]}, {row[3]})")

    print(f"\n종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
