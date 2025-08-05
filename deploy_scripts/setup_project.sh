#!/bin/bash
# 프로젝트 환경 설정 스크립트 (VM에서 실행)

set -e

echo "🏗️ 프로젝트 환경 설정 시작"
echo "============================"

PROJECT_DIR="/home/$USER/naver_land"
cd "$PROJECT_DIR"

# 1. Python 가상환경 생성
echo "🐍 Python 가상환경 생성 중..."
python3.11 -m venv venv
source venv/bin/activate

# 2. Python 패키지 설치
echo "📦 Python 패키지 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Playwright 브라우저 설치
echo "🎭 Playwright 브라우저 설치 중..."
playwright install chromium

# 4. 설정 파일 준비
echo "⚙️ 설정 파일 준비 중..."
cd collectors
if [ ! -f config.json ]; then
    cp config.template.json config.json
    echo "⚠️ config.json이 생성되었습니다."
    echo "   Kakao API 키와 Supabase 설정을 입력하세요:"
    echo "   python3 setup_deployment.py"
fi

# 5. 결과 폴더 생성
mkdir -p results
mkdir -p logs

# 6. 실행 권한 설정
chmod +x ../deploy_scripts/*.sh

echo "✅ 프로젝트 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. python3 setup_deployment.py 실행하여 API 키 설정"
echo "2. setup_cron.sh 실행하여 자동 스케줄링 설정"
echo "3. 수동 테스트: python3 parallel_batch_collect_gangnam.py"