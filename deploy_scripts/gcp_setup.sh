#!/bin/bash
# GCP Compute Engine 환경 설정 스크립트

set -e  # 오류 발생시 스크립트 중단

echo "🚀 네이버 부동산 컬렉터 GCP 배포 시작"
echo "=================================="

# 1. 시스템 업데이트
echo "📦 시스템 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 2. Python 3.11 설치
echo "🐍 Python 3.11 설치 중..."
sudo apt install -y python3.11 python3.11-pip python3.11-dev python3.11-venv

# 3. 시스템 패키지 설치
echo "📚 시스템 패키지 설치 중..."
sudo apt install -y git curl wget unzip cron

# 4. Playwright 의존성 설치
echo "🎭 Playwright 의존성 설치 중..."
sudo apt install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgtk-3-0 libatspi2.0-0 libxrandr2 libasound2 \
    libxdamage1 libxss1 libgconf-2-4

echo "✅ 시스템 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. 프로젝트를 GitHub에 업로드하세요"
echo "2. VM에서 git clone으로 프로젝트를 다운로드하세요"
echo "3. setup_project.sh를 실행하세요"