#!/bin/bash

# 네이버 부동산 수집기 실행 스크립트
# 최적화된 로그 기반 시스템 사용

set -e  # 에러 발생시 스크립트 중단

echo "🚀 네이버 부동산 수집 시작"
echo "📅 실행 시간: $(date)"
echo "🏗️  최적화된 로그 기반 시스템 사용"

# collectors 디렉토리 이동 제거 (루트에서 실행)

# 로그 디렉토리 생성
mkdir -p logs

# 실행 옵션 설정
COLLECTION_MODE=${COLLECTION_MODE:-"single"}
MAX_WORKERS=${MAX_WORKERS:-2}

echo "⚙️  수집 설정:"
echo "   - 모드: $COLLECTION_MODE"
echo "   - 워커 수: $MAX_WORKERS"

# log_based_collector.py 자체 모니터링 사용 (별도 서버 실행 제거)

# 메인 수집기 실행
echo "🔄 메인 수집 실행..."

case $COLLECTION_MODE in
    "single")
        python3 -m collectors.log_based_collector --max-workers 1
        ;;
    "parallel") 
        python3 -m collectors.log_based_collector --parallel --max-workers $MAX_WORKERS
        ;;
    "unified")
        python3 -m collectors.legacy.unified_collector
        ;;
    *)
        echo "⚠️  알 수 없는 모드: $COLLECTION_MODE"
        echo "사용 가능한 모드: single, parallel, unified"
        exit 1
        ;;
esac

# 수집 완료 후 상태 확인
echo "📋 수집 결과 확인..."
python3 collectors/monitoring/check_collection_status.py --quick

# log_based_collector.py 자체 모니터링 사용 (별도 종료 불필요)

echo "✅ 수집 완료"
echo "📅 완료 시간: $(date)"

# 로그 파일 위치 안내
echo ""
echo "📁 생성된 로그 파일:"
echo "   - 실시간 진행 로그: logs/live_progress.jsonl"
echo "   - 수집 데이터 로그: logs/collection_data.jsonl" 
echo "   - 현재 상태: logs/status.json"
echo ""
echo "🌐 웹 모니터링: http://localhost:$MONITOR_PORT (실행 중이었다면)"
