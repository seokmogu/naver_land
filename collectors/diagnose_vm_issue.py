#!/usr/bin/env python3
"""
VM 환경에서 수집기 동작 문제 진단 스크립트
"""

import sys
import os
import subprocess
import json
from datetime import datetime

def check_python_version():
    """Python 버전 확인"""
    print("🐍 Python 버전 확인...")
    version = sys.version
    print(f"  현재 버전: {version}")
    if sys.version_info < (3, 8):
        print("  ⚠️ Python 3.8 이상이 필요합니다!")
        return False
    print("  ✅ Python 버전 정상")
    return True

def check_required_packages():
    """필수 패키지 설치 확인"""
    print("\n📦 필수 패키지 확인...")
    required = ['requests', 'playwright', 'pandas', 'supabase']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"  ✅ {package} 설치됨")
        except ImportError:
            print(f"  ❌ {package} 미설치")
            missing.append(package)
    
    if missing:
        print(f"\n  ⚠️ 미설치 패키지: {', '.join(missing)}")
        print("  설치 명령: pip install " + " ".join(missing))
        return False
    return True

def check_playwright_browsers():
    """Playwright 브라우저 설치 확인"""
    print("\n🌐 Playwright 브라우저 확인...")
    try:
        result = subprocess.run(['playwright', 'install', '--help'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Playwright CLI 사용 가능")
            
            # 브라우저 설치 상태 확인
            result = subprocess.run(['playwright', 'install', '--list'], 
                                  capture_output=True, text=True)
            print("  브라우저 상태:")
            if 'chromium' in result.stdout.lower():
                print("  ✅ Chromium 설치됨")
            else:
                print("  ⚠️ Chromium 미설치. 실행: playwright install chromium")
                return False
        else:
            print("  ❌ Playwright CLI 없음")
            return False
    except FileNotFoundError:
        print("  ❌ Playwright 미설치. 실행: pip install playwright && playwright install")
        return False
    return True

def check_system_dependencies():
    """시스템 의존성 확인 (Linux용)"""
    print("\n🖥️ 시스템 의존성 확인...")
    
    if sys.platform != 'linux':
        print(f"  현재 OS: {sys.platform} (Linux가 아님)")
        return True
    
    required_libs = [
        'libnss3', 'libatk-bridge2.0-0', 'libdrm2', 
        'libxkbcommon0', 'libgtk-3-0', 'libgbm1'
    ]
    
    missing = []
    for lib in required_libs:
        result = subprocess.run(['dpkg', '-l', lib], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ {lib} 설치됨")
        else:
            print(f"  ❌ {lib} 미설치")
            missing.append(lib)
    
    if missing:
        print(f"\n  ⚠️ 미설치 라이브러리: {', '.join(missing)}")
        print("  설치 명령: sudo apt-get install -y " + " ".join(missing))
        return False
    return True

def check_config_files():
    """설정 파일 확인"""
    print("\n⚙️ 설정 파일 확인...")
    
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        print(f"  ✅ config.json 존재")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # 필수 키 확인
            if 'kakao_api' in config and 'rest_api_key' in config['kakao_api']:
                print("  ✅ Kakao API 키 설정됨")
            else:
                print("  ⚠️ Kakao API 키 미설정")
            
            if 'supabase' in config:
                if 'url' in config['supabase'] and 'anon_key' in config['supabase']:
                    print("  ✅ Supabase 설정됨")
                else:
                    print("  ⚠️ Supabase 설정 불완전")
            else:
                print("  ⚠️ Supabase 미설정")
        except json.JSONDecodeError:
            print("  ❌ config.json 파싱 오류")
            return False
    else:
        print("  ❌ config.json 파일 없음")
        print("  config.template.json을 복사하여 생성하세요")
        return False
    return True

def test_network_connectivity():
    """네트워크 연결 테스트"""
    print("\n🌍 네트워크 연결 테스트...")
    
    test_urls = [
        ('네이버 부동산', 'https://new.land.naver.com/'),
        ('Kakao API', 'https://dapi.kakao.com/'),
        ('Supabase', 'https://eslhavjipwbyvbbknixv.supabase.co/')
    ]
    
    import requests
    for name, url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 400:
                print(f"  ✅ {name} 접속 가능")
            else:
                print(f"  ⚠️ {name} 응답 코드: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name} 접속 실패: {str(e)}")
            return False
    return True

def test_token_collection():
    """토큰 수집 테스트"""
    print("\n🔑 토큰 수집 테스트...")
    try:
        from playwright_token_collector import PlaywrightTokenCollector
        print("  토큰 수집 시도 중...")
        collector = PlaywrightTokenCollector()
        token = collector.get_token()
        if token:
            print(f"  ✅ 토큰 획득 성공 (길이: {len(token)})")
            return True
        else:
            print("  ❌ 토큰 획득 실패")
            return False
    except Exception as e:
        print(f"  ❌ 토큰 수집 오류: {str(e)}")
        return False

def check_memory_and_swap():
    """메모리 및 스왑 확인"""
    print("\n💾 메모리 상태 확인...")
    
    if sys.platform == 'linux':
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            
            # 스왑 확인
            if 'Swap:' in result.stdout:
                swap_line = [l for l in result.stdout.split('\n') if 'Swap:' in l][0]
                if '0B' in swap_line or '0K' in swap_line:
                    print("  ⚠️ 스왑 메모리 미설정. VM에서는 스왑 설정을 권장합니다.")
                    print("  설정 명령:")
                    print("    sudo fallocate -l 1G /swapfile")
                    print("    sudo chmod 600 /swapfile")
                    print("    sudo mkswap /swapfile")
                    print("    sudo swapon /swapfile")
    return True

def main():
    """진단 실행"""
    print("=" * 60)
    print("🔍 네이버 부동산 수집기 VM 환경 진단")
    print(f"   실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   실행 경로: {os.getcwd()}")
    print("=" * 60)
    
    all_ok = True
    
    # 각 항목 체크
    checks = [
        ("Python 버전", check_python_version),
        ("필수 패키지", check_required_packages),
        ("Playwright 브라우저", check_playwright_browsers),
        ("시스템 의존성", check_system_dependencies),
        ("설정 파일", check_config_files),
        ("네트워크 연결", test_network_connectivity),
        ("메모리 상태", check_memory_and_swap),
        ("토큰 수집", test_token_collection),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
            if not result:
                all_ok = False
        except Exception as e:
            print(f"\n❌ {name} 체크 중 오류: {str(e)}")
            results.append((name, False))
            all_ok = False
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 진단 결과 요약")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 정상" if result else "❌ 문제"
        print(f"  {name}: {status}")
    
    if all_ok:
        print("\n✅ 모든 항목이 정상입니다!")
        print("수집기를 실행할 준비가 되었습니다.")
    else:
        print("\n⚠️ 일부 문제가 발견되었습니다.")
        print("위의 메시지를 참고하여 문제를 해결하세요.")
    
    print("\n💡 추가 확인 사항:")
    print("  1. 실제 수집 테스트: python batch_collect_gangnam.py")
    print("  2. 로그 확인: tail -f logs/daily_collection_*.log")
    print("  3. 프로세스 확인: ps aux | grep python")

if __name__ == "__main__":
    main()