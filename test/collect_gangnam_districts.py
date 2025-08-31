#!/usr/bin/env python3
"""
네이버 부동산 강남구 동별 코드 수집 스크립트
사용자가 첨부한 이미지의 "강남구지도로 보기" 버튼을 클릭하여 동별 코드를 수집합니다.
"""

import json
import time
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qs, urlparse

def collect_gangnam_district_codes():
    """강남구 동별 코드 수집 메인 함수"""
    
    print("🗺️ 강남구 동별 코드 수집 시작...")
    
    collected_codes = {}
    api_responses = []
    
    with sync_playwright() as p:
        # 브라우저 설정
        browser = p.chromium.launch(
            headless=False,  # 디버깅을 위해 브라우저 창 표시
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        # API 응답 캡처 함수
        def handle_response(response):
            try:
                # 네이버 부동산 API 응답만 캡처
                if 'land.naver.com' in response.url:
                    if '/api/' in response.url or 'articles' in response.url or 'regions' in response.url or 'areas' in response.url:
                        print(f"📡 API 호출 감지: {response.url}")
                        
                        # JSON 응답 파싱 시도
                        try:
                            data = response.json()
                            
                            # URL 파라미터에서 지역 코드 추출
                            parsed_url = urlparse(response.url)
                            params = parse_qs(parsed_url.query)
                            
                            # cortarNo 파라미터 확인
                            cortar_no = params.get('cortarNo', [None])[0]
                            
                            api_responses.append({
                                'url': response.url,
                                'params': params,
                                'cortar_no': cortar_no,
                                'data_keys': list(data.keys()) if isinstance(data, dict) else [],
                                'timestamp': time.strftime('%H:%M:%S')
                            })
                            
                            # 지역 정보가 포함된 응답 분석
                            if isinstance(data, dict):
                                # 지역 리스트나 매물 리스트 확인
                                if 'regionList' in data:
                                    regions = data['regionList']
                                    for region in regions:
                                        if 'cortarNo' in region and 'cortarName' in region:
                                            code = region['cortarNo']
                                            name = region['cortarName']
                                            collected_codes[code] = {
                                                'name': name,
                                                'source': 'regionList',
                                                'timestamp': time.strftime('%H:%M:%S')
                                            }
                                            print(f"✅ 지역 발견: {code} - {name}")
                                
                                elif 'articleList' in data and data['articleList']:
                                    # 매물 리스트에서 지역 정보 추출
                                    articles = data['articleList']
                                    for article in articles[:3]:  # 처음 몇 개만 확인
                                        if 'cortarNo' in article:
                                            code = article['cortarNo']
                                            dong_name = article.get('dongName', article.get('cortarName', 'Unknown'))
                                            
                                            if code not in collected_codes:
                                                collected_codes[code] = {
                                                    'name': dong_name,
                                                    'source': 'articleList',
                                                    'building': article.get('buildingName', ''),
                                                    'timestamp': time.strftime('%H:%M:%S')
                                                }
                                                print(f"✅ 매물에서 지역 발견: {code} - {dong_name}")
                        
                        except Exception as json_error:
                            print(f"   ⚠️ JSON 파싱 실패: {json_error}")
                            
            except Exception as e:
                print(f"   ❌ 응답 처리 오류: {e}")
        
        # 응답 리스너 등록
        page.on('response', handle_response)
        
        print("1️⃣ 네이버 부동산 접속...")
        
        # 사용자가 제공한 URL로 직접 이동
        target_url = "https://new.land.naver.com/offices?ms=37.517408,127.047313,14&a=SMS&e=RETAIL"
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        
        time.sleep(3)
        
        print("2️⃣ 강남구지도로 보기 버튼 찾기...")
        
        # 강남구지도로 보기 버튼이나 관련 요소 찾기
        try:
            # 다양한 선택자로 강남구 지도 버튼 찾기 시도
            selectors_to_try = [
                "text=강남구지도로 보기",
                "[title*='강남구']",
                "button:has-text('강남구')",
                ".region-button:has-text('강남구')",
                "a:has-text('강남구')",
                "[data-region*='강남구']"
            ]
            
            button_found = False
            for selector in selectors_to_try:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"   📍 버튼 발견: {selector}")
                        page.click(selector, timeout=5000)
                        button_found = True
                        print("   ✅ 강남구지도로 보기 버튼 클릭 완료")
                        time.sleep(5)  # API 응답 대기
                        break
                except:
                    continue
            
            if not button_found:
                print("   ⚠️ 강남구지도로 보기 버튼을 찾을 수 없음. 대체 방법 시도...")
                
                # 지도 영역 클릭으로 API 호출 유발
                try:
                    page.click(".map_wrap", timeout=5000)
                    time.sleep(2)
                    
                    # 줌 레벨 조정으로 추가 API 호출
                    page.evaluate("window.history.pushState({}, '', '?ms=37.517408,127.047313,13&a=SMS&e=RETAIL')")
                    page.reload()
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"   ❌ 대체 방법 실패: {e}")
        
        except Exception as e:
            print(f"   ❌ 버튼 클릭 실패: {e}")
        
        print("3️⃣ 강남구 하위 지역 탐색...")
        
        # 강남구 내 다른 동들로 이동하여 추가 데이터 수집
        gangnam_locations = [
            {"name": "신사동", "coords": "37.516221,127.020735"},
            {"name": "논현동", "coords": "37.510178,127.022435"},
            {"name": "압구정동", "coords": "37.527446,127.028915"},
            {"name": "청담동", "coords": "37.519833,127.047222"},
            {"name": "삼성동", "coords": "37.514322,127.058594"},
            {"name": "역삼동", "coords": "37.500705,127.036531"},
            {"name": "대치동", "coords": "37.494668,127.062835"},
        ]
        
        for location in gangnam_locations:
            print(f"   🎯 {location['name']} 지역 탐색...")
            try:
                location_url = f"https://new.land.naver.com/offices?ms={location['coords']},15&a=SMS&e=RETAIL"
                page.goto(location_url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                
                # 해당 지역에서 API 호출 유발
                page.click(".map_wrap", timeout=5000)
                time.sleep(1)
                
            except Exception as e:
                print(f"      ❌ {location['name']} 탐색 실패: {e}")
        
        print("4️⃣ 수집 완료, 브라우저 종료...")
        browser.close()
    
    # 결과 정리 및 출력
    print("\n" + "="*60)
    print("📊 강남구 동별 코드 수집 결과")
    print("="*60)
    
    print(f"🎯 총 발견된 지역 코드: {len(collected_codes)}개")
    print(f"📡 캡처된 API 응답: {len(api_responses)}개")
    
    if collected_codes:
        print("\n✅ 수집된 지역 코드들:")
        for code, info in sorted(collected_codes.items()):
            print(f"   {code}: {info['name']} (출처: {info['source']}, 시간: {info['timestamp']})")
    else:
        print("\n❌ 지역 코드를 수집하지 못했습니다.")
    
    # 결과를 JSON 파일로 저장
    result_data = {
        'collected_codes': collected_codes,
        'api_responses': api_responses,
        'collection_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_codes': len(collected_codes),
        'total_responses': len(api_responses)
    }
    
    output_file = f"test/gangnam_districts_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과가 {output_file}에 저장되었습니다.")
    
    return collected_codes, api_responses

if __name__ == "__main__":
    collect_gangnam_district_codes()