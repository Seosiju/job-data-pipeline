"""
test_database.py - Database 모듈 단위 테스트
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text


def is_db_available():
    """실제 DB 연결 가능 여부 확인 (환경변수 오염 방지)"""
    try:
        # 환경변수에서 직접 읽어서 테스트 (Config 모듈 캐시 우회)
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5433")
        db_name = os.getenv("DB_NAME", "jobkorea")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "jobkorea123")

        # 테스트 환경변수가 오염된 경우 기본값 사용
        if db_host == "testhost":
            db_host = "localhost"
            db_port = "5433"
            db_name = "jobkorea"
            db_user = "postgres"
            db_password = "jobkorea123"

        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_real_db_manager():
    """테스트용 DB Manager 생성 (환경변수 오염 방지)"""
    from database import DatabaseManager

    class TestConfig:
        DB_HOST = "localhost"
        DB_PORT = "5433"
        DB_NAME = "jobkorea"
        DB_USER = "postgres"
        DB_PASSWORD = "jobkorea123"
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
