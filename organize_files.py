import os
import shutil

def organize_files():
    """파일 정리 - 필수 파일과 테스트 파일 분리"""
    
    # 필수 파일들 (production)
    production_files = [
        # 핵심 수집기
        "naver_land_smart_collector.py",           # 토큰 재사용 가능한 스마트 수집기
        "complete_address_converter.py",           # 완전한 주소 변환기
        
        # 설정 및 종속성
        "requirements_selenium.txt",               # 패키지 목록
        "token.txt",                              # JWT 토큰
        
        # 최종 결과 데이터
        "complete_address_20250724_190056.json",  # 완전한 주소 정보 포함 데이터
        "complete_address_20250724_190056.csv",   # CSV 형태
    ]
    
    # 테스트/분석 파일들
    test_files = [
        # 테스트 및 분석
        "analyze_jwt.py",
        "analyze_cluster_structure.py", 
        "analyze_token_generation.py",
        "test_detailed_address.py",
        "browser_token_finder.py",
        "setup_selenium.py",
        
        # 초기 버전들
        "naver_land_collector.py",
        "naver_land_selenium_collector.py", 
        "naver_land_advanced_collector.py",
        "auto_token_collector.py",
        "find_token_generation.py",
        
        # 실험적 수집기
        "comprehensive_collector.py",
        "ultimate_collector.py", 
        "focused_collector.py",
        "quick_test_collector.py",
        "final_test.py",
        
        # 중간 결과물
        "simple_test.py",
        "coordinate_to_address.py",
        
        # 테스트 데이터
        "quick_test_20250724_183854.json",
        "enhanced_articles_20250724_185802.json",
        "enhanced_articles_20250724_185802.csv",
        "naver_land_20250724_182554.json",
        "naver_land_20250724_182554.csv",
        "naver_land_20250724_182935.json", 
        "naver_land_20250724_182935.csv",
        
        # 설치 및 가이드
        "install_chrome.sh",
        "SELENIUM_INSTALL_GUIDE.md",
        "README.md",
        "requirements.txt",
        
        # 브라우저 스크립트
        "browser_console_script.js",
    ]
    
    print("=== 파일 정리 시작 ===")
    
    # 필수 파일들을 production_files로 이동
    print("\n필수 파일들:")
    for file in production_files:
        if os.path.exists(file):
            shutil.move(file, f"production_files/{file}")
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (없음)")
    
    # 테스트 파일들을 test_files로 이동  
    print("\n테스트 파일들:")
    for file in test_files:
        if os.path.exists(file):
            shutil.move(file, f"test_files/{file}")
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (없음)")
    
    # 남은 파일들 확인
    remaining = []
    for file in os.listdir("."):
        if file.endswith(('.py', '.json', '.csv', '.txt', '.md', '.sh', '.js')):
            if file not in ['organize_files.py', 'venv']:
                remaining.append(file)
    
    if remaining:
        print(f"\n남은 파일들:")
        for file in remaining:
            print(f"  ? {file}")
            # 나머지는 test_files로 이동
            shutil.move(file, f"test_files/{file}")
    
    print(f"\n=== 정리 완료 ===")

if __name__ == "__main__":
    organize_files()