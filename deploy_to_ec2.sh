#!/bin/bash

# 네이버 부동산 수집기 v2.0 EC2 배포 스크립트

set -e  # 오류 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# EC2 정보 (사용자가 설정해야 함)
EC2_HOST=""
EC2_USER="ubuntu"
EC2_KEY_PATH=""
PROJECT_NAME="naver_land"
REMOTE_PATH="/home/ubuntu/${PROJECT_NAME}"

# 파라미터 체크
if [ -z "$EC2_HOST" ] || [ -z "$EC2_KEY_PATH" ]; then
    log_error "EC2_HOST와 EC2_KEY_PATH를 설정해주세요."
    log_info "스크립트 상단에서 다음 변수들을 설정하세요:"
    log_info "  EC2_HOST=\"your-ec2-ip-address\""
    log_info "  EC2_KEY_PATH=\"/path/to/your/key.pem\""
    exit 1
fi

# SSH 연결 테스트
log_info "EC2 연결 테스트 중..."
if ! ssh -i "$EC2_KEY_PATH" -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'Connected successfully'" >/dev/null 2>&1; then
    log_error "EC2 연결 실패. HOST, KEY_PATH, 보안그룹 설정을 확인해주세요."
    exit 1
fi
log_info "EC2 연결 성공"

# 프로젝트 파일 압축 (불필요한 파일 제외)
log_info "프로젝트 파일 압축 중..."
tar -czf naver_land_deploy.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='test' \
    --exclude='*.tar.gz' \
    .

# EC2로 파일 전송
log_info "파일을 EC2로 전송 중..."
scp -i "$EC2_KEY_PATH" naver_land_deploy.tar.gz "$EC2_USER@$EC2_HOST:/tmp/"

# EC2에서 설치 및 설정
log_info "EC2에서 환경 설정 중..."
ssh -i "$EC2_KEY_PATH" "$EC2_USER@$EC2_HOST" << 'EOF'
    # 색상 정의
    GREEN='\033[0;32m'
    NC='\033[0m'
    
    log_info() {
        echo -e "${GREEN}[EC2-INFO]${NC} $1"
    }
    
    log_info "Python3 및 pip 설치 확인"
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
    
    log_info "프로젝트 디렉토리 생성"
    mkdir -p ~/naver_land
    cd ~/naver_land
    
    log_info "기존 파일 백업 및 새 파일 압축 해제"
    if [ -d "backup" ]; then
        rm -rf backup_old
        mv backup backup_old
    fi
    mkdir -p backup
    if [ -f "main.py" ]; then
        cp -r . backup/ 2>/dev/null || true
    fi
    
    tar -xzf /tmp/naver_land_deploy.tar.gz
    rm /tmp/naver_land_deploy.tar.gz
    
    log_info "가상환경 생성 및 활성화"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    
    log_info "Python 의존성 설치"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Playwright 브라우저 설치
    log_info "Playwright 브라우저 설치"
    playwright install chromium
    playwright install-deps
    
    log_info "실행 권한 설정"
    chmod +x main.py
    
    log_info "환경변수 파일 확인"
    if [ ! -f ".env" ]; then
        echo "경고: .env 파일이 없습니다. 환경변수를 설정해주세요."
    fi
    
    log_info "배포 완료!"
    echo "수집기 실행 예시:"
    echo "  cd ~/naver_land"
    echo "  source venv/bin/activate"
    echo "  python main.py --area 1168010700 --max-articles 10"
EOF

# 로컬 압축 파일 정리
rm naver_land_deploy.tar.gz

log_info "배포 완료!"
log_info "EC2 접속: ssh -i $EC2_KEY_PATH $EC2_USER@$EC2_HOST"
log_info "프로젝트 디렉토리: $REMOTE_PATH"