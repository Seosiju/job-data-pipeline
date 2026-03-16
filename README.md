# JobKorea Crawler

잡코리아 검색 결과와 JD/회사 페이지를 수집해 PostgreSQL에 저장하는 2단계 구조의 크롤링 파이프라인입니다. Phase 1 검색 결과 파서 감사와 Phase 2 회사 페이지 전환의 메인 경로는 구현되었고, 현재는 후속 안정화가 우선 과제입니다.

## 현재 상태

- Phase 1: 목록 페이지에서 공고 카드 수집 후 `companies`, `job_postings` 저장
- Phase 1 정확성 감사 완료: `JobList -> CardJob` 스코프 기반 파서와 fixture 회귀 테스트 확보
- Phase 2 메인 경로 구현 완료: `JD 상세 -> 회사 페이지 링크 추출 -> 회사 페이지 방문 -> 회사 정보 업데이트`
- Phase 2 후속 안정화 반영: `companies.company_page_url` 저장/재사용으로 저장된 회사 URL이 있으면 JD 재방문을 건너뜁니다.
- 보조 스크립트 정리 완료: `scripts/analyze_detail_page.py`는 `--mode jd|company`로 현재 Phase 2 흐름에 맞게 동작합니다.
- 다중 키워드 실행 지원
- 증분 크롤링 지원
- 공고 lifecycle과 변경 이력 추적 지원
- 관련 회귀 테스트 보강 완료

## 디렉터리 구조

```text
jobkorea/
├── main.py
├── config.py
├── crawler.py
├── parser.py
├── validators.py
├── database.py
├── requirements.txt
├── scripts/
│   ├── analyze_detail_page.py
│   ├── manual_test_crawler.py
│   ├── phase2_smoke_test.py
│   └── run_crawler.sh
├── tests/
│   ├── fixtures/
│   ├── test_analyze_detail_page.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_main.py
│   ├── test_parser.py
│   ├── test_phase2_smoke_test.py
│   └── test_validators.py
└── docs/
    ├── archive/
    ├── status/
    ├── architecture/
    ├── guides/
    ├── plans/
    └── reports/
```

구조 원칙은 단순합니다.

- 루트: 실제 실행 경로와 핵심 모듈
- `scripts/`: 수동 점검, 보조 분석, 스케줄링 스크립트
- `tests/`: 자동 테스트
- `docs/`: 상태, 설계, runbook, active 계획, 최근 결과
- `docs/archive/`: 과거 계획/결과/리팩토링 기록

## 문서 분류 규칙

`docs/` 저장 규칙의 기준 문서는 [docs/README.md](/Users/snu.sim/git/jobkorea/docs/README.md)입니다.

- `status/`: 지금 상태와 다음 세션 handoff
- `architecture/`: 현재 구조, 스키마, 설계 원칙
- `plans/`: 현재 active plan만 유지
- `guides/`: 실행법, 설정법, 운영 절차
- `reports/`: 최근 완료 결과 중 현재도 참고 가치가 높은 문서
- `archive/`: 과거 plan/report/refactoring/legacy guide

판단 기준은 간단합니다.

- 작업 전이면 `plans/`
- 작업 후 결과면 `reports/`
- 현재 구조의 상세 설명이면 `architecture/`
- 실행/운영 방법이면 `guides/`
- 과거 기록이면 `archive/`
- 지금 상태의 압축 요약이면 `status/`

## 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 준비

```bash
cp .env.example .env
```

기본 예시:

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=jobkorea
DB_USER=postgres
DB_PASSWORD=your_password_here

SEARCH_KEYWORDS=데이터분석가,사업기획,프로젝트매니저
SEARCH_LOCATIONS=서울,인천
SEARCH_EXPERIENCE_TYPES=신입,경력무관
SEARCH_EMPLOYMENT_TYPES=정규직,계약직,인턴
MAX_PAGES=5
REQUEST_DELAY_MIN=2
REQUEST_DELAY_MAX=5
HEADLESS=true
RETRY_ATTEMPTS=3
CONSECUTIVE_DUPLICATE_THRESHOLD=20
STALE_AFTER_DAYS=7
LOG_LEVEL=INFO
LOG_DIR=log
```

주의:

- 코드 기본 포트는 `5433`입니다.
- 로컬 PostgreSQL이 `5432`를 쓰면 `.env`에서 바꾸면 됩니다.
- 메인 경로는 `SEARCH_KEYWORDS`이고, `SEARCH_KEYWORD`는 하위 호환성용입니다.
- `SEARCH_LOCATIONS`, `SEARCH_EXPERIENCE_TYPES`, `SEARCH_EMPLOYMENT_TYPES`는 검색 결과 메인 `JobList` 카드와 hydration 메타데이터를 기준으로 **저장 전 필터**를 적용합니다.
- 현재 구현은 잡코리아 UI 필터를 Selenium으로 클릭하지 않고, fixture로 검증한 카드/metadata를 기준으로 로컬 필터링합니다.

### 3. 데이터베이스 준비

```bash
createdb jobkorea
```

테이블은 실행 시 자동 생성됩니다.

## 실행

전체 파이프라인 실행:

```bash
python main.py
```

Phase 2 소규모 live smoke test:

```bash
python scripts/phase2_smoke_test.py --limit 1
```

이 스크립트는 상세 정보가 비어 있는 회사 중 일부만 골라 실제 `company_page_url` 재사용/회사 페이지 로딩 경로를 검증합니다.

상세 페이지 구조 수동 분석:

```bash
python scripts/analyze_detail_page.py --mode jd
python scripts/analyze_detail_page.py --mode company
```

`--mode jd`는 JD 상세에서 회사 페이지 URL 추출 경로를 점검하고,
`--mode company`는 저장된 `company_page_url`를 직접 열어 회사 페이지 구조를 분석합니다.

레거시 1페이지 CSV 점검:

```bash
python scripts/manual_test_crawler.py
```

스케줄러용 실행 스크립트:

```bash
./scripts/run_crawler.sh
```

## 테스트

기본 실행:

```bash
pytest tests/ -q
```

현재 기준 결과:

- Phase 1 검색 필터/파서/메인 경로 검증: `41 passed`
- 전체 테스트: `113 passed`

실DB 통합 테스트를 별도 인스턴스에 붙이는 예시:

```bash
TEST_REAL_DB_HOST=localhost \
TEST_REAL_DB_PORT=55433 \
TEST_REAL_DB_NAME=jobkorea \
TEST_REAL_DB_USER=postgres \
TEST_REAL_DB_PASSWORD='' \
pytest tests/ -q
```

## 핵심 데이터 모델

### `companies`

- 회사 기본 정보
- `name` 유니크
- `company_page_url` 저장
- 상세 페이지에서 `company_size`, `employee_count`, `establishment_year`, `homepage_url` 보강

### `job_postings`

- 공고 본문 정보
- `detail_url` 기준 중복 식별
- `search_keyword` 저장
- `status`, `first_seen_at`, `last_seen_at`로 lifecycle 추적

### `crawl_runs`

- 키워드 단위 실행 이력 저장

### `job_posting_history`

- 주요 필드 변경 이력 저장

## 주요 문서

새 세션이나 처음 읽는 경우 추천 순서:

1. `README.md`
2. `docs/architecture/system_architecture.md`
3. `docs/plans/data_pipeline_service_roadmap.md`
4. `docs/status/current_status.md`
5. `docs/status/session_handoff.md`
6. `docs/reports/phase2_company_page_fix_review.md`
7. `docs/reports/phase2_followup_stabilization_report.md`

주요 문서:

- 현재 구조와 동작: `docs/architecture/system_architecture.md`
- 데이터 검증 동작 reference: `docs/architecture/data_validation_behavior.md`
- Phase 2 구현 리뷰: `docs/reports/phase2_company_page_fix_review.md`
- Phase 2 후속 안정화 보고: `docs/reports/phase2_followup_stabilization_report.md`
- Phase 2 live smoke validation: `docs/reports/phase2_live_smoke_validation_report.md`
- 중장기 확장 로드맵: `docs/plans/data_pipeline_service_roadmap.md`
- 현재 상태 요약: `docs/status/current_status.md`
- 최근 세션 handoff: `docs/status/session_handoff.md`
- 문서 분류 규칙: `docs/README.md`
- 작업 규칙: `AGENTS.md`
- 운영/설정 가이드: `docs/guides/`
- 완료 보고서: `docs/reports/`
- 과거 기록: `docs/archive/`

`docs/reports/` 문서는 현재 source of truth가 아니라 historical snapshot으로 보는 것이 맞습니다.
