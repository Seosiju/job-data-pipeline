---
type: report
status: completed
date: 2026-03-15
related_plan: docs/plans/phase2_live_timeout_diagnosis_plan.md
---

# Phase 2 Live Timeout Diagnosis Report

> 작성일: 2026-03-15
> 실행 기준 문서: `docs/plans/phase2_live_timeout_diagnosis_plan.md`

## 1. 한 줄 요약

2026-03-15 기준 historical timeout artifact를 재진단한 결과, 원인은 anti-bot이 아니라 `Co_Read` 요청이 `Super` 회사 페이지로 리다이렉트되는 레이아웃 변형 경로였고, 현재 live rerun에서는 해당 경로가 정상 로드됐다.

## 2. 실제 원인 분류

- 분류: `redirect + layout variation`
- 요청 URL: `https://www.jobkorea.co.kr/Recruit/Co_Read/C/280272`
- historical failure artifact의 최종 URL: `https://www.jobkorea.co.kr/Super/neonutra`
- historical failure artifact의 title: `네오뉴트라 슈퍼기업관 - 일하기 좋은 우수 기업 | 잡코리아`
- 해석:
  - 차단/로그인/CAPTCHA 페이지 흔적은 없었다.
  - HTML 안에는 `.corpInfo` 기반 슈퍼기업관 회사 정보 블록이 존재했다.
  - 같은 URL을 2026-03-15 current worktree에서 다시 live 실행했을 때는 동일한 `Super` 리다이렉트가 발생했지만 timeout 없이 정상 파싱됐다.

즉, 이번 이슈는 selector가 완전히 틀린 경우보다는 `Co_Read -> Super` 리다이렉트와 회사 페이지 레이아웃 변형이 섞인 경로로 보는 것이 맞다.

## 3. 실제 변경 내용

- `crawler.py`
  - 최근 페이지 로드의 구조화된 진단 정보(`final_url`, `title`, `wait_locator`, `wait_timed_out`, `html_path`, `meta_path`)를 유지하도록 보강
  - 실패 메타 파일에 selector wait 정보까지 남기도록 확장

- `main.py`
  - `run_phase2_for_companies()` 결과에 회사 페이지 최종 URL/title/diagnostic path를 포함
  - `company_page_url`와 최종 URL이 다를 때 redirect를 로그로 남기도록 보강

- `scripts/phase2_smoke_test.py`
  - `--company-id` 옵션을 추가해 특정 회사를 `--limit 1` 경로로 직접 재현 가능하게 함
  - 결과 출력에 final URL/title/timeout 여부/diagnostic path를 포함

## 4. 추가한 fixture / test

- fixture
  - `tests/fixtures/jobkorea_company_page_super_neonutra_01.html`
    - source: `log/page_diagnostics/20260315_060327_회사_페이지.html`

- tests
  - `tests/test_parser.py`
    - live 슈퍼기업관 fixture 회귀 테스트 추가
  - `tests/test_crawler.py`
    - failure diagnostic metadata에 wait locator / timeout 여부가 기록되는지 검증
  - `tests/test_main.py`
    - `run_phase2_for_companies()` 결과에 redirected final URL/title이 포함되는지 검증
  - `tests/test_phase2_smoke_test.py`
    - smoke script가 `--company-id`를 후보 선택기에 전달하는지 검증

## 5. 검증 결과

- `python -m py_compile crawler.py main.py scripts/phase2_smoke_test.py tests/test_crawler.py tests/test_parser.py tests/test_main.py tests/test_phase2_smoke_test.py`
- `pytest tests/test_crawler.py tests/test_parser.py tests/test_main.py tests/test_phase2_smoke_test.py -q` -> `37 passed`
- `pytest tests/ -q` -> `110 passed`
- live rerun
  - `venv/bin/python scripts/phase2_smoke_test.py --limit 1 --headless true`
  - 결과:
    - 현재 기본 후보는 `한영회계법인 (id=59)`
    - final URL: `https://www.jobkorea.co.kr/Company/16151846/Info?utm_source=&utm_medium=&utm_campaign=`
    - title: `한영회계법인의 기업정보`
    - status: `updated`
    - wait_timed_out: `no`
  - `venv/bin/python scripts/phase2_smoke_test.py --limit 1 --company-id 58 --headless true`
  - 결과:
    - 대상: `네오뉴트라 (id=58)`
    - stored `company_page_url` 재사용
    - final URL: `https://www.jobkorea.co.kr/Super/neonutra`
    - title: `네오뉴트라 슈퍼기업관 - 일하기 좋은 우수 기업 | 잡코리아`
    - status: `updated`
    - wait_timed_out: `no`
  - `venv/bin/python scripts/phase2_smoke_test.py --limit 5 --headless true`
  - 결과:
    - 대상 5건 모두 `updated`
    - cached 재사용 1건(`id=59`) + JD 출발 4건(`id=63~66`) 모두 timeout 없이 완료
    - 모든 결과에서 `wait_timed_out: no`
    - 추가 timeout 재현 없음

## 6. 수정한 파일

- `crawler.py`
- `main.py`
- `scripts/phase2_smoke_test.py`
- `tests/test_crawler.py`
- `tests/test_main.py`
- `tests/test_parser.py`
- `tests/test_phase2_smoke_test.py`
- `tests/fixtures/jobkorea_company_page_super_neonutra_01.html`
- `docs/reports/phase2_live_timeout_diagnosis_report.md`
- `docs/status/current_status.md`
- `docs/status/session_handoff.md`
- `docs/architecture/system_architecture.md`

## 7. 남은 리스크

- 2026-03-15 earlier artifact에는 같은 URL의 timeout이 남아 있지만, current live rerun과 5건 mixed smoke sample에서는 재현되지 않았다. 즉, redirect 완료 타이밍에 따른 간헐 이슈 가능성은 줄었지만 아직 완전히 배제되지는 않는다.
- 현재 기본 Phase 2 대상 선택은 `company_size IS NULL` 기준이라, `네오뉴트라(id=58)`처럼 일부 필드만 비어 있는 회사는 일반 배치 대상에서 빠질 수 있다.
- 저장된 `company_page_url` 자체가 stale할 때 JD로 재해결하는 fallback은 여전히 없다.

## 8. 다음 권장 작업

1. Phase 2 대상 선택 기준을 `company_size` 단일 필드가 아니라 실제 missing detail 집합 기준으로 넓힐지 판단한다.
2. `Super` 회사 페이지 fixture를 더 확보해 redirect/layout variation 회귀 범위를 넓힌다.
3. 같은 URL의 간헐 timeout이 다시 보이면 현재 저장되는 HTML/meta artifact를 기준으로 retry timing 문제인지 다시 분리한다.
