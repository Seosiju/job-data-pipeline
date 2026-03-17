# Session Handoff

> Last updated: 2026-03-16
> Purpose: 다음 세션이 바로 이어서 작업할 수 있게 최근 변경과 다음 액션만 남기는 문서

## Update Rule

- 길게 쓰지 않는다.
- 이번 세션의 핵심 변경, 검증, 다음 액션만 적는다.
- 이미 `current_status.md`에 있는 일반 설명은 반복하지 않는다.

## Latest Session Summary (2026-03-16)

### 완료된 작업

1. **파이프라인 검증 완료**: "데이터분석가" 키워드로 Phase 1/2 크롤링 검증
   - Phase 1: 40개 공고 수집 (11초), 원본 일치 확인
   - Phase 2: 회사 상세 보강 성공, cache 재사용 확인
   - 검증 리포트: `docs/reports/crawl_validation_report_20260316.md`

2. **Phase 1 검색 필터 기능**: 지역/경력/고용형태 필터 추가
   - `SEARCH_LOCATIONS`, `SEARCH_EXPERIENCE_TYPES`, `SEARCH_EMPLOYMENT_TYPES` env 설정
   - hydration 메타데이터 파싱으로 고용형태 판별

3. **분석 도구 생성**: Jupyter 노트북 + Streamlit 대시보드
   - `notebooks/job_market_analysis.ipynb`: 지역별/경력별/회사규모별 분석
   - `dashboard/app.py`: 인터랙티브 대시보드 (Plotly)

4. **OCR 파싱 PoC 완료**: 잡코리아 상세요강 텍스트 추출 + LLM 파싱
   - S3에서 OCR 텍스트 추출 성공
   - LangChain + OpenAI(gpt-4o-mini)로 직무별 분리 성공
   - 안랩 공고 1개 → 3개 직무로 분리 (SW Cloud, Windows, Linux)
   - PoC 코드: `scripts/poc_ocr_parsing.py`

## Important File Landmarks

| 용도 | 파일 |
|------|------|
| 실행 시작점 | `main.py` |
| 현재 구조 설명 | `docs/architecture/system_architecture.md` |
| 현재 상태 | `docs/status/current_status.md` |
| 검증 리포트 | `docs/reports/crawl_validation_report_20260316.md` |
| OCR 파싱 PoC | `scripts/poc_ocr_parsing.py` |
| 분석 노트북 | `notebooks/job_market_analysis.ipynb` |
| 대시보드 | `dashboard/app.py` |

## Latest Known Verification

```bash
# 테스트
pytest tests/ -q  # 113 passed

# 대시보드 실행
streamlit run dashboard/app.py  # http://localhost:8501

# OCR 파싱 PoC
python scripts/poc_ocr_parsing.py
```

## Recommended Next Action

다음 세션은 아래 중 하나로 시작:

### 옵션 1: OCR 파싱 프로덕션 구현 (추천)

PoC가 완료되었으므로 본격 구현 가능:
- `job_positions` 테이블 생성 (job_postings와 1:N)
- OCR URL 추출 → LangChain 파싱 → DB 저장
- 기술스택 정규화 및 트렌드 분석

**시작점**: `scripts/poc_ocr_parsing.py` 참고

### 옵션 2: 기술스택 트렌드 분석

현재 데이터(2,148개 공고)로 분석:
- Jupyter 노트북 실행: `jupyter notebook notebooks/job_market_analysis.ipynb`
- 대시보드: `streamlit run dashboard/app.py`

### 옵션 3: 일일 자동화 설정

크론잡으로 일일 크롤링 자동화: `./scripts/run_crawler.sh`

## Quick Start (다음 세션)

```bash
cd /Users/snu.sim/git/jobkorea
source venv/bin/activate

# 현재 상태 확인
cat docs/status/session_handoff.md

# 테스트 확인
pytest tests/ -q
```
