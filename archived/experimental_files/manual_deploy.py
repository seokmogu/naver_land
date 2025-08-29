#!/usr/bin/env python3
import subprocess
import sys
import os

def deploy_files():
    """파일들을 EC2에 수동으로 배포"""
    
    # 필수 파일 목록
    core_files = [
        "emergency_recovery.py",
        "final_safe_collector.py", 
        "completely_safe_collector.py",
        "json_to_db_converter.py",
        "supabase_client.py",
        "ec2_safe_test.sh"
    ]
    
    ec2_host = "naver-ec2"
    remote_dir = "/home/ubuntu/naver_land/collectors"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("🚀 EC2 수동 배포 시작")
    print("=" * 50)
    
    # 1. SSH 연결 확인
    print("\n1️⃣ SSH 연결 확인...")
    try:
        result = subprocess.run([
            "ssh", "-o", "ConnectTimeout=10", 
            ec2_host, "echo '연결 성공'"
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            print("❌ SSH 연결 실패")
            print("STDERR:", result.stderr)
            return False
        else:
            print("✅ SSH 연결 성공")
            
    except Exception as e:
        print(f"❌ SSH 연결 중 오류: {e}")
        return False
    
    # 2. 파일 존재 확인 및 배포
    print("\n2️⃣ 파일 배포...")
    deployed_count = 0
    
    for file in core_files:
        file_path = os.path.join(script_dir, file)
        
        if os.path.exists(file_path):
            try:
                print(f"   📤 {file} 배포 중...")
                result = subprocess.run([
                    "scp", file_path, f"{ec2_host}:{remote_dir}/"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"   ✅ {file} 배포 완료")
                    deployed_count += 1
                else:
                    print(f"   ❌ {file} 배포 실패: {result.stderr}")
                    
            except Exception as e:
                print(f"   ❌ {file} 배포 중 오류: {e}")
        else:
            print(f"   ⚠️ {file} 파일이 존재하지 않음")
    
    # 3. 권한 설정
    print("\n3️⃣ 파일 권한 설정...")
    try:
        result = subprocess.run([
            "ssh", ec2_host, 
            f"chmod +x {remote_dir}/*.sh {remote_dir}/*.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 권한 설정 완료")
        else:
            print(f"⚠️ 권한 설정 중 경고: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 권한 설정 중 오류: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎉 배포 완료! ({deployed_count}/{len(core_files)} 파일)")
    
    if deployed_count == len(core_files):
        print("\n✅ 모든 파일이 성공적으로 배포되었습니다!")
        print("\n다음 단계:")
        print("  ssh naver-ec2")
        print("  cd /home/ubuntu/naver_land/collectors")
        print("  ./ec2_safe_test.sh")
        return True
    else:
        print(f"\n⚠️ {len(core_files) - deployed_count}개 파일 배포 실패")
        return False

if __name__ == "__main__":
    success = deploy_files()
    if not success:
        sys.exit(1)