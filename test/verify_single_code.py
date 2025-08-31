#!/usr/bin/env python3
"""
강남구 동별 코드 개별 검증 스크립트
각 코드를 하나씩 안정적으로 검증합니다.
"""

import json
import time
import sys
from playwright.sync_api import sync_playwright

def verify_single_code(area_code, expected_name):
    """단일 지역 코드 검증"""
    
    print(f"🔍 {area_code}:{expected_name} 검증 시작...")
    
    result = {
        'code': area_code,
        'expected_name': expected_name,
        'actual_name': '',
        'article_count': 0,
        'sample_building': '',
        'verification_status': 'failed',
        'error': '',
        'timestamp': time.strftime('%H:%M:%S')
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # 안정성을 위해 headless 모드
            context = browser.new_context()
            page = context.new_page()
            
            # API 응답 캡처
            api_captured = False
            
            def handle_response(response):
                nonlocal api_captured, result
                try:
                    if 'land.naver.com' in response.url and '/api/articles?' in response.url and f'cortarNo={area_code}' in response.url:
                        data = response.json()
                        
                        if data and 'articleList' in data:
                            articles = data['articleList']
                            result['article_count'] = len(articles)
                            
                            if articles:
                                first_article = articles[0]
                                result['actual_name'] = first_article.get('dongName', '')
                                result['sample_building'] = first_article.get('buildingName', '')
                                result['verification_status'] = 'success'
                                
                                print(f"   ✅ API 응답 확인: {result['actual_name']} (매물 {len(articles)}개)")
                                api_captured = True
                            else:
                                result['verification_status'] = 'no_articles'
                                print(f"   ❌ 매물 없음")
                                api_captured = True
                                
                except Exception as e:
                    result['error'] = f"JSON parsing error: {str(e)}"
                    print(f"   ❌ JSON 파싱 오류: {e}")
            
            page.on('response', handle_response)
            
            # 해당 지역코드로 접근
            test_url = f"https://new.land.naver.com/offices?cortarNo={area_code}&ms=37.5,127.0,14&a=SMS&e=RETAIL"
            
            print(f"   📍 URL 접근: {test_url}")
            page.goto(test_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)
            
            # API 응답을 기다림
            max_wait = 10
            wait_count = 0
            while not api_captured and wait_count < max_wait:
                time.sleep(1)
                wait_count += 1
                
                if wait_count == 3:  # 3초 후 상호작용 시도
                    try:
                        page.click("body", timeout=2000)
                        time.sleep(1)
                    except:
                        pass
            
            if not api_captured:
                result['verification_status'] = 'no_api_response'
                result['error'] = 'No API response within timeout'
                print(f"   ❌ API 응답 없음 (시간 초과)")
            
            browser.close()
            
    except Exception as e:
        result['error'] = str(e)
        result['verification_status'] = 'error'
        print(f"   ❌ 오류 발생: {e}")
    
    return result

def main():
    """메인 함수"""
    
    # 강남구 동별 코드 목록
    gangnam_codes = {
        "1168010100": "역삼동",
        "1168010300": "개포동", 
        "1168010400": "논현동",
        "1168010500": "삼성동",
        "1168010600": "대치동",
        "1168010700": "신사동",
        "1168010900": "청담동",
        "1168011000": "압구정동",
        "1168011400": "일원동",
        "1168011500": "수서동",
        "1168011800": "도곡동",
        "1168011200": "자곡동",
        "1168011100": "세곡동",
        "1168011300": "율현동"
    }
    
    # 특정 코드만 테스트하려면 명령행 인수 사용
    if len(sys.argv) > 1:
        test_code = sys.argv[1]
        if test_code in gangnam_codes:
            print(f"🎯 단일 코드 테스트: {test_code}")
            result = verify_single_code(test_code, gangnam_codes[test_code])
            print(f"결과: {result}")
            return
        else:
            print(f"❌ 잘못된 코드: {test_code}")
            return
    
    # 전체 코드 검증
    print(f"🗺️ 강남구 {len(gangnam_codes)}개 동별 코드 검증 시작...")
    
    all_results = {}
    success_count = 0
    
    for i, (code, name) in enumerate(gangnam_codes.items()):
        print(f"\n📍 {i+1}/{len(gangnam_codes)} - {code}:{name}")
        
        result = verify_single_code(code, name)
        all_results[code] = result
        
        if result['verification_status'] == 'success':
            success_count += 1
        
        # 각 검증 사이에 잠시 대기
        time.sleep(2)
    
    # 결과 요약
    print(f"\n" + "="*60)
    print(f"📊 검증 결과 요약")
    print(f"="*60)
    
    verified_codes = []
    failed_codes = []
    
    for code, result in all_results.items():
        if result['verification_status'] == 'success':
            match_status = "✅" if result['expected_name'] in result['actual_name'] or result['actual_name'] in result['expected_name'] else "⚠️"
            print(f"{match_status} {code}: {result['expected_name']} → {result['actual_name']} ({result['article_count']}개)")
            verified_codes.append(code)
        else:
            print(f"❌ {code}: {result['expected_name']} → {result['verification_status']}")
            failed_codes.append(code)
    
    print(f"\n📈 통계:")
    print(f"   성공: {len(verified_codes)}/{len(gangnam_codes)}개")
    print(f"   실패: {len(failed_codes)}개")
    
    # 결과 저장
    output_data = {
        'verification_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_codes': len(gangnam_codes),
        'success_count': len(verified_codes),
        'failed_count': len(failed_codes),
        'verified_codes': verified_codes,
        'failed_codes': failed_codes,
        'detailed_results': all_results
    }
    
    output_file = f"test/single_verification_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 상세 결과가 {output_file}에 저장되었습니다.")

if __name__ == "__main__":
    main()