# 📁 docs 문서 구조

> 이 폴더는 잡코리아 크롤링 프로젝트의 모든 문서를 관리합니다.
> 이 문서는 `docs/` 저장 규칙의 단일 source of truth입니다.

---

## 폴더 구조

```
docs/
├── README.md              ← 지금 보고 있는 파일
├── status/                현재 상태 / 세션 handoff
├── architecture/          설계 및 로드맵
├── plans/                 단계별 기획서
├── reports/               완료 보고서
├── refactoring/           리팩토링 기록
└── guides/                사용법 가이드
```

---

## 분류 원칙

문서를 저장할 때는 "이 문서가 답하려는 질문이 무엇인가?"로 먼저 판단합니다.

| 폴더 | 질문 | 저장 기준 |
|------|------|-----------|
| `status/` | 지금 무엇이 구현되었고, 다음 세션은 어디서 시작해야 하나? | 현재 상태, 리스크, handoff 같은 압축 문서 |
| `architecture/` | 시스템은 지금 어떻게 구성되어 있고 어떤 원칙으로 설계되었나? | 현재 구조, 스키마, 기술 선택, 장기 방향 |
| `plans/` | 아직 시작하지 않았거나 진행 중인 작업을 어떻게 추진할 것인가? | 착수 전 기획서, 단계별 실행 계획 |
| `guides/` | 이것을 실제로 어떻게 실행하거나 운영하는가? | 실행법, 설정법, 스케줄링, 문제 해결 |
| `refactoring/` | 구조 변경을 어떻게 했고 무엇이 달라졌는가? | Before/After, 구조도, 복잡도 변화 |
| `reports/` | 작업이 끝난 뒤 어떤 결과가 나왔는가? | 완료 보고서, 검증 결과, retrospective |

추가 규칙:

1. 현재 구조의 상세 source of truth는 `architecture/`에 둡니다. `status/`는 구조의 압축 요약과 다음 액션만 다룹니다.
2. 작업 전에 쓰는 문서는 `plans/`, 작업 후 결과 문서는 `reports/`에 둡니다.
3. `reports/`와 오래된 `plans/`는 현재 source of truth가 아닐 수 있으므로 `historical snapshot` 또는 `transitional snapshot` 여부를 명시합니다.
4. 실행 방법은 `guides/`에 두고, 구조 설명 문서에 섞어 넣지 않습니다.
5. 리팩토링 설명은 가능하면 `refactoring/`에 분리하고, 현재 구조 자체는 `architecture/`에 남깁니다.

## 빠른 분류 기준

새 문서를 어디에 둘지 헷갈리면 아래 순서로 판단합니다.

1. "지금 상태를 빨리 알려주는 문서인가?" -> `status/`
2. "현재 시스템 구조와 설계 원칙을 설명하는가?" -> `architecture/`
3. "아직 해야 할 일을 계획하는가?" -> `plans/`
4. "실행법이나 운영 절차를 설명하는가?" -> `guides/`
5. "리팩토링 변경 자체를 설명하는가?" -> `refactoring/`
6. "끝난 작업을 정리하는가?" -> `reports/`

---

## 📂 폴더별 안내

### `architecture/` — 설계 및 로드맵

시스템의 전체 구조, 기술 스택 선정, 장기 로드맵 등 **프로젝트 방향을 결정하는 문서**.

| 문서 | 설명 |
|------|------|
| [system_architecture.md](architecture/system_architecture.md) | 시스템 전체 아키텍처 |
| [jobkorea_search_results_page_structure.md](architecture/jobkorea_search_results_page_structure.md) | 검색 결과 페이지의 메인 목록/페이지네이션 파싱 구조 문서 |
| [jobkorea_jd_detail_page_structure.md](architecture/jobkorea_jd_detail_page_structure.md) | JD 상세 페이지에서 회사 페이지 링크와 보조 회사 정보를 추출하기 위한 파싱 구조 문서 |
| [jobkorea_company_page_structure.md](architecture/jobkorea_company_page_structure.md) | 회사 상세 페이지의 라벨-값 테이블 기반 파싱 구조 문서 |
| [development_roadmap.md](architecture/development_roadmap.md) | 초기 개발 로드맵 (historical snapshot) |

**새 문서 예시**: `database_schema.md`, `api_design.md`, `tech_stack_decision.md`

---

### `plans/` — 단계별 기획서

작업 착수 **전**에 작성하는 기획서. 목표, 범위, 작업 목록, 성공 기준을 포함.
이미 일부가 구현된 상태로 남아 있으면 문서 상단에 `transitional snapshot` 성격을 명시합니다.

| 문서 | 설명 |
|------|------|
| [phase1_test_plan.md](plans/phase1_test_plan.md) | Phase 1 테스트 기획서 |
| [phase1_correctness_audit_plan.md](plans/phase1_correctness_audit_plan.md) | Phase 1 검색 결과 파서 정확성 감사를 위한 handoff 실행 문서 |
| [phase2_implementation_plan.md](plans/phase2_implementation_plan.md) | Phase 2 구현 기획서 |
| [phase2_company_page_fix_plan.md](plans/phase2_company_page_fix_plan.md) | Phase 2를 JD 페이지 직접 파싱에서 회사 페이지 추적으로 전환하는 수정 기획서 |
| [next_phase_execution_plan.md](plans/next_phase_execution_plan.md) | 중간 배치 실행 기획서 (일부 구현 완료된 transitional snapshot) |
| [data_pipeline_service_roadmap.md](plans/data_pipeline_service_roadmap.md) | 중장기 데이터 파이프라인 + 서비스 확장 로드맵 |

**새 문서 예시**: `phase3_plan.md`, `docker_migration_plan.md`

---

### `reports/` — 완료 보고서

작업 완료 **후** 결과를 정리한 문서. 변경 내역, 테스트 결과, 남은 작업 등을 포함합니다.
이 폴더의 문서는 현재 상태 설명서가 아니라 **historical snapshot** 으로 취급해야 합니다.
현재 구조와 동작은 `README.md`, `architecture/system_architecture.md`, 실제 코드 파일을 우선하세요.

| 문서 | 설명 |
|------|------|
| [phase1_report.md](reports/phase1_report.md) | Phase 1 완료 보고서 |
| [phase1_maintenance_report.md](reports/phase1_maintenance_report.md) | Phase 1 보수 작업 보고서 |
| [phase1_correctness_audit_report.md](reports/phase1_correctness_audit_report.md) | Phase 1 검색 결과 파서 정확성 감사 결과와 검증 기록 |
| [phase2_company_page_fix_review.md](reports/phase2_company_page_fix_review.md) | Phase 2 회사 페이지 전환 구현 리뷰와 검증 기록 |
| [data_validation_summary.md](reports/data_validation_summary.md) | 데이터 검증 로직 구현 요약 |

**새 문서 예시**: `phase2_report.md`, `performance_report.md`

---

### `refactoring/` — 리팩토링 기록

코드 리팩토링의 Before/After, 복잡도 변화, 구조도 등을 기록.

| 문서 | 설명 |
|------|------|
| [REFACTORING_COMPLETE.md](refactoring/REFACTORING_COMPLETE.md) | parser.py 리팩토링 완료 보고 |
| [REFACTORING_SUMMARY.txt](refactoring/REFACTORING_SUMMARY.txt) | parser.py 리팩토링 빠른 참조 |
| [parser_refactoring_summary.md](refactoring/parser_refactoring_summary.md) | 리팩토링 요약 |
| [refactoring_example.md](refactoring/refactoring_example.md) | Before/After 코드 비교 |
| [refactoring_structure.md](refactoring/refactoring_structure.md) | 리팩토링 후 함수 구조도 |

**새 문서 예시**: `database_refactoring.md`, `crawler_refactoring.md`

---

### `guides/` — 사용법 가이드

시스템 운영, 설정, 도구 사용법 등 **How-to** 문서.

| 문서 | 설명 |
|------|------|
| [scheduling_guide.md](guides/scheduling_guide.md) | 스케줄링(cron/launchd) 설정법 |
| [validators_guide.md](guides/validators_guide.md) | 데이터 검증 로직 사용법 |
| [agent_guide.md](guides/agent_guide.md) | Claude Code 에이전트 가이드 |
| [review_workflow.md](guides/review_workflow.md) | 내부 리뷰/검토 워크플로우 메모 |

**새 문서 예시**: `troubleshooting.md`, `configuration.md`

### `status/` — 현재 상태 / handoff

새 세션이 빠르게 맥락을 잡기 위한 압축 문서.

| 문서 | 설명 |
|------|------|
| [current_status.md](status/current_status.md) | 현재 구현 상태, 리스크, 다음 우선순위 |
| [session_handoff.md](status/session_handoff.md) | 최근 세션 요약과 다음 액션 |

---

## 권장 읽기 순서

새 세션에서 문맥 파악이 필요하면 아래 순서로 읽습니다.

1. `README.md`
2. `architecture/system_architecture.md`
3. `plans/data_pipeline_service_roadmap.md`
4. `status/current_status.md`
5. `status/session_handoff.md`
6. `reports/phase2_company_page_fix_review.md`

---

## ✏️ 새 문서 작성 규칙

1. **폴더 선택**: 위 6개 폴더 중 성격에 맞는 곳에 저장
2. **파일명**: `소문자_스네이크_케이스.md` (예: `phase3_plan.md`)
3. **문서 상태 표기**: 과거 기록이면 `historical snapshot`, 일부 구현 반영 상태면 `transitional snapshot` 여부를 문서 상단에 명시
4. **작성 후**: 이 README의 해당 폴더 테이블에 항목 추가
