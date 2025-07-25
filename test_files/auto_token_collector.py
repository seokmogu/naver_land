import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

class NaverLandAutoTokenCollector:
    """Selenium을 사용하여 네이버 부동산 JWT 토큰 자동 획득"""
    
    def __init__(self, headless=True):
        self.token = None
        self.setup_driver(headless)
        
    def setup_driver(self, headless):
        """Chrome 드라이버 설정"""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 네트워크 로그 활성화
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        self.driver = webdriver.Chrome(options=options)
        
    def inject_xhr_interceptor(self):
        """XHR 요청을 가로채는 JavaScript 주입"""
        script = """
        window.capturedToken = null;
        
        // XMLHttpRequest 후킹
        const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
        XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
            if (header.toLowerCase() === 'authorization' && value.startsWith('Bearer ')) {
                window.capturedToken = value.substring(7);
                console.log('Token captured:', window.capturedToken);
            }
            return originalSetRequestHeader.apply(this, arguments);
        };
        
        // Fetch API 후킹
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const [url, options] = args;
            if (options && options.headers && options.headers.authorization) {
                const auth = options.headers.authorization;
                if (auth.startsWith('Bearer ')) {
                    window.capturedToken = auth.substring(7);
                    console.log('Token captured from fetch:', window.capturedToken);
                }
            }
            return originalFetch.apply(this, args);
        };
        """
        self.driver.execute_script(script)
        
    def get_token_from_network_logs(self):
        """네트워크 로그에서 토큰 추출"""
        logs = self.driver.get_log('performance')
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message['message']['method']
                
                if method == 'Network.requestWillBeSentExtraInfo':
                    headers = message['message']['params'].get('headers', {})
                    auth = headers.get('authorization', '')
                    
                    if auth.startswith('Bearer '):
                        token = auth[7:]  # 'Bearer ' 제거
                        print(f"네트워크 로그에서 토큰 발견: {token[:50]}...")
                        return token
                        
            except Exception:
                continue
                
        return None
        
    def get_token(self, url="https://new.land.naver.com/offices"):
        """네이버 부동산 페이지에서 JWT 토큰 획득"""
        try:
            print("1. 페이지 로딩 중...")
            self.driver.get(url)
            
            # JavaScript 인터셉터 주입
            self.inject_xhr_interceptor()
            
            # 페이지 로드 대기
            time.sleep(3)
            
            print("2. API 호출 트리거...")
            # 페이지 스크롤로 API 호출 유도
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            
            # JavaScript에서 캡처한 토큰 확인
            captured_token = self.driver.execute_script("return window.capturedToken;")
            if captured_token:
                print(f"3. JavaScript에서 토큰 캡처 성공!")
                self.token = captured_token
                return captured_token
            
            # 네트워크 로그에서 토큰 확인
            print("3. 네트워크 로그 확인 중...")
            network_token = self.get_token_from_network_logs()
            if network_token:
                self.token = network_token
                return network_token
                
            print("토큰을 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            print(f"오류 발생: {e}")
            return None
            
    def close(self):
        """드라이버 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            

# 사용 예시
if __name__ == "__main__":
    print("네이버 부동산 JWT 토큰 자동 수집 시작...")
    
    collector = NaverLandAutoTokenCollector(headless=False)  # headless=False로 브라우저 표시
    
    try:
        token = collector.get_token()
        
        if token:
            print(f"\n획득한 토큰: {token}")
            
            # 토큰을 파일로 저장
            with open('naver_land_token.txt', 'w') as f:
                f.write(token)
            print("\n토큰이 'naver_land_token.txt' 파일에 저장되었습니다.")
            
            # 토큰 분석
            import base64
            import json
            
            parts = token.split('.')
            if len(parts) == 3:
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
                print(f"\n토큰 Payload: {json.dumps(payload, indent=2)}")
        else:
            print("\n토큰 획득 실패")
            
    finally:
        collector.close()