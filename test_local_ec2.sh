#!/bin/bash
# EC2 환경과 동일한 로컬 테스트 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "========================================"
echo "     EC2 동일 환경 로컬 테스트"
echo "========================================"
echo ""

# Docker 설치 확인
print_step "Docker 설치 확인"
if ! command -v docker &> /dev/null; then
    print_warning "Docker가 설치되어 있지 않습니다."
    echo ""
    echo "🔄 WSL2 네이티브 테스트로 전환합니다..."
    echo ""
    exec ./test_local_native.sh
fi

print_success "Docker 확인됨: $(docker --version)"

# 1. .env 파일 확인
print_step ".env 파일 확인"
if [ ! -f ".env" ]; then
    print_warning ".env 파일이 없습니다."
    echo ""
    echo "Supabase 설정을 입력하세요:"
    read -p "SUPABASE_URL: " SUPABASE_URL
    read -sp "SUPABASE_KEY: " SUPABASE_KEY
    echo ""
    
    cat > .env << EOF
SUPABASE_URL=$SUPABASE_URL
SUPABASE_KEY=$SUPABASE_KEY
EOF
    print_success ".env 파일 생성 완료"
else
    print_success ".env 파일 존재"
fi

# 2. 토큰 캐시 확인
print_step "토큰 캐시 확인"
if [ ! -f "collectors/cached_token.json" ]; then
    print_warning "토큰 캐시가 없습니다."
    echo "Docker 컨테이너 내에서 토큰을 설정해야 합니다."
else
    print_success "토큰 캐시 존재"
fi

# 3. Docker 이미지 빌드
print_step "EC2 테스트 환경 Docker 이미지 빌드"
docker build -f Dockerfile.ec2-test -t naver-collector-ec2-test .
print_success "Docker 이미지 빌드 완료"

# 4. 테스트 옵션 선택
echo ""
echo "테스트 옵션을 선택하세요:"
echo "1) 대화형 모드 (수동 테스트)"
echo "2) 자동 Import 테스트"
echo "3) 자동 수집 테스트 (1개 워커)"
echo "4) 메모리/성능 테스트"
read -p "선택 [1-4] (기본값: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        print_step "대화형 모드로 Docker 컨테이너 시작"
        echo ""
        print_warning "컨테이너 내에서 다음 명령어들을 실행해보세요:"
        echo "  source venv/bin/activate"
        echo "  python3 collectors/setup_deployment.py  # (토큰 설정이 필요한 경우)"
        echo "  python3 -c \"from collectors.fixed_naver_collector import FixedNaverCollector; print('Import 성공')\""
        echo "  cd collectors && python3 cached_token_collector.py"
        echo ""
        docker run -it --rm \
            -v "$(pwd)/collectors/cached_token.json:/home/ubuntu/naver_land/collectors/cached_token.json" \
            -v "$(pwd)/collectors/results:/home/ubuntu/naver_land/collectors/results" \
            naver-collector-ec2-test
        ;;
    
    2)
        print_step "자동 Import 테스트 실행"
        docker run --rm \
            -v "$(pwd)/collectors/cached_token.json:/home/ubuntu/naver_land/collectors/cached_token.json" \
            naver-collector-ec2-test \
            /bin/bash -c "
                source venv/bin/activate && 
                python3 -c \"
from collectors.fixed_naver_collector import FixedNaverCollector
from collectors.supabase_client import SupabaseHelper
print('✅ FixedNaverCollector import 성공')
print('✅ SupabaseHelper import 성공')
print('🎉 모든 핵심 모듈 import 성공!')
\"
            "
        ;;
    
    3)
        print_step "자동 수집 테스트 실행 (1개 워커, 역삼동)"
        docker run --rm \
            -v "$(pwd)/collectors/cached_token.json:/home/ubuntu/naver_land/collectors/cached_token.json" \
            -v "$(pwd)/collectors/results:/home/ubuntu/naver_land/collectors/results" \
            naver-collector-ec2-test \
            /bin/bash -c "
                source venv/bin/activate && 
                cd collectors &&
                python3 parallel_batch_collect_gangnam.py --max-workers 1 --test-mode
            "
        ;;
    
    4)
        print_step "메모리/성능 테스트 실행"
        docker run --rm \
            -v "$(pwd)/collectors/cached_token.json:/home/ubuntu/naver_land/collectors/cached_token.json" \
            naver-collector-ec2-test \
            /bin/bash -c "
                source venv/bin/activate && 
                echo '=== 시스템 정보 ==='
                cat /proc/meminfo | grep -E 'MemTotal|MemAvailable'
                echo ''
                echo '=== CPU 정보 ==='
                nproc
                echo ''
                echo '=== Python 메모리 사용량 테스트 ==='
                python3 -c \"
import psutil
import os
from collectors.fixed_naver_collector import FixedNaverCollector

process = psutil.Process(os.getpid())
print(f'초기 메모리: {process.memory_info().rss / 1024 / 1024:.1f} MB')

# 모듈 로드 후
print(f'모듈 로드 후: {process.memory_info().rss / 1024 / 1024:.1f} MB')
print('✅ 메모리 사용량이 EC2 t2.micro(1GB)에서 실행 가능한 수준입니다')
\"
            "
        ;;
esac

echo ""
print_success "로컬 테스트 완료!"
echo ""
echo "다음 단계:"
echo "  1. 로컬 테스트가 성공하면 EC2 배포 실행:"
echo "     ./deploy_scripts/aws_auto_deploy.sh"
echo ""
echo "  2. EC2에서 동일한 명령어로 테스트:"
echo "     ./deploy_scripts/remote_ec2_commands.sh test"