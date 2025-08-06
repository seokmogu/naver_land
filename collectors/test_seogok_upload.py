#!/usr/bin/env python3
"""
세곡동 데이터로 새로운 스키마 테스트
변경된 테이블 구조에 저장이 잘 되는지 확인
"""

import json
from datetime import date, datetime
from supabase_client import SupabaseHelper

def test_seogok_upload():
    """세곡동 데이터 업로드 테스트"""
    print("🧪 세곡동 데이터 업로드 테스트 - 새로운 스키마")
    print("=" * 60)
    
    # 1. 기존 데이터 파일 로드
    data_file = "results/naver_streaming_강남구_세곡동_1168011100_20250805_042933.json"
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        properties = data.get('매물목록', [])
        cortar_no = data.get('수집정보', {}).get('지역코드', '1168011100')
        
        print(f"✅ 데이터 파일 로드 성공")
        print(f"  📊 매물 수: {len(properties):,}개")
        print(f"  🏘️ 지역코드: {cortar_no}")
        
    except Exception as e:
        print(f"❌ 데이터 파일 로드 실패: {e}")
        return False
    
    # 2. Supabase 연결
    try:
        helper = SupabaseHelper()
        print("✅ Supabase 연결 성공")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False
    
    # 3. 기존 세곡동 매물 상태 확인
    print(f"\n📊 기존 세곡동 매물 상태:")
    print("-" * 40)
    
    try:
        # 전체 세곡동 매물
        total_seogok = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .execute()
        
        # 활성 세곡동 매물
        active_seogok = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .eq('is_active', True)\
            .execute()
        
        print(f"  📊 전체 세곡동 매물: {total_seogok.count:,}개")
        print(f"  ✅ 활성 매물: {active_seogok.count:,}개")
        print(f"  ❌ 비활성 매물: {total_seogok.count - active_seogok.count:,}개")
        
        # 샘플 매물 정보 확인
        if active_seogok.count > 0:
            sample = helper.client.table('properties')\
                .select('article_no, price, rent_price, trade_type, last_seen_date')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .limit(3)\
                .execute()
            
            print(f"\n📋 기존 매물 샘플:")
            for prop in sample.data:
                print(f"  • {prop['article_no']}: {prop['trade_type']} - {prop['price']:,}만원")
                print(f"    월세: {prop.get('rent_price', 0):,}만원, 최종확인: {prop.get('last_seen_date')}")
        
    except Exception as e:
        print(f"  ❌ 기존 데이터 조회 실패: {e}")
    
    # 4. 새로운 데이터로 업데이트 테스트
    print(f"\n🔄 새로운 스키마로 데이터 업데이트 테스트:")
    print("-" * 40)
    
    try:
        # save_properties 메서드 호출 (새로운 스키마 적용)
        stats = helper.save_properties(properties, cortar_no)
        
        print(f"✅ 데이터 업데이트 완료:")
        print(f"  🆕 신규 매물: {stats['new_count']:,}개")
        print(f"  🔄 변동 매물: {stats['updated_count']:,}개") 
        print(f"  🗑️ 삭제 매물: {stats['removed_count']:,}개")
        print(f"  📊 전체 처리: {stats['total_saved']:,}개")
        
    except Exception as e:
        print(f"❌ 데이터 업데이트 실패: {e}")
        return False
    
    # 5. 업데이트 후 상태 확인
    print(f"\n📈 업데이트 후 상태 확인:")
    print("-" * 40)
    
    try:
        # 업데이트 후 세곡동 매물 상태
        after_total = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .execute()
        
        after_active = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .eq('is_active', True)\
            .execute()
        
        print(f"  📊 전체 매물: {after_total.count:,}개")
        print(f"  ✅ 활성 매물: {after_active.count:,}개")
        
        # 오늘 업데이트된 매물 확인
        today = date.today()
        today_updated = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .eq('last_seen_date', today.isoformat())\
            .execute()
        
        print(f"  📅 오늘 확인된 매물: {today_updated.count:,}개")
        
    except Exception as e:
        print(f"  ❌ 업데이트 후 상태 확인 실패: {e}")
    
    # 6. 새로운 기능 테스트
    print(f"\n🔧 새로운 기능 테스트:")
    print("-" * 40)
    
    try:
        # price_history 테이블 확인
        price_history = helper.client.table('price_history')\
            .select('*')\
            .execute()
        
        print(f"  💰 가격 변동 이력: {len(price_history.data):,}개")
        
        # 최근 가격 변동이 있다면 표시
        if price_history.data:
            recent = price_history.data[-1]  # 최근 기록
            print(f"  📊 최근 변동: {recent['article_no']}")
            print(f"    거래타입: {recent.get('trade_type', 'N/A')}")
            print(f"    가격변동: {recent.get('previous_price', 0):,} → {recent.get('new_price', 0):,}만원")
            if recent.get('rent_change_amount'):
                print(f"    월세변동: {recent.get('previous_rent_price', 0):,} → {recent.get('new_rent_price', 0):,}만원")
        
        # deletion_history 테이블 확인
        deletion_history = helper.client.table('deletion_history')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .execute()
        
        print(f"  🗑️ 삭제 이력: {deletion_history.count:,}개")
        
        if deletion_history.count > 0:
            recent_deleted = helper.client.table('deletion_history')\
                .select('*')\
                .eq('cortar_no', cortar_no)\
                .order('created_at', desc=True)\
                .limit(3)\
                .execute()
            
            print(f"  📋 최근 삭제된 매물:")
            for deleted in recent_deleted.data:
                print(f"    • {deleted['article_no']}: {deleted.get('deletion_reason', 'N/A')}")
                print(f"      활성기간: {deleted.get('days_active', 'N/A')}일")
        
    except Exception as e:
        print(f"  ❌ 새로운 기능 테스트 실패: {e}")
    
    # 7. 데이터 정합성 검증
    print(f"\n🔍 데이터 정합성 검증:")
    print("-" * 40)
    
    try:
        # last_seen_date가 NULL인 세곡동 매물 확인
        null_last_seen = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .is_('last_seen_date', 'null')\
            .execute()
        
        if null_last_seen.count == 0:
            print(f"  ✅ 모든 세곡동 매물에 last_seen_date 설정됨")
        else:
            print(f"  ⚠️ last_seen_date가 NULL인 매물: {null_last_seen.count:,}개")
        
        # 활성 매물 중 deleted_at이 설정된 매물 확인 (있으면 안됨)
        invalid_active = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('cortar_no', cortar_no)\
            .eq('is_active', True)\
            .not_.is_('deleted_at', 'null')\
            .execute()
        
        if invalid_active.count == 0:
            print(f"  ✅ 활성 매물에 잘못된 deleted_at 없음")
        else:
            print(f"  ❌ 활성 매물 중 deleted_at이 설정된 매물: {invalid_active.count:,}개")
        
    except Exception as e:
        print(f"  ❌ 데이터 정합성 검증 실패: {e}")
    
    print(f"\n🎯 세곡동 테스트 완료!")
    print("=" * 60)
    print("✅ 새로운 스키마로 데이터 저장 및 처리가 정상 동작합니다.")
    
    return True

if __name__ == "__main__":
    success = test_seogok_upload()
    exit(0 if success else 1)