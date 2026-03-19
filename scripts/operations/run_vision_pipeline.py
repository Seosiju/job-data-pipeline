"""
Vision OCR 파이프라인 실행

필터링된 공고에서 랜덤 N개를 선택하여 Vision OCR로 상세 정보 추출

실행:
    python scripts/run_vision_pipeline.py              # 기본 10개
    python scripts/run_vision_pipeline.py --limit 5    # 5개만
    python scripts/run_vision_pipeline.py --all        # 전체 (주의: 비용 발생)
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import pandas as pd

# Vision 파싱 함수 import
from poc_vision_parsing import (
    load_env,
    parse_image_with_vision,
    extract_detail_images,
)


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


def get_filtered_posting_ids(engine, limit=None, random_sample=True):
    """필터링된 공고 ID 목록 조회"""
    from filter_for_vision import build_filter_query

    query = build_filter_query()

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if random_sample and limit and limit < len(df):
        df = df.sample(n=limit, random_state=random.randint(1, 10000))
    elif limit:
        df = df.head(limit)

    return df


def run_pipeline(limit=10, save_results=True):
    """파이프라인 실행"""
    load_env()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        return

    engine = get_db_engine()

    print("=" * 60)
    print(f"Vision OCR 파이프라인 - {limit}개 공고 처리")
    print("=" * 60)

    # 필터링된 공고 가져오기
    print("\n📋 필터링된 공고 선택 중...")
    df = get_filtered_posting_ids(engine, limit=limit, random_sample=True)

    print(f"   선택된 공고: {len(df)}개")

    results = []
    success_count = 0
    fail_count = 0

    for idx, row in df.iterrows():
        print(f"\n[{len(results)+1}/{len(df)}] {row['company_name']}")
        print(f"   제목: {row['title'][:50]}...")
        print(f"   URL: {row['detail_url']}")

        try:
            # 1. 상세 페이지에서 이미지 추출
            print("   → 이미지 추출 중...")
            images = extract_detail_images(row['detail_url'])

            if not images:
                print("   ⚠️ 이미지를 찾지 못함")
                fail_count += 1
                results.append({
                    "job_posting_id": row['id'],
                    "company_name": row['company_name'],
                    "title": row['title'],
                    "status": "no_image",
                    "error": "이미지를 찾지 못함"
                })
                continue

            # 첫 번째 큰 이미지 사용
            image_url = images[0]['url']
            print(f"   → 이미지 발견: {image_url[:60]}...")

            # 2. Vision API로 파싱
            print("   → Vision API 파싱 중...")
            parsed = parse_image_with_vision(image_url, api_key)

            if "error" in parsed:
                print(f"   ⚠️ 파싱 실패: {parsed['error']}")
                fail_count += 1
                results.append({
                    "job_posting_id": row['id'],
                    "company_name": row['company_name'],
                    "title": row['title'],
                    "status": "parse_error",
                    "error": parsed.get('error')
                })
                continue

            # 성공
            positions = parsed.get('positions', [])
            print(f"   ✅ 성공! {len(positions)}개 직무 추출")

            for pos in positions[:3]:  # 상위 3개만 출력
                print(f"      - {pos.get('position_name', 'N/A')}")

            success_count += 1
            results.append({
                "job_posting_id": row['id'],
                "company_name": row['company_name'],
                "title": row['title'],
                "detail_url": row['detail_url'],
                "image_url": image_url,
                "status": "success",
                "parsed_data": parsed
            })

        except Exception as e:
            print(f"   ❌ 오류: {e}")
            fail_count += 1
            results.append({
                "job_posting_id": row['id'],
                "company_name": row['company_name'],
                "title": row['title'],
                "status": "error",
                "error": str(e)
            })

    # 결과 요약
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {fail_count}개")
    print(f"📊 성공률: {success_count/len(df)*100:.1f}%")

    # 결과 저장
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent.parent / "log" / f"vision_pipeline_result_{timestamp}.json"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Vision OCR 파이프라인')
    parser.add_argument('--limit', type=int, default=10, help='처리할 공고 수 (기본: 10)')
    parser.add_argument('--all', action='store_true', help='전체 처리 (주의: 비용 발생)')

    args = parser.parse_args()

    if args.all:
        confirm = input("⚠️ 전체 공고를 처리합니다. 비용이 발생합니다. 계속하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소됨")
            return
        limit = None
    else:
        limit = args.limit

    run_pipeline(limit=limit)


if __name__ == "__main__":
    main()
