import requests
from bs4 import BeautifulSoup
import re
import json

def find_token_generation():
    """네이버 부동산 페이지에서 JWT 토큰 생성 과정 찾기"""
    
    # 1. 메인 페이지 접속
    main_url = "https://new.land.naver.com/offices"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    session = requests.Session()
    
    print("1. 메인 페이지 접속 중...")
    response = session.get(main_url, headers=headers)
    print(f"   상태 코드: {response.status_code}")
    
    # 2. HTML에서 JWT 관련 스크립트 찾기
    soup = BeautifulSoup(response.text, 'html.parser')
    scripts = soup.find_all('script')
    
    print("\n2. 스크립트에서 JWT 관련 코드 검색...")
    jwt_patterns = [
        r'jwt|JWT',
        r'token|Token',
        r'authorization|Authorization',
        r'Bearer',
        r'REALESTATE'  # JWT payload에 있던 ID
    ]
    
    for i, script in enumerate(scripts):
        if script.string:
            for pattern in jwt_patterns:
                if re.search(pattern, script.string, re.IGNORECASE):
                    print(f"\n   스크립트 #{i}에서 패턴 '{pattern}' 발견!")
                    # 관련 부분만 출력
                    lines = script.string.split('\n')
                    for j, line in enumerate(lines):
                        if re.search(pattern, line, re.IGNORECASE):
                            start = max(0, j-2)
                            end = min(len(lines), j+3)
                            print("   ---")
                            for k in range(start, end):
                                print(f"   {lines[k].strip()}")
                            print("   ---")
    
    # 3. 네트워크 요청 분석을 위한 정보 수집
    print("\n3. 추가 리소스 URL 수집...")
    
    # JS 파일 URL 수집
    js_files = []
    for script in soup.find_all('script', src=True):
        js_url = script['src']
        if js_url.startswith('/'):
            js_url = f"https://new.land.naver.com{js_url}"
        elif not js_url.startswith('http'):
            js_url = f"https://new.land.naver.com/{js_url}"
        js_files.append(js_url)
        print(f"   JS 파일: {js_url}")
    
    # 4. 주요 JS 파일에서 토큰 생성 로직 찾기
    print("\n4. JS 파일에서 토큰 생성 로직 검색...")
    for js_url in js_files[:5]:  # 처음 5개만 확인
        try:
            js_response = session.get(js_url, headers=headers)
            if js_response.status_code == 200:
                content = js_response.text
                
                # JWT 생성 관련 패턴 검색
                token_patterns = [
                    r'generateToken|createToken|makeToken',
                    r'jwt\.sign|jsonwebtoken',
                    r'REALESTATE.*token',
                    r'authorization.*Bearer'
                ]
                
                for pattern in token_patterns:
                    matches = re.findall(f'.{{0,100}}{pattern}.{{0,100}}', content, re.IGNORECASE)
                    if matches:
                        print(f"\n   {js_url}에서 발견:")
                        for match in matches[:3]:  # 처음 3개만
                            print(f"   {match.strip()}")
                
        except Exception as e:
            print(f"   오류: {e}")
    
    # 5. 쿠키 확인
    print("\n5. 쿠키 확인...")
    for cookie in session.cookies:
        print(f"   {cookie.name}: {cookie.value[:50]}...")
    
    return session

# 실행
session = find_token_generation()

print("\n\n=== 분석 결과 ===")
print("네이버 부동산은 페이지 접속 시 자동으로 JWT 토큰을 생성하는 것으로 보입니다.")
print("토큰은 프론트엔드 JavaScript에서 생성되어 API 호출 시 사용됩니다.")
print("\n가능한 토큰 획득 방법:")
print("1. 브라우저 개발자 도구에서 Network 탭 확인")
print("2. 페이지 로드 후 생성되는 토큰을 localStorage나 sessionStorage에서 확인")
print("3. API 호출 시 Authorization 헤더 확인")