#!/usr/bin/env python3
"""
네이버 부동산 API 분석기
실제 페이지에서 호출되는 모든 API를 캡처하고 분석합니다.
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

class NaverAPIAnalyzer:
    def __init__(self):
        self.captured_requests = []
        self.captured_responses = []
        
    def analyze_apis(self, url):
        """페이지의 모든 API 호출 분석"""
        print("🔍 네이버 부동산 API 분석 시작...")
        print(f"📄 분석 URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=1000)  # 시각적 확인을 위해 headless=False
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            page = context.new_page()
            
            # 네트워크 요청/응답 캡처
            def handle_request(request):
                if 'new.land.naver.com/api' in request.url:
                    self.captured_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'headers': dict(request.headers),
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"📡 API 요청: {request.method} {request.url}")
            
            def handle_response(response):
                if 'new.land.naver.com/api' in response.url:
                    try:
                        response_data = {
                            'url': response.url,
                            'status': response.status,
                            'headers': dict(response.headers),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # JSON 응답 파싱 시도
                        try:
                            if 'application/json' in response.headers.get('content-type', ''):
                                body = response.json()
                                response_data['body'] = body
                                print(f"✅ API 응답: {response.status} {response.url} (데이터: {len(str(body))} chars)")
                        except:
                            response_data['body'] = 'Failed to parse JSON'
                            print(f"⚠️ API 응답: {response.status} {response.url} (JSON 파싱 실패)")
                        
                        self.captured_responses.append(response_data)
                        
                    except Exception as e:
                        print(f"❌ 응답 처리 오류: {e}")
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            try:
                print("\n🌐 페이지 로딩 중...")
                page.goto(url, wait_until="networkidle")
                
                print("⏳ 초기 로딩 대기...")
                time.sleep(5)
                
                # 페이지 상호작용으로 추가 API 호출 유발
                print("🖱️ 페이지 상호작용...")
                
                # 스크롤
                page.evaluate("window.scrollTo(0, 500)")
                time.sleep(2)
                
                # 지도 영역 클릭
                try:
                    page.click(".map_wrap", timeout=3000)
                    time.sleep(2)
                except:
                    print("지도 클릭 실패")
                
                # 필터 버튼 클릭 시도
                try:
                    page.click("button", timeout=3000)
                    time.sleep(2)
                except:
                    print("필터 버튼 클릭 실패")
                
                # 페이지 새로고침
                print("🔄 페이지 새로고침...")
                page.reload(wait_until="networkidle")
                time.sleep(5)
                
                print("📊 분석 완료!")
                
            except Exception as e:
                print(f"❌ 분석 중 오류: {e}")
            finally:
                browser.close()
    
    def save_analysis(self):
        """분석 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 요청 분석
        requests_summary = {}
        for req in self.captured_requests:
            endpoint = req['url'].split('?')[0]  # 쿼리 파라미터 제거
            if endpoint not in requests_summary:
                requests_summary[endpoint] = []
            requests_summary[endpoint].append(req)
        
        # 분석 결과
        analysis = {
            "분석시간": timestamp,
            "총_요청수": len(self.captured_requests),
            "총_응답수": len(self.captured_responses),
            "API_엔드포인트_요약": {
                endpoint: len(reqs) for endpoint, reqs in requests_summary.items()
            },
            "상세_요청": self.captured_requests,
            "상세_응답": self.captured_responses
        }
        
        filename = f"naver_api_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 분석 결과 저장: {filename}")
        return filename
    
    def print_summary(self):
        """분석 요약 출력"""
        print("\n" + "="*60)
        print("📊 API 분석 요약")
        print("="*60)
        
        print(f"📡 총 API 요청: {len(self.captured_requests)}개")
        print(f"📥 총 API 응답: {len(self.captured_responses)}개")
        
        # 엔드포인트별 통계
        endpoints = {}
        for req in self.captured_requests:
            endpoint = req['url'].split('?')[0].split('/')[-1]
            endpoints[endpoint] = endpoints.get(endpoint, 0) + 1
        
        print("\n🎯 호출된 API 엔드포인트:")
        for endpoint, count in sorted(endpoints.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {endpoint}: {count}회")
        
        # 주요 API 상세 정보
        print("\n🔍 주요 API 상세:")
        for i, req in enumerate(self.captured_requests[:5]):
            print(f"\n{i+1}. {req['method']} {req['url']}")
            if 'authorization' in req['headers']:
                auth = req['headers']['authorization']
                print(f"   🔑 토큰: {auth[:50]}...")
        
        # 응답 데이터 샘플
        print("\n📄 응답 데이터 샘플:")
        for i, resp in enumerate(self.captured_responses[:3]):
            print(f"\n{i+1}. {resp['url']}")
            print(f"   상태: {resp['status']}")
            if 'body' in resp and isinstance(resp['body'], dict):
                keys = list(resp['body'].keys())[:5]
                print(f"   데이터 키: {keys}")

def main():
    analyzer = NaverAPIAnalyzer()
    
    # 분석할 URL
    test_url = "https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    # API 분석 실행
    analyzer.analyze_apis(test_url)
    
    # 결과 출력
    analyzer.print_summary()
    
    # 결과 저장
    analyzer.save_analysis()

if __name__ == "__main__":
    main()