# Python 3.10 slim 이미지 사용 (가볍고 빠름)
FROM python:3.10-slim

# 필요한 시스템 패키지 설치 (Playwright 의존성 포함)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    # Playwright 의존성
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 먼저 복사 (캐싱 활용)
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치
RUN playwright install chromium
# 의존성은 이미 위에서 설치했으므로 install-deps는 생략

# 소스코드 복사
COPY collectors/ ./collectors/
COPY .env .env

# 환경변수 설정
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 결과 폴더 생성
RUN mkdir -p collectors/results

# 실행 스크립트 생성
COPY run.sh .
RUN chmod +x run.sh

# Cloud Run은 PORT 환경변수의 포트를 사용해야 함
EXPOSE 8080

# 실행 명령
CMD ["./run.sh"]