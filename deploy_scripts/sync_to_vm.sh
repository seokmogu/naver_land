#!/bin/bash
# 로컬 코드를 VM으로 동기화

set -e

echo "🔄 로컬 코드를 VM으로 동기화"
echo "===================================="

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

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

# 백업 생성
print_step "VM의 기존 파일 백업 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="cd ~/naver_land && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz collectors/"

# 주요 Python 파일들 동기화
print_step "Python 파일들 동기화 중"

# collectors 디렉토리의 주요 파일들
FILES_TO_SYNC=(
    "fixed_naver_collector.py"
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

for file in "${FILES_TO_SYNC[@]}"; do
    if [ -f "collectors/$file" ]; then
        print_step "동기화: $file"
        gcloud compute scp "collectors/$file" \
            "$INSTANCE_NAME":~/naver_land/collectors/"$file" \
            --zone="$ZONE" --project="$PROJECT_ID"
    else
        print_warning "$file 파일이 로컬에 없습니다. 건너뜁니다."
    fi
done

# requirements.txt 동기화
print_step "requirements.txt 동기화 중"
if [ -f "requirements.txt" ]; then
    gcloud compute scp "requirements.txt" \
        "$INSTANCE_NAME":~/naver_land/ \
        --zone="$ZONE" --project="$PROJECT_ID"
fi

# deploy_scripts 디렉토리 동기화
print_step "deploy_scripts 디렉토리 동기화 중"
for script in deploy_scripts/*.sh; do
    if [ -f "$script" ]; then
        gcloud compute scp "$script" \
            "$INSTANCE_NAME":~/naver_land/deploy_scripts/ \
            --zone="$ZONE" --project="$PROJECT_ID"
    fi
done

# 실행 권한 설정
print_step "스크립트 실행 권한 설정 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="chmod +x ~/naver_land/deploy_scripts/*.sh ~/naver_land/collectors/*.sh 2>/dev/null || true"

# 패키지 재설치 (requirements.txt 업데이트된 경우)
print_step "패키지 재설치 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="cd ~/naver_land && source venv/bin/activate && pip install -r requirements.txt"

# 테스트 제안
print_success "코드 동기화 완료!"
echo ""
echo "동기화된 코드를 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo "🧪 동기화된 코드 테스트 중..."
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c 'from fixed_naver_collector import NaverRealEstateCollector; print(\"✅ Import 성공\")'"
    
    echo ""
    echo "작은 테스트를 실행하시겠습니까? (y/N):"
    read -r RUN_SMALL_TEST
    
    if [[ "$RUN_SMALL_TEST" =~ ^[Yy]$ ]]; then
        gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
            --command="cd ~/naver_land/collectors && source ../venv/bin/activate && python3 parallel_batch_collect_gangnam.py --max-workers 1"
    fi
else
    echo "나중에 다음 명령어로 테스트할 수 있습니다:"
    echo "./deploy_scripts/remote_commands.sh test"
fi

print_success "VM 코드 동기화 완료! 🎉"