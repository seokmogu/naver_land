#!/bin/bash
# EC2 안전 배포 스크립트

set -e

echo "🚀 EC2 안전 수집기 배포"

EC2_HOST="naver-ec2"
REMOTE_DIR="/home/ubuntu/naver_land/collectors"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "EC2 연결 테스트..."
ssh -o ConnectTimeout=10 "$EC2_HOST" "echo '연결 성공'" || exit 1

CORE_FILES=(
    "emergency_recovery.py"
    "final_safe_collector.py" 
    "completely_safe_collector.py"
    "json_to_db_converter.py"
    "supabase_client.py"
    "ec2_safe_test.sh"
)

for file in "${CORE_FILES[@]}"; do
    if [[ -f "$LOCAL_DIR/$file" ]]; then
        scp "$LOCAL_DIR/$file" "$EC2_HOST:$REMOTE_DIR/"
        echo "✓ $file 배포 완료"
    fi
done

ssh "$EC2_HOST" "chmod +x $REMOTE_DIR/*.sh $REMOTE_DIR/*.py"
echo "🎉 배포 완료!"
echo ""
echo "다음 단계:"
echo "  ssh $EC2_HOST"
echo "  cd $REMOTE_DIR"
echo "  ./ec2_safe_test.sh"