"""
parser.py - HTML 파싱 및 데이터 추출
"""

import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

JOB_LIST_SELECTOR = '[data-sentry-component="JobList"]'
CARD_JOB_SELECTOR = '[data-sentry-component="CardJob"]'
JD_LINK_SELECTOR = 'a[href*="/Recruit/GI_Read/"]'
JOB_DETAIL_COMPANY_LINK_SELECTOR = (
    '[data-sentry-component="CompanyName"] a[href*="/Recruit/Co_Read/C/"]'
)
JOB_DETAIL_COMPANY_MORE_SELECTOR = (
    '#company-section [data-sentry-component="MoreButton"][href*="/Recruit/Co_Read/C/"]'
)
JOB_DETAIL_RECRUITMENT_GUIDELINES_SELECTOR = (
    '#details-section [data-sentry-component="RecruitmentGuidelines"]'
)
TITLE_SELECTOR = (
    'a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size18"]'
)
COMPANY_SELECTOR = (
    'a[href*="/Recruit/GI_Read/"] span[class*="Typography_variant_size16"]'
)
GRAY_CHIP_SELECTOR = '[data-sentry-component="GrayChip"]'
COMPANY_INFO_SECTION_SELECTOR = '.company-infomation-row.basic-infomation'
COMPANY_INFO_TABLE_SELECTOR = 'table.table-basic-infomation-primary'
COMPANY_INFO_ROW_SELECTOR = 'tr.field'
COMPANY_INFO_LABEL_SELECTOR = 'th.field-label'
COMPANY_INFO_VALUE_SELECTOR = 'td.field-value'
COMPANY_HEADER_HOMEPAGE_SELECTOR = (
    '.company-header .add-ons .home a.button-home, '
    '.company-header-branding .add-ons .home a.button-home'
)
SUPER_COMPANY_INFO_SELECTOR = '.corpInfo'

CAREER_TYPE_MAP = {
    "1": "신입",
    "2": "경력",
    "3": "신입·경력",
    "4": "경력무관",
}

EMPLOYMENT_TYPE_MAP = {
    "1": "정규직",
    "2": "계약직",
    "3": "인턴",
}


def parse_job_cards(html_source):
    """HTML에서 채용공고 카드를 파싱하여 리스트로 반환"""
    soup = BeautifulSoup(html_source, "html.parser")
    cards = _find_job_cards(soup)
    metadata_by_job_id = _build_search_metadata_by_job_id(html_source, cards)

    logger.debug("목록 카드 수: %s", len(cards))
    jobs = []

    for i, card in enumerate(cards, 1):
        try:
            job_id = _extract_job_id_from_card(card)
            job = extract_card_data(card, metadata_by_job_id.get(job_id))
            jobs.append(job)
            logger.debug("카드 파싱 성공 [%s] %s - %s", i, job["company"], job["title"])
        except Exception as e:
            logger.warning("카드 파싱 실패 [%s]: %s", i, e)

    return jobs


def filter_jobs_by_search_preferences(
    jobs: list[dict],
    allowed_locations: list[str] | None = None,
    allowed_experience_types: list[str] | None = None,
    allowed_employment_types: list[str] | None = None,
) -> list[dict]:
    """env 기반 검색 선호 조건으로 공고 목록을 필터링한다."""
    allowed_locations = _normalize_filter_values(allowed_locations)
    allowed_experience_types = _normalize_filter_values(allowed_experience_types)
    allowed_employment_types = _normalize_filter_values(allowed_employment_types)

    if not any((allowed_locations, allowed_experience_types, allowed_employment_types)):
        return jobs

    filtered = []
    for job in jobs:
        if not _matches_location_filter(job, allowed_locations):
            continue
        if not _matches_experience_filter(job, allowed_experience_types):
            continue
        if not _matches_employment_filter(job, allowed_employment_types):
            continue
        filtered.append(job)

    return filtered


def parse_company_page_url_from_job_detail(html: str) -> str | None:
    """JD 상세 HTML에서 회사 페이지 URL을 추출한다."""
    soup = BeautifulSoup(html, "html.parser")

    for selector in (
        JOB_DETAIL_COMPANY_LINK_SELECTOR,
        JOB_DETAIL_COMPANY_MORE_SELECTOR,
    ):
        link_el = soup.select_one(selector)
        if link_el and link_el.get("href"):
            return _to_absolute_jobkorea_url(link_el.get("href"))

    company_id_match = re.search(r"dimension47[^0-9]*(\d{4,})", html)
    if company_id_match:
        company_id = company_id_match.group(1)
        return f"https://www.jobkorea.co.kr/Recruit/Co_Read/C/{company_id}"

    return None


def _find_job_cards(soup):
    """검색 결과 메인 목록(JobList) 내부 카드만 우선 사용한다."""
    job_list = soup.select_one(JOB_LIST_SELECTOR)
    if job_list is not None:
        return job_list.select(CARD_JOB_SELECTOR)

    cards = soup.select(CARD_JOB_SELECTOR)
    logger.warning("JobList 컨테이너를 찾지 못해 전역 CardJob %s개로 폴백합니다.", len(cards))
    return cards


def _to_absolute_jobkorea_url(url: str) -> str:
    """상대 URL을 잡코리아 절대 URL로 정규화한다."""
    if not url:
        return ""
    if url.startswith("/"):
        return "https://www.jobkorea.co.kr" + url
    return url


def _normalize_filter_values(values: list[str] | None) -> list[str]:
    """필터 입력 리스트를 빈 값 없이 정규화한다."""
    if not values:
        return []
    return [value.strip() for value in values if value and value.strip()]


def _extract_job_id_from_detail_url(detail_url: str) -> str | None:
    """GI_Read 상세 URL에서 job id를 추출한다."""
    match = re.search(r"/Recruit/GI_Read/(\d+)", detail_url or "")
    if not match:
        return None
    return match.group(1)


def _extract_job_id_from_card(card) -> str | None:
    """카드에서 job id를 추출한다."""
    return _extract_job_id_from_detail_url(_extract_detail_url(card))


def _build_search_metadata_by_job_id(html_source: str, cards) -> dict[str, dict]:
    """검색 결과 hydration에서 카드별 메타데이터를 복원한다."""
    metadata_by_job_id: dict[str, dict] = {}

    for card in cards:
        job_id = _extract_job_id_from_card(card)
        if not job_id or job_id in metadata_by_job_id:
            continue
        metadata_by_job_id[job_id] = _extract_search_metadata_for_job_id(
            html_source,
            job_id,
        )

    return metadata_by_job_id


def _extract_search_metadata_for_job_id(html_source: str, job_id: str) -> dict:
    """특정 job id에 대한 hydration 메타데이터를 추출한다."""
    pattern = re.compile(
        rf'\\\"id\\\":\\\"{re.escape(job_id)}\\\"'
        rf'.*?\\\"employmentTypeCodeList\\\":\[(?P<employment>.*?)\]'
        rf'.*?\\\"areaCodeList\\\":\[(?P<areas>.*?)\]'
        rf'.*?\\\"careerType\\\":\\\"(?P<career>.*?)\\\"',
        re.S,
    )
    match = pattern.search(html_source)
    if not match:
        return {
            "experience_type": None,
            "employment_types": [],
            "location_codes": [],
        }

    location_codes = _parse_escaped_list_fragment(match.group("areas"))
    employment_codes = _parse_escaped_list_fragment(match.group("employment"))
    career_type = CAREER_TYPE_MAP.get(match.group("career"))

    return {
        "experience_type": career_type,
        "employment_types": _map_employment_codes_to_labels(employment_codes),
        "location_codes": location_codes,
    }


def _parse_escaped_list_fragment(fragment: str) -> list[str]:
    """next.js hydration 안의 escaped list fragment를 리스트로 정규화한다."""
    if not fragment or not fragment.strip():
        return []

    values = []
    for item in fragment.split(","):
        normalized = item.strip().strip('"').replace('\\"', "").replace("\\", "").strip()
        if normalized:
            values.append(normalized)
    return values


def _map_employment_codes_to_labels(codes: list[str]) -> list[str]:
    """잡코리아 employment code를 사람이 읽는 라벨로 변환한다."""
    labels = []
    for code in codes:
        normalized_code = code.split("/")[0]
        label = EMPLOYMENT_TYPE_MAP.get(normalized_code)
        if label and label not in labels:
            labels.append(label)
    return labels


def _extract_gray_chip_text(card, icon_selector: str) -> str:
    """아이콘 기준으로 GrayChip 텍스트를 추출한다."""
    chip_icon = card.select_one(f"{GRAY_CHIP_SELECTOR} {icon_selector}")
    if not chip_icon:
        return ""

    chip_parent = chip_icon.find_parent(attrs={"data-sentry-component": "GrayChip"})
    if not chip_parent:
        return ""

    text_el = chip_parent.select_one('[class*="Typography_variant_size14"]')
    return text_el.get_text(strip=True) if text_el else ""


def extract_card_data(card, search_metadata: dict | None = None):
    """
    개별 카드에서 전체 데이터 추출

    Args:
        card: BeautifulSoup 카드 엘리먼트

    Returns:
        dict: 추출된 채용공고 정보
    """
    detail_url = _extract_detail_url(card)
    experience = _extract_experience(card)
    title = _extract_title(card)
    metadata = search_metadata or {}

    return {
        "title": title,
        "company": _extract_company(card),
        "location": _extract_location(card),
        "experience": experience,
        "experience_type": metadata.get("experience_type") or _infer_experience_type(experience),
        "detail_url": detail_url,
        "industry": _extract_industry(card),
        "job_category": _extract_job_category(card),
        "salary": _extract_salary(card),
        "badge": _extract_badge(card),
        "apply_type": _extract_apply_type(card),
        "employment_types": metadata.get("employment_types", []) or _infer_employment_types(title),
        "location_codes": metadata.get("location_codes", []),
        "posted_date": _extract_posted_date(card),
        "deadline": _extract_deadline(card),
        "benefits": _extract_benefits(card),
    }


def _infer_experience_type(experience_text: str) -> str | None:
    """카드 텍스트에서 경력 타입을 추론한다."""
    normalized = (experience_text or "").strip()
    if not normalized:
        return None
    if "경력무관" in normalized:
        return "경력무관"
    if "신입" in normalized and "경력" in normalized:
        return "신입·경력"
    if "신입" in normalized:
        return "신입"
    if "경력" in normalized:
        return "경력"
    return None


def _infer_employment_types(title: str) -> list[str]:
    """카드 텍스트만 있을 때 고용형태를 보수적으로 추론한다."""
    normalized = (title or "").strip()
    if "인턴" in normalized:
        return ["인턴"]
    return []


def _extract_location_region(location: str) -> str | None:
    """카드 위치 텍스트에서 대표 지역명을 추출한다."""
    normalized = (location or "").strip()
    if not normalized:
        return None
    return normalized.split()[0]


def _matches_location_filter(job: dict, allowed_locations: list[str]) -> bool:
    """지역 필터 일치 여부"""
    if not allowed_locations:
        return True

    region = _extract_location_region(job.get("location", ""))
    if region and region in allowed_locations:
        return True

    location_text = (job.get("location") or "").strip()
    return any(location in location_text for location in allowed_locations)


def _matches_experience_filter(job: dict, allowed_experience_types: list[str]) -> bool:
    """경력 타입 필터 일치 여부"""
    if not allowed_experience_types:
        return True

    experience_type = job.get("experience_type") or _infer_experience_type(job.get("experience", ""))
    return experience_type in allowed_experience_types


def _matches_employment_filter(job: dict, allowed_employment_types: list[str]) -> bool:
    """고용형태 필터 일치 여부"""
    if not allowed_employment_types:
        return True

    employment_types = job.get("employment_types") or _infer_employment_types(job.get("title", ""))
    return bool(set(employment_types) & set(allowed_employment_types))


def _extract_title(card) -> str:
    """공고 제목 추출"""
    title_el = card.select_one(TITLE_SELECTOR)
    return title_el.get_text(strip=True) if title_el else ""


def _extract_company(card) -> str:
    """회사명 추출"""
    company_el = card.select_one(COMPANY_SELECTOR)
    return company_el.get_text(strip=True) if company_el else ""


def _extract_location(card) -> str:
    """근무지역 추출"""
    return _extract_gray_chip_text(card, '[class*="emoji--basicemoji-place2"]')


def _extract_experience(card) -> str:
    """경력 조건 추출"""
    exp_el = card.select_one(
        '[class*="Typography_variant_size13"][class*="flex-shrink_0"]'
    )
    return exp_el.get_text(strip=True) if exp_el else ""


def _extract_detail_url(card) -> str:
    """상세 URL 추출 및 절대 경로 변환"""
    for link_el in card.select(JD_LINK_SELECTOR):
        href = link_el.get("href", "")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.jobkorea.co.kr" + href
        return href

    return ""


def _extract_industry(card) -> str:
    """업종 추출 (briefcase 아이콘 옆 GrayChip의 첫 번째 항목)"""
    raw = _extract_gray_chip_text(card, '[class*="emoji--basicemoji-briefcase"]')
    parts = [p.strip() for p in raw.split(",")]
    return parts[0] if parts else ""


def _extract_job_category(card) -> str:
    """직무 추출 (briefcase 아이콘 옆 GrayChip의 두 번째 이후 항목)"""
    raw = _extract_gray_chip_text(card, '[class*="emoji--basicemoji-briefcase"]')
    parts = [p.strip() for p in raw.split(",")]
    return ", ".join(parts[1:]) if len(parts) > 1 else ""


def _extract_salary(card) -> str:
    """급여 정보 추출"""
    return _extract_gray_chip_text(card, '[class*="emoji--basicemoji-money_bill"]')


def _extract_badge(card) -> str:
    """뱃지 추출"""
    badge_el = card.select_one('[data-sentry-component="BadgeItem"] span')
    return badge_el.get_text(strip=True) if badge_el else ""


def _extract_apply_type(card) -> str:
    """지원 방식 추출"""
    for button in card.select('[data-sentry-component="BaseButton"]'):
        text = " ".join(button.get_text(" ", strip=True).split())
        if text in {"즉시 지원", "홈페이지 지원"}:
            return text
        if text == "즉시지원":
            return "즉시 지원"
        if text == "홈페이지지원":
            return "홈페이지 지원"

    return ""


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

    if _is_job_detail_page(soup) and not _is_company_page(soup):
        logger.debug("JD 상세 페이지로 감지되어 회사 페이지 파싱을 건너뜁니다.")
        return _init_company_details()

    if _is_company_page(soup):
        details = _parse_from_company_page_structure(soup)
        if any(details.values()):
            return details

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


def _is_job_detail_page(soup) -> bool:
    """현재 HTML이 JD 상세 페이지인지 추정한다."""
    return any(
        (
            soup.select_one(JOB_DETAIL_COMPANY_LINK_SELECTOR),
            soup.select_one(JOB_DETAIL_COMPANY_MORE_SELECTOR),
            soup.select_one(JOB_DETAIL_RECRUITMENT_GUIDELINES_SELECTOR),
            soup.select_one('script[data-sentry-component="JobPostingSchema"]'),
        )
    )


def _is_company_page(soup) -> bool:
    """현재 HTML이 회사 상세 페이지인지 추정한다."""
    return any(
        (
            soup.select_one(COMPANY_INFO_SECTION_SELECTOR),
            soup.select_one(COMPANY_INFO_TABLE_SELECTOR),
            soup.select_one(COMPANY_HEADER_HOMEPAGE_SELECTOR),
            soup.select_one(SUPER_COMPANY_INFO_SELECTOR),
        )
    )


def _parse_from_company_page_structure(soup) -> dict:
    """회사 페이지의 기본 정보 테이블을 우선 파싱한다."""
    details = _init_company_details()
    table = _find_primary_company_info_table(soup)

    if table is not None:
        for label, value, element in _iter_label_value_pairs(table):
            _extract_field_from_label_value(label, value, element, details)
    else:
        details = _parse_from_super_company_structure(soup)

    if not details["homepage_url"]:
        details["homepage_url"] = _extract_company_homepage_from_header(soup)

    return details


def _parse_from_super_company_structure(soup) -> dict:
    """슈퍼기업관 레이아웃의 corpInfo 블록을 파싱한다."""
    details = _init_company_details()
    corp_info = soup.select_one(SUPER_COMPANY_INFO_SELECTOR)
    if corp_info is None:
        return details

    for item in corp_info.select("li"):
        texts = [p.get_text(" ", strip=True) for p in item.select("p") if p.get_text(" ", strip=True)]
        if len(texts) < 2:
            continue

        label, value = _normalize_super_company_item(texts)
        if label and value:
            _extract_field_from_label_value(label, value, item, details)

    if not details["homepage_url"]:
        details["homepage_url"] = _extract_company_homepage_from_header(soup)

    return details


def _normalize_super_company_item(texts: list[str]) -> tuple[str | None, str | None]:
    """슈퍼기업관 corpInfo item을 label/value 쌍으로 정규화한다."""
    last_text = texts[-1]
    first_text = texts[0]

    if "사원수" in last_text:
        return "사원수", first_text

    if "기업형태" in last_text or "기업규모" in last_text:
        return "기업형태", first_text

    if "설립" in last_text:
        return "설립", last_text

    if any("설립" in text for text in texts):
        establishment_text = next(text for text in texts if "설립" in text)
        return "설립", establishment_text

    if "홈페이지" in last_text:
        return "홈페이지", first_text

    return None, None


def _find_primary_company_info_table(soup):
    """회사 페이지 핵심 정보 테이블을 우선 탐색한다."""
    section = soup.select_one(COMPANY_INFO_SECTION_SELECTOR)
    if section is not None:
        table = section.select_one(COMPANY_INFO_TABLE_SELECTOR)
        if table is not None:
            return table

    return soup.select_one(COMPANY_INFO_TABLE_SELECTOR)


def _iter_label_value_pairs(container):
    """테이블/행에서 레이블-값 쌍을 순서대로 순회한다."""
    for row in container.find_all("tr"):
        labels = row.find_all("th", recursive=False)
        values = row.find_all("td", recursive=False)
        if not labels or not values:
            continue

        for label_el, value_el in zip(labels, values):
            label = label_el.get_text(" ", strip=True)
            value = value_el.get_text(" ", strip=True)
            if label:
                yield label, value, value_el


def _extract_company_homepage_from_header(soup) -> str | None:
    """회사 페이지 헤더 영역의 홈페이지 링크를 fallback으로 사용한다."""
    link = soup.select_one(COMPANY_HEADER_HOMEPAGE_SELECTOR)
    if link and link.get("href"):
        return link.get("href")
    return None


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
        for label, value, element in _iter_label_value_pairs(table):
            _extract_field_from_label_value(label, value, element, details)

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
    if "기업구분" in label or "기업형태" in label or "기업규모" in label:
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
