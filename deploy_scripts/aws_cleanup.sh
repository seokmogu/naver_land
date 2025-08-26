#!/bin/bash
# AWS EC2 리소스 정리 스크립트

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
echo "     AWS EC2 리소스 정리 스크립트"
echo "========================================="
echo ""

# EC2 정보 파일 확인
if [ ! -f "ec2_info.json" ]; then
    print_error "ec2_info.json 파일이 없습니다."
    echo "aws_auto_deploy.sh를 먼저 실행하세요."
    exit 1
fi

# EC2 정보 읽기
INSTANCE_ID=$(jq -r '.instance_id' ec2_info.json)
PUBLIC_IP=$(jq -r '.public_ip' ec2_info.json)
KEY_PATH=$(jq -r '.key_path' ec2_info.json)
REGION=$(jq -r '.region' ec2_info.json)
SECURITY_GROUP_ID=$(jq -r '.security_group_id' ec2_info.json)

echo "삭제할 리소스:"
echo "  - Instance ID: $INSTANCE_ID"
echo "  - Public IP: $PUBLIC_IP"
echo "  - Security Group: $SECURITY_GROUP_ID"
echo "  - Key Pair: $(basename "$KEY_PATH" .pem)"
echo ""

read -p "정말로 모든 리소스를 삭제하시겠습니까? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "취소되었습니다."
    exit 0
fi

# 1. EC2 인스턴스 종료
print_step "EC2 인스턴스 종료 중..."
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$REGION" > /dev/null
print_success "인스턴스 종료 요청 완료"

# 2. 인스턴스 종료 대기
print_step "인스턴스 종료 대기 중... (약 1-2분)"
aws ec2 wait instance-terminated --instance-ids "$INSTANCE_ID" --region "$REGION"
print_success "인스턴스 종료 완료"

# 3. 키페어 삭제
KEY_NAME=$(basename "$KEY_PATH" .pem)
print_step "키페어 삭제 중: $KEY_NAME"
aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION"
if [ -f "$KEY_PATH" ]; then
    rm -f "$KEY_PATH"
    print_success "로컬 키 파일 삭제 완료"
fi

# 4. 보안 그룹 삭제
print_step "보안 그룹 삭제 중..."
# 잠시 대기 (ENI 해제 시간)
sleep 10
aws ec2 delete-security-group --group-id "$SECURITY_GROUP_ID" --region "$REGION" 2>/dev/null || {
    print_warning "보안 그룹 삭제 실패 (아직 사용 중일 수 있음)"
    echo "나중에 수동으로 삭제하세요:"
    echo "aws ec2 delete-security-group --group-id $SECURITY_GROUP_ID --region $REGION"
}

# 5. 설정 파일 초기화
print_step "설정 파일 초기화 중..."

# sync_to_ec2.sh 초기화
sed -i 's|EC2_HOST=".*"|EC2_HOST="your-ec2-public-ip"|' sync_to_ec2.sh
sed -i 's|EC2_USER=".*"|EC2_USER="ubuntu"|' sync_to_ec2.sh
sed -i 's|EC2_KEY=".*"|EC2_KEY="~/.ssh/your-ec2-key.pem"|' sync_to_ec2.sh

# remote_ec2_commands.sh 초기화
sed -i 's|EC2_HOST=".*"|EC2_HOST="your-ec2-public-ip"|' remote_ec2_commands.sh
sed -i 's|EC2_USER=".*"|EC2_USER="ubuntu"|' remote_ec2_commands.sh
sed -i 's|EC2_KEY=".*"|EC2_KEY="~/.ssh/your-ec2-key.pem"|' remote_ec2_commands.sh

# 6. EC2 정보 파일 백업 및 삭제
mv ec2_info.json "ec2_info_deleted_$(date +%Y%m%d_%H%M%S).json.bak"

print_success "모든 리소스가 정리되었습니다!"
echo ""
echo "백업 파일: ec2_info_deleted_*.json.bak"