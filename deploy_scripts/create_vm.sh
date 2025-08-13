#!/bin/bash
# GCP Compute Engine VM 생성 스크립트

set -e

echo "🖥️ GCP VM 인스턴스 생성 시작"
echo "==============================="

# 설정 변수
PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"
MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
BOOT_DISK_SIZE="30GB"
BOOT_DISK_TYPE="pd-standard"

# 1. 프로젝트 설정
echo "🔧 프로젝트 설정: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# 프로젝트 존재 확인
if ! gcloud projects describe "$PROJECT_ID" --quiet &>/dev/null; then
    echo "❌ 오류: 프로젝트 '$PROJECT_ID'가 존재하지 않거나 접근할 수 없습니다."
    echo "📋 사용 가능한 프로젝트 목록:"
    gcloud projects list --format="table(projectId,name,projectNumber)"
    exit 1
fi

echo "📋 배포 설정:"
echo "  프로젝트: $PROJECT_ID"
echo "  인스턴스명: $INSTANCE_NAME"
echo "  지역: $ZONE"
echo "  머신타입: $MACHINE_TYPE (무료 티어)"
echo "  디스크: $BOOT_DISK_SIZE"

# 2. 필요한 API 활성화
echo ""
echo "🔌 필요한 API 활성화 중..."
gcloud services enable compute.googleapis.com

# 3. 방화벽 규칙 생성 (HTTP/HTTPS) - 프로젝트 ID 명시
echo ""
echo "🔥 방화벽 규칙 확인 중..."
if ! gcloud compute firewall-rules describe default-allow-http --project="$PROJECT_ID" --quiet &>/dev/null; then
    gcloud compute firewall-rules create default-allow-http \
        --project="$PROJECT_ID" \
        --allow tcp:80 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow HTTP traffic"
fi

if ! gcloud compute firewall-rules describe default-allow-https --project="$PROJECT_ID" --quiet &>/dev/null; then
    gcloud compute firewall-rules create default-allow-https \
        --project="$PROJECT_ID" \
        --allow tcp:443 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow HTTPS traffic"
fi

# 4. startup 스크립트 생성
echo ""
echo "📝 Startup 스크립트 생성 중..."
cat > /tmp/startup-script.sh << 'EOF'
#!/bin/bash
# VM 시작시 자동 실행되는 스크립트

# 로그 파일 설정
exec > >(tee -a /var/log/startup-script.log)
exec 2>&1

echo "$(date): Startup script 시작"

# 시스템 업데이트
apt-get update
apt-get upgrade -y

# 필수 패키지 설치
apt-get install -y python3.11 python3.11-pip python3.11-dev python3.11-venv
apt-get install -y git curl wget unzip cron

# Playwright 의존성 설치
apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgtk-3-0 libatspi2.0-0 libxrandr2 libasound2 \
    libxdamage1 libxss1 libgconf-2-4

# Docker 설치
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker 사용자 권한 설정
usermod -aG docker $(ls /home | head -1)

# 스왑 메모리 설정 (무료티어 1GB RAM 보완)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab

# 프로젝트 클론을 위한 준비 (사용자가 나중에 수동으로 실행)
mkdir -p /home/$(ls /home | head -1)/setup
cat > /home/$(ls /home | head -1)/setup/clone_project.sh << 'INNER_EOF'
#!/bin/bash
# 프로젝트 클론 및 설정 스크립트
REPO_URL="https://github.com/seokmogu/naver_land.git"
echo "GitHub 저장소 클론 중: $REPO_URL"

git clone "$REPO_URL" ~/naver_land
cd ~/naver_land
chmod +x deploy_scripts/*.sh
./deploy_scripts/setup_project.sh
INNER_EOF

chmod +x /home/$(ls /home | head -1)/setup/clone_project.sh

echo "$(date): Startup script 완료"
EOF

# 5. VM 인스턴스 생성
echo ""
echo "🚀 VM 인스턴스 생성 중..."
gcloud compute instances create "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --network-tier=PREMIUM \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=http-server,https-server \
    --create-disk=auto-delete=yes,boot=yes,device-name="$INSTANCE_NAME",image=projects/"$IMAGE_PROJECT"/global/images/family/"$IMAGE_FAMILY",mode=rw,size="$BOOT_DISK_SIZE",type=projects/"$PROJECT_ID"/zones/"$ZONE"/diskTypes/"$BOOT_DISK_TYPE" \
    --metadata-from-file startup-script=/tmp/startup-script.sh \
    --reservation-affinity=any

# 6. VM 상태 확인
echo ""
echo "⏳ VM 부팅 대기 중..."
sleep 30

# VM 정보 출력
echo ""
echo "✅ VM 생성 완료!"
echo "==================="
gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="table(name,status,machineType.basename(),zone.basename())"

# 외부 IP 주소 확인
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo ""
echo "🌐 외부 IP 주소: $EXTERNAL_IP"

# SSH 접속 명령어 안내
echo ""
echo "🔑 SSH 접속 방법:"
echo "gcloud compute ssh --zone=\"$ZONE\" \"$INSTANCE_NAME\" --project=\"$PROJECT_ID\""
echo ""
echo "또는:"
echo "ssh -i ~/.ssh/google_compute_engine $(whoami)@$EXTERNAL_IP"

# 정리
rm -f /tmp/startup-script.sh

echo ""
echo "📋 다음 단계:"
echo "1. SSH로 VM에 접속"
echo "2. ~/setup/clone_project.sh 실행하여 프로젝트 클론"
echo "3. API 키 설정: cd ~/naver_land/collectors && python3 setup_deployment.py"
echo "4. 자동 스케줄링 설정: cd ~/naver_land && ./deploy_scripts/setup_cron.sh"