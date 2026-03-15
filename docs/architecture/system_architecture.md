# 잡코리아 채용공고 크롤링 시스템 아키텍처

> 기준 시점: 현재 워킹트리 기준
> 이 문서는 실제 파일과 현재 구현을 기준으로 정리한 source of truth입니다.

문서 분류 기준 요약:

- 현재 구조의 상세 source of truth는 `architecture/`
- 현재 상태와 handoff는 `status/`
- 현재 active 계획은 `plans/`
- 실행/운영 절차는 `guides/`
- 최근 완료 보고는 `reports/`
- 과거 기록은 `archive/`

세부 저장 규칙은 `docs/README.md`를 기준으로 봅니다.

## 1. 개요

이 프로젝트는 잡코리아 검색 결과와 JD/회사 페이지를 2단계 구조로 수집해 PostgreSQL에 적재하는 Python 기반 크롤링 파이프라인입니다.

- **Phase 1**: 검색 결과 목록에서 공고 카드 정보를 수집
- **Phase 2**: 상세 정보가 비어 있는 회사를 대상으로 JD 상세를 거쳐 회사 페이지 정보를 보강
- **키워드 단위 추적**: 각 실행은 `crawl_runs`에 기록

현재 확인된 제한:

- Phase 1 검색 결과 파서는 `JobList` 우선 + 전역 `CardJob` 폴백 구조로 보정되었지만, 폴백 경로는 여전히 남아 있습니다.
- Phase 2는 `company_page_url` 저장/재사용 경로까지 반영됐지만, 기존 데이터 중 URL이 비어 있는 회사는 첫 보강 시 한 번은 JD를 열어야 합니다.
- 저장된 `company_page_url`가 실패할 때 JD로 재해결하는 fallback은 아직 없습니다.
- JD/회사 페이지 selector 검증은 아직 소수 fixture 중심입니다.
- 2026-03-15 timeout diagnosis 기준, historical timeout artifact의 원인은 `Co_Read` 요청이 `Super` 회사 페이지로 리다이렉트되는 레이아웃 변형 경로였고, 현재 live rerun에서는 같은 URL이 정상 로드됐습니다.

## 2. 현재 구현 흐름

```text
Phase 1
JobKorea Search
  -> JobKoreaCrawler.crawl_list_pages(keyword)
  -> parse_job_cards(html)
  -> validate_job_posting(job)
  -> DatabaseManager.get_or_create_company(...)
  -> DatabaseManager.insert_job_posting(...)

Phase 2
DatabaseManager.get_companies_without_details()
  -> if companies.company_page_url exists:
       reuse company_page_url
     else:
       JobKoreaCrawler.crawl_job_detail_page(job_detail_url)
       -> parse_company_page_url_from_job_detail(job_detail_html)
       -> DatabaseManager.update_company_page_url(company_id, company_page_url)
  -> JobKoreaCrawler.crawl_company_page(company_page_url)
  -> parse_company_detail(company_html)
  -> validate_company_details(details)
  -> DatabaseManager.update_company_details(...)
```

위 Phase 2 흐름은 현재 구현 경로를 있는 그대로 적은 것입니다. 여기서 `detail_url`의 의미는 여전히 JD 상세 URL이고, `companies.company_page_url`는 회사 상세 페이지 URL 캐시입니다.

## 2.1 현재 확인된 구조 리스크

- Phase 1 파서 스코프: `parse_job_cards()`는 `JobList` 컨테이너를 우선 사용하지만, 컨테이너를 찾지 못하면 전역 `CardJob`로 폴백합니다.
- Phase 1 수집 정확성: 현재 fixture 기준 전역 `CardJob`는 `27`개, 메인 `JobList` 내부 카드는 `20`개입니다. live 구조가 크게 바뀌면 폴백 경로에서 다시 과수집될 수 있습니다.
- Phase 2 시작 URL: 저장된 `companies.company_page_url`가 있으면 이를 우선 사용하고, 없을 때만 최신 `job_postings.detail_url`에서 출발합니다.
- Phase 2 URL 캐시: 새로 찾은 회사 페이지 URL은 `companies.company_page_url`에 저장해 이후 실행에서 재사용합니다.
- Phase 2 진단 정보: 회사 페이지 로더는 최근 요청의 `final_url`, `title`, `wait_locator`, timeout 여부, diagnostic HTML/meta 경로를 보관하고 smoke/test 경로에서 이를 출력할 수 있습니다.
- 보조 분석 스크립트: `scripts/analyze_detail_page.py`는 `--mode jd|company`로 현재 흐름에 맞춰 JD 분석과 회사 페이지 분석을 분리합니다.

실제 오케스트레이션은 `main.py`, 크롤링은 `crawler.py`, 파싱은 `parser.py`, 정제는 `validators.py`, DB 처리는 `database.py` 가 담당합니다.

## 3. 모듈 구조

| 파일 | 역할 | 상태 관리 |
|------|------|-----------|
| `config.py` | 환경변수 로드, 로깅 설정, 기본값 검증 | 일부 상태 보유 |
| `crawler.py` | Selenium 드라이버 생성, 목록/상세 페이지 수집, 딜레이/쿨다운 | 상태 보유 |
| `parser.py` | HTML에서 공고/회사 정보 추출 | 상태 없음 |
| `validators.py` | 저장 전 데이터 검증 및 정제 | 상태 없음 |
| `database.py` | 테이블 생성, CRUD, 실행 이력 기록 | 상태 보유 |
| `main.py` | Phase 1/2 순서 제어, 요약 출력 | 상태 없음 |

설계 원칙은 여전히 `관리할 상태가 있으면 클래스, 없으면 함수`입니다.

## 4. 수집 조건

현재 목록 페이지 URL 패턴은 다음과 같습니다.

```text
https://www.jobkorea.co.kr/Search/?stext={keyword}&FeatureCode=WRK&Page_No={page}&careerType=1,4&tabType=recruit
```

현재 코드에서 고정된 검색 조건:

- `stext={keyword}`: 키워드별 검색
- `FeatureCode=WRK`
- `Page_No={page}`
- `careerType=1,4`
- `tabType=recruit`

현재 코드에 **지역 필터는 없습니다**. 과거 문서에 있던 `서울, 인천` 설명은 현재 구현과 일치하지 않습니다.

## 5. 기술 스택

| 구분 | 기술 | 실제 사용 위치 |
|------|------|----------------|
| 크롤링 | Selenium, webdriver-manager | `crawler.py`, `scripts/manual_test_crawler.py` |
| 봇 탐지 대응 | selenium-stealth | `crawler.py`, `scripts/manual_test_crawler.py` |
| 파싱 | BeautifulSoup4 | `parser.py`, `scripts/analyze_detail_page.py` |
| DB | PostgreSQL, SQLAlchemy, psycopg2-binary | `database.py`, DB 테스트 |
| 환경변수 | python-dotenv | `config.py`, `scripts/manual_test_crawler.py` |
| 테스트 | pytest | `tests/` |

`requirements.txt`에 `pandas`가 들어 있지만, 현재 메인 실행 경로에서는 사용하지 않습니다.

## 6. 데이터베이스 스키마

### 6.1 `companies`

```sql
CREATE TABLE IF NOT EXISTS companies (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL UNIQUE,
    company_size        VARCHAR(50),
    industry            VARCHAR(200),
    employee_count      VARCHAR(50),
    establishment_year  VARCHAR(20),
    company_page_url    TEXT,
    homepage_url        TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

주요 필드 의미:

- `name`: 회사명, 유니크
- `industry`: 목록 카드 기반 업종
- `company_page_url`: Phase 2가 재사용하는 회사 상세 페이지 URL 캐시
- `company_size`, `employee_count`, `establishment_year`, `homepage_url`: 상세 페이지 기반 보강 필드

### 6.2 `job_postings`

```sql
CREATE TABLE IF NOT EXISTS job_postings (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER REFERENCES companies(id),
    title           VARCHAR(500) NOT NULL,
    location        VARCHAR(100),
    job_category    VARCHAR(300),
    salary          VARCHAR(100),
    experience      VARCHAR(100),
    benefits        TEXT,
    badge           VARCHAR(100),
    apply_type      VARCHAR(50),
    posted_date     VARCHAR(50),
    deadline        VARCHAR(50),
    detail_url      TEXT UNIQUE,
    search_keyword  VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'active',
    first_seen_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crawled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

현재 구현상 특징:

- `detail_url` 기준으로 기존 공고를 식별
- `search_keyword` 로 어떤 키워드 실행에서 처음 수집했는지 저장
- `status`, `first_seen_at`, `last_seen_at` 로 공고 lifecycle 추적

### 6.3 `crawl_runs`

```sql
CREATE TABLE IF NOT EXISTS crawl_runs (
    id              SERIAL PRIMARY KEY,
    keyword         VARCHAR(100) NOT NULL,
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    pages_crawled   INTEGER DEFAULT 0,
    jobs_collected  INTEGER DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'running'
);
```

이 테이블은 키워드 단위 실행 상태를 저장합니다.

### 6.4 `job_posting_history`

```sql
CREATE TABLE IF NOT EXISTS job_posting_history (
    id              SERIAL PRIMARY KEY,
    job_posting_id  INTEGER REFERENCES job_postings(id) ON DELETE CASCADE,
    field_name      VARCHAR(50) NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

이 테이블은 공고 주요 필드의 변경 이력을 저장합니다.

### 6.5 인덱스

현재 코드에서 생성하는 인덱스:

- `idx_company_name`
- `idx_company_size`
- `idx_job_company_id`
- `idx_job_location`
- `idx_job_experience`
- `idx_job_deadline`
- `idx_job_keyword`
- `idx_job_status`
- `idx_job_last_seen`
- `idx_history_job_posting_id`

## 7. 설정

현재 코드 기본값은 `config.py` 기준입니다.

| 변수 | 기본값 | 비고 |
|------|--------|------|
| `DB_HOST` | `localhost` | |
| `DB_PORT` | `5433` | 코드 기본값 |
| `DB_NAME` | `jobkorea` | |
| `DB_USER` | `postgres` | |
| `DB_PASSWORD` | `jobkorea123` | 코드 기본값 |
| `SEARCH_KEYWORDS` | `데이터분석가` | 메인 경로 |
| `SEARCH_KEYWORD` | `데이터분석가` | 하위 호환성 |
| `MAX_PAGES` | `5` | |
| `REQUEST_DELAY_MIN` | `2` | |
| `REQUEST_DELAY_MAX` | `5` | |
| `HEADLESS` | `true` | |
| `RETRY_ATTEMPTS` | `3` | 페이지 재시도 횟수 |
| `CONSECUTIVE_DUPLICATE_THRESHOLD` | `20` | 증분 종료 기준 |
| `STALE_AFTER_DAYS` | `7` | stale 전환 기준 |
| `LOG_LEVEL` | `INFO` | |
| `LOG_DIR` | `log` | |

`.env.example`도 현재 기준으로 맞춰 두었지만, 실제 로컬 PostgreSQL 포트가 `5432`면 `.env`에서 덮어쓰면 됩니다.

## 8. 보조 스크립트

- `scripts/analyze_detail_page.py`: `--mode jd|company`로 JD 상세 구조와 저장된 회사 페이지 구조를 각각 분석하는 보조 스크립트
- `scripts/phase2_smoke_test.py`: Phase 2 대상 일부만 선택해 `company_page_url` 재사용과 회사 페이지 로딩을 live 기준으로 검증하는 스크립트. `--company-id`로 특정 회사를 강제 재현할 수 있습니다.
- `scripts/run_crawler.sh`: cron/systemd 등 스케줄러에서 `main.py` 실행
- `scripts/manual_test_crawler.py`: 초기에 만든 수동 1페이지 CSV 점검 스크립트

`scripts/manual_test_crawler.py`는 자동 테스트가 아니라 레거시 수동 도구입니다.

## 9. 테스트 상태

현재 테스트 구성:

- `tests/test_analyze_detail_page.py`
- `tests/test_config.py`
- `tests/test_parser.py`
- `tests/test_main.py`
- `tests/test_phase2_smoke_test.py`
- `tests/test_validators.py`
- `tests/test_database.py`

실행 결과 기준:

- Phase 1/2 parser+main+script 검증: `31 passed`
- Phase 2 smoke path 검증: `29 passed`
- 전체 테스트: `104 passed`

## 10. 현재 구현상 참고사항

- `main.py`는 사용자 진행 상황을 콘솔에 출력하고, 내부 모듈은 로깅 중심으로 동작합니다.
- `job_postings`는 신규/변경/재확인 상태를 구분해 집계하고, `crawl_runs.jobs_collected`는 신규 insert 기준으로 기록합니다.
- `get_companies_without_details()`는 회사당 저장된 `company_page_url`와 최신 `detail_url` 1건을 함께 선택합니다.
- 현재 `job_postings.detail_url`의 의미는 JD 상세 URL입니다.
- 현재 Phase 2의 메인 경로는 `저장된 company_page_url 재사용 -> 회사 페이지 방문` 또는 `JD 상세 -> 회사 페이지 링크 추출/저장 -> 회사 페이지 방문`입니다.
- `crawl_company_page()` 실패 시 `log/page_diagnostics/` 아래에 HTML/meta artifact를 남기고, 최근 결과는 `run_phase2_for_companies()`와 smoke script 출력에 전달됩니다.
- 일정 기간 재발견되지 않은 공고는 `stale` 상태로 전환됩니다.

현재 기준으로는 Phase 2 URL 재사용 경로의 live 검증, fixture 확대, fallback 보강 판단이 우선 작업입니다. 이 문서는 "구현되어 있는 경로"를 설명하며, 남은 한계는 위 제한사항을 따릅니다.

이 문서는 위 참고사항을 포함해, 현재 코드가 실제로 어떻게 동작하는지를 설명하는 데 목적이 있습니다.
