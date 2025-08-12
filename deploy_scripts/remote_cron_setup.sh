#!/bin/bash
# 원격에서 Cron 스케줄링 자동 설정 스크립트

set -e

echo "⏰ 원격 Cron 스케줄링 설정 시작"
echo "==============================="

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

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

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Cron 설정 스크립트 생성
print_step "Cron 스케줄링 스크립트 생성 중"
cat > /tmp/setup_cron_remote.sh << 'EOF'
#!/bin/bash
# VM에서 실행될 Cron 설정 스크립트

set -e

echo "⏰ Cron 스케줄링 설정 시작"

PROJECT_DIR="$HOME/naver_land"
SCRIPT_PATH="$PROJECT_DIR/deploy_scripts/daily_collection.sh"

# 1. 일일 수집 스크립트 생성
echo "📝 일일 수집 스크립트 생성 중..."
cat > "$SCRIPT_PATH" << 'INNER_EOF'
#!/bin/bash
# 일일 네이버 부동산 수집 스크립트

# 로그 파일 설정
LOG_DIR="$HOME/naver_land/logs"
LOG_FILE="$LOG_DIR/daily_collection_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# 로그 시작
echo "$(date): 일일 수집 시작" >> "$LOG_FILE"

# 프로젝트 디렉토리로 이동
cd "$HOME/naver_land"

# 가상환경 활성화
source venv/bin/activate

# 수집 실행 (collectors 디렉토리에서)
cd collectors

# 배치 스케줄러로 수집 실행
echo "$(date): 배치 수집 시작" >> "$LOG_FILE"
python3 batch_collection_scheduler.py >> "$LOG_FILE" 2>&1

# 결과 확인
if [ $? -eq 0 ]; then
    echo "$(date): 수집 성공" >> "$LOG_FILE"
    
    # 선택적: 오래된 로그 파일 정리 (30일 이상)
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    
    # 선택적: 오래된 결과 파일 정리 (7일 이상, 용량 절약)
    find "results" -name "*.json" -mtime +7 -delete 2>/dev/null || true
    
    # 성공 알림 (선택사항)
    echo "$(date): 정리 작업 완료" >> "$LOG_FILE"
else
    echo "$(date): 수집 실패 (종료 코드: $?)" >> "$LOG_FILE"
fi

echo "$(date): 일일 수집 완료" >> "$LOG_FILE"
INNER_EOF

chmod +x "$SCRIPT_PATH"
echo "✅ 일일 수집 스크립트 생성 완료: $SCRIPT_PATH"

# 2. Cron 작업 추가
echo "⏰ Cron 작업 설정 중..."

# 기존 cron 작업 백업
crontab -l > /tmp/cron_backup.txt 2>/dev/null || echo "# Empty crontab" > /tmp/cron_backup.txt

# 기존에 같은 작업이 있는지 확인
if ! crontab -l 2>/dev/null | grep -q "daily_collection.sh"; then
    # 매일 오전 9시에 실행 (한국시간 기준)
    echo "0 9 * * * $SCRIPT_PATH" >> /tmp/cron_backup.txt
    crontab /tmp/cron_backup.txt
    echo "✅ Cron 작업이 추가되었습니다: 매일 오전 9시 실행"
else
    echo "ℹ️ Cron 작업이 이미 존재합니다."
fi

# 3. Cron 서비스 확인 및 시작
echo "🔄 Cron 서비스 확인 중..."
sudo systemctl enable cron
sudo systemctl start cron

# 4. 설정 확인
echo ""
echo "✅ Cron 설정 완료!"
echo "=================="
echo ""
echo "📋 설정된 스케줄:"
crontab -l
echo ""
echo "📁 로그 위치: $LOG_DIR"
echo "📊 결과 위치: $PROJECT_DIR/collectors/results"
echo ""
echo "🧪 수동 실행 테스트:"
echo "$SCRIPT_PATH"

# 정리
rm -f /tmp/cron_backup.txt

echo ""
echo "🎉 Cron 스케줄링 설정 완료!"
EOF

chmod +x /tmp/setup_cron_remote.sh

# 스크립트를 VM에 전송
print_step "Cron 설정 스크립트를 VM에 전송 중"
gcloud compute scp /tmp/setup_cron_remote.sh "$INSTANCE_NAME":~/setup_cron_remote.sh \
    --zone="$ZONE" --project="$PROJECT_ID"

# VM에서 Cron 설정 실행
print_step "VM에서 Cron 스케줄링 설정 실행 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="~/setup_cron_remote.sh && rm ~/setup_cron_remote.sh"

print_success "Cron 스케줄링 설정 완료!"

# 수동 테스트 제안
print_step "테스트 실행 제안"
echo ""
echo "일일 수집 스크립트를 수동으로 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo "🧪 수집 테스트 실행 중... (시간이 걸릴 수 있습니다)"
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="~/naver_land/deploy_scripts/daily_collection.sh"
    print_success "테스트 실행 완료!"
else
    print_warning "나중에 다음 명령어로 테스트할 수 있습니다:"
    echo "gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
    echo "~/naver_land/deploy_scripts/daily_collection.sh"
fi

# 정리
rm -f /tmp/setup_cron_remote.sh

print_success "원격 Cron 설정 완료! 🎉"
echo ""
echo "🎯 이제 매일 오전 9시에 자동으로 네이버 부동산 데이터가 수집됩니다!"