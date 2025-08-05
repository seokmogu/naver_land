#!/usr/bin/env python3
"""
네이버 부동산 JWT 토큰 수집기 - Playwright 버전
Playwright를 사용하여 자동으로 토큰을 획득합니다.
"""

from playwright.sync_api import sync_playwright
import re
import time

class PlaywrightTokenCollector:
    def __init__(self):
        self.token = None
        
    def get_token_with_playwright(self):
        """Playwright로 JWT 토큰 자동 획득"""
        print("🔍 Playwright로 토큰 획득 시작...")
        
        with sync_playwright() as p:
            # 브라우저 실행
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # 네트워크 요청 가로채기
            intercepted_token = None
            
            def handle_request(request):
                nonlocal intercepted_token
                auth_header = request.headers.get('authorization')
                if auth_header and auth_header.startswith('Bearer ') and not intercepted_token:
                    intercepted_token = auth_header.replace('Bearer ', '')
                    print(f"🎯 토큰 캡처: {intercepted_token[:50]}...")
            
            # 페이지 생성 및 이벤트 리스너 등록
            page = context.new_page()
            page.on('request', handle_request)
            
            try:
                print("📄 네이버 부동산 접속 중...")
                page.goto("https://new.land.naver.com/offices", wait_until="networkidle")
                
                # 페이지 로딩 대기
                print("⏳ 페이지 로딩 대기...")
                page.wait_for_selector(".item", timeout=10000)
                
                # API 요청 트리거를 위해 스크롤
                page.evaluate("window.scrollTo(0, 500)")
                time.sleep(2)
                
                # 지도 이동이나 필터 변경으로 API 요청 트리거
                try:
                    # 지도 영역 클릭하여 API 요청 유발
                    page.click(".map_wrap", timeout=5000)
                    time.sleep(1)
                except:
                    pass
                
                # 페이지 새로고침으로 재시도
                if not intercepted_token:
                    print("🔄 페이지 새로고침하여 재시도...")
                    page.reload(wait_until="networkidle")
                    time.sleep(3)
                
                # 최종 확인
                if intercepted_token:
                    self.token = intercepted_token
                    print(f"✅ 토큰 획득 성공: {self.token[:50]}...")
                    return self.token
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
    token = collector.get_token_with_playwright()
    
    if token:
        print(f"\n🎯 최종 토큰: {token}")
        return token
    else:
        print("\n❌ 토큰 획득 실패")
        return None

if __name__ == "__main__":
    main()