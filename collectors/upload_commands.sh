#!/bin/bash
# 개별 파일 업로드 명령어들

cd /home/hackit/projects/naver_land/collectors

echo "🚀 개별 파일 업로드 시작"
echo "=========================="

# 개포동
echo "📍 개포동 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_개포동_1168010300_20250805_042118.json 1168010300

# 논현동 (2개 파일)
echo "📍 논현동 첫 번째 파일 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_논현동_1168010800_20250805_012213.json 1168010800

echo "📍 논현동 두 번째 파일 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_논현동_1168010800_20250805_025403.json 1168010800

# 대치동 (2개 파일)
echo "📍 대치동 첫 번째 파일 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_대치동_1168010600_20250805_023929.json 1168010600

echo "📍 대치동 두 번째 파일 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_대치동_1168010600_20250805_034632.json 1168010600

# 삼성동
echo "📍 삼성동 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_삼성동_1168010500_20250805_003644.json 1168010500

# 역삼동
echo "📍 역삼동 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_역삼동_1168010100_20250805_003644.json 1168010100

# 일원동
echo "📍 일원동 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_일원동_1168011400_20250805_042729.json 1168011400

# 청담동
echo "📍 청담동 업로드 중..."
./venv/bin/python json_to_supabase.py results/naver_streaming_강남구_청담동_1168010400_20250805_031411.json 1168010400

echo ""
echo "=========================="
echo "✅ 모든 업로드 완료!"
echo ""
echo "이미 업로드된 파일들 (중복 제거됨):"
echo "  - 압구정동 (1168011000)"
echo "  - 율현동 (1168011300)"
echo "  - 세곡동 (1168011100)"
echo "  - 수서동 (1168011500)"
echo "  - 자곡동 (1168011200)"