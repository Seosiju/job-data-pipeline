# 데이터 검증 로직 가이드

## 개요

`validators.py`는 크롤링된 데이터를 DB에 저장하기 전 검증 및 정제하는 순수 함수 모듈입니다.

## 핵심 원칙

1. **저장은 무조건 진행**: 검증 실패 시에도 데이터는 저장하되, 로그만 기록
2. **순수 함수**: 상태 없이 입력 dict를 받아 정제된 dict 반환
3. **방어적 코딩**: None, 빈 문자열, 비정상 값에 대한 안전한 처리

## 주요 함수

### 1. validate_job_posting(data: dict) -> dict

채용공고 데이터 검증 및 정제

**검증 항목:**
- 필수 필드 (title, company) 누락 체크
- 급여: 비현실적 값 필터링, "협의" -> None
- 날짜: 형식 검증, "채용시까지" -> "상시채용"
- detail_url: 유효성 검증
- 경력: "신입/인턴" -> "신입"
- 위치: 여러 지역 -> 첫 번째만

**사용 예시:**
```python
from validators import validate_job_posting

raw_data = {
    "title": "백엔드 개발자",
    "company": "테크 주식회사",
    "salary": "협의",
    "posted_date": "등록: 2024-02-26",
    "deadline": "채용시까지",
    "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/12345",
    "experience": "신입/인턴",
    "location": "서울 강남구, 서울 서초구",
}

validated = validate_job_posting(raw_data)
# {
#     "title": "백엔드 개발자",
#     "company": "테크 주식회사",
#     "salary": None,  # "협의" -> None
#     "posted_date": "2024-02-26",  # "등록: " 제거
#     "deadline": "상시채용",  # "채용시까지" -> "상시채용"
#     "detail_url": "https://www.jobkorea.co.kr/Recruit/GI_Read/12345",
#     "experience": "신입",  # "신입/인턴" -> "신입"
#     "location": "서울 강남구",  # 첫 번째 지역만
# }
```

### 2. validate_company_details(data: dict) -> dict

회사 정보 검증 및 정제

**검증 항목:**
- 설립연도: 1900~현재 범위 체크
- 사원수: "10명" -> 숫자 추출, 비현실적 값(100만명 이상) 필터링
- 회사 규모: 표준 카테고리로 통일 (대기업, 중견기업, 중소기업 등)
- 홈페이지 URL: 형식 검증

**사용 예시:**
```python
from validators import validate_company_details

raw_data = {
    "company_size": "중소기업 (주식회사)",
    "employee_count": "100명",
    "establishment_year": "2020년 설립",
    "homepage_url": "https://example.com",
}

validated = validate_company_details(raw_data)
# {
#     "company_size": "중소기업",  # 괄호 제거
#     "employee_count": "100명",
#     "establishment_year": "2020",  # 연도만 추출
#     "homepage_url": "https://example.com",
# }
```

## 세부 정제 함수

### 급여 정제 (normalize_salary)

**변환 규칙:**
- "협의", "면접 후 결정" -> None
- 연봉 100억 이상 -> None (비현실적)
- 빈 문자열 -> None

**예시:**
```python
normalize_salary("4000만원")           # "4000만원"
normalize_salary("협의")                # None
normalize_salary("100억원 이상")        # None
```

### 날짜 정제 (normalize_date, normalize_deadline)

**변환 규칙:**
- "등록: 2024-02-26" -> "2024-02-26"
- "채용시까지", "상시채용" -> "상시채용"
- "마감: 2024-03-10" -> "2024-03-10"

**예시:**
```python
normalize_date("등록: 2024-02-26", "posted_date")  # "2024-02-26"
normalize_deadline("채용시까지")                     # "상시채용"
normalize_deadline("마감: 2024-03-10")              # "2024-03-10"
```

### 회사 정보 정제

#### 설립연도 (normalize_establishment_year)

**변환 규칙:**
- 1900년 ~ 현재년도 범위 체크
- "2020년 설립" -> "2020"
- 범위 밖 -> None

**예시:**
```python
normalize_establishment_year("2020")         # "2020"
normalize_establishment_year("2020년 설립")  # "2020"
normalize_establishment_year("1800")         # None (범위 밖)
```

#### 사원수 (normalize_employee_count)

**변환 규칙:**
- "10명" -> 숫자 추출
- 100만명 이상 -> None (비현실적)
- 숫자 없음 -> 원본 유지

**예시:**
```python
normalize_employee_count("100명")        # "100명"
normalize_employee_count("1,000명 이상") # "1,000명 이상"
normalize_employee_count("1000000명")    # None (비현실적)
```

#### 회사 규모 (normalize_company_size)

**표준 카테고리:**
- 대기업
- 중견기업
- 중소기업
- 외국계기업
- 공기업
- 스타트업

**변환 규칙:**
- 키워드 매칭: "대규모" -> "대기업"
- 괄호 제거: "중소기업 (주식회사)" -> "중소기업"

**예시:**
```python
normalize_company_size("대기업")              # "대기업"
normalize_company_size("중소기업 (주식회사)")  # "중소기업"
normalize_company_size("벤처기업")            # "스타트업"
```

### 경력 정제 (normalize_experience)

**변환 규칙:**
- "신입", "인턴" -> "신입"
- "경력무관", "경력 관계없음" -> "경력무관"
- 나머지 -> 원본 유지

**예시:**
```python
normalize_experience("신입")       # "신입"
normalize_experience("인턴")       # "신입"
normalize_experience("경력무관")   # "경력무관"
normalize_experience("3년 이상")   # "3년 이상"
```

### 위치 정제 (normalize_location)

**변환 규칙:**
- 여러 지역 -> 첫 번째만
- 구분자: 콤마(,), 슬래시(/)

**예시:**
```python
normalize_location("서울 강남구")                  # "서울 강남구"
normalize_location("서울 강남구, 서울 서초구")     # "서울 강남구"
normalize_location("서울 강남구 / 경기 성남시")    # "서울 강남구"
```

### URL 검증 (is_valid_url)

**검증 규칙:**
- http:// 또는 https:// 필수
- 도메인 형식 체크
- localhost 허용

**예시:**
```python
is_valid_url("https://www.jobkorea.co.kr/Recruit/GI_Read/12345")  # True
is_valid_url("http://example.com")                                # True
is_valid_url("www.example.com")                                   # False
is_valid_url("not-a-url")                                         # False
```

## 통합 사용 (main.py)

### Phase 1: 목록 크롤링

```python
from validators import validate_job_posting

for job in jobs:
    # 데이터 검증 및 정제
    validated_job = validate_job_posting(job)

    # DB 저장
    company_id = db.get_or_create_company(
        conn,
        validated_job.get("company"),
        industry=validated_job.get("industry", "")
    )
    db.insert_job_posting(conn, company_id, validated_job, keyword)
```

### Phase 2: 상세 크롤링

```python
from validators import validate_company_details

# 파싱
details = parse_company_detail(html)

# 데이터 검증 및 정제
validated_details = validate_company_details(details)

# DB 업데이트
if any(validated_details.values()):
    db.update_company_details(company_id, validated_details)
```

## 테스트

전체 43개 테스트 케이스 구현:

```bash
# validators 테스트만 실행
pytest tests/test_validators.py -v

# 전체 테스트 실행
pytest tests/ -v
```

**테스트 커버리지:**
- 정상 케이스
- 비정상 케이스 (누락, 비현실적 값, 잘못된 형식)
- 엣지 케이스 (빈 문자열, None, 공백)

## 로깅

검증 실패 시 자동 로깅:

```python
import logging

logger = logging.getLogger(__name__)

# WARNING: 필수 필드 누락
logger.warning("필수 필드 누락: title이 비어있음")

# WARNING: 비현실적 값
logger.warning(f"비현실적 급여 값: {salary}")

# DEBUG: 파싱 실패
logger.debug(f"급여 파싱 실패: {salary} - {e}")
```

## 확장 가이드

새로운 검증 로직 추가 시:

1. `validators.py`에 순수 함수 추가
2. `tests/test_validators.py`에 테스트 케이스 추가
3. 필요시 `validate_job_posting()` 또는 `validate_company_details()`에 통합
4. `main.py`에서 호출 (이미 통합되어 있으면 자동 적용)

**예시: 새로운 필드 검증 추가**

```python
# validators.py
def normalize_tech_stack(tech_stack: str) -> Optional[str]:
    """기술 스택 정제: 파이썬 -> Python"""
    if not tech_stack:
        return None

    mapping = {
        "파이썬": "Python",
        "자바스크립트": "JavaScript",
        # ...
    }

    for korean, english in mapping.items():
        if korean in tech_stack:
            tech_stack = tech_stack.replace(korean, english)

    return tech_stack

# validate_job_posting() 함수에 추가
def validate_job_posting(data: dict) -> dict:
    # ...
    tech_stack = validated.get("tech_stack", "")
    validated["tech_stack"] = normalize_tech_stack(tech_stack)
    # ...
```

## 주의사항

1. **검증 실패 시에도 저장은 진행**: 데이터 손실 방지
2. **None vs 빈 문자열**: DB 스키마에 따라 적절히 선택
3. **로깅 레벨 선택**:
   - WARNING: 중요한 검증 실패 (필수 필드 누락, 비현실적 값)
   - DEBUG: 일반적인 파싱 실패 (형식 불일치)
4. **성능 고려**: 정규식 패턴은 모듈 레벨에서 compile

## 참고

- DB 스키마: `database.py`의 `create_tables()` 참조
- 파싱 로직: `parser.py`의 `parse_job_cards()`, `parse_company_detail()` 참조
- 통합 흐름: `main.py`의 `run_phase1()`, `run_phase2()` 참조
