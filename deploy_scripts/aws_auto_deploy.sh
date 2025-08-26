#!/bin/bash
# AWS EC2 자동 생성 및 배포 스크립트

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

# 설정 변수
PROJECT_NAME="naver-land-collector-v2"
KEY_NAME="${PROJECT_NAME}-key"
SECURITY_GROUP="${PROJECT_NAME}-sg"
INSTANCE_NAME="${PROJECT_NAME}"
REGION="ap-northeast-2"  # 서울 리전

# 인스턴스 타입 선택 (무료 티어 or 권장)
echo "========================================="
echo "     AWS EC2 자동 배포 스크립트"
echo "========================================="
echo ""
echo "인스턴스 타입을 선택하세요:"
echo "1) t2.micro (무료 티어 - 1GB RAM) - 기본 수집 가능"
echo "2) t3.small (2GB RAM) - 안정적 수집 권장"
echo "3) t3.medium (4GB RAM) - 대량 수집용"
read -p "선택 [1-3] (기본값: 1): " choice
choice=${choice:-1}

case $choice in
    1) INSTANCE_TYPE="t2.micro" ;;
    2) INSTANCE_TYPE="t3.small" ;;
    3) INSTANCE_TYPE="t3.medium" ;;
    *) INSTANCE_TYPE="t2.micro" ;;
esac

print_step "선택된 인스턴스 타입: $INSTANCE_TYPE"

# 1. AWS CLI 설치 확인
print_step "AWS CLI 확인 중..."
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI가 설치되어 있지 않습니다."
    echo "설치 방법: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# 2. AWS 자격 증명 확인
print_step "AWS 자격 증명 확인 중..."
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS 자격 증명이 설정되지 않았습니다."
    echo ""
    echo "다음 명령어를 실행하여 AWS CLI를 설정하세요:"
    echo "  aws configure"
    echo ""
    echo "필요한 정보:"
    echo "  - AWS Access Key ID"
    echo "  - AWS Secret Access Key"
    echo "  - Default region: ap-northeast-2"
    echo "  - Output format: json"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS 계정 확인: $AWS_ACCOUNT_ID"

# 3. 키페어 생성 또는 확인
print_step "SSH 키페어 설정 중..."
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"

if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$REGION" &> /dev/null; then
    print_warning "키페어 '$KEY_NAME'가 이미 존재합니다."
    if [ ! -f "$KEY_PATH" ]; then
        print_error "로컬 키 파일이 없습니다: $KEY_PATH"
        echo "기존 키를 삭제하고 새로 생성하시겠습니까? (y/N)"
        read -r RECREATE_KEY
        if [[ "$RECREATE_KEY" =~ ^[Yy]$ ]]; then
            aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION"
            aws ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text --region "$REGION" > "$KEY_PATH"
            chmod 400 "$KEY_PATH"
            print_success "새 키페어 생성 완료: $KEY_PATH"
        else
            exit 1
        fi
    fi
else
    aws ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text --region "$REGION" > "$KEY_PATH"
    chmod 400 "$KEY_PATH"
    print_success "키페어 생성 완료: $KEY_PATH"
fi

# 4. 보안 그룹 생성
print_step "보안 그룹 설정 중..."

# 기본 VPC ID 가져오기
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region "$REGION")

# 보안 그룹 확인 또는 생성
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SECURITY_GROUP" --query "SecurityGroups[0].GroupId" --output text --region "$REGION" 2>/dev/null || echo "")

if [ -z "$SG_ID" ] || [ "$SG_ID" = "None" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP" \
        --description "Security group for Naver Land Collector" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' \
        --output text \
        --region "$REGION")
    
    # SSH 접근 허용 (현재 IP만)
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 22 \
        --cidr "${MY_IP}/32" \
        --region "$REGION"
    
    print_success "보안 그룹 생성 완료: $SG_ID (SSH from $MY_IP)"
else
    print_warning "보안 그룹이 이미 존재합니다: $SG_ID"
fi

# 5. 최신 Ubuntu AMI 찾기
print_step "Ubuntu 22.04 AMI 찾는 중..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text \
    --region "$REGION")

print_success "AMI ID: $AMI_ID"

# 6. EC2 인스턴스 생성
print_step "EC2 인스턴스 생성 중..."

# User data 스크립트 (초기 설정)
USER_DATA=$(cat <<'EOF'
#!/bin/bash
# 시스템 업데이트
apt-get update
apt-get upgrade -y

# Python 및 필수 패키지 설치
apt-get install -y python3-pip python3-venv git curl wget

# Playwright 의존성 설치
apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxrandr2 libgbm1 libxcb1 libxkbcommon0 \
    libpango-1.0-0 libcairo2 libasound2

# 프로젝트 디렉토리 생성
mkdir -p /home/ubuntu/naver_land
chown -R ubuntu:ubuntu /home/ubuntu/naver_land
EOF
)

# 인스턴스 생성
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region "$REGION")

print_success "EC2 인스턴스 생성 시작: $INSTANCE_ID"

# 7. 인스턴스가 실행될 때까지 대기
print_step "인스턴스 시작 대기 중... (약 1-2분)"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

# Public IP 가져오기
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region "$REGION")

print_success "인스턴스 실행 중: $PUBLIC_IP"

# 8. SSH 연결 가능할 때까지 대기
print_step "SSH 연결 대기 중... (약 30초)"
sleep 30

MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@"$PUBLIC_IP" "echo 'SSH 연결 성공'" &> /dev/null; then
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "연결 시도 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "SSH 연결 실패"
    exit 1
fi

print_success "SSH 연결 성공"

# 9. EC2 설정 파일 업데이트
print_step "배포 스크립트 설정 업데이트 중..."

# sync_to_ec2.sh 업데이트
sed -i "s|EC2_HOST=\".*\"|EC2_HOST=\"$PUBLIC_IP\"|" deploy_scripts/sync_to_ec2.sh
sed -i "s|EC2_USER=\".*\"|EC2_USER=\"ubuntu\"|" deploy_scripts/sync_to_ec2.sh
sed -i "s|EC2_KEY=\".*\"|EC2_KEY=\"$KEY_PATH\"|" deploy_scripts/sync_to_ec2.sh

# remote_ec2_commands.sh 업데이트
sed -i "s|EC2_HOST=\".*\"|EC2_HOST=\"$PUBLIC_IP\"|" deploy_scripts/remote_ec2_commands.sh
sed -i "s|EC2_USER=\".*\"|EC2_USER=\"ubuntu\"|" deploy_scripts/remote_ec2_commands.sh
sed -i "s|EC2_KEY=\".*\"|EC2_KEY=\"$KEY_PATH\"|" deploy_scripts/remote_ec2_commands.sh

print_success "스크립트 설정 완료"

# 10. 자동 배포 시작
print_step "코드 배포 시작..."

# 스크립트 실행 권한
chmod +x deploy_scripts/sync_to_ec2.sh deploy_scripts/remote_ec2_commands.sh

# 코드 동기화
./deploy_scripts/sync_to_ec2.sh

# 환경 설정
./deploy_scripts/remote_ec2_commands.sh setup

# 11. 결과 출력
echo ""
echo "========================================="
echo "         🎉 배포 완료! 🎉"
echo "========================================="
echo ""
echo "EC2 정보:"
echo "  - Instance ID: $INSTANCE_ID"
echo "  - Public IP: $PUBLIC_IP"
echo "  - Instance Type: $INSTANCE_TYPE"
echo "  - Key Path: $KEY_PATH"
echo ""
echo "다음 단계:"
echo "  1. API 키 설정:"
echo "     ./deploy_scripts/remote_ec2_commands.sh api"
echo ""
echo "  2. 테스트 실행:"
echo "     ./deploy_scripts/remote_ec2_commands.sh test"
echo ""
echo "  3. SSH 접속:"
echo "     ssh -i $KEY_PATH ubuntu@$PUBLIC_IP"
echo ""
echo "  4. 인스턴스 종료 (비용 절감):"
echo "     aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION"
echo ""
echo "  5. 인스턴스 삭제:"
echo "     ./deploy_scripts/aws_cleanup.sh"
echo ""

# EC2 정보 저장
cat > ec2_info.json <<EOF
{
  "instance_id": "$INSTANCE_ID",
  "public_ip": "$PUBLIC_IP",
  "key_path": "$KEY_PATH",
  "region": "$REGION",
  "instance_type": "$INSTANCE_TYPE",
  "security_group_id": "$SG_ID"
}
EOF

print_success "EC2 정보가 ec2_info.json에 저장되었습니다"