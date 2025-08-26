#!/bin/bash
# Docker 내에서 EC2 환경 테스트 설정

set -e

echo "🐳 EC2 동일 환경 테스트 설정"
echo "================================="

# 가상환경 활성화
source venv/bin/activate

echo "✅ Python 가상환경 활성화됨"
echo "Python 버전: $(python3 --version)"
echo "pip 버전: $(pip --version)"

# 필수 패키지 확인
echo ""
echo "📦 설치된 패키지 확인:"
pip list | grep -E "(requests|supabase|playwright)" || echo "일부 패키지가 설치되지 않았을 수 있습니다"

# 디렉토리 구조 확인
echo ""
echo "📁 프로젝트 구조:"
ls -la

echo ""
echo "📁 collectors 디렉토리:"
ls -la collectors/

# 환경 변수 파일 확인
echo ""
echo "🔑 환경 설정 확인:"
if [ -f ".env" ]; then
    echo "✅ .env 파일 존재"
    echo "설정된 환경 변수:"
    cat .env | grep -E "SUPABASE|KAKAO" | sed 's/=.*/=<hidden>/' || echo "환경 변수가 설정되지 않았습니다"
else
    echo "⚠️ .env 파일이 없습니다"
    echo "다음 명령어로 설정하세요:"
    echo "  python3 collectors/setup_deployment.py"
fi

echo ""
echo "🎯 테스트 시나리오:"
echo "1. Import 테스트:"
echo "   python3 -c \"from collectors.fixed_naver_collector import FixedNaverCollector; print('✅ Import 성공')\""
echo ""
echo "2. 토큰 캐시 확인:"
echo "   python3 -c \"import json; print(json.load(open('collectors/cached_token.json')))\" 2>/dev/null || echo '토큰 캐시 없음'"
echo ""
echo "3. 간단한 수집 테스트:"
echo "   cd collectors && python3 cached_token_collector.py"
echo ""
echo "4. 배치 수집 테스트:"
echo "   cd collectors && python3 parallel_batch_collect_gangnam.py --max-workers 1"

echo ""
echo "🔧 문제 해결:"
echo "- 토큰 에러: python3 collectors/setup_deployment.py"
echo "- 패키지 에러: pip install -r requirements.txt"
echo "- 권한 에러: chmod +x deploy_scripts/*.sh"

echo ""
echo "✨ 준비 완료! 위 명령어들을 실행해보세요."