#!/bin/bash

# 무한 반복 수집 스크립트
# 강남구 전체 매물을 지속적으로 수집

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 파일 설정
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/collect_infinite_$(date +%Y%m%d).log"

# 수집 간격 설정 (초 단위)
WAIT_BETWEEN_CYCLES=300  # 5분 대기
WAIT_ON_ERROR=600        # 오류 시 10분 대기

# 카운터 초기화
CYCLE_COUNT=0
ERROR_COUNT=0

# 로그 함수
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp]${NC} $message"
    echo "[$timestamp] $message" >> "$LOG_FILE"
}

log_error() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR:${NC} $message"
    echo "[$timestamp] ERROR: $message" >> "$LOG_FILE"
}

log_info() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp]${NC} $message"
    echo "[$timestamp] $message" >> "$LOG_FILE"
}

# 시그널 핸들러 설정
cleanup() {
    log_message "수집 종료 시그널 받음. 정리 작업 수행 중..."
    log_message "총 수집 사이클: $CYCLE_COUNT회"
    log_message "총 오류 발생: $ERROR_COUNT회"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 시작 메시지
clear
echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}   네이버 부동산 무한 반복 수집 스크립트${NC}"
echo -e "${YELLOW}================================================${NC}"
log_message "무한 반복 수집 시작"
log_info "수집 간격: ${WAIT_BETWEEN_CYCLES}초"
log_info "오류 시 대기: ${WAIT_ON_ERROR}초"
echo ""

# 무한 반복
while true; do
    CYCLE_COUNT=$((CYCLE_COUNT + 1))
    
    echo -e "${YELLOW}----------------------------------------${NC}"
    log_message "수집 사이클 #$CYCLE_COUNT 시작"
    echo -e "${YELLOW}----------------------------------------${NC}"
    
    # 병렬 수집 실행
    START_TIME=$(date +%s)
    
    if python3 collect_all_parallel.py 2>&1 | tee -a "$LOG_FILE"; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        log_message "수집 사이클 #$CYCLE_COUNT 완료 (소요시간: ${DURATION}초)"
        
        # 정상 완료 시 대기
        log_info "다음 사이클까지 ${WAIT_BETWEEN_CYCLES}초 대기..."
        
        # 대기 중 진행률 표시
        for ((i=WAIT_BETWEEN_CYCLES; i>0; i--)); do
            printf "\r대기 중: %3d초 남음" $i
            sleep 1
        done
        printf "\r                        \r"
        
    else
        ERROR_COUNT=$((ERROR_COUNT + 1))
        log_error "수집 사이클 #$CYCLE_COUNT 실패 (오류 횟수: $ERROR_COUNT)"
        
        # 오류 발생 시 더 긴 대기
        log_info "오류 복구 대기: ${WAIT_ON_ERROR}초..."
        
        for ((i=WAIT_ON_ERROR; i>0; i--)); do
            printf "\r복구 대기: %3d초 남음" $i
            sleep 1
        done
        printf "\r                        \r"
    fi
    
    # 상태 요약 출력
    echo ""
    echo -e "${GREEN}[상태 요약]${NC}"
    echo "  - 완료 사이클: $CYCLE_COUNT"
    echo "  - 오류 발생: $ERROR_COUNT"
    echo "  - 성공률: $(( (CYCLE_COUNT - ERROR_COUNT) * 100 / CYCLE_COUNT ))%"
    echo ""
    
    # 일별 로그 파일 갱신 (자정 넘었을 때)
    CURRENT_DATE=$(date +%Y%m%d)
    if [[ ! "$LOG_FILE" == *"$CURRENT_DATE"* ]]; then
        LOG_FILE="$LOG_DIR/collect_infinite_$CURRENT_DATE.log"
        log_message "새 로그 파일 생성: $LOG_FILE"
    fi
done