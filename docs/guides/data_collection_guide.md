# 데이터 수집 및 분석 가이드

> 크롤링부터 대시보드 분석까지의 워크플로우

## 1. 크롤링 설정

### 환경변수 (.env)

```bash
# 검색 키워드 (쉼표로 구분)
SEARCH_KEYWORDS=데이터분석가,데이터엔지니어,ML엔지니어

# 페이지 수 (키워드당)
MAX_PAGES=3

# 기타 설정
HEADLESS=true
REQUEST_DELAY_MIN=2
REQUEST_DELAY_MAX=5
```

### 정렬 방식

현재 **조회수 내림차순**으로 고정되어 있습니다 (`ord=ReadCntDesc`).
인기 있는 공고 위주로 수집하여 데이터 품질을 높입니다.

### 예상 수집량

- 페이지당 약 20개 공고
- 3페이지 × N개 키워드 = 약 60×N개 공고

## 2. 크롤링 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# 크롤링 실행
python main.py
```

### 결과 확인

```bash
# 간단 요약
PGPASSWORD=jobkorea123 psql -h localhost -p 5433 -U postgres -d jobkorea -c "
SELECT
  (SELECT COUNT(*) FROM job_postings) as 공고수,
  (SELECT COUNT(*) FROM companies) as 회사수;
"
```

## 3. 대시보드 실행

```bash
streamlit run dashboard/app.py
```

브라우저에서 http://localhost:8501 접속

### 대시보드 기능

- **전체 요약**: 공고 수, 회사 수, 경력 분포
- **회사 규모별 분포**: 대기업/중견/중소/스타트업
- **지역별 분포**: 서울/경기/기타
- **키워드별 필터링**: 검색 키워드로 데이터 필터

## 4. DB 초기화 (필요시)

새로운 키워드나 설정으로 처음부터 수집하려면:

```bash
PGPASSWORD=jobkorea123 psql -h localhost -p 5433 -U postgres -d jobkorea -c "
TRUNCATE job_postings, companies, crawl_runs, job_posting_history
RESTART IDENTITY CASCADE;
"
```

## 5. Vision API 파싱 (선택)

상세요강 이미지에서 직무 정보를 추출하려면:

```bash
# 필터링된 공고 확인
python scripts/filter_for_vision.py

# Vision API로 파싱 (10개 샘플)
python scripts/run_vision_pipeline.py --limit 10
```

**주의**: Vision API는 건당 비용이 발생합니다.

## 6. 일일 자동화

크론잡으로 매일 자동 크롤링:

```bash
# crontab -e
0 9 * * * /path/to/jobkorea/scripts/run_crawler.sh >> /path/to/log/cron.log 2>&1
```

자세한 내용은 [scheduling_guide.md](scheduling_guide.md) 참고.

## 빠른 시작 (Quick Start)

```bash
cd /Users/snu.sim/git/jobkorea
source venv/bin/activate

# 1. 크롤링
python main.py

# 2. 대시보드
streamlit run dashboard/app.py
# → http://localhost:8501
```
