#!/bin/bash
# daily_collection.sh 스크립트 원격 재생성

set -e

echo "🔧 daily_collection.sh 스크립트 재생성"
echo "===================================="

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# daily_collection.sh 스크립트 생성
print_step "daily_collection.sh 스크립트 생성 중"
cat > /tmp/daily_collection.sh << 'EOF'
#!/bin/bash
# 일일 네이버 부동산 수집 스크립트

echo "$(date): 일일 수집 시작"

# 로그 파일 설정
LOG_DIR="$HOME/naver_land/logs"
LOG_FILE="$LOG_DIR/daily_collection_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# 로그 시작
echo "$(date): 일일 수집 시작" >> "$LOG_FILE"
echo "$(date): 일일 수집 시작"

# 프로젝트 디렉토리로 이동
cd "$HOME/naver_land"

# 가상환경 활성화
echo "$(date): 가상환경 활성화 중..." >> "$LOG_FILE"
echo "$(date): 가상환경 활성화 중..."
source venv/bin/activate

# 수집 실행 (collectors 디렉토리에서)
cd collectors

# 성능 최적화: 2개 워커로 실행
echo "$(date): 수집 시작 - 2개 워커" >> "$LOG_FILE"
echo "$(date): 수집 시작 - 2개 워커"
python3 parallel_batch_collect_gangnam.py --max-workers 2 2>&1 | tee -a "$LOG_FILE"

# 결과 확인
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): 수집 성공" >> "$LOG_FILE"
    echo "$(date): 수집 성공"
    
    # 선택적: 오래된 로그 파일 정리 (30일 이상)
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    
    # 선택적: 오래된 결과 파일 정리 (7일 이상, 용량 절약)
    find "results" -name "*.json" -mtime +7 -delete 2>/dev/null || true
    
    echo "$(date): 정리 작업 완료" >> "$LOG_FILE"
    echo "$(date): 정리 작업 완료"
else
    echo "$(date): 수집 실패 (종료 코드: $EXIT_CODE)" >> "$LOG_FILE"
    echo "$(date): 수집 실패 (종료 코드: $EXIT_CODE)"
fi

echo "$(date): 일일 수집 완료" >> "$LOG_FILE"
echo "$(date): 일일 수집 완료"
EOF

chmod +x /tmp/daily_collection.sh

# VM에 스크립트 전송
print_step "daily_collection.sh를 VM에 전송 중"
gcloud compute scp /tmp/daily_collection.sh "$INSTANCE_NAME":~/naver_land/deploy_scripts/daily_collection.sh \
    --zone="$ZONE" --project="$PROJECT_ID"

# VM에서 실행 권한 설정
print_step "VM에서 실행 권한 설정 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="chmod +x ~/naver_land/deploy_scripts/daily_collection.sh"

print_success "daily_collection.sh 스크립트 재생성 완료!"

# 테스트 실행 제안
print_step "테스트 실행"
echo ""
echo "스크립트를 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo "🧪 daily_collection.sh 테스트 실행 중..."
    echo "VM에서 실행되는 로그를 확인하세요."
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="~/naver_land/deploy_scripts/daily_collection.sh"
else
    echo "나중에 다음 명령어로 테스트할 수 있습니다:"
    echo "gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
    echo "~/naver_land/deploy_scripts/daily_collection.sh"
fi

# 정리
rm -f /tmp/daily_collection.sh

print_success "스크립트 재생성 완료! 🎉"