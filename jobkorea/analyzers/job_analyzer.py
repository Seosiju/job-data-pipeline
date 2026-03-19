"""
job_analyzer.py - LLM 기반 JD 구조화

OpenAI API를 사용하여 JD 텍스트에서 구조화된 정보 추출:
- 공고 유형 (단일/다중 포지션)
- 필수 요건
- 우대 사항
- 기술 스택/스킬
- 회사 도메인
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)


@dataclass
class AnalyzedJobPosting:
    """구조화된 채용공고 정보"""
    # 공고 유형
    is_multi_position: bool  # True: 여러 포지션 채용, False: 단일 포지션
    position_count: int  # 채용 포지션 수
    positions: list[str]  # 포지션 목록

    # 필수 요건
    required_education: Optional[str]  # 학력 요건
    required_experience: Optional[str]  # 경력 요건
    required_skills: list[str]  # 필수 스킬

    # 우대 사항
    preferred_skills: list[str]  # 우대 스킬
    preferred_certifications: list[str]  # 우대 자격증
    preferred_experience: list[str]  # 우대 경험

    # 회사/도메인 정보
    company_domain: str  # 회사 도메인 (IT, 헬스케어, 금융 등)
    job_category: str  # 직무 카테고리 (데이터분석, 개발, 기획 등)

    # 메타데이터
    raw_text_length: int
    analysis_confidence: str  # high, medium, low


ANALYSIS_PROMPT = """당신은 채용공고 분석 전문가입니다.
주어진 채용공고 텍스트를 분석하여 구조화된 정보를 추출해주세요.

## 분석할 채용공고:
{jd_text}

## 추출해야 할 정보:

1. **공고 유형 판별**
   - 하나의 공고에서 여러 포지션을 채용하는지 (예: "각 부문별 채용", "OO팀/XX팀 모집")
   - 단일 포지션인지

2. **필수 요건**
   - 학력: 학사, 석사, 박사 등
   - 경력: 신입, 경력 N년 이상 등
   - 필수 스킬: 반드시 갖춰야 하는 기술/역량

3. **우대 사항**
   - 우대 스킬: 있으면 좋은 기술
   - 자격증: 관련 자격증
   - 경험: 특정 경험 (예: "스타트업 경험", "대용량 데이터 처리 경험")

4. **도메인 분류**
   - company_domain: IT/소프트웨어, 헬스케어, 금융, 제조, 유통, 엔터테인먼트, 컨설팅, 공공기관, 기타
   - job_category: 데이터분석, 백엔드개발, 프론트엔드개발, 기획, 마케팅, 영업, 인사, 재무, 기타

## 출력 형식 (JSON):
{{
    "is_multi_position": true/false,
    "position_count": 숫자,
    "positions": ["포지션1", "포지션2"],
    "required_education": "학력요건 또는 null",
    "required_experience": "경력요건 또는 null",
    "required_skills": ["스킬1", "스킬2"],
    "preferred_skills": ["스킬1", "스킬2"],
    "preferred_certifications": ["자격증1"],
    "preferred_experience": ["경험1", "경험2"],
    "company_domain": "도메인",
    "job_category": "카테고리",
    "analysis_confidence": "high/medium/low"
}}

## 주의사항:
- 스킬명은 가능한 표준화해서 작성 (예: "파이썬" → "Python", "빅쿼리" → "BigQuery")
- 텍스트에 명시되지 않은 정보는 빈 리스트 또는 null로
- 불확실한 경우 confidence를 낮게 설정

JSON만 출력하세요:"""


def analyze_job_posting(
    jd_text: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
) -> Optional[AnalyzedJobPosting]:
    """
    JD 텍스트를 LLM으로 분석하여 구조화된 정보 추출

    Args:
        jd_text: 원본 JD 텍스트
        model: 사용할 OpenAI 모델
        temperature: 생성 온도 (낮을수록 일관성 높음)

    Returns:
        AnalyzedJobPosting 또는 None (분석 실패 시)
    """
    if not jd_text or len(jd_text) < 50:
        logger.warning("텍스트가 너무 짧아 분석 불가")
        return None

    try:
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        prompt = ChatPromptTemplate.from_template(ANALYSIS_PROMPT)
        chain = prompt | llm | JsonOutputParser()

        # 텍스트가 너무 길면 앞부분만 사용 (토큰 제한)
        max_chars = 8000
        truncated_text = jd_text[:max_chars] if len(jd_text) > max_chars else jd_text

        result = chain.invoke({"jd_text": truncated_text})

        return AnalyzedJobPosting(
            is_multi_position=result.get("is_multi_position", False),
            position_count=result.get("position_count", 1),
            positions=result.get("positions", []),
            required_education=result.get("required_education"),
            required_experience=result.get("required_experience"),
            required_skills=result.get("required_skills", []),
            preferred_skills=result.get("preferred_skills", []),
            preferred_certifications=result.get("preferred_certifications", []),
            preferred_experience=result.get("preferred_experience", []),
            company_domain=result.get("company_domain", "기타"),
            job_category=result.get("job_category", "기타"),
            raw_text_length=len(jd_text),
            analysis_confidence=result.get("analysis_confidence", "medium"),
        )

    except Exception as e:
        logger.error(f"JD 분석 실패: {e}")
        return None


def analyze_job_postings_batch(
    jd_texts: list[tuple[int, str]],  # [(job_posting_id, text), ...]
    model: str = "gpt-4o-mini",
    progress_callback=None,
) -> dict[int, AnalyzedJobPosting]:
    """
    여러 JD를 일괄 분석

    Args:
        jd_texts: (job_posting_id, text) 튜플 리스트
        model: 사용할 OpenAI 모델
        progress_callback: 진행 콜백 함수 (current, total, jp_id)

    Returns:
        dict: {job_posting_id: AnalyzedJobPosting}
    """
    results = {}

    for i, (jp_id, text) in enumerate(jd_texts):
        if progress_callback:
            progress_callback(i + 1, len(jd_texts), jp_id)

        result = analyze_job_posting(text, model=model)
        if result:
            results[jp_id] = result

    return results


def analyzed_to_dict(analyzed: AnalyzedJobPosting) -> dict:
    """AnalyzedJobPosting을 dict로 변환 (DB 저장용)"""
    return asdict(analyzed)
