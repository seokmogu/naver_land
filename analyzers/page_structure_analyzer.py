#!/usr/bin/env python3
"""
네이버 부동산 페이지 구조 분석기
실제 페이지 구조와 셀렉터를 확인합니다.
"""

from playwright.sync_api import sync_playwright
import time

def analyze_page_structure():
    """페이지 구조 분석"""
    url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    print(f"🔍 페이지 구조 분석: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)  # 시각적 확인
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        page = context.new_page()
        
        try:
            print("📄 페이지 로딩...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"응답 상태: {response.status if response else 'None'}")
            print(f"현재 URL: {page.url}")
            
            # 페이지 타이틀
            title = page.title()
            print(f"페이지 타이틀: {title}")
            
            # 5초 대기
            print("⏳ 5초 대기...")
            time.sleep(5)
            
            # 가능한 매물 관련 셀렉터들 확인
            selectors_to_check = [
                ".item_link",
                ".item",
                ".list_item", 
                ".article_item",
                ".property_item",
                "[class*='item']",
                "[class*='list']",
                "[class*='article']",
                "[class*='property']",
                "a[href*='article']",
                "li",
                ".result",
                ".card"
            ]
            
            print("\n🔍 셀렉터 확인:")
            found_selectors = []
            
            for selector in selectors_to_check:
                try:
                    elements = page.query_selector_all(selector)
                    count = len(elements)
                    if count > 0:
                        print(f"✅ {selector}: {count}개")
                        found_selectors.append(selector)
                        
                        # 처음 몇 개 요소의 클래스와 텍스트 확인
                        if count > 0 and count < 20:  # 너무 많지 않으면 상세 정보 출력
                            for i, element in enumerate(elements[:3]):  # 처음 3개만
                                try:
                                    class_name = element.get_attribute('class')
                                    text_content = element.text_content()[:50] if element.text_content() else ''
                                    print(f"      [{i+1}] class='{class_name}', text='{text_content}...'")
                                except:
                                    pass
                    else:
                        print(f"❌ {selector}: 없음")
                except Exception as e:
                    print(f"❌ {selector}: 오류 - {e}")
            
            # body의 innerHTML 일부 확인 (디버깅용)
            print("\n📄 페이지 내용 샘플:")
            try:
                body_html = page.evaluate("document.body.innerHTML")
                print(f"HTML 길이: {len(body_html)} characters")
                
                # 처음 1000자 출력
                print("처음 1000자:")
                print(body_html[:1000])
                print("...")
                
                # 특정 키워드 검색
                keywords = ['item', 'list', 'article', 'property', '매물', '상가']
                for keyword in keywords:
                    if keyword in body_html.lower():
                        print(f"✅ '{keyword}' 키워드 발견")
                    else:
                        print(f"❌ '{keyword}' 키워드 없음")
                        
            except Exception as e:
                print(f"HTML 내용 확인 실패: {e}")
            
            # 스크린샷 저장
            print("\n📸 스크린샷 저장...")
            page.screenshot(path="page_structure_analysis.png", full_page=True)
            print("저장됨: page_structure_analysis.png")
            
            # 네트워크 요청 확인
            print(f"\n🌐 현재 페이지에서 다시 로딩...")
            page.reload(wait_until="networkidle")
            time.sleep(5)
            
            input("엔터를 누르면 브라우저를 종료합니다...")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    analyze_page_structure()