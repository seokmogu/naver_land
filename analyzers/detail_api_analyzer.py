#!/usr/bin/env python3
"""
네이버 부동산 매물 상세 정보 API 분석기
매물 목록에서 개별 매물 클릭 시 호출되는 API를 분석합니다.
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

class DetailAPIAnalyzer:
    def __init__(self):
        self.captured_requests = []
        self.captured_responses = []
        self.detail_apis = []
        
    def analyze_detail_apis(self, url):
        """매물 상세 정보 API 분석"""
        print("🔍 매물 상세 정보 API 분석 시작...")
        print(f"📄 분석 URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=500)
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
                    
                    # 상세 정보 관련 API 필터링
                    if any(keyword in request.url for keyword in ['article', 'detail', 'info']):
                        print(f"📡 상세 API 요청: {request.method} {request.url}")
            
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
                                
                                # 상세 정보 API 응답 필터링
                                if any(keyword in response.url for keyword in ['article', 'detail', 'info']):
                                    print(f"✅ 상세 API 응답: {response.status} {response.url}")
                                    self.detail_apis.append(response_data)
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
                
                print("📋 매물 목록 로딩 대기...")
                # 매물 목록이 로드될 때까지 대기
                try:
                    page.wait_for_selector(".item_link", timeout=10000)
                    print("✅ 매물 목록 로드 완료")
                except:
                    print("⚠️ 매물 목록 로드 실패, 계속 진행...")
                
                # 첫 번째 매물 클릭
                print("\n🖱️ 첫 번째 매물 클릭...")
                try:
                    # 다양한 선택자 시도
                    selectors = [
                        ".item_link",
                        ".article_item",
                        ".list_item",
                        "[data-article-no]",
                        ".item"
                    ]
                    
                    clicked = False
                    for selector in selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            if elements:
                                print(f"🎯 {selector} 선택자로 {len(elements)}개 매물 발견")
                                elements[0].scroll_into_view_if_needed()
                                time.sleep(1)
                                elements[0].click()
                                clicked = True
                                print("✅ 매물 클릭 성공")
                                break
                        except Exception as e:
                            print(f"❌ {selector} 클릭 실패: {e}")
                            continue
                    
                    if not clicked:
                        print("⚠️ 자동 클릭 실패, 수동으로 매물을 클릭해주세요...")
                        time.sleep(10)
                
                except Exception as e:
                    print(f"❌ 매물 클릭 오류: {e}")
                
                # 상세 정보 로딩 대기
                print("⏳ 상세 정보 로딩 대기...")
                time.sleep(5)
                
                # 추가 상세 정보 로딩을 위한 스크롤
                print("📜 상세 페이지 스크롤...")
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(2)
                except:
                    pass
                
                # 두 번째 매물도 클릭해보기
                print("\n🖱️ 두 번째 매물 클릭 시도...")
                try:
                    elements = page.query_selector_all(".item_link, .article_item, .list_item")
                    if len(elements) > 1:
                        elements[1].click()
                        time.sleep(3)
                        print("✅ 두 번째 매물 클릭 성공")
                except:
                    print("⚠️ 두 번째 매물 클릭 실패")
                
                print("📊 분석 완료!")
                
            except Exception as e:
                print(f"❌ 분석 중 오류: {e}")
            finally:
                time.sleep(2)  # 마지막 응답 대기
                browser.close()
    
    def save_detail_analysis(self):
        """상세 API 분석 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 상세 API만 필터링
        detail_requests = [req for req in self.captured_requests 
                          if any(keyword in req['url'] for keyword in ['article', 'detail', 'info'])]
        
        analysis = {
            "분석시간": timestamp,
            "상세_API_요청수": len(detail_requests),
            "상세_API_응답수": len(self.detail_apis),
            "전체_요청수": len(self.captured_requests),
            "전체_응답수": len(self.captured_responses),
            "상세_API_목록": list(set([req['url'].split('?')[0] for req in detail_requests])),
            "상세_요청": detail_requests,
            "상세_응답": self.detail_apis,
            "전체_응답": self.captured_responses
        }
        
        filename = f"detail_api_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 상세 분석 결과 저장: {filename}")
        return filename
    
    def print_detail_summary(self):
        """상세 API 분석 요약 출력"""
        print("\n" + "="*60)
        print("📊 매물 상세 API 분석 요약")
        print("="*60)
        
        # 상세 API 요청 통계
        detail_requests = [req for req in self.captured_requests 
                          if any(keyword in req['url'] for keyword in ['article', 'detail', 'info'])]
        
        print(f"🔍 상세 API 요청: {len(detail_requests)}개")
        print(f"📥 상세 API 응답: {len(self.detail_apis)}개")
        
        # 상세 API 엔드포인트
        if detail_requests:
            endpoints = list(set([req['url'].split('?')[0] for req in detail_requests]))
            print(f"\n🎯 발견된 상세 API 엔드포인트:")
            for endpoint in endpoints:
                count = len([req for req in detail_requests if endpoint in req['url']])
                print(f"  - {endpoint}: {count}회")
        
        # 상세 응답 샘플
        if self.detail_apis:
            print(f"\n📄 상세 응답 샘플:")
            for i, resp in enumerate(self.detail_apis[:3]):
                print(f"\n{i+1}. {resp['url']}")
                print(f"   상태: {resp['status']}")
                if 'body' in resp and isinstance(resp['body'], dict):
                    keys = list(resp['body'].keys())[:5]
                    print(f"   주요 데이터: {keys}")

def main():
    analyzer = DetailAPIAnalyzer()
    
    # 분석할 URL
    test_url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    # 상세 API 분석 실행
    analyzer.analyze_detail_apis(test_url)
    
    # 결과 출력
    analyzer.print_detail_summary()
    
    # 결과 저장
    analyzer.save_detail_analysis()

if __name__ == "__main__":
    main()