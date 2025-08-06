#!/bin/bash
# fixed_naver_collector.py의 bool subscriptable 버그 수정

set -e

echo "🔧 fixed_naver_collector.py 버그 수정"
echo "===================================="

PROJECT_ID="gbd-match"
INSTANCE_NAME="naver-collector"
ZONE="us-central1-a"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 수정된 parse_url 함수 생성
print_step "수정된 parse_url 함수 준비"
cat > /tmp/parse_url_fix.py << 'EOF'
# parse_url 함수 수정 패치
def parse_url(self, url):
    """네이버 부동산 URL 파싱"""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    
    # ms 파라미터에서 좌표 추출 - list가 아닌 경우 처리
    ms_param = query.get('ms', [''])
    if isinstance(ms_param, list) and len(ms_param) > 0:
        ms = ms_param[0]
    else:
        ms = ms_param if isinstance(ms_param, str) else ''
    
    if ms:
        parts = ms.split(',')
        lat, lon, zoom = float(parts[0]), float(parts[1]), int(parts[2])
    else:
        lat, lon, zoom = 37.5665, 126.9780, 15
    
    # 매물 타입 추출 - list가 아닌 경우 처리
    article_types_param = query.get('a', [''])
    if isinstance(article_types_param, list) and len(article_types_param) > 0:
        article_types = article_types_param[0]
    else:
        article_types = article_types_param if isinstance(article_types_param, str) else ''
    
    purpose_param = query.get('e', [''])
    if isinstance(purpose_param, list) and len(purpose_param) > 0:
        purpose = purpose_param[0]
    else:
        purpose = purpose_param if isinstance(purpose_param, str) else ''
    
    return {
        'lat': lat,
        'lon': lon,
        'zoom': zoom,
        'article_types': article_types,
        'purpose': purpose,
        'property_type': parsed.path.split('/')[-1]
    }
EOF

# Python 스크립트로 자동 수정
print_step "Python 스크립트로 파일 수정 중"
cat > /tmp/fix_collector.py << 'EOF'
#!/usr/bin/env python3
import re

# 파일 읽기
with open('fixed_naver_collector.py', 'r', encoding='utf-8') as f:
    content = f.read()

# parse_url 함수 찾아서 수정
pattern = r'def parse_url\(self, url\):\s*"""네이버 부동산 URL 파싱""".*?return \{[^}]+\}'
replacement = '''def parse_url(self, url):
        """네이버 부동산 URL 파싱"""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        # ms 파라미터에서 좌표 추출 - list가 아닌 경우 처리
        ms_param = query.get('ms', [''])
        if isinstance(ms_param, list) and len(ms_param) > 0:
            ms = ms_param[0]
        else:
            ms = ms_param if isinstance(ms_param, str) else ''
        
        if ms:
            parts = ms.split(',')
            lat, lon, zoom = float(parts[0]), float(parts[1]), int(parts[2])
        else:
            lat, lon, zoom = 37.5665, 126.9780, 15
        
        # 매물 타입 추출 - list가 아닌 경우 처리
        article_types_param = query.get('a', [''])
        if isinstance(article_types_param, list) and len(article_types_param) > 0:
            article_types = article_types_param[0]
        else:
            article_types = article_types_param if isinstance(article_types_param, str) else ''
        
        purpose_param = query.get('e', [''])
        if isinstance(purpose_param, list) and len(purpose_param) > 0:
            purpose = purpose_param[0]
        else:
            purpose = purpose_param if isinstance(purpose_param, str) else ''
        
        return {
            'lat': lat,
            'lon': lon,
            'zoom': zoom,
            'article_types': article_types,
            'purpose': purpose,
            'property_type': parsed.path.split('/')[-1]
        }'''

# 수정 적용
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# 백업 생성
import shutil
shutil.copy('fixed_naver_collector.py', 'fixed_naver_collector.py.backup')

# 수정된 내용 저장
with open('fixed_naver_collector.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 파일 수정 완료!")
EOF

# VM에 수정 스크립트 전송
print_step "수정 스크립트를 VM에 전송 중"
gcloud compute scp /tmp/fix_collector.py "$INSTANCE_NAME":~/naver_land/collectors/fix_collector.py \
    --zone="$ZONE" --project="$PROJECT_ID"

# VM에서 수정 실행
print_step "VM에서 수정 실행 중"
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
    --command="cd ~/naver_land/collectors && python3 fix_collector.py"

print_success "fixed_naver_collector.py 버그 수정 완료!"

# 테스트 실행
print_step "수정 사항 테스트"
echo ""
echo "수정 사항을 테스트하시겠습니까? (y/N):"
read -r RUN_TEST

if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo "🧪 수정된 수집기 테스트 중..."
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --command="cd ~/naver_land/collectors && source ../venv/bin/activate && python3 parallel_batch_collect_gangnam.py --max-workers 1"
else
    echo "나중에 다음 명령어로 테스트할 수 있습니다:"
    echo "./deploy_scripts/remote_commands.sh test"
fi

# 정리
rm -f /tmp/fix_collector.py /tmp/parse_url_fix.py

print_success "버그 수정 완료! 🎉"