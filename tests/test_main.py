"""
test_main.py - main 모듈 실행 흐름 테스트
"""

import main as main_module


class FakeConnection:
    """with db.connect() 호환용 가짜 커넥션"""

    def __init__(self):
        self.commit_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        self.commit_count += 1


class FakeCrawler:
    """iter_list_pages()만 제공하는 가짜 크롤러"""

    def __init__(self, config):
        self.config = config

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def iter_list_pages(self, keyword):
        yield 1, "<page-1>"
        yield 2, "<page-2>"


class FakeDB:
    """run_phase1_for_keyword 테스트용 가짜 DB"""

    def __init__(self, insert_actions):
        self.insert_actions = iter(insert_actions)
        self.conn = FakeConnection()
        self.completed = None

    def start_crawl_run(self, keyword):
        self.started_keyword = keyword
        return 1

    def connect(self):
        return self.conn

    def get_or_create_company(self, conn, company_name, industry=""):
        return 1

    def insert_job_posting(self, conn, company_id, job_data, keyword):
        action = next(self.insert_actions)
        if action == "error":
            raise RuntimeError("insert failed")
        return {
            "action": action,
            "job_posting_id": 1,
            "changes": {},
        }

    def complete_crawl_run(self, run_id, pages, jobs, status):
        self.completed = {
            "run_id": run_id,
            "pages": pages,
            "jobs": jobs,
            "status": status,
        }


class FakeConfig:
    """run_phase1_for_keyword 테스트용 최소 설정"""

    CONSECUTIVE_DUPLICATE_THRESHOLD = 2


class FakePhase2Crawler:
    """run_phase2 테스트용 가짜 크롤러"""

    instances = []

    def __init__(self, config):
        self.config = config
        self.job_detail_calls = []
        self.company_page_calls = []
        self.random_delay_calls = 0
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def crawl_job_detail_page(self, url):
        self.job_detail_calls.append(url)
        return f"<job-detail url='{url}'>"

    def crawl_company_page(self, url, referer=None):
        self.company_page_calls.append((url, referer))
        return f"<company-page url='{url}'>"

    def _random_delay(self):
        self.random_delay_calls += 1


class FakePhase2DB:
    """run_phase2 테스트용 가짜 DB"""

    def __init__(self, companies):
        self._companies = companies
        self.updated = []
        self.saved_company_page_urls = []

    def get_companies_without_details(self):
        return self._companies

    def update_company_page_url(self, company_id, company_page_url):
        self.saved_company_page_urls.append(
            {"company_id": company_id, "company_page_url": company_page_url}
        )
        return True

    def update_company_details(self, company_id, details):
        self.updated.append({"company_id": company_id, "details": details})


class TestRunPhase1ForKeyword:
    """run_phase1_for_keyword 동작 테스트"""

    def test_stops_after_duplicate_threshold(self, monkeypatch):
        """연속 기존 공고 임계치 도달 시 조기 종료"""
        db = FakeDB(["unchanged", "updated"])

        def fake_parse_job_cards(html):
            assert html == "<page-1>"
            return [
                {"company": "회사A", "detail_url": "https://example.com/a"},
                {"company": "회사B", "detail_url": "https://example.com/b"},
            ]

        monkeypatch.setattr(main_module, "JobKoreaCrawler", FakeCrawler)
        monkeypatch.setattr(main_module, "parse_job_cards", fake_parse_job_cards)
        monkeypatch.setattr(main_module, "validate_job_posting", lambda job: job)

        stats = main_module.run_phase1_for_keyword("데이터분석가", FakeConfig(), db)

        assert stats["duplicate_threshold_hit"] is True
        assert stats["pages_crawled"] == 1
        assert stats["inserted"] == 0
        assert stats["updated"] == 1
        assert stats["unchanged"] == 1
        assert db.completed == {
            "run_id": 1,
            "pages": 1,
            "jobs": 0,
            "status": "completed",
        }

    def test_tracks_insert_update_skip_and_fail_counts(self, monkeypatch):
        """신규/변경/재확인/건너뜀/실패 집계"""
        db = FakeDB(["inserted", "updated", "unchanged", "error"])
        config = type("Config", (), {"CONSECUTIVE_DUPLICATE_THRESHOLD": 10})()

        def fake_parse_job_cards(html):
            if html == "<page-1>":
                return [
                    {"company": "회사A", "detail_url": "https://example.com/a"},
                    {"company": "회사B", "detail_url": "https://example.com/b"},
                    {"company": "회사C", "detail_url": "https://example.com/c"},
                    {"company": "회사D", "detail_url": "https://example.com/d"},
                    {"company": "", "detail_url": "https://example.com/e"},
                ]
            return []

        monkeypatch.setattr(main_module, "JobKoreaCrawler", FakeCrawler)
        monkeypatch.setattr(main_module, "parse_job_cards", fake_parse_job_cards)
        monkeypatch.setattr(main_module, "validate_job_posting", lambda job: job)

        stats = main_module.run_phase1_for_keyword("데이터분석가", config, db)

        assert stats["inserted"] == 1
        assert stats["updated"] == 1
        assert stats["unchanged"] == 1
        assert stats["failed"] == 1
        assert stats["skipped"] == 1
        assert stats["pages_crawled"] == 2
        assert stats["duplicate_threshold_hit"] is False
        assert db.completed == {
            "run_id": 1,
            "pages": 2,
            "jobs": 1,
            "status": "completed",
        }


class TestRunPhase2:
    """run_phase2 동작 테스트"""

    def setup_method(self):
        FakePhase2Crawler.instances = []

    def test_follows_jd_to_company_page_flow(self, monkeypatch):
        """Phase 2는 JD 방문 후 회사 페이지 링크를 추출해 회사 페이지를 방문해야 한다"""
        db = FakePhase2DB(
            [
                {
                    "id": 10,
                    "name": "넥스트그라운드",
                    "company_page_url": None,
                    "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/48674797",
                }
            ]
        )

        monkeypatch.setattr(main_module, "JobKoreaCrawler", FakePhase2Crawler)
        monkeypatch.setattr(
            main_module,
            "parse_company_page_url_from_job_detail",
            lambda html: "https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886",
        )
        monkeypatch.setattr(
            main_module,
            "parse_company_detail",
            lambda html: {
                "company_size": "중소기업",
                "employee_count": "23명",
                "establishment_year": "2021",
                "homepage_url": "https://zippoom.com",
            },
        )
        monkeypatch.setattr(main_module, "validate_company_details", lambda details: details)

        updated_count = main_module.run_phase2(object(), db)

        crawler = FakePhase2Crawler.instances[0]
        assert updated_count == 1
        assert crawler.job_detail_calls == [
            "https://www.jobkorea.co.kr/Recruit/GI_Read/48674797"
        ]
        assert crawler.company_page_calls == [
            (
                "https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886",
                "https://www.jobkorea.co.kr/Recruit/GI_Read/48674797",
            )
        ]
        assert db.updated == [
            {
                "company_id": 10,
                "details": {
                    "company_size": "중소기업",
                    "employee_count": "23명",
                    "establishment_year": "2021",
                    "homepage_url": "https://zippoom.com",
                },
            }
        ]
        assert db.saved_company_page_urls == [
            {
                "company_id": 10,
                "company_page_url": "https://www.jobkorea.co.kr/Recruit/Co_Read/C/35870886",
            }
        ]

    def test_reuses_stored_company_page_url_without_opening_jd(self, monkeypatch):
        """저장된 company_page_url이 있으면 JD를 다시 열지 않아야 한다"""
        db = FakePhase2DB(
            [
                {
                    "id": 12,
                    "name": "캐시회사",
                    "company_page_url": "https://www.jobkorea.co.kr/Recruit/Co_Read/C/12345678",
                    "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/22222222",
                }
            ]
        )

        parse_calls = {"company_page_url": 0}

        monkeypatch.setattr(main_module, "JobKoreaCrawler", FakePhase2Crawler)

        def fake_parse_company_page_url_from_job_detail(html):
            parse_calls["company_page_url"] += 1
            return "https://www.jobkorea.co.kr/Recruit/Co_Read/C/should-not-be-used"

        monkeypatch.setattr(
            main_module,
            "parse_company_page_url_from_job_detail",
            fake_parse_company_page_url_from_job_detail,
        )
        monkeypatch.setattr(
            main_module,
            "parse_company_detail",
            lambda html: {
                "company_size": "중견기업",
                "employee_count": "120명",
                "establishment_year": "2017",
                "homepage_url": "https://cached.example.com",
            },
        )
        monkeypatch.setattr(main_module, "validate_company_details", lambda details: details)

        updated_count = main_module.run_phase2(object(), db)

        crawler = FakePhase2Crawler.instances[0]
        assert updated_count == 1
        assert crawler.job_detail_calls == []
        assert crawler.company_page_calls == [
            (
                "https://www.jobkorea.co.kr/Recruit/Co_Read/C/12345678",
                "https://www.jobkorea.co.kr/Recruit/GI_Read/22222222",
            )
        ]
        assert parse_calls["company_page_url"] == 0
        assert db.saved_company_page_urls == []

    def test_run_phase2_uses_explicit_companies_without_db_lookup(self, monkeypatch):
        """명시된 company list가 있으면 DB 대상 조회 없이 처리해야 한다"""

        class FailIfCalledDB(FakePhase2DB):
            def get_companies_without_details(self):
                raise AssertionError("should not query db targets")

        db = FailIfCalledDB([])
        explicit_companies = [
            {
                "id": 21,
                "name": "직접주입회사",
                "company_page_url": "https://www.jobkorea.co.kr/Recruit/Co_Read/C/21000000",
                "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/21000000",
            }
        ]

        monkeypatch.setattr(main_module, "JobKoreaCrawler", FakePhase2Crawler)
        monkeypatch.setattr(
            main_module,
            "parse_company_detail",
            lambda html: {
                "company_size": "중소기업",
                "employee_count": "10명",
                "establishment_year": "2020",
                "homepage_url": "https://direct.example.com",
            },
        )
        monkeypatch.setattr(main_module, "validate_company_details", lambda details: details)

        updated_count = main_module.run_phase2(object(), db, companies=explicit_companies)

        crawler = FakePhase2Crawler.instances[0]
        assert updated_count == 1
        assert crawler.job_detail_calls == []
        assert crawler.company_page_calls == [
            (
                "https://www.jobkorea.co.kr/Recruit/Co_Read/C/21000000",
                "https://www.jobkorea.co.kr/Recruit/GI_Read/21000000",
            )
        ]

    def test_skips_when_company_page_url_is_missing(self, monkeypatch):
        """JD에서 회사 페이지 링크를 못 찾으면 회사 페이지 방문 없이 스킵해야 한다"""
        db = FakePhase2DB(
            [
                {
                    "id": 11,
                    "name": "링크없음회사",
                    "company_page_url": None,
                    "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/11111111",
                }
            ]
        )

        parse_calls = {"company_detail": 0}

        monkeypatch.setattr(main_module, "JobKoreaCrawler", FakePhase2Crawler)
        monkeypatch.setattr(
            main_module,
            "parse_company_page_url_from_job_detail",
            lambda html: None,
        )

        def fake_parse_company_detail(html):
            parse_calls["company_detail"] += 1
            return {}

        monkeypatch.setattr(main_module, "parse_company_detail", fake_parse_company_detail)
        monkeypatch.setattr(main_module, "validate_company_details", lambda details: details)

        updated_count = main_module.run_phase2(object(), db)

        crawler = FakePhase2Crawler.instances[0]
        assert updated_count == 0
        assert crawler.job_detail_calls == [
            "https://www.jobkorea.co.kr/Recruit/GI_Read/11111111"
        ]
        assert crawler.company_page_calls == []
        assert parse_calls["company_detail"] == 0
        assert db.updated == []
        assert db.saved_company_page_urls == []
