#!/bin/bash
# AWS EC2 배포 테스트 스크립트

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

echo "========================================="
echo "    AWS EC2 배포 테스트 스크립트"
echo "========================================="
echo ""

# 1. EC2 설정 확인
print_step "EC2 설정 확인"
echo "다음 정보를 확인하세요:"
echo "  - EC2_HOST: EC2 인스턴스의 퍼블릭 IP 또는 도메인"
echo "  - EC2_USER: ubuntu (Ubuntu) 또는 ec2-user (Amazon Linux)"
echo "  - EC2_KEY: EC2 접속용 PEM 키 파일 경로"
echo ""

# 2. 필요한 파일 확인
print_step "필요한 파일 확인"

if [ -f "sync_to_ec2.sh" ]; then
    print_success "sync_to_ec2.sh 파일 존재"
else
    print_error "sync_to_ec2.sh 파일이 없습니다"
fi

if [ -f "remote_ec2_commands.sh" ]; then
    print_success "remote_ec2_commands.sh 파일 존재"
else
    print_error "remote_ec2_commands.sh 파일이 없습니다"
fi

# 3. 스크립트 실행 권한 설정
print_step "스크립트 실행 권한 설정"
chmod +x sync_to_ec2.sh remote_ec2_commands.sh test_ec2_deploy.sh
print_success "실행 권한 설정 완료"

# 4. EC2 설정 가이드
echo ""
echo "========================================="
echo "           EC2 설정 가이드"
echo "========================================="
echo ""
print_step "sync_to_ec2.sh 파일 수정"
echo "다음 변수들을 수정하세요:"
echo '  EC2_HOST="your-ec2-public-ip"'
echo '  EC2_USER="ubuntu"'
echo '  EC2_KEY="~/.ssh/your-ec2-key.pem"'
echo ""

print_step "remote_ec2_commands.sh 파일 수정"
echo "동일한 변수들을 수정하세요:"
echo '  EC2_HOST="your-ec2-public-ip"'
echo '  EC2_USER="ubuntu"'
echo '  EC2_KEY="~/.ssh/your-ec2-key.pem"'
echo ""

# 5. 사용 방법 안내
echo "========================================="
echo "           사용 방법"
echo "========================================="
echo ""
print_step "1. EC2 인스턴스 준비"
echo "  - Ubuntu 20.04 또는 22.04 권장"
echo "  - Python 3.8 이상 설치"
echo "  - 보안 그룹에서 SSH(22) 포트 열기"
echo ""

print_step "2. 초기 설정"
echo "  ./sync_to_ec2.sh         # 코드를 EC2로 동기화"
echo "  ./remote_ec2_commands.sh setup  # Python 환경 설정"
echo "  ./remote_ec2_commands.sh api    # API 키 설정"
echo ""

print_step "3. 테스트"
echo "  ./remote_ec2_commands.sh test-simple     # Import 테스트"
echo "  ./remote_ec2_commands.sh test-connection # DB 연결 테스트"
echo "  ./remote_ec2_commands.sh test           # 실제 수집 테스트"
echo ""

print_step "4. 운영"
echo "  ./remote_ec2_commands.sh cron    # 크론 스케줄 설정"
echo "  ./remote_ec2_commands.sh status  # 상태 확인"
echo "  ./remote_ec2_commands.sh logs    # 로그 확인"
echo ""

# 6. 체크리스트
echo "========================================="
echo "           배포 체크리스트"
echo "========================================="
echo ""
echo "[ ] EC2 인스턴스 생성 완료"
echo "[ ] SSH 키(.pem) 파일 준비"
echo "[ ] 보안 그룹 설정 (SSH 포트 22)"
echo "[ ] EC2에 Python 3.8+ 설치"
echo "[ ] sync_to_ec2.sh의 EC2 정보 수정"
echo "[ ] remote_ec2_commands.sh의 EC2 정보 수정"
echo "[ ] Supabase API 키 준비"
echo ""

print_success "테스트 스크립트 실행 완료!"
echo ""
echo "위 체크리스트를 확인한 후 배포를 시작하세요."