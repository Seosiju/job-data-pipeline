"""
Vision OCR 대상 공고 필터링

Phase 1에서 수집한 공고 중 Vision OCR 파싱 대상을 선별합니다.

필터 조건:
- 지역: 서울, 인천
- 경력: 신입, 경력무관
- 제외: 해외영업, 해외사업, 무역, 수출

실행:
    python scripts/filter_for_vision.py           # 필터 결과 미리보기
    python scripts/filter_for_vision.py --export  # CSV 내보내기
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import pandas as pd


def load_env():
    """환경변수 로드"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()


def get_db_engine():
    """DB 연결"""
    db_url = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'jobkorea123')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5433')}/"
        f"{os.getenv('DB_NAME', 'jobkorea')}"
    )
    return create_engine(db_url)


# === 필터 설정 ===

INCLUDE_LOCATIONS = ['서울', '인천']
INCLUDE_EXPERIENCE = ['신입', '경력무관']
EXCLUDE_KEYWORDS = ['해외영업', '해외사업', '무역', '수출', '주재원', '바이어', '현지법인']


def parse_deadline_filter():
    """
    마감일 필터 SQL 조건 생성
    - '상시채용': 항상 유효
    - 'MM/DD(요일) 마감': 오늘 이후만 유효
    """
    from datetime import datetime
    today = datetime.now()

    # 현재 연도 기준 (03/17 -> 2026-03-17)
    year = today.year
    month = today.month
    day = today.day

    # SQL 조건: 상시채용이거나, 마감일이 오늘 이후
    # deadline 형식: "03/17(화) 마감" 또는 "상시채용"
    return f"""
    (
        deadline = '상시채용'
        OR deadline LIKE '%채용시%'
        OR (
            -- MM/DD 형식 파싱하여 오늘 이후만
            CASE
                WHEN deadline ~ '^[0-9]{{2}}/[0-9]{{2}}' THEN
                    TO_DATE('{year}/' || SUBSTRING(deadline FROM 1 FOR 5), 'YYYY/MM/DD') >= CURRENT_DATE
                ELSE TRUE
            END
        )
    )
    """


def build_filter_query():
    """필터 SQL 쿼리 생성"""

    # 지역 필터
    location_conditions = " OR ".join([f"location LIKE '%{loc}%'" for loc in INCLUDE_LOCATIONS])

    # 경력 필터
    exp_conditions = " OR ".join([f"experience LIKE '%{exp}%'" for exp in INCLUDE_EXPERIENCE])

    # 제외 키워드
    exclude_conditions = " AND ".join([f"title NOT LIKE '%{kw}%'" for kw in EXCLUDE_KEYWORDS])

    # 마감일 필터
    deadline_condition = parse_deadline_filter()

    query = f"""
    SELECT
        jp.id,
        jp.title,
        c.name as company_name,
        jp.location,
        jp.experience,
        jp.deadline,
        jp.detail_url,
        jp.search_keyword,
        jp.crawled_at
    FROM job_postings jp
    JOIN companies c ON jp.company_id = c.id
    WHERE
        -- 지역 필터
        ({location_conditions})
        -- 경력 필터
        AND ({exp_conditions})
        -- 해외 관련 제외
        AND {exclude_conditions}
        -- 마감일 필터 (지난 공고 제외)
        AND {deadline_condition}
        -- 활성 공고만
        AND jp.status = 'active'
    ORDER BY jp.crawled_at DESC
    """

    return query


def get_filtered_postings(engine):
    """필터링된 공고 조회"""
    query = build_filter_query()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def print_summary(df):
    """필터 결과 요약 출력"""
    print("=" * 60)
    print("Vision OCR 대상 공고 필터 결과")
    print("=" * 60)

    print(f"\n📍 지역 필터: {', '.join(INCLUDE_LOCATIONS)}")
    print(f"📋 경력 필터: {', '.join(INCLUDE_EXPERIENCE)}")
    print(f"🚫 제외 키워드: {', '.join(EXCLUDE_KEYWORDS)}")
    print(f"📅 마감일 필터: 오늘 이후만 (상시채용 포함)")

    print(f"\n✅ 필터 통과: {len(df)}개 공고")

    if len(df) == 0:
        print("\n필터 조건에 맞는 공고가 없습니다.")
        return

    # 검색 키워드별 분포
    print(f"\n📊 검색 키워드별 분포:")
    keyword_counts = df['search_keyword'].value_counts()
    for kw, count in keyword_counts.items():
        print(f"   - {kw}: {count}개")

    # 지역별 분포
    print(f"\n📍 지역별 분포 (상위 5개):")
    # 지역 정규화 (첫 단어만)
    df['region'] = df['location'].apply(lambda x: x.split()[0] if pd.notna(x) else '기타')
    region_counts = df['region'].value_counts().head(5)
    for region, count in region_counts.items():
        print(f"   - {region}: {count}개")

    # 샘플 출력
    print(f"\n📝 샘플 공고 (최근 5개):")
    print("-" * 60)
    for _, row in df.head(5).iterrows():
        print(f"[{row['company_name']}] {row['title'][:40]}")
        print(f"   위치: {row['location']} | 경력: {row['experience']}")
        print()


def export_to_csv(df, output_path):
    """CSV로 내보내기"""
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 저장 완료: {output_path}")


def main():
    load_env()
    engine = get_db_engine()

    # 전체 공고 수 확인
    total_query = "SELECT COUNT(*) as cnt FROM job_postings WHERE status = 'active'"
    with engine.connect() as conn:
        total_count = pd.read_sql(text(total_query), conn).iloc[0]['cnt']

    # 필터링된 공고 조회
    df = get_filtered_postings(engine)

    print_summary(df)

    print(f"\n📈 필터 효율:")
    print(f"   - 전체 활성 공고: {total_count}개")
    print(f"   - 필터 통과: {len(df)}개")
    print(f"   - 필터링 비율: {len(df)/total_count*100:.1f}%" if total_count > 0 else "")

    # Vision OCR 비용 추정
    if len(df) > 0:
        cost_min = len(df) * 0.01
        cost_max = len(df) * 0.03
        print(f"\n💰 Vision OCR 예상 비용: ${cost_min:.2f} - ${cost_max:.2f}")

    # CSV 내보내기 옵션
    if '--export' in sys.argv:
        output_path = Path(__file__).parent.parent / "log" / "vision_target_postings.csv"
        output_path.parent.mkdir(exist_ok=True)
        export_to_csv(df, output_path)


if __name__ == "__main__":
    main()
