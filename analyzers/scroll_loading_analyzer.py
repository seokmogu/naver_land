#!/usr/bin/env python3
"""
네이버 부동산 스크롤링 무한로딩 분석기
매물 목록을 스크롤하면서 추가 API 호출 패턴을 분석합니다.
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

class ScrollLoadingAnalyzer:
    def __init__(self):
        self.captured_requests = []
        self.captured_responses = []
        self.page_requests = []  # 페이지별 요청 추적
        
    def analyze_scroll_loading(self, url):
        """스크롤링 무한로딩 패턴 분석"""
        print("🔍 스크롤링 무한로딩 패턴 분석 시작...")
        print(f"📄 분석 URL: {url}")
        
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
                        'headers': dict(request.headers),
                        'timestamp': datetime.now().isoformat()
                    }
                    self.captured_requests.append(req_data)
                    
                    # articles API만 추적
                    if '/api/articles?' in request.url:
                        # page 파라미터 추출
                        if 'page=' in request.url:
                            import re
                            page_match = re.search(r'page=(\d+)', request.url)
                            page_num = page_match.group(1) if page_match else 'unknown'
                        else:
                            page_num = '1'  # 기본값
                            
                        print(f"📄 페이지 {page_num} 요청: {request.url.split('?')[0]}")
                        self.page_requests.append({
                            'page': page_num,
                            'url': request.url,
                            'timestamp': datetime.now().isoformat()
                        })
            
            def handle_response(response):
                if 'new.land.naver.com/api' in response.url:
                    try:
                        response_data = {
                            'url': response.url,
                            'status': response.status,
                            'headers': dict(response.headers),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # JSON 응답 파싱
                        try:
                            if 'application/json' in response.headers.get('content-type', ''):
                                body = response.json()
                                response_data['body'] = body
                                
                                # articles API 응답 분석
                                if '/api/articles?' in response.url and 'articleList' in body:
                                    article_count = len(body['articleList'])
                                    total_count = body.get('articleCount', 0)
                                    
                                    # page 파라미터 추출
                                    import re
                                    page_match = re.search(r'page=(\d+)', response.url)
                                    page_num = page_match.group(1) if page_match else '1'
                                    
                                    print(f"✅ 페이지 {page_num} 응답: {article_count}개 매물 (전체: {total_count})")
                        except:
                            response_data['body'] = 'Failed to parse JSON'
                        
                        self.captured_responses.append(response_data)
                        
                    except Exception as e:
                        print(f"❌ 응답 처리 오류: {e}")
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            try:
                print("\n🌐 페이지 로딩 중...")
                page.goto(url, wait_until="networkidle")
                time.sleep(3)
                
                # 매물 목록 로딩 대기
                print("📋 매물 목록 로딩 대기...")
                try:
                    page.wait_for_selector(".item_link, .article_item, .list_item", timeout=10000)
                    print("✅ 매물 목록 로드 완료")
                except:
                    print("⚠️ 매물 목록 로드 실패, 계속 진행...")
                
                # 초기 매물 수 확인
                initial_items = page.query_selector_all(".item_link, .article_item, .list_item")
                print(f"📊 초기 매물 수: {len(initial_items)}개")
                
                # 스크롤링으로 추가 매물 로딩 테스트
                scroll_count = 0
                max_scrolls = 10  # 최대 10번 스크롤
                
                print(f"\n📜 스크롤링 테스트 시작 (최대 {max_scrolls}번)...")
                
                for i in range(max_scrolls):
                    scroll_count += 1
                    print(f"\n🔄 스크롤 {scroll_count}번째...")
                    
                    # 현재 매물 수 확인
                    before_items = page.query_selector_all(".item_link, .article_item, .list_item")
                    before_count = len(before_items)
                    
                    # 페이지 맨 아래로 스크롤
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    
                    # 로딩 대기
                    time.sleep(3)
                    
                    # 스크롤 후 매물 수 확인
                    after_items = page.query_selector_all(".item_link, .article_item, .list_item")
                    after_count = len(after_items)
                    
                    added_count = after_count - before_count
                    print(f"📊 스크롤 후: {before_count} → {after_count} ({added_count:+d}개)")
                    
                    # 더 이상 매물이 추가되지 않으면 중단
                    if added_count == 0:
                        print("📄 더 이상 로딩할 매물이 없습니다.")
                        break
                    
                    # 잠시 대기
                    time.sleep(2)
                
                # 최종 매물 수
                final_items = page.query_selector_all(".item_link, .article_item, .list_item")
                print(f"\n🎯 최종 결과: {len(initial_items)} → {len(final_items)} ({len(final_items) - len(initial_items):+d}개 추가)")
                
                # 추가 스크롤 테스트 (더 많은 데이터 확인)
                print(f"\n🔄 추가 스크롤 테스트...")
                for i in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                
                print("📊 분석 완료!")
                
            except Exception as e:
                print(f"❌ 분석 중 오류: {e}")
            finally:
                time.sleep(2)  # 마지막 응답 대기
                browser.close()
    
    def save_scroll_analysis(self):
        """스크롤 분석 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # articles API 요청만 필터링
        articles_requests = [req for req in self.captured_requests 
                           if '/api/articles?' in req['url']]
        
        # 페이지별 요청 분석
        page_analysis = {}
        for req in self.page_requests:
            page_num = req['page']
            if page_num not in page_analysis:
                page_analysis[page_num] = []
            page_analysis[page_num].append(req)
            
        analysis = {
            "분석시간": timestamp,
            "총_API_요청수": len(self.captured_requests),
            "articles_API_요청수": len(articles_requests),
            "페이지별_요청수": {page: len(reqs) for page, reqs in page_analysis.items()},
            "페이지별_분석": page_analysis,
            "전체_요청": self.captured_requests,
            "전체_응답": self.captured_responses
        }
        
        filename = f"scroll_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 스크롤 분석 결과 저장: {filename}")
        return filename
    
    def print_scroll_summary(self):
        """스크롤 분석 요약 출력"""
        print("\n" + "="*60)
        print("📊 스크롤링 무한로딩 분석 요약")
        print("="*60)
        
        # articles API 요청 통계
        articles_requests = [req for req in self.captured_requests 
                           if '/api/articles?' in req['url']]
        
        print(f"📄 전체 API 요청: {len(self.captured_requests)}개")
        print(f"📋 매물 목록 요청: {len(articles_requests)}개")
        
        # 페이지별 분석
        if self.page_requests:
            print(f"\n📄 페이지별 요청 패턴:")
            page_counts = {}
            for req in self.page_requests:
                page = req['page']
                page_counts[page] = page_counts.get(page, 0) + 1
            
            for page, count in sorted(page_counts.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
                print(f"  - 페이지 {page}: {count}회")
        
        # 무한로딩 패턴 분석
        page_params = set()
        for req in articles_requests:
            if 'page=' in req['url']:
                import re
                page_match = re.search(r'page=(\d+)', req['url'])
                if page_match:
                    page_params.add(int(page_match.group(1)))
        
        if page_params:
            max_page = max(page_params)
            print(f"\n🔄 스크롤링 결과:")
            print(f"  - 최대 페이지: {max_page}")
            print(f"  - 총 페이지 수: {len(page_params)}")
            if max_page > 1:
                print(f"  - 무한로딩 패턴: ✅ 확인됨")
            else:
                print(f"  - 무한로딩 패턴: ❌ 미확인")

def main():
    analyzer = ScrollLoadingAnalyzer()
    
    # 분석할 URL
    test_url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    # 스크롤 분석 실행
    analyzer.analyze_scroll_loading(test_url)
    
    # 결과 출력
    analyzer.print_scroll_summary()
    
    # 결과 저장
    analyzer.save_scroll_analysis()

if __name__ == "__main__":
    main()