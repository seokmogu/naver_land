#!/bin/bash
# 전체 GCP 배포 자동화 스크립트

set -e

echo "🚀 네이버 부동산 수집기 GCP 전체 배포"
echo "====================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 1. gcloud CLI 확인 및 설치
print_step "1단계: Google Cloud CLI 확인"
if ! command -v gcloud &> /dev/null; then
    print_warning "gcloud CLI가 설치되지 않았습니다. 설치를 진행합니다..."
    chmod +x "$SCRIPT_DIR/install_gcloud.sh"
    "$SCRIPT_DIR/install_gcloud.sh"
else
    print_success "gcloud CLI가 이미 설치되어 있습니다."
    gcloud version
fi

# 2. 인증 확인
print_step "2단계: Google Cloud 인증 확인"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 | grep -q "@"; then
    print_warning "Google Cloud 인증이 필요합니다."
    echo "브라우저가 열리면 Google 계정으로 로그인하세요."
    gcloud auth login
else
    CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
    print_success "인증된 계정: $CURRENT_ACCOUNT"
fi

# 3. 프로젝트 설정
print_step "3단계: GCP 프로젝트 설정"
TARGET_PROJECT="gbd-match"

print_success "프로젝트 설정: $TARGET_PROJECT"
gcloud config set project "$TARGET_PROJECT"

# 프로젝트 존재 확인
if ! gcloud projects describe "$TARGET_PROJECT" --quiet &>/dev/null; then
    print_error "프로젝트 '$TARGET_PROJECT'가 존재하지 않거나 접근할 수 없습니다."
    echo "📋 사용 가능한 프로젝트 목록:"
    gcloud projects list --format="table(projectId,name,projectNumber)"
    exit 1
fi

FINAL_PROJECT="$TARGET_PROJECT"
print_success "사용할 프로젝트: $FINAL_PROJECT"

# 4. GitHub 저장소 설정
print_step "4단계: GitHub 저장소 준비"
GITHUB_REPO_URL="https://github.com/seokmogu/naver_land.git"
print_success "GitHub 저장소: $GITHUB_REPO_URL"

# 5. VM 생성
print_step "5단계: VM 인스턴스 생성"
chmod +x "$SCRIPT_DIR/create_vm.sh"
"$SCRIPT_DIR/create_vm.sh"

# 6. VM 접속 정보 출력
print_step "6단계: 배포 완료 안내"
ZONE="us-central1-a"
INSTANCE_NAME="naver-collector"

print_success "🎉 GCP 배포 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. VM에 SSH 접속:"
echo "   gcloud compute ssh --zone=\"$ZONE\" \"$INSTANCE_NAME\" --project=\"$FINAL_PROJECT\""
echo ""
echo "2. VM에서 프로젝트 설정:"
echo "   ~/setup/clone_project.sh"
echo "   # GitHub URL 입력: $GITHUB_REPO_URL"
echo ""
echo "3. API 키 설정:"
echo "   cd ~/naver_land/collectors"
echo "   python3 setup_deployment.py"
echo ""
echo "4. 자동 스케줄링 설정:"
echo "   cd ~/naver_land"
echo "   ./deploy_scripts/setup_cron.sh"
echo ""
echo "5. 수동 테스트:"
echo "   cd ~/naver_land/collectors"
echo "   source ../venv/bin/activate"
echo "   python3 parallel_batch_collect_gangnam.py --max-workers 2"

print_success "배포 스크립트 실행 완료! 🚀"