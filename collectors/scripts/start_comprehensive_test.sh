#!/bin/bash

# 네이버 부동산 수집기 종합 테스트 실행 스크립트
# 백그라운드에서 전체 시스템 테스트 및 모니터링

set -e

echo "🚀 네이버 부동산 수집기 종합 테스트 시작"
echo "📅 시작 시간: $(date)"
echo "=" * 60

# collectors 디렉토리로 이동
cd "$(dirname "$0")"

# Python 환경 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    exit 1
fi

# 필수 파이썬 모듈 확인
python3 -c "import psutil" 2>/dev/null || {
    echo "❌ psutil 모듈이 필요합니다: pip install psutil"
    exit 1
}

echo "✅ 환경 확인 완료"
echo ""

# 백그라운드에서 종합 테스트 실행
echo "🔄 백그라운드에서 종합 테스트 실행..."
echo "   📊 웹 모니터링: http://localhost:8888"
echo "   📋 로그 디렉토리: logs/"
echo "   📁 테스트 결과: test_results/"
echo ""

# nohup으로 백그라운드 실행
nohup python3 comprehensive_test.py > comprehensive_test.log 2>&1 &
TEST_PID=$!

echo "✅ 종합 테스트 시작됨 (PID: $TEST_PID)"
echo "📋 실시간 로그: tail -f comprehensive_test.log"
echo "🌐 웹 대시보드: http://localhost:8888 (약 10초 후 접속 가능)"
echo ""
echo "🛑 테스트 중단: kill $TEST_PID"
echo "📊 진행 상황 확인: python3 check_collection_status.py --quick"

# PID 파일 저장
echo $TEST_PID > comprehensive_test.pid

echo ""
echo "🎯 백그라운드 테스트 실행 중..."
echo "   실시간 로그 보기: tail -f comprehensive_test.log"
echo "   상태 확인: python3 check_collection_status.py --realtime"
echo "   웹 모니터링: http://localhost:8888"