#!/bin/bash
# AWS EC2로 로컬 코드 동기화

set -e

echo "🔄 로컬 코드를 EC2로 동기화"
echo "===================================="

# EC2 설정
EC2_HOST="52.78.34.225"  # EC2 퍼블릭 IP 또는 도메인
EC2_USER="ubuntu"  # EC2 사용자 (Amazon Linux는 ec2-user, Ubuntu는 ubuntu)
EC2_KEY="/home/hackit/.ssh/naver-land-collector-v2-key.pem"  # EC2 키 파일 경로
REMOTE_PATH="/home/ubuntu/naver_land"  # EC2 내 프로젝트 경로

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# SSH 연결 테스트
print_step "EC2 연결 테스트"
ssh -i "$EC2_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo '✅ EC2 연결 성공'" || {
    echo "❌ EC2 연결 실패. 다음 사항을 확인하세요:"
    echo "  1. EC2_HOST가 올바른지"
    echo "  2. EC2_KEY 파일 경로가 올바른지"
    echo "  3. EC2 보안 그룹에서 SSH(22) 포트가 열려있는지"
    exit 1
}

# 백업 생성
print_step "EC2의 기존 파일 백업 중"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
    "cd $REMOTE_PATH && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz collectors/ 2>/dev/null || true"

# 주요 Python 파일들 동기화
print_step "Python 파일들 동기화 중"

# collectors 디렉토리의 주요 파일들
FILES_TO_SYNC=(
    "fixed_naver_collector.py"
    "fixed_naver_collector_v2_optimized.py"
    "cached_token_collector.py"
    "supabase_client.py"
    "parallel_batch_collect_gangnam.py"
    "batch_collect_gangnam.py"
    "kakao_address_converter.py"
    "smart_boundary_collector.py"
    "debug_supabase_upload.py"
    "test_price_change_deletion.py"
    "test_price_change_deletion_fixed.py"
    "test_seogok_upload.py"
    "verify_db_data.py"
)

# collectors 디렉토리 생성 (없을 경우)
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $REMOTE_PATH/collectors"

for file in "${FILES_TO_SYNC[@]}"; do
    if [ -f "collectors/$file" ]; then
        print_step "동기화: $file"
        scp -i "$EC2_KEY" "collectors/$file" \
            "$EC2_USER@$EC2_HOST:$REMOTE_PATH/collectors/$file"
    else
        print_warning "$file 파일이 로컬에 없습니다. 건너뜁니다."
    fi
done

# requirements.txt 동기화
print_step "requirements.txt 동기화 중"
if [ -f "requirements.txt" ]; then
    scp -i "$EC2_KEY" "requirements.txt" \
        "$EC2_USER@$EC2_HOST:$REMOTE_PATH/"
fi

# deploy_scripts 디렉토리 동기화
print_step "deploy_scripts 디렉토리 동기화 중"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $REMOTE_PATH/deploy_scripts"

for script in deploy_scripts/*.sh; do
    if [ -f "$script" ]; then
        scp -i "$EC2_KEY" "$script" \
            "$EC2_USER@$EC2_HOST:$REMOTE_PATH/deploy_scripts/"
    fi
done

# 실행 권한 설정
print_step "스크립트 실행 권한 설정 중"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
    "chmod +x $REMOTE_PATH/deploy_scripts/*.sh $REMOTE_PATH/collectors/*.sh 2>/dev/null || true"

# Python 가상환경 확인 및 패키지 설치
print_step "Python 가상환경 확인"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "
    cd $REMOTE_PATH
    if [ ! -d 'venv' ]; then
        echo '가상환경 생성 중...'
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"

# 테스트 제안
print_success "코드 동기화 완료!"
echo ""
echo "동기화된 코드를 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo "🧪 동기화된 코드 테스트 중..."
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
        "cd $REMOTE_PATH/collectors && source ../venv/bin/activate && python3 -c 'from fixed_naver_collector import NaverRealEstateCollector; print(\"✅ Import 성공\")'"
    
    echo ""
    echo "작은 테스트를 실행하시겠습니까? (y/N):"
    read -r RUN_SMALL_TEST
    
    if [[ "$RUN_SMALL_TEST" =~ ^[Yy]$ ]]; then
        ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" \
            "cd $REMOTE_PATH/collectors && source ../venv/bin/activate && python3 parallel_batch_collect_gangnam.py --max-workers 1"
    fi
else
    echo "나중에 다음 명령어로 테스트할 수 있습니다:"
    echo "./deploy_scripts/remote_ec2_commands.sh test"
fi

print_success "EC2 코드 동기화 완료! 🎉"