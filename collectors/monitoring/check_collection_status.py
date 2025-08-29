#!/usr/bin/env python3
"""
로그 기반 수집기 상태 확인 도구
실시간으로 수집 진행 상황을 모니터링
"""

import json
import os
import time
from datetime import datetime
import glob

def check_logs():
    """로그 파일들 상태 확인"""
    print("📊 로그 파일 상태 확인")
    print("=" * 50)
    
    # 1. 상태 요약 확인
    status_file = "logs/status.json"
    if os.path.exists(status_file):
        with open(status_file, 'r', encoding='utf-8') as f:
            status = json.load(f)
        
        active = [k for k, v in status.items() if v.get('status') == 'in_progress']
        completed = [k for k, v in status.items() if v.get('status') == 'completed']
        failed = [k for k, v in status.items() if v.get('status') == 'failed']
        
        print(f"🔄 진행 중: {len(active)}개")
        print(f"✅ 완료: {len(completed)}개")
        print(f"❌ 실패: {len(failed)}개")
        
        if active:
            print(f"\n🔄 현재 진행 중인 작업:")
            for task in active:
                task_info = status[task]
                details = task_info.get('details', {})
                dong_name = details.get('dong_name', 'Unknown')
                total_collected = details.get('total_collected', 0)
                print(f"   - {dong_name}: {total_collected}개 수집 완료")
        
        if completed:
            print(f"\n✅ 완료된 작업:")
            for task in completed:
                task_info = status[task]
                details = task_info.get('details', {})
                dong_name = details.get('dong_name', 'Unknown')
                total_collected = details.get('total_collected', 0)
                print(f"   - {dong_name}: {total_collected}개 매물")
    else:
        print("❌ status.json 파일을 찾을 수 없습니다.")
    
    print()

def check_result_files():
    """수집 결과 파일들 확인"""
    print("📁 수집 결과 파일 확인")  
    print("=" * 50)
    
    result_files = glob.glob("results/naver_optimized_*.json")
    result_files.sort(key=os.path.getmtime, reverse=True)  # 최신순 정렬
    
    if result_files:
        print(f"총 {len(result_files)}개 결과 파일 발견")
        print("\n📅 최근 5개 파일:")
        
        for i, filepath in enumerate(result_files[:5]):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 매물 개수 계산
                if isinstance(data, dict):
                    if '매물목록' in data:
                        property_count = len(data['매물목록'])
                    elif 'properties' in data:
                        property_count = len(data['properties'])
                    else:
                        property_count = 0
                else:
                    property_count = 0
                
                # 파일 정보 추출
                filename = os.path.basename(filepath)
                file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
                mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                print(f"   {i+1}. {filename}")
                print(f"      📊 매물 수: {property_count}개")
                print(f"      💾 크기: {file_size:.1f}MB")
                print(f"      🕐 수정시간: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
            except Exception as e:
                print(f"   ❌ {filepath} 읽기 실패: {e}")
    else:
        print("❌ 수집 결과 파일을 찾을 수 없습니다.")
    
    print()

def check_recent_activity():
    """최근 활동 확인"""
    print("🕐 최근 활동 확인")
    print("=" * 50)
    
    progress_file = "logs/live_progress.jsonl"
    if os.path.exists(progress_file):
        try:
            # 마지막 10줄 읽기
            with open(progress_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            recent_lines = lines[-10:] if len(lines) >= 10 else lines
            
            print("📋 최근 10개 활동:")
            for line in recent_lines:
                try:
                    entry = json.loads(line.strip())
                    timestamp = entry.get('timestamp', 'Unknown')
                    entry_type = entry.get('type', 'Unknown')
                    dong_name = entry.get('dong_name', '')
                    total = entry.get('total_collected', '')
                    
                    if entry_type == 'start':
                        print(f"   🚀 {timestamp}: {dong_name} 수집 시작")
                    elif entry_type == 'complete':
                        print(f"   ✅ {timestamp}: {dong_name} 완료 ({total}개)")
                    elif entry_type == 'heartbeat' and total:
                        print(f"   🔄 {timestamp}: {dong_name} 진행 중 ({total}개)")
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            print(f"❌ 진행 로그 읽기 실패: {e}")
    else:
        print("❌ live_progress.jsonl 파일을 찾을 수 없습니다.")
    
    print()

def check_collection_data():
    """수집 데이터 로그 확인"""
    print("📄 수집 데이터 로그 확인")
    print("=" * 50)
    
    data_file = "logs/collection_data.jsonl"
    if os.path.exists(data_file):
        try:
            line_count = sum(1 for _ in open(data_file, 'r', encoding='utf-8'))
            file_size = os.path.getsize(data_file) / 1024 / 1024  # MB
            
            print(f"📊 데이터 로그 항목: {line_count:,}개")
            print(f"💾 파일 크기: {file_size:.1f}MB")
            
            # 마지막 몇 개 항목 확인
            with open(data_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            recent_data = lines[-3:] if len(lines) >= 3 else lines
            print(f"\n📋 최근 데이터 항목 {len(recent_data)}개:")
            
            for line in recent_data:
                try:
                    entry = json.loads(line.strip())
                    data_type = entry.get('type', 'Unknown')
                    dong_name = entry.get('task_id', 'Unknown').split('_')[0]
                    
                    if data_type == 'property':
                        data_info = entry.get('data', {})
                        property_name = data_info.get('article_name', 'Unknown')
                        print(f"   🏠 매물 데이터: {dong_name} - {property_name}")
                    elif data_type == 'summary':
                        data_info = entry.get('data', {})
                        total = data_info.get('total_properties', 'Unknown')
                        print(f"   📊 수집 요약: {dong_name} - {total}개 매물")
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            print(f"❌ 데이터 로그 읽기 실패: {e}")
    else:
        print("❌ collection_data.jsonl 파일을 찾을 수 없습니다.")
    
    print()

def main():
    """메인 함수"""
    print("🔍 로그 기반 수집기 상태 점검")
    print("=" * 80)
    print(f"⏰ 점검 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # 현재 디렉토리 확인
    if not os.path.exists("logs") and not os.path.exists("results"):
        print("❌ logs/ 또는 results/ 디렉토리를 찾을 수 없습니다.")
        print("💡 collectors/ 디렉토리에서 실행해주세요.")
        return
    
    check_logs()
    check_result_files() 
    check_recent_activity()
    check_collection_data()
    
    print("=" * 80)
    print("🎯 권장 명령어:")
    print("   실시간 모니터링: tail -f logs/live_progress.jsonl")
    print("   상태 확인: cat logs/status.json | python -m json.tool")
    print("   단일 테스트: python log_based_collector.py --test-single 역삼동")
    print("=" * 80)

if __name__ == "__main__":
    main()