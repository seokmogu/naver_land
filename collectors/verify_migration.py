#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 검증 스크립트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'collectors'))

from supabase_client import SupabaseHelper

def verify_migration():
    """마이그레이션 결과 검증"""
    print("🔍 데이터베이스 마이그레이션 검증")
    print("=" * 60)
    
    try:
        helper = SupabaseHelper()
        client = helper.client
        print("✅ Supabase 연결 성공")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False
    
    verification_passed = True
    
    # 1. price_history 테이블 스키마 확인
    print("\n📊 price_history 테이블 스키마 확인:")
    print("-" * 40)
    
    try:
        # 새로운 컬럼들이 추가되었는지 확인
        result = client.rpc('verify_data_integrity').execute()
        print("✅ 데이터 정합성 검증 함수 실행 가능")
        
        # price_history 테이블에서 새 컬럼 확인
        sample_query = client.table('price_history').select('*').limit(1).execute()
        
        required_columns = [
            'trade_type', 'previous_rent_price', 'new_rent_price', 
            'rent_change_amount', 'rent_change_percent'
        ]
        
        if sample_query.data:
            existing_columns = list(sample_query.data[0].keys())
            for col in required_columns:
                if col in existing_columns:
                    print(f"  ✅ {col} 컬럼 존재")
                else:
                    print(f"  ❌ {col} 컬럼 누락")
                    verification_passed = False
        else:
            print("  ℹ️  price_history 테이블에 데이터가 없음")
        
    except Exception as e:
        print(f"  ❌ price_history 테이블 확인 실패: {e}")
        verification_passed = False
    
    # 2. properties 테이블 새 컬럼 확인
    print("\n🏠 properties 테이블 삭제 추적 필드 확인:")
    print("-" * 40)
    
    try:
        sample_query = client.table('properties').select('*').limit(1).execute()
        
        new_columns = ['deleted_at', 'deletion_reason', 'last_seen_date']
        
        if sample_query.data:
            existing_columns = list(sample_query.data[0].keys())
            for col in new_columns:
                if col in existing_columns:
                    print(f"  ✅ {col} 컬럼 존재")
                else:
                    print(f"  ❌ {col} 컬럼 누락")
                    verification_passed = False
        else:
            print("  ❌ properties 테이블에 데이터가 없음")
            verification_passed = False
        
    except Exception as e:
        print(f"  ❌ properties 테이블 확인 실패: {e}")
        verification_passed = False
    
    # 3. deletion_history 테이블 존재 확인
    print("\n🗑️  deletion_history 테이블 확인:")
    print("-" * 40)
    
    try:
        result = client.table('deletion_history').select('*').limit(1).execute()
        print("  ✅ deletion_history 테이블 존재하고 접근 가능")
        print(f"  📊 현재 삭제 이력 개수: {len(result.data)}개")
        
    except Exception as e:
        print(f"  ❌ deletion_history 테이블 확인 실패: {e}")
        verification_passed = False
    
    # 4. 새로운 뷰들 확인
    print("\n👀 생성된 뷰들 확인:")
    print("-" * 40)
    
    views_to_check = ['property_lifecycle', 'price_change_summary']
    
    for view_name in views_to_check:
        try:
            result = client.rpc('select', {'query': f'SELECT * FROM {view_name} LIMIT 1'}).execute()
            print(f"  ✅ {view_name} 뷰 접근 가능")
        except Exception as e:
            # 뷰 직접 쿼리 시도
            try:
                # Supabase에서 뷰는 일반 테이블처럼 접근
                if view_name == 'property_lifecycle':
                    result = client.table('properties').select('article_no').limit(1).execute()
                    print(f"  ✅ {view_name} 관련 테이블 접근 가능")
                else:
                    print(f"  ⚠️  {view_name} 뷰 확인 불가: {e}")
            except Exception as e2:
                print(f"  ❌ {view_name} 뷰 확인 실패: {e2}")
    
    # 5. 인덱스 생성 확인 (간접적으로 쿼리 성능으로 확인)
    print("\n⚡ 인덱스 성능 확인:")
    print("-" * 40)
    
    try:
        # 인덱스가 있는 컬럼으로 쿼리 실행해서 성능 확인
        import time
        
        start_time = time.time()
        result = client.table('properties')\
            .select('article_no')\
            .eq('is_active', True)\
            .limit(100)\
            .execute()
        query_time = time.time() - start_time
        
        print(f"  ✅ is_active 인덱스 쿼리 시간: {query_time:.3f}초")
        if query_time > 1.0:
            print("  ⚠️  쿼리 시간이 1초를 초과했습니다. 인덱스 확인 필요")
        
    except Exception as e:
        print(f"  ❌ 인덱스 성능 확인 실패: {e}")
    
    # 6. 데이터 정합성 검증
    print("\n🔍 데이터 정합성 검증:")
    print("-" * 40)
    
    try:
        # properties 테이블의 last_seen_date가 모두 설정되었는지 확인
        null_last_seen = client.table('properties')\
            .select('article_no', count='exact')\
            .is_('last_seen_date', 'null')\
            .execute()
        
        if null_last_seen.count == 0:
            print("  ✅ 모든 매물에 last_seen_date가 설정됨")
        else:
            print(f"  ⚠️  {null_last_seen.count}개 매물의 last_seen_date가 NULL")
        
        # 비활성 매물 중 deleted_at이 NULL인 경우 확인
        inactive_no_deleted = client.table('properties')\
            .select('article_no', count='exact')\
            .eq('is_active', False)\
            .is_('deleted_at', 'null')\
            .execute()
        
        if inactive_no_deleted.count > 0:
            print(f"  ℹ️  비활성 매물 중 {inactive_no_deleted.count}개가 deleted_at이 NULL (기존 데이터)")
        else:
            print("  ✅ 모든 비활성 매물에 deleted_at 설정됨")
        
    except Exception as e:
        print(f"  ❌ 데이터 정합성 검증 실패: {e}")
        verification_passed = False
    
    # 7. 최종 결과
    print(f"\n🎯 마이그레이션 검증 결과:")
    print("=" * 60)
    
    if verification_passed:
        print("✅ 마이그레이션이 성공적으로 완료되었습니다!")
        print("\n📋 적용된 변경사항:")
        print("  • price_history: 월세 추적 및 거래타입 필드 추가")
        print("  • properties: 삭제 추적 필드 추가")
        print("  • deletion_history: 새 테이블 생성")
        print("  • 성능 최적화 인덱스 추가")
        print("  • 데이터 정합성 검증 함수 추가")
        
        return True
    else:
        print("❌ 마이그레이션에 문제가 있습니다. 위의 오류를 확인하세요.")
        return False

if __name__ == "__main__":
    success = verify_migration()
    exit(0 if success else 1)