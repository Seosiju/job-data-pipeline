#!/usr/bin/env python
"""
analyze_jd_with_llm.py - LLM으로 JD 텍스트 구조화 분석

Usage:
    python scripts/analyze_jd_with_llm.py [--limit N] [--force]

Options:
    --limit N   처리할 최대 공고 수 (기본: 전체)
    --force     이미 분석된 공고도 재분석
"""

import argparse
import json
import logging
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text
from jobkorea.config import Config
from jobkorea.database import DatabaseManager
from jobkorea.analyzers.job_analyzer import analyze_job_posting, analyzed_to_dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="LLM JD 분석")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 공고 수")
    parser.add_argument("--force", action="store_true", help="이미 분석된 공고도 재분석")
    args = parser.parse_args()

    # DB 연결 및 스키마 업데이트
    config = Config()
    db = DatabaseManager(config)
    db.create_tables()  # 새 테이블 생성

    # 분석 대상 조회 (100자 이상 텍스트가 있는 공고)
    with db.connect() as conn:
        if args.force:
            query = """
                SELECT jp.id, jp.title, c.name as company, jp.raw_jd_text
                FROM job_postings jp
                JOIN companies c ON jp.company_id = c.id
                WHERE jp.raw_jd_text IS NOT NULL
                  AND LENGTH(jp.raw_jd_text) >= 100
                ORDER BY jp.id
            """
        else:
            query = """
                SELECT jp.id, jp.title, c.name as company, jp.raw_jd_text
                FROM job_postings jp
                JOIN companies c ON jp.company_id = c.id
                LEFT JOIN job_posting_analysis jpa ON jp.id = jpa.job_posting_id
                WHERE jp.raw_jd_text IS NOT NULL
                  AND LENGTH(jp.raw_jd_text) >= 100
                  AND jpa.id IS NULL
                ORDER BY jp.id
            """

        if args.limit:
            query += f" LIMIT {args.limit}"

        result = conn.execute(text(query))
        postings = [(row.id, row.title, row.company, row.raw_jd_text) for row in result]

    if not postings:
        print("분석할 공고가 없습니다.")
        return

    print(f"\n{'='*60}")
    print(f"LLM JD 분석 시작")
    print(f"{'='*60}")
    print(f"대상 공고: {len(postings)}개")
    print(f"강제 재분석: {'예' if args.force else '아니오'}")
    print(f"{'='*60}\n")

    # 통계
    stats = {
        "total": len(postings),
        "success": 0,
        "failed": 0,
        "multi_position": 0,
    }

    for i, (jp_id, title, company, jd_text) in enumerate(postings, 1):
        print(f"[{i}/{len(postings)}] {company[:15]} - {title[:35]}...")

        # LLM 분석
        result = analyze_job_posting(jd_text)

        if not result:
            print(f"  ❌ 분석 실패")
            stats["failed"] += 1
            continue

        stats["success"] += 1
        if result.is_multi_position:
            stats["multi_position"] += 1

        print(f"  ✓ {result.job_category} | 스킬: {len(result.required_skills)}필수/{len(result.preferred_skills)}우대 | {'다중' if result.is_multi_position else '단일'}포지션")

        # DB 저장
        with db.connect() as conn:
            # UPSERT (ON CONFLICT UPDATE)
            conn.execute(text("""
                INSERT INTO job_posting_analysis (
                    job_posting_id, is_multi_position, position_count, positions,
                    required_education, required_experience, required_skills,
                    preferred_skills, preferred_certifications, preferred_experience,
                    company_domain, job_category, analysis_confidence, analyzed_at
                ) VALUES (
                    :jp_id, :is_multi, :pos_count, :positions,
                    :req_edu, :req_exp, :req_skills,
                    :pref_skills, :pref_certs, :pref_exp,
                    :domain, :category, :confidence, :analyzed_at
                )
                ON CONFLICT (job_posting_id) DO UPDATE SET
                    is_multi_position = EXCLUDED.is_multi_position,
                    position_count = EXCLUDED.position_count,
                    positions = EXCLUDED.positions,
                    required_education = EXCLUDED.required_education,
                    required_experience = EXCLUDED.required_experience,
                    required_skills = EXCLUDED.required_skills,
                    preferred_skills = EXCLUDED.preferred_skills,
                    preferred_certifications = EXCLUDED.preferred_certifications,
                    preferred_experience = EXCLUDED.preferred_experience,
                    company_domain = EXCLUDED.company_domain,
                    job_category = EXCLUDED.job_category,
                    analysis_confidence = EXCLUDED.analysis_confidence,
                    analyzed_at = EXCLUDED.analyzed_at
            """), {
                "jp_id": jp_id,
                "is_multi": result.is_multi_position,
                "pos_count": result.position_count,
                "positions": json.dumps(result.positions, ensure_ascii=False),
                "req_edu": result.required_education,
                "req_exp": result.required_experience,
                "req_skills": json.dumps(result.required_skills, ensure_ascii=False),
                "pref_skills": json.dumps(result.preferred_skills, ensure_ascii=False),
                "pref_certs": json.dumps(result.preferred_certifications, ensure_ascii=False),
                "pref_exp": json.dumps(result.preferred_experience, ensure_ascii=False),
                "domain": result.company_domain,
                "category": result.job_category,
                "confidence": result.analysis_confidence,
                "analyzed_at": datetime.now(),
            })
            conn.commit()

    # 결과 출력
    print(f"\n{'='*60}")
    print(f"분석 완료")
    print(f"{'='*60}")
    print(f"  총 처리: {stats['total']}개")
    print(f"  성공: {stats['success']}개")
    print(f"  실패: {stats['failed']}개")
    print(f"  다중 포지션: {stats['multi_position']}개")


if __name__ == "__main__":
    main()
