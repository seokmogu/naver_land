#!/usr/bin/env python3
"""
현재 네이버 부동산 API 상태 테스트
"""

import requests
import time
from playwright_token_collector import PlaywrightTokenCollector

def test_api_with_delays():
    """지연을 두고 API 테스트"""
    print("🔍 현재 네이버 부동산 API 상태 테스트")
    
    # 토큰 획득
    print("🔑 토큰 수집 중...")
    token_collector = PlaywrightTokenCollector()
    token = token_collector.get_token_with_playwright()
    
    if not token:
        print("❌ 토큰 획득 실패")
        return False
    
    print(f"✅ 토큰 획득 성공: {token[:50]}...")
    
    headers = {
        'authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://new.land.naver.com/',
    }
    
    # 테스트 시나리오들
    tests = [
        {
            "name": "지역코드 조회 (역삼동)",
            "url": "https://new.land.naver.com/api/cortars",
            "params": {
                'zoom': 15,
                'centerLat': 37.500775,
                'centerLon': 127.0359
            }
        },
        {
            "name": "매물 목록 조회 (역삼동)",
            "url": "https://new.land.naver.com/api/articles",
            "params": {
                'cortarNo': '1168010100',
                'order': 'rank',
                'realEstateType': 'SG:SMS:GJCG:APTHGJ:GM:TJ',
                'page': 1
            }
        }
    ]
    
    success_count = 0
    
    for i, test in enumerate(tests):
        print(f"\n📋 테스트 {i+1}: {test['name']}")
        
        # Rate limit 방지를 위해 충분한 지연
        if i > 0:
            print("⏳ Rate limit 방지 대기 (60초)...")
            time.sleep(60)
        
        try:
            response = requests.get(
                test['url'],
                headers=headers,
                params=test['params'],
                timeout=30
            )
            
            print(f"   응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 성공: 데이터 길이 {len(str(data))}")
                success_count += 1
                
                # 간단한 데이터 구조 출력
                if isinstance(data, dict):
                    print(f"   키: {list(data.keys())}")
                elif isinstance(data, list) and data:
                    print(f"   배열 길이: {len(data)}")
                    if isinstance(data[0], dict):
                        print(f"   첫 번째 항목 키: {list(data[0].keys())}")
            
            elif response.status_code == 429:
                print(f"   ⚠️ Rate limit: {response.text}")
            else:
                print(f"   ❌ 실패: {response.text}")
        
        except Exception as e:
            print(f"   ❌ 오류: {e}")
    
    print(f"\n📊 테스트 결과: {success_count}/{len(tests)} 성공")
    return success_count > 0

def check_recent_results():
    """최근 수집 결과 분석"""
    print("\n🔍 최근 수집 결과 분석")
    
    import os
    import json
    from datetime import datetime
    
    results_dir = "/home/hackit/projects/naver_land/collectors/results"
    
    if not os.path.exists(results_dir):
        print("❌ results 디렉토리가 없습니다")
        return
    
    files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    files.sort(reverse=True)  # 최신 순
    
    print(f"📁 수집 결과 파일: {len(files)}개")
    
    for filename in files[:3]:  # 최근 3개만
        filepath = os.path.join(results_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 수집 정보 추출
            collection_info = data.get('수집정보', {})
            properties = data.get('매물목록', [])
            
            print(f"\n📄 {filename}")
            print(f"   수집시간: {collection_info.get('수집시간', 'N/A')}")
            print(f"   지역코드: {collection_info.get('지역코드', 'N/A')}")
            print(f"   수집방식: {collection_info.get('수집방식', 'N/A')}")
            print(f"   매물 수: {len(properties)}개")
            
            if properties:
                sample = properties[0]
                print(f"   샘플 매물 키: {list(sample.keys())[:5]}...")
        
        except Exception as e:
            print(f"❌ {filename} 읽기 실패: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("📋 네이버 부동산 수집기 현재 상태 점검")
    print("=" * 60)
    
    # 최근 수집 결과 분석
    check_recent_results()
    
    # 현재 API 상태 테스트
    user_input = input("\nAPI 테스트를 진행하시겠습니까? (Rate limit 위험) (y/N): ")
    if user_input.lower() == 'y':
        test_api_with_delays()
    else:
        print("API 테스트를 건너뜁니다.")
    
    print("\n✅ 상태 점검 완료")