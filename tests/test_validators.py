"""
test_validators.py - 데이터 검증 로직 테스트
"""

import pytest
from validators import (
    validate_job_posting,
    validate_company_details,
    normalize_salary,
    normalize_date,
    normalize_deadline,
    normalize_establishment_year,
    normalize_employee_count,
    normalize_company_size,
    normalize_experience,
    normalize_location,
    is_valid_url,
)


class TestValidateJobPosting:
    """채용공고 데이터 검증 테스트"""

    def test_valid_job_posting(self):
        """정상 데이터 검증"""
        data = {
            "title": "백엔드 개발자",
            "company": "테크 주식회사",
            "salary": "4000만원 ~ 6000만원",
            "posted_date": "등록: 2024-02-26",
            "deadline": "마감: 2024-03-10",
            "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/12345",
            "experience": "신입",
            "location": "서울 강남구",
        }

        result = validate_job_posting(data)

        assert result["title"] == "백엔드 개발자"
        assert result["company"] == "테크 주식회사"
        assert result["salary"] == "4000만원 ~ 6000만원"
        assert result["posted_date"] == "2024-02-26"
        assert result["deadline"] == "2024-03-10"
        assert result["detail_url"] == "https://www.jobkorea.co.kr/Recruit/GI_Read/12345"
        assert result["experience"] == "신입"
        assert result["location"] == "서울 강남구"

    def test_missing_required_fields(self):
        """필수 필드 누락 처리"""
        data = {
            "title": "",
            "company": "   ",
            "salary": "협의",
        }

        result = validate_job_posting(data)

        assert result["title"] == "제목 없음"
        assert result["company"] == "회사명 없음"
        assert result["salary"] is None

    def test_invalid_url(self):
        """유효하지 않은 URL 처리"""
        data = {
            "title": "개발자",
            "company": "회사",
            "detail_url": "not-a-valid-url",
        }

        result = validate_job_posting(data)

        assert result["detail_url"] == ""

    def test_ongoing_deadline(self):
        """상시채용 처리"""
        data = {
            "title": "개발자",
            "company": "회사",
            "deadline": "채용시까지",
        }

        result = validate_job_posting(data)

        assert result["deadline"] == "상시채용"


class TestNormalizeSalary:
    """급여 정제 테스트"""

    def test_valid_salary(self):
        """정상 급여"""
        assert normalize_salary("4000만원") == "4000만원"
        assert normalize_salary("3,000만원 ~ 4,000만원") == "3,000만원 ~ 4,000만원"
        assert normalize_salary("연봉 5000만원") == "연봉 5000만원"

    def test_negotiable_salary(self):
        """협의 급여 -> None"""
        assert normalize_salary("협의") is None
        assert normalize_salary("면접 후 결정") is None
        assert normalize_salary("상담 후 결정") is None

    def test_unrealistic_salary(self):
        """비현실적 급여 -> None"""
        assert normalize_salary("100억원 이상") is None
        assert normalize_salary("1000000만원") is None

    def test_empty_salary(self):
        """빈 급여 -> None"""
        assert normalize_salary("") is None
        assert normalize_salary("   ") is None
        assert normalize_salary(None) is None

    def test_salary_with_range(self):
        """범위 급여"""
        assert normalize_salary("3억원 ~ 5억원") == "3억원 ~ 5억원"


class TestNormalizeDate:
    """날짜 정제 테스트"""

    def test_valid_date(self):
        """정상 날짜"""
        assert normalize_date("2024-02-26", "posted_date") == "2024-02-26"
        assert normalize_date("2024.02.26", "posted_date") == "2024.02.26"

    def test_date_with_prefix(self):
        """접두사 있는 날짜"""
        assert normalize_date("등록: 2024-02-26", "posted_date") == "2024-02-26"
        assert normalize_date("등록：2024-02-26", "posted_date") == "2024-02-26"

    def test_empty_date(self):
        """빈 날짜 -> None"""
        assert normalize_date("", "posted_date") is None
        assert normalize_date("   ", "posted_date") is None


class TestNormalizeDeadline:
    """마감일 정제 테스트"""

    def test_valid_deadline(self):
        """정상 마감일"""
        assert normalize_deadline("2024-03-10") == "2024-03-10"
        assert normalize_deadline("마감: 2024-03-10") == "2024-03-10"

    def test_ongoing_deadline(self):
        """상시채용"""
        assert normalize_deadline("채용시까지") == "상시채용"
        assert normalize_deadline("상시채용") == "상시채용"
        assert normalize_deadline("수시채용") == "상시채용"

    def test_empty_deadline(self):
        """빈 마감일 -> None"""
        assert normalize_deadline("") is None
        assert normalize_deadline("   ") is None


class TestNormalizeEstablishmentYear:
    """설립연도 정제 테스트"""

    def test_valid_year(self):
        """정상 설립연도"""
        assert normalize_establishment_year("2020") == "2020"
        assert normalize_establishment_year("2020년 설립") == "2020"
        assert normalize_establishment_year("설립: 2020년") == "2020"

    def test_invalid_year_range(self):
        """범위 밖 연도 -> None"""
        assert normalize_establishment_year("1800") is None
        assert normalize_establishment_year("3000") is None

    def test_invalid_year_format(self):
        """잘못된 형식 -> None"""
        assert normalize_establishment_year("올해 설립") is None
        assert normalize_establishment_year("20년") is None

    def test_empty_year(self):
        """빈 연도 -> None"""
        assert normalize_establishment_year("") is None
        assert normalize_establishment_year("   ") is None


class TestNormalizeEmployeeCount:
    """사원수 정제 테스트"""

    def test_valid_employee_count(self):
        """정상 사원수"""
        assert normalize_employee_count("10명") == "10명"
        assert normalize_employee_count("1,000명") == "1,000명"
        assert normalize_employee_count("100명 이상") == "100명 이상"

    def test_unrealistic_employee_count(self):
        """비현실적 사원수 -> None"""
        assert normalize_employee_count("1000000명") is None
        assert normalize_employee_count("2000000명 이상") is None

    def test_invalid_employee_count(self):
        """숫자 없는 사원수 -> 원본 유지"""
        result = normalize_employee_count("다수")
        assert result == "다수"

    def test_empty_employee_count(self):
        """빈 사원수 -> None"""
        assert normalize_employee_count("") is None
        assert normalize_employee_count("   ") is None


class TestNormalizeCompanySize:
    """회사 규모 정제 테스트"""

    def test_standard_company_size(self):
        """표준 카테고리"""
        assert normalize_company_size("대기업") == "대기업"
        assert normalize_company_size("중견기업") == "중견기업"
        assert normalize_company_size("중소기업") == "중소기업"
        assert normalize_company_size("외국계기업") == "외국계기업"
        assert normalize_company_size("공기업") == "공기업"
        assert normalize_company_size("스타트업") == "스타트업"

    def test_company_size_with_keywords(self):
        """키워드 포함"""
        assert normalize_company_size("대규모 기업") == "대기업"
        assert normalize_company_size("중소기업 성장") == "중소기업"
        assert normalize_company_size("벤처기업") == "스타트업"

    def test_company_size_with_parentheses(self):
        """괄호 제거"""
        result = normalize_company_size("중소기업 (주식회사)")
        assert "주식회사" not in result

    def test_empty_company_size(self):
        """빈 회사 규모 -> None"""
        assert normalize_company_size("") is None
        assert normalize_company_size("   ") is None


class TestNormalizeExperience:
    """경력 정제 테스트"""

    def test_entry_level(self):
        """신입"""
        assert normalize_experience("신입") == "신입"
        assert normalize_experience("인턴") == "신입"
        assert normalize_experience("신입/인턴") == "신입"

    def test_experience_irrelevant(self):
        """경력무관"""
        assert normalize_experience("경력무관") == "경력무관"
        assert normalize_experience("경력 관계없음") == "경력무관"

    def test_experience_years(self):
        """경력 년수 -> 원본 유지"""
        assert normalize_experience("3년 이상") == "3년 이상"
        assert normalize_experience("5~10년") == "5~10년"

    def test_empty_experience(self):
        """빈 경력 -> None"""
        assert normalize_experience("") is None
        assert normalize_experience("   ") is None


class TestNormalizeLocation:
    """근무지역 정제 테스트"""

    def test_single_location(self):
        """단일 지역"""
        assert normalize_location("서울 강남구") == "서울 강남구"
        assert normalize_location("경기 성남시") == "경기 성남시"

    def test_multiple_locations_comma(self):
        """여러 지역 (콤마) -> 첫 번째만"""
        assert normalize_location("서울 강남구, 서울 서초구") == "서울 강남구"

    def test_multiple_locations_slash(self):
        """여러 지역 (슬래시) -> 첫 번째만"""
        assert normalize_location("서울 강남구 / 경기 성남시") == "서울 강남구"

    def test_empty_location(self):
        """빈 지역 -> None"""
        assert normalize_location("") is None
        assert normalize_location("   ") is None


class TestIsValidUrl:
    """URL 유효성 검증 테스트"""

    def test_valid_urls(self):
        """유효한 URL"""
        assert is_valid_url("https://www.jobkorea.co.kr/Recruit/GI_Read/12345")
        assert is_valid_url("http://example.com")
        assert is_valid_url("https://example.com/path?query=value")
        assert is_valid_url("https://subdomain.example.com")

    def test_invalid_urls(self):
        """유효하지 않은 URL"""
        assert not is_valid_url("not-a-url")
        assert not is_valid_url("ftp://example.com")
        assert not is_valid_url("www.example.com")
        assert not is_valid_url("")
        assert not is_valid_url("   ")

    def test_localhost(self):
        """localhost"""
        assert is_valid_url("http://localhost:8000")
        assert is_valid_url("http://localhost")


class TestValidateCompanyDetails:
    """회사 정보 검증 테스트"""

    def test_valid_company_details(self):
        """정상 회사 정보"""
        data = {
            "company_size": "중소기업",
            "employee_count": "100명",
            "establishment_year": "2020",
            "homepage_url": "https://example.com",
        }

        result = validate_company_details(data)

        assert result["company_size"] == "중소기업"
        assert result["employee_count"] == "100명"
        assert result["establishment_year"] == "2020"
        assert result["homepage_url"] == "https://example.com"

    def test_invalid_establishment_year(self):
        """유효하지 않은 설립연도"""
        data = {
            "establishment_year": "1800",
        }

        result = validate_company_details(data)

        assert result["establishment_year"] is None

    def test_invalid_homepage_url(self):
        """유효하지 않은 홈페이지 URL"""
        data = {
            "homepage_url": "not-a-valid-url",
        }

        result = validate_company_details(data)

        assert result["homepage_url"] is None

    def test_company_size_normalization(self):
        """회사 규모 정제"""
        data = {
            "company_size": "중소기업 (주식회사)",
        }

        result = validate_company_details(data)

        assert "주식회사" not in result["company_size"]

    def test_unrealistic_employee_count(self):
        """비현실적 사원수"""
        data = {
            "employee_count": "1000000명",
        }

        result = validate_company_details(data)

        assert result["employee_count"] is None
