#!/usr/bin/env python3
"""
통합 종합 테스트 실행기
- 코드 정리 → 프로세스 관리 → 백그라운드 테스트 실행
- 모든 작업을 하나의 스크립트로 통합 실행
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    """통합 테스트 실행"""
    print("🚀 네이버 부동산 수집기 - 통합 종합 테스트 시작")
    print("=" * 70)
    
    # collectors 디렉토리로 이동
    collectors_dir = Path(__file__).parent / "collectors"
    if not collectors_dir.exists():
        print("❌ collectors 디렉토리를 찾을 수 없습니다")
        return False
    
    os.chdir(collectors_dir)
    print(f"📁 작업 디렉토리: {os.getcwd()}")
    
    # 실행 파일들 권한 부여
    scripts = [
        "comprehensive_test.py",
        "start_comprehensive_test.sh", 
        "check_test_status.py",
        "simple_monitor.py",
        "log_based_collector.py"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            os.chmod(script, 0o755)
            
    print("✅ 스크립트 권한 설정 완료")
    
    # Python 종속성 확인
    try:
        import psutil
        print("✅ psutil 모듈 확인 완료")
    except ImportError:
        print("❌ psutil 모듈 설치 필요: pip install psutil")
        print("   자동 설치 시도...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
            print("✅ psutil 설치 완료")
        except subprocess.CalledProcessError:
            print("❌ psutil 설치 실패")
            return False
    
    # 종합 테스트 실행
    print("\n🔄 종합 테스트 실행 중...")
    print("   📊 실시간 웹 모니터링: http://localhost:8888")
    print("   📋 CLI 상태 확인: python3 check_test_status.py --realtime")
    print("   🛑 테스트 중단: python3 check_test_status.py --stop")
    print()
    
    try:
        # 백그라운드로 종합 테스트 실행
        result = subprocess.run([
            sys.executable, "comprehensive_test.py"
        ], cwd=os.getcwd())
        
        if result.returncode == 0:
            print("\n🎉 종합 테스트가 성공적으로 완료되었습니다!")
            
            # 간단한 결과 요약
            print("\n📊 빠른 결과 확인:")
            subprocess.run([sys.executable, "check_test_status.py", "--quick"])
            
            return True
        else:
            print(f"\n❌ 종합 테스트가 실패했습니다 (종료코드: {result.returncode})")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단되었습니다")
        return False
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)