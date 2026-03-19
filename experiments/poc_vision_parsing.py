"""
PoC: 잡코리아 채용공고 이미지 Vision API 파싱

회사가 직접 올린 상세요강 이미지를 Vision LLM으로 분석하여
직무 정보를 구조화된 데이터로 추출합니다.

실행:
    python scripts/poc_vision_parsing.py

필요 패키지:
    pip install openai

환경변수:
    OPENAI_API_KEY: OpenAI API 키 (.env에 설정)
"""

import os
import re
import json
import base64
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from openai import OpenAI


def load_env():
    """환경변수 로드"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()


def create_driver() -> webdriver.Chrome:
    """Selenium 드라이버 생성"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def extract_detail_images(jd_url: str) -> list[dict]:
    """
    JD 상세 페이지에서 상세요강 이미지 URL들을 추출한다.
    잡코리아는 상세요강을 iframe 안에 로드하므로 iframe URL을 직접 접근한다.

    Returns:
        list of {"url": str, "title": str, "width": int}
    """
    import re
    import time

    driver = create_driver()
    images = []

    try:
        # JD URL에서 Gno 추출
        gno_match = re.search(r'GI_Read/(\d+)', jd_url)
        if gno_match:
            gno = gno_match.group(1)
            # iframe URL 직접 접근 (이게 실제 콘텐츠)
            iframe_url = f"https://www.jobkorea.co.kr/Recruit/GI_Read_Comt_Ifrm?Gno={gno}"
        else:
            iframe_url = jd_url

        print(f"콘텐츠 로딩: {iframe_url}")
        driver.get(iframe_url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 상세요강 이미지 찾기
        for img in soup.find_all('img'):
            src = img.get('src', '')
            title = img.get('title', '') or img.get('alt', '')
            width = img.get('width', '')

            if not src:
                continue

            # 로고, 아이콘 등 제외
            if any(skip in src.lower() for skip in ['logo', 'icon', 'btn_', 'button', 'banner', 'facebook', 'tracker']):
                continue

            # 작은 이미지 제외 (width < 300)
            try:
                w = int(width) if width else 0
                if w > 0 and w < 300:
                    continue
            except ValueError:
                pass

            # 절대 URL로 변환
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(iframe_url, src)
            elif not src.startswith('http'):
                src = urljoin(iframe_url, src)

            images.append({
                "url": src,
                "title": title,
                "width": width
            })

        # 중복 제거
        seen = set()
        unique_images = []
        for img in images:
            if img['url'] not in seen:
                seen.add(img['url'])
                unique_images.append(img)

        return unique_images

    finally:
        driver.quit()


def download_image_as_base64(image_url: str) -> Optional[str]:
    """이미지를 다운로드하여 base64로 인코딩"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        response = requests.get(image_url, headers=headers, timeout=15)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"이미지 다운로드 실패: {e}")
    return None


def get_image_media_type(url: str) -> str:
    """URL에서 이미지 타입 추출"""
    url_lower = url.lower()
    if '.png' in url_lower:
        return 'image/png'
    elif '.gif' in url_lower:
        return 'image/gif'
    elif '.webp' in url_lower:
        return 'image/webp'
    return 'image/jpeg'


def parse_image_with_vision(image_url: str, api_key: str) -> dict:
    """
    Vision API로 채용공고 이미지를 분석하여 구조화된 데이터로 변환한다.
    """
    client = OpenAI(api_key=api_key)

    # 이미지 다운로드 및 base64 인코딩
    print(f"이미지 다운로드: {image_url[:80]}...")
    image_base64 = download_image_as_base64(image_url)

    if not image_base64:
        return {"error": "이미지 다운로드 실패"}

    media_type = get_image_media_type(image_url)

    print("Vision API 호출 중...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """채용공고 이미지를 분석하여 JSON 형식으로 정보를 추출하세요.

반드시 아래 형식의 JSON만 출력하세요:
{
    "company_name": "회사명",
    "posting_title": "공고 제목",
    "positions": [
        {
            "position_name": "직무명",
            "department": "부서명 (있으면)",
            "experience_required": "경력 요구사항",
            "employment_type": "고용형태 (정규직/계약직/인턴 등)",
            "responsibilities": ["담당업무1", "담당업무2"],
            "requirements": ["자격요건1", "자격요건2"],
            "preferred": ["우대사항1", "우대사항2"],
            "tech_stack": ["기술1", "기술2"]
        }
    ],
    "benefits": ["복리후생1", "복리후생2"],
    "location": "근무지",
    "salary": "급여 정보 (있으면)"
}

여러 직무가 있으면 positions 배열에 모두 포함하세요.
이미지에서 읽을 수 없는 필드는 빈 문자열 또는 빈 배열로 두세요."""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "이 채용공고 이미지에서 직무 정보를 추출해주세요."
                    }
                ]
            }
        ],
        max_tokens=2000,
        temperature=0
    )

    content = response.choices[0].message.content

    # JSON 파싱 시도
    try:
        # ```json ... ``` 블록 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # 직접 JSON 파싱
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_response": content, "error": "JSON 파싱 실패"}


def main():
    load_env()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY가 설정되지 않았습니다.")
        return

    # 테스트: 화이트스캔 공고 이미지 직접 사용
    # (fixture에서 확인한 URL)
    test_image_url = "https://whitescan.com/images/_jobkorea_always.png"

    print("=" * 50)
    print("Vision API 기반 채용공고 이미지 파싱 PoC")
    print("=" * 50)
    print(f"\n테스트 이미지: {test_image_url}\n")

    result = parse_image_with_vision(test_image_url, api_key)

    if "error" in result:
        print(f"오류: {result.get('error')}")
        if "raw_response" in result:
            print(f"원본 응답:\n{result['raw_response']}")
        return

    # 결과 출력
    print("\n=== 파싱 결과 ===\n")

    print(f"회사명: {result.get('company_name', 'N/A')}")
    print(f"공고제목: {result.get('posting_title', 'N/A')}")
    print(f"근무지: {result.get('location', 'N/A')}")

    positions = result.get('positions', [])
    print(f"직무 수: {len(positions)}개\n")

    for i, pos in enumerate(positions, 1):
        print(f"[{i}] {pos.get('position_name', 'N/A')}")
        print(f"    경력: {pos.get('experience_required', 'N/A')}")
        print(f"    고용형태: {pos.get('employment_type', 'N/A')}")
        tech = pos.get('tech_stack', [])
        if tech:
            print(f"    기술스택: {', '.join(tech)}")
        print()

    # JSON 저장
    output_path = Path(__file__).parent.parent / "log" / "vision_parsed_sample.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"결과 저장: {output_path}")


if __name__ == "__main__":
    main()
