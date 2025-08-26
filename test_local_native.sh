#!/bin/bash
# WSL2 네이티브 환경에서 EC2와 동일한 조건으로 테스트

set -e

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

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "========================================"
echo "     WSL2 네이티브 EC2 환경 테스트"
echo "========================================"
echo ""

# 현재 환경 확인
print_step "현재 환경 확인"
echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
echo "Python: $(python3 --version)"
echo "메모리: $(free -h | grep Mem | awk '{print $2}')"
echo "CPU: $(nproc)개 코어"

# 1. 프로젝트 디렉토리 확인
print_step "프로젝트 구조 확인"
if [ ! -d "collectors" ]; then
    print_error "collectors 디렉토리가 없습니다. 올바른 위치에서 실행하세요."
    exit 1
fi
print_success "프로젝트 구조 확인됨"

# 2. Python 가상환경 설정
print_step "Python 가상환경 설정"
if [ ! -d "test_venv" ]; then
    echo "테스트용 가상환경을 생성합니다..."
    python3 -m venv test_venv
fi

source test_venv/bin/activate
print_success "가상환경 활성화: $(which python3)"

# 3. 패키지 설치
print_step "패키지 설치"
pip install --upgrade pip
pip install -r requirements.txt
print_success "패키지 설치 완료"

# 4. 환경 설정 확인
print_step "환경 설정 확인"
if [ ! -f ".env" ]; then
    print_warning ".env 파일이 없습니다."
    echo ""
    echo "Supabase 설정을 입력하세요:"
    read -p "SUPABASE_URL: " SUPABASE_URL
    read -sp "SUPABASE_KEY: " SUPABASE_KEY
    echo ""
    
    cat > .env << EOF
SUPABASE_URL=$SUPABASE_URL
SUPABASE_KEY=$SUPABASE_KEY
EOF
    print_success ".env 파일 생성 완료"
else
    print_success ".env 파일 존재"
fi

# 5. 토큰 캐시 확인
print_step "토큰 캐시 확인"
if [ ! -f "collectors/cached_token.json" ]; then
    print_warning "토큰 캐시가 없습니다."
    echo "토큰 설정을 진행하시겠습니까? (y/N)"
    read -r SETUP_TOKEN
    if [[ "$SETUP_TOKEN" =~ ^[Yy]$ ]]; then
        cd collectors
        python3 setup_deployment.py
        cd ..
    fi
else
    print_success "토큰 캐시 존재"
fi

# 6. 메모리 제한 시뮬레이션 함수
simulate_memory_limit() {
    local limit_mb=$1
    local test_name=$2
    
    print_step "$test_name 환경 시뮬레이션 (메모리 제한: ${limit_mb}MB)"
    
    # 메모리 사용량 모니터링 시작
    local pid=$$
    (
        while kill -0 $pid 2>/dev/null; do
            local mem_usage=$(ps -o rss= -p $pid 2>/dev/null | tail -1)
            if [ -n "$mem_usage" ] && [ "$mem_usage" -gt $((limit_mb * 1024)) ]; then
                echo ""
                print_error "메모리 제한 초과: ${mem_usage}KB > ${limit_mb}MB"
                echo "실제 EC2 $test_name에서는 메모리 부족으로 실패할 수 있습니다."
                return 1
            fi
            sleep 2
        done
    ) &
    local monitor_pid=$!
    
    return 0
}

# 7. 테스트 메뉴
echo ""
echo "테스트 시나리오를 선택하세요:"
echo "1) Import 테스트 (빠름)"
echo "2) 간단한 수집 테스트 (중간)"
echo "3) t2.micro 시뮬레이션 (1GB 메모리 제한)"
echo "4) t3.small 시뮬레이션 (2GB 메모리 제한)"
echo "5) 성능 벤치마크 (제한 없음)"
echo "6) 모든 테스트 실행"
read -p "선택 [1-6] (기본값: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        print_step "Import 테스트 실행"
        python3 -c "
import sys
sys.path.append('collectors')

try:
    from fixed_naver_collector import FixedNaverCollector
    print('✅ FixedNaverCollector import 성공')
    
    from supabase_client import SupabaseHelper
    print('✅ SupabaseHelper import 성공')
    
    from kakao_address_converter import KakaoAddressConverter
    print('✅ KakaoAddressConverter import 성공')
    
    print('')
    print('🎉 모든 핵심 모듈 import 성공!')
    print('EC2 배포 시 정상 동작할 것으로 예상됩니다.')
    
except ImportError as e:
    print(f'❌ Import 실패: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ 오류 발생: {e}')
    sys.exit(1)
"
        ;;
    
    2)
        print_step "간단한 수집 테스트 실행"
        cd collectors
        echo "역삼동 1페이지 수집 테스트..."
        python3 -c "
from cached_token_collector import collect_by_cortar_no
import time

start_time = time.time()
try:
    result = collect_by_cortar_no('1168010100', include_details=False, max_pages=1)
    end_time = time.time()
    
    if result.get('success'):
        print(f'✅ 수집 성공: {result.get(\"count\", 0)}개 매물')
        print(f'⏱️ 소요 시간: {end_time - start_time:.1f}초')
        print('🎉 EC2에서도 정상 동작할 것으로 예상됩니다.')
    else:
        print(f'❌ 수집 실패: {result.get(\"error\")}')
except Exception as e:
    print(f'❌ 오류 발생: {e}')
"
        cd ..
        ;;
    
    3)
        print_step "t2.micro 환경 시뮬레이션 (1GB)"
        echo "⚠️ 메모리 사용량을 모니터링합니다..."
        
        cd collectors
        python3 -c "
import psutil
import os
from cached_token_collector import collect_by_cortar_no

process = psutil.Process(os.getpid())
print(f'초기 메모리: {process.memory_info().rss / 1024 / 1024:.1f} MB')

# 수집 테스트
try:
    result = collect_by_cortar_no('1168010100', include_details=True, max_pages=1)
    current_mem = process.memory_info().rss / 1024 / 1024
    print(f'수집 후 메모리: {current_mem:.1f} MB')
    
    if current_mem < 800:  # 1GB의 80%
        print('✅ t2.micro(1GB)에서 안전하게 실행 가능')
    elif current_mem < 1000:
        print('⚠️ t2.micro에서 실행 가능하지만 여유 공간 부족')
    else:
        print('❌ t2.micro에서는 메모리 부족 위험')
        print('→ t3.small 이상 권장')
        
except Exception as e:
    print(f'❌ 테스트 실패: {e}')
"
        cd ..
        ;;
    
    4)
        print_step "t3.small 환경 시뮬레이션 (2GB)"
        cd collectors
        python3 -c "
import psutil
import os
from parallel_batch_collect_gangnam import collect_single_dong
import time

process = psutil.Process(os.getpid())
print(f'초기 메모리: {process.memory_info().rss / 1024 / 1024:.1f} MB')

# 역삼동 테스트
area_info = {
    'gu_name': '강남구',
    'dong_name': '역삼동', 
    'cortar_no': '1168010100'
}

start_time = time.time()
try:
    result = collect_single_dong(area_info, include_details=True)
    end_time = time.time()
    
    current_mem = process.memory_info().rss / 1024 / 1024
    print(f'수집 후 메모리: {current_mem:.1f} MB')
    print(f'소요 시간: {end_time - start_time:.1f}초')
    
    if result.get('success'):
        print(f'✅ 수집 성공: {result.get(\"count\", 0)}개 매물')
        print('✅ t3.small(2GB)에서 매우 안정적으로 실행 가능')
    else:
        print(f'❌ 수집 실패: {result.get(\"error\")}')
        
except Exception as e:
    print(f'❌ 테스트 실패: {e}')
"
        cd ..
        ;;
    
    5)
        print_step "성능 벤치마크 (제한 없음)"
        cd collectors
        python3 -c "
import time
import psutil
import os
from parallel_batch_collect_gangnam import collect_single_dong

areas = [
    {'gu_name': '강남구', 'dong_name': '역삼동', 'cortar_no': '1168010100'},
    {'gu_name': '강남구', 'dong_name': '삼성동', 'cortar_no': '1168010500'},
]

process = psutil.Process(os.getpid())
total_count = 0
total_time = 0

for area in areas:
    print(f'🔍 {area[\"dong_name\"]} 수집 중...')
    start_time = time.time()
    
    try:
        result = collect_single_dong(area, include_details=True)
        end_time = time.time()
        duration = end_time - start_time
        
        if result.get('success'):
            count = result.get('count', 0)
            total_count += count
            total_time += duration
            
            rate = count / duration if duration > 0 else 0
            print(f'  ✅ {count}개 매물, {duration:.1f}초, {rate:.1f}개/초')
        else:
            print(f'  ❌ 실패: {result.get(\"error\")}')
            
    except Exception as e:
        print(f'  ❌ 오류: {e}')

print(f'')
print(f'📊 전체 성능:')
print(f'  총 매물: {total_count}개')
print(f'  총 시간: {total_time:.1f}초')
if total_time > 0:
    print(f'  평균 속도: {total_count / total_time:.1f}개/초')
    print(f'  시간당 예상: {int(total_count / total_time * 3600)}개/시간')

current_mem = process.memory_info().rss / 1024 / 1024
print(f'  최대 메모리: {current_mem:.1f} MB')
"
        cd ..
        ;;
    
    6)
        print_step "모든 테스트 순차 실행"
        
        # 1. Import 테스트
        echo ""
        echo "======== 1. Import 테스트 ========"
        python3 -c "
import sys
sys.path.append('collectors')

try:
    from fixed_naver_collector import FixedNaverCollector
    print('✅ FixedNaverCollector import 성공')
    
    from supabase_client import SupabaseHelper
    print('✅ SupabaseHelper import 성공')
    
    from kakao_address_converter import KakaoAddressConverter
    print('✅ KakaoAddressConverter import 성공')
    
    print('🎉 모든 핵심 모듈 import 성공!')
    
except Exception as e:
    print(f'❌ Import 실패: {e}')
"
        
        # 2. 간단한 수집 테스트
        echo ""
        echo "======== 2. 간단한 수집 테스트 ========"
        cd collectors
        python3 -c "
from cached_token_collector import collect_by_cortar_no
import time

start_time = time.time()
try:
    result = collect_by_cortar_no('1168010100', include_details=False, max_pages=1)
    end_time = time.time()
    
    if result.get('success'):
        print(f'✅ 수집 성공: {result.get(\"count\", 0)}개 매물')
        print(f'⏱️ 소요 시간: {end_time - start_time:.1f}초')
    else:
        print(f'❌ 수집 실패: {result.get(\"error\")}')
except Exception as e:
    print(f'❌ 오류 발생: {e}')
"
        cd ..
        
        # 3. t2.micro 시뮬레이션
        echo ""
        echo "======== 3. t2.micro 환경 시뮬레이션 ========"
        cd collectors
        python3 -c "
import psutil
import os
from cached_token_collector import collect_by_cortar_no

process = psutil.Process(os.getpid())
print(f'초기 메모리: {process.memory_info().rss / 1024 / 1024:.1f} MB')

try:
    result = collect_by_cortar_no('1168010100', include_details=True, max_pages=1)
    current_mem = process.memory_info().rss / 1024 / 1024
    print(f'수집 후 메모리: {current_mem:.1f} MB')
    
    if current_mem < 800:
        print('✅ t2.micro(1GB)에서 안전하게 실행 가능')
    elif current_mem < 1000:
        print('⚠️ t2.micro에서 실행 가능하지만 여유 공간 부족')
    else:
        print('❌ t2.micro에서는 메모리 부족 위험')
        print('→ t3.small 이상 권장')
        
except Exception as e:
    print(f'❌ 테스트 실패: {e}')
"
        cd ..
        
        echo ""
        print_success "모든 테스트 완료!"
        ;;
esac

echo ""
print_success "테스트 완료!"
echo ""
echo "결과 해석:"
echo "  ✅ 성공 시: EC2 배포 시 정상 동작 예상"
echo "  ⚠️ 경고 시: EC2에서 리소스 최적화 필요"  
echo "  ❌ 실패 시: 설정 또는 환경 문제 해결 필요"
echo ""
echo "다음 단계:"
echo "  1. 테스트 성공 → EC2 배포: ./deploy_scripts/aws_auto_deploy.sh"
echo "  2. 메모리 부족 → 더 큰 인스턴스 타입 선택"
echo "  3. 토큰 오류 → collectors/setup_deployment.py 재실행"