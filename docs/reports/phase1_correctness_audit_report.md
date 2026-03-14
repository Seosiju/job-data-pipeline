# Phase 1 검색 결과 파서 정확성 감사 보고서 (Historical Snapshot)

> 작성일: 2026-03-14
> 상태: Historical snapshot
> 실행 기준 문서: `docs/archive/plans/phase1_correctness_audit_plan.md`
> 이 문서는 2026-03-14 시점 감사 결과와 검증 결과를 정리한 완료 보고서입니다.
> 현재 동작의 source of truth는 `parser.py`, `tests/test_parser.py`, `docs/architecture/jobkorea_search_results_page_structure.md` 입니다.

---

## 한 줄 요약

Phase 1 검색 결과 파서는 전역 `CardJob` 과수집으로 메인 목록 20개 대신 27개를 읽고 있었고, 이를 `JobList -> CardJob` 스코프로 보정한 뒤 fixture 기반 테스트로 재발을 막았습니다.

---

## 감사 범위

포함:

- `parse_job_cards()` 스코프 검증
- JD URL, 제목, 회사명, 위치, 업종/직무, 급여, 지원방식 selector 검증
- 메인 목록 카드 수 검증
- 관련 테스트 추가/수정

제외:

- Phase 2 회사 페이지 전환
- DB 스키마 변경
- API/프론트엔드 작업

---

## 실제로 잘못되어 있던 점

### 1. 메인 목록 외 카드 과수집

fixture `tests/fixtures/jobkorea_search_page_02.html` 기준:

- 페이지 전체 전역 `CardJob`: `27`
- 메인 목록 `JobList` 내부 `CardJob`: `20`

기존 `parse_job_cards()`는 전역 `CardJob`를 순회하고 있었기 때문에, 실제 검색 결과 메인 목록보다 앞에 렌더링된 다른 카드가 먼저 파싱되었습니다.

이 영향으로 기존 parser의 첫 반환값은 아래처럼 메인 목록 첫 카드가 아니었습니다.

- 잘못 읽힌 첫 카드 회사명: `일양㈜`
- 잘못 읽힌 첫 카드 제목: `기본급 350만(차등지급) 부동산 직원 모집 - 주5일 오전10시-오후3시`

하지만 메인 목록의 실제 첫 카드는 아래였습니다.

- 회사명: `킨코스코리아㈜`
- 제목: `킨코스코리아㈜ 영업부문 사업기획팀/영업직/디자인그룹 경력 및 신입사원 모집`

### 2. 지원방식 추출의 brittle selector

기존 `_extract_apply_type()`은 해시 클래스에 의존하고 있었습니다.

- 해시 클래스: 구조 변경에 취약
- 요구사항: `즉시 지원`, `홈페이지 지원`을 버튼 텍스트 기준으로 읽어야 함

현재 fixture에서는 일부 카드에서 우연히 동작했지만, 안정적인 기준으로 보기 어려웠습니다.

### 3. 테스트 기준이 현재 fixture를 고정하지 못함

기존 `tests/test_parser.py`는 삭제된 `sample_list.html`, `sample_detail.html`에 의존하고 있었고, 실제 Phase 1 fixture 기준 기대값을 고정하지 못하고 있었습니다.

즉, 정확성 감사 자체를 자동화로 재현할 수 없는 상태였습니다.

---

## 수정 내용

### 1. parser 보정

수정 파일: `parser.py`

- `parse_job_cards()`가 먼저 `JobList` 컨테이너를 찾고, 그 안에서만 `CardJob`를 순회하도록 변경
- `JobList`가 없을 때만 전역 `CardJob`로 폴백하도록 제한
- 제목/회사명 selector를 `GI_Read` anchor 내부 typography로 강화
- JD URL 추출을 카드 내부 `GI_Read` anchor 기준으로 정리
- 위치/업종/직무/급여는 `GrayChip` + 아이콘 기준 helper로 정리
- 지원방식은 `BaseButton` 텍스트를 읽어서 `즉시 지원` / `홈페이지 지원`으로 추출하도록 변경

### 2. 테스트 보강

수정 파일: `tests/test_parser.py`

- 현재 fixture `jobkorea_search_page_02.html` 기반 테스트로 교체
- 실패 기대를 먼저 고정한 뒤 parser 보정
- 아래 항목을 자동 테스트로 고정
  - `JobList -> CardJob` 스코프
  - JD URL / 제목 / 회사명
  - 위치 / 업종 / 직무 분리
  - 급여 chip 있음 / 없음
  - `즉시 지원` / `홈페이지 지원`
  - `8,515` vs `8,513` 결과 수 불일치가 있어도 카드 파싱 정상 동작

---

## 검증한 핵심 기대값

| 항목 | fixture 기준 기대값 | 결과 |
|------|---------------------|------|
| 메인 목록 카드 수 | `20` | 통과 |
| 전체 전역 카드 수 | `27` | 통과 |
| 첫 카드 회사명 | `킨코스코리아㈜` | 통과 |
| 첫 카드 제목 | `킨코스코리아㈜ 영업부문 사업기획팀/영업직/디자인그룹 경력 및 신입사원 모집` | 통과 |
| 첫 카드 위치 | `서울 금천구 외 3` | 통과 |
| 첫 카드 업종 | `출판·인쇄·사진` | 통과 |
| 첫 카드 직무 | `경영·비즈니스기획, 채널관리자, 제품디자이너` | 통과 |
| 급여 chip 있는 카드 | `사업기획 및 연구지원` -> `연봉 4,000~6,000만원` | 통과 |
| 지원방식 1 | 첫 카드 `즉시 지원` | 통과 |
| 지원방식 2 | 둘째 카드 `홈페이지 지원` | 통과 |
| 결과 수 불일치 | `8,515`와 `8,513`이 함께 있어도 카드 파싱 `20`개 유지 | 통과 |

---

## 테스트 실행 기록

### 1. failing expectation 고정 후 1차 실행

`tests/test_parser.py`를 현재 fixture 기준 기대값으로 먼저 수정한 뒤 실행했습니다.

결과:

- `pytest tests/test_parser.py -q`
- `5 failed, 13 passed`

실패 원인 요약:

- parser 반환 카드 수가 `27`개였음
- 첫 카드 기준 JD URL, 제목, 위치가 메인 목록 기준값과 맞지 않았음
- 둘째 카드 지원방식도 메인 목록 기준과 어긋났음

즉, 테스트가 의도대로 기존 과수집 문제를 먼저 잡아냈습니다.

### 2. parser 보정 후 재실행

- `pytest tests/test_parser.py -q` -> `18 passed`
- `pytest tests/ -q` -> `86 passed`

---

## 변경 파일

- `parser.py`
- `tests/test_parser.py`

---

## 남은 리스크

- 현재 감사는 저장된 검색 결과 fixture 1개 기준이다. 다른 키워드나 다른 날짜 저장본에서도 같은 구조가 유지되는지 추가 fixture가 더 필요하다.
- `JobList`를 찾지 못할 때 전역 `CardJob`로 폴백하는 경로는 남아 있다. 비정상 HTML 대응용이지만, live DOM이 크게 바뀌면 다시 과수집 위험이 생길 수 있다.
- `apply_type`은 현재 확인된 `즉시 지원`, `홈페이지 지원` 중심으로 처리한다. 다른 버튼 라벨이 등장하면 추가 검증이 필요하다.

---

## 참고 문서

- `docs/archive/plans/phase1_correctness_audit_plan.md`
- `docs/architecture/jobkorea_search_results_page_structure.md`
- `tests/fixtures/jobkorea_search_page_02.html`
