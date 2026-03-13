"""
validators.py - 데이터 검증 및 정제
"""

import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def validate_job_posting(data: dict) -> dict:
    """
    채용공고 데이터 검증 및 정제

    검증 항목:
    - 필수 필드 (title, company) 누락 체크
    - 급여: 비현실적 값 필터링, "협의" -> None
    - 날짜: 형식 검증, "채용시까지" 처리
    - detail_url: 유효성 검증

    Args:
        data: 원본 채용공고 데이터 dict

    Returns:
        dict: 정제된 데이터 (검증 실패 시에도 저장은 진행, 로그만 기록)
    """
    validated = data.copy()

    # 1. 필수 필드 검증
    if not validated.get("title") or not validated.get("title").strip():
        logger.warning("필수 필드 누락: title이 비어있음")
        validated["title"] = "제목 없음"

    if not validated.get("company") or not validated.get("company").strip():
        logger.warning("필수 필드 누락: company가 비어있음")
        validated["company"] = "회사명 없음"

    # 2. 급여 검증 및 정제
    salary = validated.get("salary", "")
    validated["salary"] = normalize_salary(salary)

    # 3. 날짜 검증 및 정제
    posted_date = validated.get("posted_date", "")
    validated["posted_date"] = normalize_date(posted_date, "posted_date")

    deadline = validated.get("deadline", "")
    validated["deadline"] = normalize_deadline(deadline)

    # 4. detail_url 검증
    detail_url = validated.get("detail_url", "")
    if detail_url and not is_valid_url(detail_url):
        logger.warning(f"유효하지 않은 URL: {detail_url}")
        validated["detail_url"] = ""

    # 5. 경력 정제
    experience = validated.get("experience", "")
    validated["experience"] = normalize_experience(experience)

    # 6. 위치 정제
    location = validated.get("location", "")
    validated["location"] = normalize_location(location)

    return validated


def validate_company_details(data: dict) -> dict:
    """
    회사 정보 검증 및 정제

    검증 항목:
    - 설립연도: 1900~현재 범위
    - 사원수: "10명" -> 숫자 추출, 비현실적 값 필터링
    - URL: 형식 검증

    Args:
        data: 원본 회사 정보 dict

    Returns:
        dict: 정제된 데이터
    """
    validated = data.copy()

    # 1. 설립연도 검증
    establishment_year = validated.get("establishment_year")
    if establishment_year:
        validated["establishment_year"] = normalize_establishment_year(establishment_year)

    # 2. 사원수 정제
    employee_count = validated.get("employee_count")
    if employee_count:
        validated["employee_count"] = normalize_employee_count(employee_count)

    # 3. 회사 규모 정제
    company_size = validated.get("company_size")
    if company_size:
        validated["company_size"] = normalize_company_size(company_size)

    # 4. 홈페이지 URL 검증
    homepage_url = validated.get("homepage_url")
    if homepage_url and not is_valid_url(homepage_url):
        logger.warning(f"유효하지 않은 홈페이지 URL: {homepage_url}")
        validated["homepage_url"] = None

    return validated


# ============================================================================
# 급여 정제
# ============================================================================

def normalize_salary(salary: str) -> Optional[str]:
    """
    급여 정보 정제

    - "협의", "면접 후 결정" 등 -> None
    - 비현실적 값 필터링 (연봉 10억 이상 등)
    - 형식 통일: "3000만원 ~ 4000만원" -> "3,000만원 ~ 4,000만원"

    Args:
        salary: 원본 급여 문자열

    Returns:
        정제된 급여 문자열 또는 None
    """
    if not salary or not salary.strip():
        return None

    salary = salary.strip()

    # "협의", "면접 후 결정" 등의 키워드 -> None
    negotiable_keywords = ["협의", "면접", "상담", "결정", "논의"]
    if any(keyword in salary for keyword in negotiable_keywords):
        return None

    # 숫자 추출 (만원, 억원 단위)
    # 예: "3000만원" -> 3000, "1억원" -> 10000 (만원 단위로 변환)
    try:
        # "억" 단위 체크
        if "억" in salary:
            amount_match = re.search(r"(\d+(?:,?\d+)*)\s*억", salary)
            if amount_match:
                amount = int(amount_match.group(1).replace(",", ""))
                # 연봉 100억 이상은 비현실적
                if amount >= 100:
                    logger.warning(f"비현실적 급여 값: {salary}")
                    return None

        # "만원" 단위 체크
        elif "만원" in salary or "만" in salary:
            amount_match = re.search(r"(\d+(?:,?\d+)*)\s*만", salary)
            if amount_match:
                amount = int(amount_match.group(1).replace(",", ""))
                # 연봉 100억(1000000만원) 이상은 비현실적
                if amount >= 1000000:
                    logger.warning(f"비현실적 급여 값: {salary}")
                    return None

        return salary

    except Exception as e:
        logger.debug(f"급여 파싱 실패: {salary} - {e}")
        return salary


# ============================================================================
# 날짜 정제
# ============================================================================

def normalize_date(date_str: str, field_name: str) -> Optional[str]:
    """
    날짜 문자열 정제

    Args:
        date_str: 원본 날짜 문자열
        field_name: 필드명 (로깅용)

    Returns:
        정제된 날짜 문자열 또는 None
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    # "등록:" 제거
    date_str = re.sub(r"등록\s*[:：]?\s*", "", date_str)

    return date_str


def normalize_deadline(deadline: str) -> Optional[str]:
    """
    마감일 정제

    - "채용시까지", "상시채용" -> "상시채용"
    - "마감:" 제거

    Args:
        deadline: 원본 마감일 문자열

    Returns:
        정제된 마감일 문자열 또는 None
    """
    if not deadline or not deadline.strip():
        return None

    deadline = deadline.strip()

    # "채용시까지", "상시채용" 등 -> "상시채용"
    ongoing_keywords = ["채용시", "상시", "수시"]
    if any(keyword in deadline for keyword in ongoing_keywords):
        return "상시채용"

    # "마감:" 제거
    deadline = re.sub(r"마감\s*[:：]?\s*", "", deadline)

    return deadline


# ============================================================================
# 회사 정보 정제
# ============================================================================

def normalize_establishment_year(year_str: str) -> Optional[str]:
    """
    설립연도 검증 및 정제

    - 1900년 ~ 현재년도 범위 체크
    - "2020년 설립" -> "2020"

    Args:
        year_str: 원본 설립연도 문자열

    Returns:
        정제된 연도 문자열(YYYY) 또는 None
    """
    if not year_str or not year_str.strip():
        return None

    year_str = year_str.strip()

    # 연도 추출 (4자리 숫자)
    year_match = re.search(r"(\d{4})", year_str)
    if not year_match:
        logger.warning(f"설립연도 파싱 실패: {year_str}")
        return None

    year = int(year_match.group(1))
    current_year = datetime.now().year

    # 1900년 ~ 현재년도 범위 체크
    if year < 1900 or year > current_year:
        logger.warning(f"설립연도 범위 오류: {year} (유효 범위: 1900~{current_year})")
        return None

    return str(year)


def normalize_employee_count(count_str: str) -> Optional[str]:
    """
    사원수 정제

    - "10명" -> 숫자 추출
    - "1000명 이상" -> "1000명 이상" 유지
    - 비현실적 값(100만명 이상) 필터링

    Args:
        count_str: 원본 사원수 문자열

    Returns:
        정제된 사원수 문자열 또는 None
    """
    if not count_str or not count_str.strip():
        return None

    count_str = count_str.strip()

    # 숫자 추출
    count_match = re.search(r"(\d+(?:,?\d+)*)", count_str)
    if not count_match:
        logger.debug(f"사원수 파싱 실패: {count_str}")
        return count_str

    try:
        count = int(count_match.group(1).replace(",", ""))

        # 비현실적 값 필터링 (100만명 이상)
        if count >= 1000000:
            logger.warning(f"비현실적 사원수 값: {count_str}")
            return None

        return count_str

    except Exception as e:
        logger.debug(f"사원수 검증 실패: {count_str} - {e}")
        return count_str


def normalize_company_size(size_str: str) -> Optional[str]:
    """
    회사 규모 정제

    - "중소기업 (주식회사)" -> "중소기업"
    - 표준 카테고리로 통일

    Args:
        size_str: 원본 회사 규모 문자열

    Returns:
        정제된 회사 규모 문자열 또는 None
    """
    if not size_str or not size_str.strip():
        return None

    size_str = size_str.strip()

    # 표준 카테고리 매핑
    size_mapping = {
        "대기업": ["대기업", "대규모"],
        "중견기업": ["중견기업", "중견"],
        "중소기업": ["중소기업", "중소"],
        "외국계기업": ["외국계", "외국인"],
        "공기업": ["공기업", "공공"],
        "스타트업": ["스타트업", "벤처"],
    }

    for standard, keywords in size_mapping.items():
        if any(keyword in size_str for keyword in keywords):
            return standard

    # 괄호 안 내용 제거 (예: "중소기업 (주식회사)" -> "중소기업")
    size_str = re.sub(r"\s*\([^)]*\)", "", size_str)

    return size_str


# ============================================================================
# 기타 정제 함수
# ============================================================================

def normalize_experience(experience: str) -> Optional[str]:
    """
    경력 정보 정제

    - "신입", "경력무관" 등 통일
    - "3년~5년" -> "3년 ~ 5년"

    Args:
        experience: 원본 경력 문자열

    Returns:
        정제된 경력 문자열 또는 None
    """
    if not experience or not experience.strip():
        return None

    experience = experience.strip()

    # 표준 카테고리 매핑
    if "신입" in experience or "인턴" in experience:
        return "신입"
    elif "무관" in experience or "관계없음" in experience:
        return "경력무관"

    return experience


def normalize_location(location: str) -> Optional[str]:
    """
    근무지역 정제

    - "서울 강남구" -> "서울 강남구"
    - 여러 지역 -> 첫 번째 지역만

    Args:
        location: 원본 위치 문자열

    Returns:
        정제된 위치 문자열 또는 None
    """
    if not location or not location.strip():
        return None

    location = location.strip()

    # 여러 지역이 콤마나 슬래시로 구분된 경우 -> 첫 번째만
    if "," in location:
        location = location.split(",")[0].strip()
    elif "/" in location:
        location = location.split("/")[0].strip()

    return location


# ============================================================================
# URL 검증
# ============================================================================

def is_valid_url(url: str) -> bool:
    """
    URL 유효성 검증

    Args:
        url: 검증할 URL 문자열

    Returns:
        bool: 유효하면 True
    """
    if not url or not url.strip():
        return False

    url = url.strip()

    # 기본 URL 패턴 체크
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$", re.IGNORECASE
    )

    return bool(url_pattern.match(url))
