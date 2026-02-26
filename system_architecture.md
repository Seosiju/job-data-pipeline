# 잡코리아 채용공고 크롤링 시스템 아키텍처

## 1. 프로젝트 개요

잡코리아(JobKorea)에서 '데이터분석가' 관련 채용공고를 자동으로 수집하고, PostgreSQL 데이터베이스에 저장하여 SQL 기반 분석이 가능하도록 하는 시스템.

---

## 2. 시스템 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                          시스템 전체 흐름                             │
└─────────────────────────────────────────────────────────────────────┘

                        [Phase 1: 목록 크롤링]
┌──────────┐     ┌──────────────┐     ┌──────────┐     ┌─────────────┐
│ JobKorea │────▶│  Crawler     │────▶│  Parser  │────▶│ PostgreSQL  │
│ (검색결과) │     │  (Selenium)  │     │  (BS4)   │     │             │
└──────────┘     └──────────────┘     └──────────┘     │ job_postings│
                                                        │ companies   │
                        [Phase 2: 상세 크롤링]           └──────┬──────┘
┌──────────┐     ┌──────────────┐     ┌──────────┐            │
│ JobKorea │────▶│  Crawler     │────▶│  Parser  │────────────┘
│ (상세페이지)│     │  (Selenium)  │     │  (BS4)   │
└──────────┘     └──────────────┘     └──────────┘
                                                        ┌─────────────┐
                                                        │  SQL 분석    │
                                                        │  (JOIN 쿼리)  │
                                                        └─────────────┘
```

### 크롤링 2단계 전략
- **Phase 1 (목록 페이지)**: 검색 결과에서 공고 카드 정보 수집 → `job_postings` 테이블
- **Phase 2 (상세 페이지)**: 각 공고의 detail_url에 접속하여 회사 상세 정보 수집 → `companies` 테이블

---

## 3. 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| **언어** | Python 3.10+ | 메인 개발 언어 |
| **크롤링** | Selenium + ChromeDriver | 동적 페이지 렌더링 및 탐색 |
| **파싱** | BeautifulSoup4 | HTML 파싱, 데이터 추출 |
| **봇 우회** | selenium-stealth | 봇 탐지 우회 |
| **데이터 처리** | pandas | DataFrame 생성 및 정제 |
| **DB** | PostgreSQL | 데이터 저장 및 SQL 분석 |
| **DB 드라이버** | psycopg2 / SQLAlchemy | Python ↔ PostgreSQL 연결 |
| **환경 관리** | python-dotenv | DB 접속 정보 등 환경변수 관리 |

---

## 4. 수집 대상 (검색 조건)

| 항목 | 값 |
|------|-----|
| **검색어** | 데이터분석가 |
| **지역** | 서울, 인천 |
| **경력** | 신입(careerType=1), 경력무관(careerType=4) |
| **탭** | 채용(tabType=recruit) |
| **정렬** | 관련도순 (기본값) |

### 기본 URL 패턴
```
https://www.jobkorea.co.kr/Search/?stext=데이터분석가&FeatureCode=WRK&Page_No={page}&careerType=1,4&tabType=recruit
```

---

## 5. 데이터베이스 설계

### 5.1 ER 다이어그램

```
┌─────────────────────┐         ┌─────────────────────────┐
│     companies       │         │     job_postings         │
├─────────────────────┤         ├─────────────────────────┤
│ id (PK)             │◄───┐    │ id (PK)                 │
│ name                │    └────│ company_id (FK)         │
│ company_size        │         │ title                   │
│ industry            │         │ location                │
│ employee_count      │         │ job_category            │
│ establishment_year  │         │ salary                  │
│ homepage_url        │         │ experience              │
│ created_at          │         │ benefits                │
│ updated_at          │         │ badge                   │
└─────────────────────┘         │ apply_type              │
                                │ posted_date             │
                                │ deadline                │
                                │ detail_url              │
                                │ crawled_at              │
                                └─────────────────────────┘
```

### 5.2 `companies` 테이블 (회사 정보)

| # | 컬럼명 | 타입 | 설명 | 출처 |
|---|--------|------|------|------|
| 1 | `id` | SERIAL (PK) | 자동 증가 고유 ID | - |
| 2 | `name` | VARCHAR(200) | 회사명 | 목록 카드 |
| 3 | `company_size` | VARCHAR(50) | 기업 규모 | 상세 페이지 (기업 정보) |
| 4 | `industry` | VARCHAR(200) | 업종 | 목록 카드 (GrayChip 💼) |
| 5 | `employee_count` | VARCHAR(50) | 사원수 | 상세 페이지 (기업 정보) |
| 6 | `establishment_year` | VARCHAR(20) | 설립연도 | 상세 페이지 (기업 정보) |
| 7 | `homepage_url` | TEXT | 기업 홈페이지 | 상세 페이지 (기업 정보) |
| 8 | `created_at` | TIMESTAMP | 최초 등록 시각 | 자동 |
| 9 | `updated_at` | TIMESTAMP | 최종 갱신 시각 | 자동 |

> **`company_size` 값 예시**: 대기업, 중견기업, 중소기업, 스타트업 등  
> 잡코리아 상세 페이지의 기업 정보 섹션에서 수집합니다.  
> 뱃지에 "탄탄한 중견기업" 같은 힌트가 있기도 하지만, 정확한 분류는 상세 페이지에서 가져옵니다.

### 5.3 `job_postings` 테이블 (채용공고)

| # | 컬럼명 | 타입 | 설명 | 출처 |
|---|--------|------|------|------|
| 1 | `id` | SERIAL (PK) | 자동 증가 고유 ID | - |
| 2 | `company_id` | INTEGER (FK) | 회사 테이블 참조 | companies.id |
| 3 | `title` | VARCHAR(500) | 공고 제목 | 목록 카드 (`size18` 텍스트) |
| 4 | `location` | VARCHAR(100) | 근무지역 | 목록 카드 (GrayChip 📍) |
| 5 | `job_category` | VARCHAR(300) | 직무 카테고리 | 목록 카드 (GrayChip 💼) |
| 6 | `salary` | VARCHAR(100) | 급여 정보 | 목록 카드 (GrayChip 💵) |
| 7 | `experience` | VARCHAR(100) | 경력 조건 | 목록 카드 (`size13` 텍스트) |
| 8 | `benefits` | TEXT | 복리후생 | 목록 카드 (경력 옆 • 뒤) |
| 9 | `badge` | VARCHAR(100) | 뱃지 | 목록 카드 (BadgeItem) |
| 10 | `apply_type` | VARCHAR(50) | 지원 방식 | 목록 카드 (버튼 텍스트) |
| 11 | `posted_date` | VARCHAR(50) | 등록일 | 목록 카드 |
| 12 | `deadline` | VARCHAR(50) | 마감일 | 목록 카드 |
| 13 | `detail_url` | TEXT | 상세 페이지 URL | 목록 카드 (`<a>` href) |
| 14 | `crawled_at` | TIMESTAMP | 크롤링 수집 시각 | 자동 |

> **`salary` 출처 설명**: HTML 카드 안의 GrayChip 중 💵 아이콘(`emoji--basicemoji-money_bill`) 옆 텍스트.  
> ⚠️ 모든 공고에 급여가 표시되진 않음. 회사가 급여를 공개한 경우에만 해당 칩이 노출됨.

> **`industry`와 `job_category` 분리 기준**: HTML에서 `은행·금융, 데이터분석가` 형태로 표시됨.  
> 쉼표 기준 첫 번째 항목이 업종(→ `companies.industry`), 나머지가 직무(→ `job_postings.job_category`).

---

## 6. PostgreSQL DDL

```sql
-- 회사 정보 테이블
CREATE TABLE IF NOT EXISTS companies (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL UNIQUE,
    company_size        VARCHAR(50),
    industry            VARCHAR(200),
    employee_count      VARCHAR(50),
    establishment_year  VARCHAR(20),
    homepage_url        TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 채용공고 테이블
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
    crawled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_company_name ON companies(name);
CREATE INDEX idx_company_size ON companies(company_size);
CREATE INDEX idx_job_company_id ON job_postings(company_id);
CREATE INDEX idx_job_location ON job_postings(location);
CREATE INDEX idx_job_experience ON job_postings(experience);
CREATE INDEX idx_job_deadline ON job_postings(deadline);
```

---

## 7. 프로젝트 디렉토리 구조

```
jobkorea/
├── system_architecture.md    # 시스템 아키텍처 문서 (본 파일)
├── .env                      # 환경변수 (아래 참조)
├── requirements.txt          # Python 패키지 목록
├── crawler.py                # 크롤링 메인 스크립트
├── parser.py                 # HTML 파싱 및 데이터 추출
├── database.py               # PostgreSQL 연결 및 테이블 관리
├── main.py                   # 실행 진입점
└── data/                     # (선택) CSV 백업 저장 폴더
    └── jobs_backup.csv
```

### .env 파일에 넣어야 할 정보

```env
# ===== PostgreSQL 접속 정보 =====
DB_HOST=localhost              # DB 서버 주소 (Docker면 localhost)
DB_PORT=5432                   # PostgreSQL 기본 포트
DB_NAME=jobkorea               # 데이터베이스 이름 (직접 생성 필요)
DB_USER=postgres               # DB 사용자명 (PostgreSQL 기본 사용자)
DB_PASSWORD=your_password      # DB 비밀번호 (설치 시 설정한 값)

# ===== 크롤링 설정 =====
SEARCH_KEYWORD=데이터분석가     # 검색 키워드
MAX_PAGES=5                    # 최대 크롤링 페이지 수
REQUEST_DELAY_MIN=2            # 요청 간 최소 딜레이 (초)
REQUEST_DELAY_MAX=5            # 요청 간 최대 딜레이 (초)
```

> PostgreSQL을 Docker로 설치하면 `DB_PASSWORD`는 docker run 시 지정한 값,
> 로컬 설치면 설치 과정에서 설정한 비밀번호를 입력합니다.

---

## 8. 처리 흐름 (상세)

### Phase 1: 목록 페이지 크롤링 (crawler.py)
```
1. Selenium WebDriver 초기화 (Chrome + stealth 설정)
2. User-Agent 설정 및 봇 탐지 우회
3. 검색 URL 접속 (Page_No=1 부터 시작)
4. 페이지 로딩 대기 (WebDriverWait)
5. 페이지 HTML 소스 가져오기
6. CardJob 단위로 파싱 → job_postings 저장
7. 회사명 기준으로 companies 테이블에 신규 회사 등록
8. 다음 페이지 존재 여부 확인 → 반복
9. 요청 간 랜덤 딜레이 (2~5초)
```

### Phase 2: 상세 페이지 크롤링 (회사 정보 보강)
```
1. companies 테이블에서 company_size가 NULL인 회사 조회
2. 해당 회사의 공고 상세 페이지(detail_url) 접속
3. 기업 정보 섹션에서 규모, 사원수, 설립연도 등 추출
4. companies 테이블 UPDATE
5. 요청 간 랜덤 딜레이 (3~7초)
```

---

## 9. 크롤링 주기

| 항목 | 설정 |
|------|------|
| **주기** | 하루 1회 |
| **추천 시간** | 매일 오전 9시 (새 공고가 업무시간에 올라오므로) |
| **자동화 방법** | cron (로컬) 또는 GitHub Actions (클라우드) |
| **중복 처리** | `detail_url` UNIQUE 제약조건으로 중복 INSERT 방지 |

---

## 10. 봇 탐지 우회 전략

| 전략 | 구현 방법 |
|------|----------|
| User-Agent 설정 | 실제 Chrome UA 문자열 사용 |
| Stealth 모드 | `selenium-stealth` 라이브러리 적용 |
| 랜덤 딜레이 | `time.sleep(random.uniform(2, 5))` |
| Headless 감지 우회 | `navigator.webdriver` 플래그 변경 |
| Referer 설정 | 잡코리아 메인 URL을 Referer로 설정 |

---

## 11. 예상 SQL 분석 쿼리 예시

```sql
-- 기업 규모별 공고 수 (JOIN 활용)
SELECT c.company_size, COUNT(*) as cnt
FROM job_postings jp
JOIN companies c ON jp.company_id = c.id
GROUP BY c.company_size
ORDER BY cnt DESC;

-- 대기업/중견기업 공고만 조회
SELECT jp.title, c.name, c.company_size, jp.location, jp.salary
FROM job_postings jp
JOIN companies c ON jp.company_id = c.id
WHERE c.company_size IN ('대기업', '중견기업');

-- 지역별 공고 수
SELECT location, COUNT(*) as cnt
FROM job_postings
GROUP BY location
ORDER BY cnt DESC;

-- 급여 정보가 있는 공고 (회사 규모 포함)
SELECT jp.title, c.name, c.company_size, jp.salary
FROM job_postings jp
JOIN companies c ON jp.company_id = c.id
WHERE jp.salary IS NOT NULL AND jp.salary != '';

-- 가장 많은 공고를 올린 회사 TOP 10
SELECT c.name, c.company_size, COUNT(*) as posting_count
FROM job_postings jp
JOIN companies c ON jp.company_id = c.id
GROUP BY c.name, c.company_size
ORDER BY posting_count DESC
LIMIT 10;

-- 업종별 분포
SELECT c.industry, COUNT(*) as cnt
FROM job_postings jp
JOIN companies c ON jp.company_id = c.id
GROUP BY c.industry
ORDER BY cnt DESC;
```

---

## 12. 향후 확장 가능성

- **정기 크롤링 자동화**: cron 또는 GitHub Actions로 매일 자동 수집
- **다중 키워드 지원**: 데이터엔지니어, 데이터사이언티스트 등 추가 검색
- **대시보드 연동**: Streamlit 또는 Metabase로 시각화
- **알림 기능**: 신규 공고 발생 시 Slack/이메일 알림
- **이력 관리**: 공고 상태 변화 추적 (신규 → 마감 등)
