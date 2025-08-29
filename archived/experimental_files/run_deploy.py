#!/usr/bin/env python3
import subprocess
import sys
import os

def run_deploy():
    """배포 스크립트 실행"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    deploy_script = os.path.join(script_dir, "deploy.sh")
    
    # 실행 권한 부여
    os.chmod(deploy_script, 0o755)
    
    # 배포 스크립트 실행
    try:
        result = subprocess.run([deploy_script], cwd=script_dir, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"배포 실행 중 오류: {e}")
        return False

if __name__ == "__main__":
    success = run_deploy()
    if not success:
        sys.exit(1)