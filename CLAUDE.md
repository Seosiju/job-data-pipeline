# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

잡코리아 채용공고를 2단계로 수집하는 Python 크롤러입니다.

- Phase 1: 검색 결과 목록 페이지를 수집해 `companies`, `job_postings`에 저장
- Phase 2: JD 상세를 거쳐 회사 페이지를 방문해 `companies`를 업데이트
- 키워드별 실행 기록은 `crawl_runs`에 저장
- 공고 lifecycle과 필드 변경 이력은 `job_posting_history`와 상태 컬럼으로 추적

## Session Bootstrap

새 세션에서 먼저 읽을 순서:

1. `README.md`
2. `docs/architecture/system_architecture.md`
3. `docs/plans/data_pipeline_service_roadmap.md`
4. `docs/status/current_status.md`
5. `docs/status/session_handoff.md`

## Documentation Taxonomy

문서 분류의 단일 기준은 `docs/README.md`입니다.

- `status/`: 지금 상태, 리스크, 다음 액션
- `architecture/`: 현재 구조, 설계 원칙, 상세 source of truth
- `plans/`: 착수 전 또는 진행 중 작업 계획
- `guides/`: 실행법과 운영 절차
- `refactoring/`: 구조 변경 기록
- `reports/`: 완료 결과 정리. 현재 상태 판단 기준으로 직접 쓰지 않음

판단이 애매하면:

1. 현재 구조의 상세 설명이면 `architecture/`
2. 현재 상태의 압축 요약이면 `status/`
3. 미래 작업 계획이면 `plans/`
4. 사용법이면 `guides/`
5. 완료 결과면 `reports/`

## Commands

```bash
# 전체 테스트
pytest tests/ -q

# 단일 테스트 파일
pytest tests/test_parser.py -v

# 특정 테스트
pytest tests/test_parser.py::TestParseJobCards::test_parse_multiple_cards -v

# 메인 크롤러 실행
python main.py

# 상세 페이지 구조 수동 분석
python scripts/analyze_detail_page.py

# 레거시 1페이지 수동 점검 스크립트
python scripts/manual_test_crawler.py

# 스케줄러용 실행 스크립트
./scripts/run_crawler.sh
```

## Architecture

### Modules

| Module | Pattern | Responsibility |
|--------|---------|----------------|
| `config.py` | class + helper function | 환경변수 로드, 로깅 초기화 |
| `crawler.py` | class | Selenium 드라이버 생명주기, 목록/상세 페이지 수집 |
| `parser.py` | functions | HTML에서 공고/회사 정보 추출 |
| `validators.py` | functions | 저장 전 데이터 검증 및 정제 |
| `database.py` | class | SQLAlchemy 연결, 테이블 생성, CRUD |
| `main.py` | functions | Phase 1/2 오케스트레이션, 요약 출력 |

설계 원칙: 관리할 상태가 있으면 클래스, 없으면 함수.

### Data Flow

```text
JobKorea Search
  -> JobKoreaCrawler.crawl_list_pages(keyword)
  -> parse_job_cards()
  -> validate_job_posting()
  -> DatabaseManager.get_or_create_company()
  -> DatabaseManager.insert_job_posting()

companies without details
  -> JobKoreaCrawler.crawl_job_detail_page()
  -> parse_company_page_url_from_job_detail()
  -> JobKoreaCrawler.crawl_company_page()
  -> parse_company_detail()
  -> validate_company_details()
  -> DatabaseManager.update_company_details()
```

### Database

- `companies`
- `job_postings`
- `crawl_runs`
- `job_posting_history`

`job_postings.detail_url` identifies existing postings, `search_keyword` stores the first collected keyword, and lifecycle fields track `active/stale` visibility.

## Environment Variables

Primary variables in `.env`:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `SEARCH_KEYWORDS` for the main multi-keyword path
- `SEARCH_KEYWORD` only for backward compatibility
- `MAX_PAGES`, `REQUEST_DELAY_MIN`, `REQUEST_DELAY_MAX`, `HEADLESS`
- `RETRY_ATTEMPTS`, `CONSECUTIVE_DUPLICATE_THRESHOLD`, `STALE_AFTER_DAYS`
- `LOG_LEVEL`, `LOG_DIR`

Code defaults currently use `DB_PORT=5433`.

## Current Notes

- `scripts/manual_test_crawler.py` is a manual script, not a pytest test module.
- `scripts/analyze_detail_page.py` is a helper script and is not yet fully aligned with the current Phase 2 flow.
- Phase 1 now tracks `inserted`, `updated`, `unchanged`, `skipped`, and `failed` separately.
- `main.py` owns operator-facing console output, while internal modules use logging-first behavior.
- DB tests are intentionally skipped when a local PostgreSQL instance is unavailable.
