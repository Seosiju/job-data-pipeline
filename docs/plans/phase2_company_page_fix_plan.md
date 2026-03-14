# Phase 2 회사 페이지 전환 수정 기획서

> 작성일: 2026-03-14
> 기준: 현재 워킹트리, `log/crawler.log`, `log/error.log`
> 목적: 다른 에이전트가 현재 Phase 2 장애와 수정 방향을 바로 이해하고 이어서 구현할 수 있게 정리한 문서

## 1. 한 줄 요약

현재 Phase 2는 "회사 정보가 있는 회사 페이지"가 아니라 `job_postings.detail_url`에 저장된 JD 상세 페이지를 직접 파싱하려고 한다. 인간 기준 기대 동선인 `JD 상세 -> 회사명 클릭 -> 회사 페이지 -> 회사 정보 추출`이 코드에 구현되어 있지 않다.

## 2. 기대 동작과 실제 동작

### 기대 동작

사용자 관점에서 회사 정보 수집 흐름은 아래와 같다.

1. 목록에서 공고를 찾는다.
2. JD 상세 페이지로 들어간다.
3. JD 상세 페이지에서 회사명을 클릭한다.
4. 회사 전용 페이지로 이동한다.
5. 회사 페이지에서 `company_size`, `employee_count`, `establishment_year`, `homepage_url` 등을 읽는다.

### 현재 실제 동작

현재 구현은 아래 흐름으로 동작한다.

1. Phase 1에서 목록 카드의 `/Recruit/GI_Read/...` 링크를 `detail_url`로 저장한다.
2. Phase 2에서 `companies`와 조인된 최신 `job_postings.detail_url`을 그대로 가져온다.
3. 그 URL을 `crawl_detail_page()`로 연다.
4. 열린 HTML에서 곧바로 `parse_company_detail()`을 실행한다.
5. 파싱 결과가 있으면 `companies`를 업데이트한다.

즉 현재 코드는:

```text
목록 -> JD 상세 페이지 -> JD HTML에서 회사 정보 직접 추출 시도
```

이고, 아직 구현되지 않은 기대 흐름은:

```text
목록 -> JD 상세 페이지 -> 회사 페이지 링크 추출 -> 회사 페이지 접속 -> 회사 정보 추출
```

이다.

## 3. 현재 장애 증상

2026-03-14 기준 로그에서 확인된 상태는 다음과 같다.

- 16:31:24 첫 실행은 DB 접속 실패로 종료
  - 원인: `localhost:5433` 연결 거부
- 17:22:43 이후 실행은 DB 연결 성공
- Phase 1은 3개 키워드 기준 정상 완료
  - 신규 331건
  - 변경 12건
  - 실패 0건
- Phase 2는 `758개 회사`를 대상으로 시작
- 이후 `상세 페이지 로딩 실패`가 반복되고 `상세 페이지 크롤링 에러`가 누적됨
- `Phase 2 완료` 로그는 없음

현재 로그 기준 추가 징후:

- `상세 페이지 로딩 실패` 17회
- `상세 페이지 크롤링 에러` 5회
- `연속 실패 감지 - 쿨다운 적용` 2회
- 로그가 실행 단위로 분리되지 않고 같은 파일에 누적되어 troubleshooting 난도가 올라감

이 로그 패턴은 "DB 문제"보다 "Phase 2 페이지 해석/접속 방식 문제"가 현재의 핵심 병목이라는 뜻이다.

## 4. 현재 코드 경로

### 4.1 Phase 1 URL 저장 경로

[parser.py](../../parser.py)의 `_extract_detail_url()`은 목록 카드에서 `/Recruit/GI_Read/...` 링크를 추출한다.

```text
CardJob
  -> a[href*="/Recruit/GI_Read/"]
  -> job_postings.detail_url 저장
```

이 URL은 공고 상세 URL이다. 회사 페이지 URL이 아니다.

### 4.2 Phase 2 대상 조회 경로

[database.py](../../database.py)의 `get_companies_without_details()`는 아래 조건으로 대상 회사를 뽑는다.

- `companies.company_size IS NULL`
- `job_postings.detail_url IS NOT NULL`
- 회사당 최신 `detail_url` 1개 선택

즉 Phase 2 입력은 현재도 회사 페이지 URL이 아니라 JD 상세 URL이다.

### 4.3 Phase 2 실행 경로

[main.py](../../main.py)의 `run_phase2()`는 DB에서 가져온 `detail_url`을 그대로 `crawler.crawl_detail_page(detail_url)`에 전달한다.

이후 같은 HTML에 대해:

- `parse_company_detail(html)`
- `validate_company_details(details)`
- `db.update_company_details(company_id, details)`

를 수행한다.

### 4.4 현재 파싱 전제

[parser.py](../../parser.py)의 `parse_company_detail()`은 다음 필드를 추출하려고 시도한다.

- `company_size`
- `employee_count`
- `establishment_year`
- `homepage_url`

하지만 이 함수는 현재 "입력 HTML이 정말 회사 전용 페이지인가?"를 구분하지 않는다. JD 상세 HTML이 들어와도 그대로 회사 페이지로 간주하고 `dl`, `table`, 키워드 폴백을 시도한다.

## 5. 파일별 문제점

### [parser.py](../../parser.py)

문제:

- `_extract_detail_url()`이 공고 상세 URL만 저장한다.
- 회사 페이지 URL을 뽑는 함수가 없다.
- `parse_company_detail()`은 JD HTML과 회사 HTML을 구분하지 않는다.

영향:

- Phase 2가 잘못된 페이지 타입을 입력받아도 조용히 진행된다.
- 파싱 실패 원인이 "구조 변경"인지 "잘못된 페이지 방문"인지 로그만으로 구분하기 어렵다.

### [database.py](../../database.py)

문제:

- `get_companies_without_details()`가 JD URL만 반환한다.
- `companies` 테이블에 회사 페이지 URL을 저장할 컬럼이 없다.

영향:

- Phase 2가 매번 JD 기준으로 시작할 수밖에 없다.
- 회사 페이지 URL을 한 번 알아내도 재사용할 수 없다.

### [main.py](../../main.py)

문제:

- `run_phase2()`가 "JD -> 회사 페이지" 중간 단계를 갖고 있지 않다.
- `detail_url` 변수명이 JD URL인지 회사 URL인지 의미가 모호하다.

영향:

- 오케스트레이션 수준에서 설계 의도가 잘못 고정되어 있다.
- 사람이 읽으면 "상세 크롤링"이 회사 페이지 방문처럼 보이지만 실제로는 아니다.

### [crawler.py](../../crawler.py)

문제:

- `crawl_detail_page()`라는 이름이 JD 상세와 회사 상세를 구분하지 않는다.
- `wait_locator=(By.CSS_SELECTOR, '[class*="inner-wrap"], [class*="company-info"]')`가 현재 방문 페이지 타입에 따라 과도하게 모호하다.
- `_load_page_with_retry()` 내부에서 재시도마다 `consecutive_failures`가 증가한다.
- `crawl_detail_page()`의 `except`에서도 `consecutive_failures`를 한 번 더 증가시킨다.

영향:

- 페이지 단위 실패보다 더 빠르게 쿨다운이 걸린다.
- 실제 실패 원인이 셀렉터 미스인지, 페이지 차단인지, 리다이렉트인지 구분이 어렵다.
- JD와 회사 페이지의 대기 조건을 분리하기 어렵다.

### [scripts/analyze_detail_page.py](../../scripts/analyze_detail_page.py)

문제:

- 샘플 `detail_url`을 가져와 그 HTML만 분석한다.
- 현재 문제 정의 기준에서는 "회사 페이지 구조 분석"이 아니라 "JD 페이지 구조 분석"에 머무를 가능성이 크다.

영향:

- 수동 디버깅 방향 자체가 잘못될 수 있다.
- Phase 2 실패 원인을 재현해도 해결 방향으로 바로 이어지지 않는다.

### [config.py](../../config.py)

문제:

- 로그 파일이 실행 단위로 분리되지 않고 append 된다.

영향:

- 첫 번째 DB 실패와 두 번째 Phase 2 실패가 같은 로그 파일에 누적된다.
- 장애 타임라인을 읽을 때 세션 구분 비용이 크다.

이 문제는 Phase 2의 본질적인 기능 오류는 아니지만, 디버깅 생산성을 떨어뜨리는 운영 문제다.

## 6. 현재 구현이 왜 인간 기준 흐름과 어긋나는가

핵심 원인은 "Phase 2 입력 데이터"와 "Phase 2 목적 데이터"가 같은 페이지에 있다고 가정했기 때문이다.

- 입력 데이터: `job_postings.detail_url`
- 목적 데이터: 회사 전용 프로필 정보

이 둘은 실제 사이트에서 다른 페이지일 가능성이 높다. 사용자가 직접 확인한 동선도 `JD 상세 -> 회사명 클릭 -> 회사 페이지`이므로, 현재 구현의 전제가 사이트 UX와 맞지 않는다.

즉 현재 Phase 2 문제는 단순한 셀렉터 수정 이슈가 아니라, **페이지 타입을 잘못 잡은 설계 문제**다.

## 7. 권장 해결 방향

### 7.1 최소 수정안

가장 작은 수정으로 올바른 흐름을 구현하는 방법은 아래와 같다.

1. JD 상세 페이지를 연다.
2. JD HTML에서 회사 페이지 링크를 추출한다.
3. 회사 페이지 URL이 없으면 스킵하고 로그를 남긴다.
4. 회사 페이지를 연다.
5. 회사 페이지 HTML에서 회사 정보를 파싱한다.
6. `companies` 테이블을 업데이트한다.

목표 흐름:

```text
companies without details
  -> latest job_detail_url
  -> crawl_job_detail_page(job_detail_url)
  -> parse_company_page_url(job_detail_html)
  -> crawl_company_page(company_page_url)
  -> parse_company_page(company_html)
  -> validate_company_details(details)
  -> update companies
```

이 방식은 스키마 변경 없이도 당장 Phase 2의 의미를 바로잡을 수 있다.

### 7.2 권장 구조안

장기적으로는 회사 페이지 URL을 별도 필드로 저장하는 것이 낫다.

권장 변경:

- `companies.company_page_url` 컬럼 추가
- Phase 2에서 회사 페이지 URL을 발견하면 `companies`에 저장
- 이후 실행에서는 이미 저장된 `company_page_url`을 우선 사용
- 없을 때만 JD 상세로 돌아가 링크를 다시 찾음

권장 이유:

- 같은 회사를 처리할 때 매번 JD 페이지를 다시 열지 않아도 된다.
- Phase 2 데이터 흐름이 명확해진다.
- 변수명과 함수명을 페이지 타입 기준으로 분리할 수 있다.

### 7.3 네이밍 정리

현재 `detail_url`은 너무 많은 의미를 담고 있다. 아래처럼 의미를 분리하는 것이 좋다.

- `job_detail_url`: 공고 상세 URL (`/Recruit/GI_Read/...`)
- `company_page_url`: 회사 전용 페이지 URL
- `crawl_job_detail_page()`
- `crawl_company_page()`
- `parse_company_page_url_from_job_detail()`
- `parse_company_profile()`

이 네이밍 정리만 해도 Phase 2의 책임 경계가 훨씬 선명해진다.

## 8. 제안 구현 순서

### 1단계. 진짜 페이지 흐름부터 바로잡기

- `parser.py`
  - JD 상세 HTML에서 회사 페이지 링크를 뽑는 함수 추가
  - 회사 페이지 전용 파서 함수명 분리
- `crawler.py`
  - JD 상세 / 회사 페이지 크롤링 메서드 분리
- `main.py`
  - `run_phase2()`를 `JD -> 회사 페이지 -> 회사 정보 저장` 흐름으로 수정

### 2단계. DB 스키마 보강

- `companies.company_page_url` 추가
- `get_companies_without_details()`가 `company_page_url` 우선 사용하도록 개선
- 필요한 경우 `company_page_url_last_seen_at` 같은 추적 필드 검토

### 3단계. 실패 처리 개선

- `consecutive_failures`를 "재시도 횟수"가 아니라 "페이지 단위 최종 실패 수" 기준으로 관리
- `crawl_detail_page()` 쪽 이중 증가 제거
- 예외 타입과 현재 URL, 페이지 타입을 함께 로깅
- JD 페이지 실패와 회사 페이지 실패를 분리된 메시지로 기록

### 4단계. 수동 분석 도구 정리

- `scripts/analyze_detail_page.py`를 회사 페이지 기준 분석 도구로 바꾸거나 이름을 변경
- 가능하면 JD HTML과 회사 HTML을 둘 다 저장하도록 확장

## 9. 권장 코드 변경 포인트

### parser.py

추가 대상:

- `parse_company_page_url_from_job_detail(html: str) -> str | None`
- `parse_company_profile(html: str) -> dict`

정리 대상:

- 기존 `parse_company_detail()`는 회사 페이지 전용 함수로 이름을 바꾸거나 래퍼로만 유지

### crawler.py

추가 대상:

- `crawl_job_detail_page(url: str) -> str`
- `crawl_company_page(url: str) -> str`

정리 대상:

- 현재 `crawl_detail_page()`는 deprecated wrapper로 두거나 제거
- 페이지 타입별 `wait_locator` 분리

### database.py

추가 대상:

- `companies.company_page_url` 컬럼
- `update_company_page_url(company_id, company_page_url)`
- `get_companies_without_details()`에서 `company_page_url` 우선 전략

### main.py

정리 대상:

- `run_phase2()`를 아래 순서로 변경

```text
회사 대상 조회
  -> 회사 페이지 URL 있으면 바로 회사 페이지 방문
  -> 없으면 JD 상세 방문
  -> JD에서 회사 페이지 URL 추출
  -> 회사 페이지 방문
  -> 회사 정보 파싱/검증
  -> DB 업데이트
```

### scripts/analyze_detail_page.py

정리 대상:

- 파일명과 목적을 현재 Phase 2 흐름에 맞게 변경
- 최소한 "JD 페이지 링크 분석"과 "회사 페이지 구조 분석"을 분리

## 10. 테스트 전략

### 단위 테스트

`tests/test_parser.py`

- JD 상세 fixture에서 회사 페이지 링크 추출 테스트 추가
- 회사 페이지 fixture에서 `company_size`, `employee_count`, `establishment_year`, `homepage_url` 파싱 테스트 추가
- JD HTML을 `parse_company_profile()`에 넣었을 때 빈 결과 또는 명시적 실패를 반환하는 테스트 추가

`tests/test_main.py`

- FakeCrawler를 확장해 `crawl_job_detail_page()`와 `crawl_company_page()` 호출 순서 검증
- 회사 페이지 URL이 없을 때 skip되는지 검증

`tests/test_database.py`

- `company_page_url` 저장/조회 테스트 추가
- `get_companies_without_details()`가 회사당 한 건만 반환하는 성질 유지 검증

### 수동 검증

1. 샘플 JD URL 1건으로 회사 링크가 실제로 추출되는지 확인
2. 추출된 회사 페이지 URL이 로그인 없이 열리는지 확인
3. 회사 페이지 HTML에 목표 필드가 존재하는지 확인
4. `python main.py` 실행 후 `companies`에 상세 값이 채워지는지 SQL로 확인

스키마에 `company_page_url`을 추가한 뒤 사용할 수 있는 예시 SQL:

```sql
SELECT name, company_page_url, company_size, employee_count, establishment_year
FROM companies
WHERE company_size IS NOT NULL
ORDER BY updated_at DESC
LIMIT 20;
```

## 11. 구현 완료 기준

아래 조건을 만족하면 이 이슈는 해결된 것으로 본다.

- Phase 2가 JD 페이지를 직접 회사 정보 페이지로 간주하지 않는다.
- 회사 페이지 URL 추출 경로가 코드에 명시적으로 존재한다.
- 회사 페이지 URL을 재사용할 수 있다.
- Phase 2 실패 로그가 "JD 단계 실패"와 "회사 페이지 단계 실패"를 구분한다.
- 동일한 페이지 실패 몇 번 만에 과도한 쿨다운이 걸리는 문제가 완화된다.
- 테스트에 새 흐름이 반영된다.

## 12. 이번 문서의 권장 후속 작업

이 문서를 기준으로 다음 순서로 진행하는 것이 좋다.

1. 샘플 JD 1건에서 회사 페이지 링크 추출 가능 여부를 수동 검증
2. `parser.py`, `crawler.py`, `main.py`의 Phase 2 흐름 수정
3. `companies.company_page_url` 스키마 추가 여부 결정
4. 테스트 추가
5. 구현 완료 후 `docs/architecture/system_architecture.md`와 `README.md`의 Phase 2 설명 갱신
