# Session Handoff

> Last updated: 2026-03-14
> Purpose: 다음 세션이 바로 이어서 작업할 수 있게 최근 변경과 다음 액션만 남기는 문서

## Update Rule

- 길게 쓰지 않는다.
- 이번 세션의 핵심 변경, 검증, 다음 액션만 적는다.
- 이미 `current_status.md`에 있는 일반 설명은 반복하지 않는다.

## Latest Session Summary

- `companies.company_page_url` 컬럼과 저장/재사용 경로를 Phase 2에 추가
- 저장된 회사 페이지 URL이 있으면 JD를 다시 열지 않고 회사 페이지를 직접 방문하도록 최적화
- `scripts/analyze_detail_page.py`를 `--mode jd|company` 기반으로 정리
- 관련 테스트와 결과 보고를 `docs/reports/phase2_followup_stabilization_report.md`에 기록
- `scripts/phase2_smoke_test.py`를 추가해 회사 1~N건만 대상으로 Phase 2 live 검증이 가능하게 함
- live smoke test에서 `네오뉴트라(id=58)` cached URL 경로의 회사 페이지 timeout을 재현함

## Important File Landmarks

- 실행 시작점: `main.py`
- 현재 구조 설명: `docs/architecture/system_architecture.md`
- 현재 active plan: `docs/plans/data_pipeline_service_roadmap.md`
- Phase 2 후속 안정화 보고: `docs/reports/phase2_followup_stabilization_report.md`
- Phase 2 live smoke validation: `docs/reports/phase2_live_smoke_validation_report.md`
- 중장기 로드맵: `docs/plans/data_pipeline_service_roadmap.md`
- 지금 상태 요약: `docs/status/current_status.md`

## Latest Known Verification

- `python3 -m py_compile main.py crawler.py parser.py database.py scripts/analyze_detail_page.py tests/test_main.py tests/test_parser.py tests/test_database.py tests/test_analyze_detail_page.py`
- `pytest tests/test_main.py tests/test_parser.py tests/test_analyze_detail_page.py -q` -> `31 passed`
- `pytest tests/test_database.py -q` -> `20 passed`
- `pytest tests/test_main.py tests/test_database.py tests/test_phase2_smoke_test.py -q` -> `29 passed`
- `pytest tests/ -q` -> `104 passed`
- `venv/bin/python scripts/phase2_smoke_test.py --limit 1 --headless true`
  - cached `company_page_url` 재사용 확인
  - 회사 페이지 URL `https://www.jobkorea.co.kr/Recruit/Co_Read/C/280272` 로딩 timeout 재현

## Recommended Next Action

다음 세션의 첫 작업은 아래 중 하나로 시작한다.

1. `crawl_company_page()` 실패 시 최종 URL과 HTML을 진단용으로 남기는 경로 추가
2. 실패한 회사 페이지를 수동 확인해 차단/리다이렉트/레이아웃 변형 여부 분리
3. 실패 HTML을 fixture로 고정하고 selector 또는 page-type detection 보강
