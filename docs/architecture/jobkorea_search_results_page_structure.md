# JobKorea 검색 결과 페이지 파싱 구조

> 기준 샘플: `tests/fixtures/jobkorea_search_page_02.html`
> 페이지 유형: 검색 결과 페이지 (`/Search/?stext=<keyword>`)
> 목적: 검색 결과 HTML에서 메인 채용공고 목록과 페이지네이션을 안정적으로 추출하기 위한 파서 명세

## 1. 문서 목적

이 문서는 잡코리아 검색 결과 페이지를 파서 관점에서 정리한 source of truth다.

현재 핵심 질문은 세 가지다.

1. 메인 목록 카드와 부가 카드/광고 카드를 어떻게 구분할 것인가
2. 각 카드에서 JD URL, 제목, 회사명, 지역, 직무 정보를 어떤 순서로 안정적으로 읽을 것인가
3. 페이지네이션과 검색 결과 메타 정보를 어떤 DOM에서 가져올 것인가

이 문서는 "검색 결과 페이지 전체에서 `CardJob`를 긁는 방식"이 왜 위험한지와, 반드시 `JobList` 스코프 안에서 파싱해야 하는 이유를 명시한다.

## 2. 샘플 범위와 주의점

- 본 문서는 현재 워킹트리에서 확인 가능한 실샘플 `jobkorea_search_page_02.html` 기준으로 작성했다.
- 샘플은 브라우저 저장본이며, Next.js hydration script와 `_files/` 상대경로가 섞여 있다.
- DOM 기준으로는 메인 목록 `20`개, 페이지 전체 `CardJob`는 `27`개가 확인된다.
- 즉, 전역 `CardJob` 탐색은 메인 목록 외 카드까지 섞어 가져올 수 있다.
- 타이틀/메타에는 총 `8,515건`, `JobList` 헤더에는 총 `8,513건`이 보인다. 검색 결과 수는 hydration/탭 상태 차이로 미세하게 어긋날 수 있으므로 단일 source만 절대시하면 안 된다.

## 3. 페이지 정체성

### URL 패턴

```text
https://www.jobkorea.co.kr/Search/?stext=<keyword>
```

페이지네이션은 querystring `Page_No`로 이동한다.

```text
https://www.jobkorea.co.kr/Search?stext=사업기획&Page_No=2
```

### 구조적 특징

- Next.js/React 기반 검색 결과 페이지
- 메인 영역 외에 탭, 필터, 연관검색어, 파워링크, 전문채용관, 최근검색어 등이 함께 렌더링된다
- 동일한 `CardJob` 컴포넌트가 메인 목록 외 영역에도 존재할 수 있다
- hydration script 안에는 검색 결과 수, 탭 상태, product list 참조 정보가 포함된다

파서 관점의 결론:

- 전역 `CardJob` 수집이 아니라 `JobList -> CardJob` 스코프 파싱이 기본 전략이어야 한다.

## 4. 핵심 DOM 랜드마크

### 4.1 검색 결과 메타

```css
title
link[rel="canonical"]
script[data-sentry-component="JsonLdScript"]
```

관찰 사실:

- `title`에는 검색어와 총 검색 결과 수가 포함된다.
- `canonical`은 `/Search/?stext=<keyword>` 형태다.
- `JsonLdScript`는 breadcrumb 수준의 구조 정보만 담고 있으며, 카드 데이터 자체는 포함하지 않는다.

활용:

- `search_keyword`
- canonical URL
- breadcrumb sanity check

### 4.2 탭 영역

```css
[data-sentry-component="Tab"]
```

관찰 사실:

- `채용정보`, `기업정보`, `알바몬공고` 탭이 존재한다.
- 현재 샘플은 `채용정보` 탭 기준이다.

활용:

- 현재 파서가 어느 탭 구조를 읽는지 sanity check

주의:

- 검색 결과 페이지 전체를 파싱할 때는 반드시 "채용정보 탭 구조"임을 전제로 해야 한다.

### 4.3 필터 영역

```css
[data-sentry-component="FilterList"]
```

관찰 사실:

- `직무`, `지역`, `경력`, `기업형태`, `학력`, `고용형태`, `조건추가` 버튼이 존재한다.
- 필터 값이 DOM 상단 텍스트나 hydration script에 반영될 수 있다.

활용:

- 현재 검색 상태 확인
- 추후 필터 자동화 시 진입점

### 4.4 메인 목록 영역

```css
[data-sentry-component="JobList"]
```

관찰 사실:

- 메인 채용공고 목록은 이 컨테이너 안에 있다.
- 샘플 기준 `JobList` 내부 `CardJob`는 `20`개다.
- 이 컨테이너 안에 결과 수 헤더와 페이지네이션도 함께 들어 있다.

평가:

- 목록 파싱의 절대 1순위 스코프다.

### 4.5 개별 채용 카드

```css
[data-sentry-component="JobList"] [data-sentry-component="CardJob"]
```

관찰 사실:

- 카드 안에는 보통 다음 블록이 들어 있다.
  - 회사 로고 링크 `CompanyLogo` (옵션)
  - 제목 링크
  - 회사명 링크
  - `GrayChip` 2~3개
  - 뱃지 `BadgeItem` 0~1개 이상
  - 버튼 `BaseButton` 2개 내외 (`스크랩`, `즉시 지원` 또는 `홈페이지 지원`)

중요:

- 회사 로고 링크, 제목 링크, 회사명 링크 모두 같은 `GI_Read` JD URL로 향한다.
- 즉, 검색 결과 카드에서 회사명 클릭은 회사 페이지가 아니라 JD 상세로 이동한다.

### 4.6 페이지네이션

```css
[data-sentry-component="Pagination"] a[href*="Page_No="]
```

관찰 사실:

- 페이지네이션은 `nav[data-sentry-component="Pagination"]`로 렌더링된다.
- 샘플 기준 `Prev`, `1..10`, `Next` 링크가 존재한다.
- 첫 그룹에서 `Prev`는 `Page_No=0`, `Next`는 `Page_No=11`이다.

활용:

- 다음 페이지 URL 계산
- 현재 페이지 그룹 파악

### 4.7 hydration script fallback

관찰 사실:

- hydration script에 아래 보조 데이터가 들어 있다.
  - `jobsLength: 8513`
  - `resultCount: 8513`
  - `productList` 참조
  - `JOB_PRODUCT_LIST` query key

활용:

- 결과 수 sanity check
- DOM 불완전 저장본에서 최소 메타 보강

주의:

- hydration script는 최후 fallback로만 사용한다.
- DOM과 script의 결과 수가 어긋날 수 있으므로, 카드 파싱 결과를 script 값에 맞춰 억지 보정하면 안 된다.

## 5. 카드 필드별 권장 selector

## 5.1 카드 스코프

### Primary

```css
[data-sentry-component="JobList"] [data-sentry-component="CardJob"]
```

### Avoid

```css
[data-sentry-component="CardJob"]
```

이유:

- 전역 `CardJob`는 메인 목록 외 카드까지 포함한다.
- 현재 샘플에서도 전역 `27`개, 메인 목록 `20`개로 차이가 난다.

## 5.2 JD 상세 URL

### Primary

- 카드 내부 `a[href*="/Recruit/GI_Read/"]` 중 첫 번째 `href`

### Secondary

- 제목 링크 `a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size18"]`의 부모 anchor

주의:

- 회사명 링크와 회사 로고 링크도 같은 JD URL을 가리킨다.
- 세 링크가 모두 같은 `href`이므로, 카드 내부에서는 중복 제거 후 하나만 저장하면 된다.

## 5.3 제목

### Primary

```css
a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size18"]
```

평가:

- 현재 샘플에서 제목 링크 내부 텍스트는 `size18` typography로 안정적으로 구분된다.

주의:

- 전역 `size18` 탐색보다 반드시 카드 스코프 안에서 anchor와 함께 묶어야 한다.

## 5.4 회사명

### Primary

```css
a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size16"]
```

평가:

- 현재 샘플에서 회사명 링크 내부 텍스트는 `size16` typography다.
- 일부 카드에는 회사 로고가 없지만 회사명 링크는 유지된다.

주의:

- 검색 결과 카드의 회사명 링크는 회사 페이지 URL이 아니다.

## 5.5 위치

### Primary

```css
[data-sentry-component="GrayChip"] .emoji--basicemoji-place2
```

추출 방식:

- 위치 아이콘이 들어 있는 `GrayChip`의 텍스트를 읽는다.

샘플 값:

- `서울 금천구 외 3`
- `서울 강남구`

## 5.6 업종과 직무

### Primary

```css
[data-sentry-component="GrayChip"] .emoji--basicemoji-briefcase
```

추출 방식:

- briefcase 아이콘이 있는 `GrayChip`의 텍스트를 읽는다.
- 쉼표 기준 분리 후 첫 항목은 `industry`, 나머지는 `job_category`로 저장한다.

샘플 값:

```text
출판·인쇄·사진, 경영·비즈니스기획, 채널관리자, 제품디자이너
```

정규화 예시:

```text
industry -> 출판·인쇄·사진
job_category -> 경영·비즈니스기획, 채널관리자, 제품디자이너
```

## 5.7 급여

### Primary

```css
[data-sentry-component="GrayChip"] .emoji--basicemoji-money_bill
```

관찰 사실:

- 샘플 기준 대부분 카드는 `GrayChip` 2개지만, 일부 카드는 급여용 세 번째 chip이 추가된다.
- 예: `연봉 4,000~6,000만원`

주의:

- "세 번째 chip = 급여"로 고정하면 안 된다.
- 반드시 money icon 기준으로 식별해야 한다.

## 5.8 뱃지

### Primary

```css
[data-sentry-component="BadgeItem"] span
```

샘플 값:

- `신입 지원 가능`
- `믿고보는 대기업`
- `유연근무제 시행중`
- `재택/원격근무 가능`

## 5.9 지원 방식

### Primary

- 카드 내부 `button[data-sentry-component="BaseButton"]` 중 `스크랩`이 아닌 마지막 버튼 텍스트

샘플 값:

- `즉시 지원`
- `홈페이지 지원`

주의:

- 현재 코드의 `_16czznu` 해시형 클래스 기반 추출은 brittle하다.
- 버튼 텍스트 기반 분기가 더 안전하다.

## 5.10 경력 / 복리후생 / 등록일 / 마감일

관찰 사실:

- 이 구간은 semantic component marker가 약하다.
- 카드 하단의 `Typography_variant_size13` + `Typography_weight_regular` 텍스트에 함께 섞여 있다.

권장 전략:

- 카드 스코프 안에서 텍스트 규칙으로 읽는다.
- `등록`, `마감`, `상시채용`, `내일마감`은 날짜/마감 후보
- `지원`, `보험`, `제도`, `이벤트`, `식사`, `검진`, `복장` 등은 복리후생 후보

평가:

- 이 구간은 1차 semantic selector보다 "카드 스코프 + 텍스트 패턴" fallback이 맞다.

## 6. 권장 파싱 순서

검색 결과 파서는 아래 순서를 추천한다.

1. `canonical`, `title`, `Tab`으로 현재 검색 컨텍스트 확인
2. `JobList` 컨테이너 찾기
3. `JobList` 내부 `CardJob`만 순회
4. 각 카드에서 JD URL 중복 제거
5. 제목, 회사명, `GrayChip`, badge, apply button, 하단 텍스트를 순서대로 추출
6. `Pagination`에서 다음 페이지 후보 URL 추출
7. 필요하면 hydration script에서 결과 수만 sanity check

권장 함수 경계:

```python
def parse_search_page_context(html: str) -> dict[str, str | int | None]
def find_job_list_container(soup) -> Tag | None
def parse_job_cards_from_search(html: str) -> list[dict[str, str]]
def parse_job_card(card) -> dict[str, str]
def parse_search_pagination(html: str) -> dict[str, str | list[str]]
```

## 7. 안정성 등급

### Primary

- `[data-sentry-component="JobList"]`
- `[data-sentry-component="JobList"] [data-sentry-component="CardJob"]`
- `[data-sentry-component="Pagination"]`
- `a[href*="/Recruit/GI_Read/"]` within card
- `[data-sentry-component="GrayChip"]` with icon marker

### Secondary

- `span[class*="Typography_variant_size18"]` for title
- `span[class*="Typography_variant_size16"]` for company
- `[data-sentry-component="BadgeItem"]`
- hydration script의 `jobsLength`, `resultCount`

### Avoid

- 전역 `[data-sentry-component="CardJob"]`
- 전역 `a[href*="/Recruit/GI_Read/"]`
- `_16czznu*`, `Typography_*`, `Flex_*`, `_10fvqwx0` 같은 해시/스타일 클래스 단독 사용
- 브라우저 저장본의 `_files/` 상대경로
- "세 번째 chip = 급여" 같은 위치 고정 규칙

## 8. 실패 패턴

### 8.1 `JobList` 없음

의미:

- 탭이 `채용정보`가 아님
- 페이지 구조 변경
- 비정상 렌더링/차단

### 8.2 전역 `CardJob`는 잡히는데 `JobList` 안 카드 수가 0

의미:

- 메인 목록이 아닌 추천 카드/광고 카드만 저장됐을 가능성
- 저장본 손상 가능성

### 8.3 결과 수 불일치

관찰:

- 샘플에서 `title`은 `8,515`, `JobList` 헤더와 hydration은 `8,513`이다.

대응:

- 결과 수는 진단용 메타로만 사용한다.
- 카드 개수나 페이지 종료 판단을 결과 수 하나에만 의존하지 않는다.

## 9. 현재 코드에 대한 직접 시사점

현재 `parse_job_cards()`는 먼저 `JobList` 컨테이너를 찾고, 그 안에서 `CardJob`를 순회한다.

즉, 이 문서가 지적한 핵심 문제였던 "전역 `CardJob` 27개 과수집"은 현재 코드에서 1차 보정된 상태다.

다만 `JobList`를 찾지 못하면 전역 `CardJob`로 폴백하므로, live 구조가 크게 바뀌면 다시 과수집 가능성은 남아 있다.

현재 코드 기준으로 반영된 사항:

- `parse_job_cards()`는 `JobList` 우선 스코프 사용
- `_extract_title()`와 `_extract_company()`는 `GI_Read` anchor 내부 selector 사용
- `_extract_apply_type()`는 해시 클래스 대신 버튼 텍스트 기반으로 동작
- `_extract_location()`, `_extract_industry()`, `_extract_job_category()`, `_extract_salary()`는 아이콘 기반 `GrayChip` 식별 유지
- 카드별 `job id`를 기준으로 hydration metadata에서 `careerType`, `employmentTypeCodeList`, `areaCodeList`를 복원해 `experience_type`, `employment_types`, `location_codes`를 보강한다
- env의 `SEARCH_LOCATIONS`, `SEARCH_EXPERIENCE_TYPES`, `SEARCH_EMPLOYMENT_TYPES`는 위 카드/hydration 메타데이터를 기준으로 저장 전 필터에 사용된다

현재 기준의 남은 권장 보강:

- `JobList` 미탐지 시 전역 `CardJob` 폴백 경로를 어떻게 다룰지 명확히 결정
- hydration metadata 파서가 live script 구조 변경에 얼마나 견디는지 fixture를 더 확보해 검증

## 10. 테스트 포인트

추가 테스트는 최소 아래를 커버해야 한다.

- 전역 `CardJob`는 `27`개지만 메인 목록 파서는 `20`개만 반환
- 카드 1개에서 JD URL, 제목, 회사명 추출
- location chip과 briefcase chip 분리
- salary chip이 있는 카드와 없는 카드 모두 처리
- `즉시 지원` / `홈페이지 지원` 버튼 추출
- `Pagination`에서 `Page_No=2` 같은 번호 링크와 `Next` 링크 추출
- 결과 수 불일치가 있어도 카드 파싱은 정상 동작

## 11. 권장 후속 문서

이 문서는 검색 결과 페이지만 다룬다.

목록에서 들어가는 JD 구조와 회사 페이지 구조는 아래 문서를 함께 본다.

- `docs/architecture/jobkorea_jd_detail_page_structure.md`
- `docs/architecture/jobkorea_company_page_structure.md`
