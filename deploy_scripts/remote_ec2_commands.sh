#!/bin/bash
# EC2 원격 명령어 실행 도구

set -e

# EC2 설정
EC2_HOST="52.78.34.225"  # EC2 퍼블릭 IP 또는 도메인
EC2_USER="ubuntu"  # EC2 사용자 (Amazon Linux는 ec2-user, Ubuntu는 ubuntu)
EC2_KEY="/home/hackit/.ssh/naver-land-collector-v2-key.pem"  # EC2 키 파일 경로
REMOTE_PATH="/home/ubuntu/naver_land"  # EC2 내 프로젝트 경로

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

show_help() {
    echo "EC2 원격 명령어 도구"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  setup          - 기본 환경 설정 (Python 가상환경, 패키지 설치)"
    echo "  api            - API 키 설정 (.env 파일 생성)"
    echo "  cron           - Cron 스케줄링 설정"
    echo "  test           - 수집 테스트 실행"
    echo "  status         - 프로젝트 상태 확인"
    echo "  logs           - 최신 로그 확인"
    echo "  error-logs     - 에러 로그만 확인"
    echo "  debug          - 상세 디버그 정보 수집"
    echo "  test-connection - Supabase API 연결 테스트"
    echo "  install-packages - 필수 패키지 설치"
    echo "  check-timezone - EC2 시간대 및 크론탭 확인"
    echo "  results        - 수집 결과 확인"
    echo "  shell          - EC2에 SSH 접속"
    echo "  system-info    - EC2 시스템 정보 확인"
    echo ""
    echo "예시:"
    echo "  $0 setup    # 기본 환경 설정"
    echo "  $0 api      # API 키 설정"
    echo "  $0 test     # 테스트 실행"
    echo "  $0 debug    # 문제 진단"
}

# EC2에 명령어 실행
run_remote_command() {
    local command="$1"
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "$command"
}

case "${1:-help}" in
    "setup")
        print_step "기본 환경 설정 실행"
        run_remote_command "
            cd $REMOTE_PATH
            # Python 가상환경 생성
            if [ ! -d 'venv' ]; then
                echo '🔧 Python 가상환경 생성 중...'
                python3 -m venv venv
            fi
            
            # 필수 패키지 설치
            source venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            
            # 필요한 디렉토리 생성
            mkdir -p logs results collectors/results
            
            echo '✅ 기본 환경 설정 완료'
        "
        ;;
    
    "api")
        print_step "API 키 설정"
        echo "Supabase URL을 입력하세요:"
        read -r SUPABASE_URL
        echo "Supabase API Key를 입력하세요:"
        read -rs SUPABASE_KEY
        echo ""
        
        run_remote_command "
            cd $REMOTE_PATH
            cat > .env << EOF
SUPABASE_URL=$SUPABASE_URL
SUPABASE_KEY=$SUPABASE_KEY
EOF
            echo '✅ API 키 설정 완료'
        "
        ;;
    
    "cron")
        print_step "매일 수집 크론 스케줄 설정"
        run_remote_command "
            # 기존 크론탭 백업
            crontab -l > ~/crontab_backup_\$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true
            
            # 현재 시간 확인 (UTC)
            current_hour=\$(date +%H)
            current_minute=\$(date +%M)
            
            # 현재 시간 + 5분 후 시작 (첫 실행)
            start_minute=\$((current_minute + 5))
            start_hour=\$current_hour
            
            # 60분 초과시 시간 조정
            if [ \$start_minute -ge 60 ]; then
                start_minute=\$((start_minute - 60))
                start_hour=\$((start_hour + 1))
            fi
            
            # 24시간 초과시 조정
            if [ \$start_hour -ge 24 ]; then
                start_hour=\$((start_hour - 24))
            fi
            
            echo \"🕐 현재 시간: \$(date)\"
            echo \"⏰ 첫 실행: \$(printf '%02d:%02d' \$start_hour \$start_minute) UTC (약 5분 후)\"
            echo \"🔄 이후 매일: 19:00 UTC (한국시간 04:00)\"
            echo \"\"
            
            # 새로운 크론탭 설정 - 오늘부터 시작 + 매일 실행
            cat << EOF | crontab -
# 첫 실행: 지금부터 5분 후 (1회만)
\$start_minute \$start_hour * * * cd $REMOTE_PATH/collectors && python3 parallel_batch_collect_gangnam.py --max-workers 1
# 매일 19:00 UTC (한국시간 04:00) - 정기 수집
0 19 * * * cd $REMOTE_PATH/collectors && python3 parallel_batch_collect_gangnam.py --max-workers 1
EOF
            
            echo '✅ 매일 수집 크론탭 설정 완료'
            echo '📅 실행 스케줄:'
            echo \"  🚀 첫 실행: 오늘 \$(printf '%02d:%02d' \$start_hour \$start_minute) UTC\"
            echo '  🔄 정기 실행: 매일 19:00 UTC (한국시간 04:00)'
            echo '  📊 수집 범위: 강남구 전체 (14개 동)'
            echo '  ⚙️  워커 수: 1개 (안정성 우선)'
            echo ''
            echo '=== 설정된 크론탭 ==='
            crontab -l
            echo ''
            echo '📝 참고:'
            echo '  - 첫 실행은 오늘 1회만 실행됩니다'
            echo '  - 내일부터는 매일 04:00 KST에 실행됩니다'
            echo '  - 로그 확인: ./deploy_scripts/remote_ec2_commands.sh logs'
        "
        ;;
    
    "test")
        print_step "수집 테스트 실행"
        run_remote_command "
            cd $REMOTE_PATH/collectors
            source ../venv/bin/activate
            python3 parallel_batch_collect_gangnam.py --max-workers 1
        "
        ;;
    
    "test-simple")
        print_step "단순 Import 테스트"
        run_remote_command "
            cd $REMOTE_PATH/collectors
            source ../venv/bin/activate
            python3 -c \"
from fixed_naver_collector import FixedNaverCollector, collect_by_cortar_no
from supabase_client import SupabaseHelper
print('✅ Import 성공')
helper = SupabaseHelper()
print('✅ Helper 생성 성공')
print('✅ collect_by_cortar_no 함수 사용 가능')
\"
        "
        ;;
    
    "status")
        print_step "프로젝트 상태 확인"
        run_remote_command "
            echo '=== 프로젝트 디렉토리 ==='
            ls -la $REMOTE_PATH/
            echo ''
            echo '=== collectors 디렉토리 ==='
            ls -la $REMOTE_PATH/collectors/
            echo ''
            echo '=== Cron 설정 ==='
            crontab -l 2>/dev/null || echo '크론탭 설정 없음'
            echo ''
            echo '=== Python 프로세스 ==='
            ps aux | grep -E 'python.*collect' | grep -v grep || echo '실행 중인 수집 프로세스 없음'
        "
        ;;
    
    "logs")
        print_step "최신 로그 확인"
        run_remote_command "
            if [ -d '$REMOTE_PATH/logs' ]; then
                echo '=== 로그 파일 목록 ==='
                ls -la $REMOTE_PATH/logs/
                echo ''
                echo '=== 최신 로그 내용 ==='
                tail -50 $REMOTE_PATH/logs/*.log 2>/dev/null || echo '로그 파일이 없습니다'
            else
                echo '로그 디렉토리가 없습니다'
            fi
        "
        ;;
    
    "error-logs")
        print_step "에러 로그 확인"
        run_remote_command "
            cd $REMOTE_PATH/logs
            echo '=== 최근 에러 로그 ==='
            grep -i 'error\|exception\|failed' *.log | tail -50 2>/dev/null || echo '에러 로그가 없습니다.'
        "
        ;;
    
    "debug")
        print_step "디버그 정보 수집"
        run_remote_command "
            echo '=== Python 버전 ==='
            python3 --version
            
            echo -e '\n=== 가상환경 상태 ==='
            ls -la $REMOTE_PATH/venv/bin/python 2>/dev/null || echo '가상환경 없음'
            
            echo -e '\n=== 환경변수 확인 ==='
            cat $REMOTE_PATH/.env 2>/dev/null | grep -E 'SUPABASE|API' | sed 's/=.*/=<hidden>/' || echo '.env 파일 없음'
            
            echo -e '\n=== 디스크 공간 ==='
            df -h /
            
            echo -e '\n=== 메모리 사용량 ==='
            free -m
            
            echo -e '\n=== CPU 정보 ==='
            nproc
            uptime
        "
        ;;
    
    "test-connection")
        print_step "API 연결 테스트"
        run_remote_command "
            cd $REMOTE_PATH/collectors
            source ../venv/bin/activate
            python3 -c \"
from supabase_client import SupabaseHelper
try:
    helper = SupabaseHelper()
    print('✅ Supabase Helper 초기화 성공')
    # 테이블 존재 확인
    response = helper.client.table('areas').select('*').limit(1).execute()
    print(f'✅ areas 테이블 접근 성공: {len(response.data)}개 데이터')
except Exception as e:
    print(f'❌ 연결 실패: {e}')
    import traceback
    traceback.print_exc()
\"
        "
        ;;
    
    "check-timezone")
        print_step "EC2 시간대 확인"
        run_remote_command "
            echo '=== 현재 시간대 ==='
            timedatectl 2>/dev/null || date
            
            echo -e '\n=== 현재 시간 ==='
            date
            
            echo -e '\n=== 현재 크론탭 ==='
            crontab -l 2>/dev/null || echo '크론탭 설정 없음'
        "
        ;;
    
    "install-packages")
        print_step "필수 패키지 설치"
        run_remote_command "
            cd $REMOTE_PATH
            source venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
        "
        ;;
    
    "results")
        print_step "수집 결과 확인"
        run_remote_command "
            echo '=== 결과 파일 목록 ==='
            ls -la $REMOTE_PATH/collectors/results/ 2>/dev/null || echo '결과 디렉토리가 없습니다'
            
            echo -e '\n=== 파일 크기 ==='
            du -sh $REMOTE_PATH/collectors/results/* 2>/dev/null || echo '결과 파일이 없습니다'
        "
        ;;
    
    "system-info")
        print_step "EC2 시스템 정보"
        run_remote_command "
            echo '=== EC2 인스턴스 정보 ==='
            ec2-metadata 2>/dev/null || echo 'ec2-metadata 명령어가 없습니다'
            
            echo -e '\n=== OS 정보 ==='
            cat /etc/os-release
            
            echo -e '\n=== 커널 정보 ==='
            uname -a
            
            echo -e '\n=== 네트워크 정보 ==='
            ip addr show | grep -E 'inet |state UP'
        "
        ;;
    
    "kill-processes")
        print_step "실행 중인 수집 프로세스 종료"
        run_remote_command "pkill -f 'python.*collect' || echo '종료할 프로세스가 없습니다.'"
        ;;
    
    "shell")
        print_step "EC2 SSH 접속"
        ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST"
        ;;
    
    "help"|*)
        show_help
        ;;
esac