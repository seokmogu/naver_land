#!/usr/bin/env python3
"""
네이버 부동산 무한스크롤 분석기
제공된 특정 URL에서 모든 매물을 무한스크롤로 로딩하며 API 패턴 분석
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

class InfinityScrollAnalyzer:
    def __init__(self):
        self.captured_requests = []
        self.captured_responses = []
        self.page_loads = []  # 페이지별 로딩 추적
        
    def analyze_infinity_scroll(self, url):
        """무한스크롤 패턴 정확 분석"""
        print("🔄 무한스크롤 패턴 분석 시작...")
        print(f"📄 URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=200)
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
                    
                    # articles API 추적
                    if '/api/articles?' in request.url:
                        import re
                        page_match = re.search(r'page=(\d+)', request.url)
                        page_num = page_match.group(1) if page_match else '1'
                        print(f"📄 API 요청 - 페이지 {page_num}")
            
            def handle_response(response):
                if 'new.land.naver.com/api' in response.url:
                    try:
                        response_data = {
                            'url': response.url,
                            'status': response.status,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # articles API 응답 분석
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
                                    
                                    print(f"✅ API 응답 - 페이지 {page_num}: {article_count}개 매물 (전체: {total_count})")
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
                
                # 매물 목록 대기
                print("📋 매물 목록 로딩 대기...")
                page.wait_for_selector(".item_link", timeout=15000)
                
                # 초기 매물 수 확인
                initial_items = page.query_selector_all(".item_link")
                print(f"📊 초기 매물: {len(initial_items)}개")
                
                # 페이지 정보 확인
                try:
                    # 총 매물 수 표시 찾기
                    total_element = page.query_selector(".filter_number, .total_count, .result_count")
                    if total_element:
                        total_text = total_element.inner_text()
                        print(f"📊 총 매물 표시: {total_text}")
                except:
                    pass
                
                # 무한스크롤 시작
                print(f"\n🔄 무한스크롤 시작...")
                scroll_count = 0
                max_scrolls = 20  # 최대 20번 스크롤
                no_change_count = 0  # 변화 없는 횟수
                
                last_count = len(initial_items)
                
                for i in range(max_scrolls):
                    scroll_count += 1
                    print(f"\n📜 스크롤 {scroll_count}번...")
                    
                    # 현재 위치에서 스크롤
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    
                    # 로딩 대기
                    time.sleep(3)
                    
                    # 매물 수 확인
                    current_items = page.query_selector_all(".item_link")
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
                    
                    # 로딩 인디케이터 확인
                    try:
                        loading = page.query_selector(".loading, .spinner, .load-more")
                        if loading and loading.is_visible():
                            print("⏳ 로딩 중...")
                            time.sleep(2)
                    except:
                        pass
                
                # 최종 결과
                final_items = page.query_selector_all(".item_link")
                total_loaded = len(final_items)
                total_added = total_loaded - len(initial_items)
                
                print(f"\n🎯 최종 결과:")
                print(f"   초기: {len(initial_items)}개")
                print(f"   최종: {total_loaded}개")
                print(f"   추가: {total_added}개")
                print(f"   스크롤: {scroll_count}번")
                
                # 페이지 로딩 통계
                if self.page_loads:
                    pages = [int(p['page']) for p in self.page_loads if p['page'].isdigit()]
                    if pages:
                        print(f"   최대 페이지: {max(pages)}")
                        print(f"   총 페이지 수: {len(set(pages))}")
                
                print("📊 분석 완료!")
                
            except Exception as e:
                print(f"❌ 분석 중 오류: {e}")
            finally:
                time.sleep(3)  # 마지막 응답 대기
                browser.close()
    
    def save_infinity_analysis(self):
        """무한스크롤 분석 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # articles API만 필터링
        articles_requests = [req for req in self.captured_requests if req.get('is_articles')]
        articles_responses = [resp for resp in self.captured_responses 
                            if '/api/articles?' in resp['url'] and 'body' in resp]
        
        analysis = {
            "분석시간": timestamp,
            "총_요청수": len(self.captured_requests),
            "articles_요청수": len(articles_requests),
            "articles_응답수": len(articles_responses),
            "페이지_로딩_순서": self.page_loads,
            "로딩된_페이지수": len(set(p['page'] for p in self.page_loads)),
            "전체_요청": self.captured_requests,
            "articles_응답": articles_responses
        }
        
        filename = f"infinity_scroll_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 분석 결과 저장: {filename}")
        return filename
    
    def print_infinity_summary(self):
        """무한스크롤 분석 요약"""
        print("\n" + "="*60)
        print("📊 무한스크롤 분석 요약")
        print("="*60)
        
        articles_requests = [req for req in self.captured_requests if req.get('is_articles')]
        
        print(f"📄 전체 API 요청: {len(self.captured_requests)}개")
        print(f"📋 매물 API 요청: {len(articles_requests)}개")
        
        if self.page_loads:
            pages = [p['page'] for p in self.page_loads]
            unique_pages = list(set(pages))
            
            print(f"\n📄 로딩된 페이지:")
            print(f"   - 총 페이지 수: {len(unique_pages)}")
            print(f"   - 페이지 범위: {min(unique_pages)} ~ {max(unique_pages)}")
            
            print(f"\n📊 페이지별 매물 수:")
            for load in self.page_loads:
                print(f"   - 페이지 {load['page']}: {load['article_count']}개")
            
            total_articles = sum(load['article_count'] for load in self.page_loads)
            print(f"\n🎯 총 로딩된 매물: {total_articles}개")
            
            # 무한스크롤 패턴 확인
            if len(unique_pages) > 1:
                print(f"✅ 무한스크롤 패턴 확인됨!")
            else:
                print(f"❌ 무한스크롤 패턴 미확인")

def main():
    analyzer = InfinityScrollAnalyzer()
    
    # 원래 제공된 URL 사용
    original_url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    # 무한스크롤 분석
    analyzer.analyze_infinity_scroll(original_url)
    
    # 결과 출력
    analyzer.print_infinity_summary()
    
    # 결과 저장
    analyzer.save_infinity_analysis()

if __name__ == "__main__":
    main()