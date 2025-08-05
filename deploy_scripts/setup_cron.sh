#!/bin/bash
# Cron 자동 스케줄링 설정 스크립트

set -e

echo "⏰ Cron 스케줄링 설정 시작"
echo "========================="

PROJECT_DIR="/home/$USER/naver_land"
SCRIPT_PATH="$PROJECT_DIR/deploy_scripts/daily_collection.sh"

# 1. 일일 수집 스크립트 생성
echo "📝 일일 수집 스크립트 생성 중..."
cat > "$SCRIPT_PATH" << 'EOF'
#!/bin/bash
# 일일 네이버 부동산 수집 스크립트

# 로그 파일 설정
LOG_DIR="/home/$USER/naver_land/logs"
LOG_FILE="$LOG_DIR/daily_collection_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# 로그 시작
echo "$(date): 일일 수집 시작" >> "$LOG_FILE"

# 프로젝트 디렉토리로 이동
cd "/home/$USER/naver_land"

# 가상환경 활성화
source venv/bin/activate

# 수집 실행 (collectors 디렉토리에서)
cd collectors

# 성능 최적화: 4개 워커로 실행
python3 parallel_batch_collect_gangnam.py --max-workers 4 >> "$LOG_FILE" 2>&1

# 결과 확인
if [ $? -eq 0 ]; then
    echo "$(date): 수집 성공" >> "$LOG_FILE"
    
    # 선택적: 오래된 로그 파일 정리 (30일 이상)
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    
    # 선택적: 오래된 결과 파일 정리 (7일 이상, 용량 절약)
    find "results" -name "*.json" -mtime +7 -delete 2>/dev/null || true
else
    echo "$(date): 수집 실패" >> "$LOG_FILE"
fi

echo "$(date): 일일 수집 완료" >> "$LOG_FILE"
EOF

chmod +x "$SCRIPT_PATH"

# 2. Cron 작업 추가
echo "⏰ Cron 작업 설정 중..."

# 기존 cron 작업 백업
crontab -l > /tmp/cron_backup.txt 2>/dev/null || echo "# Empty crontab" > /tmp/cron_backup.txt

# 새로운 cron 작업 추가 (기존 작업이 없는 경우에만)
if ! crontab -l 2>/dev/null | grep -q "daily_collection.sh"; then
    # 매일 오전 9시에 실행 (한국시간 기준)
    echo "0 9 * * * $SCRIPT_PATH" >> /tmp/cron_backup.txt
    crontab /tmp/cron_backup.txt
    echo "✅ Cron 작업이 추가되었습니다: 매일 오전 9시 실행"
else
    echo "ℹ️ Cron 작업이 이미 존재합니다."
fi

# 3. Cron 서비스 시작
sudo systemctl enable cron
sudo systemctl start cron

echo "✅ Cron 설정 완료!"
echo ""
echo "설정된 스케줄:"
echo "- 매일 오전 9시에 자동 실행"
echo "- 로그 위치: $LOG_DIR"
echo "- 결과 위치: $PROJECT_DIR/collectors/results"
echo ""
echo "Cron 작업 확인: crontab -l"
echo "수동 실행 테스트: $SCRIPT_PATH"