#!/usr/bin/env python3
"""
DB와 수집 데이터 정합성 검증
"""

import os
import json
from datetime import date
from supabase_client import SupabaseHelper

def count_properties_in_file(filepath):
    """JSON 파일의 매물 수 카운트"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            properties = data.get('매물목록', [])
        elif isinstance(data, list):
            properties = data
        else:
            return 0, []
        
        return len(properties), properties
    except Exception as e:
        print(f"❌ 파일 읽기 오류 {filepath}: {e}")
        return 0, []

def extract_cortar_no_from_filename(filename):
    """파일명에서 지역코드 추출"""
    parts = filename.split('_')
    for part in parts:
        if part.isdigit() and len(part) == 10:
            return part
    return None

def main():
    print("🔍 DB와 수집 데이터 정합성 검증")
    print("=" * 60)
    
    # 1. Supabase 연결
    try:
        helper = SupabaseHelper()
        print("✅ Supabase 연결 성공")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return
    
    # 2. 수집 데이터 분석
    results_dir = "results"
    collection_data = {}
    total_collected = 0
    
    print("\n📁 수집된 데이터 분석:")
    print("-" * 40)
    
    for filename in os.listdir(results_dir):
        if filename.endswith('.json') and 'parallel_collection' not in filename:
            filepath = os.path.join(results_dir, filename)
            cortar_no = extract_cortar_no_from_filename(filename)
            
            if cortar_no:
                count, properties = count_properties_in_file(filepath)
                
                if cortar_no not in collection_data:
                    collection_data[cortar_no] = {
                        'files': [],
                        'total_count': 0,
                        'unique_properties': set()
                    }
                
                # 매물번호로 중복 체크
                property_ids = set()
                for prop in properties:
                    if '매물번호' in prop:
                        property_ids.add(prop['매물번호'])
                
                collection_data[cortar_no]['files'].append({
                    'filename': filename,
                    'count': count,
                    'property_ids': property_ids
                })
                collection_data[cortar_no]['total_count'] += count
                collection_data[cortar_no]['unique_properties'].update(property_ids)
                
                total_collected += count
                
                # 동 이름 추출
                dong_name = ""
                if '강남구_' in filename:
                    dong_part = filename.split('강남구_')[1]
                    dong_name = dong_part.split('_')[0]
                
                print(f"  {dong_name} ({cortar_no}): {count:,}개")
    
    print(f"\n📊 수집 데이터 총계: {total_collected:,}개")
    
    # 중복 제거 후 실제 유니크 매물 수
    total_unique_collected = 0
    print("\n🔍 지역별 중복 제거 분석:")
    print("-" * 40)
    
    for cortar_no, data in collection_data.items():
        unique_count = len(data['unique_properties'])
        file_count = len(data['files'])
        total_count = data['total_count']
        
        total_unique_collected += unique_count
        
        status = "✅" if file_count == 1 else "⚠️"
        print(f"  {cortar_no}: {unique_count:,}개 (파일 {file_count}개, 총 {total_count:,}개) {status}")
        
        if file_count > 1:
            for file_info in data['files']:
                print(f"    - {file_info['filename']}: {file_info['count']:,}개")
    
    print(f"\n📊 중복 제거 후 유니크 매물: {total_unique_collected:,}개")
    
    # 3. DB 데이터 확인
    print("\n💾 DB 저장된 데이터 확인:")
    print("-" * 40)
    
    try:
        # 전체 매물 수
        total_db_query = helper.client.table('properties').select('*', count='exact').execute()
        total_db_count = total_db_query.count
        print(f"  전체 매물 수: {total_db_count:,}개")
        
        # 지역별 매물 수
        db_by_region = {}
        for cortar_no in collection_data.keys():
            region_query = helper.client.table('properties').select('*', count='exact').eq('cortar_no', cortar_no).execute()
            region_count = region_query.count
            db_by_region[cortar_no] = region_count
            print(f"  {cortar_no}: {region_count:,}개")
        
        # 오늘 날짜 매물만 확인
        today_str = date.today().isoformat()
        today_query = helper.client.table('properties').select('*', count='exact').gte('created_at', today_str).execute()
        today_count = today_query.count
        print(f"  오늘 등록된 매물: {today_count:,}개")
        
    except Exception as e:
        print(f"❌ DB 쿼리 실패: {e}")
        return
    
    # 4. 정합성 검증
    print("\n🔍 정합성 검증 결과:")
    print("=" * 60)
    
    print(f"수집 데이터 (중복 제거 전): {total_collected:,}개")
    print(f"수집 데이터 (중복 제거 후): {total_unique_collected:,}개")
    print(f"DB 저장된 데이터 (전체): {total_db_count:,}개")
    print(f"DB 저장된 데이터 (오늘): {today_count:,}개")
    
    # 지역별 비교
    print(f"\n📊 지역별 정합성:")
    print("-" * 40)
    
    all_match = True
    for cortar_no in collection_data.keys():
        collected_unique = len(collection_data[cortar_no]['unique_properties'])
        db_count = db_by_region.get(cortar_no, 0)
        
        match_status = "✅" if collected_unique == db_count else "❌"
        if collected_unique != db_count:
            all_match = False
        
        diff = db_count - collected_unique
        diff_str = f" (차이: {diff:+d})" if diff != 0 else ""
        
        print(f"  {cortar_no}: 수집 {collected_unique:,}개 → DB {db_count:,}개 {match_status}{diff_str}")
    
    # 최종 결과
    print(f"\n🎯 최종 결과:")
    print("-" * 40)
    
    if all_match and total_unique_collected == today_count:
        print("✅ 정합성 검증 통과!")
        print("   수집된 모든 데이터가 DB에 정상적으로 저장되었습니다.")
    elif total_unique_collected <= total_db_count:
        print("⚠️  DB에 더 많은 데이터가 있습니다.")
        print("   이전 데이터나 다른 수집 작업의 데이터가 포함된 것 같습니다.")
    else:
        print("❌ 데이터 불일치 발견!")
        print("   일부 데이터가 DB에 저장되지 않았을 수 있습니다.")
    
    print("\n💡 참고사항:")
    print("- DB 전체 데이터에는 이전 수집 데이터도 포함될 수 있습니다.")
    print("- 중복 매물은 매물번호 기준으로 자동 제거됩니다.")
    print("- 가격 변동은 별도 테이블(price_history)에 기록됩니다.")

if __name__ == "__main__":
    main()