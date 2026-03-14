# Phase 2 - 본 시스템 구현 기획서

## 목표

Phase 1 테스트 크롤링이 성공적으로 완료되었으므로, `system_architecture.md`에 정의된 본 시스템을 완성한다.
코드 구조를 정비하되, **필요한 곳만 OOP를 적용**하고 과도한 추상화는 피한다.

---

## 현재 코드의 구조적 문제점

### 1. 드라이버 생명주기 관리 부재

`crawl_pages()` 안에서 드라이버를 생성하고 종료한다. Phase 2 상세 크롤링을 추가하면 **드라이버를 매번 다시 생성하는 비효율**이 생긴다.
→ `JobKoreaCrawler` 클래스 + Context Manager로 해결

### 2. 설정값이 3개 파일에 분산

`load_dotenv()`가 `crawler.py`, `database.py`, `main.py`에서 각각 호출되고, 설정 상수도 파일마다 따로 정의된다.
→ `Config` 클래스로 통합

### 3. 에러 발생 시 원인 추적 불가

`main.py`에서 `except Exception as e`로 잡지만, 에러 내용을 출력하지 않고 `total_skipped += 1`만 한다.
→ 에러 메시지를 print로 출력하도록 수정 (logging 전환은 자동화 단계에서)

---

## OOP 적용 기준

| 대상 | OOP 적용? | 이유 |
|------|----------|------|
| Config (설정) | ✅ 클래스 | 설정을 한 곳에서 관리, 여러 모듈이 공유 |
| Crawler (크롤러) | ✅ 클래스 | 드라이버라는 **상태**를 관리해야 함 |
| Parser (파서) | ❌ 함수 유지 | 내부 상태 없음. HTML→dict 순수 함수 |
| Database (DB) | ✅ 클래스 | 엔진/커넥션이라는 **상태**를 관리해야 함 |

> **원칙: 관리할 상태가 있으면 클래스, 없으면 함수.**

---

## 변경 후 디렉토리 구조

```
jobkorea/
├── docs/                          # 문서
│   ├── system_architecture.md
│   ├── phase1_test_plan.md
│   └── phase2_implementation_plan.md
├── .env                           # 환경변수 (HEADLESS 추가)
├── requirements.txt               # 패키지 (sqlalchemy, psycopg2 추가)
├── config.py                [신규] # 설정 통합 관리
├── crawler.py               [수정] # JobKoreaCrawler 클래스
├── parser.py                [수정] # 기존 함수 유지 + parse_company_detail() 추가
├── database.py              [수정] # DatabaseManager 클래스
├── main.py                  [수정] # Phase 1 + Phase 2 통합 실행
├── test_crawler.py                 # Phase 1 테스트 (보존)
└── output/
    └── test_result.csv
```

---

## 작업 목록 (순서대로)

### 작업 0: `requirements.txt` 보완

```diff
 selenium>=4.15.0
 selenium-stealth>=1.0.6
 beautifulsoup4>=4.12.0
 pandas>=2.0.0
 python-dotenv>=1.0.0
 webdriver-manager>=4.0.0
+sqlalchemy>=2.0.0
+psycopg2-binary>=2.9.0
```

---

### 작업 1: `config.py` 신규 생성

모든 환경변수를 한 곳에서 관리하는 Config 클래스.

```python
class Config:
    """환경변수 기반 설정 관리"""
    # DB: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    # 크롤링: SEARCH_KEYWORD, MAX_PAGES, DELAY_MIN, DELAY_MAX, HEADLESS

    @property
    def database_url(self) -> str
```

`.env`에 `HEADLESS=true` 추가.

---

### 작업 2: `crawler.py` → JobKoreaCrawler 클래스

```python
class JobKoreaCrawler:
    """드라이버 생명주기를 관리하는 크롤러"""

    def __init__(self, config: Config)
    def __enter__ / __exit__           # with문으로 안전한 드라이버 관리

    def crawl_list_pages(self) -> list[str]     # Phase 1
    def crawl_detail_page(self, url) -> str     # Phase 2
```

추가 변경:
- Referer 설정 (봇 우회 보완)
- Headless 모드를 Config에서 읽어오기

---

### 작업 3: 상세 페이지 HTML 구조 분석 (Phase 2 사전 작업)

**Phase 2 파싱 로직을 작성하기 전에**, 실제 상세 페이지의 HTML 구조를 확인해야 한다.

방법:
1. DB에서 `detail_url` 하나를 가져온다
2. 브라우저로 접속하여 기업 정보 섹션의 HTML 구조를 확인한다
3. company_size, employee_count, establishment_year, homepage_url이 어떤 셀렉터로 추출 가능한지 파악한다

→ 파악 결과를 바탕으로 작업 4의 파싱 로직을 작성한다.

---

### 작업 4: `parser.py` — Phase 2 함수 추가

기존 함수(`parse_job_cards`, `extract_card_data`)는 **그대로 유지**.
상세 페이지용 파싱 함수만 추가:

```python
def parse_company_detail(html: str) -> dict:
    """상세 페이지에서 회사 정보 추출"""
    # → company_size, employee_count, establishment_year, homepage_url
```

---

### 작업 5: `database.py` → DatabaseManager 클래스

```python
class DatabaseManager:
    """DB 연결 및 CRUD 관리"""

    def __init__(self, config: Config)
    def create_tables(self)
    def get_or_create_company(self, name, industry) -> int
    def insert_job_posting(self, company_id, job_data)
    def get_companies_without_details(self) -> list     # Phase 2
    def update_company_details(self, company_id, details) # Phase 2
    def get_summary(self) -> dict
```

---

### 작업 6: `main.py` 수정

새 클래스들을 사용하도록 변경. Phase 1 → Phase 2 순서로 실행.

```python
def main():
    config = Config()
    db = DatabaseManager(config)
    db.create_tables()

    # Phase 1: 목록 크롤링
    with JobKoreaCrawler(config) as crawler:
        html_pages = crawler.crawl_list_pages()
    # 파싱 + DB 저장 (기존 함수 사용)

    # Phase 2: 상세 크롤링
    companies = db.get_companies_without_details()
    with JobKoreaCrawler(config) as crawler:
        for company in companies:
            html = crawler.crawl_detail_page(company.detail_url)
            details = parse_company_detail(html)
            db.update_company_details(company.id, details)
```

---

## 검증 방법

### 자동 검증
1. `pip install -r requirements.txt` — 설치 확인
2. `python -c "from config import Config; print(Config().database_url)"` — 설정 확인

### 기존 데이터 호환성 검증
1. 리팩토링 전후로 DB의 `companies`, `job_postings` 레코드 수가 동일한지 확인
2. `python main.py` 실행 시 기존 데이터에 영향 없이 Phase 2가 정상 동작하는지 확인

### Phase 2 결과 검증
```sql
SELECT name, company_size, employee_count, establishment_year
FROM companies
WHERE company_size IS NOT NULL;
```

---

## 향후 작업 (이번 범위 밖)

다음 단계에서 필요할 때 진행:
- `print()` → `logging` 전환 (cron 자동화 시)
- 다중 키워드 지원
- 대시보드 연동

---

## 관련 문서

- 시스템 아키텍처: [system_architecture.md](../architecture/system_architecture.md)
- Phase 1 테스트 기획: [phase1_test_plan.md](./phase1_test_plan.md)
