#!/bin/bash

# Cloud Run 환경에서 실행될 스크립트
echo "🚀 네이버 부동산 수집 시작"
echo "📅 실행 시간: $(date)"

# collectors 디렉토리로 이동
cd collectors

# 강남구 전체 수집 실행
python3 parallel_batch_collect_gangnam.py --max-workers 2 --include-details

echo "✅ 수집 완료"
echo "📅 완료 시간: $(date)"