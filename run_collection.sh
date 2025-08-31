#!/bin/bash

# 네이버 부동산 수집기 실행 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 프로젝트 디렉토리로 이동
cd ~/naver_land

# 가상환경 활성화
log_info "가상환경 활성화 중..."
source venv/bin/activate

# 환경변수 확인
if [ ! -f ".env" ]; then
    log_warn ".env 파일이 없습니다. 환경변수를 설정해주세요."
fi

# 수집 실행
case "$1" in
    "gangnam")
        log_info "강남구 전체 수집 시작..."
        python main.py --gangnam --max-pages 5
        ;;
    "test")
        log_info "테스트 수집 (논현동 10개 매물)..."
        python main.py --area 1168010700 --max-articles 10
        ;;
    "area")
        if [ -z "$2" ]; then
            echo "사용법: $0 area [지역코드] [최대매물수]"
            echo "예시: $0 area 1168010700 20"
            exit 1
        fi
        MAX_ARTICLES=${3:-50}
        log_info "지역 $2 수집 시작 (최대 $MAX_ARTICLES 개)..."
        python main.py --area "$2" --max-articles "$MAX_ARTICLES"
        ;;
    "article")
        if [ -z "$2" ]; then
            echo "사용법: $0 article [매물번호]"
            echo "예시: $0 article 2390390123"
            exit 1
        fi
        log_info "매물 $2 수집 시작..."
        python main.py --article "$2"
        ;;
    *)
        echo "네이버 부동산 수집기 v2.0"
        echo ""
        echo "사용법:"
        echo "  $0 test                    # 테스트 수집 (논현동 10개)"
        echo "  $0 gangnam                 # 강남구 전체 수집"
        echo "  $0 area [지역코드] [개수]   # 특정 지역 수집"
        echo "  $0 article [매물번호]      # 특정 매물 수집"
        echo ""
        echo "강남구 지역 코드 예시:"
        echo "  신사동: 1168010600"
        echo "  논현동: 1168010700"
        echo "  압구정동: 1168010800"
        echo "  청담동: 1168011000"
        ;;
esac