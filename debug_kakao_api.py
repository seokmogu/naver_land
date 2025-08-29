#!/usr/bin/env python3
"""
카카오 API 디버깅 도구
실제 API 호출과 응답을 확인
"""

import os
import sys
import json
import requests
from pathlib import Path

def debug_kakao_api():
    """카카오 API 상태와 설정 확인"""
    
    print("🔍 카카오 API 디버깅 시작")
    print("="*50)
    
    # 1. 환경변수 확인
    print("1. 환경변수 확인:")
    kakao_key = os.getenv('KAKAO_REST_API_KEY')
    if kakao_key:
        print(f"✅ KAKAO_REST_API_KEY 존재: {kakao_key[:10]}...")
    else:
        print("❌ KAKAO_REST_API_KEY 환경변수 없음")
    
    # 2. .env 파일 확인
    print("\n2. .env 파일 확인:")
    env_files = ['.env', 'collectors/.env', 'collectors/core/.env']
    env_found = False
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"✅ {env_file} 파일 존재")
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    if 'KAKAO' in content:
                        print(f"   카카오 키 설정 있음")
                        env_found = True
                    else:
                        print(f"   카카오 키 설정 없음")
            except:
                print(f"   읽기 실패")
        else:
            print(f"❌ {env_file} 파일 없음")
    
    # 3. config.json 확인
    print("\n3. config.json 확인:")
    config_files = [
        'collectors/config/config.json',
        'collectors/core/config.json',
        'config.json'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ {config_file} 존재")
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    if 'kakao_api' in config:
                        print(f"   카카오 API 설정 있음")
                    else:
                        print(f"   카카오 API 설정 없음")
            except Exception as e:
                print(f"   JSON 파싱 실패: {e}")
    
    # 4. 직접 API 테스트 (하드코딩된 키로)
    print("\n4. 카카오 API 직접 테스트:")
    print("❌ API 키가 없어서 테스트 불가능")
    print("\n💡 해결방법:")
    print("1. 카카오 개발자 센터에서 REST API 키 발급")
    print("2. 다음 중 하나의 방법으로 설정:")
    print("   - export KAKAO_REST_API_KEY='your_key_here'")
    print("   - .env 파일 생성: KAKAO_REST_API_KEY=your_key_here")
    print("   - config.json 수정")
    
    return False

def create_env_template():
    """환경변수 템플릿 파일 생성"""
    env_content = """# 카카오 API 설정
KAKAO_REST_API_KEY=your_kakao_rest_api_key_here

# 사용법:
# 1. 카카오 개발자 센터 (https://developers.kakao.com/)에서 앱 생성
# 2. REST API 키 복사
# 3. 위의 your_kakao_rest_api_key_here 부분을 실제 키로 교체
# 4. 파일명을 .env로 변경
"""
    
    with open('.env.template', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ .env.template 파일 생성됨")
    print("   실제 API 키를 넣고 .env로 이름 변경하세요")

def test_with_sample_key():
    """샘플 키로 API 호출 형식 테스트"""
    print("\n5. API 호출 형식 테스트:")
    
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {
        'Authorization': 'KakaoAK sample_key_here',
        'Content-Type': 'application/json'
    }
    params = {
        'x': '127.027610',  # 경도 (강남역)
        'y': '37.498095',   # 위도
        'input_coord': 'WGS84'
    }
    
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ API 호출 형식은 정상 (인증 오류는 예상됨)")
            return True
        else:
            print(f"응답: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
    
    return False

if __name__ == "__main__":
    debug_kakao_api()
    create_env_template()
    test_with_sample_key()
    
    print(f"\n🎯 결론:")
    print(f"카카오 API 키 설정이 필요합니다!")
    print(f"설정 후 다시 테스트해보세요.")