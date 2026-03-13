"""
parser.py - HTML 파싱 및 데이터 추출
"""

import re
from bs4 import BeautifulSoup


def parse_job_cards(html_source):
    """HTML에서 채용공고 카드를 파싱하여 리스트로 반환"""
    soup = BeautifulSoup(html_source, "html.parser")
    cards = soup.find_all("div", attrs={"data-sentry-component": "CardJob"})

    print(f"  발견된 카드 수: {len(cards)}")
    jobs = []

    for i, card in enumerate(cards, 1):
        try:
            job = extract_card_data(card)
            jobs.append(job)
            print(f"  [{i}] {job['company']} - {job['title']}")
        except Exception as e:
            print(f"  [{i}] 파싱 실패: {e}")

    return jobs


def extract_card_data(card):
    """
    개별 카드에서 전체 데이터 추출

    Args:
        card: BeautifulSoup 카드 엘리먼트

    Returns:
        dict: 추출된 채용공고 정보
    """
    return {
        "title": _extract_title(card),
        "company": _extract_company(card),
        "location": _extract_location(card),
        "experience": _extract_experience(card),
        "detail_url": _extract_detail_url(card),
        "industry": _extract_industry(card),
        "job_category": _extract_job_category(card),
        "salary": _extract_salary(card),
        "badge": _extract_badge(card),
        "apply_type": _extract_apply_type(card),
        "posted_date": _extract_posted_date(card),
        "deadline": _extract_deadline(card),
        "benefits": _extract_benefits(card),
    }


def _extract_title(card) -> str:
    """공고 제목 추출"""
    title_el = card.select_one('[class*="Typography_variant_size18"]')
    return title_el.get_text(strip=True) if title_el else ""


def _extract_company(card) -> str:
    """회사명 추출"""
    company_el = card.select_one('[class*="Typography_variant_size16"]')
    return company_el.get_text(strip=True) if company_el else ""


def _extract_location(card) -> str:
    """근무지역 추출"""
    location_chip = card.select_one('[class*="emoji--basicemoji-place2"]')
    if not location_chip:
        return ""

    chip_parent = location_chip.find_parent(
        attrs={"data-sentry-component": "GrayChip"}
    )
    if not chip_parent:
        return ""

    loc_text = chip_parent.select_one('[class*="Typography_variant_size14"]')
    return loc_text.get_text(strip=True) if loc_text else ""


def _extract_experience(card) -> str:
    """경력 조건 추출"""
    exp_el = card.select_one(
        '[class*="Typography_variant_size13"][class*="flex-shrink_0"]'
    )
    return exp_el.get_text(strip=True) if exp_el else ""


def _extract_detail_url(card) -> str:
    """상세 URL 추출 및 절대 경로 변환"""
    link_el = card.select_one('a[href*="/Recruit/GI_Read/"]')
    if not link_el:
        return ""

    href = link_el.get("href", "")
    if href.startswith("/"):
        href = "https://www.jobkorea.co.kr" + href

    return href


def _extract_industry(card) -> str:
    """업종 추출 (briefcase 아이콘 옆 GrayChip의 첫 번째 항목)"""
    industry_chip = card.select_one('[class*="emoji--basicemoji-briefcase"]')
    if not industry_chip:
        return ""

    chip_parent = industry_chip.find_parent(
        attrs={"data-sentry-component": "GrayChip"}
    )
    if not chip_parent:
        return ""

    text_el = chip_parent.select_one('[class*="Typography_variant_size14"]')
    if not text_el:
        return ""

    raw = text_el.get_text(strip=True)
    parts = [p.strip() for p in raw.split(",")]
    return parts[0] if parts else ""


def _extract_job_category(card) -> str:
    """직무 추출 (briefcase 아이콘 옆 GrayChip의 두 번째 이후 항목)"""
    industry_chip = card.select_one('[class*="emoji--basicemoji-briefcase"]')
    if not industry_chip:
        return ""

    chip_parent = industry_chip.find_parent(
        attrs={"data-sentry-component": "GrayChip"}
    )
    if not chip_parent:
        return ""

    text_el = chip_parent.select_one('[class*="Typography_variant_size14"]')
    if not text_el:
        return ""

    raw = text_el.get_text(strip=True)
    parts = [p.strip() for p in raw.split(",")]
    return ", ".join(parts[1:]) if len(parts) > 1 else ""


def _extract_salary(card) -> str:
    """급여 정보 추출"""
    salary_chip = card.select_one('[class*="emoji--basicemoji-money_bill"]')
    if not salary_chip:
        return ""

    chip_parent = salary_chip.find_parent(
        attrs={"data-sentry-component": "GrayChip"}
    )
    if not chip_parent:
        return ""

    sal_text = chip_parent.select_one('[class*="Typography_variant_size14"]')
    return sal_text.get_text(strip=True) if sal_text else ""


def _extract_badge(card) -> str:
    """뱃지 추출"""
    badge_el = card.select_one('[data-sentry-component="BadgeItem"] span')
    return badge_el.get_text(strip=True) if badge_el else ""


def _extract_apply_type(card) -> str:
    """지원 방식 추출"""
    apply_btn = card.select_one(
        '[class*="_16czznu"] [class*="Typography_variant_size12"]'
    )
    return apply_btn.get_text(strip=True) if apply_btn else ""


def _extract_date_spans(card):
    """날짜 관련 span 요소들 추출 (등록일, 마감일 파싱용 헬퍼)"""
    return card.select(
        '[class*="Typography_variant_size13"][class*="Typography_weight_regular"]'
    )


def _extract_posted_date(card) -> str:
    """등록일 추출"""
    date_spans = _extract_date_spans(card)
    dates = [
        s.get_text(strip=True) for s in date_spans
        if "등록" in s.get_text() or "마감" in s.get_text() or "채용" in s.get_text()
    ]
    return dates[0] if len(dates) > 0 else ""


def _extract_deadline(card) -> str:
    """마감일 추출"""
    date_spans = _extract_date_spans(card)
    dates = [
        s.get_text(strip=True) for s in date_spans
        if "등록" in s.get_text() or "마감" in s.get_text() or "채용" in s.get_text()
    ]
    return dates[1] if len(dates) > 1 else ""


def _extract_benefits(card) -> str:
    """복리후생 추출"""
    date_spans = _extract_date_spans(card)
    benefit_spans = [s.get_text(strip=True) for s in date_spans]
    benefit_texts = [
        t for t in benefit_spans
        if "지원" in t or "제도" in t or "보험" in t
    ]
    return ", ".join(benefit_texts) if benefit_texts else ""


def parse_company_detail(html: str) -> dict:
    """
    상세 페이지에서 회사 정보 추출 (Phase 2)

    3가지 파싱 전략을 순차적으로 시도:
    1. dl/dt/dd 구조
    2. table 구조
    3. 키워드 기반 탐색

    Args:
        html: 상세 페이지 HTML 소스

    Returns:
        dict: company_size, employee_count, establishment_year, homepage_url
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


def _parse_from_dl_structure(soup) -> dict:
    """
    dl/dt/dd 구조에서 회사 정보 추출

    Args:
        soup: BeautifulSoup 객체

    Returns:
        dict: 추출된 회사 정보
    """
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
    """
    table 구조에서 회사 정보 추출

    Args:
        soup: BeautifulSoup 객체

    Returns:
        dict: 추출된 회사 정보
    """
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
    """
    키워드 기반으로 회사 정보 추출 (폴백 전략)

    Args:
        soup: BeautifulSoup 객체

    Returns:
        dict: 추출된 회사 정보
    """
    details = _init_company_details()

    # 기업규모 키워드 탐색
    details["company_size"] = _extract_company_size_by_keyword(soup)

    # 설립연도 패턴 탐색
    details["establishment_year"] = _extract_establishment_year_by_pattern(soup)

    # 홈페이지 링크 탐색
    details["homepage_url"] = _extract_homepage_url(soup)

    return details


def _init_company_details() -> dict:
    """회사 정보 딕셔너리 초기화"""
    return {
        "company_size": None,
        "employee_count": None,
        "establishment_year": None,
        "homepage_url": None,
    }


def _extract_field_from_label_value(label: str, value: str, element, details: dict) -> None:
    """
    레이블-값 쌍에서 회사 정보 추출 (원본 details 딕셔너리 수정)

    Args:
        label: 필드 레이블 (예: "기업규모", "사원수")
        value: 필드 값
        element: BeautifulSoup 엘리먼트 (링크 탐색용)
        details: 결과를 저장할 딕셔너리
    """
    if "기업형태" in label or "기업규모" in label:
        details["company_size"] = value

    elif "사원수" in label or "직원수" in label:
        details["employee_count"] = value

    elif "설립" in label:
        details["establishment_year"] = _extract_year_from_text(value)

    elif "홈페이지" in label or "URL" in label:
        details["homepage_url"] = _extract_url_from_element(element, value)


def _extract_year_from_text(text: str) -> str:
    """
    텍스트에서 4자리 연도 추출

    Args:
        text: 연도가 포함된 텍스트 (예: "2010년 설립")

    Returns:
        str: 추출된 연도 또는 원본 텍스트
    """
    year_match = re.search(r"(\d{4})", text)
    return year_match.group(1) if year_match else text


def _extract_url_from_element(element, value: str) -> str:
    """
    엘리먼트에서 URL 추출 (링크 또는 텍스트)

    Args:
        element: BeautifulSoup 엘리먼트
        value: 텍스트 값

    Returns:
        str: 추출된 URL 또는 None
    """
    link = element.find("a")
    if link and link.get("href"):
        return link.get("href")
    elif value and value.startswith("http"):
        return value
    return None


def _extract_company_size_by_keyword(soup) -> str:
    """
    기업규모를 키워드로 탐색

    Args:
        soup: BeautifulSoup 객체

    Returns:
        str: 기업규모 또는 None
    """
    size_keywords = ["대기업", "중견기업", "중소기업", "외국계", "공기업", "스타트업"]

    for size_keyword in size_keywords:
        size_el = soup.find(string=lambda t: t and size_keyword in t)
        if size_el:
            return size_keyword

    return None


def _extract_establishment_year_by_pattern(soup) -> str:
    """
    설립연도를 패턴으로 탐색

    Args:
        soup: BeautifulSoup 객체

    Returns:
        str: 설립연도 또는 None
    """
    year_pattern = soup.find(string=re.compile(r"설립\s*:?\s*\d{4}"))
    if year_pattern:
        year_match = re.search(r"(\d{4})", year_pattern)
        if year_match:
            return year_match.group(1)

    return None


def _extract_homepage_url(soup) -> str:
    """
    홈페이지 URL을 링크에서 탐색

    Args:
        soup: BeautifulSoup 객체

    Returns:
        str: 홈페이지 URL 또는 None
    """
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)

        # 홈페이지 텍스트가 있거나, jobkorea가 아닌 외부 링크
        is_homepage_link = "홈페이지" in text
        is_external_link = href.startswith("http") and "jobkorea" not in href

        if is_homepage_link or is_external_link:
            if "jobkorea" not in href and "javascript" not in href:
                return href

    return None
