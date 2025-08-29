#!/bin/bash
# EC2에서 안전한 수집기 테스트 스크립트
# 단계별 안전성 검증

set -e  # 오류 발생시 중단

echo "🛡️ EC2 안전한 수집기 테스트 시작"
echo "==============================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

log_info "작업 디렉토리: $SCRIPT_DIR"

# 1. 사전 점검
echo ""
echo "1️⃣ 사전 점검"
echo "----------------------------------------"

# 필수 파일 확인
REQUIRED_FILES=(
    "emergency_recovery.py"
    "final_safe_collector.py"
    "completely_safe_collector.py"
    "json_to_db_converter.py"
    "supabase_client.py"
    "config.json"
)

log_info "필수 파일 존재 확인..."
for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        log_success "✓ $file"
    else
        log_error "✗ $file 파일이 없습니다"
        exit 1
    fi
done

# Python 환경 확인
log_info "Python 환경 확인..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "✓ $PYTHON_VERSION"
else
    log_error "Python3이 설치되지 않았습니다"
    exit 1
fi

# 의존성 확인
log_info "Python 패키지 확인..."
python3 -c "import requests, supabase, json, os" 2>/dev/null && log_success "✓ 필수 패키지 설치됨" || {
    log_error "필수 패키지가 없습니다. requirements.txt를 확인하세요"
    exit 1
}

# 2. 데이터베이스 상태 확인
echo ""
echo "2️⃣ 데이터베이스 상태 확인"
echo "----------------------------------------"

log_info "응급 복구 시스템으로 현재 상태 확인..."
python3 emergency_recovery.py || {
    log_error "데이터베이스 상태 확인 실패"
    exit 1
}

# 3. 안전한 수집 테스트 (테스트 모드)
echo ""
echo "3️⃣ 안전한 수집 테스트 (테스트 모드)"
echo "----------------------------------------"

TEST_REGION="1168010100"  # 강남구 신사동
log_info "테스트 지역: $TEST_REGION (강남구 신사동)"
log_info "DB 저장하지 않고 테스트만 실행..."

python3 final_safe_collector.py "$TEST_REGION" --max-pages 2 --test || {
    log_error "테스트 모드 수집 실패"
    exit 1
}

log_success "테스트 모드 수집 완료"

# 4. 품질 검증 후 실제 저장 테스트
echo ""
echo "4️⃣ 품질 검증 후 실제 저장 테스트"
echo "----------------------------------------"

read -p "품질이 충분하다면 실제 DB 저장을 테스트하시겠습니까? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "실제 DB 저장 테스트 시작..."
    log_warning "⚠️ 기존 매물은 삭제되지 않습니다 (안전 모드)"
    
    python3 final_safe_collector.py "$TEST_REGION" --max-pages 2 || {
        log_error "실제 저장 테스트 실패"
        exit 1
    }
    
    log_success "실제 저장 테스트 완료"
    
    # 5. 안전성 재확인
    echo ""
    echo "5️⃣ 안전성 재확인"
    echo "----------------------------------------"
    
    log_info "저장 후 데이터베이스 상태 재확인..."
    python3 emergency_recovery.py
    
else
    log_info "실제 저장 테스트를 건너뜁니다"
fi

# 6. 완료 요약
echo ""
echo "6️⃣ 테스트 완료 요약"
echo "----------------------------------------"

log_success "모든 테스트가 완료되었습니다!"
log_info "✅ 사전 점검 통과"
log_info "✅ 데이터베이스 연결 확인"
log_info "✅ 안전한 수집 테스트 통과"

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "✅ 실제 저장 테스트 통과"
    log_info "✅ 안전성 재확인 완료"
fi

echo ""
log_success "🎉 EC2 안전한 수집기 테스트 성공!"
echo ""
echo "다음 단계:"
echo "  1. 정기 수집을 위한 cron 설정"
echo "  2. 모니터링 시스템 구축"
echo "  3. 백업 및 복구 절차 수립"