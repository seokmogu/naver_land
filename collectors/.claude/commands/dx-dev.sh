#!/bin/bash
# DX Dev: 개발 워크플로우 최적화

echo "⚡ 개발 워크플로우 시작"
echo "====================="

# 옵션 파싱
COMMAND="${1:-help}"

case $COMMAND in
    "start")
        echo "🚀 개발 세션 시작..."
        
        # 환경 체크
        python test_setup.py
        
        # Git 상태 확인
        echo ""
        echo "📊 Git 상태:"
        git status --short
        
        # 최근 작업 표시
        echo ""
        echo "📝 최근 커밋:"
        git log --oneline -3
        
        # 다음 단계 제안
        echo ""
        echo "💡 추천 작업:"
        if [ $(git status --porcelain | wc -l) -gt 0 ]; then
            echo "  1. git add . && git commit -m 'WIP: 현재 작업 저장'"
        fi
        echo "  2. python enhanced_data_collector.py (수집기 실행)"
        echo "  3. ./dx-dev.sh monitor (모니터링 시작)"
        ;;
        
    "monitor")
        echo "📊 실시간 모니터링 시작..."
        
        # 로그 파일 모니터링
        if [ -d "logs" ]; then
            echo "📋 최근 로그:"
            find logs -name "*.log" -type f -exec tail -3 {} \; 2>/dev/null || echo "로그 파일 없음"
        fi
        
        # 결과 파일 모니터링  
        if [ -d "results" ]; then
            echo ""
            echo "📊 최근 결과:"
            ls -lt results/ | head -5 2>/dev/null || echo "결과 파일 없음"
        fi
        
        # 프로세스 확인
        echo ""
        echo "⚙️ 실행 중인 프로세스:"
        ps aux | grep -E "(python|collector)" | grep -v grep || echo "실행 중인 수집기 없음"
        ;;
        
    "test")
        echo "🧪 빠른 테스트 실행..."
        
        # 환경 테스트
        python test_setup.py
        
        # 핵심 모듈 테스트
        echo ""
        echo "🔧 핵심 모듈 테스트:"
        python -c "
try:
    from core.collector import *
    print('✅ Core collector 모듈')
except Exception as e:
    print(f'❌ Core collector 모듈: {e}')

try:
    import enhanced_data_collector
    print('✅ Enhanced collector 모듈')
except Exception as e:
    print(f'❌ Enhanced collector 모듈: {e}')
" 2>/dev/null
        ;;
        
    "commit")
        echo "💾 스마트 커밋..."
        
        # 변경된 파일 표시
        echo "📁 변경된 파일:"
        git status --short
        
        # 자동 정리
        echo ""
        echo "🧹 자동 정리 중..."
        find . -name "*.pyc" -delete 2>/dev/null || true
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # 커밋 제안
        echo ""
        echo "💡 커밋 메시지 제안:"
        
        # 파일 변경 분석
        if git status --porcelain | grep -q "enhanced_data_collector.py"; then
            echo "  '🔧 Enhanced collector 개선'"
        fi
        
        if git status --porcelain | grep -q "core/"; then
            echo "  '⚙️ Core 모듈 업데이트'"
        fi
        
        if git status --porcelain | grep -q "config/"; then
            echo "  '🔧 설정 파일 업데이트'"
        fi
        
        echo "  '🚀 개발 진행'"
        echo ""
        echo "실행: git add . && git commit -m '메시지'"
        ;;
        
    "clean")
        echo "🧹 개발 환경 정리..."
        
        # 임시 파일 정리
        find . -name "*.pyc" -delete 2>/dev/null || true
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.log" -size +10M -delete 2>/dev/null || true
        
        # 오래된 결과 파일 아카이브
        if [ -d "results" ]; then
            find results -name "*.json" -mtime +7 -exec mv {} archived/ \; 2>/dev/null || true
        fi
        
        echo "✅ 정리 완료"
        ;;
        
    "help"|*)
        echo "🛠️ DX Dev 명령어:"
        echo ""
        echo "  dx-dev start   : 개발 세션 시작"  
        echo "  dx-dev monitor : 실시간 모니터링"
        echo "  dx-dev test    : 빠른 환경 테스트"
        echo "  dx-dev commit  : 스마트 커밋"
        echo "  dx-dev clean   : 개발 환경 정리"
        echo ""
        echo "💡 일반적인 워크플로우:"
        echo "  1. dx-dev start    (세션 시작)"
        echo "  2. 코드 작업"
        echo "  3. dx-dev test     (테스트)"
        echo "  4. dx-dev commit   (커밋)"
        ;;
esac