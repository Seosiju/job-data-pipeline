# 📁 docs 문서 구조

> 이 폴더는 잡코리아 크롤링 프로젝트의 모든 문서를 관리합니다.
> 이 문서는 `docs/` 저장 규칙의 단일 source of truth입니다.

---

## 폴더 구조

``` 
docs/
├── README.md              ← 지금 보고 있는 파일
├── archive/               과거 계획 / 결과 / 리팩토링 / 레거시 가이드
├── status/                현재 상태 / 세션 handoff
├── architecture/          현재 구조 / selector 근거 / 핵심 모듈 동작
├── plans/                 현재 active 계획
├── reports/               최근 완료 보고서
└── guides/                운영 runbook
```

---

## 분류 원칙

문서를 저장할 때는 "이 문서가 답하려는 질문이 무엇인가?"로 먼저 판단합니다.

| 폴더 | 질문 | 저장 기준 |
|------|------|-----------|
| `archive/` | 이 문서는 지금 판단 기준이 아니라 과거 기록인가? | 완료된 plan/report, refactoring 기록, 더 이상 쓰지 않는 guide |
| `status/` | 지금 무엇이 구현되었고, 다음 세션은 어디서 시작해야 하나? | 현재 상태, 리스크, handoff 같은 압축 문서 |
| `architecture/` | 시스템은 지금 어떻게 구성되어 있고 핵심 모듈은 실제로 어떻게 동작하나? | 현재 구조, 스키마, selector 근거, 핵심 모듈 reference |
| `plans/` | 지금부터 실제로 추진할 active work는 무엇인가? | 착수 전 기획서, 현재 기준으로 살아 있는 계획 |
| `guides/` | 이것을 실제로 어떻게 실행하거나 운영하는가? | 실행법, 설정법, 스케줄링, 운영 절차 |
| `reports/` | 최근 완료된 작업 중 지금도 참고 가치가 있는 결과는 무엇인가? | 완료 보고서, 검증 결과, retrospective |

추가 규칙:

1. 현재 구조의 상세 source of truth는 `architecture/`에 둡니다. `status/`는 구조의 압축 요약과 다음 액션만 다룹니다.
2. 작업 전에 쓰는 문서는 `plans/`, 작업 후 결과 문서는 `reports/`에 둡니다.
3. `plans/`에는 active 문서만 남기고, 완료되거나 오래된 문서는 `archive/`로 이동합니다.
4. 실행 방법은 `guides/`에 두고, 구조 설명 문서에 섞어 넣지 않습니다.
5. `reports/`도 시간이 지나 기본 컨텍스트에서 제외되면 `archive/reports/`로 이동합니다.
6. 에이전트 작업 방식과 검토 흐름은 `AGENTS.md`에 두고, `docs/`에는 두지 않습니다.

## 빠른 분류 기준

새 문서를 어디에 둘지 헷갈리면 아래 순서로 판단합니다.

1. "지금 상태를 빨리 알려주는 문서인가?" -> `status/`
2. "현재 시스템 구조와 설계 원칙을 설명하는가?" -> `architecture/`
3. "아직 해야 할 일을 계획하는가?" -> `plans/`
4. "실행법이나 운영 절차를 설명하는가?" -> `guides/`
5. "최근 완료 결과를 정리하는가?" -> `reports/`
6. "지금 기준이 아니라 과거 기록인가?" -> `archive/`

---

## 📂 폴더별 안내

### `architecture/` — 현재 구조와 근거 문서

시스템의 현재 구조, selector 근거, 핵심 모듈 동작처럼 **현재 구현을 설명하는 source of truth 문서**.

| 문서 | 설명 |
|------|------|
| [system_architecture.md](architecture/system_architecture.md) | 시스템 전체 아키텍처 |
| [jobkorea_search_results_page_structure.md](architecture/jobkorea_search_results_page_structure.md) | 검색 결과 페이지의 메인 목록/페이지네이션 파싱 구조 문서 |
| [jobkorea_jd_detail_page_structure.md](architecture/jobkorea_jd_detail_page_structure.md) | JD 상세 페이지에서 회사 페이지 링크와 보조 회사 정보를 추출하기 위한 파싱 구조 문서 |
| [jobkorea_company_page_structure.md](architecture/jobkorea_company_page_structure.md) | 회사 상세 페이지의 라벨-값 테이블 기반 파싱 구조 문서 |
| [data_validation_behavior.md](architecture/data_validation_behavior.md) | `validators.py`의 실제 검증/정제 동작을 정리한 reference 문서 |

**새 문서 예시**: `database_schema.md`, `api_design.md`, `tech_stack_decision.md`

---

### `plans/` — 단계별 기획서

작업 착수 **전**에 작성하는 active 기획서. 목표, 범위, 작업 목록, 성공 기준을 포함합니다.
완료되거나 오래된 계획은 `archive/plans/`로 이동합니다.

- `Active plan`: 현재도 기준으로 쓰는 계획
- `Transitional snapshot`: 일부 구현이 반영되어 active plan으로 바로 쓰면 안 되는 문서
- `Historical snapshot`: 완료되었거나 현재 구조와 직접 맞지 않는 과거 계획 문서

| 문서 | 설명 |
|------|------|
| [data_pipeline_service_roadmap.md](plans/data_pipeline_service_roadmap.md) | 현재 active plan인 중장기 데이터 파이프라인 + 서비스 확장 로드맵 |
| [phase2_live_timeout_diagnosis_plan.md](plans/phase2_live_timeout_diagnosis_plan.md) | 회사 페이지 live timeout 원인 분리와 fixture/회귀 테스트 보강을 위한 단기 실행 계획 |

**새 문서 예시**: `phase3_plan.md`, `docker_migration_plan.md`

---

### `reports/` — 완료 보고서

작업 완료 **후** 결과를 정리한 문서. 변경 내역, 테스트 결과, 남은 작업 등을 포함합니다.
이 폴더의 문서는 현재 상태 설명서가 아니라 **historical snapshot** 으로 취급해야 합니다.
현재 구조와 동작은 `README.md`, `architecture/system_architecture.md`, 실제 코드 파일을 우선하세요.

| 문서 | 설명 |
|------|------|
| [phase1_correctness_audit_report.md](reports/phase1_correctness_audit_report.md) | Phase 1 검색 결과 파서 정확성 감사 결과와 검증 기록 |
| [phase2_company_page_fix_review.md](reports/phase2_company_page_fix_review.md) | Phase 2 회사 페이지 전환 구현 리뷰와 검증 기록 |
| [phase2_followup_stabilization_report.md](reports/phase2_followup_stabilization_report.md) | Phase 2 후속 안정화 결과와 검증 기록 |
| [phase2_live_smoke_validation_report.md](reports/phase2_live_smoke_validation_report.md) | Phase 2 제한 live run 결과와 회사 페이지 로딩 실패 재현 기록 |

**새 문서 예시**: `phase2_report.md`, `performance_report.md`

---

### `guides/` — 사용법 가이드

시스템 운영, 설정, 도구 사용법 등 **How-to** 문서.

| 문서 | 설명 |
|------|------|
| [scheduling_guide.md](guides/scheduling_guide.md) | 스케줄링(cron/launchd) 설정법 |

**새 문서 예시**: `troubleshooting.md`, `configuration.md`

### `archive/` — 과거 기록

현재 기본 컨텍스트에서 제외되는 문서를 보관합니다.

| 위치 | 설명 |
|------|------|
| [archive/plans/](archive/plans) | historical/transitional 계획 문서 |
| [archive/reports/](archive/reports) | 기본 컨텍스트에서 제외된 과거 결과 문서 |
| [archive/refactoring/](archive/refactoring) | 리팩토링 기록과 before/after 자료 |
| [archive/guides/](archive/guides) | 더 이상 active guide가 아닌 문서 |
| [archive/architecture/](archive/architecture) | 과거 구조/로드맵 문서 |

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
6. `plans/phase2_live_timeout_diagnosis_plan.md`
7. `reports/phase2_company_page_fix_review.md`
8. `reports/phase2_followup_stabilization_report.md`
9. `archive/`는 필요할 때만

---

## ✏️ 새 문서 작성 규칙

1. **폴더 선택**: 위 6개 폴더 중 성격에 맞는 곳에 저장
2. **파일명**: `소문자_스네이크_케이스.md` (예: `phase3_plan.md`)
3. **plans frontmatter**: `docs/plans/` 문서는 YAML frontmatter로 `status`, `type`, `last_reviewed`, `superseded_by`, `related_report`, `source_of_truth`를 관리
4. **문서 상태 표기**: 과거 기록이면 `historical snapshot`, 일부 구현 반영 상태면 `transitional snapshot` 여부를 문서 상단에 명시
5. **작성 후**: 이 README의 해당 폴더 테이블에 항목 추가
