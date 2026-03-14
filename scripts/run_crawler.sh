#!/bin/bash
# ===========================================
# JobKorea Crawler 실행 스크립트
# ===========================================
# 스케줄링용 스크립트 (cron, systemd 등)
#
# 사용법:
#   chmod +x scripts/run_crawler.sh
#   ./scripts/run_crawler.sh
#
# cron 예시 (매일 오전 9시):
#   0 9 * * * /path/to/jobkorea/scripts/run_crawler.sh
#
# ===========================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 프로젝트 루트로 이동
cd "$PROJECT_ROOT"

# 가상환경 활성화 (있는 경우)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 환경변수 로드
if [ -f ".env" ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# 날짜/시간 로그
echo "=========================================="
echo "JobKorea Crawler 실행"
echo "시작 시각: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 크롤러 실행
python main.py

# 실행 결과
EXIT_CODE=$?
echo "=========================================="
echo "종료 시각: $(date '+%Y-%m-%d %H:%M:%S')"
echo "종료 코드: $EXIT_CODE"
echo "=========================================="

exit $EXIT_CODE
