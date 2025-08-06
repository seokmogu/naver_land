#!/bin/bash
# 로컬에서 원격 VM 자동 설정 스크립트

set -e

echo "🔧 원격 VM 자동 설정 시작"
echo "========================="

# 설정 변수
PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

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

# 1. VM 상태 확인
print_step "1단계: VM 상태 확인"
if ! gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet &>/dev/null; then
    print_error "VM '$INSTANCE_NAME'이 존재하지 않습니다."
    echo "먼저 VM을 생성하세요: ./deploy_scripts/create_vm.sh"
    exit 1
fi

STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format="value(status)")
if [ "$STATUS" != "RUNNING" ]; then
    print_warning "VM이 중지되어 있습니다. 시작 중..."
    gcloud compute instances start "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID"
    echo "VM 부팅 대기 중..."
    sleep 30
fi

print_success "VM이 실행 중입니다"

# 2. 원격 설정 스크립트 생성
print_step "2단계: 원격 설정 스크립트 생성"
cat > /tmp/remote_vm_setup.sh << 'EOF'
#!/bin/bash
# VM에서 실행될 설정 스크립트

set -e

echo "🚀 VM 자동 설정 시작"

# 시스템 패키지 설치
echo "📦 시스템 업데이트 및 패키지 설치..."
sudo apt update -y

# Python 3 및 pip 설치 (Ubuntu 22.04 기본)
echo "🐍 Python 환경 설치..."
sudo apt install -y python3 python3-pip python3-venv python3-dev

# 기본 패키지 설치
sudo apt install -y git curl wget unzip cron

# Playwright 의존성 설치
echo "🎭 Playwright 의존성 설치..."
sudo apt install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgtk-3-0 libatspi2.0-0 libxrandr2 libasound2 \
    libxdamage1 libxss1 libgconf-2-4

# 기존 프로젝트 폴더 정리
if [ -d "$HOME/naver_land" ]; then
    echo "⚠️ 기존 프로젝트 폴더 삭제..."
    rm -rf ~/naver_land
fi

# 프로젝트 클론
echo "📁 프로젝트 클론..."
git clone https://github.com/seokmogu/naver_land.git ~/naver_land
cd ~/naver_land

# Python 가상환경 생성
echo "🐍 Python 환경 설정..."
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 설정 파일 준비
cd ~/naver_land/collectors
if [ ! -f config.json ]; then
    cp config.template.json config.json
fi

# 폴더 생성
mkdir -p results
mkdir -p ../logs

# 실행 권한 설정
chmod +x ../deploy_scripts/*.sh

echo "✅ 기본 설정 완료!"
echo ""
echo "다음 명령어들을 실행하세요:"
echo "1. API 키 설정: cd ~/naver_land/collectors && python3 setup_deployment.py"
echo "2. Cron 설정: cd ~/naver_land && ./deploy_scripts/setup_cron.sh"
echo "3. 테스트: cd ~/naver_land/collectors && source ../venv/bin/activate && python3 parallel_batch_collect_gangnam.py --max-workers 1"
EOF

chmod +x /tmp/remote_vm_setup.sh
print_success "원격 설정 스크립트 생성 완료"

# 3. 스크립트를 VM에 전송
print_step "3단계: 스크립트를 VM에 전송"
gcloud compute scp /tmp/remote_vm_setup.sh "$INSTANCE_NAME":~/remote_vm_setup.sh \
    --zone="$ZONE" --project="$PROJECT_ID"
print_success "스크립트 전송 완료"

# 4. 원격에서 스크립트 실행
print_step "4단계: 원격에서 설정 스크립트 실행"
echo "VM에서 자동 설정을 시작합니다. 시간이 걸릴 수 있습니다..."

gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="chmod +x ~/remote_vm_setup.sh && ~/remote_vm_setup.sh"

print_success "원격 설정 완료!"

# 5. 후속 작업 안내
print_step "5단계: 후속 작업 안내"
echo ""
echo "🎉 기본 설정이 완료되었습니다!"
echo ""
echo "이제 다음 작업을 진행하세요:"
echo ""
echo "1️⃣ API 키 설정 (대화형):"
echo "gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
echo "cd ~/naver_land/collectors && python3 setup_deployment.py"
echo ""
echo "2️⃣ 또는 로컬에서 원격 명령어 실행:"
echo "./deploy_scripts/remote_api_setup.sh"
echo ""
echo "3️⃣ Cron 스케줄링 설정:"
echo "./deploy_scripts/remote_cron_setup.sh"

# 정리
rm -f /tmp/remote_vm_setup.sh

print_success "원격 VM 자동 설정 완료! 🚀"