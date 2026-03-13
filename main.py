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
from datetime import datetime

from config import Config, setup_logging
from crawler import JobKoreaCrawler
from parser import parse_job_cards, parse_company_detail
from database import DatabaseManager
from validators import validate_job_posting, validate_company_details

logger = logging.getLogger(__name__)


def run_phase1_for_keyword(keyword: str, config: Config, db: DatabaseManager) -> int:
    """
    Phase 1: 특정 키워드에 대한 목록 페이지 크롤링 및 DB 저장

    Args:
        keyword: 검색 키워드
        config: 설정 객체
        db: 데이터베이스 매니저

    Returns:
        int: 저장된 공고 수
    """
    logger.info(f"Phase 1 시작 - 키워드: {keyword}")
    run_id = db.start_crawl_run(keyword)

    total_saved = 0
    total_skipped = 0
    pages_crawled = 0

    try:
        # 크롤링
        with JobKoreaCrawler(config) as crawler:
            html_pages = crawler.crawl_list_pages(keyword)
        pages_crawled = len(html_pages)

        # 파싱 + DB 저장
        with db.connect() as conn:
            for page_num, html in enumerate(html_pages, 1):
                logger.debug(f"페이지 {page_num} 파싱 중...")
                jobs = parse_job_cards(html)

                for job in jobs:
                    company_name = job.get("company", "")
                    if not company_name:
                        continue

                    try:
                        # 데이터 검증 및 정제
                        validated_job = validate_job_posting(job)

                        # 회사 등록/조회
                        company_id = db.get_or_create_company(
                            conn,
                            validated_job.get("company"),
                            industry=validated_job.get("industry", "")
                        )

                        # 공고 저장 (키워드 포함)
                        db.insert_job_posting(conn, company_id, validated_job, keyword)
                        total_saved += 1
                    except Exception as e:
                        logger.error(f"저장 실패 ({company_name}): {e}")
                        total_skipped += 1

                conn.commit()

        db.complete_crawl_run(run_id, pages_crawled, total_saved, "completed")
        logger.info(f"Phase 1 완료 - 키워드: {keyword}, 저장: {total_saved}건, 건너뜀: {total_skipped}건")

    except Exception as e:
        logger.error(f"Phase 1 실패 - 키워드: {keyword}, 에러: {e}", exc_info=True)
        db.complete_crawl_run(run_id, pages_crawled, total_saved, "failed")

    return total_saved


def run_phase1(config: Config, db: DatabaseManager) -> int:
    """
    Phase 1: 모든 키워드에 대한 목록 크롤링

    Returns:
        int: 총 저장된 공고 수
    """
    print("\n" + "=" * 60)
    print("Phase 1: 목록 크롤링")
    print("=" * 60)

    keywords = config.SEARCH_KEYWORDS
    logger.info(f"크롤링 대상 키워드: {keywords}")

    total_saved = 0
    for i, keyword in enumerate(keywords, 1):
        keyword = keyword.strip()
        if not keyword:
            continue

        print(f"\n[{i}/{len(keywords)}] 키워드: {keyword}")
        saved = run_phase1_for_keyword(keyword, config, db)
        total_saved += saved

    print(f"\nPhase 1 전체 완료: {total_saved}건 저장")
    return total_saved


def run_phase2(config: Config, db: DatabaseManager) -> int:
    """
    Phase 2: 상세 페이지 크롤링 및 회사 정보 업데이트

    Returns:
        int: 업데이트된 회사 수
    """
    print("\n" + "=" * 60)
    print("Phase 2: 상세 크롤링")
    print("=" * 60)

    companies = db.get_companies_without_details()
    total = len(companies)

    if total == 0:
        logger.info("모든 회사의 상세 정보가 이미 수집되었습니다")
        print("\n모든 회사의 상세 정보가 이미 수집되었습니다.")
        return 0

    logger.info(f"상세 정보 수집 대상: {total}개 회사")
    print(f"\n상세 정보가 필요한 회사: {total}개")

    updated_count = 0

    with JobKoreaCrawler(config) as crawler:
        for i, company in enumerate(companies, 1):
            company_id = company["id"]
            company_name = company["name"]
            detail_url = company["detail_url"]

            logger.debug(f"[{i}/{total}] {company_name} 크롤링 중...")
            print(f"\n[{i}/{total}] {company_name}")

            try:
                # 상세 페이지 크롤링
                html = crawler.crawl_detail_page(detail_url)

                if html:
                    # 파싱
                    details = parse_company_detail(html)

                    # 데이터 검증 및 정제
                    validated_details = validate_company_details(details)

                    # DB 업데이트
                    if any(validated_details.values()):
                        db.update_company_details(company_id, validated_details)
                        updated_count += 1
                        logger.info(f"회사 정보 업데이트: {company_name} - {validated_details}")
                        print(f"   업데이트: {validated_details}")
                    else:
                        logger.warning(f"추출된 정보 없음: {company_name}")
                        print("   추출된 정보 없음")

                # 다음 요청 전 딜레이
                if i < total:
                    crawler._random_delay()

            except Exception as e:
                logger.error(f"상세 크롤링 실패: {company_name} - {e}")
                print(f"   에러: {e}")

    logger.info(f"Phase 2 완료: {updated_count}/{total}개 회사 업데이트")
    print(f"\nPhase 2 완료: {updated_count}/{total}개 회사 업데이트")
    return updated_count


def print_summary(db: DatabaseManager):
    """결과 요약 출력"""
    print("\n" + "=" * 60)
    print("크롤링 결과 요약")
    print("=" * 60)

    summary = db.get_summary()
    print(f"  등록된 회사 수: {summary['company_count']}개")
    print(f"  등록된 공고 수: {summary['job_count']}건")
    print(f"  상세 정보 수집: {summary['companies_with_details']}개")

    logger.info(f"최종 통계 - 회사: {summary['company_count']}, 공고: {summary['job_count']}, 상세: {summary['companies_with_details']}")

    # 최근 공고 미리보기
    print("\n최근 공고 5건:")
    recent_jobs = db.get_recent_jobs(5)
    for i, job in enumerate(recent_jobs, 1):
        print(f"  [{i}] {job['company']} - {job['title']} ({job['location']}, {job['experience']})")


def main():
    # 설정 로드
    config = Config()

    # 로깅 시스템 초기화
    setup_logging(config.LOG_LEVEL, config.LOG_DIR)

    print("=" * 60)
    print("잡코리아 크롤링 시작")
    print("=" * 60)

    # 설정 검증
    warnings = config.validate()
    for warning in warnings:
        logger.warning(f"설정 경고: {warning}")
        print(f"  설정 경고: {warning}")

    # 설정 출력
    print(f"검색 키워드: {', '.join(config.SEARCH_KEYWORDS)}")
    print(f"최대 페이지: {config.MAX_PAGES}")
    print(f"Headless 모드: {config.HEADLESS}")
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
        print(f"\n크롤링 실패: {e}")
        raise

    print(f"\n종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
