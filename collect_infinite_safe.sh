#!/bin/bash

# 무한 반복 수집 스크립트 (메모리 관리 포함)
# 강남구 전체 매물을 지속적으로 수집하며 메모리 관리

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 로그 파일 설정
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/collect_infinite_$(date +%Y%m%d).log"

# 수집 간격 설정 (초 단위)
WAIT_BETWEEN_CYCLES=300  # 5분 대기
WAIT_ON_ERROR=600        # 오류 시 10분 대기
MEMORY_CHECK_INTERVAL=5  # 5사이클마다 메모리 체크

# 메모리 임계값 설정 (%)
MEMORY_THRESHOLD=80      # 80% 이상 사용시 정리
SWAP_THRESHOLD=50        # 스왑 50% 이상 사용시 정리

# 카운터 초기화
CYCLE_COUNT=0
ERROR_COUNT=0
MEMORY_CLEAN_COUNT=0

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

log_warning() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING:${NC} $message"
    echo "[$timestamp] WARNING: $message" >> "$LOG_FILE"
}

# 메모리 상태 체크
check_memory() {
    # 메모리 사용률 계산
    local mem_total=$(free -m | awk 'NR==2 {print $2}')
    local mem_used=$(free -m | awk 'NR==2 {print $3}')
    local mem_percent=$((mem_used * 100 / mem_total))
    
    # 스왑 사용률 계산
    local swap_total=$(free -m | awk 'NR==3 {print $2}')
    local swap_used=$(free -m | awk 'NR==3 {print $3}')
    local swap_percent=0
    if [ "$swap_total" -gt 0 ]; then
        swap_percent=$((swap_used * 100 / swap_total))
    fi
    
    echo -e "${PURPLE}[메모리 상태]${NC}"
    echo "  - RAM 사용: ${mem_used}MB / ${mem_total}MB (${mem_percent}%)"
    echo "  - Swap 사용: ${swap_used}MB / ${swap_total}MB (${swap_percent}%)"
    
    # 로그 기록
    echo "[메모리] RAM: ${mem_percent}%, Swap: ${swap_percent}%" >> "$LOG_FILE"
    
    # 임계값 체크
    if [ "$mem_percent" -gt "$MEMORY_THRESHOLD" ] || [ "$swap_percent" -gt "$SWAP_THRESHOLD" ]; then
        return 1  # 메모리 정리 필요
    fi
    return 0  # 정상
}

# 메모리 정리
clean_memory() {
    log_warning "메모리 정리 시작..."
    
    # Python 가비지 컬렉션 강제 실행
    python3 -c "import gc; gc.collect()" 2>/dev/null
    
    # 시스템 캐시 정리 (권한이 있는 경우)
    if [ -w /proc/sys/vm/drop_caches ]; then
        sync
        echo 1 > /proc/sys/vm/drop_caches
        log_info "시스템 캐시 정리 완료"
    fi
    
    # 임시 파일 정리
    if [ -d "/tmp" ]; then
        find /tmp -type f -name "*.tmp" -mtime +1 -delete 2>/dev/null
        find /tmp -type f -name "tmp*" -mtime +1 -delete 2>/dev/null
    fi
    
    MEMORY_CLEAN_COUNT=$((MEMORY_CLEAN_COUNT + 1))
    log_message "메모리 정리 완료 (총 ${MEMORY_CLEAN_COUNT}회 수행)"
    
    # 정리 후 상태 확인
    sleep 2
    check_memory
}

# 시그널 핸들러 설정
cleanup() {
    log_message "수집 종료 시그널 받음. 정리 작업 수행 중..."
    log_message "총 수집 사이클: $CYCLE_COUNT회"
    log_message "총 오류 발생: $ERROR_COUNT회"
    log_message "총 메모리 정리: $MEMORY_CLEAN_COUNT회"
    
    # 마지막 메모리 정리
    clean_memory
    
    exit 0
}

trap cleanup SIGINT SIGTERM

# 시작 메시지
clear
echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}   네이버 부동산 무한 반복 수집 스크립트${NC}"
echo -e "${YELLOW}          (메모리 관리 기능 포함)${NC}"
echo -e "${YELLOW}================================================${NC}"
log_message "무한 반복 수집 시작 (메모리 관리 활성화)"
log_info "수집 간격: ${WAIT_BETWEEN_CYCLES}초"
log_info "오류 시 대기: ${WAIT_ON_ERROR}초"
log_info "메모리 임계값: RAM ${MEMORY_THRESHOLD}%, Swap ${SWAP_THRESHOLD}%"
echo ""

# 초기 메모리 상태 확인
check_memory

# 무한 반복
while true; do
    CYCLE_COUNT=$((CYCLE_COUNT + 1))
    
    echo -e "${YELLOW}----------------------------------------${NC}"
    log_message "수집 사이클 #$CYCLE_COUNT 시작"
    echo -e "${YELLOW}----------------------------------------${NC}"
    
    # 주기적 메모리 체크
    if [ $((CYCLE_COUNT % MEMORY_CHECK_INTERVAL)) -eq 0 ]; then
        log_info "정기 메모리 체크 (${MEMORY_CHECK_INTERVAL}사이클마다)"
        if ! check_memory; then
            clean_memory
        fi
    fi
    
    # 병렬 수집 실행
    START_TIME=$(date +%s)
    
    # timeout 명령어로 최대 실행 시간 제한 (2시간)
    if timeout 7200 python3 collect_all_parallel.py 2>&1 | tee -a "$LOG_FILE"; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        log_message "수집 사이클 #$CYCLE_COUNT 완료 (소요시간: ${DURATION}초)"
        
        # 메모리 상태 확인
        if ! check_memory; then
            log_warning "메모리 사용량 높음. 정리 수행..."
            clean_memory
        fi
        
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
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 124 ]; then
            log_error "수집 사이클 #$CYCLE_COUNT 시간 초과 (2시간)"
        else
            log_error "수집 사이클 #$CYCLE_COUNT 실패 (종료코드: $EXIT_CODE, 오류 횟수: $ERROR_COUNT)"
        fi
        
        # 오류 발생 시 메모리 정리
        log_warning "오류 발생. 메모리 정리 수행..."
        clean_memory
        
        # Python 프로세스 강제 종료
        pkill -f "python3.*collect" 2>/dev/null
        sleep 2
        
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
    echo "  - 메모리 정리: $MEMORY_CLEAN_COUNT회"
    if [ $CYCLE_COUNT -gt 0 ]; then
        echo "  - 성공률: $(( (CYCLE_COUNT - ERROR_COUNT) * 100 / CYCLE_COUNT ))%"
    fi
    echo ""
    
    # 일별 로그 파일 갱신 (자정 넘었을 때)
    CURRENT_DATE=$(date +%Y%m%d)
    if [[ ! "$LOG_FILE" == *"$CURRENT_DATE"* ]]; then
        LOG_FILE="$LOG_DIR/collect_infinite_$CURRENT_DATE.log"
        log_message "새 로그 파일 생성: $LOG_FILE"
        
        # 오래된 로그 파일 정리 (7일 이상)
        find "$LOG_DIR" -name "collect_infinite_*.log" -mtime +7 -delete 2>/dev/null
        log_info "7일 이상 된 로그 파일 정리"
    fi
    
    # 10사이클마다 강제 가비지 컬렉션
    if [ $((CYCLE_COUNT % 10)) -eq 0 ]; then
        log_info "정기 가비지 컬렉션 수행 (10사이클마다)"
        python3 -c "import gc; gc.collect(); print('Python GC 수행 완료')"
    fi
done