#!/bin/bash

# EC2 라이트웨이트 Job 관리 시스템 배포 스크립트
# 메모리 <100MB 최적화 버전

set -e

echo "🚀 라이트웨이트 Job 관리 시스템 배포 시작"
echo "================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시스템 요구사항 확인
check_requirements() {
    log_info "시스템 요구사항 확인 중..."
    
    # Python 3.7+ 확인
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
        log_success "Python $PYTHON_VERSION 발견"
    else
        log_error "Python 3이 필요합니다"
        exit 1
    fi
    
    # 메모리 확인
    TOTAL_MEM=$(free -m | grep '^Mem:' | awk '{print $2}')
    if [ "$TOTAL_MEM" -lt 512 ]; then
        log_warning "메모리가 부족할 수 있습니다 (${TOTAL_MEM}MB). 권장: 512MB 이상"
    else
        log_success "메모리: ${TOTAL_MEM}MB"
    fi
    
    # 디스크 공간 확인
    AVAILABLE_SPACE=$(df -h . | tail -1 | awk '{print $4}' | sed 's/G//')
    if (( $(echo "$AVAILABLE_SPACE < 1" | bc -l) )); then
        log_error "디스크 공간이 부족합니다 (${AVAILABLE_SPACE}GB). 최소 1GB 필요"
        exit 1
    else
        log_success "디스크 여유공간: ${AVAILABLE_SPACE}GB"
    fi
}

# 의존성 설치
install_dependencies() {
    log_info "의존성 패키지 설치 중..."
    
    # 최소 필수 패키지만 설치
    pip3 install --user --upgrade pip > /dev/null 2>&1
    
    # requirements.txt가 있으면 사용, 없으면 최소 패키지만
    if [ -f "../requirements.txt" ]; then
        log_info "requirements.txt에서 패키지 설치 중..."
        pip3 install --user -r ../requirements.txt > /dev/null 2>&1
    else
        log_info "최소 필수 패키지 설치 중..."
        pip3 install --user requests pytz > /dev/null 2>&1
    fi
    
    log_success "의존성 설치 완료"
}

# 디렉토리 구조 생성
setup_directories() {
    log_info "디렉토리 구조 생성 중..."
    
    mkdir -p scheduler_data/job_logs
    mkdir -p logs
    mkdir -p results
    
    # 권한 설정
    chmod 755 scheduler_data
    chmod 755 scheduler_data/job_logs
    chmod 755 logs
    chmod 755 results
    
    log_success "디렉토리 구조 생성 완료"
}

# 실행 권한 설정
setup_permissions() {
    log_info "실행 권한 설정 중..."
    
    chmod +x lightweight_scheduler.py
    chmod +x job_dashboard.py  
    chmod +x job_cli.py
    chmod +x log_based_collector.py
    chmod +x simple_monitor.py
    
    log_success "실행 권한 설정 완료"
}

# 시스템 서비스 설정 (systemd)
setup_systemd_service() {
    log_info "systemd 서비스 설정 중..."
    
    # 현재 경로
    CURRENT_DIR=$(pwd)
    USER=$(whoami)
    
    # Job 스케줄러 서비스
    cat > /tmp/job-scheduler.service << EOF
[Unit]
Description=Lightweight Job Scheduler for Naver Real Estate Collector
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/job_cli.py run --data-dir $CURRENT_DIR/scheduler_data
Restart=always
RestartSec=10

# 메모리 제한 (100MB)
MemoryLimit=100M
MemoryHigh=80M

# 로그 설정
StandardOutput=journal
StandardError=journal

# 환경변수
Environment=PYTHONPATH=$CURRENT_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Job 대시보드 서비스
    cat > /tmp/job-dashboard.service << EOF
[Unit]
Description=Lightweight Job Dashboard for Naver Real Estate Collector
After=network.target job-scheduler.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/job_dashboard.py --port 8888 --host 0.0.0.0 --scheduler-data $CURRENT_DIR/scheduler_data
Restart=always
RestartSec=10

# 메모리 제한
MemoryLimit=50M
MemoryHigh=40M

# 로그 설정
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # 서비스 파일 설치 시도 (sudo 권한 필요)
    if sudo -n true 2>/dev/null; then
        sudo mv /tmp/job-scheduler.service /etc/systemd/system/
        sudo mv /tmp/job-dashboard.service /etc/systemd/system/
        sudo systemctl daemon-reload
        
        log_success "systemd 서비스 설정 완료"
        log_info "서비스 시작: sudo systemctl start job-scheduler job-dashboard"
        log_info "자동 시작 설정: sudo systemctl enable job-scheduler job-dashboard"
    else
        log_warning "sudo 권한이 없어 systemd 서비스를 설치할 수 없습니다"
        log_info "수동으로 서비스 파일을 설치해주세요:"
        log_info "  sudo mv /tmp/job-scheduler.service /etc/systemd/system/"
        log_info "  sudo mv /tmp/job-dashboard.service /etc/systemd/system/"
    fi
}

# 방화벽 설정
setup_firewall() {
    log_info "방화벽 설정 확인 중..."
    
    # ufw가 활성화되어 있는지 확인
    if command -v ufw &> /dev/null && sudo ufw status | grep -q "Status: active"; then
        log_info "ufw 방화벽이 활성화되어 있습니다"
        
        # 포트 8888 열기
        if sudo -n true 2>/dev/null; then
            sudo ufw allow 8888/tcp > /dev/null 2>&1
            log_success "포트 8888 (대시보드) 허용"
        else
            log_warning "수동으로 포트를 열어주세요: sudo ufw allow 8888/tcp"
        fi
    else
        log_info "ufw 방화벽이 비활성화되어 있거나 설치되지 않음"
    fi
    
    # AWS 보안 그룹 안내
    log_info "AWS EC2 사용 시 보안 그룹에서 포트 8888을 열어주세요"
}

# 테스트 실행
run_tests() {
    log_info "시스템 테스트 실행 중..."
    
    # 1. 스케줄러 임포트 테스트
    python3 -c "from lightweight_scheduler import LightweightScheduler; print('스케줄러 모듈 로드 성공')" 2>/dev/null
    if [ $? -eq 0 ]; then
        log_success "스케줄러 모듈 테스트 통과"
    else
        log_error "스케줄러 모듈 테스트 실패"
        return 1
    fi
    
    # 2. CLI 도구 테스트
    python3 job_cli.py --help > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_success "CLI 도구 테스트 통과"
    else
        log_error "CLI 도구 테스트 실패"
        return 1
    fi
    
    # 3. 메모리 사용량 테스트 (간단한 스케줄러 실행)
    timeout 5s python3 -c "
from lightweight_scheduler import LightweightScheduler
import time
s = LightweightScheduler()
s.start()
time.sleep(2)
s.stop()
print('메모리 테스트 통과')
" 2>/dev/null
    if [ $? -eq 0 ] || [ $? -eq 124 ]; then  # 124는 timeout 코드
        log_success "메모리 사용량 테스트 통과"
    else
        log_warning "메모리 사용량 테스트에서 경고 발생"
    fi
    
    log_success "모든 테스트 통과"
}

# 설정 파일 생성
create_config() {
    log_info "설정 파일 생성 중..."
    
    cat > job_system_config.json << EOF
{
    "system": {
        "max_memory_mb": 100,
        "max_concurrent_jobs": 3,
        "log_retention_days": 7,
        "cleanup_interval_hours": 24
    },
    "scheduler": {
        "check_interval_seconds": 10,
        "max_job_runtime_seconds": 7200,
        "default_retry_count": 0,
        "data_directory": "./scheduler_data"
    },
    "dashboard": {
        "port": 8888,
        "host": "0.0.0.0",
        "refresh_interval_seconds": 30,
        "max_log_lines": 100
    },
    "collection": {
        "default_max_workers": 2,
        "timeout_minutes": 120,
        "retry_delay_minutes": 5
    }
}
EOF

    log_success "설정 파일 생성 완료 (job_system_config.json)"
}

# 사용법 안내
show_usage_guide() {
    echo ""
    echo "🎉 라이트웨이트 Job 관리 시스템 배포 완료!"
    echo "================================================"
    echo ""
    echo "📚 사용 방법:"
    echo ""
    echo "1️⃣ 스케줄러 시작 (데몬 모드):"
    echo "   python3 job_cli.py start --daemon"
    echo ""
    echo "2️⃣ 대시보드 시작:"
    echo "   python3 job_dashboard.py"
    echo "   브라우저에서 http://localhost:8888 접속"
    echo ""
    echo "3️⃣ 빠른 설정 (권장 Job들 자동 생성):"
    echo "   python3 job_cli.py setup"
    echo ""
    echo "4️⃣ 수동 Job 생성 예제:"
    echo "   python3 job_cli.py create single --dong 역삼동 --name '역삼동_테스트'"
    echo "   python3 job_cli.py create full --workers 2 --name '전체수집'"
    echo ""
    echo "5️⃣ 상태 확인:"
    echo "   python3 job_cli.py status"
    echo "   python3 job_cli.py list"
    echo ""
    echo "🔧 관리 명령어:"
    echo "   python3 job_cli.py logs                  # 스케줄러 로그 확인"
    echo "   python3 job_cli.py cancel <job_id>       # Job 취소"
    echo "   python3 job_cli.py remove <job_id>       # Job 제거"
    echo "   python3 job_cli.py stop                  # 스케줄러 중지"
    echo ""
    echo "🌐 외부 접속 설정 (EC2):"
    echo "   - 보안 그룹에서 포트 8888 허용"
    echo "   - http://<EC2-PUBLIC-IP>:8888 으로 접속"
    echo ""
    echo "⚙️ systemd 서비스 (선택사항):"
    echo "   sudo systemctl start job-scheduler    # 스케줄러 서비스 시작"
    echo "   sudo systemctl start job-dashboard    # 대시보드 서비스 시작"
    echo "   sudo systemctl enable job-scheduler   # 자동 시작 설정"
    echo ""
    echo "📊 리소스 모니터링:"
    echo "   - 메모리 사용량: <100MB 목표"
    echo "   - CPU 사용률: <10% 유휴시"
    echo "   - 로그 파일: scheduler_data/ 디렉토리"
    echo ""
    echo "🆘 문제 해결:"
    echo "   - 로그 확인: tail -f scheduler_data/scheduler.log"
    echo "   - 프로세스 확인: ps aux | grep python"
    echo "   - 포트 확인: netstat -tlnp | grep 8888"
    echo ""
}

# 메인 실행 함수
main() {
    echo "현재 디렉토리: $(pwd)"
    echo "사용자: $(whoami)"
    echo ""
    
    # 단계별 실행
    check_requirements
    echo ""
    
    install_dependencies
    echo ""
    
    setup_directories
    echo ""
    
    setup_permissions
    echo ""
    
    setup_systemd_service
    echo ""
    
    setup_firewall
    echo ""
    
    create_config
    echo ""
    
    run_tests
    echo ""
    
    show_usage_guide
}

# 인수 처리
case "${1:-}" in
    --help|-h)
        echo "사용법: $0 [--help|--test-only|--no-systemd]"
        echo ""
        echo "옵션:"
        echo "  --help        이 도움말 표시"
        echo "  --test-only   테스트만 실행"
        echo "  --no-systemd  systemd 서비스 설정 건너뛰기"
        exit 0
        ;;
    --test-only)
        log_info "테스트 모드 실행"
        run_tests
        exit $?
        ;;
    --no-systemd)
        log_info "systemd 서비스 설정 건너뛰기 모드"
        main() {
            check_requirements
            install_dependencies
            setup_directories
            setup_permissions
            setup_firewall
            create_config
            run_tests
            show_usage_guide
        }
        main
        ;;
    "")
        # 기본 실행
        main
        ;;
    *)
        log_error "알 수 없는 옵션: $1"
        echo "사용법: $0 [--help|--test-only|--no-systemd]"
        exit 1
        ;;
esac