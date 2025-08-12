#!/usr/bin/env python3
"""
실제 네이버 부동산 페이지에서 토큰 수집 테스트
"""

from playwright.sync_api import sync_playwright
import json
import time

def test_naver_page():
    """실제 네이버 부동산 페이지 테스트"""
    url = "https://new.land.naver.com/offices?ms=37.4986291,127.0359669,13&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    print(f"🔍 실제 페이지 테스트: {url}")
    
    with sync_playwright() as p:
        # 브라우저 실행
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        
        # 토큰 캡처
        captured_token = None
        api_calls = []
        
        def handle_request(request):
            nonlocal captured_token
            
            # API 호출 기록
            if 'new.land.naver.com/api' in request.url:
                api_calls.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers)
                })
                print(f"📡 API 호출: {request.method} {request.url}")
                
                # Authorization 헤더에서 토큰 추출
                auth = request.headers.get('authorization')
                if auth and auth.startswith('Bearer ') and not captured_token:
                    captured_token = auth.replace('Bearer ', '')
                    print(f"🎯 토큰 캡처: {captured_token[:50]}...")
        
        page = context.new_page()
        page.on('request', handle_request)
        
        try:
            print("📄 페이지 로딩 중...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"   응답 상태: {response.status if response else 'None'}")
            print(f"   현재 URL: {page.url}")
            
            # 페이지 타이틀 확인
            title = page.title()
            print(f"   페이지 타이틀: {title}")
            
            # 페이지가 제대로 로드되었는지 확인
            if '404' in page.url or '404' in title:
                print("❌ 404 페이지로 리다이렉트됨")
                return False
            
            # 잠시 대기하여 API 호출 관찰
            print("⏳ API 호출 대기 중...")
            time.sleep(5)
            
            # 스크롤하여 추가 API 호출 유도
            print("📜 스크롤하여 API 호출 유도...")
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(2)
            page.evaluate("window.scrollTo(0, 1000)")
            time.sleep(3)
            
            # 결과 출력
            print(f"\n📊 결과 요약:")
            print(f"   캡처된 토큰: {'있음' if captured_token else '없음'}")
            print(f"   API 호출 수: {len(api_calls)}")
            
            if captured_token:
                print(f"✅ 토큰: {captured_token}")
                
                # 토큰으로 API 테스트
                import requests
                headers = {
                    'authorization': f'Bearer {captured_token}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://new.land.naver.com/',
                }
                
                print("\n🧪 토큰으로 API 테스트:")
                test_response = requests.get(
                    "https://new.land.naver.com/api/cortars",
                    headers=headers,
                    params={
                        'zoom': 15,
                        'centerLat': 37.4986291,
                        'centerLon': 127.0359669
                    }
                )
                print(f"   테스트 응답: {test_response.status_code}")
                if test_response.status_code == 200:
                    print(f"   데이터: {test_response.json()}")
                else:
                    print(f"   오류: {test_response.text}")
            
            if api_calls:
                print(f"\n📋 API 호출 목록:")
                for i, call in enumerate(api_calls[:5]):  # 처음 5개만
                    print(f"   {i+1}. {call['method']} {call['url']}")
            
            return captured_token is not None
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_naver_page()
    print(f"\n{'✅ 성공' if success else '❌ 실패'}")