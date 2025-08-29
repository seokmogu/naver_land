#!/usr/bin/env python3
import subprocess
import sys

def check_ssh_connection():
    """SSH 연결 확인"""
    try:
        print("🔍 SSH 연결 테스트 중...")
        result = subprocess.run([
            "ssh", "-o", "ConnectTimeout=10", 
            "naver-ec2", "echo '연결 성공'"
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ SSH 연결 성공")
            print(result.stdout.strip())
            return True
        else:
            print("❌ SSH 연결 실패")
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ SSH 연결 타임아웃 (15초)")
        return False
    except Exception as e:
        print(f"❌ SSH 연결 중 오류: {e}")
        return False

if __name__ == "__main__":
    if check_ssh_connection():
        print("\n✅ SSH 연결이 정상적으로 작동합니다.")
        print("이제 배포를 진행할 수 있습니다.")
    else:
        print("\n❌ SSH 연결에 문제가 있습니다.")
        print("다음을 확인해주세요:")
        print("1. SSH 키 설정이 올바른지 확인")
        print("2. EC2 인스턴스가 실행 중인지 확인") 
        print("3. 보안 그룹 설정 확인")
        sys.exit(1)