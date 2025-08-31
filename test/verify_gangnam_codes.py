#!/usr/bin/env python3
"""
강남구 동별 코드 검증 스크립트
사용자가 제공한 14개 동별 코드를 Playwright로 검증합니다.
"""

import json
import time
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qs, urlparse

def verify_gangnam_district_codes():
    """사용자 제공 강남구 동별 코드 검증"""
    
    print("🔍 강남구 동별 코드 검증 시작...")
    
    # 사용자 제공 강남구 동별 코드
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
    
    verification_results = {}
    api_responses = []
    
    with sync_playwright() as p:
        # 브라우저 설정
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        # API 응답 캡처
        def handle_response(response):
            try:
                if 'land.naver.com' in response.url and '/api/articles?' in response.url:
                    # 현재 테스트 중인 코드 정보
                    current_code = getattr(handle_response, 'current_code', None)
                    current_name = getattr(handle_response, 'current_name', None)
                    
                    if current_code and f'cortarNo={current_code}' in response.url:
                        try:
                            data = response.json()
                            
                            if data and 'articleList' in data:
                                articles = data['articleList']
                                
                                api_responses.append({
                                    'code': current_code,
                                    'expected_name': current_name,
                                    'url': response.url,
                                    'article_count': len(articles),
                                    'timestamp': time.strftime('%H:%M:%S')
                                })
                                
                                if articles:
                                    # 첫 번째 매물에서 실제 지역명 확인
                                    first_article = articles[0]
                                    actual_dong = first_article.get('dongName', '')
                                    actual_building = first_article.get('buildingName', '')
                                    actual_address = first_article.get('realEstateTypeCode', '')
                                    
                                    # 검증 결과 저장
                                    verification_results[current_code] = {
                                        'expected_name': current_name,
                                        'actual_dong_name': actual_dong,
                                        'article_count': len(articles),
                                        'sample_building': actual_building,
                                        'match_status': 'verified' if current_name in actual_dong or actual_dong in current_name else 'mismatch',
                                        'api_response': True,
                                        'timestamp': time.strftime('%H:%M:%S')
                                    }
                                    
                                    status = "✅" if verification_results[current_code]['match_status'] == 'verified' else "⚠️"
                                    print(f"  {status} {current_code}: {current_name} -> 실제: {actual_dong} (매물 {len(articles)}개)")
                                
                                else:
                                    verification_results[current_code] = {
                                        'expected_name': current_name,
                                        'actual_dong_name': 'N/A',
                                        'article_count': 0,
                                        'sample_building': '',
                                        'match_status': 'no_articles',
                                        'api_response': True,
                                        'timestamp': time.strftime('%H:%M:%S')
                                    }
                                    print(f"  ❌ {current_code}: {current_name} -> 매물 없음")
                        
                        except Exception as e:
                            print(f"     ❌ JSON 파싱 오류: {e}")
                            verification_results[current_code] = {
                                'expected_name': current_name,
                                'actual_dong_name': 'ERROR',
                                'article_count': 0,
                                'sample_building': '',
                                'match_status': 'api_error',
                                'api_response': False,
                                'error': str(e),
                                'timestamp': time.strftime('%H:%M:%S')
                            }
                        
            except Exception as e:
                print(f"     ❌ 응답 처리 오류: {e}")
        
        page.on('response', handle_response)
        
        print("1️⃣ 네이버 부동산 초기 접속...")
        page.goto("https://land.naver.com", wait_until="domcontentloaded")
        time.sleep(2)
        
        # 각 동별 코드 검증
        print(f"\n2️⃣ {len(gangnam_codes)}개 동별 코드 검증 시작...")
        
        for i, (code, expected_name) in enumerate(gangnam_codes.items()):
            print(f"\n📍 {i+1}/{len(gangnam_codes)} - {code}:{expected_name} 검증 중...")
            
            # 현재 테스트 코드 설정
            handle_response.current_code = code
            handle_response.current_name = expected_name
            
            try:
                # 해당 지역코드로 직접 URL 접근
                test_url = f"https://new.land.naver.com/offices?cortarNo={code}&ms=37.5,127.0,14&a=SMS&e=RETAIL"
                page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(3)
                
                # 페이지 상호작용으로 API 호출 유발
                try:
                    page.click(".map_wrap", timeout=5000)
                    time.sleep(1)
                    
                    # 스크롤로 추가 데이터 로드
                    page.evaluate("window.scrollTo(0, 300)")
                    time.sleep(1)
                    
                except Exception as interaction_error:
                    print(f"     ⚠️ 페이지 상호작용 실패: {interaction_error}")
                
                # 코드가 검증되지 않은 경우 오류로 기록
                if code not in verification_results:
                    verification_results[code] = {
                        'expected_name': expected_name,
                        'actual_dong_name': 'NO_RESPONSE',
                        'article_count': 0,
                        'sample_building': '',
                        'match_status': 'no_api_response',
                        'api_response': False,
                        'timestamp': time.strftime('%H:%M:%S')
                    }
                    print(f"     ❌ {code}:{expected_name} -> API 응답 없음")
                
            except Exception as e:
                print(f"     ❌ {code}:{expected_name} 테스트 실패: {e}")
                verification_results[code] = {
                    'expected_name': expected_name,
                    'actual_dong_name': 'ERROR', 
                    'article_count': 0,
                    'sample_building': '',
                    'match_status': 'page_error',
                    'api_response': False,
                    'error': str(e),
                    'timestamp': time.strftime('%H:%M:%S')
                }
        
        print("\n3️⃣ 검증 완료, 브라우저 종료...")
        browser.close()
    
    # 검증 결과 분석 및 출력
    print("\n" + "="*80)
    print("📊 강남구 동별 코드 검증 결과")
    print("="*80)
    
    verified_count = 0
    mismatch_count = 0
    no_articles_count = 0
    error_count = 0
    
    print(f"\n✅ 성공적으로 검증된 코드들:")
    for code, result in verification_results.items():
        if result['match_status'] == 'verified':
            verified_count += 1
            print(f"   {code}: {result['expected_name']} ✓ (실제: {result['actual_dong_name']}, 매물: {result['article_count']}개)")
    
    print(f"\n⚠️ 이름 불일치 코드들:")
    for code, result in verification_results.items():
        if result['match_status'] == 'mismatch':
            mismatch_count += 1
            print(f"   {code}: {result['expected_name']} → {result['actual_dong_name']} (매물: {result['article_count']}개)")
    
    print(f"\n❓ 매물 없는 코드들:")
    for code, result in verification_results.items():
        if result['match_status'] == 'no_articles':
            no_articles_count += 1
            print(f"   {code}: {result['expected_name']} (매물 없음)")
    
    print(f"\n❌ 오류 발생 코드들:")
    for code, result in verification_results.items():
        if result['match_status'] in ['api_error', 'page_error', 'no_api_response']:
            error_count += 1
            print(f"   {code}: {result['expected_name']} (오류: {result['match_status']})")
    
    print(f"\n📈 검증 통계:")
    print(f"   총 코드 수: {len(gangnam_codes)}개")
    print(f"   검증 성공: {verified_count}개")
    print(f"   이름 불일치: {mismatch_count}개") 
    print(f"   매물 없음: {no_articles_count}개")
    print(f"   오류 발생: {error_count}개")
    
    # 결과를 JSON 파일로 저장
    final_results = {
        'verification_info': {
            'total_codes': len(gangnam_codes),
            'verified_count': verified_count,
            'mismatch_count': mismatch_count,
            'no_articles_count': no_articles_count,
            'error_count': error_count,
            'verification_time': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'code_verification_results': verification_results,
        'api_responses': api_responses
    }
    
    output_file = f"test/gangnam_code_verification_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 검증 결과가 {output_file}에 저장되었습니다.")
    
    return verification_results

if __name__ == "__main__":
    verify_gangnam_district_codes()