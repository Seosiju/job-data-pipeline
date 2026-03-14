# JobKorea 회사 페이지 파싱 구조

> 기준 샘플: `tests/fixtures/jobkorea_company_page_02.html`
> 페이지 유형: 회사 상세 페이지 (`/Recruit/Co_Read/C/<company_id>`)
> 목적: 회사 페이지 HTML에서 `companies` 보강 필드를 안정적으로 추출하기 위한 파서 명세

## 1. 문서 목적

이 문서는 잡코리아 회사 상세 페이지의 실제 구조를 파서 관점에서 정리한다.

현재 목표는 아래 필드를 안정적으로 추출하는 것이다.

- `company_size`
- `employee_count`
- `establishment_year`
- `homepage_url`

추가로 현재 샘플에서 함께 확보 가능한 필드도 같이 기록한다.

- `industry`
- `address`
- `representative`
- `main_business`
- `insurances`

## 2. 샘플 범위와 주의점

- 본 문서는 현재 워킹트리에서 확인 가능한 실샘플 `jobkorea_company_page_02.html` 기준으로 작성했다.
- 이 샘플은 브라우저 저장본이라 로컬 상대경로, 스크립트, 광고 코드가 많다.
- 하지만 메인 데이터 영역은 서버 렌더링된 고전적인 HTML 테이블 구조라 파싱 난이도는 낮은 편이다.
- 현재 기준 샘플 수는 1개이므로, 후속 샘플이 추가되면 필드명 변형 여부를 꼭 검증해야 한다.

## 3. 페이지 정체성

### URL 패턴

관찰된 URL 변형은 최소 두 가지다.

```text
https://www.jobkorea.co.kr/Recruit/Co_Read/C/<company_id>
https://www.jobkorea.co.kr/Recruit/Co_Read/C/<company_slug>/Company_name/<company_name>
```

샘플 기준 확인된 값:

```text
https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886
https://www.jobkorea.co.kr/Recruit/Co_Read/C/nextground/Company_name/%E3%88%9C%EB%84%A5%EC%8A%A4%ED%8A%B8%EA%B7%B8%EB%9D%BC%EC%9A%B4%EB%93%9C
```

정리:

- JD에서 따라오는 링크와 페이지 내부 navigation/script 값은 숫자형 접근 URL을 주로 사용한다.
- `canonical`, `og:url` 등 메타에는 slug 기반 URL 변형이 함께 존재할 수 있다.
- 파서는 두 형식을 같은 회사 페이지로 인식할 수 있어야 한다.

### 구조적 특징

- JD 상세보다 전통적인 서버 렌더링 페이지에 가깝다.
- 기본 회사 정보는 `table.table-basic-infomation-primary`에 정리되어 있다.
- `th.field-label` / `td.field-value` 구조가 명확하다.
- `근무환경`, `복리후생`, `기업소개`, `기업위치` 등 확장 섹션도 존재한다.

파서 관점에서 중요한 결론:

- 메인 추출은 "라벨-값 테이블 파싱"으로 해결하는 것이 가장 안전하다.
- 레이아웃/위치 기반 selector보다 레이블 텍스트 기반 매핑이 훨씬 견고하다.

## 4. 핵심 DOM 랜드마크

### 4.1 회사 페이지 네비게이션

```css
.company-nav .company-nav-item.active
```

관찰 사실:

- 현재 활성 탭이 `기업정보`인지 확인할 수 있다.
- `채용`, `연봉정보` 등 다른 하위 탭도 같은 네비게이션에 존재한다.

파서 활용:

- 이 페이지가 회사 메인 정보 페이지인지 sanity check 용도로만 사용
- 실제 데이터 추출의 primary selector로 삼을 필요는 없다

### 4.2 기본 정보 섹션

```css
.company-infomation-row.basic-infomation
```

관찰 사실:

- `h2.header` 텍스트가 `기업정보`
- 안쪽에 `table.table-basic-infomation-primary`가 존재한다

평가:

- 기본 회사 정보를 담는 핵심 섹션이다.

### 4.3 기본 정보 테이블

```css
table.table-basic-infomation-primary
```

관찰 사실:

- 각 `tr.field`에 최대 2개의 label-value 쌍이 들어 있다.
- 한 row 안에 `th -> td -> th -> td` 구조가 반복된다.
- 즉, "row당 하나의 필드"가 아니라 "row당 여러 필드"일 수 있다.

파서 권장:

- 행 단위가 아니라 `th.field-label`과 대응 `td.field-value`를 순서대로 매핑한다.
- 구현 시에는 각 `tr.field`에서 direct child 기준으로 `th.field-label` 목록과 `td.field-value` 목록을 각각 수집한 뒤, 같은 인덱스끼리 zip 하는 방식이 가장 안전하다.

### 4.4 헤더 fallback 랜드마크

```css
.company-header-branding-body .name
.company-header-branding-body .summary .summary-item
.company-header .add-ons .home a.button-home
```

관찰 사실:

- 헤더 영역에도 회사명, 업종 요약, 홈페이지 링크가 중복 노출된다.
- 메인 테이블이 실패하거나 일부 필드가 비어 있을 때 보조 fallback으로 활용 가능하다.

파서 활용:

- `company_name` fallback
- `industry` fallback
- `homepage_url` fallback

## 5. 실제 확인된 필드

샘플 기준으로 아래 매핑이 확인되었다.

```text
산업 -> 모바일·APP
사원수 -> 23명
기업구분 -> 중소기업
설립일 -> 2021.03.19 (6년차)
자본금 -> -
매출액 -> -
대표자 -> 김청산
주요사업 -> 인터넷정보서비스업, 프롭테크, 소프트웨어 개발 및 공급업
4대보험 -> 국민연금, 건강보험, 고용보험, 산재보험
홈페이지 -> https://zippoom.com
주소 -> 서울 강남구 테헤란로 217 ...
```

## 6. 저장 대상 필드별 권장 규칙

### 6.1 `employee_count`

레이블:

- `사원수`
- alias: `직원수`

Primary selector strategy:

- `table.table-basic-infomation-primary`
- `th.field-label` 텍스트가 `사원수`인 셀을 찾고, 대응하는 `td.field-value`의 텍스트를 읽는다

샘플 값:

- `23명`

정규화:

- 현재 스키마는 문자열 저장이므로 원문 저장 가능
- 필요하면 validator에서 숫자 추출

### 6.2 `company_size`

레이블:

- `기업구분`
- alias: `기업형태`, `기업규모`

샘플 값:

- `중소기업`

주의:

- 현재 스키마 필드명은 `company_size`지만 실제 회사 페이지 레이블은 `기업구분`이다.
- 의미적으로는 `기업형태/기업구분`에 더 가깝다.
- 현재 스키마를 유지한다면 `기업구분` 값을 `company_size`에 매핑하는 것이 현실적이다.
- 이후 분류 로직을 고도화할 계획이 있다면 원문 보존용 `company_type_raw`를 별도로 둘 여지도 있다.

### 6.3 `establishment_year`

레이블:

- `설립일`

샘플 값:

- `2021.03.19 (6년차)`

정규화:

- 현재 validator 흐름상 최종 저장값은 `2021`처럼 연도만 유지하는 편이 맞다.
- 파서에서 먼저 `2021.03.19` 전체를 읽고, validator에서 연도만 남기거나
- 파서에서 첫 4자리 연도만 추출해도 된다

권장:

- 파서는 원문을 보존하고, validator에서 연도 추출을 담당하는 편이 역할 분리가 낫다.

### 6.4 `homepage_url`

레이블:

- `홈페이지`
- alias: `URL`

Primary selector strategy:

- 레이블 `홈페이지`에 대응하는 `td.field-value a[href]`

Fallback:

- 같은 셀의 텍스트 값을 URL 후보로 사용
- 헤더 영역 `.company-header .add-ons .home a.button-home`

샘플 값:

- `https://zippoom.com`

주의:

- 링크 텍스트와 `href`가 다를 수 있으므로 `href` 우선

## 7. 추가 확보 가능한 필드

현재 스키마에는 없지만 샘플에서 안정적으로 읽히는 값들이다.

### `industry`

- 레이블: `산업`
- 샘플 값: `모바일·APP`

### `address`

- 레이블: `주소`
- 샘플 값: `서울 강남구 테헤란로 217 ...`

### `representative`

- 레이블: `대표자`

### `main_business`

- 레이블: `주요사업`

### `insurances`

- 레이블: `4대보험`

이 값들은 향후 `companies` 스키마 확장 시 바로 활용 가능하다.

## 8. 권장 파싱 순서

회사 페이지 파서는 아래 순서를 추천한다.

1. 회사 메인 정보 테이블 존재 여부 확인
2. 각 `tr.field`에서 모든 `th.field-label` / `td.field-value` 쌍을 순서대로 매핑해 dict 생성
3. 저장 대상 필드로 변환
4. `홈페이지`는 `a[href]` 우선
5. 누락 필드는 헤더 fallback에서 보강
6. `설립일`은 raw text를 유지한 뒤 validator에서 정규화

권장 함수 경계:

```python
def parse_company_profile(html: str) -> dict[str, str | None]
def parse_company_label_value_table(html: str) -> dict[str, str]
def extract_company_field(field_map: dict[str, str], label: str) -> str | None
```

권장 세부 helper:

```python
def find_primary_company_info_table(soup) -> Tag | None
def extract_label_value_pairs(table) -> dict[str, str]
def normalize_company_fact(label: str, value: str) -> tuple[str | None, str | None]
```

## 9. 안정성 등급

### Primary

- `table.table-basic-infomation-primary`
- `tr.field`
- `th.field-label`
- `td.field-value`

### Secondary

- `.company-infomation-row.basic-infomation`
- `h2.header`
- `td.field-value a[href]`
- `.company-header-branding-body .name`
- `.company-header-branding-body .summary .summary-item`
- `.company-header .add-ons .home a.button-home`

### Avoid

- 스크립트 내 문자열
- 브라우저 저장본의 `_files/` 상대경로
- 광고 영역 클래스
- `nth-child` 기반 위치 selector
- DOM 위치만 믿고 `2번째 td = 사원수`처럼 고정하는 방식

이유:

- 한 row에 2쌍의 label-value가 섞여 있으므로 위치만 믿는 파싱은 필드 순서 변경에 취약하다.

## 10. fallback 전략

### Primary

- 기본 정보 테이블 레이블 매핑

### Secondary

- 테이블이 없다면 `기업정보` 헤더 근처의 `th`/`td` 구조 탐색
- 일부 필드만 누락됐다면 헤더 영역의 회사명/업종/홈페이지 링크로 보강

### Tertiary

- 메타 태그에서 회사명/페이지 정체성만 확인
- `basic-infomation` 블록 내부에 한정한 텍스트/정규식 fallback

중요:

- `근무환경`, `복리후생`, `기업소개` 같은 하위 섹션은 현재 저장 대상 필드와 직접 연결되지 않으므로 Phase 2 MVP에서는 기본 정보 테이블만 먼저 안정화하는 편이 좋다.

## 11. 실패 패턴

### 11.1 기본 정보 테이블 없음

의미:

- 회사 페이지 레이아웃 변경
- 로그인/차단/오류 페이지
- 저장본 손상

로그 권장 예시:

```text
Company profile table not found: <company_page_url>
```

### 11.2 레이블은 있는데 값이 비어 있음

의미:

- 실제 값 미공개
- 대시/빈 참조값

대응:

- `-`, 빈 문자열은 `None`으로 정규화 고려

### 11.3 `홈페이지`에 링크가 없고 텍스트만 있음

대응:

- `href` 우선
- 없으면 텍스트에서 URL 정규식 추출

## 12. 현재 코드에 대한 직접 시사점

현재 `parse_company_detail()`은 `dl`, `table`, 키워드 폴백 순서로 동작한다.

이 회사 페이지 샘플 기준으로는 `table` 전략이 가장 강력하고, 현재 코드는 `company page structure -> dl -> table -> keyword` 순서로 보강되어 있다.

현재 코드는 row 내부의 다중 `th/td` pair를 순회하고, `기업구분`, `기업형태`, `기업규모`를 모두 `company_size`로 매핑한다.

현재 코드 기준으로 반영된 사항:

- 테이블 레이블 매핑 helper가 분리되어 있다.
- row 내부의 다중 `th/td` pair를 전부 순회한다.
- `기업구분`, `기업형태`, `기업규모`를 같은 분류군으로 취급한다.
- `설립일`은 parser에서 연도 추출, validator에서 범위 검증을 수행한다.

현재 기준의 남은 권장 보강:

- 함수명 명확화가 필요한지 재검토
- parser와 validator 사이의 책임 분리를 문서에서 더 명시적으로 설명

## 13. 테스트 포인트

추가 테스트는 최소 아래를 커버해야 한다.

- `table.table-basic-infomation-primary` 존재 여부
- `사원수` 추출
- `기업구분` 추출
- `설립일` 추출
- `홈페이지 a[href]` 추출
- `대표자`, `주요사업`, `주소` 같은 추가 필드 매핑
- `-` 또는 빈 값 처리

## 14. 권장 후속 문서

이 문서는 회사 페이지 자체만 다룬다.

JD에서 이 회사 페이지로 넘어오는 링크 추출 규칙은 다음 문서를 함께 본다.

- `docs/architecture/jobkorea_jd_detail_page_structure.md`
