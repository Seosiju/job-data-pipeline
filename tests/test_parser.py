"""
test_parser.py - Parser 모듈 단위 테스트
"""

import pytest
from parser import parse_job_cards, parse_company_detail, extract_card_data
from bs4 import BeautifulSoup


class TestParseJobCards:
    """parse_job_cards 함수 테스트"""

    def test_parse_multiple_cards(self, sample_list_html):
        """여러 카드가 있는 HTML 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert len(jobs) == 3
        assert jobs[0]["company"] == "테스트회사"
        assert jobs[1]["company"] == "샘플기업"
        assert jobs[2]["company"] == "미니멀컴퍼니"

    def test_parse_empty_html(self, empty_html):
        """빈 HTML 파싱 시 빈 리스트 반환"""
        jobs = parse_job_cards(empty_html)
        assert jobs == []

    def test_parse_card_title(self, sample_list_html):
        """공고 제목 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["title"] == "시니어 데이터 분석가"
        assert jobs[1]["title"] == "주니어 데이터 엔지니어"

    def test_parse_card_location(self, sample_list_html):
        """근무지역 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["location"] == "서울 강남구"
        assert jobs[1]["location"] == "경기 성남시"

    def test_parse_card_detail_url(self, sample_list_html):
        """상세 URL 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert "12345678" in jobs[0]["detail_url"]
        assert "87654321" in jobs[1]["detail_url"]
        assert jobs[0]["detail_url"].startswith("https://www.jobkorea.co.kr")

    def test_parse_card_experience(self, sample_list_html):
        """경력 조건 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["experience"] == "경력 3년↑"
        assert jobs[1]["experience"] == "신입·경력"

    def test_parse_card_industry(self, sample_list_html):
        """업종/직무 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["industry"] == "IT·인터넷"
        assert "데이터분석" in jobs[0]["job_category"]

    def test_parse_card_salary(self, sample_list_html):
        """급여 정보 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["salary"] == "4000만원 이상"

    def test_parse_card_badge(self, sample_list_html):
        """뱃지 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["badge"] == "적극채용중"

    def test_parse_card_apply_type(self, sample_list_html):
        """지원 방식 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["apply_type"] == "즉시지원"

    def test_parse_card_dates(self, sample_list_html):
        """등록일/마감일 파싱"""
        jobs = parse_job_cards(sample_list_html)

        assert "등록" in jobs[0]["posted_date"]
        assert "마감" in jobs[0]["deadline"]

    def test_parse_minimal_card(self, sample_list_html):
        """최소 정보만 있는 카드 파싱"""
        jobs = parse_job_cards(sample_list_html)

        # 세 번째 카드는 최소 정보만 있음
        minimal_job = jobs[2]
        assert minimal_job["title"] == "데이터 사이언티스트"
        assert minimal_job["company"] == "미니멀컴퍼니"
        # 없는 필드는 빈 문자열
        assert minimal_job["location"] == ""
        assert minimal_job["detail_url"] == ""


class TestParseCompanyDetail:
    """parse_company_detail 함수 테스트"""

    def test_parse_company_size(self, sample_detail_html):
        """기업규모 파싱"""
        details = parse_company_detail(sample_detail_html)

        assert details["company_size"] == "중견기업"

    def test_parse_employee_count(self, sample_detail_html):
        """사원수 파싱"""
        details = parse_company_detail(sample_detail_html)

        assert details["employee_count"] == "500명"

    def test_parse_establishment_year(self, sample_detail_html):
        """설립연도 파싱"""
        details = parse_company_detail(sample_detail_html)

        assert details["establishment_year"] == "2010"

    def test_parse_homepage_url(self, sample_detail_html):
        """홈페이지 URL 파싱"""
        details = parse_company_detail(sample_detail_html)

        assert details["homepage_url"] == "https://example.com"

    def test_parse_empty_html(self, empty_html):
        """빈 HTML 파싱 시 None 값 반환"""
        details = parse_company_detail(empty_html)

        assert details["company_size"] is None
        assert details["employee_count"] is None
        assert details["establishment_year"] is None
        assert details["homepage_url"] is None

    def test_parse_table_structure(self):
        """테이블 구조 HTML 파싱"""
        html = """
        <table>
            <tr><th>기업규모</th><td>대기업</td></tr>
            <tr><th>직원수</th><td>1000명</td></tr>
            <tr><th>설립</th><td>2005년</td></tr>
        </table>
        """
        details = parse_company_detail(html)

        assert details["company_size"] == "대기업"
        assert details["employee_count"] == "1000명"
        assert details["establishment_year"] == "2005"

    def test_parse_keyword_fallback(self):
        """키워드 기반 폴백 파싱"""
        html = """
        <div>
            <p>우리 회사는 스타트업입니다.</p>
            <p>설립: 2020년</p>
        </div>
        """
        details = parse_company_detail(html)

        assert details["company_size"] == "스타트업"
        assert details["establishment_year"] == "2020"


class TestExtractCardData:
    """extract_card_data 함수 테스트"""

    def test_extract_returns_dict(self, sample_list_html):
        """반환값이 딕셔너리인지 확인"""
        soup = BeautifulSoup(sample_list_html, "html.parser")
        card = soup.find("div", attrs={"data-sentry-component": "CardJob"})

        result = extract_card_data(card)

        assert isinstance(result, dict)

    def test_extract_all_fields_present(self, sample_list_html):
        """모든 필드가 존재하는지 확인"""
        soup = BeautifulSoup(sample_list_html, "html.parser")
        card = soup.find("div", attrs={"data-sentry-component": "CardJob"})

        result = extract_card_data(card)

        expected_fields = [
            "title", "company", "location", "experience",
            "detail_url", "industry", "job_category", "salary",
            "badge", "apply_type", "posted_date", "deadline", "benefits"
        ]

        for field in expected_fields:
            assert field in result
