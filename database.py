"""
database.py - PostgreSQL 연결 및 테이블 관리
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """DB 연결 및 CRUD 관리"""

    def __init__(self, config: Config):
        self.config = config
        self.engine = None
        self._connect_with_validation()

    def _connect_with_validation(self):
        """DB 연결 및 검증"""
        try:
            self.engine = create_engine(self.config.database_url)
            # 연결 테스트
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("데이터베이스 연결 성공")
        except OperationalError as e:
            logger.error("데이터베이스 연결 실패")
            self._print_troubleshooting_guide(e)
            raise
        except Exception as e:
            logger.error(f"예상치 못한 DB 오류: {e}")
            raise

    def _print_troubleshooting_guide(self, error: Exception):
        """연결 실패 시 문제 해결 가이드 출력"""
        print("\n" + "=" * 60)
        print("❌ 데이터베이스 연결 실패")
        print("=" * 60)
        print(f"\n📍 연결 정보:")
        print(f"   Host: {self.config.DB_HOST}")
        print(f"   Port: {self.config.DB_PORT}")
        print(f"   Database: {self.config.DB_NAME}")
        print(f"   User: {self.config.DB_USER}")
        print(f"\n🔍 에러 내용:")
        print(f"   {error}")
        print(f"\n💡 확인 사항:")
        print("   1. PostgreSQL이 실행 중인가요?")
        print("      → brew services start postgresql (macOS)")
        print("      → sudo systemctl start postgresql (Linux)")
        print("   2. .env 파일의 DB 정보가 정확한가요?")
        print("   3. 데이터베이스가 생성되어 있나요?")
        print(f"      → createdb {self.config.DB_NAME}")
        print("=" * 60 + "\n")

    def create_tables(self):
        """테이블 생성 (없으면 생성, 있으면 무시)"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS companies (
                    id                  SERIAL PRIMARY KEY,
                    name                VARCHAR(200) NOT NULL UNIQUE,
                    company_size        VARCHAR(50),
                    industry            VARCHAR(200),
                    employee_count      VARCHAR(50),
                    establishment_year  VARCHAR(20),
                    homepage_url        TEXT,
                    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS job_postings (
                    id              SERIAL PRIMARY KEY,
                    company_id      INTEGER REFERENCES companies(id),
                    title           VARCHAR(500) NOT NULL,
                    location        VARCHAR(100),
                    job_category    VARCHAR(300),
                    salary          VARCHAR(100),
                    experience      VARCHAR(100),
                    benefits        TEXT,
                    badge           VARCHAR(100),
                    apply_type      VARCHAR(50),
                    posted_date     VARCHAR(50),
                    deadline        VARCHAR(50),
                    detail_url      TEXT UNIQUE,
                    search_keyword  VARCHAR(100),
                    crawled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            # 크롤링 실행 기록 테이블
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS crawl_runs (
                    id              SERIAL PRIMARY KEY,
                    keyword         VARCHAR(100) NOT NULL,
                    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at    TIMESTAMP,
                    pages_crawled   INTEGER DEFAULT 0,
                    jobs_collected  INTEGER DEFAULT 0,
                    status          VARCHAR(20) DEFAULT 'running'
                );
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_company_name ON companies(name);
                CREATE INDEX IF NOT EXISTS idx_company_size ON companies(company_size);
                CREATE INDEX IF NOT EXISTS idx_job_company_id ON job_postings(company_id);
                CREATE INDEX IF NOT EXISTS idx_job_location ON job_postings(location);
                CREATE INDEX IF NOT EXISTS idx_job_experience ON job_postings(experience);
                CREATE INDEX IF NOT EXISTS idx_job_deadline ON job_postings(deadline);
                CREATE INDEX IF NOT EXISTS idx_job_keyword ON job_postings(search_keyword);
            """))

            conn.commit()
        logger.info("테이블 생성 완료 (companies, job_postings, crawl_runs)")

    def start_crawl_run(self, keyword: str) -> int:
        """크롤링 실행 시작 기록"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO crawl_runs (keyword, status)
                    VALUES (:keyword, 'running')
                    RETURNING id
                """),
                {"keyword": keyword}
            )
            run_id = result.fetchone()[0]
            conn.commit()
            logger.info(f"크롤링 실행 시작 (run_id: {run_id}, keyword: {keyword})")
            return run_id

    def complete_crawl_run(self, run_id: int, pages: int, jobs: int, status: str = "completed"):
        """크롤링 실행 완료 기록"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE crawl_runs
                    SET completed_at = CURRENT_TIMESTAMP,
                        pages_crawled = :pages,
                        jobs_collected = :jobs,
                        status = :status
                    WHERE id = :id
                """),
                {"id": run_id, "pages": pages, "jobs": jobs, "status": status}
            )
            conn.commit()
            logger.info(f"크롤링 실행 완료 (run_id: {run_id}, pages: {pages}, jobs: {jobs})")

    def get_or_create_company(self, conn, company_name: str, industry: str = "") -> int:
        """회사가 있으면 ID 반환, 없으면 생성 후 ID 반환"""
        result = conn.execute(
            text("SELECT id FROM companies WHERE name = :name"),
            {"name": company_name}
        )
        row = result.fetchone()

        if row:
            return row[0]

        result = conn.execute(
            text("""
                INSERT INTO companies (name, industry)
                VALUES (:name, :industry)
                ON CONFLICT (name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """),
            {"name": company_name, "industry": industry}
        )
        return result.fetchone()[0]

    def insert_job_posting(self, conn, company_id: int, job_data: dict, keyword: str = ""):
        """채용공고 삽입 (중복 시 무시)"""
        conn.execute(
            text("""
                INSERT INTO job_postings (
                    company_id, title, location, job_category, salary,
                    experience, benefits, badge, apply_type,
                    posted_date, deadline, detail_url, search_keyword
                ) VALUES (
                    :company_id, :title, :location, :job_category, :salary,
                    :experience, :benefits, :badge, :apply_type,
                    :posted_date, :deadline, :detail_url, :search_keyword
                )
                ON CONFLICT (detail_url) DO NOTHING
            """),
            {
                "company_id": company_id,
                "title": job_data.get("title", ""),
                "location": job_data.get("location", ""),
                "job_category": job_data.get("job_category", ""),
                "salary": job_data.get("salary", ""),
                "experience": job_data.get("experience", ""),
                "benefits": job_data.get("benefits", ""),
                "badge": job_data.get("badge", ""),
                "apply_type": job_data.get("apply_type", ""),
                "posted_date": job_data.get("posted_date", ""),
                "deadline": job_data.get("deadline", ""),
                "detail_url": job_data.get("detail_url", ""),
                "search_keyword": keyword,
            }
        )

    def get_companies_without_details(self) -> list:
        """Phase 2: 상세 정보가 없는 회사 목록 반환"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT c.id, c.name, jp.detail_url
                FROM companies c
                JOIN job_postings jp ON c.id = jp.company_id
                WHERE c.company_size IS NULL
                  AND jp.detail_url IS NOT NULL
                  AND jp.detail_url != ''
                ORDER BY c.id
            """))
            return [{"id": row[0], "name": row[1], "detail_url": row[2]} for row in result.fetchall()]

    def update_company_details(self, company_id: int, details: dict):
        """Phase 2: 회사 상세 정보 업데이트"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE companies
                    SET company_size = COALESCE(:company_size, company_size),
                        employee_count = COALESCE(:employee_count, employee_count),
                        establishment_year = COALESCE(:establishment_year, establishment_year),
                        homepage_url = COALESCE(:homepage_url, homepage_url),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {
                    "id": company_id,
                    "company_size": details.get("company_size"),
                    "employee_count": details.get("employee_count"),
                    "establishment_year": details.get("establishment_year"),
                    "homepage_url": details.get("homepage_url"),
                }
            )
            conn.commit()

    def get_summary(self) -> dict:
        """DB 요약 통계 반환"""
        with self.engine.connect() as conn:
            company_count = conn.execute(text("SELECT COUNT(*) FROM companies")).fetchone()[0]
            job_count = conn.execute(text("SELECT COUNT(*) FROM job_postings")).fetchone()[0]
            companies_with_details = conn.execute(
                text("SELECT COUNT(*) FROM companies WHERE company_size IS NOT NULL")
            ).fetchone()[0]

            return {
                "company_count": company_count,
                "job_count": job_count,
                "companies_with_details": companies_with_details,
            }

    def get_recent_jobs(self, limit: int = 5) -> list:
        """최근 공고 목록 반환"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT jp.title, c.name, jp.location, jp.experience
                FROM job_postings jp
                JOIN companies c ON jp.company_id = c.id
                ORDER BY jp.crawled_at DESC
                LIMIT :limit
            """), {"limit": limit})
            return [{"title": row[0], "company": row[1], "location": row[2], "experience": row[3]}
                    for row in result.fetchall()]

    def connect(self):
        """커넥션 반환 (with문에서 사용)"""
        return self.engine.connect()


# 하위 호환성을 위한 함수들
def get_engine(config: Config = None):
    """기존 함수 시그니처 유지 (하위 호환성)"""
    if config is None:
        config = Config()
    return create_engine(config.database_url)


def create_tables(engine):
    """기존 함수 시그니처 유지 (하위 호환성)"""
    config = Config()
    db = DatabaseManager(config)
    db.engine = engine
    db.create_tables()


def get_or_create_company(conn, company_name, industry=""):
    """기존 함수 시그니처 유지 (하위 호환성)"""
    config = Config()
    db = DatabaseManager(config)
    return db.get_or_create_company(conn, company_name, industry)


def insert_job_posting(conn, company_id, job_data):
    """기존 함수 시그니처 유지 (하위 호환성)"""
    config = Config()
    db = DatabaseManager(config)
    db.insert_job_posting(conn, company_id, job_data)
