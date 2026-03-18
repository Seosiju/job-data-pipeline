#!/usr/bin/env python
"""
extract_jd_text.py - JD 상세 페이지에서 텍스트 추출 후 DB 저장

Usage:
    python scripts/extract_jd_text.py [--limit N] [--force]

Options:
    --limit N   처리할 최대 공고 수 (기본: 전체)
    --force     이미 추출된 공고도 재추출
"""

import argparse
import logging
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, "/Users/snu.sim/git/jobkorea")

from sqlalchemy import text
from config import Config
from database import DatabaseManager
from extractors.html_extractor import extract_jd_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="JD 텍스트 추출")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 공고 수")
    parser.add_argument("--force", action="store_true", help="이미 추출된 공고도 재추출")
    args = parser.parse_args()

    # DB 연결 및 스키마 업데이트
    config = Config()
    db = DatabaseManager(config)
    db.create_tables()  # 새 컬럼 추가

    # 추출 대상 공고 조회
    with db.connect() as conn:
        if args.force:
            query = text("""
                SELECT id, detail_url, title
                FROM job_postings
                WHERE detail_url IS NOT NULL
                ORDER BY id
            """)
        else:
            query = text("""
                SELECT id, detail_url, title
                FROM job_postings
                WHERE detail_url IS NOT NULL
                  AND (raw_jd_text IS NULL OR raw_jd_text = '')
                ORDER BY id
            """)

        if args.limit:
            query = text(str(query) + f" LIMIT {args.limit}")

        result = conn.execute(query)
        postings = [(row.id, row.detail_url, row.title) for row in result]

    if not postings:
        print("추출할 공고가 없습니다.")
        return

    print(f"\n{'='*60}")
    print(f"JD 텍스트 추출 시작")
    print(f"{'='*60}")
    print(f"대상 공고: {len(postings)}개")
    print(f"강제 재추출: {'예' if args.force else '아니오'}")
    print(f"{'='*60}\n")

    # Selenium 드라이버 설정
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    # 통계
    stats = {
        "total": len(postings),
        "text_based": 0,
        "image_based": 0,
        "error": 0,
    }

    try:
        for i, (jp_id, detail_url, title) in enumerate(postings, 1):
            print(f"[{i}/{len(postings)}] {title[:40]}...")

            # 텍스트 추출
            result = extract_jd_text(detail_url, driver=driver, wait_time=1.5)

            if result.error:
                print(f"  ❌ 오류: {result.error}")
                stats["error"] += 1
                continue

            # 통계 업데이트
            if result.is_text_based:
                stats["text_based"] += 1
                status = "✓ HTML"
            else:
                stats["image_based"] += 1
                status = "⚠ OCR필요"

            print(f"  {status} | {result.char_count:,}자")

            # DB 저장
            with db.connect() as conn:
                conn.execute(text("""
                    UPDATE job_postings
                    SET raw_jd_text = :text,
                        jd_extracted_at = :extracted_at
                    WHERE id = :id
                """), {
                    "text": result.text,
                    "extracted_at": datetime.now(),
                    "id": jp_id,
                })
                conn.commit()

    finally:
        driver.quit()

    # 결과 출력
    print(f"\n{'='*60}")
    print(f"추출 완료")
    print(f"{'='*60}")
    print(f"  총 처리: {stats['total']}개")
    print(f"  HTML 추출 가능: {stats['text_based']}개 ({stats['text_based']/stats['total']*100:.1f}%)")
    print(f"  OCR 필요: {stats['image_based']}개 ({stats['image_based']/stats['total']*100:.1f}%)")
    print(f"  오류: {stats['error']}개")


if __name__ == "__main__":
    main()
