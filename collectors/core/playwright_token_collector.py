#!/usr/bin/env python3
"""
네이버 부동산 JWT 토큰 수집기 - Playwright 버전
Playwright를 사용하여 자동으로 토큰을 획득합니다.
"""

from playwright.sync_api import sync_playwright
import time

class PlaywrightTokenCollector:
    def __init__(self):
        self.token = None
        
    def get_token_with_playwright(self):
        """Playwright로 JWT 토큰 자동 획득 - 브라우저 감지 우회"""
        print("🔍 Playwright로 토큰 획득 시작...")
        
        with sync_playwright() as p:
            # 브라우저 실행 (완전한 Chrome 모방)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # 완전한 Chrome 컨텍스트 생성
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                extra_http_headers={
                    'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Cache-Control': 'max-age=0'
                }
            )
            
            # 네트워크 요청 가로채기
            intercepted_token = None
            captured_cookies = None
            
            def handle_request(request):
                nonlocal intercepted_token
                auth_header = request.headers.get('authorization')
                if auth_header and auth_header.startswith('Bearer ') and not intercepted_token:
                    intercepted_token = auth_header.replace('Bearer ', '')
                    print(f"🎯 토큰 캡처: {intercepted_token[:50]}...")
            
            # 페이지 생성 및 이벤트 리스너 등록
            page = context.new_page()
            page.on('request', handle_request)
            
            # webdriver 속성 숨기기
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Chrome runtime 추가
                window.chrome = {
                    runtime: {}
                };
                
                // Permissions API 모킹
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            try:
                print("📄 단계별 네비게이션 시작...")
                
                # 1단계: naver.com 먼저 방문
                print("1️⃣ naver.com 방문...")
                page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                
                # 2단계: land.naver.com 방문
                print("2️⃣ land.naver.com 방문...")
                page.goto("https://land.naver.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                
                # 3단계: 최종 offices 페이지 방문
                print("3️⃣ offices 페이지 방문...")
                page.goto("https://new.land.naver.com/offices?ms=37.4986291,127.0359669,13&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL", 
                         wait_until="domcontentloaded", timeout=30000)
                
                # 페이지 로딩 대기
                print("⏳ 페이지 로딩 대기...")
                try:
                    page.wait_for_selector(".item", timeout=10000)
                    print("✅ 매물 목록 로딩 완료")
                except:
                    print("⚠️ 매물 목록 로딩 중...")
                    page.wait_for_timeout(5000)
                
                # API 요청 트리거
                print("🔄 API 요청 트리거...")
                page.evaluate("window.scrollTo(0, 500)")
                time.sleep(2)
                
                # 지도 상호작용으로 API 요청 유발
                try:
                    page.click(".map_wrap", timeout=5000)
                    time.sleep(2)
                except:
                    pass
                
                # 토큰을 못찾았으면 새로고침
                if not intercepted_token:
                    print("🔄 페이지 새로고침하여 재시도...")
                    page.reload(wait_until="networkidle")
                    time.sleep(3)
                
                # 최종 결과 확인
                if intercepted_token:
                    # 쿠키도 함께 수집
                    captured_cookies = context.cookies()
                    self.token = intercepted_token
                    self.cookies = captured_cookies
                    print(f"✅ 토큰 획득 성공: {self.token[:50]}...")
                    print(f"🍪 쿠키 수집 완료: {len(captured_cookies)}개")
                    return {'token': self.token, 'cookies': captured_cookies}
                else:
                    print("❌ 토큰을 찾을 수 없습니다.")
                    
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
            finally:
                browser.close()
                
        return None
    
    def save_token(self):
        """토큰 저장 - 비활성화"""
        pass
    
    def load_token(self):
        """토큰 로드 - 비활성화"""
        return None

def main():
    collector = PlaywrightTokenCollector()
    result = collector.get_token_with_playwright()
    
    if result:
        print(f"\n🎯 최종 토큰: {result['token']}")
        print(f"🍪 최종 쿠키: {len(result['cookies'])}개")
        return result
    else:
        print("\n❌ 토큰 획득 실패")
        return None

if __name__ == "__main__":
    main()