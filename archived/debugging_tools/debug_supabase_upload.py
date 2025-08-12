#!/usr/bin/env python3
"""
Supabase 업로드 과정 디버깅
"""
import json
from supabase_client import SupabaseHelper

def main():
    filename = "results/naver_streaming_강남구_대치동_1168010600_20250805_023929.json"
    cortar_no = "1168010600"
    
    print("🔍 Supabase 업로드 과정 디버깅")
    print("=" * 60)
    
    # 1. 파일 로드
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    properties = data.get('매물목록', [])
    print(f"📁 로드된 매물 수: {len(properties):,}개")
    
    # 2. Helper 초기화
    helper = SupabaseHelper()
    
    # 3. 기존 데이터 확인
    existing_query = helper.client.table('properties').select('article_no', count='exact').eq('cortar_no', cortar_no).execute()
    print(f"📊 기존 DB 매물 수: {existing_query.count:,}개")
    
    # 4. 작은 배치로 테스트 (처음 100개만)
    print(f"\n🧪 테스트: 처음 100개만 업로드")
    test_properties = properties[:100]
    
    try:
        result = helper.save_properties(test_properties, cortar_no)
        print(f"✅ 테스트 결과: {result}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. 전체 업로드 시도
    print(f"\n🚀 전체 업로드: {len(properties):,}개")
    
    try:
        full_result = helper.save_properties(properties, cortar_no)
        print(f"✅ 전체 결과: {full_result}")
    except Exception as e:
        print(f"❌ 전체 업로드 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. 최종 DB 상태 확인
    final_query = helper.client.table('properties').select('article_no', count='exact').eq('cortar_no', cortar_no).execute()
    print(f"📊 최종 DB 매물 수: {final_query.count:,}개")

if __name__ == "__main__":
    main()