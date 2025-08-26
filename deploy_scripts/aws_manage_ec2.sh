#!/bin/bash
# AWS EC2 관리 스크립트

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
    INSTANCE_TYPE=$(jq -r '.instance_type' ec2_info.json)
}

# 인스턴스 상태 확인
get_instance_state() {
    aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text \
        --region "$REGION" 2>/dev/null || echo "terminated"
}

# 새 Public IP 업데이트
update_public_ip() {
    NEW_IP=$(aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region "$REGION" 2>/dev/null || echo "")
    
    if [ -n "$NEW_IP" ] && [ "$NEW_IP" != "None" ]; then
        # ec2_info.json 업데이트
        jq ".public_ip = \"$NEW_IP\"" ec2_info.json > ec2_info_tmp.json && mv ec2_info_tmp.json ec2_info.json
        
        # 스크립트 업데이트
        sed -i "s|EC2_HOST=\".*\"|EC2_HOST=\"$NEW_IP\"|" sync_to_ec2.sh
        sed -i "s|EC2_HOST=\".*\"|EC2_HOST=\"$NEW_IP\"|" remote_ec2_commands.sh
        
        PUBLIC_IP=$NEW_IP
        print_success "Public IP 업데이트: $PUBLIC_IP"
    fi
}

# 비용 계산
calculate_cost() {
    local hours=$1
    case $INSTANCE_TYPE in
        "t2.micro")
            echo "무료 티어 (750시간/월 무료)"
            ;;
        "t3.small")
            cost=$(echo "scale=2; $hours * 0.0208" | bc)
            echo "\$$cost (시간당 \$0.0208)"
            ;;
        "t3.medium")
            cost=$(echo "scale=2; $hours * 0.0416" | bc)
            echo "\$$cost (시간당 \$0.0416)"
            ;;
        *)
            echo "비용 정보 없음"
            ;;
    esac
}

show_help() {
    echo "AWS EC2 관리 도구"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  status    - 인스턴스 상태 확인"
    echo "  start     - 인스턴스 시작"
    echo "  stop      - 인스턴스 중지 (비용 절감)"
    echo "  restart   - 인스턴스 재시작"
    echo "  ssh       - SSH 접속"
    echo "  info      - 상세 정보 확인"
    echo "  cost      - 예상 비용 계산"
    echo "  monitor   - 실시간 모니터링"
    echo ""
}

case "${1:-help}" in
    "status")
        check_ec2_info
        print_step "EC2 인스턴스 상태 확인"
        STATE=$(get_instance_state)
        
        case $STATE in
            "running")
                print_success "인스턴스 실행 중"
                echo "  - Instance ID: $INSTANCE_ID"
                echo "  - Public IP: $PUBLIC_IP"
                echo "  - Type: $INSTANCE_TYPE"
                
                # 실행 시간 확인
                LAUNCH_TIME=$(aws ec2 describe-instances \
                    --instance-ids "$INSTANCE_ID" \
                    --query 'Reservations[0].Instances[0].LaunchTime' \
                    --output text \
                    --region "$REGION")
                echo "  - 시작 시간: $LAUNCH_TIME"
                
                # 예상 비용
                HOURS=$(echo "scale=2; ($(date +%s) - $(date -d "$LAUNCH_TIME" +%s)) / 3600" | bc)
                echo "  - 실행 시간: ${HOURS}시간"
                echo "  - 예상 비용: $(calculate_cost $HOURS)"
                ;;
            "stopped")
                print_warning "인스턴스 중지됨"
                echo "  시작하려면: $0 start"
                ;;
            "terminated")
                print_error "인스턴스가 종료되었습니다"
                echo "  새로 생성하려면: ./aws_auto_deploy.sh"
                ;;
            *)
                print_warning "인스턴스 상태: $STATE"
                ;;
        esac
        ;;
    
    "start")
        check_ec2_info
        print_step "EC2 인스턴스 시작 중..."
        
        STATE=$(get_instance_state)
        if [ "$STATE" = "running" ]; then
            print_warning "인스턴스가 이미 실행 중입니다"
            exit 0
        fi
        
        aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" > /dev/null
        print_step "인스턴스 시작 대기 중... (약 30초)"
        aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
        
        update_public_ip
        print_success "인스턴스 시작 완료: $PUBLIC_IP"
        ;;
    
    "stop")
        check_ec2_info
        print_step "EC2 인스턴스 중지 중..."
        
        STATE=$(get_instance_state)
        if [ "$STATE" = "stopped" ]; then
            print_warning "인스턴스가 이미 중지되었습니다"
            exit 0
        fi
        
        # 실행 시간 및 비용 표시
        LAUNCH_TIME=$(aws ec2 describe-instances \
            --instance-ids "$INSTANCE_ID" \
            --query 'Reservations[0].Instances[0].LaunchTime' \
            --output text \
            --region "$REGION")
        HOURS=$(echo "scale=2; ($(date +%s) - $(date -d "$LAUNCH_TIME" +%s)) / 3600" | bc)
        
        echo "실행 시간: ${HOURS}시간"
        echo "예상 비용: $(calculate_cost $HOURS)"
        echo ""
        
        read -p "정말로 인스턴스를 중지하시겠습니까? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "취소되었습니다."
            exit 0
        fi
        
        aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$REGION" > /dev/null
        print_step "인스턴스 중지 대기 중..."
        aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID" --region "$REGION"
        print_success "인스턴스 중지 완료 (비용 절감 모드)"
        ;;
    
    "restart")
        check_ec2_info
        print_step "EC2 인스턴스 재시작 중..."
        aws ec2 reboot-instances --instance-ids "$INSTANCE_ID" --region "$REGION"
        print_success "재시작 요청 완료"
        
        sleep 30
        update_public_ip
        ;;
    
    "ssh")
        check_ec2_info
        STATE=$(get_instance_state)
        if [ "$STATE" != "running" ]; then
            print_error "인스턴스가 실행 중이 아닙니다 (상태: $STATE)"
            echo "먼저 시작하세요: $0 start"
            exit 1
        fi
        
        print_step "SSH 접속: ubuntu@$PUBLIC_IP"
        ssh -i "$KEY_PATH" ubuntu@"$PUBLIC_IP"
        ;;
    
    "info")
        check_ec2_info
        print_step "EC2 인스턴스 상세 정보"
        
        aws ec2 describe-instances \
            --instance-ids "$INSTANCE_ID" \
            --region "$REGION" \
            --output table
        ;;
    
    "cost")
        check_ec2_info
        print_step "예상 비용 계산"
        
        echo "인스턴스 타입: $INSTANCE_TYPE"
        echo ""
        echo "시간별 비용:"
        echo "  - 1시간: $(calculate_cost 1)"
        echo "  - 24시간: $(calculate_cost 24)"
        echo "  - 1주일 (168시간): $(calculate_cost 168)"
        echo "  - 1개월 (730시간): $(calculate_cost 730)"
        echo ""
        
        STATE=$(get_instance_state)
        if [ "$STATE" = "running" ]; then
            LAUNCH_TIME=$(aws ec2 describe-instances \
                --instance-ids "$INSTANCE_ID" \
                --query 'Reservations[0].Instances[0].LaunchTime' \
                --output text \
                --region "$REGION")
            HOURS=$(echo "scale=2; ($(date +%s) - $(date -d "$LAUNCH_TIME" +%s)) / 3600" | bc)
            echo "현재 실행 시간: ${HOURS}시간"
            echo "현재까지 예상 비용: $(calculate_cost $HOURS)"
        fi
        
        echo ""
        print_warning "비용 절약 팁:"
        echo "  - 사용하지 않을 때는 인스턴스를 중지하세요: $0 stop"
        echo "  - t2.micro는 월 750시간 무료입니다 (무료 티어)"
        ;;
    
    "monitor")
        check_ec2_info
        print_step "실시간 모니터링 (Ctrl+C로 종료)"
        
        while true; do
            clear
            echo "========================================="
            echo "     EC2 인스턴스 모니터링"
            echo "========================================="
            echo ""
            
            STATE=$(get_instance_state)
            echo "상태: $STATE"
            echo "Instance ID: $INSTANCE_ID"
            echo "Type: $INSTANCE_TYPE"
            
            if [ "$STATE" = "running" ]; then
                echo "Public IP: $PUBLIC_IP"
                
                # CPU 사용률
                CPU=$(aws cloudwatch get-metric-statistics \
                    --namespace AWS/EC2 \
                    --metric-name CPUUtilization \
                    --dimensions Name=InstanceId,Value="$INSTANCE_ID" \
                    --start-time "$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S)" \
                    --end-time "$(date -u +%Y-%m-%dT%H:%M:%S)" \
                    --period 300 \
                    --statistics Average \
                    --query 'Datapoints[0].Average' \
                    --output text \
                    --region "$REGION" 2>/dev/null || echo "N/A")
                
                echo "CPU 사용률: ${CPU}%"
            fi
            
            echo ""
            echo "업데이트: $(date)"
            sleep 10
        done
        ;;
    
    "help"|*)
        show_help
        ;;
esac