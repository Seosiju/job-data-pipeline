# parser.py 리팩토링 구조도

## 전체 함수 구조

```
parser.py (27 functions, avg complexity: A-3.63)
│
├─ Public API (3 functions)
│  ├─ parse_job_cards() [A-3]
│  ├─ parse_company_detail() [A-3]
│  └─ extract_card_data() [A-1]
│
├─ Card Extraction Helpers (14 functions)
│  ├─ _extract_title() [A-2]
│  ├─ _extract_company() [A-2]
│  ├─ _extract_location() [A-4]
│  ├─ _extract_experience() [A-2]
│  ├─ _extract_detail_url() [A-3]
│  ├─ _extract_industry() [B-6]
│  ├─ _extract_job_category() [B-6]
│  ├─ _extract_salary() [A-4]
│  ├─ _extract_badge() [A-2]
│  ├─ _extract_apply_type() [A-2]
│  ├─ _extract_date_spans() [A-1]
│  ├─ _extract_posted_date() [B-6]
│  ├─ _extract_deadline() [B-6]
│  └─ _extract_benefits() [B-7]
│
└─ Company Detail Helpers (10 functions)
   ├─ _parse_from_dl_structure() [A-3]
   ├─ _parse_from_table_structure() [A-4]
   ├─ _parse_from_keywords() [A-1]
   ├─ _init_company_details() [A-1]
   ├─ _extract_field_from_label_value() [B-8]
   ├─ _extract_year_from_text() [A-2]
   ├─ _extract_url_from_element() [A-5]
   ├─ _extract_company_size_by_keyword() [A-4]
   ├─ _extract_establishment_year_by_pattern() [A-3]
   └─ _extract_homepage_url() [B-7]
```

---

## parse_company_detail() 호출 흐름

```
parse_company_detail(html)
│
├─ BeautifulSoup(html) → soup
│
├─ [전략 1] _parse_from_dl_structure(soup)
│  │
│  ├─ _init_company_details() → details
│  │
│  ├─ for dl in soup.find_all("dl"):
│  │  └─ for dt, dd in zip(...):
│  │     └─ _extract_field_from_label_value(label, value, dd, details)
│  │        ├─ if "기업규모" → details["company_size"] = value
│  │        ├─ if "사원수" → details["employee_count"] = value
│  │        ├─ if "설립" → _extract_year_from_text(value)
│  │        └─ if "홈페이지" → _extract_url_from_element(dd, value)
│  │
│  └─ return details
│
├─ if any(details.values()):
│  └─ return details  ✓ 성공
│
├─ [전략 2] _parse_from_table_structure(soup)
│  │
│  ├─ _init_company_details() → details
│  │
│  ├─ for table in soup.find_all("table"):
│  │  └─ for row in table.find_all("tr"):
│  │     └─ _extract_field_from_label_value(label, value, cell, details)
│  │
│  └─ return details
│
├─ if any(details.values()):
│  └─ return details  ✓ 성공
│
└─ [전략 3] _parse_from_keywords(soup)
   │
   ├─ _init_company_details() → details
   │
   ├─ details["company_size"] = _extract_company_size_by_keyword(soup)
   │  └─ for keyword in ["대기업", "중견기업", ...]:
   │     └─ soup.find(string=lambda t: keyword in t)
   │
   ├─ details["establishment_year"] = _extract_establishment_year_by_pattern(soup)
   │  └─ soup.find(string=re.compile(r"설립\s*:?\s*\d{4}"))
   │
   ├─ details["homepage_url"] = _extract_homepage_url(soup)
   │  └─ for a_tag in soup.find_all("a", href=True):
   │     └─ if "홈페이지" in text or external link
   │
   └─ return details
```

---

## extract_card_data() 호출 흐름

```
extract_card_data(card)
│
└─ return {
    │
    ├─ "title": _extract_title(card)
    │  └─ card.select_one('[class*="Typography_variant_size18"]')
    │
    ├─ "company": _extract_company(card)
    │  └─ card.select_one('[class*="Typography_variant_size16"]')
    │
    ├─ "location": _extract_location(card)
    │  ├─ card.select_one('[class*="emoji--basicemoji-place2"]')
    │  └─ find_parent → select_one text
    │
    ├─ "experience": _extract_experience(card)
    │  └─ card.select_one('[class*="Typography_variant_size13"]...')
    │
    ├─ "detail_url": _extract_detail_url(card)
    │  ├─ card.select_one('a[href*="/Recruit/GI_Read/"]')
    │  └─ if startswith("/") → prepend base URL
    │
    ├─ "industry": _extract_industry(card)
    │  ├─ card.select_one('[class*="emoji--basicemoji-briefcase"]')
    │  ├─ find_parent → select_one text
    │  └─ split(",")[0]
    │
    ├─ "job_category": _extract_job_category(card)
    │  ├─ card.select_one('[class*="emoji--basicemoji-briefcase"]')
    │  ├─ find_parent → select_one text
    │  └─ ", ".join(split(",")[1:])
    │
    ├─ "salary": _extract_salary(card)
    │  ├─ card.select_one('[class*="emoji--basicemoji-money_bill"]')
    │  └─ find_parent → select_one text
    │
    ├─ "badge": _extract_badge(card)
    │  └─ card.select_one('[data-sentry-component="BadgeItem"] span')
    │
    ├─ "apply_type": _extract_apply_type(card)
    │  └─ card.select_one('[class*="_16czznu"] ...')
    │
    ├─ "posted_date": _extract_posted_date(card)
    │  ├─ _extract_date_spans(card)
    │  └─ filter by "등록" | "마감" | "채용" → [0]
    │
    ├─ "deadline": _extract_deadline(card)
    │  ├─ _extract_date_spans(card)
    │  └─ filter by "등록" | "마감" | "채용" → [1]
    │
    └─ "benefits": _extract_benefits(card)
       ├─ _extract_date_spans(card)
       └─ filter by "지원" | "제도" | "보험" → join
   }
```

---

## 복잡도 등급별 함수 분포

### A등급 함수 (1-5) - 20개

```
[1] extract_card_data
    _extract_date_spans
    _parse_from_keywords
    _init_company_details

[2] _extract_title
    _extract_company
    _extract_experience
    _extract_badge
    _extract_apply_type
    _extract_year_from_text

[3] parse_job_cards
    _extract_detail_url
    parse_company_detail
    _parse_from_dl_structure
    _extract_establishment_year_by_pattern

[4] _extract_location
    _extract_salary
    _parse_from_table_structure
    _extract_company_size_by_keyword

[5] _extract_url_from_element
```

### B등급 함수 (6-10) - 7개

```
[6] _extract_industry
    _extract_job_category
    _extract_posted_date
    _extract_deadline

[7] _extract_benefits
    _extract_homepage_url

[8] _extract_field_from_label_value
```

---

## 리팩토링 전후 비교

### Before: 복잡한 모놀리식 함수

```
parse_company_detail() [F-42, 97 lines]
├─ BeautifulSoup 초기화
├─ 빈 딕셔너리 생성
├─ [방법 1] dl/dt/dd 파싱 (30줄)
│  ├─ dl 순회
│  ├─ dt/dd 매칭
│  └─ 10가지 if-elif 분기
│     ├─ 기업규모 추출
│     ├─ 사원수 추출
│     ├─ 설립연도 추출 (정규식 포함)
│     ├─ 홈페이지 URL 추출 (링크 파싱 포함)
│     └─ ...
├─ [방법 2] table 파싱 (30줄)
│  ├─ table 순회
│  ├─ tr/th/td 매칭
│  └─ 10가지 if-elif 분기 (위와 동일 로직 중복)
│     ├─ 기업규모 추출
│     ├─ 사원수 추출
│     ├─ 설립연도 추출 (정규식 포함)
│     ├─ 홈페이지 URL 추출 (링크 파싱 포함)
│     └─ ...
└─ [방법 3] 키워드 파싱 (30줄)
   ├─ 기업규모 키워드 탐색 (for loop + lambda)
   ├─ 설립연도 패턴 탐색 (regex + 조건문)
   └─ 홈페이지 링크 탐색 (for loop + 중첩 조건문)
```

### After: 계층화된 명확한 구조

```
parse_company_detail() [A-3, 14 lines]
├─ _parse_from_dl_structure() [A-3]
│  └─ _extract_field_from_label_value() [B-8]
│     ├─ _extract_year_from_text() [A-2]
│     └─ _extract_url_from_element() [A-5]
│
├─ _parse_from_table_structure() [A-4]
│  └─ _extract_field_from_label_value() [B-8]
│     ├─ _extract_year_from_text() [A-2]
│     └─ _extract_url_from_element() [A-5]
│
└─ _parse_from_keywords() [A-1]
   ├─ _extract_company_size_by_keyword() [A-4]
   ├─ _extract_establishment_year_by_pattern() [A-3]
   └─ _extract_homepage_url() [B-7]
```

---

## 핵심 개선 포인트

### 1. 중복 제거
**Before:** 방법 1과 방법 2에서 동일한 필드 추출 로직 반복 (60줄)
**After:** `_extract_field_from_label_value()` 하나로 통합 (15줄)

### 2. 관심사 분리
**Before:** 파싱 전략 + 필드 추출 + 데이터 변환이 한 함수에 혼재
**After:** 각 관심사를 별도 함수로 분리
- 파싱 전략: `_parse_from_*()` 함수
- 필드 추출: `_extract_field_from_label_value()`
- 데이터 변환: `_extract_year_from_text()`, `_extract_url_from_element()`

### 3. 추상화 레벨 통일
**Before:** 고수준 로직과 저수준 구현이 섞여 있음
**After:** 각 함수가 동일한 추상화 레벨 유지
- 메인 함수: 전략 선택
- 헬퍼 함수: 구체적 구현

### 4. 명확한 네이밍
**Before:** 주석으로 설명이 필요
**After:** 함수명만으로 의도 파악 가능

---

## 결론

리팩토링을 통해 `parser.py`가:
- **97줄 → 14줄** (parse_company_detail)
- **F-42 → A-3** (복잡도)
- **모놀리식 → 계층화된 구조**

로 개선되어 유지보수가 쉬운 코드베이스로 변화했습니다.
