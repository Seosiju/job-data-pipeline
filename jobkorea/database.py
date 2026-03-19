"""
database.py - PostgreSQL 연결 및 테이블 관리
"""

import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from jobkorea.config import Config

logger = logging.getLogger(__name__)


TRACKED_JOB_FIELDS = (
    "title",
    "location",
    "job_category",
    "salary",
    "experience",
    "benefits",
    "badge",
    "apply_type",
    "posted_date",
    "deadline",
)

JOB_STATUS_ACTIVE = "active"
JOB_STATUS_STALE = "stale"


def _normalize_db_field_value(value: Any) -> Any:
    """DB 비교/저장 전 빈 문자열을 None으로 정규화"""
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    return value


def _calculate_job_posting_changes(
    existing: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, tuple[Any, Any]]:
    """
    기존 공고와 신규 파싱 결과를 비교해 실제 변경된 필드만 반환

    빈 값(None, "")은 기존 값을 덮어쓰지 않도록 변경으로 간주하지 않는다.
    """
    changes = {}

    for field in TRACKED_JOB_FIELDS:
        old_value = _normalize_db_field_value(existing.get(field))
        new_value = _normalize_db_field_value(incoming.get(field))

        if new_value is None:
            continue

        if old_value != new_value:
            changes[field] = (old_value, new_value)

    return changes


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
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("데이터베이스 연결 성공")
        except OperationalError as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
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
        """테이블 생성 및 기존 스키마 진화"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS companies (
                    id                  SERIAL PRIMARY KEY,
                    name                VARCHAR(200) NOT NULL UNIQUE,
                    company_size        VARCHAR(50),
                    industry            VARCHAR(200),
                    employee_count      VARCHAR(50),
                    establishment_year  VARCHAR(20),
                    company_page_url    TEXT,
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
                    status          VARCHAR(20) DEFAULT 'active',
                    first_seen_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    crawled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

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
                CREATE TABLE IF NOT EXISTS job_posting_history (
                    id              SERIAL PRIMARY KEY,
                    job_posting_id  INTEGER REFERENCES job_postings(id) ON DELETE CASCADE,
                    field_name      VARCHAR(50) NOT NULL,
                    old_value       TEXT,
                    new_value       TEXT,
                    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            # JD 분석 결과 테이블
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS job_posting_analysis (
                    id                      SERIAL PRIMARY KEY,
                    job_posting_id          INTEGER REFERENCES job_postings(id) ON DELETE CASCADE UNIQUE,
                    is_multi_position       BOOLEAN DEFAULT FALSE,
                    position_count          INTEGER DEFAULT 1,
                    positions               JSONB DEFAULT '[]',
                    required_education      VARCHAR(100),
                    required_experience     VARCHAR(100),
                    required_skills         JSONB DEFAULT '[]',
                    preferred_skills        JSONB DEFAULT '[]',
                    preferred_certifications JSONB DEFAULT '[]',
                    preferred_experience    JSONB DEFAULT '[]',
                    company_domain          VARCHAR(50),
                    job_category            VARCHAR(50),
                    analysis_confidence     VARCHAR(20),
                    analyzed_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            self._ensure_companies_schema(conn)
            self._ensure_job_postings_schema(conn)
            self._backfill_job_posting_lifecycle(conn)
            self._ensure_indexes(conn)
            conn.commit()

        logger.info("테이블 생성 완료 (companies, job_postings, crawl_runs, job_posting_history)")

    def _ensure_companies_schema(self, conn):
        """기존 companies 테이블에 필요한 컬럼 추가"""
        conn.execute(text(
            "ALTER TABLE companies ADD COLUMN IF NOT EXISTS company_page_url TEXT"
        ))

    def _ensure_job_postings_schema(self, conn):
        """기존 job_postings 테이블에 필요한 컬럼 추가"""
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS search_keyword VARCHAR(100)"
        ))
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'"
        ))
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ))
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ))
        # JD 텍스트 추출용 컬럼
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS raw_jd_text TEXT"
        ))
        conn.execute(text(
            "ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS jd_extracted_at TIMESTAMP"
        ))

    def _backfill_job_posting_lifecycle(self, conn):
        """기존 데이터에 lifecycle 컬럼 기본값 채우기"""
        conn.execute(text("""
            UPDATE job_postings
            SET first_seen_at = COALESCE(first_seen_at, crawled_at, CURRENT_TIMESTAMP),
                last_seen_at = COALESCE(last_seen_at, crawled_at, CURRENT_TIMESTAMP),
                status = COALESCE(NULLIF(status, ''), :active_status)
            WHERE first_seen_at IS NULL
               OR last_seen_at IS NULL
               OR status IS NULL
               OR status = ''
        """), {"active_status": JOB_STATUS_ACTIVE})

    def _ensure_indexes(self, conn):
        """조회 성능용 인덱스 생성"""
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_company_name ON companies(name)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_company_size ON companies(company_size)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_company_id ON job_postings(company_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_location ON job_postings(location)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_experience ON job_postings(experience)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_deadline ON job_postings(deadline)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_keyword ON job_postings(search_keyword)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_status ON job_postings(status)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_job_last_seen ON job_postings(last_seen_at)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_history_job_posting_id ON job_posting_history(job_posting_id)"
        ))

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

    def complete_crawl_run(
        self,
        run_id: int,
        pages: int,
        jobs: int,
        status: str = "completed",
    ):
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
            logger.info(
                f"크롤링 실행 완료 (run_id: {run_id}, pages: {pages}, jobs: {jobs}, status: {status})"
            )

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

    def _build_job_posting_params(
        self,
        company_id: int,
        job_data: dict,
        keyword: str,
    ) -> dict[str, Any]:
        """공고 insert/update용 파라미터 정규화"""
        return {
            "company_id": company_id,
            "title": _normalize_db_field_value(job_data.get("title")),
            "location": _normalize_db_field_value(job_data.get("location")),
            "job_category": _normalize_db_field_value(job_data.get("job_category")),
            "salary": _normalize_db_field_value(job_data.get("salary")),
            "experience": _normalize_db_field_value(job_data.get("experience")),
            "benefits": _normalize_db_field_value(job_data.get("benefits")),
            "badge": _normalize_db_field_value(job_data.get("badge")),
            "apply_type": _normalize_db_field_value(job_data.get("apply_type")),
            "posted_date": _normalize_db_field_value(job_data.get("posted_date")),
            "deadline": _normalize_db_field_value(job_data.get("deadline")),
            "detail_url": _normalize_db_field_value(job_data.get("detail_url")),
            "search_keyword": _normalize_db_field_value(keyword),
            "status": JOB_STATUS_ACTIVE,
        }

    def _insert_job_posting_history(
        self,
        conn,
        job_posting_id: int,
        changes: dict[str, tuple[Any, Any]],
    ):
        """필드 변경 이력 저장"""
        for field_name, (old_value, new_value) in changes.items():
            conn.execute(
                text("""
                    INSERT INTO job_posting_history (
                        job_posting_id, field_name, old_value, new_value
                    ) VALUES (
                        :job_posting_id, :field_name, :old_value, :new_value
                    )
                """),
                {
                    "job_posting_id": job_posting_id,
                    "field_name": field_name,
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )

    def _insert_new_job_posting(self, conn, params: dict[str, Any]) -> int:
        """신규 공고 insert"""
        result = conn.execute(
            text("""
                INSERT INTO job_postings (
                    company_id, title, location, job_category, salary,
                    experience, benefits, badge, apply_type,
                    posted_date, deadline, detail_url, search_keyword,
                    status, first_seen_at, last_seen_at
                ) VALUES (
                    :company_id, :title, :location, :job_category, :salary,
                    :experience, :benefits, :badge, :apply_type,
                    :posted_date, :deadline, :detail_url, :search_keyword,
                    :status, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                RETURNING id
            """),
            params
        )
        return result.fetchone()[0]

    def insert_job_posting(self, conn, company_id: int, job_data: dict, keyword: str = "") -> dict:
        """
        채용공고 반영

        Returns:
            dict: action(inserted/updated/unchanged), job_posting_id, changes
        """
        params = self._build_job_posting_params(company_id, job_data, keyword)
        detail_url = params["detail_url"]

        if detail_url is None:
            job_posting_id = self._insert_new_job_posting(conn, params)
            return {
                "action": "inserted",
                "job_posting_id": job_posting_id,
                "changes": {},
            }

        existing = conn.execute(
            text(f"""
                SELECT id, company_id, search_keyword, status, {", ".join(TRACKED_JOB_FIELDS)}
                FROM job_postings
                WHERE detail_url = :detail_url
            """),
            {"detail_url": detail_url}
        ).mappings().first()

        if not existing:
            job_posting_id = self._insert_new_job_posting(conn, params)
            return {
                "action": "inserted",
                "job_posting_id": job_posting_id,
                "changes": {},
            }

        changes = _calculate_job_posting_changes(existing, params)
        update_params = {
            **params,
            "id": existing["id"],
        }

        if changes:
            conn.execute(
                text("""
                    UPDATE job_postings
                    SET company_id = :company_id,
                        title = COALESCE(:title, title),
                        location = COALESCE(:location, location),
                        job_category = COALESCE(:job_category, job_category),
                        salary = COALESCE(:salary, salary),
                        experience = COALESCE(:experience, experience),
                        benefits = COALESCE(:benefits, benefits),
                        badge = COALESCE(:badge, badge),
                        apply_type = COALESCE(:apply_type, apply_type),
                        posted_date = COALESCE(:posted_date, posted_date),
                        deadline = COALESCE(:deadline, deadline),
                        search_keyword = COALESCE(search_keyword, :search_keyword),
                        status = :status,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                update_params
            )
            self._insert_job_posting_history(conn, existing["id"], changes)
            return {
                "action": "updated",
                "job_posting_id": existing["id"],
                "changes": changes,
            }

        conn.execute(
            text("""
                UPDATE job_postings
                SET company_id = :company_id,
                    search_keyword = COALESCE(search_keyword, :search_keyword),
                    status = :status,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """),
            update_params
        )
        return {
            "action": "unchanged",
            "job_posting_id": existing["id"],
            "changes": {},
        }

    def exists_job_posting(self, detail_url: str) -> bool:
        """detail_url 기준 기존 공고 존재 여부 확인"""
        detail_url = _normalize_db_field_value(detail_url)
        if detail_url is None:
            return False

        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM job_postings WHERE detail_url = :detail_url LIMIT 1"),
                {"detail_url": detail_url}
            ).fetchone()
            return result is not None

    def get_companies_without_details(self, limit: int | None = None) -> list:
        """Phase 2: 상세 정보가 없는 회사 목록을 회사당 1건씩 반환"""
        query = """
            SELECT DISTINCT ON (c.id) c.id, c.name, c.company_page_url, jp.detail_url
            FROM companies c
            LEFT JOIN job_postings jp
              ON c.id = jp.company_id
             AND jp.detail_url IS NOT NULL
            WHERE c.company_size IS NULL
              AND (
                NULLIF(c.company_page_url, '') IS NOT NULL
                OR jp.detail_url IS NOT NULL
              )
            ORDER BY c.id,
                     COALESCE(jp.last_seen_at, jp.crawled_at) DESC NULLS LAST,
                     jp.id DESC NULLS LAST
        """
        params: dict[str, int] = {}
        if limit is not None:
            query += "\nLIMIT :limit"
            params["limit"] = limit

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "company_page_url": row[2],
                    "detail_url": row[3],
                }
                for row in result.fetchall()
            ]

    def update_company_page_url(self, company_id: int, company_page_url: str | None) -> bool:
        """Phase 2: 회사 페이지 URL 저장 또는 갱신"""
        normalized_url = _normalize_db_field_value(company_page_url)
        if normalized_url is None:
            return False

        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE companies
                    SET company_page_url = :company_page_url,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                      AND company_page_url IS DISTINCT FROM :company_page_url
                """),
                {
                    "id": company_id,
                    "company_page_url": normalized_url,
                }
            )
            conn.commit()
            return bool(result.rowcount)

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

    def mark_stale_job_postings(self, stale_after_days: int) -> int:
        """일정 기간 재발견되지 않은 공고를 stale 상태로 전환"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE job_postings
                    SET status = :stale_status
                    WHERE status = :active_status
                      AND COALESCE(last_seen_at, crawled_at) <
                          CURRENT_TIMESTAMP - (:stale_after_days * INTERVAL '1 day')
                """),
                {
                    "stale_status": JOB_STATUS_STALE,
                    "active_status": JOB_STATUS_ACTIVE,
                    "stale_after_days": stale_after_days,
                }
            )
            conn.commit()
            return result.rowcount or 0

    def get_summary(self) -> dict:
        """DB 요약 통계 반환"""
        with self.engine.connect() as conn:
            company_count = conn.execute(
                text("SELECT COUNT(*) FROM companies")
            ).fetchone()[0]
            job_count = conn.execute(
                text("SELECT COUNT(*) FROM job_postings")
            ).fetchone()[0]
            companies_with_details = conn.execute(
                text("SELECT COUNT(*) FROM companies WHERE company_size IS NOT NULL")
            ).fetchone()[0]
            active_jobs = conn.execute(
                text("SELECT COUNT(*) FROM job_postings WHERE status = :status"),
                {"status": JOB_STATUS_ACTIVE}
            ).fetchone()[0]
            stale_jobs = conn.execute(
                text("SELECT COUNT(*) FROM job_postings WHERE status = :status"),
                {"status": JOB_STATUS_STALE}
            ).fetchone()[0]
            history_count = conn.execute(
                text("SELECT COUNT(*) FROM job_posting_history")
            ).fetchone()[0]

            return {
                "company_count": company_count,
                "job_count": job_count,
                "companies_with_details": companies_with_details,
                "active_jobs": active_jobs,
                "stale_jobs": stale_jobs,
                "history_count": history_count,
            }

    def get_recent_jobs(self, limit: int = 5) -> list:
        """최근 발견된 공고 목록 반환"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT jp.title, c.name, jp.location, jp.experience, jp.status
                FROM job_postings jp
                JOIN companies c ON jp.company_id = c.id
                ORDER BY COALESCE(jp.first_seen_at, jp.crawled_at) DESC
                LIMIT :limit
            """), {"limit": limit})
            return [
                {
                    "title": row[0],
                    "company": row[1],
                    "location": row[2],
                    "experience": row[3],
                    "status": row[4],
                }
                for row in result.fetchall()
            ]

    def connect(self):
        """커넥션 반환 (with문에서 사용)"""
        return self.engine.connect()


# 하위 호환성을 위한 함수들
def get_engine(config: Config = None):
    """기존 함수 시그니처 유지 (하위 호환성)"""
    if config is None:
        config = Config()
    return create_engine(config.database_url)


