"""
Selenium과 Chrome 드라이버 설정 도우미
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import sys


def check_chrome_installed():
    """Chrome 브라우저 설치 확인"""
    try:
        # Windows
        if sys.platform == "win32":
            result = subprocess.run(['where', 'chrome'], capture_output=True, text=True)
        # macOS/Linux
        else:
            result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Chrome 브라우저가 설치되어 있습니다.")
            return True
        else:
            print("✗ Chrome 브라우저를 찾을 수 없습니다.")
            print("  https://www.google.com/chrome/ 에서 설치해주세요.")
            return False
    except:
        print("Chrome 브라우저 확인 중 오류 발생")
        return False


def setup_chrome_driver():
    """Chrome 드라이버 자동 설정"""
    try:
        print("Chrome 드라이버 설정 중...")
        
        # webdriver-manager를 사용하여 자동으로 드라이버 다운로드
        service = Service(ChromeDriverManager().install())
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # 테스트용
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.google.com")
        print(f"✓ Chrome 드라이버 설정 성공! (버전: {driver.capabilities['browserVersion']})")
        driver.quit()
        
        return True
        
    except Exception as e:
        print(f"✗ Chrome 드라이버 설정 실패: {e}")
        return False


def install_requirements():
    """필요한 패키지 설치"""
    print("필요한 패키지 설치 중...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_selenium.txt"])
        print("✓ 패키지 설치 완료")
        return True
    except:
        print("✗ 패키지 설치 실패")
        return False


if __name__ == "__main__":
    print("=== Selenium 환경 설정 ===\n")
    
    # 1. 패키지 설치
    if not install_requirements():
        sys.exit(1)
    
    # 2. Chrome 확인
    if not check_chrome_installed():
        sys.exit(1)
    
    # 3. Chrome 드라이버 설정
    if not setup_chrome_driver():
        print("\n수동 설치 방법:")
        print("1. https://chromedriver.chromium.org/ 에서 Chrome 버전에 맞는 드라이버 다운로드")
        print("2. 다운로드한 파일을 PATH에 추가하거나 프로젝트 폴더에 복사")
        sys.exit(1)
    
    print("\n✓ 모든 설정이 완료되었습니다!")
    print("이제 naver_land_selenium_collector.py를 실행할 수 있습니다.")