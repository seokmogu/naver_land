#!/bin/bash

echo "🐳 Docker 로컬 테스트 시작"
echo "========================="

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    echo "👉 Docker Desktop을 설치하고 WSL Integration을 활성화하세요."
    echo "   https://www.docker.com/products/docker-desktop/"
    exit 1
fi

echo "✅ Docker 설치 확인"

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️ .env 파일이 없습니다. 생성 중..."
    cp collectors/config.json .env.example
    echo "👉 .env 파일을 설정해주세요"
    exit 1
fi

# 1. Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker-compose build

# 2. 간단한 테스트 실행 (율현동 1페이지)
echo "🧪 테스트 실행: 율현동 1페이지 수집"
docker-compose up

echo "✅ 테스트 완료!"
echo ""
echo "📊 결과 확인:"
echo "ls -la collectors/results/"
echo ""
echo "🚀 전체 실행하려면:"
echo "docker-compose run naver-collector ./run.sh"