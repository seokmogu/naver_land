#!/bin/bash

# 네이버 부동산 데이터 수집기 실행 스크립트

echo "🚀 네이버 부동산 데이터 수집기 시작"
echo "📅 시작 시간: $(date)"
echo "=" | tr -d '\n' && seq -s "=" 50 | tr -d '0-9' && echo

# 환경 설정 확인
echo "🔍 환경 설정 확인..."
if [ ! -f ".env" ]; then
    echo "⚠️ .env 파일이 없습니다. 환경변수를 설정해주세요."
fi

# 토큰 확인
echo "🔑 토큰 상태 확인..."
python3 -c "
from enhanced_data_collector import EnhancedNaverCollector
collector = EnhancedNaverCollector()
print('✅ 토큰 상태 확인 완료')
"

# 수집 시작
echo ""
echo "🎯 데이터 수집 시작..."
python3 -c "
from enhanced_data_collector import EnhancedNaverCollector
import datetime

print('🏗️ 수집기 초기화 중...')
collector = EnhancedNaverCollector()

# 강남구 전체 수집
print('🌟 강남구 전체 데이터 수집 시작')
print('📍 대상: 강남구 22개 동')
print('⏰ 예상 소요시간: 2-3시간')
print()

# 실제 수집 실행
gangnam_dongs = [
    {'name': '역삼동', 'code': '1168010100'},
    {'name': '개포동', 'code': '1168010300'},  
    {'name': '청담동', 'code': '1168010400'},
    {'name': '삼성동', 'code': '1168010500'},
    {'name': '대치동', 'code': '1168010600'},
    {'name': '신사동', 'code': '1168010700'},
    {'name': '논현동', 'code': '1168010800'},
    {'name': '압구정동', 'code': '1168011000'},
    {'name': '세곡동', 'code': '1168011100'},
    {'name': '자곡동', 'code': '1168011200'},
    {'name': '율현동', 'code': '1168011300'},
    {'name': '일원동', 'code': '1168011400'},
    {'name': '수서동', 'code': '1168011500'},
    {'name': '도곡동', 'code': '1168011800'}
]

try:
    collector.collect_gangnam_all_enhanced(gangnam_dongs)
    print('🎉 수집 완료!')
    collector.print_collection_stats()
except Exception as e:
    print(f'❌ 수집 중 오류 발생: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "📅 완료 시간: $(date)"
echo "🏁 수집기 종료"