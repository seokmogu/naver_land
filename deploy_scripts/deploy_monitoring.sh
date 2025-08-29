#!/bin/bash
# 네이버 수집 모니터링 도구 AWS EC2 배포 스크립트

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

# EC2 정보 파일 확인
check_ec2_info() {
    if [ ! -f "ec2_info.json" ]; then
        print_error "ec2_info.json 파일이 없습니다."
        echo "aws_auto_deploy.sh를 먼저 실행하세요."
        exit 1
    fi
    
    INSTANCE_ID=$(jq -r '.instance_id' ec2_info.json)
    PUBLIC_IP=$(jq -r '.public_ip' ec2_info.json)
    KEY_PATH=$(jq -r '.key_path' ec2_info.json)
    REGION=$(jq -r '.region' ec2_info.json)
}

# 인스턴스 상태 확인
get_instance_state() {
    aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text \
        --region "$REGION" 2>/dev/null || echo "terminated"
}

# 모니터링 도구 배포
deploy_monitoring_tools() {
    print_step "모니터링 도구 EC2 배포 시작..."
    
    # 1. 모니터링 파일들 EC2로 복사
    print_step "모니터링 파일들 EC2로 복사 중..."
    
    scp -i "$KEY_PATH" -o StrictHostKeyChecking=no \
        ../collectors/live_monitor.py \
        ../collectors/progress_logger.py \
        ubuntu@${PUBLIC_IP}:/home/ubuntu/naver_land/collectors/
    
    print_success "모니터링 파일 복사 완료"
    
    # 2. EC2에서 필요한 패키지 설치
    print_step "EC2에서 필요한 패키지 설치 중..."
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@${PUBLIC_IP} << 'EOF'
# 파이썬 패키지 업데이트
sudo apt update
sudo apt install -y python3-pip htop

# 필요한 파이썬 패키지 설치
pip3 install --upgrade pip
pip3 install fastapi uvicorn websockets psutil

# 권한 설정
chmod +x /home/ubuntu/naver_land/collectors/*.py

echo "✅ 패키지 설치 완료"
EOF
    
    print_success "패키지 설치 완료"
    
    # 3. 모니터링 서비스 스크립트 생성
    print_step "모니터링 서비스 스크립트 생성 중..."
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@${PUBLIC_IP} << 'EOF'
# 모니터링 디렉토리 생성
mkdir -p /home/ubuntu/naver_land/monitoring

# 웹 대시보드 서비스 스크립트 생성
cat > /home/ubuntu/naver_land/monitoring/start_dashboard.sh << 'DASHBOARD_EOF'
#!/bin/bash
# 웹 대시보드 시작 스크립트

cd /home/ubuntu/naver_land/collectors

echo "🌐 웹 대시보드 시작 중..."
echo "📱 브라우저에서 http://$(curl -s http://checkip.amazonaws.com):8000 으로 접속하세요"

# 백그라운드로 실행
nohup python3 live_monitor.py > /home/ubuntu/naver_land/logs/dashboard.log 2>&1 &
echo $! > /home/ubuntu/naver_land/monitoring/dashboard.pid

echo "✅ 웹 대시보드 시작됨 (PID: $(cat /home/ubuntu/naver_land/monitoring/dashboard.pid))"
echo "📄 로그: /home/ubuntu/naver_land/logs/dashboard.log"
DASHBOARD_EOF

# CLI 모니터링 시작 스크립트 생성
cat > /home/ubuntu/naver_land/monitoring/start_cli_monitor.sh << 'CLI_EOF'
#!/bin/bash
# CLI 모니터링 시작 스크립트

cd /home/ubuntu/naver_land/collectors

echo "🖥️ CLI 라이브 모니터링 시작..."
echo "Ctrl+C로 종료 가능"

python3 live_monitor.py
CLI_EOF

# 빠른 상태 확인 스크립트 생성
cat > /home/ubuntu/naver_land/monitoring/quick_check.sh << 'QUICK_EOF'
#!/bin/bash
# 빠른 상태 확인 스크립트

cd /home/ubuntu/naver_land/collectors
python3 quick_status.py
QUICK_EOF

# 모니터링 중지 스크립트 생성
cat > /home/ubuntu/naver_land/monitoring/stop_monitoring.sh << 'STOP_EOF'
#!/bin/bash
# 모니터링 서비스 중지 스크립트

echo "🛑 모니터링 서비스 중지 중..."

# 웹 대시보드 중지
if [ -f /home/ubuntu/naver_land/monitoring/dashboard.pid ]; then
    PID=$(cat /home/ubuntu/naver_land/monitoring/dashboard.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ 웹 대시보드 중지됨 (PID: $PID)"
    else
        echo "⚠️ 웹 대시보드가 이미 중지되었습니다"
    fi
    rm -f /home/ubuntu/naver_land/monitoring/dashboard.pid
fi

# 모든 모니터링 프로세스 중지
pkill -f "live_monitor.py" 2>/dev/null && echo "✅ 라이브 모니터 프로세스 중지됨"
pkill -f "live_monitor.py" 2>/dev/null && echo "✅ CLI 모니터 프로세스 중지됨"

echo "🎯 모든 모니터링 서비스 중지 완료"
STOP_EOF

# 실행 권한 부여
chmod +x /home/ubuntu/naver_land/monitoring/*.sh

echo "✅ 모니터링 서비스 스크립트 생성 완료"
EOF
    
    print_success "모니터링 서비스 스크립트 생성 완료"
    
    # 4. 방화벽 설정 (포트 8000 오픈)
    print_step "방화벽 설정 (포트 8000 오픈) 중..."
    
    # Security Group에 웹 대시보드 포트 추가
    aws ec2 authorize-security-group-ingress \
        --group-id $(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text --region "$REGION") \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" 2>/dev/null || print_warning "포트 8000이 이미 열려있거나 오류 발생"
    
    print_success "방화벽 설정 완료"
}

# 모니터링 도구 사용법 안내
show_usage_guide() {
    print_step "모니터링 도구 사용법 안내"
    
    echo ""
    echo "🎯 배포된 모니터링 도구들:"
    echo ""
    echo "1. 📊 빠른 상태 확인:"
    echo "   ssh -i $KEY_PATH ubuntu@${PUBLIC_IP}"
    echo "   ./naver_land/monitoring/quick_check.sh"
    echo ""
    echo "2. 🖥️ CLI 라이브 모니터링:"
    echo "   ssh -i $KEY_PATH ubuntu@${PUBLIC_IP}"
    echo "   ./naver_land/monitoring/start_cli_monitor.sh"
    echo ""
    echo "3. 🌐 웹 대시보드:"
    echo "   ./naver_land/monitoring/start_dashboard.sh"
    echo "   브라우저: http://${PUBLIC_IP}:8000"
    echo ""
    echo "4. 🛑 모니터링 중지:"
    echo "   ./naver_land/monitoring/stop_monitoring.sh"
    echo ""
    echo "📁 주요 경로:"
    echo "   - 설정: /home/ubuntu/naver_land/collectors/config.json"
    echo "   - 로그: /home/ubuntu/naver_land/logs/"
    echo "   - 스크립트: /home/ubuntu/naver_land/monitoring/"
    echo ""
    
    # 웹 대시보드 자동 시작 여부 확인
    read -p "🚀 웹 대시보드를 지금 시작하시겠습니까? (y/N): " start_dashboard
    
    if [[ "$start_dashboard" =~ ^[Yy]$ ]]; then
        print_step "웹 대시보드 시작 중..."
        
        ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ubuntu@${PUBLIC_IP} \
            "/home/ubuntu/naver_land/monitoring/start_dashboard.sh"
        
        print_success "웹 대시보드 시작됨!"
        echo ""
        echo "🌐 브라우저에서 접속: http://${PUBLIC_IP}:8000"
        echo "📊 실시간 수집 현황을 확인하세요!"
    fi
}

# 메인 실행
main() {
    print_step "네이버 수집 모니터링 도구 AWS EC2 배포"
    echo "================================================"
    
    # EC2 정보 확인
    check_ec2_info
    
    # 인스턴스 상태 확인
    STATE=$(get_instance_state)
    if [ "$STATE" != "running" ]; then
        print_error "EC2 인스턴스가 실행 중이 아닙니다 (상태: $STATE)"
        echo "먼저 인스턴스를 시작하세요: ./aws_manage_ec2.sh start"
        exit 1
    fi
    
    print_success "EC2 인스턴스 실행 중 확인됨 ($PUBLIC_IP)"
    
    # 모니터링 도구 배포
    deploy_monitoring_tools
    
    # 사용법 안내
    show_usage_guide
    
    print_success "모니터링 도구 배포 완료!"
}

# 스크립트 실행
main "$@"