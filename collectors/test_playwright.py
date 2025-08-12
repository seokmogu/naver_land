#!/usr/bin/env python3
"""
Playwright 동작 테스트 스크립트
VM 환경에서 네이버 부동산 접속 문제 디버깅
"""

from playwright.sync_api import sync_playwright
import time

def test_basic_connection():
    """기본 연결 테스트"""
    print("=" * 60)
    print("🔍 Playwright 기본 연결 테스트")
    print("=" * 60)
    
    with sync_playwright() as p:
        print("\n1. 브라우저 실행...")
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        
        print("2. 컨텍스트 생성...")
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        print("3. 페이지 생성...")
        page = context.new_page()
        
        # 콘솔 메시지 캡처
        page.on("console", lambda msg: print(f"   [CONSOLE] {msg.text}"))
        
        # 페이지 에러 캡처
        page.on("pageerror", lambda err: print(f"   [ERROR] {err}"))
        
        print("\n4. 네이버 부동산 접속 시도...")
        try:
            response = page.goto("https://new.land.naver.com/offices", 
                               wait_until="domcontentloaded", 
                               timeout=30000)
            print(f"   응답 상태: {response.status if response else 'None'}")
            print(f"   URL: {page.url}")
            
            # 페이지 타이틀 확인
            title = page.title()
            print(f"   페이지 타이틀: {title}")
            
            # HTML 내용 일부 확인
            html = page.content()
            print(f"   HTML 길이: {len(html)} bytes")
            
            # 스크린샷 저장
            page.screenshot(path="debug_screenshot.png")
            print("   스크린샷 저장: debug_screenshot.png")
            
            # body 태그 확인
            body_exists = page.locator("body").count() > 0
            print(f"   body 태그 존재: {body_exists}")
            
            # 특정 요소들 확인
            print("\n5. 페이지 요소 확인...")
            selectors = [
                ".item",
                "#content",
                "div",
                "[class*='item']",
                "[class*='list']"
            ]
            
            for selector in selectors:
                count = page.locator(selector).count()
                print(f"   {selector}: {count}개")
            
            print("\n6. 네트워크 요청 모니터링...")
            
            # 새 페이지에서 네트워크 모니터링
            page2 = context.new_page()
            requests = []
            
            def capture_request(request):
                if 'api' in request.url or 'auth' in request.headers:
                    requests.append({
                        'url': request.url,
                        'method': request.method,
                        'auth': request.headers.get('authorization', 'None')
                    })
            
            page2.on('request', capture_request)
            
            print("   페이지 재접속 (네트워크 모니터링)...")
            page2.goto("https://new.land.naver.com/offices", wait_until="domcontentloaded")
            
            # 스크롤하여 API 호출 유도
            page2.evaluate("window.scrollTo(0, 500)")
            time.sleep(3)
            
            print(f"   캡처된 API 요청: {len(requests)}개")
            for req in requests[:5]:  # 처음 5개만 출력
                print(f"     - {req['method']} {req['url'][:80]}...")
                if req['auth'] != 'None':
                    print(f"       Auth: {req['auth'][:50]}...")
            
        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")
            
            # 오류 시 추가 정보
            print("\n   추가 디버깅 정보:")
            print(f"   현재 URL: {page.url}")
            
            # HTML 내용 확인
            html = page.content()
            print(f"   HTML 시작 부분: {html[:500]}")
            
        finally:
            browser.close()
            print("\n✅ 브라우저 종료")

def test_headless_vs_headful():
    """헤드리스 vs 헤드풀 모드 비교"""
    print("\n" + "=" * 60)
    print("🔍 헤드리스 모드 테스트")
    print("=" * 60)
    
    for headless in [True, False]:
        mode = "헤드리스" if headless else "헤드풀"
        print(f"\n{mode} 모드 테스트:")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=headless,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                page = browser.new_page()
                response = page.goto("https://new.land.naver.com/", timeout=10000)
                
                print(f"  ✅ {mode} 모드: 성공 (상태: {response.status if response else 'None'})")
                browser.close()
                
        except Exception as e:
            print(f"  ❌ {mode} 모드: 실패 - {str(e)[:100]}")

if __name__ == "__main__":
    print("네이버 부동산 Playwright 접속 테스트\n")
    
    # 기본 연결 테스트
    test_basic_connection()
    
    # 헤드리스 모드 비교 (선택적)
    # test_headless_vs_headful()
    
    print("\n테스트 완료!")