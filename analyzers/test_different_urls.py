#!/usr/bin/env python3
"""
다양한 네이버 부동산 URL 테스트
"""

from playwright.sync_api import sync_playwright
import time

def test_urls():
    """다양한 URL 테스트"""
    
    urls_to_test = [
        "https://land.naver.com/",
        "https://new.land.naver.com/",
        "https://land.naver.com/offices",
        "https://new.land.naver.com/complexes",
        "https://land.naver.com/complexes",
        "https://new.land.naver.com/map"
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        for url in urls_to_test:
            print(f"\n🔍 테스트 URL: {url}")
            
            try:
                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
                
                print(f"   응답 상태: {response.status if response else 'None'}")
                print(f"   최종 URL: {page.url}")
                print(f"   타이틀: {page.title()}")
                
                # 페이지에 매물 관련 요소가 있는지 확인
                time.sleep(3)
                
                # 일반적인 부동산 관련 셀렉터들
                selectors = [
                    "[class*='item']", 
                    "[class*='list']", 
                    "[class*='article']",
                    "[class*='card']",
                    "a[href*='article']",
                    "[data-article]"
                ]
                
                found_elements = 0
                for selector in selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements:
                            found_elements += len(elements)
                    except:
                        pass
                
                print(f"   매물 관련 요소: {found_elements}개")
                
                # 404가 아니고 매물 요소가 있으면 성공
                if '404' not in page.url and '404' not in page.title() and found_elements > 10:
                    print(f"   ✅ 성공! 이 URL을 사용할 수 있습니다.")
                    
                    # 스크린샷 저장
                    filename = f"success_{url.replace('https://', '').replace('/', '_')}.png"
                    page.screenshot(path=filename)
                    print(f"   스크린샷 저장: {filename}")
                else:
                    print(f"   ❌ 실패 또는 매물 없음")
                
                page.close()
                
            except Exception as e:
                print(f"   ❌ 오류: {e}")
        
        browser.close()

if __name__ == "__main__":
    test_urls()