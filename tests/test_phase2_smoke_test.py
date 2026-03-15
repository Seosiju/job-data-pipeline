"""phase2_smoke_test 스크립트 테스트"""

import scripts.phase2_smoke_test as smoke_module


class FakeSmokeDB:
    """phase2_smoke_test용 가짜 DB"""

    last_instance = None

    def __init__(self, config):
        self.config = config
        self.limit_calls = []
        self.engine = object()
        self.__class__.last_instance = self

    def create_tables(self):
        self.created_tables = True

    def get_companies_without_details(self, limit=None):
        self.limit_calls.append(limit)
        return [
            {
                "id": 1,
                "name": "스모크회사A",
                "company_page_url": None,
                "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/1",
            },
            {
                "id": 2,
                "name": "스모크회사B",
                "company_page_url": "https://www.jobkorea.co.kr/Recruit/Co_Read/C/2",
                "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/2",
            },
        ][: limit or 2]


class TestPhase2SmokeTestScript:
    """phase2_smoke_test 스크립트 동작 테스트"""

    def test_main_runs_limited_smoke_test(self, monkeypatch):
        before_after_calls = []
        run_calls = {}
        candidate_calls = []

        monkeypatch.setattr(smoke_module, "DatabaseManager", FakeSmokeDB)
        monkeypatch.setattr(
            smoke_module,
            "get_smoke_test_candidates",
            lambda db, limit, company_id=None: candidate_calls.append(
                {"limit": limit, "company_id": company_id}
            ) or [
                {
                    "id": 1,
                    "name": "스모크회사A",
                    "company_page_url": None,
                    "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/1",
                }
            ],
        )
        monkeypatch.setattr(
            smoke_module,
            "get_company_snapshots",
            lambda db, ids: before_after_calls.append(list(ids)) or {
                company_id: {"id": company_id, "company_page_url": None, "company_size": None}
                for company_id in ids
            },
        )
        monkeypatch.setattr(
            smoke_module,
            "run_phase2_for_companies",
            lambda config, db, companies: run_calls.update(
                {"headless": config.HEADLESS, "company_ids": [company["id"] for company in companies]}
            ) or [
                {
                    "company_id": company["id"],
                    "company_name": company["name"],
                    "status": "updated",
                }
                for company in companies
            ],
        )

        exit_code = smoke_module.main(["--limit", "1", "--headless", "true"])

        db = FakeSmokeDB.last_instance
        assert exit_code == 0
        assert db.limit_calls == []
        assert candidate_calls == [{"limit": 1, "company_id": None}]
        assert before_after_calls == [[1], [1]]
        assert run_calls == {"headless": True, "company_ids": [1]}

    def test_main_passes_company_id_to_candidate_selector(self, monkeypatch):
        candidate_calls = []

        monkeypatch.setattr(smoke_module, "DatabaseManager", FakeSmokeDB)
        monkeypatch.setattr(
            smoke_module,
            "get_smoke_test_candidates",
            lambda db, limit, company_id=None: candidate_calls.append(
                {"limit": limit, "company_id": company_id}
            ) or [],
        )

        exit_code = smoke_module.main(["--limit", "1", "--company-id", "58"])

        assert exit_code == 1
        assert candidate_calls == [{"limit": 1, "company_id": 58}]

    def test_main_rejects_non_positive_limit(self):
        exit_code = smoke_module.main(["--limit", "0"])

        assert exit_code == 1
