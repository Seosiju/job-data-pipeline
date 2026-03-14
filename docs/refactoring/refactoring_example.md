# 리팩토링 예시: parse_company_detail()

## Before (복잡도: F-42, 97줄)

```python
def parse_company_detail(html: str) -> dict:
    """상세 페이지에서 회사 정보 추출 (Phase 2)"""
    soup = BeautifulSoup(html, "html.parser")
    details = {
        "company_size": None,
        "employee_count": None,
        "establishment_year": None,
        "homepage_url": None,
    }

    # 방법 1: dl/dt/dd 구조에서 추출 (tbRow 클래스)
    for dl in soup.find_all("dl"):
        dt_elements = dl.find_all("dt")
        dd_elements = dl.find_all("dd")

        for dt, dd in zip(dt_elements, dd_elements):
            label = dt.get_text(strip=True)
            value = dd.get_text(strip=True)

            if "기업형태" in label or "기업규모" in label:
                details["company_size"] = value
            elif "사원수" in label or "직원수" in label:
                details["employee_count"] = value
            elif "설립" in label:
                # 설립일에서 연도 추출
                year_match = re.search(r"(\d{4})", value)
                if year_match:
                    details["establishment_year"] = year_match.group(1)
                else:
                    details["establishment_year"] = value
            elif "홈페이지" in label or "URL" in label:
                link = dd.find("a")
                if link and link.get("href"):
                    details["homepage_url"] = link.get("href")
                elif value and value.startswith("http"):
                    details["homepage_url"] = value

    # 방법 2: 테이블 구조에서 추출
    if not any(details.values()):
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)

                    if "기업형태" in label or "기업규모" in label:
                        details["company_size"] = value
                    elif "사원수" in label or "직원수" in label:
                        details["employee_count"] = value
                    elif "설립" in label:
                        year_match = re.search(r"(\d{4})", value)
                        if year_match:
                            details["establishment_year"] = year_match.group(1)
                        else:
                            details["establishment_year"] = value
                    elif "홈페이지" in label:
                        link = cells[1].find("a")
                        if link and link.get("href"):
                            details["homepage_url"] = link.get("href")
                        elif value and value.startswith("http"):
                            details["homepage_url"] = value

    # 방법 3: 특정 클래스명으로 직접 탐색
    if not any(details.values()):
        # 기업규모 (대기업, 중견기업, 중소기업 등)
        for size_keyword in ["대기업", "중견기업", "중소기업", "외국계", "공기업", "스타트업"]:
            size_el = soup.find(string=lambda t: t and size_keyword in t)
            if size_el:
                details["company_size"] = size_keyword
                break

        # 설립연도 패턴
        year_pattern = soup.find(string=re.compile(r"설립\s*:?\s*\d{4}"))
        if year_pattern:
            year_match = re.search(r"(\d{4})", year_pattern)
            if year_match:
                details["establishment_year"] = year_match.group(1)

        # 홈페이지 링크
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            text = a_tag.get_text(strip=True)
            if "홈페이지" in text or (href.startswith("http") and "jobkorea" not in href):
                if "jobkorea" not in href and "javascript" not in href:
                    details["homepage_url"] = href
                    break

    return details
```

**문제점:**
- 3가지 파싱 전략이 하나의 함수에 혼재
- 중복 코드가 많음 (방법 1과 방법 2가 거의 동일한 로직)
- 중첩 깊이가 깊음 (최대 5단계)
- 한 함수가 너무 많은 책임을 가짐

---

## After (복잡도: A-3, 14줄)

```python
def parse_company_detail(html: str) -> dict:
    """
    상세 페이지에서 회사 정보 추출 (Phase 2)

    3가지 파싱 전략을 순차적으로 시도:
    1. dl/dt/dd 구조
    2. table 구조
    3. 키워드 기반 탐색
    """
    soup = BeautifulSoup(html, "html.parser")

    # 방법 1: dl/dt/dd 구조에서 추출
    details = _parse_from_dl_structure(soup)
    if any(details.values()):
        return details

    # 방법 2: 테이블 구조에서 추출
    details = _parse_from_table_structure(soup)
    if any(details.values()):
        return details

    # 방법 3: 키워드 기반 폴백
    details = _parse_from_keywords(soup)
    return details
```

**분리된 헬퍼 함수들:**

```python
def _parse_from_dl_structure(soup) -> dict:
    """dl/dt/dd 구조에서 회사 정보 추출"""
    details = _init_company_details()

    for dl in soup.find_all("dl"):
        dt_elements = dl.find_all("dt")
        dd_elements = dl.find_all("dd")

        for dt, dd in zip(dt_elements, dd_elements):
            label = dt.get_text(strip=True)
            value = dd.get_text(strip=True)
            _extract_field_from_label_value(label, value, dd, details)

    return details


def _parse_from_table_structure(soup) -> dict:
    """table 구조에서 회사 정보 추출"""
    details = _init_company_details()

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                _extract_field_from_label_value(label, value, cells[1], details)

    return details


def _parse_from_keywords(soup) -> dict:
    """키워드 기반으로 회사 정보 추출 (폴백 전략)"""
    details = _init_company_details()
    details["company_size"] = _extract_company_size_by_keyword(soup)
    details["establishment_year"] = _extract_establishment_year_by_pattern(soup)
    details["homepage_url"] = _extract_homepage_url(soup)
    return details


def _extract_field_from_label_value(label: str, value: str, element, details: dict) -> None:
    """레이블-값 쌍에서 회사 정보 추출 (원본 details 딕셔너리 수정)"""
    if "기업형태" in label or "기업규모" in label:
        details["company_size"] = value
    elif "사원수" in label or "직원수" in label:
        details["employee_count"] = value
    elif "설립" in label:
        details["establishment_year"] = _extract_year_from_text(value)
    elif "홈페이지" in label or "URL" in label:
        details["homepage_url"] = _extract_url_from_element(element, value)
```

**개선 효과:**

1. **가독성**: 메인 함수가 "무엇을" 하는지 명확히 보임
2. **재사용성**: 중복 로직을 `_extract_field_from_label_value()` 하나로 통합
3. **테스트 용이성**: 각 전략을 독립적으로 테스트 가능
4. **유지보수성**: 버그 발생 시 문제 함수만 수정
5. **확장성**: 새로운 파싱 전략 추가 시 기존 코드 영향 없음

---

## 복잡도 비교

| 함수 | Before | After |
|------|--------|-------|
| `parse_company_detail()` | F (42) | A (3) |
| `_parse_from_dl_structure()` | - | A (3) |
| `_parse_from_table_structure()` | - | A (4) |
| `_parse_from_keywords()` | - | A (1) |
| `_extract_field_from_label_value()` | - | B (8) |
| `_extract_year_from_text()` | - | A (2) |
| `_extract_url_from_element()` | - | A (5) |
| `_extract_company_size_by_keyword()` | - | A (4) |
| `_extract_establishment_year_by_pattern()` | - | A (3) |
| `_extract_homepage_url()` | - | B (7) |

**결과**: 하나의 F등급 함수가 → 10개의 A~B등급 함수로 분리
