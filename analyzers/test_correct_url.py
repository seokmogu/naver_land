#!/usr/bin/env python3
"""
제공된 정확한 URL로 매물 조회 테스트
"""

from playwright.sync_api import sync_playwright
import time

def test_correct_url():
    """정확한 URL로 매물 조회 테스트"""
    
    url = "https://new.land.naver.com/offices?ms=37.4986291,127.0359669,13&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    print(f"🔍 정확한 URL 테스트: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, 
            slow_mo=1000,
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
        
        # API 호출 모니터링
        api_calls = []
        
        def handle_request(request):
            if 'new.land.naver.com/api' in request.url:
                api_calls.append({
                    'url': request.url,
                    'method': request.method,
                    'timestamp': time.time()
                })
                print(f"📡 API 호출: {request.method} {request.url}")
        
        page = context.new_page()
        page.on('request', handle_request)
        
        try:
            print("📄 페이지 로딩...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            print(f"   응답 상태: {response.status if response else 'None'}")
            print(f"   최종 URL: {page.url}")
            print(f"   타이틀: {page.title()}")
            
            # 404 체크
            if '404' in page.url or '404' in page.title():
                print("❌ 404 페이지로 리다이렉트됨")
                return False
            
            print("⏳ 페이지 로딩 대기 (10초)...")
            time.sleep(10)
            
            # 다양한 매물 관련 셀렉터 시도
            selectors_to_try = [
                ".item_link",
                ".item",
                ".list_item",
                ".article_item",
                ".property_item",
                ".card",
                "article",
                "[class*='item']",
                "[class*='article']",
                "[class*='property']", 
                "[class*='card']",
                "a[href*='article']",
                "li[data-article]",
                ".result_item",
                ".search_result"
            ]
            
            print("\n🔍 매물 요소 찾기:")
            found_elements = []
            
            for selector in selectors_to_try:
                try:
                    elements = page.query_selector_all(selector)
                    count = len(elements)
                    if count > 0:
                        print(f"✅ {selector}: {count}개")
                        found_elements.append({
                            'selector': selector,
                            'count': count,
                            'elements': elements[:3]  # 처음 3개만 저장
                        })
                        
                        # 첫 번째 요소의 상세 정보
                        if elements:
                            first_element = elements[0]
                            try:
                                class_name = first_element.get_attribute('class')
                                text_content = first_element.text_content()[:100] if first_element.text_content() else ''
                                print(f"      첫 번째 요소: class='{class_name}', text='{text_content}...'")
                            except:
                                pass
                    else:
                        print(f"❌ {selector}: 없음")
                except Exception as e:
                    print(f"❌ {selector}: 오류 - {e}")
            
            # 스크린샷 저장
            print(f"\n📸 스크린샷 저장...")
            page.screenshot(path="correct_url_test.png", full_page=True)
            print("저장됨: correct_url_test.png")
            
            # 페이지 소스 일부 확인
            print(f"\n📄 페이지 내용 확인...")
            html = page.content()
            print(f"HTML 길이: {len(html)} characters")
            
            # 매물 관련 키워드 검색
            keywords = ['매물', '상가', '오피스', '사무실', 'office', 'article']
            for keyword in keywords:
                if keyword in html.lower():
                    print(f"✅ '{keyword}' 키워드 발견")
                else:
                    print(f"❌ '{keyword}' 키워드 없음")
            
            # 수동 스크롤 테스트
            if found_elements:
                print(f"\n📜 스크롤 테스트...")
                page.evaluate("window.scrollTo(0, 500)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 1000)")
                time.sleep(2)
                
                # 스크롤 후 요소 수 재확인
                for found in found_elements[:2]:  # 처음 2개 셀렉터만
                    new_elements = page.query_selector_all(found['selector'])
                    new_count = len(new_elements)
                    if new_count != found['count']:
                        print(f"🔄 {found['selector']}: {found['count']} → {new_count} (스크롤 후 변화)")
                    else:
                        print(f"⏸️ {found['selector']}: {found['count']} (변화 없음)")
            
            print(f"\n📊 API 호출 요약:")
            print(f"   총 API 호출: {len(api_calls)}개")
            for call in api_calls:
                print(f"   - {call['method']} {call['url']}")
            
            input("\n엔터를 누르면 브라우저를 종료합니다...")
            
            return len(found_elements) > 0
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_correct_url()
    print(f"\n{'✅ 성공' if success else '❌ 실패'}")