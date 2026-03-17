"""
main.py - 잡코리아 크롤링 실행 진입점
=========================================
사용법:
    python main.py

전체 흐름:
    Phase 1: 목록 크롤링 (다중 키워드 지원)
        1. PostgreSQL 테이블 생성
        2. 각 키워드별 검색 결과 크롤링
        3. HTML 파싱 → 데이터 추출
        4. DB 저장 (companies + job_postings)

    Phase 2: 상세 크롤링
        5. 상세 정보가 없는 회사 조회
        6. 상세 페이지 크롤링
        7. 회사 정보 업데이트 (company_size, employee_count 등)

    결과 요약 출력
"""

import logging
from collections import Counter
from datetime import datetime

from config import Config, setup_logging
from crawler import JobKoreaCrawler
from parser import (
    filter_jobs_by_search_preferences,
    parse_company_detail,
    parse_company_page_url_from_job_detail,
    parse_job_cards,
)
from database import DatabaseManager
from validators import validate_job_posting, validate_company_details, is_ad_posting

logger = logging.getLogger(__name__)


def _print_section(title: str):
    """사용자용 콘솔 섹션 헤더 출력"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def _init_phase1_stats() -> dict:
    """Phase 1 통계 초기화"""
    return {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "failed": 0,
        "pages_crawled": 0,
        "duplicate_threshold_hit": False,
    }


def _resolve_phase2_company_page_url(
    company: dict,
    crawler: JobKoreaCrawler,
    db: DatabaseManager,
) -> tuple[str | None, str | None]:
    """저장된 company_page_url 재사용 또는 JD에서 회사 페이지 URL 추출"""
    company_id = company["id"]
    company_name = company["name"]
    stored_company_page_url = (company.get("company_page_url") or "").strip()
    job_detail_url = (company.get("detail_url") or "").strip()

    if stored_company_page_url:
        logger.info(f"저장된 회사 페이지 URL 재사용: {company_name}")
        print("   저장된 회사 페이지 URL 재사용")
        return stored_company_page_url, job_detail_url or None

    if not job_detail_url:
        logger.info(f"회사 페이지 URL과 JD URL이 모두 없어 스킵: {company_name}")
        print("   회사 페이지 URL과 JD URL이 없어 스킵")
        return None, None

    job_detail_html = crawler.crawl_job_detail_page(job_detail_url)
    if not job_detail_html:
        logger.info(f"JD 상세 페이지 로드 실패: {company_name}")
        print("   JD 상세 페이지 로드 실패")
        return None, job_detail_url

    company_page_url = parse_company_page_url_from_job_detail(job_detail_html)
    if not company_page_url:
        logger.info(f"회사 페이지 링크 추출 실패: {company_name}")
        print("   회사 페이지 링크 추출 실패")
        return None, job_detail_url

    if db.update_company_page_url(company_id, company_page_url):
        logger.info(f"회사 페이지 URL 저장: {company_name} -> {company_page_url}")

    print("   JD에서 회사 페이지 URL 확보")
    return company_page_url, job_detail_url


def _attach_company_page_diagnostics(result: dict, crawler: JobKoreaCrawler) -> None:
    """최근 회사 페이지 로드 진단 정보를 result에 복사한다."""
    diagnostics = crawler.get_last_page_diagnostics() or {}
    result["company_page_final_url"] = diagnostics.get("final_url")
    result["company_page_title"] = diagnostics.get("title")
    result["company_page_wait_locator"] = diagnostics.get("wait_locator")
    result["company_page_wait_timed_out"] = diagnostics.get("wait_timed_out")
    result["company_page_error"] = diagnostics.get("error")
    result["company_page_diagnostic_html_path"] = diagnostics.get("html_path")
    result["company_page_diagnostic_meta_path"] = diagnostics.get("meta_path")


def run_phase1_for_keyword(keyword: str, config: Config, db: DatabaseManager) -> dict:
    """
    Phase 1: 특정 키워드에 대한 목록 페이지 크롤링 및 DB 저장

    Args:
        keyword: 검색 키워드
        config: 설정 객체
        db: 데이터베이스 매니저

    Returns:
        dict: 실행 통계
    """
    logger.info(f"Phase 1 시작 - 키워드: {keyword}")
    run_id = db.start_crawl_run(keyword)
    stats = _init_phase1_stats()
    duplicate_streak = 0

    try:
        with JobKoreaCrawler(config) as crawler:
            with db.connect() as conn:
                for page_num, html in crawler.iter_list_pages(keyword):
                    stats["pages_crawled"] = page_num
                    logger.debug(f"페이지 {page_num} 파싱 중...")
                    jobs = parse_job_cards(html)
                    filtered_jobs = filter_jobs_by_search_preferences(
                        jobs,
                        allowed_locations=getattr(config, "SEARCH_LOCATIONS", []),
                        allowed_experience_types=getattr(config, "SEARCH_EXPERIENCE_TYPES", []),
                        allowed_employment_types=getattr(config, "SEARCH_EMPLOYMENT_TYPES", []),
                    )
                    if len(filtered_jobs) != len(jobs):
                        logger.info(
                            "검색 조건 필터 적용 - 키워드: %s, 페이지: %s, 원본: %s건, 통과: %s건",
                            keyword,
                            page_num,
                            len(jobs),
                            len(filtered_jobs),
                        )
                    jobs = filtered_jobs

                    for job in jobs:
                        company_name = job.get("company", "").strip()
                        if not company_name:
                            stats["skipped"] += 1
                            duplicate_streak = 0
                            continue

                        # 광고성 공고 필터링
                        title = job.get("title", "")
                        if is_ad_posting(title):
                            stats["skipped"] += 1
                            continue

                        try:
                            validated_job = validate_job_posting(job)
                            company_id = db.get_or_create_company(
                                conn,
                                validated_job.get("company"),
                                industry=validated_job.get("industry", "")
                            )

                            result = db.insert_job_posting(
                                conn,
                                company_id,
                                validated_job,
                                keyword,
                            )
                            action = result["action"]
                            stats[action] += 1

                            detail_url = (validated_job.get("detail_url") or "").strip()
                            if detail_url:
                                if action == "inserted":
                                    duplicate_streak = 0
                                elif action in {"updated", "unchanged"}:
                                    duplicate_streak += 1
                                else:
                                    duplicate_streak = 0
                            else:
                                duplicate_streak = 0

                            if duplicate_streak >= config.CONSECUTIVE_DUPLICATE_THRESHOLD:
                                stats["duplicate_threshold_hit"] = True
                                logger.info(
                                    f"증분 크롤링 조기 종료 - 키워드: {keyword}, "
                                    f"연속 기존 공고 {duplicate_streak}건"
                                )
                                break

                        except Exception as e:
                            logger.error(f"저장 실패 ({company_name}): {e}")
                            stats["failed"] += 1
                            duplicate_streak = 0

                    conn.commit()

                    if stats["duplicate_threshold_hit"]:
                        break

        db.complete_crawl_run(
            run_id,
            stats["pages_crawled"],
            stats["inserted"],
            "completed",
        )
        logger.info(
            f"Phase 1 완료 - 키워드: {keyword}, "
            f"신규: {stats['inserted']}건, 변경: {stats['updated']}건, "
            f"재확인: {stats['unchanged']}건, 건너뜀: {stats['skipped']}건, 실패: {stats['failed']}건"
        )

    except Exception as e:
        logger.error(f"Phase 1 실패 - 키워드: {keyword}, 에러: {e}", exc_info=True)
        db.complete_crawl_run(
            run_id,
            stats["pages_crawled"],
            stats["inserted"],
            "failed",
        )

    return stats


def run_phase1(config: Config, db: DatabaseManager) -> dict:
    """
    Phase 1: 모든 키워드에 대한 목록 크롤링

    Returns:
        dict: 집계 통계
    """
    _print_section("Phase 1: 목록 크롤링")

    keywords = config.SEARCH_KEYWORDS
    logger.info(f"크롤링 대상 키워드: {keywords}")

    totals = _init_phase1_stats()
    for i, keyword in enumerate(keywords, 1):
        keyword = keyword.strip()
        if not keyword:
            continue

        print(f"\n[{i}/{len(keywords)}] 키워드: {keyword}")
        stats = run_phase1_for_keyword(keyword, config, db)
        print(
            f"   신규 {stats['inserted']}건, 변경 {stats['updated']}건, "
            f"재확인 {stats['unchanged']}건, 건너뜀 {stats['skipped']}건, 실패 {stats['failed']}건"
        )
        if stats["duplicate_threshold_hit"]:
            print(
                f"   증분 종료: 연속 기존 공고 "
                f"{config.CONSECUTIVE_DUPLICATE_THRESHOLD}건 도달"
            )

        for key in ("inserted", "updated", "unchanged", "skipped", "failed"):
            totals[key] += stats[key]
        totals["pages_crawled"] += stats["pages_crawled"]

    stale_marked = db.mark_stale_job_postings(config.STALE_AFTER_DAYS)
    totals["stale_marked"] = stale_marked

    print(
        f"\nPhase 1 전체 완료: 신규 {totals['inserted']}건, 변경 {totals['updated']}건, "
        f"재확인 {totals['unchanged']}건, 건너뜀 {totals['skipped']}건, 실패 {totals['failed']}건"
    )
    print(f"stale 처리: {stale_marked}건")
    return totals


def run_phase2_for_companies(
    config: Config,
    db: DatabaseManager,
    companies: list[dict],
) -> list[dict]:
    """선택된 회사 목록에 대해서만 Phase 2 상세 보강을 수행한다."""
    total = len(companies)

    if total == 0:
        logger.info("선택된 Phase 2 대상이 없습니다")
        print("\n선택된 Phase 2 대상이 없습니다.")
        return []

    logger.info(f"상세 정보 수집 대상: {total}개 회사")
    print(f"\n상세 정보가 필요한 회사: {total}개")

    results: list[dict] = []

    with JobKoreaCrawler(config) as crawler:
        for i, company in enumerate(companies, 1):
            company_id = company["id"]
            company_name = company["name"]
            used_cached_company_page_url = bool((company.get("company_page_url") or "").strip())

            logger.debug(f"[{i}/{total}] {company_name} 크롤링 중...")
            print(f"\n[{i}/{total}] {company_name}")

            result = {
                "company_id": company_id,
                "company_name": company_name,
                "used_cached_company_page_url": used_cached_company_page_url,
                "company_page_url": None,
                "job_detail_url": (company.get("detail_url") or "").strip() or None,
                "status": "unknown",
                "updated": False,
                "details": None,
                "company_page_final_url": None,
                "company_page_title": None,
                "company_page_wait_locator": None,
                "company_page_wait_timed_out": None,
                "company_page_error": None,
                "company_page_diagnostic_html_path": None,
                "company_page_diagnostic_meta_path": None,
            }

            try:
                company_page_url, job_detail_url = _resolve_phase2_company_page_url(
                    company,
                    crawler,
                    db,
                )
                result["company_page_url"] = company_page_url
                result["job_detail_url"] = job_detail_url

                if not company_page_url:
                    result["status"] = "skipped_missing_company_page_url"
                    results.append(result)
                    continue

                # 회사 페이지 방문
                company_html = crawler.crawl_company_page(
                    company_page_url,
                    referer=job_detail_url,
                )
                _attach_company_page_diagnostics(result, crawler)
                if (
                    result["company_page_final_url"]
                    and result["company_page_final_url"] != company_page_url
                ):
                    logger.info(
                        "회사 페이지 리다이렉트 감지: requested=%s final=%s title=%s",
                        company_page_url,
                        result["company_page_final_url"],
                        result["company_page_title"] or "<empty>",
                    )
                if not company_html:
                    logger.info(f"회사 페이지 로드 실패: {company_name}")
                    print("   회사 페이지 로드 실패")
                    result["status"] = "company_page_load_failed"
                    results.append(result)
                    continue

                # 회사 페이지 HTML 파싱
                details = parse_company_detail(company_html)

                # 데이터 검증 및 정제
                validated_details = validate_company_details(details)
                result["details"] = validated_details

                # DB 업데이트
                if any(validated_details.values()):
                    db.update_company_details(company_id, validated_details)
                    logger.info(f"회사 정보 업데이트: {company_name} - {validated_details}")
                    print(f"   업데이트: {validated_details}")
                    result["status"] = "updated"
                    result["updated"] = True
                else:
                    logger.info(f"추출된 정보 없음: {company_name}")
                    print("   추출된 정보 없음")
                    result["status"] = "no_details_extracted"

                results.append(result)

                # 다음 요청 전 딜레이
                if i < total:
                    crawler._random_delay()

            except Exception as e:
                logger.error(f"상세 크롤링 실패: {company_name} - {e}")
                result["status"] = "exception"
                result["error"] = str(e)
                results.append(result)

    counts = Counter(result["status"] for result in results)
    logger.info(
        "Phase 2 상세 처리 결과 - "
        + ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))
    )
    return results


def run_phase2(
    config: Config,
    db: DatabaseManager,
    companies: list[dict] | None = None,
) -> int:
    """
    Phase 2: 상세 페이지 크롤링 및 회사 정보 업데이트

    Returns:
        int: 업데이트된 회사 수
    """
    _print_section("Phase 2: 상세 크롤링")

    if companies is None:
        companies = db.get_companies_without_details()
    total = len(companies)

    if total == 0:
        logger.info("모든 회사의 상세 정보가 이미 수집되었습니다")
        print("\n모든 회사의 상세 정보가 이미 수집되었습니다.")
        return 0

    results = run_phase2_for_companies(config, db, companies)
    updated_count = sum(1 for result in results if result["updated"])
    logger.info(f"Phase 2 완료: {updated_count}/{total}개 회사 업데이트")
    print(f"\nPhase 2 완료: {updated_count}/{total}개 회사 업데이트")
    return updated_count


def print_summary(db: DatabaseManager):
    """결과 요약 출력"""
    _print_section("크롤링 결과 요약")

    summary = db.get_summary()
    print(f"  등록된 회사 수: {summary['company_count']}개")
    print(f"  등록된 공고 수: {summary['job_count']}건")
    print(f"  상세 정보 수집: {summary['companies_with_details']}개")
    print(f"  활성 공고 수: {summary['active_jobs']}건")
    print(f"  stale 공고 수: {summary['stale_jobs']}건")
    print(f"  공고 이력 수: {summary['history_count']}건")

    logger.info(
        f"최종 통계 - 회사: {summary['company_count']}, 공고: {summary['job_count']}, "
        f"상세: {summary['companies_with_details']}, 활성: {summary['active_jobs']}, "
        f"stale: {summary['stale_jobs']}, 이력: {summary['history_count']}"
    )

    # 최근 공고 미리보기
    print("\n최근 공고 5건:")
    recent_jobs = db.get_recent_jobs(5)
    for i, job in enumerate(recent_jobs, 1):
        print(
            f"  [{i}] {job['company']} - {job['title']} "
            f"({job['location']}, {job['experience']}, status={job['status']})"
        )


def main():
    # 설정 로드
    config = Config()

    # 로깅 시스템 초기화
    setup_logging(config.LOG_LEVEL, config.LOG_DIR)

    _print_section("잡코리아 크롤링 시작")

    # 설정 검증
    warnings = config.validate()
    for warning in warnings:
        logger.warning(f"설정 경고: {warning}")

    # 설정 출력
    print(f"검색 키워드: {', '.join(config.SEARCH_KEYWORDS)}")
    print(f"최대 페이지: {config.MAX_PAGES}")
    print(f"Headless 모드: {config.HEADLESS}")
    print(f"재시도 횟수: {config.RETRY_ATTEMPTS}")
    print(f"증분 종료 기준: 연속 기존 공고 {config.CONSECUTIVE_DUPLICATE_THRESHOLD}건")
    print(f"stale 전환 기준: {config.STALE_AFTER_DAYS}일")
    print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    logger.info("=" * 40)
    logger.info("크롤링 시작")
    logger.info(f"키워드: {config.SEARCH_KEYWORDS}")
    logger.info(f"최대 페이지: {config.MAX_PAGES}")
    logger.info("=" * 40)

    try:
        # DB 준비
        print("\n데이터베이스 준비 중...")
        db = DatabaseManager(config)
        db.create_tables()

        # Phase 1: 목록 크롤링
        run_phase1(config, db)

        # Phase 2: 상세 크롤링
        run_phase2(config, db)

        # 결과 요약
        print_summary(db)

        logger.info("크롤링 정상 종료")

    except Exception as e:
        logger.critical(f"크롤링 실패: {e}", exc_info=True)
        raise

    print(f"\n종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
