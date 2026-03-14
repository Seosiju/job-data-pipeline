# Phase 2 회사 페이지 전환 구현 리뷰 (Historical Snapshot)

> 작성일: 2026-03-14
> 기준: 현재 워킹트리, Phase 2 구현 결과, 관련 테스트 재검증
> 목적: Phase 2 회사 페이지 전환 구현이 실제로 반영되었는지 검토하고, 남은 리스크를 기록한다.

## 1. 결론

Phase 2의 메인 오케스트레이션은 실제로 수정되었다.

현재 `run_phase2()`는 더 이상 `job_postings.detail_url`의 JD HTML을 곧바로 회사 정보 파서에 넣지 않는다. 대신 아래 흐름으로 동작한다.

```text
job_detail_url
  -> crawl_job_detail_page(job_detail_url)
  -> parse_company_page_url_from_job_detail(job_detail_html)
  -> crawl_company_page(company_page_url)
  -> parse_company_detail(company_html)
  -> validate_company_details(details)
  -> update_company_details(company_id, details)
```

즉, 이번 변경의 핵심 목표였던 `JD 상세 -> 회사 페이지 링크 추출 -> 회사 페이지 방문 -> 회사 정보 파싱` 경로는 구현되었다.

## 2. 확인된 구현 사항

### 2.1 `main.py`

- `run_phase2()`가 JD 상세 페이지를 먼저 방문한다.
- JD HTML에서 회사 페이지 URL을 추출한다.
- 회사 페이지 URL이 없으면 회사 페이지 방문 없이 스킵한다.
- 회사 페이지 HTML에 대해서만 `parse_company_detail()`을 호출한다.

### 2.2 `parser.py`

- `parse_company_page_url_from_job_detail()`가 JD 상세 fixture에서 회사 페이지 URL을 추출한다.
- `parse_company_detail()`는 JD 페이지와 회사 페이지를 구분한다.
- 회사 페이지에서는 `table.table-basic-infomation-primary`의 다중 `th/td` 쌍을 읽어 핵심 필드를 파싱한다.
- JD HTML이 들어오면 회사 상세 필드를 빈 값으로 반환한다.

### 2.3 테스트

- JD fixture에서 회사 페이지 URL 추출 테스트가 추가되었다.
- 회사 페이지 fixture에서 `company_size`, `employee_count`, `establishment_year`, `homepage_url` 파싱 테스트가 추가되었다.
- `run_phase2()`가 JD -> 회사 페이지 순서를 따르는지 검증하는 흐름 테스트가 추가되었다.
- JD에서 회사 페이지 링크를 찾지 못할 때 회사 페이지 방문 없이 스킵하는 테스트가 추가되었다.

## 3. 리뷰 Findings

### Medium

`scripts/analyze_detail_page.py`는 아직 새 Phase 2 흐름을 반영하지 못했다.

- 이 스크립트는 DB에서 `job_postings.detail_url`을 가져온다.
- 현재 그 값의 의미는 JD 상세 URL이다.
- 그런데 스크립트는 그 URL을 `crawler.crawl_detail_page(detail_url)`에 넘긴다.
- 현재 `crawl_detail_page()`는 하위 호환 래퍼로 `crawl_company_page()`를 호출한다.

즉, 메인 파이프라인은 맞게 고쳐졌지만 보조 분석 스크립트는 여전히 "JD URL을 회사 페이지 크롤러에 넘기는" 의미 불일치 상태다.

이 문제는 운영 메인 경로를 깨는 수준은 아니지만, 수동 디버깅과 구조 분석에는 잘못된 신호를 줄 수 있다.

## 4. 검증 기록

실행한 검증:

- `python3 -m py_compile main.py crawler.py parser.py database.py validators.py tests/test_parser.py tests/test_main.py`
- `pytest tests/test_parser.py tests/test_main.py -q` -> `25 passed`
- `pytest tests/ -q` -> `91 passed`

직접 확인한 동작:

- JD fixture에서 회사 페이지 URL 추출 성공
- JD fixture를 `parse_company_detail()`에 넣으면 빈 결과 반환
- 회사 페이지 fixture를 `parse_company_detail()`에 넣으면 핵심 4개 필드 추출 성공

## 5. 남은 리스크

- `company_page_url`를 DB에 저장하지 않아서, 이후 실행에서도 JD를 다시 열어 회사 페이지 링크를 재추출해야 한다.
- JD에서 회사 페이지 URL을 못 찾을 때의 마지막 fallback은 현재 `dimension47` 기반이다. live DOM이 바뀌면 추가 보강이 필요할 수 있다.
- 회사 페이지 selector와 JD selector는 현재 fixture 중심으로 검증돼 있다. 다른 레이아웃 변형 샘플이 추가되면 회귀 테스트를 넓혀야 한다.
- `scripts/analyze_detail_page.py`는 새 흐름에 맞춰 정리하지 않으면 계속 오해를 만들 수 있다.

## 6. 권장 후속 작업

1. `scripts/analyze_detail_page.py`를 `crawl_job_detail_page()` 기준으로 고치거나, 회사 페이지 분석용 별도 입력 경로로 분리한다.
2. `companies.company_page_url` 저장 여부를 결정한다.
3. JD 상세 / 회사 페이지 fixture를 더 확보해 selector 회귀 범위를 넓힌다.
4. README와 현재 상태 문서에서 Phase 2를 "미구현"으로 설명하는 낡은 문구를 제거한다.
