# 잡코리아 크롤러 개발 로드맵 (Historical Snapshot)

> 최종 업데이트: 2026-03-10
> 상태: Historical snapshot
> 주의: 이 문서는 초기에 작성된 단계별 로드맵입니다. 현재 구현 상태나 다음 작업 우선순위 판단에는 직접 사용하지 않습니다.
> 현재 기준 판단은 `docs/status/current_status.md`, `docs/architecture/system_architecture.md`, `docs/plans/data_pipeline_service_roadmap.md`를 우선합니다.

---

## 프로젝트 비전

**채용 시장 분석 + 오픈소스 공유**를 목표로 하는 잡코리아 크롤링 시스템

### 핵심 요구사항 요약

| 항목 | 결정 사항 |
|------|----------|
| 사용 목적 | 개인 분석 + 오픈소스 공개 |
| 크롤링 주기 | 매일 오전 9시 |
| 키워드 | 다중 키워드 지원 필요 |
| 데이터 보존 | 마감 공고 보관 (히스토리 추적) |
| 사용자 | 우선 개인, GitHub 공개 예정 |
| 알림 | 로그 파일 필수, Slack/이메일은 추후 |
| 봇 차단 | 자동 대응 로직 구현 |
| 데이터 품질 | 검증 로직 추가 |

---

## 개발 단계 개요

```
Phase 1: 안정화 (1주)     → 로깅, 리팩토링, 검증
Phase 2: 확장 (2주)       → 다중 키워드, 히스토리, 스케줄링
Phase 3: 공개 준비 (1주)  → 문서화, 오픈소스 준비
Phase 4: 고도화 (선택)    → 대시보드, 알림, 분석 기능
```

---

## Phase 1: 안정화 (1주)

> 목표: 프로덕션 환경에서 안정적으로 동작하도록 기반 강화

### 1.1 로깅 시스템 구축 (필수)

**현재 문제**: 모든 출력이 `print()`로 되어 있어 문제 추적 불가

**구현 내용**:
```
log/
├── crawler.log      # 크롤링 로그
├── parser.log       # 파싱 로그
└── error.log        # 에러 전용 로그
```

**작업 목록**:
- [ ] `log/` 디렉토리 생성 및 `.gitignore` 추가
- [ ] `config.py`에 로깅 설정 추가 (LOG_LEVEL, LOG_FILE)
- [ ] `crawler.py` print() → logging 전환
- [ ] `parser.py` print() → logging 전환
- [ ] `main.py` print() → logging 전환
- [ ] 로그 로테이션 설정 (파일 크기 제한)

**예상 시간**: 2시간

---

### 1.2 파싱 함수 리팩토링 (필수)

**현재 문제**: 복잡도 F등급(42), E등급(32) 함수 존재

**구현 내용**:
```python
# Before: 100줄짜리 단일 함수
def parse_company_detail(html): ...

# After: 기능별 분리
def parse_company_detail(html): ...      # 30줄, 조율 역할
def _parse_from_dl_structure(soup): ...  # 25줄
def _parse_from_table_structure(soup): ... # 25줄
def _parse_from_keywords(soup): ...      # 25줄
```

**작업 목록**:
- [ ] `parse_company_detail()` 3개 함수로 분리
- [ ] `extract_card_data()` 헬퍼 함수로 분리
- [ ] 기존 테스트 통과 확인
- [ ] radon 복잡도 재측정 (목표: 모두 A~B등급)

**예상 시간**: 3시간

---

### 1.3 데이터 검증 로직 추가 (필수)

**현재 문제**: 비정상 데이터가 그대로 저장됨

**구현 내용**:
```python
# parser.py 또는 새 파일 validators.py
def validate_job_posting(data: dict) -> dict:
    """채용공고 데이터 검증 및 정제"""
    # 급여: 비현실적 값 필터링
    # 날짜: 형식 검증
    # 필수 필드: 누락 체크

def validate_company_details(data: dict) -> dict:
    """회사 정보 검증"""
    # 설립연도: 1900~현재
    # 사원수: 숫자 형식
    # URL: 형식 검증
```

**작업 목록**:
- [ ] `validators.py` 파일 생성
- [ ] `validate_job_posting()` 구현
- [ ] `validate_company_details()` 구현
- [ ] `main.py`에서 저장 전 검증 호출
- [ ] 검증 실패 시 로그 기록 (저장은 진행)

**예상 시간**: 2시간

---

### 1.4 DB 연결 검증 (필수)

**현재 문제**: DB 미실행 시 불친절한 에러

**구현 내용**:
```python
# database.py
def __init__(self, config):
    try:
        self.engine = create_engine(...)
        self._test_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error("❌ 데이터베이스 연결 실패")
        self._print_troubleshooting_guide()
        raise
```

**작업 목록**:
- [ ] `_test_connection()` 메서드 추가
- [ ] `_print_troubleshooting_guide()` 메서드 추가
- [ ] 연결 실패 시 명확한 가이드 출력

**예상 시간**: 30분

---

### 1.5 테스트 정비 (권장)

**작업 목록**:
- [ ] 환경변수 불일치 테스트 수정
- [ ] `conftest.py` 개선 (테스트용 환경변수 설정)
- [ ] 모든 테스트 통과 확인

**예상 시간**: 1시간

---

### Phase 1 완료 기준

- [ ] 모든 로그가 파일에 기록됨
- [ ] radon 복잡도 모두 A~B등급
- [ ] 데이터 검증 로직 작동
- [ ] DB 연결 실패 시 명확한 에러 메시지
- [ ] pytest 모든 테스트 통과

---

## Phase 2: 확장 (2주)

> 목표: 다중 키워드, 히스토리 추적, 자동 실행 지원

### 2.1 다중 키워드 지원 (필수)

**구현 내용**:
```python
# config.py
SEARCH_KEYWORDS = os.getenv(
    "SEARCH_KEYWORDS",
    "데이터분석가,사업기획,프로젝트매니저"
).split(",")

# main.py
for keyword in config.SEARCH_KEYWORDS:
    logger.info(f"키워드 '{keyword}' 크롤링 시작")
    run_phase1_for_keyword(keyword, config, db)
    run_phase2(config, db)
```

**DB 스키마 변경**:
```sql
-- 크롤링 실행 기록 테이블
CREATE TABLE crawl_runs (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    pages_crawled INT DEFAULT 0,
    jobs_collected INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running'  -- running, completed, failed
);

-- job_postings에 키워드 연결 (선택)
ALTER TABLE job_postings
ADD COLUMN search_keyword VARCHAR(100);
```

**작업 목록**:
- [ ] `config.py`에 `SEARCH_KEYWORDS` 추가
- [ ] `crawl_runs` 테이블 생성
- [ ] `main.py` 다중 키워드 루프 구현
- [ ] 키워드별 통계 출력
- [ ] 기존 단일 키워드 호환성 유지

**예상 시간**: 4시간

---

### 2.2 히스토리 추적 (필수)

**구현 내용**:
```sql
-- 공고 변경 이력 테이블
CREATE TABLE job_posting_history (
    id SERIAL PRIMARY KEY,
    job_posting_id INT REFERENCES job_postings(id),
    field_name VARCHAR(50),       -- 'deadline', 'salary' 등
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 마감 공고 상태 추적
ALTER TABLE job_postings
ADD COLUMN status VARCHAR(20) DEFAULT 'active';  -- active, expired, closed
```

**작업 목록**:
- [ ] `job_posting_history` 테이블 생성
- [ ] `status` 컬럼 추가
- [ ] 마감일 지난 공고 자동 상태 변경 (daily job)
- [ ] 변경 감지 및 히스토리 기록 로직
- [ ] 히스토리 조회 함수 추가

**예상 시간**: 4시간

---

### 2.3 증분 크롤링 (필수)

**현재 문제**: 매번 전체 페이지를 처음부터 크롤링

**구현 내용**:
```python
def should_stop_crawling(job_postings: list, db: DatabaseManager) -> bool:
    """이미 수집한 공고가 나오면 중단"""
    for job in job_postings:
        if db.exists_job_posting(job['detail_url']):
            consecutive_duplicates += 1
            if consecutive_duplicates >= 10:
                return True
    return False
```

**작업 목록**:
- [ ] `exists_job_posting()` 메서드 추가
- [ ] 중복 공고 연속 발견 시 조기 종료 로직
- [ ] 마지막 크롤링 시각 기록
- [ ] 신규 공고만 저장되도록 개선

**예상 시간**: 3시간

---

### 2.4 스케줄링 설정 (필수)

**매일 오전 9시 실행**:

```bash
# crontab -e
0 9 * * * cd /path/to/jobkorea && /path/to/python main.py >> log/cron.log 2>&1
```

**또는 systemd timer** (권장):
```ini
# /etc/systemd/system/jobkorea-crawler.service
[Unit]
Description=JobKorea Crawler

[Service]
Type=oneshot
WorkingDirectory=/path/to/jobkorea
ExecStart=/path/to/python main.py
User=your_user

# /etc/systemd/system/jobkorea-crawler.timer
[Unit]
Description=Run JobKorea Crawler daily at 9 AM

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**작업 목록**:
- [ ] cron 또는 systemd timer 설정 문서 작성
- [ ] 스케줄러 설정 예제 추가
- [ ] 실행 스크립트 (`scripts/run_crawler.sh`) 생성

**예상 시간**: 1시간

---

### 2.5 봇 탐지 대응 강화 (필수)

**현재 조치**: selenium-stealth, User-Agent, Referer, 랜덤 딜레이

**추가 구현**:
```python
# crawler.py
class JobKoreaCrawler:
    def __init__(self, config):
        self.consecutive_failures = 0
        self.max_failures = 5

    def crawl_with_retry(self, url: str, max_retries: int = 3) -> str:
        """재시도 로직 포함 크롤링"""
        for attempt in range(max_retries):
            try:
                html = self._crawl(url)
                self.consecutive_failures = 0
                return html
            except Exception as e:
                self.consecutive_failures += 1
                logger.warning(f"크롤링 실패 (시도 {attempt+1}/{max_retries}): {e}")

                if self.consecutive_failures >= self.max_failures:
                    logger.error("연속 실패 한계 도달 - 봇 탐지 의심")
                    self._apply_cooldown()

                time.sleep(random.uniform(5, 10))

        return ""

    def _apply_cooldown(self):
        """쿨다운 적용 (봇 탐지 의심 시)"""
        cooldown = random.uniform(60, 120)  # 1~2분 대기
        logger.info(f"쿨다운 적용: {cooldown:.0f}초 대기")
        time.sleep(cooldown)
        self._restart_driver()  # 드라이버 재시작
```

**작업 목록**:
- [ ] 재시도 로직 구현 (`tenacity` 또는 직접 구현)
- [ ] 연속 실패 감지 및 쿨다운
- [ ] 드라이버 재시작 로직
- [ ] User-Agent 로테이션 (선택)
- [ ] 실패 URL 기록 테이블

**예상 시간**: 3시간

---

### Phase 2 완료 기준

- [ ] 여러 키워드 동시 크롤링 가능
- [ ] 크롤링 실행 기록이 DB에 저장됨
- [ ] 마감 공고 히스토리 추적 가능
- [ ] 증분 크롤링으로 효율성 향상
- [ ] cron/systemd로 매일 9시 자동 실행
- [ ] 봇 탐지 시 자동 대응 (쿨다운, 재시도)

---

## Phase 3: 공개 준비 (1주)

> 목표: GitHub 오픈소스 공개를 위한 문서화 및 사용성 개선

### 3.1 README 강화 (필수)

**구성**:
```markdown
# JobKorea Crawler

> 잡코리아 채용공고 자동 수집 및 분석 도구

## Features
- 2단계 크롤링 (목록 → 상세)
- 다중 키워드 지원
- 봇 탐지 우회
- 히스토리 추적

## Quick Start
1. Clone & Install
2. Configure .env
3. Run

## Configuration
...

## Usage Examples
...

## Contributing
...

## License
MIT
```

**작업 목록**:
- [ ] README.md 전면 개편
- [ ] 설치 가이드 상세화
- [ ] 사용 예제 추가
- [ ] 스크린샷/GIF 추가 (선택)

**예상 시간**: 2시간

---

### 3.2 설정 예제 및 문서 (필수)

**작업 목록**:
- [ ] `.env.example` 파일 생성 (모든 설정 항목 + 설명)
- [ ] `docs/configuration.md` 상세 설정 가이드
- [ ] `docs/troubleshooting.md` 문제 해결 가이드

**예상 시간**: 2시간

---

### 3.3 Docker 지원 (권장)

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Chrome 설치
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: jobkorea
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: jobkorea123
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  crawler:
    build: .
    depends_on:
      - postgres
    env_file:
      - .env
    volumes:
      - ./log:/app/log

volumes:
  pgdata:
```

**작업 목록**:
- [ ] `Dockerfile` 생성
- [ ] `docker-compose.yml` 생성
- [ ] `.dockerignore` 생성
- [ ] Docker 사용법 문서화

**예상 시간**: 3시간

---

### 3.4 코드 품질 정리 (권장)

**작업 목록**:
- [ ] 불필요한 주석 정리
- [ ] 일관된 코드 스타일 (black, isort)
- [ ] 타입 힌트 추가 (주요 함수)
- [ ] docstring 보완

**예상 시간**: 2시간

---

### 3.5 라이선스 및 기여 가이드 (필수)

**작업 목록**:
- [ ] `LICENSE` 파일 추가 (MIT 권장)
- [ ] `CONTRIBUTING.md` 작성
- [ ] Issue 템플릿 추가
- [ ] PR 템플릿 추가

**예상 시간**: 1시간

---

### Phase 3 완료 기준

- [ ] README로 5분 내 시작 가능
- [ ] Docker로 원클릭 실행 가능
- [ ] 모든 설정 항목 문서화됨
- [ ] 라이선스 및 기여 가이드 존재
- [ ] GitHub에 공개 가능한 상태

---

## Phase 4: 고도화 (선택, 추후)

> 목표: 분석 기능, 대시보드, 알림 시스템

### 4.1 통계 분석 기능

```sql
-- 분석용 SQL View
CREATE VIEW job_statistics AS
SELECT
    search_keyword,
    DATE(crawled_at) as crawl_date,
    COUNT(*) as total_jobs,
    COUNT(DISTINCT company_id) as unique_companies,
    AVG(CASE WHEN salary LIKE '%만원%' THEN ... END) as avg_salary
FROM job_postings
GROUP BY search_keyword, DATE(crawled_at);
```

**예상 시간**: 4시간

---

### 4.2 웹 대시보드 (Streamlit)

```python
# dashboard.py
import streamlit as st
import pandas as pd

st.title("잡코리아 채용 분석 대시보드")

# 키워드별 공고 수 추이
st.line_chart(df_trend)

# 최근 공고 목록
st.dataframe(df_recent_jobs)

# 기업 규모별 분포
st.bar_chart(df_company_size)
```

**예상 시간**: 8시간

---

### 4.3 알림 시스템 (Slack)

```python
def send_slack_notification(webhook_url: str, message: str):
    requests.post(webhook_url, json={"text": message})

# 사용 예
send_slack_notification(
    config.SLACK_WEBHOOK_URL,
    f"✅ 크롤링 완료: {keyword} - {count}개 공고 수집"
)
```

**예상 시간**: 2시간

---

### 4.4 API 서버 (FastAPI)

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/jobs")
def get_jobs(keyword: str = None, location: str = None):
    return db.search_jobs(keyword, location)

@app.get("/stats")
def get_statistics():
    return db.get_statistics()
```

**예상 시간**: 6시간

---

## 일정 요약

| 단계 | 기간 | 핵심 산출물 |
|------|------|------------|
| **Phase 1** | 1주 | 로깅, 리팩토링, 검증 로직 |
| **Phase 2** | 2주 | 다중 키워드, 히스토리, 스케줄링 |
| **Phase 3** | 1주 | Docker, README, 오픈소스 준비 |
| **Phase 4** | 선택 | 대시보드, 알림, API |

**총 예상 기간**: 4~5주 (Phase 1~3)

---

## 우선순위 매트릭스

```
           높은 영향
              │
    ┌─────────┼─────────┐
    │ 로깅    │ 다중키워드│
    │ 리팩토링│ 스케줄링 │
높은├─────────┼─────────┤
노력│ Docker  │ 대시보드 │
    │         │ API     │
    └─────────┼─────────┘
              │
           낮은 영향

※ 좌상단부터 우선 진행
```

---

## 체크리스트

### Phase 1 (이번 주)
- [ ] 로깅 시스템 구축
- [ ] 파싱 함수 리팩토링
- [ ] 데이터 검증 로직
- [ ] DB 연결 검증
- [ ] 테스트 정비

### Phase 2 (다음 2주)
- [ ] 다중 키워드 지원
- [ ] 히스토리 추적
- [ ] 증분 크롤링
- [ ] 스케줄링 설정
- [ ] 봇 탐지 대응 강화

### Phase 3 (4주차)
- [ ] README 강화
- [ ] 설정 예제 및 문서
- [ ] Docker 지원
- [ ] 코드 품질 정리
- [ ] 라이선스 및 기여 가이드

---

## 참고 자료

- [CLAUDE.md](/Users/snu.sim/git/jobkorea/CLAUDE.md) - 프로젝트 개요
- [agent_guide.md](../guides/agent_guide.md) - 에이전트 사용법
- [phase2_implementation_plan.md](../plans/phase2_implementation_plan.md) - Phase 2 구현 계획

---

*이 로드맵은 요구사항 변경에 따라 업데이트될 수 있습니다.*
