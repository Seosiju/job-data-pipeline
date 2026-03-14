"""
test_database.py - Database 모듈 단위 테스트
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text

from database import (
    JOB_STATUS_ACTIVE,
    JOB_STATUS_STALE,
    _calculate_job_posting_changes,
)


REAL_DB_ENV_MAP = {
    "host": ("TEST_REAL_DB_HOST", "DB_HOST", "localhost"),
    "port": ("TEST_REAL_DB_PORT", "DB_PORT", "5433"),
    "name": ("TEST_REAL_DB_NAME", "DB_NAME", "jobkorea"),
    "user": ("TEST_REAL_DB_USER", "DB_USER", "postgres"),
    "password": ("TEST_REAL_DB_PASSWORD", "DB_PASSWORD", "jobkorea123"),
}


def get_real_db_settings() -> dict[str, str]:
    """실제 DB 테스트용 접속 정보 반환"""
    settings = {}
    for key, (preferred_env, fallback_env, default) in REAL_DB_ENV_MAP.items():
        settings[key] = os.getenv(preferred_env) or os.getenv(fallback_env, default)

    if settings["host"] == "testhost":
        settings = {
            "host": "localhost",
            "port": "5433",
            "name": "jobkorea",
            "user": "postgres",
            "password": "jobkorea123",
        }

    return settings


def build_database_url(settings: dict[str, str]) -> str:
    """테스트용 DB URL 생성"""
    return (
        f"postgresql://{settings['user']}:{settings['password']}"
        f"@{settings['host']}:{settings['port']}/{settings['name']}"
    )


def is_db_available():
    """실제 DB 연결 가능 여부 확인 (환경변수 오염 방지)"""
    try:
        settings = get_real_db_settings()
        engine = create_engine(build_database_url(settings))
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_real_db_manager():
    """테스트용 DB Manager 생성 (환경변수 오염 방지)"""
    from database import DatabaseManager
    settings = get_real_db_settings()

    class TestConfig:
        DB_HOST = settings["host"]
        DB_PORT = settings["port"]
        DB_NAME = settings["name"]
        DB_USER = settings["user"]
        DB_PASSWORD = settings["password"]
        DELAY_MIN = 2
        DELAY_MAX = 5

        @property
        def database_url(self):
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    return DatabaseManager(TestConfig())


# 실제 DB 필요한 테스트 마커
requires_db = pytest.mark.skipif(
    not is_db_available(),
    reason="PostgreSQL DB not available"
)


class TestDatabaseManager:
    """DatabaseManager 클래스 테스트"""

    @requires_db
    def test_init_creates_engine(self):
        """초기화 시 engine이 생성되는지 확인 (실제 DB 연결 필요)"""
        db = get_real_db_manager()

        assert db.engine is not None

    @requires_db
    def test_database_url_format_check(self):
        """Config의 database_url 형식이 engine에 반영되는지 확인 (실제 DB 연결 필요)"""
        db = get_real_db_manager()

        # SQLAlchemy가 비밀번호를 마스킹하므로 host/port/db만 확인
        url_str = str(db.engine.url)
        assert "localhost" in url_str
        assert "5433" in url_str
        assert "jobkorea" in url_str

    @requires_db
    def test_create_tables_no_error(self):
        """테이블 생성이 에러 없이 실행되는지 확인"""
        db = get_real_db_manager()

        # 에러 없이 실행되면 통과
        try:
            db.create_tables()
        except Exception as e:
            pytest.fail(f"create_tables raised exception: {e}")

    @requires_db
    def test_create_tables_adds_company_page_url_column(self):
        """companies 테이블에 company_page_url 컬럼이 존재해야 한다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            column_exists = conn.execute(
                text("""
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'companies'
                      AND column_name = 'company_page_url'
                """)
            ).fetchone()

        assert column_exists is not None

    @requires_db
    def test_connection_context_manager(self):
        """connect()가 context manager로 동작하는지 확인"""
        db = get_real_db_manager()

        with db.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1


class TestGetOrCreateCompany:
    """get_or_create_company 함수 테스트"""

    @requires_db
    def test_create_new_company(self):
        """새 회사 생성 시 ID 반환"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            # 유니크한 회사명 사용
            import uuid
            company_name = f"테스트회사_{uuid.uuid4().hex[:8]}"

            company_id = db.get_or_create_company(conn, company_name, "IT")
            conn.commit()

            assert company_id is not None
            assert isinstance(company_id, int)

    @requires_db
    def test_get_existing_company(self):
        """기존 회사 조회 시 동일 ID 반환"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            import uuid
            company_name = f"중복테스트_{uuid.uuid4().hex[:8]}"

            # 첫 번째 생성
            id1 = db.get_or_create_company(conn, company_name, "IT")
            conn.commit()

            # 두 번째 조회
            id2 = db.get_or_create_company(conn, company_name, "IT")

            assert id1 == id2

    @requires_db
    def test_update_company_page_url_persists_value(self):
        """company_page_url 저장 경로가 동작해야 한다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            company_name = f"회사URL테스트_{uuid.uuid4().hex[:8]}"
            company_id = db.get_or_create_company(conn, company_name, "IT")
            conn.commit()

        changed = db.update_company_page_url(
            company_id,
            "https://www.jobkorea.co.kr/Recruit/Co_Read/C/55555555",
        )

        with db.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT company_page_url
                    FROM companies
                    WHERE id = :id
                """),
                {"id": company_id},
            ).mappings().one()

        assert changed is True
        assert row["company_page_url"] == "https://www.jobkorea.co.kr/Recruit/Co_Read/C/55555555"


class TestInsertJobPosting:
    """insert_job_posting 함수 테스트"""

    @requires_db
    def test_insert_job(self):
        """공고 삽입이 에러 없이 실행되는지 확인"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            import uuid
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"공고테스트_{unique_id}"

            company_id = db.get_or_create_company(conn, company_name)

            job_data = {
                "title": "테스트 공고",
                "location": "서울",
                "experience": "신입",
                "detail_url": f"https://example.com/job/{unique_id}",
            }

            # 에러 없이 실행되면 통과
            db.insert_job_posting(conn, company_id, job_data)
            conn.commit()

    @requires_db
    def test_duplicate_url_ignored(self):
        """중복 URL 삽입 시 무시되는지 확인"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            import uuid
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"중복URL테스트_{unique_id}"
            detail_url = f"https://example.com/dup/{unique_id}"

            company_id = db.get_or_create_company(conn, company_name)

            job_data = {
                "title": "원본 공고",
                "detail_url": detail_url,
            }

            # 첫 번째 삽입
            db.insert_job_posting(conn, company_id, job_data)
            conn.commit()

            # 두 번째 삽입 (동일 URL) - 에러 없이 무시되어야 함
            job_data["title"] = "중복 공고"
            db.insert_job_posting(conn, company_id, job_data)
            conn.commit()

    @requires_db
    def test_insert_sets_lifecycle_fields_as_active(self):
        """신규 공고는 active 상태와 lifecycle timestamp를 가진다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"라이프사이클테스트_{unique_id}"
            detail_url = f"https://example.com/lifecycle/{unique_id}"
            company_id = db.get_or_create_company(conn, company_name)

            result = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "라이프사이클 공고",
                    "detail_url": detail_url,
                },
                keyword="데이터분석가",
            )
            conn.commit()

            row = conn.execute(
                text("""
                    SELECT status, first_seen_at, last_seen_at, search_keyword
                    FROM job_postings
                    WHERE id = :id
                """),
                {"id": result["job_posting_id"]},
            ).mappings().one()

            assert result["action"] == "inserted"
            assert row["status"] == JOB_STATUS_ACTIVE
            assert row["first_seen_at"] is not None
            assert row["last_seen_at"] is not None
            assert row["search_keyword"] == "데이터분석가"

    @requires_db
    def test_reinsert_with_changes_records_history_and_updates_last_seen(self):
        """동일 공고 재수집 시 변경 이력과 last_seen_at이 갱신된다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"이력테스트_{unique_id}"
            detail_url = f"https://example.com/history/{unique_id}"
            company_id = db.get_or_create_company(conn, company_name)

            inserted = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "초기 공고",
                    "salary": "4000만원",
                    "detail_url": detail_url,
                },
                keyword="데이터분석가",
            )
            conn.commit()

            first_row = conn.execute(
                text("""
                    SELECT id, last_seen_at
                    FROM job_postings
                    WHERE id = :id
                """),
                {"id": inserted["job_posting_id"]},
            ).mappings().one()

            updated = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "수정 공고",
                    "salary": "5000만원",
                    "detail_url": detail_url,
                },
                keyword="데이터분석가",
            )
            conn.commit()

            second_row = conn.execute(
                text("""
                    SELECT title, salary, status, last_seen_at
                    FROM job_postings
                    WHERE id = :id
                """),
                {"id": inserted["job_posting_id"]},
            ).mappings().one()
            history_rows = conn.execute(
                text("""
                    SELECT field_name, old_value, new_value
                    FROM job_posting_history
                    WHERE job_posting_id = :job_posting_id
                    ORDER BY field_name
                """),
                {"job_posting_id": inserted["job_posting_id"]},
            ).mappings().all()

            assert updated["action"] == "updated"
            assert second_row["title"] == "수정 공고"
            assert second_row["salary"] == "5000만원"
            assert second_row["status"] == JOB_STATUS_ACTIVE
            assert second_row["last_seen_at"] >= first_row["last_seen_at"]
            assert history_rows == [
                {
                    "field_name": "salary",
                    "old_value": "4000만원",
                    "new_value": "5000만원",
                },
                {
                    "field_name": "title",
                    "old_value": "초기 공고",
                    "new_value": "수정 공고",
                },
            ]

    @requires_db
    def test_reinsert_without_changes_keeps_history_empty(self):
        """동일 공고 재수집 시 변경이 없으면 history가 추가되지 않는다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"무변경테스트_{unique_id}"
            detail_url = f"https://example.com/unchanged/{unique_id}"
            company_id = db.get_or_create_company(conn, company_name)

            inserted = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "같은 공고",
                    "salary": "4000만원",
                    "detail_url": detail_url,
                },
                keyword="데이터분석가",
            )
            conn.commit()

            unchanged = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "같은 공고",
                    "salary": "4000만원",
                    "detail_url": detail_url,
                },
                keyword="데이터분석가",
            )
            conn.commit()

            history_count = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM job_posting_history
                    WHERE job_posting_id = :job_posting_id
                """),
                {"job_posting_id": inserted["job_posting_id"]},
            ).scalar_one()

            assert unchanged["action"] == "unchanged"
            assert history_count == 0

    @requires_db
    def test_mark_stale_job_postings_updates_only_old_active_rows(self):
        """오래된 active 공고만 stale로 바뀐다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"stale테스트_{unique_id}"
            stale_url = f"https://example.com/stale/{unique_id}"
            fresh_url = f"https://example.com/fresh/{unique_id}"
            company_id = db.get_or_create_company(conn, company_name)

            stale_job = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "오래된 공고",
                    "detail_url": stale_url,
                },
                keyword="데이터분석가",
            )
            fresh_job = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "최근 공고",
                    "detail_url": fresh_url,
                },
                keyword="데이터분석가",
            )

            conn.execute(
                text("""
                    UPDATE job_postings
                    SET last_seen_at = CURRENT_TIMESTAMP - INTERVAL '10 days'
                    WHERE id = :id
                """),
                {"id": stale_job["job_posting_id"]},
            )
            conn.commit()

        marked = db.mark_stale_job_postings(7)

        with db.connect() as conn:
            statuses = conn.execute(
                text("""
                    SELECT detail_url, status
                    FROM job_postings
                    WHERE detail_url IN (:stale_url, :fresh_url)
                    ORDER BY detail_url
                """),
                {"stale_url": stale_url, "fresh_url": fresh_url},
            ).mappings().all()

        assert marked >= 1
        assert statuses == [
            {"detail_url": fresh_url, "status": JOB_STATUS_ACTIVE},
            {"detail_url": stale_url, "status": JOB_STATUS_STALE},
        ]

    @requires_db
    def test_get_companies_without_details_returns_latest_detail_url_per_company(self):
        """상세 미수집 회사는 회사당 최신 detail_url 1건만 반환한다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"상세중복테스트_{unique_id}"
            older_url = f"https://example.com/company-old/{unique_id}"
            latest_url = f"https://example.com/company-new/{unique_id}"
            company_id = db.get_or_create_company(conn, company_name)

            older = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "이전 공고",
                    "detail_url": older_url,
                },
                keyword="데이터분석가",
            )
            latest = db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "최신 공고",
                    "detail_url": latest_url,
                },
                keyword="데이터분석가",
            )
            conn.execute(
                text("""
                    UPDATE job_postings
                    SET last_seen_at = CURRENT_TIMESTAMP - INTERVAL '5 days'
                    WHERE id = :id
                """),
                {"id": older["job_posting_id"]},
            )
            conn.execute(
                text("""
                    UPDATE job_postings
                    SET last_seen_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {"id": latest["job_posting_id"]},
            )
            conn.commit()

        companies = db.get_companies_without_details()
        matched = [row for row in companies if row["name"] == company_name]

        assert matched == [
            {
                "id": company_id,
                "name": company_name,
                "company_page_url": None,
                "detail_url": latest_url,
            }
        ]

    @requires_db
    def test_get_companies_without_details_includes_saved_company_page_url(self):
        """저장된 company_page_url이 있으면 Phase 2 재사용 대상에 포함되어야 한다"""
        db = get_real_db_manager()
        db.create_tables()

        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            company_name = f"회사URL재사용테스트_{unique_id}"
            detail_url = f"https://example.com/company-cache/{unique_id}"
            company_page_url = f"https://www.jobkorea.co.kr/Recruit/Co_Read/C/{unique_id}"
            company_id = db.get_or_create_company(conn, company_name)
            db.insert_job_posting(
                conn,
                company_id,
                {
                    "title": "회사 페이지 재사용 공고",
                    "detail_url": detail_url,
                },
                keyword="데이터분석가",
            )
            conn.commit()

        db.update_company_page_url(company_id, company_page_url)

        companies = db.get_companies_without_details()
        matched = [row for row in companies if row["name"] == company_name]

        assert matched == [
            {
                "id": company_id,
                "name": company_name,
                "company_page_url": company_page_url,
                "detail_url": detail_url,
            }
        ]

    @requires_db
    def test_get_companies_without_details_respects_limit(self):
        """Phase 2 대상 조회는 limit를 적용할 수 있어야 한다"""
        db = get_real_db_manager()
        db.create_tables()

        company_ids = []
        with db.connect() as conn:
            unique_id = uuid.uuid4().hex[:8]
            for index in range(3):
                company_name = f"phase2limit_{unique_id}_{index}"
                detail_url = f"https://example.com/phase2limit/{unique_id}/{index}"
                company_id = db.get_or_create_company(conn, company_name)
                company_ids.append(company_id)
                db.insert_job_posting(
                    conn,
                    company_id,
                    {
                        "title": f"limit test {index}",
                        "detail_url": detail_url,
                    },
                    keyword="데이터분석가",
                )
            conn.commit()

        companies = db.get_companies_without_details(limit=2)
        matched = [row for row in companies if row["id"] in company_ids]

        assert len(companies) == 2
        assert len(matched) <= 2


class TestSummaryAndRecent:
    """get_summary, get_recent_jobs 테스트"""

    @requires_db
    def test_get_summary_returns_dict(self):
        """get_summary가 딕셔너리를 반환하는지 확인"""
        db = get_real_db_manager()
        db.create_tables()

        summary = db.get_summary()

        assert isinstance(summary, dict)
        assert "company_count" in summary
        assert "job_count" in summary
        assert "companies_with_details" in summary

    @requires_db
    def test_get_recent_jobs_returns_list(self):
        """get_recent_jobs가 리스트를 반환하는지 확인"""
        db = get_real_db_manager()
        db.create_tables()

        jobs = db.get_recent_jobs(5)

        assert isinstance(jobs, list)


class TestJobPostingChangeDetection:
    """공고 필드 변경 감지 로직 테스트"""

    def test_detects_only_meaningful_changes(self):
        """실제 값이 바뀐 필드만 변경으로 감지"""
        existing = {
            "title": "기존 공고",
            "salary": "4000만원",
            "deadline": "2024-03-10",
        }
        incoming = {
            "title": "수정된 공고",
            "salary": "5000만원",
            "deadline": "2024-03-10",
        }

        changes = _calculate_job_posting_changes(existing, incoming)

        assert changes == {
            "title": ("기존 공고", "수정된 공고"),
            "salary": ("4000만원", "5000만원"),
        }

    def test_empty_values_do_not_overwrite_existing_data(self):
        """빈 문자열과 None은 기존 값을 덮어쓰는 변경으로 취급하지 않음"""
        existing = {
            "title": "기존 공고",
            "salary": "4000만원",
            "deadline": "2024-03-10",
        }
        incoming = {
            "title": "기존 공고",
            "salary": "",
            "deadline": None,
        }

        changes = _calculate_job_posting_changes(existing, incoming)

        assert changes == {}
