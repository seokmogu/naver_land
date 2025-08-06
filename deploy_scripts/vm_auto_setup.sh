#!/bin/bash
# VM에서 실행하는 완전 자동 배포 스크립트

set -e

echo "🚀 네이버 부동산 수집기 VM 자동 설정 시작"
echo "============================================"

# 색상 정의
RED='\033[0;31m'
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

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. 시스템 패키지 설치
print_step "1단계: 시스템 패키지 설치"
sudo apt update
sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
sudo apt install -y git curl wget unzip cron

# Playwright 의존성 설치
sudo apt install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgtk-3-0 libatspi2.0-0 libxrandr2 libasound2 \
    libxdamage1 libxss1 libgconf-2-4

print_success "시스템 패키지 설치 완료"

# 2. 프로젝트 클론
print_step "2단계: 프로젝트 클론"
if [ -d "~/naver_land" ]; then
    print_warning "기존 프로젝트 폴더가 있습니다. 삭제하고 새로 클론합니다."
    rm -rf ~/naver_land
fi

git clone https://github.com/seokmogu/naver_land.git ~/naver_land
cd ~/naver_land
print_success "프로젝트 클론 완료"

# 3. Python 가상환경 생성 및 패키지 설치
print_step "3단계: Python 환경 설정"
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

print_success "Python 환경 설정 완료"

# 4. 설정 파일 준비
print_step "4단계: 설정 파일 준비"
cd ~/naver_land/collectors

if [ ! -f config.json ]; then
    cp config.template.json config.json
    print_success "config.json 생성 완료"
else
    print_warning "config.json이 이미 존재합니다"
fi

# 결과 및 로그 폴더 생성
mkdir -p results
mkdir -p ../logs

print_success "폴더 구조 설정 완료"

# 5. 실행 권한 설정
chmod +x ../deploy_scripts/*.sh

# 6. API 키 설정 안내
print_step "5단계: API 키 설정"
echo ""
echo "이제 API 키를 설정해야 합니다:"
echo "python3 setup_deployment.py"
echo ""
echo "API 키 설정을 지금 하시겠습니까? (y/N):"
read -r SETUP_API

if [[ "$SETUP_API" =~ ^[Yy]$ ]]; then
    python3 setup_deployment.py
    print_success "API 키 설정 완료"
else
    print_warning "나중에 다음 명령어로 API 키를 설정하세요:"
    echo "cd ~/naver_land/collectors && python3 setup_deployment.py"
fi

# 7. Cron 자동 스케줄링 설정
print_step "6단계: 자동 스케줄링 설정"
cd ~/naver_land

echo "매일 자동 수집 스케줄을 설정하시겠습니까? (y/N):"
read -r SETUP_CRON

if [[ "$SETUP_CRON" =~ ^[Yy]$ ]]; then
    ./deploy_scripts/setup_cron.sh
    print_success "자동 스케줄링 설정 완료"
else
    print_warning "나중에 다음 명령어로 스케줄링을 설정하세요:"
    echo "cd ~/naver_land && ./deploy_scripts/setup_cron.sh"
fi

# 8. 테스트 실행 제안
print_step "7단계: 테스트 실행"
echo "수집 테스트를 실행하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    cd ~/naver_land/collectors
    source ../venv/bin/activate
    echo "테스트 수집 시작 (1개 워커, 소량 데이터)..."
    python3 parallel_batch_collect_gangnam.py --max-workers 1
    print_success "테스트 실행 완료"
else
    print_warning "나중에 다음 명령어로 테스트하세요:"
    echo "cd ~/naver_land/collectors"
    echo "source ../venv/bin/activate"
    echo "python3 parallel_batch_collect_gangnam.py --max-workers 1"
fi

# 9. 완료 안내
echo ""
echo "🎉 VM 자동 설정 완료!"
echo "===================="
echo ""
echo "📁 프로젝트 위치: ~/naver_land"
echo "⚙️ 설정 파일: ~/naver_land/collectors/config.json"
echo "📊 수집 결과: ~/naver_land/collectors/results/"
echo "📝 로그 파일: ~/naver_land/logs/"
echo ""
echo "🔄 일일 자동 수집 확인:"
echo "crontab -l"
echo ""
echo "🚀 수동 수집 실행:"
echo "cd ~/naver_land/collectors"
echo "source ../venv/bin/activate"
echo "python3 parallel_batch_collect_gangnam.py --max-workers 2"
echo ""
print_success "모든 설정이 완료되었습니다! 🎯"