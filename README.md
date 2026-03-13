# 잡코리아 채용공고 크롤링 파이프라인

잡코리아(JobKorea) 검색 결과와 상세 페이지를 수집해 PostgreSQL에 저장하는 2단계 크롤링 파이프라인입니다.

## 현재 구현 범위

- **Phase 1**: 검색 결과 목록 페이지 크롤링 후 `companies`, `job_postings` 저장
- **Phase 2**: 상세 정보가 비어 있는 회사의 상세 페이지를 방문해 회사 정보 보강
- **다중 키워드 지원**: `SEARCH_KEYWORDS` 기준으로 키워드별 실행
- **실행 이력 저장**: `crawl_runs` 테이블에 키워드별 실행 상태 기록
- **데이터 정제**: 저장 전 `validators.py`에서 급여, 날짜, URL, 회사 정보 정제
- **봇 탐지 대응**: stealth, User-Agent, Referer, 랜덤 딜레이, 연속 실패 쿨다운

## 실제 파일 구조

```text
jobkorea/
├── config.py
├── crawler.py
├── database.py
├── main.py
├── parser.py
├── validators.py
├── analyze_detail_page.py
├── run_crawler.sh
├── requirements.txt
├── tests/
│   ├── fixtures/
│   ├── test_config.py
│   ├── test_crawler.py
│   ├── test_database.py
│   ├── test_parser.py
│   └── test_validators.py
└── docs/
    ├── architecture/
    ├── guides/
    ├── plans/
    ├── refactoring/
    └── reports/
```

`tests/test_crawler.py`는 이름과 달리 pytest 테스트가 아니라, 초기에 만들었던 수동 1페이지 점검 스크립트입니다.

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 준비

```bash
cp .env.example .env
```

기본 예시는 다음과 같습니다.

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=jobkorea
DB_USER=postgres
DB_PASSWORD=your_password_here

SEARCH_KEYWORDS=데이터분석가,사업기획,프로젝트매니저
MAX_PAGES=5
REQUEST_DELAY_MIN=2
REQUEST_DELAY_MAX=5
HEADLESS=true
LOG_LEVEL=INFO
LOG_DIR=log
```

주의:
- 코드 기본값은 `DB_PORT=5433`입니다. 로컬 PostgreSQL이 `5432`를 쓰면 `.env`에서 직접 바꾸면 됩니다.
- `SEARCH_KEYWORDS`가 기본 경로이고, `SEARCH_KEYWORD`는 하위 호환성용입니다.

### 3. PostgreSQL 준비

```bash
createdb jobkorea
```

테이블은 실행 시 자동 생성됩니다.

## 실행

전체 파이프라인 실행:

```bash
python main.py
```

상세 페이지 구조를 수동 분석할 때:

```bash
python analyze_detail_page.py
```

레거시 1페이지 CSV 점검 스크립트 실행:

```bash
python tests/test_crawler.py
```

스케줄러용 래퍼 스크립트:

```bash
./run_crawler.sh
```

## 테스트

```bash
pytest tests/ -q
```

현재 기준 테스트 결과:
- `69 passed, 10 skipped`
- 스킵된 10건은 로컬 PostgreSQL이 필요한 DB 테스트입니다.

## 데이터 모델

### `companies`

- `id`
- `name` `UNIQUE`
- `company_size`
- `industry`
- `employee_count`
- `establishment_year`
- `homepage_url`
- `created_at`
- `updated_at`

### `job_postings`

- `id`
- `company_id`
- `title`
- `location`
- `job_category`
- `salary`
- `experience`
- `benefits`
- `badge`
- `apply_type`
- `posted_date`
- `deadline`
- `detail_url` `UNIQUE`
- `search_keyword`
- `crawled_at`

### `crawl_runs`

- `id`
- `keyword`
- `started_at`
- `completed_at`
- `pages_crawled`
- `jobs_collected`
- `status`

## 문서 안내

- 현재 구조와 실행 흐름: `docs/architecture/system_architecture.md`
- 운영/설정 가이드: `docs/guides/`
- `docs/reports/`의 문서는 완료 시점 기록입니다. 현재 상태 설명서가 아니라 historical snapshot으로 보아야 합니다.
