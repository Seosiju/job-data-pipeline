"""
extractors - JD 텍스트 추출 모듈
"""

from .html_extractor import extract_jd_text, extract_jd_text_batch

__all__ = ["extract_jd_text", "extract_jd_text_batch"]
