#!/usr/bin/env python3
"""
시스템 테스트 실행 스크립트
- collectors 디렉토리로 이동 후 테스트 실행
- 백그라운드 모드로 실행하여 세션 독립성 보장
"""

import os
import sys
import subprocess
import time

def main():
    # collectors 디렉토리로 이동
    collectors_dir = os.path.join(os.getcwd(), "collectors")
    
    if not os.path.exists(collectors_dir):
        print("❌ collectors 디렉토리를 찾을 수 없습니다.")
        print(f"현재 경로: {os.getcwd()}")
        return False
    
    print(f"📁 작업 디렉토리로 이동: {collectors_dir}")
    os.chdir(collectors_dir)
    
    # 필요한 Python 파일들 실행권한 확인
    python_files = [
        "test_runner.py",
        "quick_system_check.py", 
        "comprehensive_system_test.py"
    ]
    
    for py_file in python_files:
        if not os.path.exists(py_file):
            print(f"❌ 필수 파일 누락: {py_file}")
            return False
    
    print("✅ 모든 필수 파일 확인됨")
    
    # 백그라운드로 통합 테스트 실행
    print("\n🚀 네이버 부동산 수집기 종합 테스트 시작")
    print("="*60)
    
    try:
        # 통합 테스트 실행 (백그라운드)
        result = subprocess.run([
            sys.executable, "test_runner.py", "--background"
        ], text=True)
        
        if result.returncode == 0:
            print("✅ 테스트가 성공적으로 완료되었습니다!")
            
            # 결과 파일들 확인
            if os.path.exists('test_results'):
                result_files = os.listdir('test_results')
                if result_files:
                    print("\n📄 생성된 결과 파일:")
                    for file in result_files:
                        print(f"  - {file}")
            
            # 웹 모니터링 정보
            print("\n🌐 웹 모니터링 대시보드:")
            print("  http://localhost:8889 또는 http://localhost:8888")
            
            return True
        else:
            print(f"❌ 테스트 실행 실패 (코드: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)