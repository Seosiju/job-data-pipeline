"""crawler.py 진단 경로 테스트"""

from pathlib import Path

from crawler import JobKoreaCrawler


class FakeDriver:
    """진단 산출물 테스트용 가짜 드라이버"""

    current_url = "https://www.jobkorea.co.kr/final"
    title = "차단 또는 예외 페이지"
    page_source = "<html><body>blocked</body></html>"


class BrokenPageSourceDriver:
    """page_source 접근이 실패하는 가짜 드라이버"""

    current_url = "https://www.jobkorea.co.kr/final"
    title = "broken"

    @property
    def page_source(self):
        raise RuntimeError("page_source unavailable")


class TestCrawlerDiagnostics:
    """페이지 실패 진단 산출물 테스트"""

    def test_capture_failure_diagnostics_writes_html_and_meta(self, tmp_path):
        crawler = JobKoreaCrawler.__new__(JobKoreaCrawler)
        crawler.config = type("Config", (), {"LOG_DIR": str(tmp_path)})()
        crawler.driver = FakeDriver()

        html_path = crawler._capture_failure_diagnostics(
            "회사 페이지",
            "https://www.jobkorea.co.kr/requested",
            RuntimeError("timeout"),
        )

        assert html_path is not None
        assert html_path.exists()
        assert html_path.read_text(encoding="utf-8") == "<html><body>blocked</body></html>"

        meta_path = Path(str(html_path).replace(".html", ".txt"))
        assert meta_path.exists()
        meta_text = meta_path.read_text(encoding="utf-8")
        assert "requested_url: https://www.jobkorea.co.kr/requested" in meta_text
        assert "current_url: https://www.jobkorea.co.kr/final" in meta_text
        assert "title: 차단 또는 예외 페이지" in meta_text
        assert "error: timeout" in meta_text

    def test_capture_failure_diagnostics_handles_page_source_failure(self, tmp_path):
        crawler = JobKoreaCrawler.__new__(JobKoreaCrawler)
        crawler.config = type("Config", (), {"LOG_DIR": str(tmp_path)})()
        crawler.driver = BrokenPageSourceDriver()

        html_path = crawler._capture_failure_diagnostics(
            "회사 페이지",
            "https://www.jobkorea.co.kr/requested",
            RuntimeError("timeout"),
        )

        assert html_path is not None
        assert html_path.exists()
        assert html_path.read_text(encoding="utf-8") == ""
