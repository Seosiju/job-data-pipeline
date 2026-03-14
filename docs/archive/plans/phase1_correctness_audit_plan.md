---
type: plan
status: historical
last_reviewed: 2026-03-14
superseded_by: docs/plans/data_pipeline_service_roadmap.md
related_report: docs/reports/phase1_correctness_audit_report.md
source_of_truth: false
---

# Phase 1 검색 결과 파서 정확성 감사 실행 문서 (Historical Snapshot)

> 작성일: 2026-03-14
> 목적: 다른 에이전트가 바로 Phase 1 검색 결과 파서 정확성 검증과 필요한 수정 작업에 착수할 수 있게 하는 handoff 문서
> 성격: historical snapshot
> 결과: `docs/reports/phase1_correctness_audit_report.md`

## 0. 현재 관점에서 보면

이 감사는 이미 실행되었고, 핵심 수정과 검증 결과는 `docs/reports/phase1_correctness_audit_report.md`에 기록돼 있습니다.

따라서 이 문서는 현재 active plan이 아니라, 당시 어떤 facts와 범위로 감사가 진행됐는지 보여주는 기록 문서입니다.

## 1. 한 줄 요약

현재 Phase 1은 검색 결과 메인 목록만 읽어야 하지만, 실제 구현은 전역 `CardJob`를 순회하고 있다. 따라서 "메인 목록 외 카드가 섞여 저장되는지"를 우선 검증하고, fixture 기반 테스트와 selector 보정을 통해 검색 결과 파서를 신뢰 가능한 상태로 만들어야 한다.

## 2. 문제 배경

이 프로젝트의 전체 데이터 파이프라인은 Phase 1 결과를 기반으로 움직인다.

- `job_postings`
- `companies`
- Phase 2 회사 정보 보강 대상 선택
- 향후 운영 지표, 분석 레이어, API, 대시보드

따라서 Phase 1이 잘못 수집하면 이후 단계도 연쇄적으로 오염된다.

현재 우려는 "사이트 구조를 충분히 이해하지 못한 상태에서 검색 결과 파서가 구현되었을 수 있다"는 점이며, 이 우려는 이미 일부 사실로 확인됐다.

## 3. 현재 확인된 사실

### 3.1 fixture 기준 카드 수

기준 샘플:

- `tests/fixtures/jobkorea_search_page_02.html`

확인 사실:

- 페이지 전체 전역 `CardJob`: `27`
- 메인 목록 `JobList` 내부 `CardJob`: `20`

즉, 검색 결과 페이지 전체에서 전역 `CardJob`를 읽으면 메인 목록 외 카드가 섞일 수 있다.

### 3.2 현재 구현

현재 [parser.py](../../parser.py)의 `parse_job_cards()`는 아래 방식으로 카드를 찾는다.

```python
cards = soup.find_all("div", attrs={"data-sentry-component": "CardJob"})
```

이 구현은 `JobList` 스코프를 사용하지 않는다.

### 3.3 링크 구조 검증 facts

기준 샘플의 메인 `20`개 카드에서 확인한 사실:

- 각 카드에는 보통 JD로 가는 링크가 3개 내외 존재한다.
- 회사 로고 링크, 제목 링크, 회사명 링크는 모두 같은 `GI_Read` JD URL로 향한다.
- 카드 단위로 보면 `a[href*="/Recruit/GI_Read/"]`의 고유 `href`는 `1`개다.

즉, 검색 결과 카드에서 회사명 클릭은 회사 페이지가 아니라 JD 상세 페이지로 이동한다.

### 3.4 selector 검증 facts

기준 문서:

- `docs/architecture/jobkorea_search_results_page_structure.md`

fixture 기준으로 확인된 핵심 facts:

- 메인 목록 컨테이너: `[data-sentry-component="JobList"]`
- 카드 스코프: `[data-sentry-component="JobList"] [data-sentry-component="CardJob"]`
- 제목: `a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size18"]`
- 회사명: `a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size16"]`
- 위치 chip: `[data-sentry-component="GrayChip"] .emoji--basicemoji-place2`
- 업종/직무 chip: `[data-sentry-component="GrayChip"] .emoji--basicemoji-briefcase`
- 페이지네이션: `[data-sentry-component="Pagination"] a[href*="Page_No="]`

### 3.5 첫 카드 샘플 facts

기준 샘플 첫 카드에서 확인한 값:

- 회사명: `킨코스코리아㈜`
- 위치 chip: `서울 금천구 외 3`
- 업종/직무 chip: `출판·인쇄·사진, 경영·비즈니스기획, 채널관리자, 제품디자이너`

### 3.6 페이지네이션 facts

기준 샘플에서 확인한 값:

- `Prev`, `1..10`, `Next` 링크 존재
- 첫 그룹 기준 `Prev=Page_No=0`
- 첫 그룹 기준 `Next=Page_No=11`

## 4. 이번 감사의 범위

이번 작업의 범위는 Phase 1 검색 결과 페이지 파서의 정확성 검증과 필요한 보정이다.

포함:

- 검색 결과 페이지 fixture와 현재 parser 비교
- `parse_job_cards()` 스코프 검증
- 제목, 회사명, JD URL, 위치, 업종/직무, 급여, 지원방식 selector 검증
- 메인 목록 카드 수 검증
- 필요한 테스트 추가
- 필요 시 parser 수정

제외:

- Phase 2 회사 페이지 전환 수정
- 회사 페이지 파서 수정
- DB 스키마 변경
- API/프론트엔드 작업
- 장기 로드맵 문서 개편

## 5. 작업 목표

이번 감사의 목표는 아래 세 가지다.

1. 현재 Phase 1이 실제로 무엇을 잘못 읽고 있는지 확정한다.
2. fixture 기반 자동 테스트로 검색 결과 파서의 기본 정확도를 고정한다.
3. 메인 목록 기준으로 신뢰 가능한 최소 selector 세트를 코드에 반영한다.

## 6. 단계별 작업

### Step 1. 기준 문서와 fixture 재확인

반드시 먼저 읽을 것:

1. `docs/architecture/jobkorea_search_results_page_structure.md`
2. `tests/fixtures/jobkorea_search_page_02.html`
3. `parser.py`
4. `tests/test_parser.py`

목적:

- 현재 코드가 fixture 기준으로 어디서 어긋나는지 명확히 잡는다.

### Step 2. 실패하는 기대를 테스트로 고정

우선 추가할 테스트:

- 전역 `CardJob`는 `27`개지만 메인 목록 파서는 `20`개만 반환해야 한다.
- 카드 1개에서 JD URL, 제목, 회사명이 추출되어야 한다.
- 위치 chip과 briefcase chip이 분리되어야 한다.
- 급여 chip이 있는 카드와 없는 카드 모두 처리되어야 한다.
- `즉시 지원` / `홈페이지 지원`이 버튼 텍스트 기준으로 읽혀야 한다.
- 결과 수 불일치(`8,515` vs `8,513`)가 있어도 카드 파싱은 정상 동작해야 한다.

테스트의 목적은 "현재 selector가 어떤 구조를 기준으로 안정적이라고 볼 수 있는지"를 먼저 고정하는 것이다.

### Step 3. parser 보정

우선 검토 대상 함수:

- `parse_job_cards()`
- `_extract_title()`
- `_extract_company()`
- `_extract_detail_url()`
- `_extract_location()`
- `_extract_industry()`
- `_extract_job_category()`
- `_extract_salary()`
- `_extract_apply_type()`

권장 변경 방향:

- `parse_job_cards()`는 먼저 `JobList` 컨테이너를 찾고, 그 안에서만 `CardJob`를 순회
- 제목/회사명은 typography 크기만 보지 말고 `GI_Read` anchor 내부에서 찾도록 스코프 강화
- `apply_type`은 해시 클래스가 아니라 버튼 텍스트 기반으로 추출
- `GrayChip` 기반 필드는 현재 아이콘 기반 전략을 유지하되 카드 스코프를 더 엄격히 제한

### Step 4. 회귀 검증

최소 검증:

- `pytest tests/test_parser.py -q`
- 필요 시 `pytest tests/ -q`

가능하면 검증 후 확인할 것:

- 검색 결과 fixture 기준 기대 카드 수가 유지되는지
- 새 selector가 기존 회사/JD 상세 파서에 불필요한 영향을 주지 않는지

### Step 5. 결과 기록

감사 결과가 끝나면 최소 아래를 남긴다.

- 무엇이 실제로 잘못되어 있었는지
- 어떤 selector/함수 경계를 수정했는지
- 어떤 테스트로 고정했는지
- 아직 남은 애매한 구간이 무엇인지

## 7. 완료 기준

아래 조건을 모두 만족해야 이번 감사가 끝난 것으로 본다.

- 메인 검색 결과 fixture 기준 파서 반환 카드 수가 `20`개로 고정된다.
- 전역 `CardJob` 과수집 문제가 테스트로 재발하지 않게 막힌다.
- JD URL, 제목, 회사명, 위치, 업종/직무, 지원방식의 최소 추출 정확도가 fixture 기준으로 검증된다.
- 테스트가 추가되고 통과한다.
- 변경 결과를 다른 에이전트가 바로 이해할 수 있도록 코드/테스트가 충분히 읽힌다.

## 8. 테스트와 fixture 사용법

주요 파일:

- `tests/fixtures/jobkorea_search_page_02.html`
- `tests/test_parser.py`

추천 절차:

1. fixture를 기준으로 selector를 먼저 확정
2. fixture 기반 테스트를 추가
3. parser를 수정
4. parser 테스트를 재실행

핵심 원칙:

- live 사이트 확인보다 fixture 기준 자동 테스트를 먼저 신뢰한다.
- fixture가 표현하는 것은 "현재 저장 시점의 실샘플"이므로, 여기서 통과하지 못하면 현재 코드 정확성을 주장할 수 없다.

## 9. 주의사항

- 기존 dirty worktree를 되돌리지 않는다.
- unrelated file은 건드리지 않는다.
- `Phase 1 audit`인데 Phase 2 설계 문제를 같이 해결하려고 범위를 키우지 않는다.
- `_files/` 상대경로, 해시 클래스, 칩 위치 순서 같은 brittle 규칙에 의존하지 않는다.
- 문서에 없는 가정을 코드에 바로 넣지 말고, fixture나 테스트로 먼저 증명한다.

## 10. Out Of Scope

이번 작업에서 하지 말아야 할 것:

- `companies` 스키마 변경
- `company_page_url` 컬럼 추가
- 회사 페이지 파서 구현
- 스케줄러 등록
- 운영 대시보드/API 구현
- 장기 서비스 로드맵 수정

## 11. 시작 체크리스트

다음 에이전트는 아래 순서로 시작하면 된다.

1. `docs/architecture/jobkorea_search_results_page_structure.md` 읽기
2. `tests/fixtures/jobkorea_search_page_02.html` 확인
3. `parser.py`의 `parse_job_cards()`와 필드 extractor 확인
4. `tests/test_parser.py`에 실패하는 기대를 먼저 추가
5. parser 수정
6. parser 테스트 실행

이 문서의 목적은 "계획 논의"가 아니라 "즉시 실행"이다. 다음 작업자는 Phase 1 검색 결과 파서 정확성 검증만 집중해서 끝내면 된다.
