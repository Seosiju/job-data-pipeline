# Phase 2 후속 안정화 보고서 (Historical Snapshot)

> 작성일: 2026-03-14
> 실행 기준 문서: `docs/plans/data_pipeline_service_roadmap.md`
> 관련 선행 문서: `docs/reports/phase2_company_page_fix_review.md`

## 1. 한 줄 요약

`companies.company_page_url` 저장/재사용을 도입해 Phase 2의 불필요한 JD 재방문을 줄였고, 보조 분석 스크립트와 회귀 테스트를 현재 흐름에 맞게 정리했다.

## 2. 이번 작업의 목표

- `company_page_url` 저장 구조 도입 여부 판단과 실제 반영
- 저장된 회사 페이지 URL이 있으면 JD 재방문 최소화
- `scripts/analyze_detail_page.py`의 의미를 현재 Phase 2 흐름과 일치시키기
- 관련 테스트와 검증 경로 보강

## 3. 실제 변경 내용

- company_page_url 저장/재사용
  `companies`에 `company_page_url` 컬럼을 추가하는 additive migration을 도입했다.
  Phase 2가 JD에서 새 회사 페이지 URL을 찾으면 바로 `companies.company_page_url`에 저장한다.
  이후 같은 회사를 다시 보강할 때 저장된 `company_page_url`가 있으면 JD를 다시 열지 않고 회사 페이지를 직접 방문한다.

- JD 재방문 최소화
  `get_companies_without_details()`가 회사당 `company_page_url`와 최신 `detail_url`을 함께 반환하도록 바꿨다.
  `run_phase2()`는 저장된 `company_page_url`를 우선 사용하고, URL이 없을 때만 `detail_url` 기반 JD 방문으로 내려간다.

- analyze_detail_page 스크립트 정리
  `scripts/analyze_detail_page.py`를 `--mode jd|company` CLI로 분리했다.
  `--mode jd`는 JD 상세를 열어 회사 페이지 URL 추출 경로를 확인한다.
  `--mode company`는 DB에 저장된 `company_page_url`를 열어 회사 페이지 구조와 파싱 결과를 확인한다.

- 테스트 보강
  JD에서 찾은 회사 페이지 URL 저장, 저장된 URL 재사용 시 JD 스킵, parser fallback, script mode 동작을 각각 테스트로 고정했다.

## 4. 수정한 파일

- `main.py`
- `database.py`
- `scripts/analyze_detail_page.py`
- `tests/test_main.py`
- `tests/test_parser.py`
- `tests/test_database.py`
- `tests/test_analyze_detail_page.py`
- `README.md`
- `docs/status/current_status.md`
- `docs/status/session_handoff.md`
- `docs/architecture/system_architecture.md`
- `docs/architecture/jobkorea_jd_detail_page_structure.md`
- `docs/reports/phase2_followup_stabilization_report.md`

## 5. 검증 결과

- `python3 -m py_compile main.py crawler.py parser.py database.py scripts/analyze_detail_page.py tests/test_main.py tests/test_parser.py tests/test_database.py tests/test_analyze_detail_page.py`
- `pytest tests/test_main.py tests/test_parser.py tests/test_analyze_detail_page.py -q` -> `31 passed`
- `pytest tests/test_database.py -q` -> `20 passed`
- `pytest tests/ -q` -> `100 passed`

## 6. 남은 리스크

- 기존 데이터 중 `company_page_url`가 아직 없는 회사는 첫 보강 시 한 번은 JD를 열어야 한다.
- 저장된 `company_page_url`가 stale하거나 실패할 때 JD로 재해결하는 fallback은 아직 없다.
- JD 상세 / 회사 페이지 selector 검증은 여전히 소수 fixture 중심이라 live DOM drift 대응 범위가 좁다.

## 7. 다음 권장 작업

- JD 상세 / 회사 페이지 fixture를 더 확보해 selector 회귀 범위를 넓힌다.
- 저장된 `company_page_url` 실패 시 JD 재해결 fallback을 넣을지 판단한다.
- 소규모 live run으로 `company_page_url` 백필과 재사용 경로가 실제로 안정적인지 확인한다.
