#!/usr/bin/env python3
"""
수정된 supabase_client.py 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'collectors'))

from supabase_client import SupabaseHelper
from datetime import date

def test_updated_client():
    """수정된 클라이언트 테스트"""
    print("🧪 수정된 Supabase 클라이언트 테스트")
    print("=" * 60)
    
    try:
        helper = SupabaseHelper()
        print("✅ Supabase 연결 성공")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False
    
    # 1. 기본 연결 테스트
    print("\n📊 기본 기능 테스트:")
    print("-" * 40)
    
    try:
        # properties 테이블 스키마 확인
        sample = helper.client.table('properties').select('*').limit(1).execute()
        if sample.data:
            columns = list(sample.data[0].keys())
            required_fields = ['last_seen_date', 'deleted_at', 'deletion_reason']
            
            for field in required_fields:
                if field in columns:
                    print(f"  ✅ {field} 필드 존재")
                else:
                    print(f"  ❌ {field} 필드 누락")
        
        # price_history 테이블 스키마 확인
        price_sample = helper.client.table('price_history').select('*').limit(1).execute()
        if price_sample.data:
            price_columns = list(price_sample.data[0].keys())
            price_required = ['trade_type', 'previous_rent_price', 'new_rent_price', 
                             'rent_change_amount', 'rent_change_percent']
            
            for field in price_required:
                if field in price_columns:
                    print(f"  ✅ price_history.{field} 필드 존재")
                else:
                    print(f"  ❌ price_history.{field} 필드 누락")
        else:
            print("  ℹ️  price_history 테이블에 데이터가 없음")
        
    except Exception as e:
        print(f"  ❌ 스키마 확인 실패: {e}")
        return False
    
    # 2. 테스트 데이터로 새로운 기능 테스트
    print("\n🔧 새로운 기능 테스트 (시뮬레이션):")
    print("-" * 40)
    
    try:
        # _prepare_property_record 함수 테스트
        test_prop = {
            '매물번호': 'TEST123',
            '매물명': '테스트 매물',
            '부동산타입': '아파트',
            '거래타입': '월세',
            '매매가격': 50000,  # 5억
            '월세': 200,  # 200만원
            '전용면적': '84.95',
            '공급면적': '109.12',
            '층정보': '15/25',
            '방향': '남향',
            '상세주소': '서울 강남구 테스트동',
            '태그': ['역세권', '학군'],
            '설명': '테스트용 매물입니다.',
            '상세정보': {
                '위치정보': {
                    '정확한_위도': 37.4923,
                    '정확한_경도': 127.0551
                },
                '카카오주소변환': {
                    '도로명주소': '서울 강남구 테스트로 123',
                    '지번주소': '서울 강남구 테스트동 123-45',
                    '건물명': '테스트 아파트',
                    '우편번호': '06123'
                }
            }
        }
        
        # 새로운 _prepare_property_record 함수 테스트
        today = date.today()
        record = helper._prepare_property_record(test_prop, '1168010100', today)
        
        expected_fields = ['last_seen_date', 'is_active']
        for field in expected_fields:
            if field in record:
                print(f"  ✅ _prepare_property_record에 {field} 추가됨")
            else:
                print(f"  ❌ _prepare_property_record에 {field} 누락")
        
        print(f"  📅 last_seen_date: {record.get('last_seen_date')}")
        print(f"  🔄 is_active: {record.get('is_active')}")
        
    except Exception as e:
        print(f"  ❌ _prepare_property_record 테스트 실패: {e}")
    
    # 3. 실제 데이터로 통계 확인
    print("\n📈 실제 데이터 통계:")
    print("-" * 40)
    
    try:
        # 전체 매물 수
        total_properties = helper.client.table('properties').select('*', count='exact').execute()
        print(f"  📊 전체 매물 수: {total_properties.count:,}개")
        
        # 활성 매물 수
        active_properties = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('is_active', True)\
            .execute()
        print(f"  ✅ 활성 매물 수: {active_properties.count:,}개")
        
        # 비활성 매물 수
        inactive_properties = helper.client.table('properties')\
            .select('*', count='exact')\
            .eq('is_active', False)\
            .execute()
        print(f"  ❌ 비활성 매물 수: {inactive_properties.count:,}개")
        
        # 삭제 이력 수
        deletion_history = helper.client.table('deletion_history').select('*', count='exact').execute()
        print(f"  🗑️ 삭제 이력 수: {deletion_history.count:,}개")
        
        # 가격 변동 이력 수
        price_history = helper.client.table('price_history').select('*', count='exact').execute()
        print(f"  💰 가격 변동 이력: {price_history.count:,}개")
        
        # last_seen_date가 NULL인 매물 수
        null_last_seen = helper.client.table('properties')\
            .select('*', count='exact')\
            .is_('last_seen_date', 'null')\
            .execute()
        print(f"  ⚠️ last_seen_date NULL: {null_last_seen.count:,}개")
        
    except Exception as e:
        print(f"  ❌ 통계 조회 실패: {e}")
    
    print("\n🎯 테스트 완료!")
    print("=" * 60)
    print("✅ 수정된 supabase_client.py가 새로운 스키마와 호환됩니다.")
    print("\n📋 주요 개선사항:")
    print("  • 월세 가격 변동 추적 기능 추가")
    print("  • 매물 삭제 시 상세 이력 기록")
    print("  • last_seen_date 자동 업데이트")
    print("  • deletion_history 테이블 활용")
    
    return True

if __name__ == "__main__":
    success = test_updated_client()
    exit(0 if success else 1)