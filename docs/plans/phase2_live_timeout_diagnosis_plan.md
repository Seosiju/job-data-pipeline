---
type: plan
status: active
last_reviewed: 2026-03-15
superseded_by:
related_report: docs/reports/phase2_live_smoke_validation_report.md
source_of_truth: true
---

# Phase 2 Live Timeout Diagnosis Plan

> 작성일: 2026-03-15
> 목적: cached `company_page_url` 경로에서 재현된 회사 페이지 로딩 timeout의 원인을 분리하고, 후속 수정이 가능한 증거를 남긴다.
> 범위: Phase 2 회사 페이지 로더 진단, 실패 HTML/최종 URL 수집, fixture화, 회귀 테스트 보강

## 1. 배경

- `scripts/phase2_smoke_test.py --limit 1 --headless true` 기준으로 `company_page_url` 재사용까지는 확인됐다.
- 하지만 실제 회사 페이지 로딩은 timeout으로 실패했다.
- 현재 문제는 DB나 Phase 2 오케스트레이션이 아니라, live company page loader가 일부 회사 페이지에서 기대 selector를 기다리다 실패하는 것이다.

관련 결과 문서:

- `docs/reports/phase2_live_smoke_validation_report.md`
- `docs/reports/phase2_followup_stabilization_report.md`

## 2. 목표

이 배치의 목표는 새 기능 추가가 아니다.

1. timeout이 selector 문제인지, 차단/리다이렉트인지, 레이아웃 변형인지 분리한다.
2. 실패 시 최종 URL, title, page source 같은 진단 정보를 남긴다.
3. 재현된 실패 HTML을 fixture로 저장하고 자동 테스트로 고정한다.
4. 필요한 경우에만 `crawl_company_page()` selector 또는 fallback을 수정한다.

## 3. 작업 범위

포함:

- `crawl_company_page()` 실패 진단 보강
- `scripts/phase2_smoke_test.py` 기반 재현
- 실패 HTML/메타데이터 수집
- fixture 추가
- parser/crawler/page-type detection 회귀 테스트 보강

제외:

- 스케줄러 자동화
- API/프론트엔드
- 새로운 분석 기능
- 대규모 리팩토링

## 4. 읽어야 할 문서

작업 시작 전 최소 문서:

1. `AGENTS.md`
2. `README.md`
3. `docs/status/current_status.md`
4. `docs/architecture/system_architecture.md`
5. `docs/plans/data_pipeline_service_roadmap.md`
6. `docs/reports/phase2_live_smoke_validation_report.md`

필요 시 추가 문서:

- `docs/architecture/jobkorea_company_page_structure.md`
- `docs/architecture/jobkorea_jd_detail_page_structure.md`
- `docs/reports/phase2_followup_stabilization_report.md`

## 5. 단계별 실행 순서

### Step 1. 실패 진단 정보 추가

대상 파일:

- `crawler.py`
- 필요 시 `config.py`

해야 할 일:

- `crawl_company_page()` 실패 시 아래를 남긴다.
  - 시도한 URL
  - 최종 URL
  - 페이지 title
  - selector wait 실패 여부
  - page source 저장 경로
- 진단 HTML은 임시/로그 디렉터리에 남기고, 경로를 로그에 출력한다.

### Step 2. smoke test로 실제 실패 재현

대상 파일:

- `scripts/phase2_smoke_test.py`

해야 할 일:

- `--limit 1` 기준으로 실패 사례를 재현한다.
- 실패 회사 ID, 회사명, `company_page_url`, 최종 URL, title을 기록한다.

### Step 3. 실패 원인 분리

판단 기준:

- 회사 페이지 본문은 보이는데 selector만 못 잡으면 selector/fallback 문제
- 로그인/차단/에러/빈 화면이면 anti-bot 또는 리다이렉트 문제
- 완전히 다른 레이아웃이면 새 fixture와 page-type handling 필요

### Step 4. fixture와 테스트 고정

대상 파일:

- `tests/fixtures/...`
- `tests/test_crawler.py`
- `tests/test_parser.py`

해야 할 일:

- 실제 실패 HTML을 fixture로 저장한다.
- 진단된 원인에 맞춰 회귀 테스트를 추가한다.
- selector 수정이 있었다면 해당 fixture로 재발 방지 테스트를 넣는다.

### Step 5. 최소 수정 반영

원인 분리 후 필요한 경우에만:

- `crawl_company_page()` wait selector 확장
- page-type detection 보강
- cached `company_page_url` 실패 시 다음 단계 fallback 설계 초안 작성

## 6. 완료 기준

아래가 모두 만족되면 이 배치는 완료다.

1. live timeout 실패 시 최종 URL/title/page source를 확보할 수 있다.
2. 실패 원인이 `selector`, `layout drift`, `redirect`, `anti-bot` 중 어디인지 설명 가능하다.
3. 실패 HTML 또는 유사 케이스가 fixture로 저장된다.
4. 관련 자동 테스트가 추가된다.
5. 수정이 있었다면 `pytest tests/ -q`가 통과한다.
6. 결과가 `docs/reports/`에 별도 보고서로 남는다.

## 7. 작업 후 문서화

반드시 갱신할 문서:

- `docs/reports/<task>_report.md`
- `docs/status/current_status.md`
- `docs/status/session_handoff.md`

조건부 갱신:

- 런타임 동작이 바뀌면 `docs/architecture/system_architecture.md`
- active 우선순위가 바뀌면 `docs/plans/data_pipeline_service_roadmap.md`

## 8. 권장 보고서 파일명

- `docs/reports/phase2_live_timeout_diagnosis_report.md`

보고서에는 최소한 아래를 포함한다.

- 한 줄 요약
- 실제 원인 분류
- 수정한 파일
- 추가한 fixture/test
- 검증 결과
- 남은 리스크
- 다음 권장 작업
