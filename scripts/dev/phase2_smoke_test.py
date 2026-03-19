"""
phase2_smoke_test.py - 소규모 Phase 2 live validation 스크립트

사용법:
    python scripts/phase2_smoke_test.py --limit 3

목적:
    - 현재 Phase 2 대상 중 일부 회사만 골라 실제로 보강 경로를 검증한다.
    - `company_page_url` 백필과 재사용이 live site 기준으로 동작하는지 확인한다.
    - 전체 `main.py`를 돌리지 않고도 회사 페이지 실패 사례를 빠르게 좁힌다.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from jobkorea.config import Config
from jobkorea.database import DatabaseManager
from jobkorea.main import run_phase2_for_companies


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="제한된 회사 수만 대상으로 Phase 2 live smoke test를 수행한다."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="검증할 회사 수",
    )
    parser.add_argument(
        "--headless",
        choices=("true", "false"),
        default="true",
        help="브라우저 headless 모드",
    )
    parser.add_argument(
        "--company-id",
        type=int,
        help="특정 회사 ID만 대상으로 강제 재현",
    )
    return parser.parse_args(argv)


def get_company_candidate_by_id(db: DatabaseManager, company_id: int) -> dict | None:
    """특정 회사 ID의 Phase 2 실행용 후보 행을 조회한다."""
    with db.engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    c.id,
                    c.name,
                    c.company_page_url,
                    latest_job.detail_url
                FROM companies c
                LEFT JOIN LATERAL (
                    SELECT jp.detail_url
                    FROM job_postings jp
                    WHERE jp.company_id = c.id
                      AND jp.detail_url IS NOT NULL
                    ORDER BY COALESCE(jp.last_seen_at, jp.crawled_at) DESC NULLS LAST,
                             jp.id DESC NULLS LAST
                    LIMIT 1
                ) latest_job ON TRUE
                WHERE c.id = :company_id
                LIMIT 1
            """),
            {"company_id": company_id},
        ).mappings().first()

    if row is None:
        return None

    candidate = dict(row)
    if not candidate.get("company_page_url") and not candidate.get("detail_url"):
        return None
    return candidate


def get_smoke_test_candidates(
    db: DatabaseManager,
    limit: int,
    company_id: int | None = None,
) -> list[dict]:
    """smoke test 후보를 조회한다."""
    if company_id is None:
        return db.get_companies_without_details(limit=limit)

    candidate = get_company_candidate_by_id(db, company_id)
    if candidate is None:
        return []
    return [candidate]


def get_company_snapshots(db: DatabaseManager, company_ids: list[int]) -> dict[int, dict]:
    """선택된 회사의 전/후 상태 스냅샷을 조회한다."""
    if not company_ids:
        return {}

    with db.engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    id,
                    name,
                    company_page_url,
                    company_size,
                    employee_count,
                    establishment_year,
                    homepage_url
                FROM companies
                WHERE id = ANY(:company_ids)
                ORDER BY id
            """),
            {"company_ids": company_ids},
        ).mappings().all()

    return {row["id"]: dict(row) for row in rows}


def print_candidates(candidates: list[dict]) -> None:
    """검증 대상 회사 목록 출력"""
    print("\n선택된 Phase 2 smoke test 대상:")
    for candidate in candidates:
        print(
            f"- id={candidate['id']} name={candidate['name']} "
            f"cached_url={'yes' if candidate.get('company_page_url') else 'no'} "
            f"detail_url={'yes' if candidate.get('detail_url') else 'no'}"
        )


def print_results(before: dict[int, dict], after: dict[int, dict], results: list[dict]) -> None:
    """실행 결과와 before/after delta 출력"""
    counts = Counter(result["status"] for result in results)

    print("\nPhase 2 smoke test 결과 요약:")
    for status, count in sorted(counts.items()):
        print(f"- {status}: {count}")

    print("\n회사별 before/after:")
    for result in results:
        company_id = result["company_id"]
        before_row = before.get(company_id, {})
        after_row = after.get(company_id, {})
        print(
            f"- {result['company_name']} (id={company_id}) "
            f"status={result['status']} "
            f"cached_before={'yes' if before_row.get('company_page_url') else 'no'} "
            f"cached_after={'yes' if after_row.get('company_page_url') else 'no'} "
            f"details_after={'yes' if after_row.get('company_size') else 'no'}"
        )
        if result.get("company_page_final_url"):
            print(f"  final_url={result['company_page_final_url']}")
        if result.get("company_page_title"):
            print(f"  title={result['company_page_title']}")
        if result.get("company_page_wait_timed_out") is not None:
            print(
                "  wait_timed_out="
                + ("yes" if result["company_page_wait_timed_out"] else "no")
            )
        if result.get("company_page_diagnostic_html_path"):
            print(f"  diagnostic_html={result['company_page_diagnostic_html_path']}")
        if result.get("company_page_diagnostic_meta_path"):
            print(f"  diagnostic_meta={result['company_page_diagnostic_meta_path']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit <= 0:
        print("❌ --limit는 1 이상의 정수여야 합니다.")
        return 1

    config = Config()
    config.HEADLESS = args.headless == "true"

    db = DatabaseManager(config)
    db.create_tables()

    candidates = get_smoke_test_candidates(
        db,
        limit=args.limit,
        company_id=args.company_id,
    )
    if not candidates:
        if args.company_id is not None:
            print(f"회사 ID {args.company_id}에 대한 Phase 2 대상이 없습니다.")
            return 1
        print("선택 가능한 Phase 2 대상이 없습니다.")
        return 0

    company_ids = [candidate["id"] for candidate in candidates]
    before = get_company_snapshots(db, company_ids)

    print_candidates(candidates)
    results = run_phase2_for_companies(config, db, candidates)
    after = get_company_snapshots(db, company_ids)
    print_results(before, after, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
