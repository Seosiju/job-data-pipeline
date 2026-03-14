# JobKorea JD 상세 페이지 파싱 구조

> 기준 샘플: `tests/fixtures/jobkorea_jd_detail_02.html`
> 페이지 유형: 채용공고 상세 페이지 (`/Recruit/GI_Read/<job_id>`)
> 목적: JD 상세 HTML에서 회사 페이지 URL과 보조 회사 정보를 안정적으로 추출하기 위한 파서 명세

## 1. 문서 목적

이 문서는 현재 잡코리아 JD 상세 페이지의 구조를 파서 관점에서 정리한 source of truth다.

핵심 질문은 두 가지다.

1. JD 상세 페이지에서 회사 페이지 URL을 어떻게 안정적으로 찾을 것인가
2. 회사 페이지 진입 전 JD 안에서 어떤 회사 보조 정보를 안전하게 가져올 수 있는가

현재 Phase 2 이슈의 핵심은 JD 상세를 회사 페이지처럼 직접 파싱하고 있다는 점이므로, 이 문서는 "회사 페이지로 넘어가는 링크"를 가장 중요한 추출 대상으로 본다.

## 2. 샘플 범위와 주의점

- 본 문서는 현재 워킹트리에서 확인 가능한 실샘플 `jobkorea_jd_detail_02.html` 기준으로 작성했다.
- 이 샘플은 브라우저 저장본이라 스크립트, 스타일, `_files/` 상대경로가 많이 섞여 있다.
- 현재 저장본에는 `RecruitmentGuidelines`, `근무지주소`, `인근지하철` 등 주요 JD 본문 정보가 직접 포함되어 있다.
- 다만 일부 상세 서술형 콘텐츠나 보조 리소스는 별도 iframe/외부 경로를 참조할 가능성이 있다.
- 하지만 핵심 DOM 텍스트와 `data-sentry-component` 속성은 남아 있어 파서 설계 근거로는 충분하다.
- 현재 기준으로는 샘플 수가 1개이므로, 문서의 `Primary selector`는 실제 운영 중 추가 샘플로 반드시 재검증해야 한다.

## 3. 페이지 정체성

### URL 패턴

```text
https://www.jobkorea.co.kr/Recruit/GI_Read/<job_id>
```

샘플에서는 querystring이 붙어 있다.

```text
https://www.jobkorea.co.kr/Recruit/GI_Read/48674797?Oem_Code=C1&...
```

### 구조적 특징

- Next.js/React 계열 페이지
- `data-sentry-component`, `data-sentry-element`, `data-sentry-source-file` 속성이 많이 붙어 있음
- 해시형 CSS 클래스가 다수 존재함
- JD 본문 외에 추천공고, 사이드바, 관련 태그 등 부가 콘텐츠가 함께 포함됨

파서 관점에서 중요한 결론:

- 해시형 클래스보다 `data-sentry-component`, `id`, 텍스트 라벨, URL 패턴이 더 신뢰할 만하다.

## 4. 핵심 DOM 랜드마크

### 4.1 JSON-LD 메타 블록

```css
script[data-sentry-component="JobPostingSchema"]
```

관찰 사실:

- `JobPosting` 스키마가 JSON-LD로 포함되어 있다.
- `title`, `description`, `hiringOrganization.name`, `jobLocation.address.addressLocality`, `experienceRequirements`, `url` 등이 있다.

파서 활용:

- 메타 fallback 데이터 소스로 유용하다.
- 단, 회사 페이지 URL은 여기 없다.

추천 용도:

- `company_name`
- `job_title`
- `job_location`
- JD canonical URL 보정

### 4.2 회사명 링크 블록

```css
[data-sentry-component="CompanyName"] a[href*="/Recruit/Co_Read/C/"]
```

관찰 사실:

- 타이틀 영역 상단의 회사명 텍스트가 회사 페이지 링크를 가진다.
- 샘플 값:
  - 텍스트: `㈜넥스트그라운드`
  - href: `https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886`

평가:

- JD에서 회사 페이지 URL을 찾는 1순위 selector다.

이유:

- 의미 기반 컴포넌트 이름이 붙어 있다.
- 링크 텍스트가 회사명과 일치한다.
- URL 패턴이 명확하다.

### 4.3 기업 정보 섹션

```css
#company-section
```

관찰 사실:

- JD 본문 아래에 별도 회사 요약 영역이 있다.
- `data-sentry-component="CorpInformation"`가 함께 붙어 있다.
- 섹션 헤더 텍스트는 `기업 정보`다.

활용:

- 회사 링크 fallback
- JD 내부 보조 회사 정보 추출

### 4.4 기업정보 더보기 링크

```css
#company-section [data-sentry-component="MoreButton"][href*="/Recruit/Co_Read/C/"]
```

관찰 사실:

- `기업정보 더보기` 버튼이 회사 페이지 링크를 가진다.
- 회사명 링크와 같은 `Co_Read` URL을 가리킨다.

평가:

- 회사명 링크 다음 2순위 fallback selector로 적합하다.

### 4.5 모집요강 블록

```css
#details-section [data-sentry-component="RecruitmentGuidelines"]
```

관찰 사실:

- 현재 fixture에는 모집요강 핵심 정보가 직접 DOM에 들어 있다.
- 샘플 기준 확인된 항목:
  - `모집분야` -> `사업개발`
  - `모집인원` -> `○ 명`
  - `고용형태` -> `정규직 (수습 3개월)`
  - `급여` -> `회사 내규에 따름 (면접 후 결정)`
  - `근무시간` -> `주5일(월~금) 09:00 ~ 18:00`
  - `근무지주소` -> `서울 강남구 테헤란로 217 ...`
  - `인근지하철` -> `선릉역`, `역삼역`, `언주역` 관련 정보

파서 활용:

- JD 본문이 현재 HTML에 어느 정도 직접 포함되어 있는지 확인하는 핵심 랜드마크다.
- 회사 정보와 분리된 JD 자체 필드 추출 근거로 사용할 수 있다.

주의:

- 현재 문서의 주목적은 회사 페이지 URL과 회사 fallback 정보 추출이므로, 이 블록은 JD 본문 source of truth의 일부로만 기록한다.
- 더 긴 서술형 상세 설명이 항상 동일한 방식으로 포함되는지는 추가 샘플로 교차검증해야 한다.

### 4.6 회사 요약 카드들

```css
#company-section [data-sentry-component="CorpInformationBox"]
```

관찰 사실:

- JD 안에 회사 요약 카드가 반복된다.
- 샘플 기준 확인된 항목:
  - `사원수` -> `50명 이하`
  - `기업구분` -> `중소기업 (비상장)`
  - `산업(업종)` -> `모바일·APP`
  - `위치` -> `서울 강남구 ...`

평가:

- 회사 페이지로 넘어가기 전 임시 보강 데이터로는 유용하다.
- 하지만 이 섹션만으로 `설립일`, `홈페이지`는 확보되지 않았다.

### 4.7 스크립트 기반 회사 식별자 fallback

관찰 사실:

- 샘플 스크립트에는 GTM/추적용 dimension 값으로 회사 id와 회사명이 들어 있다.
- 확인된 값 예시:
  - `dimension47` -> `35870886` (회사 id)
  - `dimension48` -> `㈜넥스트그라운드` (회사명)
  - `dimension43` -> 업종
  - `dimension46` -> 위치
  - `dimension66` -> 회사 분류

파서 활용:

- DOM 링크 추출이 실패한 경우 마지막 fallback으로 회사 id를 복원할 수 있다.
- 이 경우 URL은 `https://www.jobkorea.co.kr/Recruit/Co_Read/C/<company_id>` 형태로 조합한다.

주의:

- 스크립트 변수명은 운영 중 바뀔 수 있으므로 DOM selector보다 우선하면 안 된다.

## 5. 추출 대상과 권장 selector

## 5.1 회사 페이지 URL

### Primary

```css
[data-sentry-component="CompanyName"] a[href*="/Recruit/Co_Read/C/"]
```

### Fallback

```css
#company-section [data-sentry-component="MoreButton"][href*="/Recruit/Co_Read/C/"]
```

### Last-resort fallback

1. 스크립트에서 회사 id 후보 추출
2. `https://www.jobkorea.co.kr/Recruit/Co_Read/C/<company_id>` 조합
3. 그래도 실패하면 전역 `a[href*="/Recruit/Co_Read/C/"]`는 참고용 경고 로그만 남기고 바로 채택하지 않는다

주의:

- 페이지 전체에 추천공고/연관회사 링크가 섞일 수 있으므로, 전역 fallback은 반드시 `CompanyName` 또는 `#company-section` 탐색 실패 후에만 사용해야 한다.
- 전역 fallback 사용 시 가장 먼저 등장한 링크를 바로 채택하지 말고, 타이틀 영역 근처인지 확인하는 것이 안전하다.

## 5.2 회사명

### Primary

```css
[data-sentry-component="CompanyName"] h2
```

### Fallback

- `script[data-sentry-component="JobPostingSchema"]` 내부 `hiringOrganization.name`
- `meta[name="writer"]`

## 5.3 JD 내부 회사 보조 정보

### Recommended extraction scope

- `사원수`
- `기업구분`
- `산업(업종)`
- `위치`

### Recommended approach

`CorpInformationBox`를 카드 단위로 순회하면서 "라벨 텍스트 -> 값" 매핑을 만든다.

이유:

- 아이콘 클래스는 의미가 있긴 하지만 장기적으로 텍스트 라벨보다 덜 안전하다.
- 해시 클래스는 재배포 시 바뀔 수 있다.

### Example normalized mapping

```text
사원수 -> employee_count_fallback
기업구분 -> company_type_fallback
산업(업종) -> industry_fallback
위치 -> address_fallback
```

주의:

- 현재 스키마의 `company_size`와 JD의 `기업구분`은 완전히 같은 개념은 아니다.
- JD fallback 값은 회사 페이지가 실패했을 때의 임시 보강 데이터로 다루는 편이 맞다.
- 지도 링크가 존재하면 좌표와 주소 보조 정보도 추가 수집할 수 있다.
- `RecruitmentGuidelines`의 `근무지주소`, `인근지하철` 라인은 회사 정보라기보다 JD 근무지 보조 데이터로 분리해서 다루는 편이 안전하다.

## 6. 권장 파싱 순서

JD 상세 파서는 아래 순서를 추천한다.

1. JSON-LD 메타 읽기
2. 타이틀 영역 `CompanyName`에서 회사명과 회사 페이지 URL 추출
3. 실패 시 `#company-section`의 `MoreButton`으로 회사 페이지 URL 추출
4. 실패 시 스크립트의 회사 id fallback으로 `Co_Read` URL 조합
5. 필요 시 `RecruitmentGuidelines`에서 JD 본문 필드 추출
6. `#company-section`의 `CorpInformationBox` 카드에서 회사 보조 정보 추출
7. 최종적으로 `company_page_url`이 없으면 Phase 2 스킵 후보로 처리

중요:

- JD 상단 메타/회사 링크 파싱과 JD 본문 필드 파싱은 함수 경계상 분리하는 편이 맞다.
- 다만 현재 샘플은 `RecruitmentGuidelines` 수준의 주요 JD 본문을 직접 포함하므로, shell-only fixture로 보면 안 된다.
- 일부 더 긴 서술형 본문이나 보조 리소스는 별도 경로일 수 있으므로, 본문 파서는 추가 샘플로 교차검증하는 편이 낫다.

권장 함수 경계:

```python
def parse_company_page_url_from_job_detail(html: str) -> str | None
def parse_company_summary_from_job_detail(html: str) -> dict[str, str | None]
def parse_jobposting_schema(html: str) -> dict[str, str | None]
def parse_jd_shell(html: str) -> dict[str, str | None]
def parse_jd_description_body(html: str) -> dict[str, str | None]
```

## 7. 안정성 등급

### Primary

- `[data-sentry-component="CompanyName"] a[href*="/Recruit/Co_Read/C/"]`
- `#details-section [data-sentry-component="RecruitmentGuidelines"]`
- `#company-section`
- `#company-section [data-sentry-component="MoreButton"]`
- `script[data-sentry-component="JobPostingSchema"]`

### Secondary

- `[data-sentry-component="CorpInformationBox"]`
- `meta[name="writer"]`
- GTM dimension 값이 들어 있는 스크립트

### Avoid

- `Typography_variant_*`
- `Flex_*`
- `_1ycqh5m*`, `_3sqppx0` 같은 해시형 클래스
- `jk-_R_*`, `base-ui-_R_*` 같은 React 생성 id
- 중복 등장하는 `recommended-section`, `corp-box-tooltip-container` 같은 id
- 페이지 저장본의 `_files/` 상대경로
- 추천공고 영역까지 포함한 전역 `a[href*="/Recruit/Co_Read/C/"]` 단독 사용

## 8. 실패 패턴

다음 경우는 명시적으로 로그를 남기는 것이 좋다.

### 8.1 회사 페이지 링크 없음

의미:

- 로그인 상태, A/B 테스트, OEM 경로 차이, DOM 변경 가능성

로그 권장 예시:

```text
JD company page URL not found: <job_detail_url>
```

### 8.2 `company-section` 자체 없음

의미:

- JD 구조 변경
- 봇 차단/비정상 렌더링
- 미완성 HTML 저장본

### 8.3 JD 설명 본문 파싱 실패

의미:

- 상단 메타/회사 링크는 정상인데 `RecruitmentGuidelines` 같은 JD 본문 블록이나 일부 보조 리소스가 누락된 상태일 가능성

대응:

- 회사 링크 추출 실패와 JD 본문 추출 실패를 같은 예외로 묶지 않는다

### 8.4 전역 `Co_Read` 링크만 존재

의미:

- 추천공고나 외부 추천 카드까지 DOM에 섞였을 가능성

대응:

- 타이틀 영역 또는 기업 정보 섹션 근처만 신뢰

## 9. 현재 코드에 대한 직접 시사점

현재 `parser.py`의 `_extract_detail_url()`은 목록 카드에서 JD URL만 저장한다. 이건 문제 없다.

문제였던 부분은 Phase 2에서 JD URL을 바로 회사 정보 페이지처럼 다루던 오케스트레이션이었고, 이 메인 경로는 현재 구현에서 수정되었다.

현재 코드 기준으로 반영된 사항:

- JD -> 회사 페이지 URL 추출 함수가 추가되었다.
- Phase 2는 JD를 먼저 열고 회사 페이지 URL을 얻은 뒤 회사 페이지를 방문한다.
- `parse_company_detail()`는 JD HTML과 회사 페이지 HTML을 구분한다.

현재 기준의 남은 권장 보강:

- JD 내부 `CorpInformationBox` 값을 회사 페이지 실패 시 fallback 보강 데이터로 쓸지 결정
- 회사 페이지 URL을 DB에 저장해 매 실행마다 JD를 다시 열지 않도록 할지 결정

## 10. 테스트 포인트

추가 테스트는 최소 아래를 커버해야 한다.

- `CompanyName` 링크에서 `Co_Read` URL 추출
- `MoreButton` 링크에서 `Co_Read` URL 추출
- `RecruitmentGuidelines`에서 `근무지주소`, `인근지하철` 같은 JD 본문 필드 추출
- `CorpInformationBox`에서 `사원수`, `기업구분`, `산업(업종)`, `위치` 추출
- `JobPostingSchema`에서 `hiringOrganization.name` 추출
- JD에 회사 페이지 URL이 없는 경우 `None` 반환

## 11. 권장 후속 문서

이 문서는 회사 페이지 전환 전 단계만 다룬다.

실제 회사 상세 필드 파싱 규칙은 다음 문서를 함께 본다.

- `docs/architecture/jobkorea_company_page_structure.md`
