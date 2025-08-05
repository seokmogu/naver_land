#!/usr/bin/env python3
"""
네이버 부동산 좌측 매물 목록 스크롤 분석기
좌측 매물 목록 영역의 스크롤을 통한 무한로딩 패턴 분석
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

class ListScrollAnalyzer:
    def __init__(self):
        self.captured_requests = []
        self.captured_responses = []
        self.page_loads = []
        
    def analyze_list_scroll(self, url):
        """좌측 매물 목록 스크롤 분석"""
        print("📋 좌측 매물 목록 스크롤 분석 시작...")
        print(f"📄 URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=300)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            page = context.new_page()
            
            # 네트워크 요청/응답 캡처
            def handle_request(request):
                if 'new.land.naver.com/api' in request.url:
                    req_data = {
                        'url': request.url,
                        'method': request.method,
                        'timestamp': datetime.now().isoformat(),
                        'is_articles': '/api/articles?' in request.url
                    }
                    self.captured_requests.append(req_data)
                    
                    if '/api/articles?' in request.url:
                        import re
                        page_match = re.search(r'page=(\d+)', request.url)
                        page_num = page_match.group(1) if page_match else '1'
                        print(f"📄 매물 API 요청 - 페이지 {page_num}")
            
            def handle_response(response):
                if 'new.land.naver.com/api' in response.url:
                    try:
                        response_data = {
                            'url': response.url,
                            'status': response.status,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        if '/api/articles?' in response.url and response.status == 200:
                            try:
                                body = response.json()
                                if 'articleList' in body:
                                    article_count = len(body['articleList'])
                                    total_count = body.get('articleCount', 0)
                                    
                                    import re
                                    page_match = re.search(r'page=(\d+)', response.url)
                                    page_num = page_match.group(1) if page_match else '1'
                                    
                                    response_data['body'] = body
                                    response_data['article_count'] = article_count
                                    response_data['total_count'] = total_count
                                    response_data['page_num'] = page_num
                                    
                                    self.page_loads.append({
                                        'page': page_num,
                                        'article_count': article_count,
                                        'total_count': total_count,
                                        'timestamp': datetime.now().isoformat()
                                    })
                                    
                                    print(f"✅ 매물 API 응답 - 페이지 {page_num}: {article_count}개 (전체: {total_count})")
                            except:
                                pass
                        
                        self.captured_responses.append(response_data)
                        
                    except Exception as e:
                        print(f"❌ 응답 처리 오류: {e}")
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            try:
                print("\n🌐 페이지 로딩...")
                page.goto(url, wait_until="networkidle")
                time.sleep(5)
                
                # 좌측 매물 목록 영역 찾기
                print("🔍 좌측 매물 목록 영역 찾는 중...")
                
                # 다양한 매물 목록 컨테이너 선택자 시도
                list_selectors = [
                    ".ArticleList", 
                    ".article_list", 
                    ".list_contents",
                    ".item_article_list",
                    ".ArticleListArea",
                    ".list_wrap",
                    "#ArticleListApp",
                    "[class*='article'][class*='list']",
                    "[class*='List'][class*='Container']"
                ]
                
                list_container = None
                for selector in list_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            list_container = element
                            print(f"✅ 매물 목록 컨테이너 발견: {selector}")
                            break
                    except:
                        continue
                
                if not list_container:
                    print("⚠️ 매물 목록 컨테이너를 찾을 수 없습니다. 일반 스크롤을 시도합니다.")
                
                # 초기 매물 수 확인
                initial_items = page.query_selector_all(".item_link, .article_item")
                print(f"📊 초기 매물: {len(initial_items)}개")
                
                # 좌측 목록 영역 스크롤 시작
                print(f"\n📋 좌측 매물 목록 스크롤 시작...")
                scroll_count = 0
                max_scrolls = 15
                no_change_count = 0
                last_count = len(initial_items)
                
                for i in range(max_scrolls):
                    scroll_count += 1
                    print(f"\n📜 목록 스크롤 {scroll_count}번...")
                    
                    # 좌측 목록 영역 스크롤
                    if list_container:
                        # 특정 컨테이너 내부 스크롤
                        try:
                            page.evaluate(f"""
                                const container = document.querySelector('{list_selectors[0]}');
                                if (container) {{
                                    container.scrollTop = container.scrollHeight;
                                }}
                            """)
                            print("🎯 매물 목록 컨테이너 스크롤 실행")
                        except:
                            # 대안: 페이지 전체 스크롤
                            page.evaluate("window.scrollTo(0, window.scrollY + 1000)")
                            print("🔄 페이지 스크롤로 대체")
                    else:
                        # 좌측 영역 추정하여 스크롤
                        try:
                            # 좌측 절반 영역에서 스크롤 이벤트 발생
                            page.evaluate("""
                                const leftArea = document.elementFromPoint(300, 400);
                                if (leftArea) {
                                    let scrollable = leftArea;
                                    while (scrollable && scrollable.scrollHeight <= scrollable.clientHeight) {
                                        scrollable = scrollable.parentElement;
                                    }
                                    if (scrollable) {
                                        scrollable.scrollTop += 1000;
                                    }
                                }
                            """)
                            print("🎯 좌측 영역 스크롤 실행")
                        except:
                            page.evaluate("window.scrollTo(0, window.scrollY + 1000)")
                            print("🔄 일반 스크롤로 대체")
                    
                    # 로딩 대기
                    time.sleep(4)
                    
                    # 매물 수 확인
                    current_items = page.query_selector_all(".item_link, .article_item")
                    current_count = len(current_items)
                    added = current_count - last_count
                    
                    print(f"📊 매물 수: {last_count} → {current_count} ({added:+d})")
                    
                    if added > 0:
                        no_change_count = 0
                        last_count = current_count
                        print(f"✅ {added}개 매물 추가 로딩됨")
                    else:
                        no_change_count += 1
                        print(f"⏸️ 추가 로딩 없음 ({no_change_count}/3)")
                        
                        # 3번 연속 변화가 없으면 중단
                        if no_change_count >= 3:
                            print("📄 더 이상 로딩할 매물이 없습니다.")
                            break
                    
                    # 로딩 상태 확인
                    try:
                        loading_elements = page.query_selector_all(".loading, .spinner, [class*='load']")
                        visible_loading = [el for el in loading_elements if el.is_visible()]
                        if visible_loading:
                            print("⏳ 로딩 중... 추가 대기")
                            time.sleep(3)
                    except:
                        pass
                
                # 최종 결과
                final_items = page.query_selector_all(".item_link, .article_item")
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
                        print(f"   로딩된 페이지: {len(set(pages))}개")
                
                print("📊 분석 완료!")
                
            except Exception as e:
                print(f"❌ 분석 중 오류: {e}")
            finally:
                time.sleep(3)
                browser.close()
    
    def save_list_scroll_analysis(self):
        """분석 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        articles_requests = [req for req in self.captured_requests if req.get('is_articles')]
        
        analysis = {
            "분석시간": timestamp,
            "분석타입": "좌측_매물_목록_스크롤",
            "총_요청수": len(self.captured_requests),
            "매물_API_요청수": len(articles_requests),
            "페이지_로딩_순서": self.page_loads,
            "로딩된_페이지수": len(set(p['page'] for p in self.page_loads)),
            "전체_응답": self.captured_responses
        }
        
        filename = f"list_scroll_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 분석 결과 저장: {filename}")
        return filename
    
    def print_list_scroll_summary(self):
        """분석 요약 출력"""
        print("\n" + "="*60)
        print("📊 좌측 매물 목록 스크롤 분석 요약")
        print("="*60)
        
        articles_requests = [req for req in self.captured_requests if req.get('is_articles')]
        
        print(f"📄 전체 API 요청: {len(self.captured_requests)}개")
        print(f"📋 매물 API 요청: {len(articles_requests)}개")
        
        if self.page_loads:
            pages = [p['page'] for p in self.page_loads]
            unique_pages = list(set(pages))
            
            print(f"\n📄 로딩된 페이지:")
            print(f"   - 총 페이지 수: {len(unique_pages)}")
            if len(unique_pages) > 1:
                print(f"   - 페이지 범위: {min(unique_pages)} ~ {max(unique_pages)}")
            
            print(f"\n📊 페이지별 매물 수:")
            for load in self.page_loads:
                print(f"   - 페이지 {load['page']}: {load['article_count']}개")
            
            if len(unique_pages) > 1:
                print(f"\n✅ 좌측 목록 무한스크롤 패턴 확인됨!")
            else:
                print(f"\n❌ 무한스크롤 패턴 미확인 (매물 부족)")

def main():
    analyzer = ListScrollAnalyzer()
    
    # 원래 제공된 URL
    original_url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    # 좌측 목록 스크롤 분석
    analyzer.analyze_list_scroll(original_url)
    
    # 결과 출력
    analyzer.print_list_scroll_summary()
    
    # 결과 저장
    analyzer.save_list_scroll_analysis()

if __name__ == "__main__":
    main()