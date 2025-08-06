#!/bin/bash
# 원격에서 누락된 패키지 설치 스크립트

set -e

echo "📦 원격 패키지 설치 시작"
echo "========================"

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 업데이트된 requirements.txt를 VM에 전송
print_step "업데이트된 requirements.txt를 VM에 전송 중"
gcloud compute scp requirements.txt "$INSTANCE_NAME":~/naver_land/requirements.txt \
    --zone="$ZONE" --project="$PROJECT_ID"

# VM에서 패키지 설치 스크립트 생성
print_step "패키지 설치 스크립트 생성 중"
cat > /tmp/install_packages.sh << 'EOF'
#!/bin/bash
# VM에서 실행될 패키지 설치 스크립트

set -e

echo "🐍 Python 패키지 업데이트 시작"

# 프로젝트 디렉토리로 이동
cd ~/naver_land

# 가상환경 활성화
echo "가상환경 활성화 중..."
source venv/bin/activate

# pip 업그레이드
echo "pip 업그레이드 중..."
pip install --upgrade pip

# requirements.txt에서 패키지 설치
echo "requirements.txt에서 패키지 설치 중..."
pip install -r requirements.txt

# Playwright 브라우저 의존성 설치
echo "Playwright 브라우저 의존성 설치 중..."
# 시스템 의존성 직접 설치 (playwright install-deps 대신)
sudo apt-get update
sudo apt-get install -y libgbm1 libnss3 libxss1 libasound2 libxtst6 libxrandr2 libgtk-3-0 libxdamage1 libdrm2 libxkbcommon0 libatspi2.0-0

# Chromium 브라우저 설치
echo "Chromium 브라우저 설치 중..."
python3 -m playwright install chromium

# 설치된 패키지 확인
echo ""
echo "✅ 설치된 패키지 목록:"
pip list | grep -E "(supabase|requests|playwright|pandas)"

# supabase 설치 확인
echo ""
echo "🧪 supabase 모듈 테스트:"
python3 -c "
try:
    from supabase import create_client, Client
    print('✅ supabase 모듈 import 성공!')
except ImportError as e:
    print(f'❌ supabase 모듈 import 실패: {e}')
"

# Playwright 브라우저 테스트
echo ""
echo "🎭 Playwright 브라우저 테스트:"
python3 -c "
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()
    print('✅ Playwright 브라우저 테스트 성공!')
except Exception as e:
    print(f'❌ Playwright 브라우저 테스트 실패: {e}')
"

echo ""
echo "🎉 패키지 설치 완료!"
EOF

chmod +x /tmp/install_packages.sh

# 스크립트를 VM에 전송
print_step "패키지 설치 스크립트를 VM에 전송 중"
gcloud compute scp /tmp/install_packages.sh "$INSTANCE_NAME":~/install_packages.sh \
    --zone="$ZONE" --project="$PROJECT_ID"

# VM에서 패키지 설치 실행
print_step "VM에서 패키지 설치 실행 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="~/install_packages.sh && rm ~/install_packages.sh"

print_success "패키지 설치 완료!"

# 수집 스크립트 테스트
print_step "수집 스크립트 다시 테스트"
echo ""
echo "이제 daily_collection.sh를 다시 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo "🧪 daily_collection.sh 테스트 실행 중..."
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="~/naver_land/deploy_scripts/daily_collection.sh"
else
    echo "나중에 다음 명령어로 테스트할 수 있습니다:"
    echo "gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
    echo "~/naver_land/deploy_scripts/daily_collection.sh"
fi

# 정리
rm -f /tmp/install_packages.sh

print_success "원격 패키지 설치 완료! 🎉"