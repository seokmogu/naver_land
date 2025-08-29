#!/bin/bash
# EC2에서 실행할 응급 중단 스크립트

echo "🚨 네이버 부동산 수집기 응급 중단 스크립트"
echo "=================================================="

# 현재 시간
echo "실행 시간: $(date)"

# 1. 크론탭 백업 및 비활성화
echo "🔄 크론탭 백업 및 비활성화..."
crontab -l > /tmp/backup_crontab_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ 크론탭 백업 완료"
    crontab -r
    echo "✅ 크론탭 비활성화 완료"
else
    echo "ℹ️ 활성 크론탭이 없습니다"
fi

# 2. 실행 중인 관련 프로세스 확인 및 중단
echo "🔄 실행 중인 프로세스 확인..."

# json_to_supabase 프로세스 중단
echo "json_to_supabase 프로세스 확인:"
ps aux | grep json_to_supabase | grep -v grep
if [ $? -eq 0 ]; then
    echo "🛑 json_to_supabase 프로세스 중단 중..."
    pkill -f json_to_supabase
    echo "✅ json_to_supabase 프로세스 중단 완료"
else
    echo "ℹ️ json_to_supabase 프로세스 없음"
fi

# collector 프로세스 확인
echo "collector 프로세스 확인:"
ps aux | grep python | grep collector | grep -v grep
if [ $? -eq 0 ]; then
    echo "⚠️ collector 프로세스가 실행 중입니다. 수동으로 확인하세요."
    ps aux | grep python | grep collector | grep -v grep
else
    echo "ℹ️ collector 프로세스 없음"
fi

# 3. 스케줄링 파일 찾기
echo "🔄 스케줄링 파일 확인..."
find /home/hackit/naver_land -name "*schedule*" -type f 2>/dev/null
find /home/hackit/naver_land -name "*cron*" -type f 2>/dev/null

# 4. 현재 상태 저장
echo "🔄 현재 상태 저장..."
echo "Date: $(date)" > /tmp/emergency_stop_status.txt
echo "User: $(whoami)" >> /tmp/emergency_stop_status.txt
echo "Working Directory: $(pwd)" >> /tmp/emergency_stop_status.txt
echo "Python Processes:" >> /tmp/emergency_stop_status.txt
ps aux | grep python >> /tmp/emergency_stop_status.txt

echo ""
echo "🎯 응급 중단 완료!"
echo "📄 상태 파일: /tmp/emergency_stop_status.txt"
echo "📄 크론탭 백업: /tmp/backup_crontab_*.txt"
echo ""
echo "⚠️ 다음 단계:"
echo "1. 데이터 손실 범위 확인"
echo "2. 백업 생성"
echo "3. 개선된 수집기 배포"