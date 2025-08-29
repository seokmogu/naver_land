#!/bin/bash
# 개선된 수집기를 EC2에 배포하는 스크립트

echo "🚀 네이버 부동산 수집기 EC2 배포 스크립트"
echo "=============================================="

# EC2 정보 (실제 값으로 업데이트됨)
EC2_HOST="52.78.34.225"
EC2_USER="hackit"
EC2_PATH="/home/hackit/naver_land"
KEY_PATH="/Users/smgu/test_code/naver_land/naver-land-collector-v2-key.pem"

# 현재 경로
LOCAL_PATH="/Users/smgu/test_code/naver_land/collectors"

echo "📋 배포 계획:"
echo "  로컬: $LOCAL_PATH"
echo "  EC2: $EC2_USER@$EC2_HOST:$EC2_PATH"
echo ""

# 1. EC2 연결 테스트
echo "🔄 EC2 연결 테스트..."
ssh -i $KEY_PATH -o ConnectTimeout=10 $EC2_USER@$EC2_HOST "echo '✅ EC2 연결 성공'"

if [ $? -ne 0 ]; then
    echo "❌ EC2 연결 실패. 연결 정보를 확인하세요."
    exit 1
fi

# 2. EC2에서 응급 중단 실행
echo "🚨 EC2에서 응급 중단 실행..."
scp -i $KEY_PATH $LOCAL_PATH/ec2_emergency_stop.sh $EC2_USER@$EC2_HOST:/tmp/
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST "chmod +x /tmp/ec2_emergency_stop.sh && /tmp/ec2_emergency_stop.sh"

echo "⏳ 5초 대기 (중단 완료 확인)..."
sleep 5

# 3. 백업 디렉토리 생성
echo "🔄 EC2에서 백업 생성..."
BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST "
    mkdir -p /home/hackit/backups/$BACKUP_NAME && 
    cp -r $EC2_PATH/collectors /home/hackit/backups/$BACKUP_NAME/ &&
    echo '✅ 백업 완료: /home/hackit/backups/$BACKUP_NAME'
"

# 4. 개선된 파일들 EC2로 전송
echo "🔄 개선된 파일들 EC2로 전송..."

FILES_TO_DEPLOY=(
    "emergency_recovery.py"
    "json_to_db_converter.py" 
    "enhanced_collector_with_direct_save.py"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ -f "$LOCAL_PATH/$file" ]; then
        echo "📤 전송 중: $file"
        scp -i $KEY_PATH "$LOCAL_PATH/$file" "$EC2_USER@$EC2_HOST:$EC2_PATH/collectors/"
        if [ $? -eq 0 ]; then
            echo "✅ 전송 완료: $file"
        else
            echo "❌ 전송 실패: $file"
        fi
    else
        echo "⚠️ 파일 없음: $file"
    fi
done

# 5. EC2에서 파일 권한 설정
echo "🔄 EC2에서 파일 권한 설정..."
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST "
    cd $EC2_PATH/collectors &&
    chmod +x *.py &&
    echo '✅ 파일 권한 설정 완료'
"

# 6. EC2에서 응급 복구 실행 (선택사항)
echo ""
echo "🤔 EC2에서 응급 데이터 복구를 실행하시겠습니까? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🔄 EC2에서 응급 복구 실행..."
    ssh -i $KEY_PATH $EC2_USER@$EC2_HOST "
        cd $EC2_PATH/collectors &&
        python3 emergency_recovery.py > recovery_log_\$(date +%Y%m%d_%H%M%S).txt 2>&1 &&
        echo '✅ 응급 복구 완료'
    "
else
    echo "ℹ️ 응급 복구를 건너뛰었습니다. 수동으로 실행하세요:"
    echo "   ssh $EC2_USER@$EC2_HOST"
    echo "   cd $EC2_PATH/collectors"
    echo "   python3 emergency_recovery.py"
fi

# 7. EC2에서 새로운 수집기 테스트
echo ""
echo "🧪 EC2에서 새로운 수집기를 테스트하시겠습니까? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🔄 EC2에서 테스트 수집 실행..."
    ssh -i $KEY_PATH $EC2_USER@$EC2_HOST "
        cd $EC2_PATH/collectors &&
        python3 enhanced_collector_with_direct_save.py 11680102 --max-pages 2 --test &&
        echo '✅ 테스트 완료'
    "
else
    echo "ℹ️ 테스트를 건너뛰었습니다. 수동으로 실행하세요:"
    echo "   ssh $EC2_USER@$EC2_HOST"
    echo "   cd $EC2_PATH/collectors"
    echo "   python3 enhanced_collector_with_direct_save.py 11680102 --max-pages 2 --test"
fi

echo ""
echo "🎯 배포 완료!"
echo "📋 다음 단계:"
echo "1. EC2에 접속하여 응급 복구 실행 확인"
echo "2. 새로운 수집기 테스트 실행"
echo "3. 정상 작동 확인 후 자동화 재설정"
echo ""
echo "🔗 EC2 접속: ssh -i $KEY_PATH $EC2_USER@$EC2_HOST"