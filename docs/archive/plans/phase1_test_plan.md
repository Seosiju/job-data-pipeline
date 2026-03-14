---
type: plan
status: historical
last_reviewed: 2026-03-14
superseded_by: docs/plans/data_pipeline_service_roadmap.md
related_report:
source_of_truth: false
---

# Phase 1 - 첫 크롤링 테스트 기획서 (Historical Snapshot)

> 상태: Historical snapshot
> 주의: CSV 1페이지 수동 검증 단계의 초기 부트스트랩 문서입니다. 현재 실행 경로와 디렉터리 구조는 이 문서와 다릅니다.

## 목표

빠르게 실제 데이터를 확인하고, 이를 토대로 본 기획(system_architecture.md)을 확장하기 위한 최소한의 토대 구축.

> **핵심 원칙: 완벽한 시스템보다 작동하는 결과물을 먼저.**

---

## 범위 (Scope)

| 항목 | 테스트 범위 | 향후 확장 |
|------|------------|----------|
| 페이지 수 | **1페이지만** | 전체 페이지 |
| 저장 방식 | **CSV 파일** | PostgreSQL |
| 수집 항목 | **핵심 5개만** | 14개 전체 |
| 크롤링 단계 | **목록 페이지만** | 상세 페이지 포함 |
| 자동화 | **수동 실행** | 스케줄러(cron) |

---

## 수집 항목 (최소 5개)

| 컬럼명 | 설명 | 이유 |
|--------|------|------|
| `title` | 공고 제목 | 핵심 식별자 |
| `company` | 회사명 | 핵심 식별자 |
| `location` | 근무지역 | 필터링에 중요 |
| `experience` | 경력 조건 | 필터링에 중요 |
| `detail_url` | 상세 URL | 향후 Phase 2 확장의 기반 |

나머지 컬럼(`salary`, `deadline` 등)은 코드에 **주석으로 포함**해두어 이후 활성화하기 쉽게 준비.

---

## 파일 구조 (테스트용)

```
jobkorea/
├── phase1_test_plan.md     # 본 기획서
├── system_architecture.md  # 본 기획 (참조용)
├── .env                    # 환경변수
├── requirements.txt        # 패키지 목록
└── test_crawler.py         # 테스트 크롤러 (단일 파일)
```

> 테스트 단계에서는 `crawler.py`, `parser.py`, `database.py`로 나누지 않고 **단일 파일**로 작성. 작동 확인 후 분리.

---

## 실행 순서

```
1. requirements.txt 패키지 설치
2. test_crawler.py 실행
3. output/test_result.csv 확인 (직접 눈으로 데이터 검토)
4. 문제점 및 개선사항 기록 (아래 체크리스트)
5. 확인 완료 후 → 본 기획(system_architecture.md) 단계로 진행
```

---

## 테스트 체크리스트

크롤링 실행 후 직접 확인할 항목:

### 데이터 품질
- [ ] CSV가 정상적으로 생성되었는가?
- [ ] 1페이지 기준 몇 건이 수집되었는가? (예상: 15~17건)
- [ ] `title`, `company` 값이 정상적으로 들어왔는가?
- [ ] `location` 값이 서울/인천 이외의 지역이 포함되었는가?
- [ ] `detail_url`이 유효한 링크인가? (브라우저에서 직접 확인)

### 크롤링 동작
- [ ] 봇 차단 없이 정상 응답을 받았는가?
- [ ] 예상치 못한 에러가 발생했는가?
- [ ] 속도가 적절한가? (딜레이 2~5초 설정 기준)

### 구조 검증
- [ ] `salary`가 없는 공고 비율이 어느 정도인가?
- [ ] `job_category`에서 복수 직무가 있는 경우가 있는가?
- [ ] 페이지 구조(HTML)가 예상했던 것과 일치하는가?

---

## 성공 기준 (Definition of Done)

- `output/test_result.csv`에 10건 이상 수집됨
- 5개 필수 컬럼이 모두 정상 값으로 채워짐
- 봇 차단 없이 1페이지 완주

성공 시 → `system_architecture.md` 기반의 본 개발(PostgreSQL + 14개 컬럼)로 진행.

---

## 관련 문서

- 본 기획: [system_architecture.md](../architecture/system_architecture.md)
