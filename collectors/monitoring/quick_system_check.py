#!/usr/bin/env python3
"""
빠른 시스템 상태 체크
- 핵심 컴포넌트들의 기본 동작 확인
- 종합 테스트 전 사전 점검용
"""

import os
import sys
import json
import time
from datetime import datetime
import subprocess

def check_file_exists(filepath, description):
    """파일 존재 여부 확인"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"  {status} {description}: {filepath}")
    return exists

def check_python_module(module_name):
    """Python 모듈 import 확인"""
    try:
        __import__(module_name)
        print(f"  ✅ {module_name} 모듈")
        return True
    except ImportError as e:
        print(f"  ❌ {module_name} 모듈: {e}")
        return False

def check_database_connection():
    """데이터베이스 연결 확인"""
    try:
        from supabase_client import SupabaseHelper
        helper = SupabaseHelper()
        
        # 간단한 쿼리로 연결 테스트
        start_time = time.time()
        result = helper.client.table('properties').select('count', count='exact').limit(1).execute()
        response_time = (time.time() - start_time) * 1000
        
        print(f"  ✅ 데이터베이스 연결: {response_time:.1f}ms")
        return True
    except Exception as e:
        print(f"  ❌ 데이터베이스 연결: {e}")
        return False

def check_log_system():
    """로그 시스템 기본 확인"""
    try:
        from integrated_logger import IntegratedProgressTracker, LogLevel
        
        # 간단한 로그 테스트
        tracker = IntegratedProgressTracker(log_dir="./quick_check_logs", log_level=LogLevel.DEBUG)
        tracker.enhanced_logger.info("quick_check", "로그 시스템 테스트")
        
        # 로그 파일 생성 확인
        log_dir_exists = os.path.exists("quick_check_logs")
        tracker.close()
        
        if log_dir_exists:
            print("  ✅ 통합 로그 시스템")
            return True
        else:
            print("  ❌ 통합 로그 시스템: 로그 디렉토리 생성 실패")
            return False
    except Exception as e:
        print(f"  ❌ 통합 로그 시스템: {e}")
        return False

def check_collector_system():
    """수집기 시스템 기본 확인"""
    try:
        from unified_collector import UnifiedCollector
        
        collector = UnifiedCollector()
        
        # 헬스 체크 테스트
        health_result = collector.health_check("1168010100")  # 역삼동
        
        if health_result.get('total_properties') is not None:
            print(f"  ✅ 통합 수집기: {health_result.get('total_properties', 0)}개 매물 확인")
            return True
        else:
            print("  ❌ 통합 수집기: 헬스 체크 실패")
            return False
    except Exception as e:
        print(f"  ❌ 통합 수집기: {e}")
        return False

def check_web_monitor():
    """웹 모니터링 시스템 확인"""
    try:
        import requests
        
        # 이미 실행 중인 모니터 확인
        test_ports = [8888, 8889]
        running_monitor = None
        
        for port in test_ports:
            try:
                response = requests.get(f"http://localhost:{port}/api/status", timeout=3)
                if response.status_code == 200:
                    running_monitor = port
                    break
            except:
                continue
        
        if running_monitor:
            print(f"  ✅ 웹 모니터링: http://localhost:{running_monitor} 실행 중")
            return True
        else:
            print("  ⚠️ 웹 모니터링: 실행 중인 서버 없음 (정상 - 필요시 시작됨)")
            return True
    except Exception as e:
        print(f"  ❌ 웹 모니터링 준비: {e}")
        return False

def check_system_resources():
    """시스템 리소스 확인"""
    try:
        import psutil
        
        # 메모리 확인
        memory = psutil.virtual_memory()
        memory_gb = memory.total / 1024 / 1024 / 1024
        memory_used_percent = memory.percent
        
        # 디스크 확인
        disk = psutil.disk_usage('.')
        disk_gb = disk.total / 1024 / 1024 / 1024
        disk_used_percent = (disk.used / disk.total) * 100
        
        print(f"  📊 메모리: {memory_gb:.1f}GB 총용량, {memory_used_percent:.1f}% 사용 중")
        print(f"  💾 디스크: {disk_gb:.1f}GB 총용량, {disk_used_percent:.1f}% 사용 중")
        
        # 경고 조건
        warnings = []
        if memory_used_percent > 80:
            warnings.append("메모리 사용량이 높습니다")
        if disk_used_percent > 90:
            warnings.append("디스크 공간이 부족합니다")
        
        if warnings:
            for warning in warnings:
                print(f"  ⚠️ {warning}")
            return False
        else:
            print("  ✅ 시스템 리소스 충분")
            return True
            
    except Exception as e:
        print(f"  ❌ 시스템 리소스 확인: {e}")
        return False

def main():
    """메인 체크 함수"""
    print("🔍 네이버 부동산 수집기 시스템 상태 빠른 점검")
    print("=" * 60)
    
    check_results = {}
    
    # 1. 핵심 파일 존재 확인
    print("\n📁 1. 핵심 파일 확인")
    files_to_check = [
        ("unified_collector.py", "통합 수집기"),
        ("integrated_logger.py", "통합 로거"),
        ("simple_monitor.py", "웹 모니터"),
        ("supabase_client.py", "DB 클라이언트"),
        ("comprehensive_system_test.py", "종합 테스트")
    ]
    
    file_check_results = []
    for filepath, description in files_to_check:
        result = check_file_exists(filepath, description)
        file_check_results.append(result)
    
    check_results['core_files'] = all(file_check_results)
    
    # 2. Python 모듈 확인
    print("\n📦 2. Python 모듈 확인")
    modules_to_check = ['requests', 'psutil', 'pytz', 'json', 'threading']
    
    module_check_results = []
    for module in modules_to_check:
        result = check_python_module(module)
        module_check_results.append(result)
    
    check_results['python_modules'] = all(module_check_results)
    
    # 3. 데이터베이스 연결 확인
    print("\n🗄️ 3. 데이터베이스 연결 확인")
    check_results['database'] = check_database_connection()
    
    # 4. 로그 시스템 확인
    print("\n📋 4. 로그 시스템 확인")
    check_results['logging_system'] = check_log_system()
    
    # 5. 수집기 시스템 확인
    print("\n🚀 5. 수집기 시스템 확인")
    check_results['collector_system'] = check_collector_system()
    
    # 6. 웹 모니터링 준비 확인
    print("\n🌐 6. 웹 모니터링 준비 확인")
    check_results['web_monitoring'] = check_web_monitor()
    
    # 7. 시스템 리소스 확인
    print("\n💻 7. 시스템 리소스 확인")
    check_results['system_resources'] = check_system_resources()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 점검 결과 요약")
    print("=" * 60)
    
    total_checks = len(check_results)
    passed_checks = sum(1 for result in check_results.values() if result)
    pass_rate = (passed_checks / total_checks) * 100
    
    print(f"📈 전체 통과율: {passed_checks}/{total_checks} ({pass_rate:.1f}%)")
    
    for check_name, result in check_results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  - {check_name}: {status}")
    
    # 권장사항
    print("\n💡 권장사항")
    if pass_rate >= 90:
        print("  ✅ 시스템이 종합 테스트를 실행할 준비가 되었습니다.")
        print("  🚀 다음 명령으로 종합 테스트를 실행하세요:")
        print("    ./run_comprehensive_test.sh")
    elif pass_rate >= 70:
        print("  ⚠️ 일부 문제가 있지만 기본적인 테스트는 가능합니다.")
        print("  🔧 실패한 항목들을 점검 후 테스트 실행을 권장합니다.")
    else:
        print("  ❌ 주요 시스템에 문제가 있습니다.")
        print("  🛠️ 실패한 항목들을 먼저 해결해주세요.")
    
    # 결과 저장
    result_data = {
        'check_time': datetime.now().isoformat(),
        'pass_rate': pass_rate,
        'results': check_results,
        'recommendation': 'ready' if pass_rate >= 90 else 'partial' if pass_rate >= 70 else 'not_ready'
    }
    
    os.makedirs('test_logs', exist_ok=True)
    with open('test_logs/quick_check_result.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 상세 결과: test_logs/quick_check_result.json")
    
    return pass_rate >= 70  # 70% 이상이면 성공

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)