"""
database.py - PostgreSQL 연결 및 테이블 관리
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "jobkorea")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "jobkorea123")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    """SQLAlchemy 엔진 생성"""
    return create_engine(DATABASE_URL)


def create_tables(engine):
    """테이블 생성 (없으면 생성, 있으면 무시)"""
    with engine.connect() as conn:
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
                crawled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_company_name ON companies(name);
            CREATE INDEX IF NOT EXISTS idx_company_size ON companies(company_size);
            CREATE INDEX IF NOT EXISTS idx_job_company_id ON job_postings(company_id);
            CREATE INDEX IF NOT EXISTS idx_job_location ON job_postings(location);
            CREATE INDEX IF NOT EXISTS idx_job_experience ON job_postings(experience);
            CREATE INDEX IF NOT EXISTS idx_job_deadline ON job_postings(deadline);
        """))

        conn.commit()
    print("✅ 테이블 생성 완료 (companies, job_postings)")


def get_or_create_company(conn, company_name, industry=""):
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


def insert_job_posting(conn, company_id, job_data):
    """채용공고 삽입 (중복 시 무시)"""
    conn.execute(
        text("""
            INSERT INTO job_postings (
                company_id, title, location, job_category, salary,
                experience, benefits, badge, apply_type,
                posted_date, deadline, detail_url
            ) VALUES (
                :company_id, :title, :location, :job_category, :salary,
                :experience, :benefits, :badge, :apply_type,
                :posted_date, :deadline, :detail_url
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
        }
    )
