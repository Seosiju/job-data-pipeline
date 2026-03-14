# Archive

이 폴더는 현재 기본 컨텍스트에서 제외되는 historical reference 문서를 보관합니다.

원칙:

- `archive/plans/`: 완료되었거나 더 이상 active가 아닌 과거 계획 문서
- `archive/reports/`: 현재 판단의 직접 기준으로 쓰지 않는 과거 결과 문서
- `archive/refactoring/`: 구조 개선 기록과 before/after 자료
- `archive/guides/`: 더 이상 운영 runbook으로 쓰지 않는 문서
- `archive/architecture/`: historical snapshot 성격의 과거 구조/로드맵 문서

사용 규칙:

1. 새 세션 시작 시 기본적으로 `archive/`는 읽지 않는다.
2. 과거 결정 배경, 구현 근거, 회고가 필요할 때만 연다.
3. active 문서와 historical 문서가 충돌하면 active 문서를 우선한다.
