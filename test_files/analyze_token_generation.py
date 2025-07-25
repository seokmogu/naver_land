import requests
import base64
import json
from datetime import datetime
import re

def decode_jwt(token):
    """JWT 토큰 디코딩"""
    parts = token.split('.')
    if len(parts) != 3:
        return None, None
    
    def pad_base64(data):
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return data
    
    header = json.loads(base64.urlsafe_b64decode(pad_base64(parts[0])))
    payload = json.loads(base64.urlsafe_b64decode(pad_base64(parts[1])))
    
    return header, payload

def analyze_naver_land_page():
    """네이버 부동산 페이지 분석"""
    print("네이버 부동산 페이지 분석 중...")
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    # 1. 메인 페이지 접속
    main_url = "https://new.land.naver.com/offices"
    response = session.get(main_url, headers=headers)
    print(f"메인 페이지 상태: {response.status_code}")
    
    # 2. JavaScript 파일에서 토큰 생성 로직 찾기
    js_pattern = r'<script[^>]*src="([^"]+)"'
    js_urls = re.findall(js_pattern, response.text)
    
    token_endpoints = []
    for js_url in js_urls:
        if js_url.startswith('/'):
            js_url = f"https://new.land.naver.com{js_url}"
        
        try:
            js_response = session.get(js_url, headers=headers)
            if js_response.status_code == 200:
                # 토큰 관련 패턴 찾기
                if 'token' in js_response.text.lower() or 'authorization' in js_response.text.lower():
                    # API 엔드포인트 패턴 찾기
                    api_patterns = [
                        r'/api/[a-zA-Z]+/token',
                        r'/auth/token',
                        r'/token/generate',
                        r'getToken["\']?\s*:\s*["\']([^"\']+)',
                        r'token.*?["\']([^"\']+/token[^"\']*)["\']'
                    ]
                    
                    for pattern in api_patterns:
                        matches = re.findall(pattern, js_response.text)
                        if matches:
                            token_endpoints.extend(matches)
                            print(f"토큰 엔드포인트 발견: {matches}")
        except:
            continue
    
    # 3. 쿠키 확인
    print("\n쿠키 정보:")
    for cookie in session.cookies:
        print(f"  {cookie.name}: {cookie.value[:50]}...")
    
    return session, token_endpoints

def try_get_token_directly(session):
    """직접 토큰 획득 시도"""
    print("\n직접 토큰 획득 시도...")
    
    # 가능한 토큰 엔드포인트들
    possible_endpoints = [
        "https://new.land.naver.com/api/auth/token",
        "https://new.land.naver.com/api/token",
        "https://new.land.naver.com/auth/token",
        "https://new.land.naver.com/api/articles/token",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://new.land.naver.com/offices",
        "Origin": "https://new.land.naver.com"
    }
    
    for endpoint in possible_endpoints:
        try:
            # GET 시도
            response = session.get(endpoint, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'token' in data or 'access_token' in data or 'jwt' in data:
                    print(f"✓ 토큰 발견: {endpoint}")
                    return data
            
            # POST 시도
            post_data = {"id": "REALESTATE", "type": "anonymous"}
            response = session.post(endpoint, json=post_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'token' in data or 'access_token' in data or 'jwt' in data:
                    print(f"✓ 토큰 발견 (POST): {endpoint}")
                    return data
                    
        except Exception as e:
            continue
    
    return None

def analyze_token_pattern():
    """토큰 패턴 분석"""
    print("\n=== 토큰 패턴 분석 ===")
    
    # 샘플 토큰
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTMzNDkxMzYsImV4cCI6MTc1MzM1OTkzNn0.0nZJh8gSjWq9kkWflwTMSUV_ELPWRUISqvzcXkXPf3c"
    
    header, payload = decode_jwt(token)
    print(f"Header: {header}")
    print(f"Payload: {payload}")
    
    if payload:
        iat = datetime.fromtimestamp(payload['iat'])
        exp = datetime.fromtimestamp(payload['exp'])
        print(f"\n발급 시간: {iat}")
        print(f"만료 시간: {exp}")
        print(f"유효 기간: {(exp - iat).total_seconds() / 3600}시간")
        print(f"ID: {payload.get('id')}")
    
    print("\n분석 결과:")
    print("1. 토큰은 서버에서 생성 (HS256 알고리즘)")
    print("2. ID는 항상 'REALESTATE'")
    print("3. 유효기간은 3시간")
    print("4. 페이지 로드 시 자동 발급")

# 실행
if __name__ == "__main__":
    analyze_token_pattern()
    
    # 페이지 분석
    session, endpoints = analyze_naver_land_page()
    
    # 직접 토큰 획득 시도
    token_data = try_get_token_directly(session)
    
    if token_data:
        print(f"\n토큰 획득 성공!")
        print(f"데이터: {token_data}")
    else:
        print(f"\n직접 토큰 획득 실패")
        print("토큰은 JavaScript 실행 환경에서만 생성되는 것으로 보입니다.")