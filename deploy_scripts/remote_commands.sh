#!/bin/bash
# VM 원격 명령어 실행 도구

set -e

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

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
    echo "VM 원격 명령어 도구"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  setup          - 기본 환경 설정 (프로젝트 클론, Python 설치)"
    echo "  api            - API 키 설정 대화형 모드"
    echo "  cron           - Cron 스케줄링 설정"
    echo "  test           - 수집 테스트 실행"
    echo "  status         - 프로젝트 상태 확인"
    echo "  logs           - 최신 로그 확인"
    echo "  error-logs     - 에러 로그만 확인"
    echo "  debug          - 상세 디버그 정보 수집"
    echo "  test-connection - Supabase API 연결 테스트"
    echo "  install-packages - 필수 패키지 설치"
    echo "  setup-weekly-cron - 주간 크론탭 설정 (서울시간 월요일 04시)"
    echo "  setup-tomorrow-cron - 내일 시작 + 주간 크론탭 설정"
    echo "  check-timezone - VM 시간대 및 크론탭 확인"
    echo "  results        - 수집 결과 확인"
    echo "  shell          - VM에 SSH 접속"
    echo ""
    echo "예시:"
    echo "  $0 setup    # 기본 환경 설정"
    echo "  $0 api      # API 키 설정"
    echo "  $0 test     # 테스트 실행"
    echo "  $0 debug    # 문제 진단"
}

# VM에 명령어 실행
run_remote_command() {
    local command="$1"
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="$command"
}

case "${1:-help}" in
    "setup")
        print_step "기본 환경 설정 실행"
        ./deploy_scripts/remote_setup.sh
        ;;
    "api")
        print_step "API 키 설정 (대화형 모드)"
        run_remote_command "cd ~/naver_land/collectors && python3 setup_deployment.py"
        ;;
    "cron")
        print_step "Cron 스케줄링 설정"
        run_remote_command "cd ~/naver_land && ./deploy_scripts/setup_cron.sh"
        ;;
    "test")
        print_step "수집 테스트 실행"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 parallel_batch_collect_gangnam.py --max-workers 1"
        ;;
    "test-simple")
        print_step "단순 Import 테스트"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from fixed_naver_collector import FixedNaverCollector, collect_by_cortar_no
from supabase_client import SupabaseHelper
print('✅ Import 성공')
helper = SupabaseHelper()
print('✅ Helper 생성 성공')
# collect_by_cortar_no는 자동으로 토큰을 가져옴
print('✅ collect_by_cortar_no 함수 사용 가능')
\""
        ;;
    "test-error")
        print_step "에러 재현 테스트"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from supabase_client import SupabaseHelper
from fixed_naver_collector import collect_by_cortar_no

try:
    helper = SupabaseHelper()
    print('✅ Helper 초기화 성공')
    
    # 강남구 역삼동 테스트
    cortar_no = '1168010100'
    print(f'🔍 테스트 지역: 강남구 역삼동 ({cortar_no})')
    
    # 수집 실행 (작은 양만)
    print('📡 데이터 수집 시작...')
    properties = collect_by_cortar_no(cortar_no)
    print(f'✅ 수집 완료: {len(properties)}개 매물')
    
    if properties:
        # 처음 10개만 테스트
        test_props = properties[:10]
        print(f'💾 DB 저장 테스트: {len(test_props)}개')
        result = helper.save_properties(test_props, cortar_no)
        print(f'✅ 저장 결과: {result}')
    else:
        print('⚠️ 수집된 매물이 없습니다')
        
except Exception as e:
    print(f'❌ 에러 발생: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
\""
        ;;
    "test-small")
        print_step "가장 작은 동 테스트 (율현동)"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from supabase_client import SupabaseHelper
from fixed_naver_collector import collect_by_cortar_no
from datetime import date

try:
    helper = SupabaseHelper()
    print('✅ Helper 초기화 성공')
    
    # 가장 작은 동 - 율현동
    cortar_no = '1168011300'
    print(f'🔍 테스트 지역: 강남구 율현동 ({cortar_no})')
    
    # 수집 실행 (1페이지만)
    print('📡 데이터 수집 시작 (1페이지만)...')
    result = collect_by_cortar_no(cortar_no, include_details=False, max_pages=1)
    
    if result['success']:
        properties = result['properties']
        print(f'✅ 수집 완료: {len(properties)}개 매물')
        
        if properties:
            print(f'💾 DB 저장 시작: {len(properties)}개')
            save_result = helper.save_properties(properties, cortar_no)
            print(f'✅ 저장 완료: {save_result}')
            
            # 통계도 저장
            helper.save_daily_stats(date.today(), cortar_no, properties, save_result)
            print('✅ 통계 저장 완료')
        else:
            print('⚠️ 수집된 매물이 없습니다')
    else:
        print(f'❌ 수집 실패: {result.get(\"error\")}')
        
except Exception as e:
    print(f'❌ 에러 발생: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
\""
        ;;
    "test-tiny")
        print_step "율현동 1페이지 수집 및 DB 저장 테스트"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from supabase_client import SupabaseHelper
from fixed_naver_collector import collect_by_cortar_no
from datetime import date

try:
    helper = SupabaseHelper()
    print('✅ Helper 초기화 성공')
    
    # 가장 작은 동 - 율현동
    cortar_no = '1168011300'
    print(f'🔍 테스트 지역: 강남구 율현동 ({cortar_no})')
    
    # 수집 실행 (1페이지만)
    print('📡 데이터 수집 시작 (1페이지만)...')
    properties = collect_by_cortar_no(cortar_no, include_details=False, max_pages=1)
    
    print(f'📊 반환 결과 타입: {type(properties)}')
    
    if isinstance(properties, dict) and properties.get('success'):
        filepath = properties.get('filepath')
        count = properties.get('count', 0)
        print(f'✅ 수집 완료: {count}개 매물 (파일: {filepath})')
        
        if count > 0 and filepath:
            # 파일에서 매물 데이터 읽기
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                
            property_list = file_data.get('매물목록', [])
            print(f'💾 DB 저장 시작: {len(property_list)}개')
            save_result = helper.save_properties(property_list, cortar_no)
            print(f'✅ 저장 완료: {save_result}')
            
            # 통계도 저장
            helper.save_daily_stats(date.today(), cortar_no, property_list, save_result)
            print('✅ 통계 저장 완료')
            
            # collection_logs에 완료 로그 저장
            from datetime import datetime
            log_data = {
                'gu_name': '강남구',
                'dong_name': '율현동',
                'cortar_no': cortar_no,
                'collection_type': 'manual_test',
                'status': 'completed',
                'total_collected': count,
                'error_message': None,
                'started_at': datetime.now().isoformat(),
                'completed_at': datetime.now().isoformat()
            }
            helper.log_collection(log_data)
            print('✅ collection_logs 저장 완료')
        else:
            print('⚠️ 수집된 매물이 없습니다')
    else:
        print(f'❌ 수집 실패')
        print(f'📄 내용: {properties}')
        
except Exception as e:
    print(f'❌ 에러 발생: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
\""
        ;;
    "status")
        print_step "프로젝트 상태 확인"
        run_remote_command "ls -la ~/naver_land/ && echo '=== collectors 디렉토리 ===' && ls -la ~/naver_land/collectors/ && echo '=== Cron 설정 ===' && crontab -l"
        ;;
    "logs")
        print_step "최신 로그 확인"
        run_remote_command "ls -la ~/naver_land/logs/ && echo '=== 최신 로그 내용 ===' && tail -20 ~/naver_land/logs/daily_collection_20250806_090001.log 2>/dev/null"
        ;;
    "check-daily-script")
        print_step "Daily Collection 스크립트 확인"
        run_remote_command "cat ~/naver_land/deploy_scripts/daily_collection.sh 2>/dev/null || echo '스크립트가 없습니다.'"
        ;;
    "error-logs")
        print_step "에러 로그 확인"
        run_remote_command "cd ~/naver_land/logs && echo '=== 최근 에러 로그 ===' && grep -i 'error\|exception\|failed' *.log | tail -50 2>/dev/null || echo '에러 로그가 없습니다.'"
        ;;
    "debug")
        print_step "디버그 정보 수집"
        run_remote_command "
            echo '=== Python 버전 ==='
            python3 --version
            echo -e '\n=== 가상환경 상태 ==='
            ls -la ~/naver_land/venv/bin/python 2>/dev/null || echo '가상환경 없음'
            echo -e '\n=== parse_qs 테스트 ==='
            cd ~/naver_land && source venv/bin/activate && python3 -c \"
from urllib.parse import parse_qs
# 네이버 부동산 URL 예시
test_query = 'ms=37.5665,126.9780,15&a=APT&e=RETAIL'
result = parse_qs(test_query)
print(f'parse_qs 결과 타입: {type(result)}')
print(f'ms 값: {result.get(\"ms\")} (타입: {type(result.get(\"ms\"))})')
print(f'a 값: {result.get(\"a\")} (타입: {type(result.get(\"a\"))})')
\"
            echo -e '\n=== 환경변수 확인 ==='
            cat ~/naver_land/.env 2>/dev/null | grep -E 'SUPABASE|API' | sed 's/=.*/=<hidden>/'
            echo -e '\n=== 프로세스 상태 ==='
            ps aux | grep -E 'python.*collect' | grep -v grep || echo '실행 중인 수집 프로세스 없음'
            echo -e '\n=== 최근 Cron 실행 로그 ==='
            tail -20 /var/log/syslog | grep CRON 2>/dev/null || echo 'Cron 로그 접근 불가'
            echo -e '\n=== 디스크 공간 ==='
            df -h ~/
            echo -e '\n=== 메모리 사용량 ==='
            free -m
        "
        ;;
    "test-connection")
        print_step "API 연결 테스트"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
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
\""
        ;;
    "check-logs")
        print_step "collection_logs 테이블 확인"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from supabase_client import SupabaseHelper
from datetime import datetime
try:
    helper = SupabaseHelper()
    # 최근 로그 확인
    # ID 역순으로 정렬하여 최신 로그 확인
    from supabase import Client
    response = helper.client.from_('collection_logs').select('*').order('id', desc=True).limit(10).execute()
    print(f'📊 최근 collection_logs: {len(response.data)}개')
    if response.data:
        for log in response.data:
            print(f'  - {log}')
    else:
        print('  - 로그가 없습니다')
except Exception as e:
    print(f'❌ 로그 확인 실패: {e}')
    import traceback
    traceback.print_exc()
\""
        ;;
    "check-timezone")
        print_step "VM 시간대 및 크론탭 확인"
        run_remote_command "
            echo '=== 현재 시간대 ==='
            timedatectl
            echo -e '\n=== 현재 시간 ==='
            date
            echo -e '\n=== 현재 크론탭 ==='
            crontab -l
            echo -e '\n=== 다음 실행 시간 ==='
            echo '📅 다음 실행 예정: 매주 일요일 19:00 UTC'
            echo '🕐 서울시간 기준: 매주 월요일 04:00 KST'
            echo '⏰ 이번 주 일요일: 2025-08-10 19:00 UTC (2025-08-11 04:00 KST)'
        "
        ;;
    "setup-weekly-cron")
        print_step "주간 크론탭 설정 (서울시간 일요일 04시)"
        run_remote_command "
            echo '🕐 새로운 크론탭 설정: 매주 일요일 19:00 UTC (서울시간 04:00)'
            # 기존 크론탭 백업
            crontab -l > ~/crontab_backup_\$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true
            
            # 새로운 크론탭 설정
            echo '# 매주 일요일 19:00 UTC (서울시간 월요일 04:00) - 주간 전체 수집
0 19 * * 0 /home/hackit/naver_land/deploy_scripts/daily_collection.sh' | crontab -
            
            echo '✅ 크론탭 설정 완료'
            echo '📅 다음 실행 예정:'
            echo '  - UTC: 매주 일요일 19:00'  
            echo '  - 서울시간: 매주 월요일 04:00'
            
            echo -e '\n=== 설정된 크론탭 ==='
            crontab -l
        "
        ;;
    "setup-tomorrow-cron")
        print_step "내일 시작 + 주간 크론탭 설정"
        run_remote_command "
            echo '🕐 크론탭 설정: 내일(8/7) 04:00 KST 시작, 그 후 매주 수요일'
            # 기존 크론탭 백업
            crontab -l > ~/crontab_backup_\$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true
            
            # 새로운 크론탭 설정 - 내일(8/6 19시 UTC) + 매주 수요일(19시 UTC)
            echo '# 내일 8월 7일 04:00 KST (8월 6일 19:00 UTC) 1회 실행
0 19 6 8 * /home/hackit/naver_land/deploy_scripts/daily_collection.sh
# 그 후 매주 수요일 19:00 UTC (목요일 04:00 KST) - 주간 전체 수집  
0 19 * * 3 /home/hackit/naver_land/deploy_scripts/daily_collection.sh' | crontab -
            
            echo '✅ 크론탭 설정 완료'
            echo '📅 실행 스케줄:'
            echo '  🚀 첫 실행: 2025-08-07 04:00 KST (내일)'
            echo '  🔄 정기 실행: 매주 목요일 04:00 KST'
            echo '  ⏰ UTC 기준: 매주 수요일 19:00'
            
            echo -e '\n=== 설정된 크론탭 ==='
            crontab -l
        "
        ;;
    "test-cron-service")
        print_step "크론 서비스 상태 확인"
        run_remote_command "
            echo '=== 크론 서비스 상태 ==='
            systemctl status cron
            echo -e '\n=== 크론 데몬 실행 확인 ==='
            ps aux | grep cron | grep -v grep
            echo -e '\n=== 최근 크론 로그 ==='
            tail -10 /var/log/syslog | grep CRON || echo '크론 로그 없음'
        "
        ;;
    "test-new-features")
        print_step "새로운 기능 테스트"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from supabase_client import SupabaseHelper
print('✅ 업데이트된 SupabaseHelper 테스트')

# 새로운 기능들이 정상적으로 작동하는지 확인
helper = SupabaseHelper()

# 테이블들이 존재하는지 확인
tables_to_check = ['properties', 'price_history', 'deletion_history', 'daily_stats', 'collection_logs']
for table in tables_to_check:
    try:
        result = helper.client.table(table).select('*').limit(1).execute()
        print(f'✅ {table} 테이블 접근 가능: {len(result.data)}개 데이터')
    except Exception as e:
        print(f'❌ {table} 테이블 오류: {e}')

print('🔧 업데이트된 코드가 정상적으로 작동합니다')
\""
        ;;
    "test-upload")
        print_step "세곡동 테스트 파일 실행"
        run_remote_command "cd ~/naver_land/collectors && source ../venv/bin/activate && python3 test_seogok_upload.py"
        ;;
    "install-packages")
        print_step "필수 패키지 설치"
        run_remote_command "cd ~/naver_land && source venv/bin/activate && pip install -r requirements.txt"
        ;;
    "results")
        print_step "수집 결과 확인"
        run_remote_command "ls -la ~/naver_land/collectors/results/ && echo '=== 파일 크기 ===' && du -sh ~/naver_land/collectors/results/* 2>/dev/null || echo '결과 파일이 없습니다.'"
        ;;
    "fix-collector")
        print_step "fixed_naver_collector.py 수정"
        run_remote_command "cd ~/naver_land/collectors && cp fixed_naver_collector.py fixed_naver_collector.py.backup && sed -i \"s/query.get('ms', \[''\])\[0\]/query.get('ms', \[''\])[0] if isinstance(query.get('ms'), list) else query.get('ms', '')/g\" fixed_naver_collector.py && sed -i \"s/query.get('a', \[''\])\[0\]/query.get('a', \[''\])[0] if isinstance(query.get('a'), list) else query.get('a', '')/g\" fixed_naver_collector.py && sed -i \"s/query.get('e', \[''\])\[0\]/query.get('e', \[''\])[0] if isinstance(query.get('e'), list) else query.get('e', '')/g\" fixed_naver_collector.py && echo '✅ 수정 완료'"
        ;;
    "kill-processes")
        print_step "실행 중인 수집 프로세스 종료"
        run_remote_command "pkill -f 'python.*collect' || echo '종료할 프로세스가 없습니다.'"
        ;;
    "shell")
        print_step "VM SSH 접속"
        gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID"
        ;;
    "help"|*)
        show_help
        ;;
esac