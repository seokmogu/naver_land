#!/bin/bash
# Google Cloud CLI 설치 및 초기 설정 스크립트

set -e

echo "☁️ Google Cloud CLI 설치 시작"
echo "================================"

# 운영체제 감지
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="darwin"
else
    echo "❌ 지원하지 않는 운영체제입니다."
    exit 1
fi

# 1. Google Cloud CLI 설치
echo "📦 Google Cloud CLI 설치 중..."

if [[ "$OS" == "linux" ]]; then
    # Linux 설치
    if ! command -v gcloud &> /dev/null; then
        echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
        curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
        sudo apt-get update && sudo apt-get install google-cloud-cli
        echo "✅ gcloud CLI 설치 완료"
    else
        echo "ℹ️ gcloud CLI가 이미 설치되어 있습니다."
    fi
elif [[ "$OS" == "darwin" ]]; then
    # macOS 설치
    if ! command -v gcloud &> /dev/null; then
        if command -v brew &> /dev/null; then
            brew install --cask google-cloud-sdk
        else
            echo "❌ Homebrew가 필요합니다. https://brew.sh/ 에서 설치하세요."
            exit 1
        fi
        echo "✅ gcloud CLI 설치 완료"
    else
        echo "ℹ️ gcloud CLI가 이미 설치되어 있습니다."
    fi
fi

# 2. 버전 확인
echo ""
echo "🔍 gcloud CLI 버전 확인:"
gcloud version

echo ""
echo "✅ Google Cloud CLI 설치 완료!"
echo ""
echo "다음 단계:"
echo "1. gcloud auth login  # Google 계정 로그인"
echo "2. gcloud config set project PROJECT_ID  # 프로젝트 설정"
echo "3. ./create_vm.sh  # VM 생성 스크립트 실행"
echo ""
echo "또는 전체 자동화:"
echo "./deploy_to_gcp.sh"