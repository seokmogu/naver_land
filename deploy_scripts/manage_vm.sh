#!/bin/bash
# GCP VM 관리 스크립트

set -e

INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"
PROJECT_ID="gbd-match"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "================================"
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

# 도움말 출력
show_help() {
    echo "GCP VM 관리 도구"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  status    - VM 상태 확인"
    echo "  start     - VM 시작"
    echo "  stop      - VM 중지"
    echo "  restart   - VM 재시작"
    echo "  ssh       - VM에 SSH 접속"
    echo "  logs      - 수집 로그 확인"
    echo "  results   - 수집 결과 확인"
    echo "  cost      - 예상 비용 확인"
    echo "  delete    - VM 삭제 (주의!)"
    echo "  help      - 도움말 출력"
}

# VM 상태 확인
check_status() {
    print_header "VM 상태 확인"
    
    if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --quiet &>/dev/null; then
        STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(status)")
        EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
        
        echo "인스턴스: $INSTANCE_NAME"
        echo "상태: $STATUS"
        echo "외부 IP: $EXTERNAL_IP"
        echo "지역: $ZONE"
        
        if [ "$STATUS" = "RUNNING" ]; then
            print_success "VM이 실행 중입니다."
        else
            print_warning "VM이 중지되어 있습니다."
        fi
    else
        print_error "VM 인스턴스가 존재하지 않습니다."
        exit 1
    fi
}

# VM 시작
start_vm() {
    print_header "VM 시작"
    
    STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(status)")
    
    if [ "$STATUS" = "RUNNING" ]; then
        print_warning "VM이 이미 실행 중입니다."
    else
        gcloud compute instances start "$INSTANCE_NAME" --zone="$ZONE"
        print_success "VM을 시작했습니다."
        
        echo "외부 IP 주소 확인 중..."
        sleep 10
        EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
        echo "외부 IP: $EXTERNAL_IP"
    fi
}

# VM 중지
stop_vm() {
    print_header "VM 중지"
    
    STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(status)")
    
    if [ "$STATUS" = "TERMINATED" ]; then
        print_warning "VM이 이미 중지되어 있습니다."
    else
        gcloud compute instances stop "$INSTANCE_NAME" --zone="$ZONE"
        print_success "VM을 중지했습니다."
        print_warning "비용 절약: VM이 중지된 동안에는 컴퓨팅 비용이 발생하지 않습니다."
    fi
}

# VM 재시작
restart_vm() {
    print_header "VM 재시작"
    
    gcloud compute instances reset "$INSTANCE_NAME" --zone="$ZONE"
    print_success "VM을 재시작했습니다."
}

# SSH 접속
ssh_connect() {
    print_header "SSH 접속"
    
    STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(status)")
    
    if [ "$STATUS" != "RUNNING" ]; then
        print_error "VM이 실행 중이 아닙니다. 먼저 VM을 시작하세요."
        echo "VM 시작: $0 start"
        exit 1
    fi
    
    gcloud compute ssh --zone="$ZONE" "$INSTANCE_NAME" --project="$PROJECT_ID"
}

# 로그 확인
check_logs() {
    print_header "수집 로그 확인"
    
    echo "최신 로그 파일들:"
    gcloud compute ssh --zone="$ZONE" "$INSTANCE_NAME" --project="$PROJECT_ID" --command="ls -la ~/naver_land/logs/ | tail -5"
    
    echo ""
    echo "최신 로그 내용 (마지막 20줄):"
    gcloud compute ssh --zone="$ZONE" "$INSTANCE_NAME" --project="$PROJECT_ID" --command="tail -20 ~/naver_land/logs/daily_collection_*.log 2>/dev/null | tail -20"
}

# 수집 결과 확인
check_results() {
    print_header "수집 결과 확인"
    
    echo "최신 결과 파일들:"
    gcloud compute ssh --zone="$ZONE" "$INSTANCE_NAME" --project="$PROJECT_ID" --command="ls -la ~/naver_land/collectors/results/ | tail -5"
    
    echo ""
    echo "결과 파일 크기:"
    gcloud compute ssh --zone="$ZONE" "$INSTANCE_NAME" --project="$PROJECT_ID" --command="du -sh ~/naver_land/collectors/results/* 2>/dev/null | tail -5"
}

# 비용 확인
check_cost() {
    print_header "예상 비용 확인"
    
    echo "현재 VM 사양:"
    gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="table(machineType.basename(),disks[0].diskSizeGb,status)"
    
    echo ""
    echo "💰 무료 티어 (e2-micro) 예상 비용:"
    echo "- VM 인스턴스: 무료 (월 744시간)"
    echo "- 부팅 디스크: 무료 (30GB HDD)"
    echo "- 네트워크: 무료 (월 1GB 아웃바운드)"
    echo ""
    echo "⚠️ 무료 한도 초과시 과금됩니다."
    echo "현재 사용량 확인: https://console.cloud.google.com/billing"
}

# VM 삭제
delete_vm() {
    print_header "VM 삭제 (주의!)"
    
    print_error "이 작업은 되돌릴 수 없습니다!"
    echo "VM과 모든 데이터가 영구적으로 삭제됩니다."
    echo ""
    echo "정말로 삭제하시겠습니까? (DELETE 입력):"
    read -r CONFIRM
    
    if [ "$CONFIRM" = "DELETE" ]; then
        gcloud compute instances delete "$INSTANCE_NAME" --zone="$ZONE" --quiet
        print_success "VM이 삭제되었습니다."
    else
        print_warning "삭제가 취소되었습니다."
    fi
}

# 메인 로직
case "${1:-help}" in
    "status")
        check_status
        ;;
    "start")
        start_vm
        ;;
    "stop")
        stop_vm
        ;;
    "restart")
        restart_vm
        ;;
    "ssh")
        ssh_connect
        ;;
    "logs")
        check_logs
        ;;
    "results")
        check_results
        ;;
    "cost")
        check_cost
        ;;
    "delete")
        delete_vm
        ;;
    "help"|*)
        show_help
        ;;
esac