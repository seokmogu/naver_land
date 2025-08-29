#!/bin/bash
# AWS EC2로 최적화된 코드 동기화 스크립트

set -e

echo "🔄 최적화된 로그 기반 시스템을 EC2로 동기화"
echo "=============================================="

# EC2 설정
EC2_HOST="52.78.34.225"  # EC2 퍼블릭 IP 또는 도메인
EC2_USER="ubuntu"  # EC2 사용자 (Amazon Linux는 ec2-user, Ubuntu는 ubuntu)
EC2_KEY="/home/hackit/.ssh/naver-land-collector-v2-key.pem"  # EC2 키 파일 경로
REMOTE_PATH="/home/ubuntu/naver_land"  # EC2 내 프로젝트 경로

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# SSH 연결 테스트
print_step "EC2 연결 테스트"
ssh -i "$EC2_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo '✅ EC2 연결 성공'" || {
    print_error "EC2 연결 실패. 다음 사항을 확인하세요:"
    echo "  1. EC2_HOST가 올바른지"
    echo "  2. EC2_KEY 파일 경로가 올바른지"
    echo "  3. EC2 보안 그룹에서 SSH(22) 포트가 열려있는지"
    exit 1
}

# 백업 생성
print_step "EC2의 기존 파일 백업 중"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
    "cd $REMOTE_PATH && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz collectors/ 2>/dev/null || true"

# 최적화된 핵심 파일들 동기화
print_step "최적화된 핵심 시스템 파일들 동기화"

# 핵심 수집 시스템
CORE_FILES=(
    "log_based_collector.py"          # 메인 수집기 (최신)
    "log_based_logger.py"             # 실시간 JSON 로깅 시스템
    "fixed_naver_collector_v2_optimized.py"  # 네이버 API 엔진
    "unified_collector.py"            # 통합 수집기
)

# 모니터링 시스템
MONITORING_FILES=(
    "simple_monitor.py"               # 웹 대시보드
    "check_collection_status.py"      # CLI 상태 도구
    "live_monitor.py"                 # 라이브 모니터링
)

# 인프라 지원
INFRASTRUCTURE_FILES=(
    "playwright_token_collector.py"   # JWT 토큰 수집기
    "cached_token_collector.py"       # 캐시된 토큰 수집기
    "supabase_client.py"              # DB 클라이언트
    "kakao_address_converter.py"      # 주소 변환
    "json_to_supabase.py"             # JSON → DB 변환
    "enhanced_logger.py"              # 고급 로깅
    "progress_logger.py"              # 진행 상황 로거
    "integrated_logger.py"            # 통합 로깅
)

# collectors 디렉토리 생성
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $REMOTE_PATH/collectors/logs"

# 파일별 동기화
sync_files() {
    local files=("$@")
    for file in "${files[@]}"; do
        if [ -f "collectors/$file" ]; then
            print_step "동기화: $file"
            scp -i "$EC2_KEY" "collectors/$file" \
                "$EC2_USER@$EC2_HOST:$REMOTE_PATH/collectors/$file"
        else
            print_warning "$file 파일이 로컬에 없습니다. 건너뜁니다."
        fi
    done
}

print_step "핵심 수집 시스템 동기화"
sync_files "${CORE_FILES[@]}"

print_step "모니터링 시스템 동기화"
sync_files "${MONITORING_FILES[@]}"

print_step "인프라 지원 모듈 동기화"
sync_files "${INFRASTRUCTURE_FILES[@]}"

# 설정 파일들 동기화
print_step "설정 및 의존성 파일 동기화"
if [ -f "requirements.txt" ]; then
    scp -i "$EC2_KEY" "requirements.txt" \
        "$EC2_USER@$EC2_HOST:$REMOTE_PATH/"
fi

# 업데이트된 run.sh 동기화
if [ -f "run.sh" ]; then
    print_step "업데이트된 run.sh 동기화"
    scp -i "$EC2_KEY" "run.sh" \
        "$EC2_USER@$EC2_HOST:$REMOTE_PATH/"
fi

# deploy_scripts 디렉토리 동기화
print_step "배포 스크립트 동기화"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $REMOTE_PATH/deploy_scripts"

for script in deploy_scripts/*.sh; do
    if [ -f "$script" ]; then
        scp -i "$EC2_KEY" "$script" \
            "$EC2_USER@$EC2_HOST:$REMOTE_PATH/deploy_scripts/"
    fi
done

# 실행 권한 설정
print_step "스크립트 실행 권한 설정"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
    "chmod +x $REMOTE_PATH/deploy_scripts/*.sh $REMOTE_PATH/run.sh $REMOTE_PATH/collectors/*.sh 2>/dev/null || true"

# Python 가상환경 설정 및 패키지 업데이트
print_step "Python 환경 설정 및 패키지 업데이트"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "
    cd $REMOTE_PATH
    if [ ! -d 'venv' ]; then
        echo '🏗️  가상환경 생성 중...'
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Playwright 브라우저 설치 (토큰 수집용)
    playwright install chromium 2>/dev/null || echo 'Playwright 브라우저 설치는 나중에 수행하세요.'
"

# 최적화된 시스템 검증
print_step "최적화된 시스템 검증"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
    "cd $REMOTE_PATH/collectors && source ../venv/bin/activate && python3 -c '
import sys
try:
    from log_based_collector import LogBasedNaverCollector
    print(\"✅ 메인 수집기 import 성공\")
    
    from log_based_logger import LogBasedProgressTracker
    print(\"✅ 로깅 시스템 import 성공\")
    
    from simple_monitor import *
    print(\"✅ 모니터링 시스템 import 성공\")
    
    print(\"🎉 최적화된 시스템 검증 완료!\")
except Exception as e:
    print(f\"❌ 검증 실패: {e}\")
    sys.exit(1)
'"

print_success "최적화된 코드 동기화 완료!"

# 실행 안내
echo ""
echo "🚀 EC2에서 실행 방법:"
echo "   1. SSH 접속: ssh -i \"$EC2_KEY\" $EC2_USER@$EC2_HOST"
echo "   2. 프로젝트 이동: cd $REMOTE_PATH"
echo "   3. 수집 실행: ./run.sh"
echo ""
echo "📊 모니터링 접근:"
echo "   - 웹 대시보드: http://$EC2_HOST:8000"
echo "   - CLI 상태 확인: cd collectors && python3 check_collection_status.py --quick"
echo ""

# 테스트 실행 옵션
echo "최적화된 시스템을 바로 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    print_step "최적화된 시스템 테스트 실행"
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
        "cd $REMOTE_PATH && COLLECTION_MODE=single ./run.sh"
else
    print_success "나중에 './run.sh'로 실행하세요!"
fi

print_success "최적화된 로그 기반 시스템 배포 완료! 🎉"