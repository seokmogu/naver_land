#!/bin/bash
# 원격에서 API 키 자동 설정 스크립트

set -e

echo "🔑 원격 API 키 설정 시작"
echo "========================"

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

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

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 로컬 config.json 사용
print_step "로컬 config.json 파일 확인"
LOCAL_CONFIG="./collectors/config.json"

if [ ! -f "$LOCAL_CONFIG" ]; then
    print_error "로컬 config.json 파일을 찾을 수 없습니다: $LOCAL_CONFIG"
    exit 1
fi

print_success "로컬 config.json 파일 발견"

# 로컬 config.json의 내용 확인
echo "📋 현재 config.json 설정:"
python3 -c "
import json
with open('$LOCAL_CONFIG', 'r', encoding='utf-8') as f:
    config = json.load(f)
print('Kakao API Key:', config['kakao_api']['rest_api_key'][:10] + '...')
if 'supabase' in config:
    print('Supabase URL:', config['supabase']['url'])
    print('Supabase Key:', config['supabase']['anon_key'][:20] + '...')
"

# 로컬 config.json을 VM에 직접 전송
print_step "config.json을 VM에 전송 중"
gcloud compute scp "$LOCAL_CONFIG" "$INSTANCE_NAME":~/naver_land/collectors/config.json \
    --zone="$ZONE" --project="$PROJECT_ID"

print_success "API 키 설정 완료!"

# VM에서 설정 확인
print_step "VM에서 설정 확인 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="cd ~/naver_land/collectors && python3 -c \"
import json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
print('✅ VM에서 config.json 확인 완료')
print('Kakao API Key:', config['kakao_api']['rest_api_key'][:10] + '...')
if 'supabase' in config:
    print('Supabase URL:', config['supabase']['url'])
\""

# 설정 테스트
print_step "API 키 테스트 실행 중"
echo "Kakao API 키 테스트를 실행하시겠습니까? (y/N):"
read -r TEST_API

if [[ "$TEST_API" =~ ^[Yy]$ ]]; then
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="cd ~/naver_land/collectors && source ../venv/bin/activate && python3 -c \"
from kakao_address_converter import KakaoAddressConverter
converter = KakaoAddressConverter()
result = converter.convert_coord_to_address('37.498095', '127.027610')
if result:
    print('✅ Kakao API 테스트 성공!')
    address = result.get('대표주소', 'N/A')
    print(f'테스트 주소: {address}')
else:
    print('❌ Kakao API 테스트 실패')
\""
fi

print_success "원격 API 키 설정 완료! 🎉"