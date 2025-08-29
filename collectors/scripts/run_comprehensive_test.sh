#!/bin/bash

# 네이버 부동산 수집기 종합 테스트 실행 스크립트
echo "🚀 네이버 부동산 수집기 종합 테스트 시작"
echo "==============================================="

# 현재 디렉토리 확인
if [ ! -f "comprehensive_system_test.py" ]; then
    echo "❌ comprehensive_system_test.py 파일을 찾을 수 없습니다."
    echo "💡 collectors/ 디렉토리에서 실행해주세요."
    exit 1
fi

# Python 환경 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3이 설치되어 있지 않습니다."
    exit 1
fi

echo "🔍 시스템 환경 확인..."
echo "  - Python: $(python3 --version)"
echo "  - 작업 디렉토리: $(pwd)"

# 필요한 디렉토리 생성
echo "📁 테스트 디렉토리 준비..."
mkdir -p test_logs
mkdir -p test_results
mkdir -p logs
mkdir -p results

# 종속성 확인
echo "📦 필요한 패키지 확인..."
python3 -c "
import sys
required_packages = ['requests', 'psutil', 'pytz']
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
        print(f'  ✅ {package}')
    except ImportError:
        print(f'  ❌ {package} (설치 필요)')
        missing_packages.append(package)

if missing_packages:
    print(f'\\n📥 누락된 패키지 설치: pip install {\" \".join(missing_packages)}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "💡 누락된 패키지를 설치하고 다시 시도해주세요."
    exit 1
fi

# 백그라운드 실행 여부 확인
BACKGROUND_MODE=false
if [ "$1" = "--background" ] || [ "$1" = "-b" ]; then
    BACKGROUND_MODE=true
    echo "🔄 백그라운드 모드로 실행됩니다."
fi

echo "🚀 종합 테스트 실행 중..."
echo "  - 로그 모니터링 시스템 검증"
echo "  - 데이터베이스 저장 검증"
echo "  - 변경 이력 관리 시스템 검증"
echo "  - 웹 모니터링 시스템 검증"
echo "  - 전체 시스템 성능 평가"
echo ""

# 시작 시간 기록
start_time=$(date)
echo "⏰ 테스트 시작 시간: $start_time"

if [ "$BACKGROUND_MODE" = true ]; then
    # 백그라운드 실행
    nohup python3 comprehensive_system_test.py > test_logs/comprehensive_test.log 2>&1 &
    TEST_PID=$!
    
    echo "🔄 백그라운드로 실행 중... (PID: $TEST_PID)"
    echo "📋 로그 확인: tail -f test_logs/comprehensive_test.log"
    echo "🌐 웹 모니터: http://localhost:8889 (몇 분 후 접속 가능)"
    echo "🛑 중단하기: kill $TEST_PID"
    echo ""
    echo "📄 테스트 완료 후 결과는 test_results/ 디렉토리에 저장됩니다."
    
    # PID 파일 저장 (나중에 종료할 때 사용)
    echo $TEST_PID > test_logs/test_pid
    
else
    # 포그라운드 실행
    echo "⚠️  주의: 테스트는 5-15분 정도 소요될 수 있습니다."
    echo "🌐 테스트 중 http://localhost:8889 에서 실시간 모니터링 가능"
    echo ""
    
    # 사용자 확인
    read -p "계속하시겠습니까? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 테스트가 취소되었습니다."
        exit 1
    fi
    
    # 테스트 실행
    python3 comprehensive_system_test.py
    
    # 결과 확인
    echo ""
    echo "✅ 테스트 완료!"
    echo "📄 결과 파일:"
    ls -la test_results/*.md test_results/*.json 2>/dev/null || echo "  결과 파일이 생성되지 않았습니다."
fi

end_time=$(date)
echo "⏰ 테스트 종료 시간: $end_time"

echo ""
echo "🎉 종합 테스트 스크립트 완료"
echo "==============================================="