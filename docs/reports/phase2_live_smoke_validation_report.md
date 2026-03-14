# Phase 2 Live Smoke Validation Report (Historical Snapshot)

> 작성일: 2026-03-15
> 실행 기준 문서: `docs/plans/data_pipeline_service_roadmap.md`
> 관련 선행 문서: `docs/reports/phase2_followup_stabilization_report.md`

## 1. 한 줄 요약

소규모 live smoke test 경로를 추가해 회사 1건만 대상으로 Phase 2를 검증했고, `company_page_url` 재사용은 확인됐지만 실제 회사 페이지 로딩은 timeout으로 실패했다.

## 2. 이번 작업의 목표

- 전체 `main.py` 대신 Phase 2 대상 일부만 검증할 수 있는 live smoke test 경로를 만든다.
- `company_page_url` 백필/재사용이 실제 사이트에서 동작하는지 빠르게 확인한다.
- 실사이트 실패를 fixture나 후속 수정으로 연결할 수 있게 재현 가능한 실행 경로를 남긴다.

## 3. 실제 변경 내용

- `main.py`
  `run_phase2_for_companies()`를 추가해 선택된 회사 목록만 대상으로 Phase 2를 실행할 수 있게 했다.
  기존 `run_phase2()`는 이 공통 경로를 사용하도록 정리했다.

- `database.py`
  `get_companies_without_details(limit=...)`를 지원해 smoke test가 일부 회사만 조회할 수 있게 했다.

- `scripts/phase2_smoke_test.py`
  Phase 2 대상 일부만 골라 before/after 스냅샷과 실행 결과를 출력하는 live smoke test 스크립트를 추가했다.

- 테스트
  `tests/test_phase2_smoke_test.py`, `tests/test_main.py`, `tests/test_database.py`에 제한 실행 경로와 limit 동작을 고정했다.

## 4. 실행 환경

- 로컬 Docker PostgreSQL: `localhost:5433`
- 검증 명령: `venv/bin/python scripts/phase2_smoke_test.py --limit 1 --headless true`

## 5. 실행 결과

- 선택 대상: `네오뉴트라 (id=58)`
- 실행 전 상태:
  - `company_page_url` 있음
  - `company_size`, `employee_count`, `establishment_year`, `homepage_url` 없음
- 실제 경로:
  - 저장된 `company_page_url` 재사용
  - 회사 페이지 URL: `https://www.jobkorea.co.kr/Recruit/Co_Read/C/280272`
  - 회사 페이지 로딩 3회 재시도 모두 실패
- 실행 후 상태:
  - `company_page_url` 유지
  - 상세 필드는 여전히 비어 있음

## 6. 확인된 사실

- 문제는 Docker/PostgreSQL 연결이 아니다. DB 연결과 대상 조회는 정상 동작했다.
- 문제는 live Phase 2의 회사 페이지 로더다.
- 적어도 이번 샘플에서는 `company_page_url` 재사용 경로까지는 정상적으로 도달했지만, `crawl_company_page()`가 기대 selector를 기다리다 timeout으로 실패했다.
- 따라서 다음 우선순위는 `company_page_url` 저장 구조가 아니라, **실제 회사 페이지 로딩 실패 원인 진단**이다.

## 7. 해석 시 주의

- 같은 날 earlier exploratory run이 DB 상태를 일부 변경했기 때문에, 이번 보고서는 전체 row count delta보다 **타깃 회사 단위 결과**를 기준으로 본다.
- 이번 smoke test는 1건 기준이다. 이 결과만으로 모든 회사 페이지가 동일하게 실패한다고 단정하면 안 된다.

## 8. 남은 리스크

- cached `company_page_url`가 있어도 실제 live company page loader가 timeout 날 수 있다.
- 실패 시 현재 코드는 raw HTML이나 최종 리다이렉트 정보를 남기지 않아 원인 분리가 어렵다.
- 회사 페이지 레이아웃 변형, 차단 페이지, 로그인/리다이렉트 여부를 아직 구분하지 못한다.

## 9. 다음 권장 작업

1. `crawl_company_page()` 실패 시 최종 URL과 page source를 진단용으로 남기는 경로를 추가한다.
2. 실패한 회사 페이지 URL을 수동으로 열어 정상 회사 페이지인지, 차단/리다이렉트인지 확인한다.
3. live 실패 HTML을 fixture로 저장하고 selector 또는 page-type detection을 보강한다.
