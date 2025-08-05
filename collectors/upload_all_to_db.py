#!/usr/bin/env python3
"""
results 폴더의 모든 JSON 파일을 Supabase에 업로드
"""

import os
import json
import subprocess
from datetime import datetime

def extract_cortar_no_from_filename(filename):
    """파일명에서 지역코드 추출"""
    parts = filename.split('_')
    for part in parts:
        if part.isdigit() and len(part) == 10:
            return part
    return None

def main():
    results_dir = "results"
    json_files = []
    
    # JSON 파일 목록 수집 (parallel_collection 제외)
    for filename in os.listdir(results_dir):
        if filename.endswith('.json') and 'parallel_collection' not in filename:
            filepath = os.path.join(results_dir, filename)
            cortar_no = extract_cortar_no_from_filename(filename)
            if cortar_no:
                file_size = os.path.getsize(filepath)
                json_files.append((filepath, cortar_no, filename, file_size))
    
    # 파일 크기순으로 정렬 (작은 것부터)
    json_files.sort(key=lambda x: x[3])
    
    print(f"📊 총 {len(json_files)}개 파일을 업로드합니다.")
    print("=" * 60)
    
    # 파일 크기 정보 출력
    print("\n📁 파일 크기 정보:")
    for filepath, cortar_no, filename, file_size in json_files:
        print(f"  - {filename}: {file_size:,} bytes")
    
    success_count = 0
    fail_count = 0
    total_properties = 0
    failed_files = []
    
    # 각 파일 업로드
    for i, (filepath, cortar_no, filename, file_size) in enumerate(json_files):
        print(f"\n[{i+1}/{len(json_files)}] 업로드 중: {filename}")
        print(f"  - 지역코드: {cortar_no}")
        print(f"  - 파일 크기: {file_size:,} bytes")
        
        # python 실행
        cmd = ["./venv/bin/python", "json_to_supabase.py", filepath, cortar_no]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5분 타임아웃
            
            if result.returncode == 0:
                # 성공 메시지에서 매물 수 추출
                output_lines = result.stdout.strip().split('\n')
                property_count = 0
                for line in output_lines:
                    if '전체 처리 완료:' in line:
                        count_str = line.split(':')[1].strip().split('개')[0]
                        property_count = int(count_str)
                        total_properties += property_count
                        print(f"  ✅ 성공: {property_count}개 매물 저장")
                        break
                success_count += 1
            else:
                print(f"  ❌ 실패: {result.stderr}")
                fail_count += 1
                failed_files.append(filename)
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ 타임아웃 (5분 초과)")
            fail_count += 1
            failed_files.append(filename)
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            fail_count += 1
            failed_files.append(filename)
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("📊 업로드 완료 요약:")
    print(f"  - 전체 파일: {len(json_files)}개")
    print(f"  - 성공: {success_count}개")
    print(f"  - 실패: {fail_count}개")
    print(f"  - 총 매물 수: {total_properties:,}개")
    
    if failed_files:
        print(f"\n❌ 실패한 파일들:")
        for f in failed_files:
            print(f"  - {f}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()