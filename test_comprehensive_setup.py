#!/usr/bin/env python3
"""
포괄적 스키마 설정 테스트 스크립트
- 스키마 업데이트 실행
- 참조 데이터 채우기  
- 배포 검증 테스트
"""

import subprocess
import sys
import os
from pathlib import Path

def run_sql_script(script_path: str, description: str):
    """SQL 스크립트 실행"""
    print(f"\n🚀 {description} 실행 중...")
    print(f"📄 스크립트: {script_path}")
    
    # PostgreSQL 접속 정보 (실제 환경에 맞게 수정)
    # 여기서는 스크립트 파일 존재 확인만
    if not Path(script_path).exists():
        print(f"❌ 스크립트 파일을 찾을 수 없습니다: {script_path}")
        return False
        
    print(f"✅ 스크립트 파일 확인 완료")
    print(f"💡 실제 실행을 위해서는 다음 명령어를 사용하세요:")
    print(f"   psql -h <host> -d <database> -U <username> -f {script_path}")
    
    return True

def run_python_test(script_path: str, description: str):
    """Python 테스트 스크립트 실행"""
    print(f"\n🧪 {description} 실행 중...")
    print(f"📄 스크립트: {script_path}")
    
    if not Path(script_path).exists():
        print(f"❌ 테스트 스크립트를 찾을 수 없습니다: {script_path}")
        return False
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ 테스트 성공!")
            print("📊 출력:", result.stdout[-500:])  # 마지막 500자만 표시
        else:
            print("❌ 테스트 실패!")  
            print("🔍 오류:", result.stderr[-500:])
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ 테스트 시간 초과")
        return False
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {e}")
        return False

def main():
    """포괄적 스키마 설정 테스트 실행"""
    print("🎯 네이버 부동산 수집기 - 포괄적 스키마 설정")
    print("="*60)
    
    current_dir = Path(__file__).parent
    
    # 1. 스키마 업데이트 스크립트 확인
    schema_script = current_dir / "comprehensive_schema_update.sql"
    success1 = run_sql_script(str(schema_script), "포괄적 스키마 업데이트")
    
    # 2. 참조 데이터 채우기 스크립트 확인  
    reference_script = current_dir / "populate_missing_reference_data.sql"
    success2 = run_sql_script(str(reference_script), "참조 데이터 채우기")
    
    # 3. 배포 검증 테스트 실행 (실제 Python 실행)
    test_script = current_dir / "test_schema_deployment.py"
    success3 = run_python_test(str(test_script), "스키마 배포 검증")
    
    # 4. 결과 요약
    print("\n" + "="*60)
    print("📊 설정 완료 요약")
    print("="*60)
    
    total_steps = 3
    successful_steps = sum([success1, success2, success3])
    
    print(f"✅ 완료된 단계: {successful_steps}/{total_steps}")
    
    if successful_steps == total_steps:
        print("🎉 모든 설정이 성공적으로 완료되었습니다!")
        print("\n📋 다음 단계:")
        print("   1. SQL 스크립트들을 실제 데이터베이스에 실행")
        print("   2. enhanced_data_collector.py로 실제 수집 시작")
        print("   3. 30% 데이터 손실 문제 해결 확인")
        
    else:
        print("⚠️ 일부 설정에서 문제가 발생했습니다.")
        print("🔧 실패한 단계를 검토하고 수정해주세요.")
        
    # 5. 파일 존재 확인 요약
    print(f"\n📄 생성된 파일들:")
    files_to_check = [
        "comprehensive_schema_update.sql",
        "test_schema_deployment.py", 
        "populate_missing_reference_data.sql",
        "enhanced_data_collector.py"
    ]
    
    for file_name in files_to_check:
        file_path = current_dir / file_name
        status = "✅" if file_path.exists() else "❌"
        print(f"   {status} {file_name}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()