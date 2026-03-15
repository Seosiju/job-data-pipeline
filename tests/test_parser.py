"""
test_parser.py - Parser 모듈 단위 테스트
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from parser import (
    extract_card_data,
    parse_company_detail,
    parse_company_page_url_from_job_detail,
    parse_job_cards,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SEARCH_RESULTS_FIXTURE = FIXTURES_DIR / "jobkorea_search_page_02.html"
JD_DETAIL_FIXTURE = FIXTURES_DIR / "jobkorea_jd_detail_02.html"
COMPANY_PAGE_FIXTURE = FIXTURES_DIR / "jobkorea_company_page_02.html"
SUPER_COMPANY_PAGE_FIXTURE = FIXTURES_DIR / "jobkorea_company_page_super_neonutra_01.html"


@pytest.fixture
def sample_list_html():
    """Phase 1 검색 결과 페이지 샘플 HTML"""
    return SEARCH_RESULTS_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def jd_detail_html():
    """JD 상세 페이지 fixture"""
    return JD_DETAIL_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def company_page_html():
    """회사 페이지 fixture"""
    return COMPANY_PAGE_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def super_company_page_html():
    """슈퍼기업관 회사 페이지 fixture"""
    return SUPER_COMPANY_PAGE_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def sample_detail_html():
    """상세 페이지 파서 회귀용 최소 샘플 HTML"""
    return """
    <dl>
        <dt>기업규모</dt><dd>중견기업</dd>
        <dt>사원수</dt><dd>500명</dd>
        <dt>설립일</dt><dd>2010년</dd>
        <dt>홈페이지</dt>
        <dd><a href="https://example.com">https://example.com</a></dd>
    </dl>
    """


@pytest.fixture
def search_results_soup(sample_list_html):
    return BeautifulSoup(sample_list_html, "html.parser")


@pytest.fixture
def job_list_cards(search_results_soup):
    job_list = search_results_soup.select_one('[data-sentry-component="JobList"]')
    assert job_list is not None
    return job_list.select('[data-sentry-component="CardJob"]')


class TestParseJobCards:
    """Phase 1 검색 결과 카드 파싱 테스트"""

    def test_parse_job_cards_does_not_print_to_stdout(self, sample_list_html, capsys):
        """파서는 표준출력 대신 로깅을 사용한다"""
        parse_job_cards(sample_list_html)
        captured = capsys.readouterr()

        assert captured.out == ""

    def test_parse_job_cards_uses_joblist_scope_only(
        self,
        sample_list_html,
        search_results_soup,
        job_list_cards,
    ):
        """전역 CardJob가 아니라 JobList 내부 CardJob만 파싱해야 한다"""
        assert len(search_results_soup.select('[data-sentry-component="CardJob"]')) == 27
        assert len(job_list_cards) == 20

        jobs = parse_job_cards(sample_list_html)

        assert len(jobs) == 20
        assert jobs[0]["company"] == "킨코스코리아㈜"
        assert jobs[0]["title"] == "킨코스코리아㈜ 영업부문 사업기획팀/영업직/디자인그룹 경력 및 신입사원 모집"

    def test_parse_card_primary_fields_on_first_job(self, sample_list_html):
        """첫 카드에서 JD URL, 제목, 회사명을 추출해야 한다"""
        jobs = parse_job_cards(sample_list_html)
        first_job = jobs[0]

        assert (
            first_job["detail_url"]
            == "https://www.jobkorea.co.kr/Recruit/GI_Read/48724493?Oem_Code=C1&logpath=1&stext=%EC%82%AC%EC%97%85%EA%B8%B0%ED%9A%8D&listno=1&sc=630"
        )
        assert first_job["title"] == "킨코스코리아㈜ 영업부문 사업기획팀/영업직/디자인그룹 경력 및 신입사원 모집"
        assert first_job["company"] == "킨코스코리아㈜"

    def test_parse_card_location_industry_and_job_category(self, sample_list_html):
        """위치 chip과 업종/직무 chip을 분리해서 읽어야 한다"""
        jobs = parse_job_cards(sample_list_html)
        first_job = jobs[0]

        assert first_job["location"] == "서울 금천구 외 3"
        assert first_job["industry"] == "출판·인쇄·사진"
        assert first_job["job_category"] == "경영·비즈니스기획, 채널관리자, 제품디자이너"

    def test_parse_salary_when_chip_exists_and_when_missing(self, sample_list_html):
        """급여 chip 유무에 따라 빈 문자열 또는 실제 급여를 반환해야 한다"""
        jobs = parse_job_cards(sample_list_html)
        salary_job = next(job for job in jobs if job["title"] == "사업기획 및 연구지원")

        assert jobs[0]["salary"] == ""
        assert salary_job["salary"] == "연봉 4,000~6,000만원"
        assert salary_job["industry"] == "무역·상사"
        assert salary_job["job_category"] == "백화점·유통·도소매, 쇼핑몰·오픈마켓·소셜커머스, 식품가공"

    def test_parse_apply_type_uses_button_text(self, sample_list_html):
        """지원 방식은 버튼 텍스트 기준으로 읽어야 한다"""
        jobs = parse_job_cards(sample_list_html)

        assert jobs[0]["apply_type"] == "즉시 지원"
        assert jobs[1]["apply_type"] == "홈페이지 지원"
        assert {job["apply_type"] for job in jobs} <= {"즉시 지원", "홈페이지 지원"}

    def test_parse_job_cards_ignores_result_count_mismatch(self, sample_list_html):
        """8,515 vs 8,513 결과 수 차이가 있어도 카드 파싱은 정상 동작해야 한다"""
        assert "8,515" in sample_list_html
        assert "8,513" in sample_list_html

        jobs = parse_job_cards(sample_list_html)

        assert len(jobs) == 20

    def test_all_parsed_cards_have_jd_url_title_and_company(self, sample_list_html):
        """메인 목록에 포함된 모든 카드는 JD URL, 제목, 회사명이 있어야 한다"""
        jobs = parse_job_cards(sample_list_html)

        assert all(job["detail_url"].startswith("https://www.jobkorea.co.kr/Recruit/GI_Read/") for job in jobs)
        assert all(job["title"] for job in jobs)
        assert all(job["company"] for job in jobs)


class TestParseCompanyDetail:
    """parse_company_detail 함수 테스트"""

    def test_extract_company_page_url_from_jd_fixture(self, jd_detail_html):
        """JD 상세 fixture에서 회사 페이지 URL을 추출해야 한다"""
        company_page_url = parse_company_page_url_from_job_detail(jd_detail_html)

        assert (
            company_page_url
            == "https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886"
        )

    def test_extract_company_page_url_from_more_button_fallback(self):
        """CompanyName 링크가 없으면 MoreButton 링크를 사용해야 한다"""
        html = """
        <section id="company-section">
            <a data-sentry-component="MoreButton" href="/Recruit/Co_Read/C/98765432">
                기업정보 더보기
            </a>
        </section>
        """

        company_page_url = parse_company_page_url_from_job_detail(html)

        assert company_page_url == "https://www.jobkorea.co.kr/Recruit/Co_Read/C/98765432"

    def test_extract_company_page_url_from_dimension47_fallback(self):
        """링크가 없으면 dimension47 fallback으로 company id를 복원해야 한다"""
        html = """
        <script>
        window.dataLayer = [{"dimension47":"35870886"}];
        </script>
        """

        company_page_url = parse_company_page_url_from_job_detail(html)

        assert company_page_url == "https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886"

    def test_parse_company_page_fixture(self, company_page_html):
        """회사 페이지 fixture에서 핵심 상세 필드를 파싱해야 한다"""
        details = parse_company_detail(company_page_html)

        assert details["company_size"] == "중소기업"
        assert details["employee_count"] == "23명"
        assert details["establishment_year"] == "2021"
        assert details["homepage_url"] == "https://zippoom.com/"

    def test_parse_super_company_page_structure(self):
        """슈퍼기업관 레이아웃에서도 핵심 상세 필드를 파싱해야 한다"""
        html = """
        <article class="starHead company-header-container">
            <div class="company-header">
                <div class="add-ons">
                    <div class="home">
                        <a class="button-home" href="http://neonutra.com/">홈페이지</a>
                    </div>
                </div>
            </div>
        </article>
        <div class="corpInfo">
            <ul>
                <li class="icnCorp01">
                    <p>설립 17년차</p>
                    <p>2005년도 설립</p>
                </li>
                <li class="icnCorp02">
                    <p>53명</p>
                    <p>사원수</p>
                </li>
                <li class="icnCorp03">
                    <p>중소기업</p>
                    <p>기업형태</p>
                </li>
            </ul>
        </div>
        """

        details = parse_company_detail(html)

        assert details["company_size"] == "중소기업"
        assert details["employee_count"] == "53명"
        assert details["establishment_year"] == "2005"
        assert details["homepage_url"] == "http://neonutra.com/"

    def test_parse_live_super_company_page_fixture(self, super_company_page_html):
        """live redirect로 저장한 슈퍼기업관 fixture도 현재 파서가 처리해야 한다"""
        details = parse_company_detail(super_company_page_html)

        assert details["company_size"] == "중소기업"
        assert details["employee_count"] == "53명"
        assert details["establishment_year"] == "2005"
        assert details["homepage_url"] == "http://www.neonutra.com"

    def test_parse_company_detail_returns_empty_for_jd_fixture(self, jd_detail_html):
        """JD 상세 HTML은 회사 페이지 파서가 비워서 반환해야 한다"""
        details = parse_company_detail(jd_detail_html)

        assert details["company_size"] is None
        assert details["employee_count"] is None
        assert details["establishment_year"] is None
        assert details["homepage_url"] is None

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

    def test_extract_returns_dict(self, job_list_cards):
        """반환값이 딕셔너리인지 확인"""
        result = extract_card_data(job_list_cards[0])

        assert isinstance(result, dict)

    def test_extract_all_fields_present(self, job_list_cards):
        """모든 필드가 존재하는지 확인"""
        result = extract_card_data(job_list_cards[0])

        expected_fields = [
            "title",
            "company",
            "location",
            "experience",
            "detail_url",
            "industry",
            "job_category",
            "salary",
            "badge",
            "apply_type",
            "posted_date",
            "deadline",
            "benefits",
        ]

        for field in expected_fields:
            assert field in result

    def test_extract_salary_card(self, job_list_cards):
        """급여 chip이 있는 카드도 extract_card_data에서 정확히 읽어야 한다"""
        result = extract_card_data(job_list_cards[10])

        assert result["title"] == "사업기획 및 연구지원"
        assert result["salary"] == "연봉 4,000~6,000만원"
        assert result["apply_type"] == "즉시 지원"
