#!/usr/bin/env python3
"""
병렬 수집 실행 스크립트
역삼동과 나머지 지역을 동시에 수집
"""

import subprocess
import sys
import time
from datetime import datetime
import threading

def run_script(script_name, label):
    """개별 스크립트 실행 함수"""
    
    print(f"[{label}] 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 스크립트 실행
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 실시간 출력
        for line in process.stdout:
            print(f"[{label}] {line}", end='')
        
        # 프로세스 종료 대기
        return_code = process.wait()
        
        if return_code == 0:
            print(f"[{label}] 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"[{label}] 실패 (종료 코드: {return_code})")
            
    except Exception as e:
        print(f"[{label}] 오류: {e}")

def main():
    """메인 실행 함수"""
    
    print("="*70)
    print(f"병렬 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("프로세스 1: 역삼동 수집")
    print("프로세스 2: 역삼동 제외 나머지 전체 수집")
    print("="*70)
    
    try:
        # 두 개의 스레드 생성
        thread1 = threading.Thread(
            target=run_script, 
            args=("collect_yeoksam.py", "프로세스1-역삼동")
        )
        
        thread2 = threading.Thread(
            target=run_script,
            args=("collect_except_yeoksam.py", "프로세스2-나머지")
        )
        
        # 스레드 시작
        print("\n두 프로세스를 동시에 시작합니다...\n")
        thread1.start()
        thread2.start()
        
        # 두 스레드가 모두 종료될 때까지 대기
        thread1.join()
        thread2.join()
        
        print("\n" + "="*70)
        print(f"병렬 수집 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n사용자 중단 요청. 모든 프로세스를 종료합니다...")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n예기치 않은 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()