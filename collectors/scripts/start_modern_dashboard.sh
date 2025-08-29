#!/bin/bash

# 현대적 실시간 모니터링 대시보드 시작 스크립트

echo "🚀 현대적 실시간 모니터링 대시보드 시작"
echo "=================================================="

# 필요한 패키지 설치 확인
echo "📦 필수 패키지 확인 중..."

# psutil 설치 확인
python3 -c "import psutil" 2>/dev/null || {
    echo "⚠️  psutil이 설치되어 있지 않습니다. 설치하는 중..."
    pip3 install psutil
}

# websockets 설치 확인 (향후 WebSocket 지원용)
python3 -c "import websockets" 2>/dev/null || {
    echo "⚠️  websockets이 설치되어 있지 않습니다. 설치하는 중..."
    pip3 install websockets
}

echo "✅ 패키지 설치 완료"

# 로그 디렉토리 확인
if [ ! -d "logs" ]; then
    echo "📁 logs 디렉토리 생성 중..."
    mkdir -p logs
fi

if [ ! -d "results" ]; then
    echo "📁 results 디렉토리 생성 중..."
    mkdir -p results
fi

# 포트 설정 (기본값: 8888)
PORT=${1:-8888}

# 서버 시작
echo ""
echo "🌐 대시보드 시작 중..."
echo "   - 포트: $PORT"
echo "   - 현대적 UI: http://localhost:$PORT/modern"
echo "   - 레거시 UI: http://localhost:$PORT/"
echo "   - API 문서: http://localhost:$PORT/api/"
echo ""
echo "📊 특징:"
echo "   ✅ 5초 실시간 업데이트"
echo "   ✅ 반응형 모바일 디자인"  
echo "   ✅ 접근성 (WCAG 2.1 AA)"
echo "   ✅ 필터링 및 검색"
echo "   ✅ 시스템 리소스 모니터링"
echo "   ✅ API 압축 및 캐싱"
echo ""

# Python 서버 실행
exec python3 modern_monitor_server.py --port $PORT --cache-ttl 5