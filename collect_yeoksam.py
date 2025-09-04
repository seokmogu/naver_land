#!/usr/bin/env python3
"""
역삼동 전용 수집 스크립트
역삼동(1168010100)의 모든 매물을 수집
"""

import subprocess
import sys
import time
from datetime import datetime

def main():
    """역삼동 매물 수집 메인 함수"""
    
    print("="*60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 역삼동 매물 수집 시작")
    print("지역 코드: 1168010100")
    print("="*60)
    
    # 역삼동 수집 명령어
    cmd = [
        sys.executable, "main.py",
        "--area", "1168010100",
        "--max-pages", "100"  # 모든 페이지 수집
    ]
    
    try:
        # 수집 프로세스 실행
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 실시간 출력
        for line in process.stdout:
            print(f"[역삼동] {line}", end='')
        
        # 프로세스 종료 대기
        return_code = process.wait()
        
        if return_code == 0:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 역삼동 수집 완료")
        else:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 역삼동 수집 실패 (종료 코드: {return_code})")
            
    except KeyboardInterrupt:
        print("\n\n사용자 중단 요청. 프로세스를 종료합니다...")
        process.terminate()
        process.wait()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()