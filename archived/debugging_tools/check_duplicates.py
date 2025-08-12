#!/usr/bin/env python3
"""
중복 파일 및 데이터 수 확인
"""

import os
import json
from collections import defaultdict

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
            return 0
        
        return len(properties)
    except:
        return 0

def main():
    results_dir = "results"
    
    # 1. parallel_collection 요약에서 예상 수치 추출
    summary_file = os.path.join(results_dir, "parallel_collection_gangnam_20250805_003637.json")
    
    print("📊 요약 파일에서 예상 수치:")
    print("=" * 50)
    
    summary_data = {}
    total_expected = 0
    
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        for result in summary.get('results', []):
            dong_name = result.get('dong_name', '')
            collected_count = result.get('collected_count', 0)
            json_filepath = result.get('json_filepath', '')
            filename = os.path.basename(json_filepath)
            
            summary_data[dong_name] = {
                'expected': collected_count,
                'filename': filename
            }
            total_expected += collected_count
            
            print(f"  {dong_name}: {collected_count:,}개 (파일: {filename})")
    
    print(f"\n📈 요약 파일 총계: {total_expected:,}개")
    
    # 2. 실제 파일들에서 데이터 수 확인
    print("\n" + "=" * 50)
    print("📁 실제 파일들의 데이터 수:")
    print("=" * 50)
    
    actual_files = {}
    dong_files = defaultdict(list)
    total_actual = 0
    
    for filename in os.listdir(results_dir):
        if filename.endswith('.json') and 'parallel_collection' not in filename:
            filepath = os.path.join(results_dir, filename)
            count = count_properties_in_file(filepath)
            
            # 동 이름 추출
            if '강남구_' in filename:
                dong_part = filename.split('강남구_')[1]
                dong_name = dong_part.split('_')[0]
                
                dong_files[dong_name].append({
                    'filename': filename,
                    'count': count,
                    'size': os.path.getsize(filepath)
                })
                
                total_actual += count
                print(f"  {filename}: {count:,}개")
    
    print(f"\n📈 실제 파일 총계: {total_actual:,}개")
    
    # 3. 중복 파일 분석
    print("\n" + "=" * 50)
    print("🔍 동별 파일 분석:")
    print("=" * 50)
    
    duplicates_found = False
    total_from_unique = 0
    
    for dong_name, files in dong_files.items():
        expected = summary_data.get(dong_name, {}).get('expected', 0)
        
        print(f"\n📍 {dong_name}:")
        print(f"  예상: {expected:,}개")
        
        if len(files) > 1:
            duplicates_found = True
            print(f"  ⚠️  중복 파일 {len(files)}개 발견:")
            max_count = 0
            for file_info in files:
                print(f"    - {file_info['filename']}: {file_info['count']:,}개 ({file_info['size']:,} bytes)")
                max_count = max(max_count, file_info['count'])
            total_from_unique += max_count
            print(f"  💡 가장 큰 파일 사용 권장: {max_count:,}개")
        else:
            file_info = files[0]
            print(f"  ✅ 단일 파일: {file_info['count']:,}개")
            total_from_unique += file_info['count']
    
    # 4. 최종 결과
    print("\n" + "=" * 50)
    print("📊 최종 분석 결과:")
    print("=" * 50)
    print(f"요약 파일 예상: {total_expected:,}개")
    print(f"실제 파일 총합: {total_actual:,}개")
    print(f"중복 제거 후: {total_from_unique:,}개")
    print(f"차이: {total_actual - total_from_unique:,}개 (중복)")
    
    if duplicates_found:
        print("\n⚠️  중복 파일이 있습니다!")
        print("💡 업로드 시 가장 큰 파일만 사용하거나, 모든 파일을 업로드하면 중복 제거됩니다.")
    else:
        print("\n✅ 중복 파일 없음")

if __name__ == "__main__":
    main()