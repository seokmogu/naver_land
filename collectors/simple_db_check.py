#!/usr/bin/env python3
"""
간단한 DB 상태 확인
"""

from supabase_client import SupabaseHelper

def main():
    try:
        helper = SupabaseHelper()
        
        # 전체 매물 수
        total_query = helper.client.table('properties').select('*', count='exact').execute()
        total_count = total_query.count
        
        print(f"🏠 전체 매물 수: {total_count:,}개")
        
        # 지역별 매물 수 (강남구만)
        gangnam_regions = [
            '1168010100',  # 역삼동
            '1168010800',  # 논현동  
            '1168010500',  # 삼성동
            '1168010600',  # 대치동
            '1168010400',  # 청담동
            '1168011000',  # 압구정동
            '1168011500',  # 수서동
            '1168011300',  # 율현동
            '1168011200',  # 자곡동
            '1168010300',  # 개포동
            '1168011400',  # 일원동
            '1168011100'   # 세곡동
        ]
        
        region_names = {
            '1168010100': '역삼동',
            '1168010800': '논현동',
            '1168010500': '삼성동', 
            '1168010600': '대치동',
            '1168010400': '청담동',
            '1168011000': '압구정동',
            '1168011500': '수서동',
            '1168011300': '율현동',
            '1168011200': '자곡동',
            '1168010300': '개포동',
            '1168011400': '일원동',
            '1168011100': '세곡동'
        }
        
        print(f"\n📍 강남구 지역별 매물 수:")
        print("-" * 40)
        
        total_gangnam = 0
        for region_code in gangnam_regions:
            query = helper.client.table('properties').select('*', count='exact').eq('cortar_no', region_code).execute()
            count = query.count
            total_gangnam += count
            region_name = region_names.get(region_code, region_code)
            print(f"  {region_name} ({region_code}): {count:,}개")
        
        print(f"\n📊 강남구 총계: {total_gangnam:,}개")
        
        # 오늘 날짜 데이터
        from datetime import date
        today_str = date.today().isoformat()
        today_query = helper.client.table('properties').select('*', count='exact').gte('created_at', today_str).execute()
        today_count = today_query.count
        
        print(f"📅 오늘 등록된 매물: {today_count:,}개")
        
        # 최근 매물 몇 개 샘플 확인
        sample_query = helper.client.table('properties').select('atcl_no, cortar_no, created_at').order('created_at', desc=True).limit(5).execute()
        
        print(f"\n🔍 최근 등록된 매물 샘플:")
        print("-" * 40)
        for prop in sample_query.data:
            print(f"  매물번호: {prop['atcl_no']}, 지역코드: {prop['cortar_no']}, 등록시간: {prop['created_at']}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()