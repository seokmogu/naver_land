#!/bin/bash
# EC2 연결 테스트 스크립트

echo "🔍 EC2 연결 테스트"
echo "==================="

EC2_HOST="52.78.34.225"
KEY_PATH="/Users/smgu/test_code/naver_land/naver-land-collector-v2-key.pem"

echo "📋 연결 정보:"
echo "  호스트: $EC2_HOST"
echo "  키 파일: $KEY_PATH"
echo ""

# 1. 키 파일 권한 확인
echo "🔑 키 파일 권한 확인:"
ls -la "$KEY_PATH"
echo ""

# 2. 핑 테스트
echo "🏓 핑 테스트:"
ping -c 3 $EC2_HOST
echo ""

# 3. 포트 22 (SSH) 확인
echo "🔌 SSH 포트 확인:"
nc -z -v $EC2_HOST 22
echo ""

# 4. 다양한 사용자로 SSH 연결 시도
echo "👤 SSH 연결 테스트:"

users=("ubuntu" "ec2-user" "hackit" "admin")

for user in "${users[@]}"; do
    echo "  🔄 $user@$EC2_HOST 연결 시도..."
    timeout 10 ssh -i "$KEY_PATH" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$user@$EC2_HOST" "echo '✅ $user 연결 성공'" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "    ✅ $user 사용자 연결 성공!"
        WORKING_USER=$user
        break
    else
        echo "    ❌ $user 연결 실패"
    fi
done

if [ ! -z "$WORKING_USER" ]; then
    echo ""
    echo "🎉 연결 성공! 사용자: $WORKING_USER"
    echo ""
    echo "📋 시스템 정보:"
    ssh -i "$KEY_PATH" "$WORKING_USER@$EC2_HOST" "
        echo '  OS: $(lsb_release -d 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME)';
        echo '  홈 디렉토리: $(pwd)';
        echo '  Python: $(python3 --version 2>/dev/null || echo 'Python3 없음')';
        echo '  디스크 사용량:';
        df -h | head -2;
        echo '  기존 프로젝트:';
        ls -la | grep naver || echo '  naver_land 프로젝트 없음'
    "
    
    echo ""
    echo "🚀 배포 가능! 다음 명령어로 배포하세요:"
    echo "  ./deploy_to_ec2.sh (EC2_USER를 '$WORKING_USER'로 수정 후)"
else
    echo ""
    echo "❌ 모든 사용자 연결 실패"
    echo ""
    echo "🔧 해결 방법:"
    echo "  1. EC2 인스턴스가 실행 중인지 AWS 콘솔에서 확인"
    echo "  2. 보안 그룹에서 SSH(22) 포트가 열려있는지 확인"  
    echo "  3. 올바른 키 파일을 사용하고 있는지 확인"
    echo "  4. EC2 퍼블릭 IP가 변경되었는지 확인"
fi