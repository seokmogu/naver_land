#!/usr/bin/env python3
"""
종합 테스트 상태 확인 도구
실행 중인 테스트의 상태를 실시간으로 확인
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import glob

def check_test_process():
    """테스트 프로세스 상태 확인"""
    pid_file = Path("comprehensive_test.pid")
    
    if not pid_file.exists():
        return None, "PID 파일을 찾을 수 없습니다"
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # 프로세스 존재 확인
        import psutil
        if psutil.pid_exists(pid):
            proc = psutil.Process(pid)
            return pid, f"실행 중 ({proc.name()})"
        else:
            return pid, "종료됨"
            
    except Exception as e:
        return None, f"PID 확인 오류: {e}"

def get_latest_test_results():
    """최신 테스트 결과 조회"""
    test_dirs = glob.glob("test_results/test_*")
    if not test_dirs:
        return None
        
    # 가장 최신 테스트 디렉토리
    latest_dir = max(test_dirs, key=os.path.getmtime)
    
    # 요약 파일 확인
    summary_file = Path(latest_dir) / "test_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None

def get_log_statistics():
    """로그 파일 통계"""
    stats = {
        'progress_logs': 0,
        'property_data_logs': 0,
        'completed_dongs': 0,
        'active_tasks': 0,
        'latest_activity': None,
        'log_file_sizes': {}
    }
    
    # live_progress.jsonl
    progress_file = Path("logs/live_progress.jsonl")
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            stats['progress_logs'] = len(lines)
            stats['log_file_sizes']['progress'] = f"{progress_file.stat().st_size / 1024:.1f}KB"
            
            if lines:
                try:
                    latest = json.loads(lines[-1].strip())
                    stats['latest_activity'] = latest.get('timestamp')
                except:
                    pass
    
    # collection_data.jsonl
    data_file = Path("logs/collection_data.jsonl")
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            stats['property_data_logs'] = len(f.readlines())
            stats['log_file_sizes']['data'] = f"{data_file.stat().st_size / 1024:.1f}KB"
    
    # status.json
    status_file = Path("logs/status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
            
            for task_info in status_data.values():
                if task_info.get('status') == 'completed':
                    stats['completed_dongs'] += 1
                elif task_info.get('status') == 'started':
                    stats['active_tasks'] += 1
    
    return stats

def check_web_dashboard():
    """웹 대시보드 접근 확인"""
    try:
        import urllib.request
        import urllib.error
        
        # 8888 포트 접근 테스트
        response = urllib.request.urlopen('http://localhost:8888/api/status', timeout=5)
        if response.getcode() == 200:
            return True, "정상 접근"
        else:
            return False, f"HTTP {response.getcode()}"
            
    except urllib.error.URLError as e:
        return False, f"접속 불가: {e.reason}"
    except Exception as e:
        return False, f"확인 오류: {e}"

def print_status_dashboard():
    """상태 대시보드 출력"""
    while True:
        # 화면 클리어 (선택적)
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 네이버 부동산 수집기 종합 테스트 상태")
        print("=" * 70)
        print(f"📅 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 테스트 프로세스 상태
        pid, status = check_test_process()
        print("🔄 테스트 프로세스 상태:")
        if pid:
            print(f"   PID: {pid} | 상태: {status}")
        else:
            print(f"   상태: {status}")
        print()
        
        # 웹 대시보드 상태
        dashboard_ok, dashboard_msg = check_web_dashboard()
        print("🌐 웹 대시보드:")
        print(f"   상태: {'✅ 정상' if dashboard_ok else '❌ 오류'} ({dashboard_msg})")
        print(f"   URL: http://localhost:8888")
        print()
        
        # 로그 통계
        stats = get_log_statistics()
        print("📊 실시간 통계:")
        print(f"   진행 로그: {stats['progress_logs']:,}개 ({stats['log_file_sizes'].get('progress', 'N/A')})")
        print(f"   매물 데이터: {stats['property_data_logs']:,}개 ({stats['log_file_sizes'].get('data', 'N/A')})")
        print(f"   완료된 동: {stats['completed_dongs']}/14개")
        print(f"   진행 중: {stats['active_tasks']}개")
        print(f"   최근 활동: {stats['latest_activity'] or 'N/A'}")
        
        # 진행률 계산
        progress = (stats['completed_dongs'] / 14) * 100
        progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
        print(f"   진행률: [{progress_bar}] {progress:.1f}%")
        print()
        
        # 최신 테스트 결과
        latest_result = get_latest_test_results()
        if latest_result:
            print("📋 최신 테스트 결과:")
            print(f"   테스트 ID: {latest_result['test_id']}")
            print(f"   시작 시간: {latest_result['start_time']}")
            print(f"   상태: {latest_result['status']}")
            if 'success_rate' in latest_result:
                print(f"   성공률: {latest_result['success_rate']:.1f}%")
        print()
        
        # 파일 상태
        print("📁 로그 파일 상태:")
        for log_file in ['logs/live_progress.jsonl', 'logs/collection_data.jsonl', 'logs/status.json']:
            if os.path.exists(log_file):
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                age = datetime.now() - mtime
                age_str = f"{int(age.total_seconds())}초 전" if age.total_seconds() < 60 else f"{int(age.total_seconds()/60)}분 전"
                print(f"   ✅ {log_file} (업데이트: {age_str})")
            else:
                print(f"   ❌ {log_file} (없음)")
        
        print("=" * 70)
        print("🔄 30초마다 자동 갱신 | Ctrl+C로 종료")
        print("🌐 웹 모니터링: http://localhost:8888")
        print("📋 실시간 로그: tail -f logs/live_progress.jsonl")
        
        # 30초 대기
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n🛑 모니터링 종료")
            break

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="종합 테스트 상태 확인")
    parser.add_argument("--quick", action="store_true", help="빠른 상태 확인")
    parser.add_argument("--realtime", action="store_true", help="실시간 모니터링")
    parser.add_argument("--stop", action="store_true", help="테스트 중단")
    
    args = parser.parse_args()
    
    if args.stop:
        # 테스트 중단
        pid_file = Path("comprehensive_test.pid")
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                import psutil
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    proc.terminate()
                    print(f"🛑 테스트 프로세스 중단됨 (PID: {pid})")
                else:
                    print("❌ 실행 중인 테스트가 없습니다")
                
                pid_file.unlink()
                
            except Exception as e:
                print(f"❌ 테스트 중단 오류: {e}")
        else:
            print("❌ 실행 중인 테스트를 찾을 수 없습니다")
    
    elif args.realtime:
        # 실시간 모니터링
        print("🚀 실시간 모니터링 시작...")
        print_status_dashboard()
    
    else:
        # 빠른 상태 확인 (기본값)
        print("🚀 종합 테스트 상태 확인")
        print("=" * 50)
        
        pid, status = check_test_process()
        print(f"🔄 테스트 프로세스: {status}")
        if pid:
            print(f"   PID: {pid}")
        
        dashboard_ok, dashboard_msg = check_web_dashboard()
        print(f"🌐 웹 대시보드: {'정상' if dashboard_ok else '오류'} ({dashboard_msg})")
        
        stats = get_log_statistics()
        print(f"📊 진행 상황:")
        print(f"   완료된 동: {stats['completed_dongs']}/14개")
        print(f"   수집된 매물: {stats['property_data_logs']:,}개")
        print(f"   최근 활동: {stats['latest_activity'] or 'N/A'}")
        
        print("\n💡 더 자세한 정보:")
        print("   python3 check_test_status.py --realtime  # 실시간 모니터링")
        print("   python3 check_test_status.py --stop      # 테스트 중단")
        print("   http://localhost:8888                    # 웹 대시보드")

if __name__ == "__main__":
    main()