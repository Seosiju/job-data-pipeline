"""
PoC: 잡코리아 OCR 텍스트 수집 및 LLM 파싱

이 스크립트는 잡코리아 채용공고의 상세요강(이미지)을 OCR 텍스트로 추출하고,
LangChain + OpenAI를 사용하여 직무별로 구조화된 데이터로 파싱합니다.

실행:
    python scripts/poc_ocr_parsing.py

필요 패키지:
    pip install langchain langchain-openai

환경변수:
    OPENAI_API_KEY: OpenAI API 키 (.env에 설정)
"""

import os
import re
import json
from pathlib import Path
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


# === 데이터 모델 ===

class Position(BaseModel):
    """개별 직무 정보"""
    position_name: str = Field(description="직무명")
    experience_required: str = Field(description="경력 요구사항")
    responsibilities: List[str] = Field(description="담당업무 리스트")
    requirements: List[str] = Field(description="자격요건 리스트")
    preferred: List[str] = Field(description="우대요건 리스트")
    tech_stack: List[str] = Field(description="기술스택")


class JobPostingParsed(BaseModel):
    """파싱된 채용공고"""
    company_name: str = Field(description="회사명")
    posting_title: str = Field(description="공고 제목")
    positions: List[Position] = Field(description="직무 목록")


# === OCR 텍스트 추출 ===

def extract_ocr_url(jd_url: str) -> str | None:
    """JD 페이지에서 OCR signed URL을 추출한다."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(jd_url)
        import time
        time.sleep(4)  # JavaScript 렌더링 대기

        page_source = driver.page_source

        # OCR URL 패턴 (AWS S3 signed URL)
        pattern = r'https://job-hub-files[^"]*_OCR\.html[^"]*Amz-Signature=[a-f0-9]+'
        matches = re.findall(pattern, page_source)

        if matches:
            ocr_url = max(matches, key=len)  # 가장 긴 매치 선택
            ocr_url = ocr_url.encode().decode('unicode_escape')
            return ocr_url

        return None

    finally:
        driver.quit()


def fetch_ocr_text(ocr_url: str) -> str | None:
    """OCR URL에서 텍스트를 추출한다."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    response = requests.get(ocr_url, headers=headers, timeout=15)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator='\n', strip=True)

    return None


# === LLM 파싱 ===

def parse_ocr_with_llm(ocr_text: str, api_key: str) -> dict:
    """OCR 텍스트를 LLM으로 파싱하여 구조화된 데이터로 변환한다."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    parser = JsonOutputParser(pydantic_object=JobPostingParsed)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """채용공고 OCR 텍스트를 구조화된 JSON으로 변환하세요.
각 직무를 분리하고, 기술스택은 언어/프레임워크/도구를 모두 추출하세요.
{format_instructions}"""),
        ("human", "{ocr_text}")
    ])

    chain = prompt | llm | parser

    return chain.invoke({
        "ocr_text": ocr_text,
        "format_instructions": parser.get_format_instructions()
    })


# === 메인 ===

def main():
    # 환경변수 로드
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY가 설정되지 않았습니다.")
        return

    # 샘플 JD URL (안랩)
    jd_url = "https://www.jobkorea.co.kr/Recruit/GI_Read/48647720"

    print(f"=== OCR 텍스트 추출 ===")
    print(f"JD URL: {jd_url}")

    ocr_url = extract_ocr_url(jd_url)
    if not ocr_url:
        print("OCR URL을 찾지 못했습니다.")
        return

    print(f"OCR URL 발견 (길이: {len(ocr_url)})")

    ocr_text = fetch_ocr_text(ocr_url)
    if not ocr_text:
        print("OCR 텍스트를 가져오지 못했습니다.")
        return

    print(f"OCR 텍스트 추출 완료 ({len(ocr_text)} chars)")

    print(f"\n=== LLM 파싱 ===")
    result = parse_ocr_with_llm(ocr_text, api_key)

    print(f"회사명: {result['company_name']}")
    print(f"공고제목: {result['posting_title']}")
    print(f"직무 수: {len(result['positions'])}개\n")

    for i, pos in enumerate(result['positions'], 1):
        print(f"[{i}] {pos['position_name']}")
        print(f"    경력: {pos['experience_required']}")
        print(f"    기술스택: {', '.join(pos['tech_stack'])}")
        print()

    # JSON 저장
    output_path = Path(__file__).parent.parent / "log" / "ocr_parsed_sample.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"결과 저장: {output_path}")


if __name__ == "__main__":
    main()
