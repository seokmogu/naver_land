#!/usr/bin/env python3
"""
네이버 부동산 정확한 좌측 목록 스크롤 분석기
더 정밀하게 좌측 매물 목록 영역을 찾아서 스크롤
"""

from playwright.sync_api import sync_playwright
import time
from datetime import datetime

class PreciseListScrollAnalyzer:
    def __init__(self):
        self.captured_requests = []
        self.captured_responses = []
        self.page_loads = []
        
    def analyze_precise_list_scroll(self, url):
        """정밀한 좌측 목록 스크롤 분석"""
        print("🎯 정밀한 좌측 매물 목록 스크롤 분석...")
        print(f"📄 URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=500)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            page = context.new_page()
            
            # 네트워크 요청/응답 캡처
            def handle_request(request):
                if 'new.land.naver.com/api' in request.url:
                    if '/api/articles?' in request.url:
                        import re
                        page_match = re.search(r'page=(\d+)', request.url)
                        page_num = page_match.group(1) if page_match else '1'
                        print(f"🌐 매물 API 요청 - 페이지 {page_num}")
                    
                    self.captured_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'timestamp': datetime.now().isoformat()
                    })
            
            def handle_response(response):
                if '/api/articles?' in response.url and response.status == 200:
                    try:
                        body = response.json()
                        if 'articleList' in body:
                            article_count = len(body['articleList'])
                            total_count = body.get('articleCount', 0)
                            
                            import re
                            page_match = re.search(r'page=(\d+)', response.url)
                            page_num = page_match.group(1) if page_match else '1'
                            
                            self.page_loads.append({
                                'page': page_num,
                                'article_count': article_count,
                                'total_count': total_count,
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            print(f"✅ 매물 API 응답 - 페이지 {page_num}: {article_count}개 (전체: {total_count})")
                    except:
                        pass
                
                self.captured_responses.append({
                    'url': response.url,
                    'status': response.status,
                    'timestamp': datetime.now().isoformat()
                })
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            try:
                print("\n🌐 페이지 로딩...")
                page.goto(url, wait_until="networkidle")
                time.sleep(5)
                
                # 페이지 구조 분석
                print("🔍 페이지 구조 분석 중...")
                
                # 모든 스크롤 가능한 요소 찾기
                scrollable_elements = page.evaluate("""
                    () => {
                        const elements = [];
                        const all = document.querySelectorAll('*');
                        for (let el of all) {
                            const style = window.getComputedStyle(el);
                            if (style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                                el.scrollHeight > el.clientHeight) {
                                const rect = el.getBoundingClientRect();
                                elements.push({
                                    tagName: el.tagName,
                                    className: el.className,
                                    id: el.id,
                                    scrollHeight: el.scrollHeight,
                                    clientHeight: el.clientHeight,
                                    left: rect.left,
                                    top: rect.top,
                                    width: rect.width,
                                    height: rect.height
                                });
                            }
                        }
                        return elements;
                    }
                """)
                
                print(f"📊 스크롤 가능한 요소 {len(scrollable_elements)}개 발견")
                
                # 좌측 영역의 스크롤 요소 찾기
                left_scrollable = []
                for el in scrollable_elements:
                    if el['left'] < 500 and el['width'] > 200 and el['height'] > 300:  # 좌측 + 적당한 크기
                        left_scrollable.append(el)
                        print(f"  📋 좌측 스크롤 요소: {el['tagName']}.{el['className']} (h:{el['scrollHeight']}/{el['clientHeight']})")
                
                # 초기 매물 수 확인
                initial_items = page.query_selector_all(".item_link")
                print(f"📊 초기 매물: {len(initial_items)}개")
                
                # 매물 목록의 정확한 선택자 찾기
                print("\n🔍 매물 목록 컨테이너 정밀 분석...")
                
                # 여러 선택자 시도
                container_selectors = [
                    ".list_contents",
                    ".ArticleList", 
                    ".article_list_container",
                    ".list_wrap",
                    ".contents_area",
                    ".item_list",
                    "[class*='List']",
                    "[class*='list']"
                ]
                
                best_container = None
                for selector in container_selectors:
                    try:
                        container = page.query_selector(selector)
                        if container:
                            # 컨테이너가 매물 아이템을 포함하는지 확인
                            items_in_container = page.query_selector_all(f"{selector} .item_link")
                            if len(items_in_container) > 0:
                                print(f"✅ 매물 컨테이너 발견: {selector} ({len(items_in_container)}개 매물 포함)")
                                best_container = selector
                                break
                    except:
                        continue
                
                if not best_container:
                    print("⚠️ 정확한 매물 컨테이너를 찾지 못했습니다.")
                
                # 스크롤 시작
                print(f"\n📋 정밀 스크롤 시작...")
                scroll_count = 0
                max_scrolls = 20
                last_count = len(initial_items)
                
                for i in range(max_scrolls):
                    scroll_count += 1
                    print(f"\n📜 스크롤 {scroll_count}번...")
                    
                    # 여러 스크롤 방법 동시 시도
                    if best_container:
                        # 방법 1: 특정 컨테이너 스크롤
                        page.evaluate(f"""
                            const container = document.querySelector('{best_container}');
                            if (container) {{
                                container.scrollTo(0, container.scrollHeight);
                                console.log('컨테이너 스크롤:', container.scrollTop);
                            }}
                        """)
                        print("🎯 매물 컨테이너 스크롤 실행")
                    
                    # 방법 2: 좌측 영역 추정 스크롤
                    page.evaluate("""
                        // 좌측 절반 영역에서 스크롤 가능한 요소 찾기
                        const leftElements = Array.from(document.elementsFromPoint(250, 400));
                        for (let el of leftElements) {
                            if (el.scrollHeight > el.clientHeight) {
                                el.scrollTo(0, el.scrollHeight);
                                console.log('좌측 요소 스크롤:', el.className);
                                break;
                            }
                        }
                    """)
                    
                    # 방법 3: wheel 이벤트로 스크롤 시뮬레이션
                    page.evaluate("""
                        const listArea = document.elementFromPoint(300, 400);
                        if (listArea) {
                            listArea.dispatchEvent(new WheelEvent('wheel', {
                                deltaY: 1000,
                                bubbles: true
                            }));
                        }
                    """)
                    
                    print("🔄 다중 스크롤 방법 실행")
                    
                    # 충분한 로딩 대기
                    time.sleep(5)
                    
                    # 매물 수 확인
                    current_items = page.query_selector_all(".item_link")
                    current_count = len(current_items)
                    added = current_count - last_count
                    
                    print(f"📊 매물 수: {last_count} → {current_count} ({added:+d})")
                    
                    if added > 0:
                        last_count = current_count
                        print(f"✅ {added}개 매물 새로 로딩됨!")
                        
                        # 성공적으로 로딩되면 계속 진행
                        continue
                    else:
                        print(f"⏸️ 추가 로딩 없음...")
                        
                        # 로딩 상태 재확인
                        time.sleep(3)
                        recheck_items = page.query_selector_all(".item_link")
                        if len(recheck_items) > current_count:
                            print(f"⏳ 지연 로딩 감지: {current_count} → {len(recheck_items)}")
                            last_count = len(recheck_items)
                            continue
                        
                        # 2번 연속 변화 없으면 중단
                        if i > 0:
                            print("📄 매물 로딩 완료")
                            break
                
                # 최종 결과
                final_items = page.query_selector_all(".item_link")
                total_loaded = len(final_items)
                total_added = total_loaded - len(initial_items)
                
                print(f"\n🎯 최종 결과:")
                print(f"   초기: {len(initial_items)}개")
                print(f"   최종: {total_loaded}개")
                print(f"   추가: {total_added}개")
                print(f"   스크롤: {scroll_count}번")
                
                if self.page_loads:
                    pages = [int(p['page']) for p in self.page_loads if p['page'].isdigit()]
                    if pages:
                        print(f"   최대 페이지: {max(pages)}")
                        print(f"   로딩 페이지: {len(set(pages))}개")
                
                print("📊 분석 완료!")
                
            except Exception as e:
                print(f"❌ 분석 중 오류: {e}")
            finally:
                input("브라우저를 직접 확인해보세요. 계속하려면 Enter를 누르세요...")
                browser.close()
    
    def print_summary(self):
        """결과 요약"""
        print("\n" + "="*60)
        print("📊 정밀 스크롤 분석 결과")
        print("="*60)
        
        if self.page_loads:
            pages = list(set(p['page'] for p in self.page_loads))
            print(f"📄 로딩된 페이지: {len(pages)}개")
            
            for load in self.page_loads:
                print(f"   - 페이지 {load['page']}: {load['article_count']}개")
            
            if len(pages) > 1:
                print(f"\n✅ 무한스크롤 확인됨! ({min(pages)} ~ {max(pages)})")
            else:
                print(f"\n❌ 단일 페이지만 로딩됨")

def main():
    analyzer = PreciseListScrollAnalyzer()
    
    original_url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    analyzer.analyze_precise_list_scroll(original_url)
    analyzer.print_summary()

if __name__ == "__main__":
    main()