# Current Status

> Last updated: 2026-03-15
> Purpose: 새 세션이 1분 안에 현재 상태를 파악하기 위한 압축 문서

## Source Of Truth

읽기 우선순위:

1. `README.md`
2. `docs/architecture/system_architecture.md`
3. `docs/plans/data_pipeline_service_roadmap.md`
4. `docs/status/current_status.md`
5. `docs/status/session_handoff.md`

`docs/reports/`는 현재 상태 문서가 아니라 historical snapshot이다.

문서 분류 기준 요약:

- `status/`: 지금 상태와 다음 액션
- `architecture/`: 현재 구조와 설계 원칙의 상세 source of truth
- `plans/`: 현재 active plan
- `guides/`: 실행/운영 방법
- `reports/`: 최근 완료 결과 정리
- `archive/`: 과거 계획/결과/리팩토링 기록

이 문서는 `status/` 문서이므로 구조의 상세 설명을 담지 않는다. 상세 규칙과 구조 설명은 `docs/README.md`, `docs/architecture/system_architecture.md`를 따른다.

## What Is Implemented

- 잡코리아 Phase 1/Phase 2 오케스트레이션 코드 경로
- PostgreSQL 적재
- 다중 키워드 실행
- 증분 크롤링
- 공고 lifecycle 추적
- 공고 변경 이력 저장
- `companies.company_page_url` 저장/재사용
- `scripts/phase2_smoke_test.py` 제한 live 검증 경로
- `scripts/phase2_smoke_test.py --company-id <id>` 강제 재현 경로
- 수동 스크립트와 자동 테스트 경로 분리
- `scripts/analyze_detail_page.py --mode jd|company`
- 검색 결과 / JD 상세 / 회사 페이지 구조 분석 문서
- Phase 1 검색 결과 파서 정확성 감사 완료 (`docs/reports/phase1_correctness_audit_report.md`)
- Phase 2 회사 페이지 전환 메인 경로 구현 완료 (`docs/reports/phase2_company_page_fix_review.md`)
- Phase 2 후속 안정화 완료 (`docs/reports/phase2_followup_stabilization_report.md`)
- Phase 2 live timeout 진단 완료 (`docs/reports/phase2_live_timeout_diagnosis_report.md`)

## Current Repo Shape

- 루트: `main.py`, `config.py`, `crawler.py`, `parser.py`, `validators.py`, `database.py`
- `scripts/`: 수동 점검, 구조 분석, 스케줄링 실행 스크립트
- `tests/`: 자동 테스트
- `docs/`: `status`, `architecture`, `plans`, `guides`, `reports`, `archive`

## Latest Verification

- Phase 1/2 parser+main+script 검증: `pytest tests/test_main.py tests/test_parser.py tests/test_analyze_detail_page.py -q` -> `31 passed`
- Phase 2 smoke path 검증: `pytest tests/test_main.py tests/test_database.py tests/test_phase2_smoke_test.py -q` -> `29 passed`
- 전체 테스트: `pytest tests/ -q` -> `110 passed`
- live smoke test: `venv/bin/python scripts/phase2_smoke_test.py --limit 1 --headless true`
  - 결과: 현재 기본 대상 `한영회계법인(id=59)`가 정상 업데이트되고 final URL/title이 출력됨
- targeted live smoke test: `venv/bin/python scripts/phase2_smoke_test.py --limit 1 --company-id 58 --headless true`
  - 결과: `네오뉴트라(id=58)`의 cached `company_page_url`가 `https://www.jobkorea.co.kr/Super/neonutra`로 리다이렉트됐고 현재 live rerun에서는 timeout 없이 업데이트 성공
- broader live smoke test: `venv/bin/python scripts/phase2_smoke_test.py --limit 5 --headless true`
  - 결과: cached 1건 + JD 출발 4건이 모두 `updated`, 현재 표본에서는 timeout 재현 없음

## Remaining Risks

- Phase 1 검색 결과 파서는 현재 fixture 기준으로 안정화됐지만, fixture가 1개라 DOM drift 탐지 범위는 아직 좁음
- `JobList`를 찾지 못할 때 전역 `CardJob`로 폴백하는 경로가 남아 있어, live 구조가 크게 바뀌면 다시 과수집 가능성이 있음
- 기존 데이터 중 `company_page_url`가 아직 비어 있는 회사는 첫 Phase 2 보강 시 한 번은 JD를 열어야 함
- historical artifact 기준 `Co_Read -> Super` 리다이렉트 경로에서 timeout이 한 번 기록됐지만, 2026-03-15 current live rerun과 5건 mixed smoke sample에서는 동일 증상이 재현되지 않음
- 현재는 `Co_Read -> Super` 리다이렉트가 일어나도 관찰된 `final_url`을 `companies.company_page_url`에 재저장하지 않으므로, 캐시 정규화 여부를 아직 결정하지 못한 상태다
- 현재 기본 Phase 2 대상 조회는 `company_size IS NULL` 기준이라 일부 필드만 비어 있는 회사는 자동 재보강 대상에서 빠질 수 있음
- 저장된 `company_page_url`가 stale하거나 실패하는 경우 JD로 재해결하는 fallback은 아직 없다
- JD/회사 페이지 selector 회귀 검증은 아직 소수 fixture 중심이라 레이아웃 변형 대응 범위가 좁음

## Next Priorities

1. 리다이렉트된 `final_url`을 `companies.company_page_url` 캐시에 반영할지 판단
2. Phase 2 대상 선택을 `company_size IS NULL` 단일 조건에서 넓힐지 판단
3. `Super` 회사 페이지 fixture를 더 확보해 redirect/layout variation 회귀 범위 확장
4. 저장된 `company_page_url` 실패 시 JD 재해결 fallback을 넣을지 판단
5. `scripts/run_crawler.sh` 기반 일일 자동 실행 실제 적용
6. `crawl_runs` 기반 운영 상태 요약 기능 추가

즉시 실행용 문서:

- `docs/plans/data_pipeline_service_roadmap.md`
- `docs/plans/phase2_live_timeout_diagnosis_plan.md`
- `docs/reports/phase2_live_timeout_diagnosis_report.md`
- `docs/reports/phase2_live_smoke_validation_report.md`

## Guardrails

- Airflow, Kafka, Redis Queue 같은 큰 도구는 지금 넣지 않는다.
- 원문 텍스트를 먼저 저장하고, 정규화는 그 다음에 한다.
- 프론트엔드가 DB에 직접 붙지 않게 한다.
- 배치는 idempotent하게 유지한다.
