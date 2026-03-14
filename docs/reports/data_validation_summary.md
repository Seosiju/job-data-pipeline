# 데이터 검증 로직 구현 요약

## 구현 내용

잡코리아 크롤링 시스템에 데이터 검증 및 정제 로직을 추가했습니다.

### 1. 신규 파일

#### `/Users/snu.sim/git/jobkorea/validators.py` (502줄)

**핵심 함수:**
- `validate_job_posting(data: dict) -> dict`: 채용공고 데이터 검증
- `validate_company_details(data: dict) -> dict`: 회사 정보 검증

**세부 정제 함수:**
- `normalize_salary()`: 급여 정제 ("협의" -> None, 비현실적 값 필터링)
- `normalize_date()`, `normalize_deadline()`: 날짜 정제
- `normalize_establishment_year()`: 설립연도 검증 (1900~현재)
- `normalize_employee_count()`: 사원수 정제 (비현실적 값 필터링)
- `normalize_company_size()`: 회사 규모 표준화 (대기업, 중견기업 등)
- `normalize_experience()`: 경력 통일 ("신입/인턴" -> "신입")
- `normalize_location()`: 위치 정제 (여러 지역 -> 첫 번째만)
- `is_valid_url()`: URL 유효성 검증

**특징:**
- 순수 함수 설계 (상태 없음)
- 검증 실패 시에도 저장 진행 (로그만 기록)
- 방어적 코딩 (None, 빈 문자열 안전 처리)

#### `/Users/snu.sim/git/jobkorea/tests/test_validators.py` (433줄)

**테스트 커버리지:**
- 43개 테스트 케이스
- 정상 케이스, 비정상 케이스, 엣지 케이스 모두 커버
- 100% 통과 확인

**테스트 클래스:**
- `TestValidateJobPosting`: 채용공고 검증 통합 테스트
- `TestNormalizeSalary`: 급여 정제
- `TestNormalizeDate`: 날짜 정제
- `TestNormalizeDeadline`: 마감일 정제
- `TestNormalizeEstablishmentYear`: 설립연도 검증
- `TestNormalizeEmployeeCount`: 사원수 정제
- `TestNormalizeCompanySize`: 회사 규모 정제
- `TestNormalizeExperience`: 경력 정제
- `TestNormalizeLocation`: 위치 정제
- `TestIsValidUrl`: URL 검증
- `TestValidateCompanyDetails`: 회사 정보 검증 통합 테스트

#### `/Users/snu.sim/git/jobkorea/docs/guides/validators_guide.md`

완전한 사용 가이드 및 API 문서

### 2. 수정된 파일

#### `/Users/snu.sim/git/jobkorea/main.py`

**변경 사항:**

1. **Import 추가:**
```python
from validators import validate_job_posting, validate_company_details
```

2. **Phase 1 (목록 크롤링) 수정:**
```python
# 기존 (라인 64-78)
for job in jobs:
    company_id = db.get_or_create_company(conn, company_name, industry=job.get("industry", ""))
    db.insert_job_posting(conn, company_id, job, keyword)

# 변경 후
for job in jobs:
    validated_job = validate_job_posting(job)  # 검증 추가
    company_id = db.get_or_create_company(conn, validated_job.get("company"), industry=validated_job.get("industry", ""))
    db.insert_job_posting(conn, company_id, validated_job, keyword)
```

3. **Phase 2 (상세 크롤링) 수정:**
```python
# 기존 (라인 165-174)
if html:
    details = parse_company_detail(html)
    if any(details.values()):
        db.update_company_details(company_id, details)

# 변경 후
if html:
    details = parse_company_detail(html)
    validated_details = validate_company_details(details)  # 검증 추가
    if any(validated_details.values()):
        db.update_company_details(company_id, validated_details)
```

## 검증 항목 상세

### 채용공고 검증 (validate_job_posting)

| 필드 | 검증 내용 | 변환 예시 |
|------|----------|-----------|
| title | 필수 필드, 비어있으면 "제목 없음" | "" -> "제목 없음" |
| company | 필수 필드, 비어있으면 "회사명 없음" | "" -> "회사명 없음" |
| salary | 협의 -> None, 비현실적 값 필터링 | "협의" -> None, "100억" -> None |
| posted_date | "등록:" 제거 | "등록: 2024-02-26" -> "2024-02-26" |
| deadline | 상시채용 통일, "마감:" 제거 | "채용시까지" -> "상시채용" |
| detail_url | URL 형식 검증 | "not-url" -> "" |
| experience | 표준 카테고리 통일 | "신입/인턴" -> "신입" |
| location | 여러 지역 -> 첫 번째만 | "서울, 경기" -> "서울" |

### 회사 정보 검증 (validate_company_details)

| 필드 | 검증 내용 | 변환 예시 |
|------|----------|-----------|
| establishment_year | 1900~현재 범위, 연도만 추출 | "2020년 설립" -> "2020", "1800" -> None |
| employee_count | 비현실적 값 필터링 | "100명" -> "100명", "1000000명" -> None |
| company_size | 표준 카테고리, 괄호 제거 | "중소기업 (주식회사)" -> "중소기업" |
| homepage_url | URL 형식 검증 | "not-url" -> None |

## 실행 결과

### 테스트 통과

```bash
$ pytest tests/test_validators.py -v
============================= test session starts ==============================
collected 43 items

tests/test_validators.py::TestValidateJobPosting::test_valid_job_posting PASSED
tests/test_validators.py::TestValidateJobPosting::test_missing_required_fields PASSED
tests/test_validators.py::TestValidateJobPosting::test_invalid_url PASSED
tests/test_validators.py::TestValidateJobPosting::test_ongoing_deadline PASSED
...
============================== 43 passed in 0.04s ==============================
```

### 전체 테스트 통과

```bash
$ pytest tests/ -v
============================= test session starts ==============================
collected 79 items

...
============================== 69 passed, 10 skipped in 0.28s ==================
```

## 데이터 품질 향상 효과

### Before (검증 없음)

```python
{
    "title": "",
    "company": "테크 (주)",
    "salary": "협의",
    "posted_date": "등록: 2024-02-26",
    "deadline": "채용시까지",
    "detail_url": "invalid-url",
    "experience": "신입/인턴",
    "location": "서울 강남구, 서울 서초구",
}
```

### After (검증 적용)

```python
{
    "title": "제목 없음",  # 빈 문자열 처리
    "company": "테크 (주)",
    "salary": None,  # "협의" -> None
    "posted_date": "2024-02-26",  # "등록:" 제거
    "deadline": "상시채용",  # "채용시까지" -> "상시채용"
    "detail_url": "",  # 유효하지 않은 URL 제거
    "experience": "신입",  # "신입/인턴" -> "신입"
    "location": "서울 강남구",  # 첫 번째 지역만
}
```

## 로깅 예시

```
WARNING: 필수 필드 누락: title이 비어있음
WARNING: 비현실적 급여 값: 100억원 이상
WARNING: 유효하지 않은 URL: not-a-valid-url
WARNING: 설립연도 범위 오류: 1800 (유효 범위: 1900~2026)
DEBUG: 급여 파싱 실패: 알 수 없음 - ...
```

## 성능 영향

- 검증 로직은 순수 함수로 구현되어 오버헤드 최소화
- 테스트 실행 시간: 0.04초 (43개 테스트)
- 크롤링 속도에 영향 없음 (네트워크 I/O가 병목)

## 향후 확장

### 1. 기술 스택 표준화

```python
def normalize_tech_stack(tech_stack: str) -> Optional[str]:
    """파이썬 -> Python, 자바스크립트 -> JavaScript"""
    mapping = {
        "파이썬": "Python",
        "자바스크립트": "JavaScript",
        "리액트": "React",
        # ...
    }
    # ...
```

### 2. 중복 검출

```python
def detect_duplicate_job(job1: dict, job2: dict) -> bool:
    """fuzzy matching으로 중복 공고 검출"""
    # title 유사도, company 일치, location 일치 등
    pass
```

### 3. 데이터 스코어링

```python
def calculate_data_quality_score(data: dict) -> float:
    """데이터 품질 점수 (0.0 ~ 1.0)"""
    # 필수 필드 채움 정도, URL 유효성, 날짜 형식 등
    pass
```

## 프로젝트 구조 (업데이트)

```
jobkorea/
├── validators.py          # 신규: 데이터 검증 로직
├── main.py                # 수정: validators 통합
├── tests/
│   └── test_validators.py # 신규: validators 테스트
└── docs/
    ├── validators_guide.md           # 신규: 사용 가이드
    └── data_validation_summary.md    # 신규: 구현 요약
```

## 체크리스트

- [x] validators.py 구현 (502줄)
- [x] test_validators.py 작성 (433줄, 43개 테스트)
- [x] main.py 수정 (Phase 1, Phase 2에 검증 적용)
- [x] 전체 테스트 통과 (69 passed, 10 skipped)
- [x] 문서화 (validators_guide.md)
- [x] 구현 요약 (data_validation_summary.md)

## 사용법

### 1. 직접 사용

```python
from validators import validate_job_posting, validate_company_details

# 채용공고 검증
job = {"title": "개발자", "company": "회사", "salary": "협의"}
validated_job = validate_job_posting(job)

# 회사 정보 검증
company = {"establishment_year": "2020년", "employee_count": "100명"}
validated_company = validate_company_details(company)
```

### 2. main.py 실행 (자동 적용)

```bash
python main.py
```

Phase 1, Phase 2에서 자동으로 검증 로직이 적용됩니다.

### 3. 테스트 실행

```bash
# validators 테스트만
pytest tests/test_validators.py -v

# 전체 테스트
pytest tests/ -v
```

## 참고 문서

- **사용 가이드**: `/Users/snu.sim/git/jobkorea/docs/guides/validators_guide.md`
- **구현 상세**: `/Users/snu.sim/git/jobkorea/validators.py`
- **테스트 코드**: `/Users/snu.sim/git/jobkorea/tests/test_validators.py`
- **통합 흐름**: `/Users/snu.sim/git/jobkorea/main.py`
