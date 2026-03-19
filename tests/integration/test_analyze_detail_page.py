"""analyze_detail_page 스크립트 테스트"""

import scripts.dev.analyze_detail_page as analyze_module


class FakeScriptCrawler:
    """analyze_detail_page 테스트용 가짜 크롤러"""

    instances = []

    def __init__(self, config):
        self.config = config
        self.job_detail_calls = []
        self.company_page_calls = []
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def crawl_job_detail_page(self, url):
        self.job_detail_calls.append(url)
        return f"<job-detail url='{url}'>"

    def crawl_company_page(self, url):
        self.company_page_calls.append(url)
        return f"<company-page url='{url}'>"


class TestAnalyzeDetailPageScript:
    """analyze_detail_page 스크립트 동작 테스트"""

    def setup_method(self):
        FakeScriptCrawler.instances = []

    def test_main_jd_mode_uses_job_detail_flow(self, monkeypatch, tmp_path):
        """JD 모드는 crawl_job_detail_page와 JD 출력 파일을 사용해야 한다"""
        captured = {}

        monkeypatch.setattr(
            analyze_module,
            "get_sample_job_detail_target",
            lambda: ("https://example.com/jd/1", "JD샘플회사"),
        )
        monkeypatch.setattr(analyze_module, "JobKoreaCrawler", FakeScriptCrawler)
        monkeypatch.setattr(analyze_module, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(
            analyze_module,
            "analyze_html_structure",
            lambda html, mode: captured.update({"html": html, "mode": mode}),
        )

        exit_code = analyze_module.main(["--mode", "jd"])

        crawler = FakeScriptCrawler.instances[0]
        assert exit_code == 0
        assert crawler.job_detail_calls == ["https://example.com/jd/1"]
        assert crawler.company_page_calls == []
        assert captured["mode"] == "jd"
        assert (tmp_path / "output" / "sample_job_detail.html").exists()

    def test_main_company_mode_uses_company_page_flow(self, monkeypatch, tmp_path):
        """company 모드는 저장된 company_page_url을 직접 사용해야 한다"""
        captured = {}

        monkeypatch.setattr(
            analyze_module,
            "get_sample_company_page_target",
            lambda: ("https://example.com/company/1", "회사샘플회사"),
        )
        monkeypatch.setattr(analyze_module, "JobKoreaCrawler", FakeScriptCrawler)
        monkeypatch.setattr(analyze_module, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(
            analyze_module,
            "analyze_html_structure",
            lambda html, mode: captured.update({"html": html, "mode": mode}),
        )

        exit_code = analyze_module.main(["--mode", "company"])

        crawler = FakeScriptCrawler.instances[0]
        assert exit_code == 0
        assert crawler.job_detail_calls == []
        assert crawler.company_page_calls == ["https://example.com/company/1"]
        assert captured["mode"] == "company"
        assert (tmp_path / "output" / "sample_company_page.html").exists()

    def test_main_company_mode_returns_error_when_company_page_url_missing(self, monkeypatch):
        """company 모드는 저장된 company_page_url이 없으면 안내 후 종료해야 한다"""
        monkeypatch.setattr(
            analyze_module,
            "get_sample_company_page_target",
            lambda: (None, None),
        )

        exit_code = analyze_module.main(["--mode", "company"])

        assert exit_code == 1
