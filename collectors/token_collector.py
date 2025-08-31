#!/usr/bin/env python3
"""
네이버 부동산 JWT Bearer 토큰 수집기 (Playwright 기반)
실제 브라우저에서 동작하는 JWT 토큰 수집 방식으로 개선
"""

import requests
import time
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import re

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright가 설치되지 않았습니다. 브라우저 기반 토큰 수집을 사용할 수 없습니다.")
    print("   설치: pip install playwright && playwright install chromium")

class NaverTokenCollector:
    def __init__(self):
        self.session = requests.Session()
        self.jwt_token = None  # JWT Bearer 토큰
        self.cookies = {}
        self.expires_at = None
        self.use_browser_method = PLAYWRIGHT_AVAILABLE  # Playwright 사용 가능하면 브라우저 방식 우선
        self.last_validation_time = None  # 마지막 토큰 검증 시간
        self.validation_interval = 300  # 5분마다만 토큰 검증
        self.token_refresh_buffer = 5  # 5분 전에만 토큰 갱신
    
    def collect_jwt_token_with_browser(self) -> Optional[Dict]:
        """Playwright를 사용하여 실제 브라우저에서 JWT Bearer 토큰 수집"""
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright를 사용할 수 없어 브라우저 방식 토큰 수집 실패")
            return None
        
        print("🎭 브라우저로 JWT Bearer 토큰 수집 중...")
        
        try:
            with sync_playwright() as p:
                # 브라우저 실행 (완전한 Chrome 모방)
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox', 
                        '--disable-setuid-sandbox', 
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                # 완전한 Chrome 컨텍스트 생성
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    locale='ko-KR',
                    timezone_id='Asia/Seoul',
                    extra_http_headers={
                        'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"Windows"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br, zstd',
                        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Cache-Control': 'max-age=0'
                    }
                )
                
                page = context.new_page()
                
                # webdriver 속성 숨기기 및 Chrome 런타임 추가
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    // Chrome runtime 추가
                    window.chrome = {
                        runtime: {}
                    };
                    
                    // Permissions API 모킹
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)
                
                captured_token = None
                
                # API 요청 감시하여 Bearer 토큰 캡처
                def handle_request(request):
                    nonlocal captured_token
                    if 'land.naver.com' in request.url and '/api/' in request.url:
                        auth_header = request.headers.get('authorization', '')
                        if auth_header.startswith('Bearer ') and not captured_token:
                            captured_token = auth_header.replace('Bearer ', '')
                            print(f"🔥 JWT 토큰 캡처 성공: {captured_token[:30]}...")
                
                page.on('request', handle_request)
                
                print("📄 단계별 네비게이션 시작...")
                
                # 1단계: naver.com 먼저 방문
                print("1️⃣ naver.com 방문...")
                page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                
                # 2단계: land.naver.com 방문
                print("2️⃣ land.naver.com 방문...")
                page.goto("https://land.naver.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                
                # 3단계: 최종 offices 페이지 방문
                print("3️⃣ offices 페이지 방문...")
                target_url = "https://new.land.naver.com/offices?ms=37.4986291,127.0359669,13&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                
                # 페이지 로딩 대기
                print("⏳ 페이지 로딩 대기...")
                try:
                    page.wait_for_selector(".item", timeout=10000)
                    print("✅ 매물 목록 로딩 완료")
                except:
                    print("⚠️ 매물 목록 로딩 중...")
                    page.wait_for_timeout(5000)
                
                # API 요청 트리거
                print("🔄 API 요청 트리거...")
                page.evaluate("window.scrollTo(0, 500)")
                time.sleep(2)
                
                # 지도 상호작용으로 API 요청 유발
                try:
                    page.click(".map_wrap", timeout=5000)
                    time.sleep(2)
                except:
                    pass
                
                # 토큰을 못찾았으면 새로고침
                if not captured_token:
                    print("🔄 페이지 새로고침하여 재시도...")
                    page.reload(wait_until="networkidle")
                    time.sleep(3)
                
                # 최종 결과 확인
                if captured_token:
                    # 쿠키도 함께 수집
                    captured_cookies = context.cookies()
                    cookies = {}
                    for cookie in captured_cookies:
                        cookies[cookie['name']] = cookie['value']
                    # JWT 토큰 파싱하여 만료시간 추출
                    try:
                        import base64
                        # JWT의 payload 부분 디코딩 (두 번째 부분)
                        payload_part = captured_token.split('.')[1]
                        # Base64 패딩 추가
                        payload_part += '=' * (4 - len(payload_part) % 4)
                        payload_decoded = base64.urlsafe_b64decode(payload_part)
                        payload_json = json.loads(payload_decoded)
                        
                        # 만료시간 추출
                        if 'exp' in payload_json:
                            expires_at = datetime.fromtimestamp(payload_json['exp'])
                        else:
                            expires_at = datetime.now() + timedelta(hours=3)  # 기본 3시간
                        
                        print(f"✅ JWT 토큰 만료시간: {expires_at}")
                        
                    except Exception as e:
                        print(f"⚠️ JWT 파싱 실패, 기본 만료시간 사용: {e}")
                        expires_at = datetime.now() + timedelta(hours=3)
                    
                    token_data = {
                        'token': captured_token,
                        'jwt_token': captured_token,  # JWT 토큰
                        'cookies': cookies,
                        'expires_at': expires_at,
                        'collected_at': datetime.now(),
                        'auth_type': 'jwt_bearer'
                    }
                    
                    self.jwt_token = captured_token
                    self.cookies = cookies
                    self.expires_at = expires_at
                    self._token_capture_logged = False  # 다음 수집 시 메시지 출력 허용
                    
                    return token_data
                else:
                    print("❌ JWT 토큰을 캡처하지 못했습니다")
                    return None
                    
        except Exception as e:
            print(f"❌ 브라우저 토큰 수집 실패: {e}")
            return None
        finally:
            try:
                browser.close()
            except:
                pass
    
    def collect_token_from_page(self) -> Optional[Dict]:
        """토큰 수집 - 브라우저 방식 우선, 실패시 기존 방식"""
        # 브라우저 방식이 가능하면 우선 시도
        if self.use_browser_method:
            result = self.collect_jwt_token_with_browser()
            if result:
                return result
            else:
                print("⚠️ 브라우저 방식 실패, 기존 쿠키 방식으로 전환")
        
        # 기존 쿠키 기반 방식
        print("🍪 네이버 랜드 페이지에서 세션 쿠키 수집 중...")
        
        try:
            # 1. 메인 페이지 접속하여 세션 쿠키 획득
            main_url = "https://land.naver.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            response = self.session.get(main_url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"❌ 메인 페이지 접속 실패: {response.status_code}")
                return None
            
            print("✅ 메인 페이지 접속 성공")
            
            # 2. 쿠키 정보 수집 (특히 JSESSIONID)
            cookies = {}
            session_cookies = []
            
            for cookie in self.session.cookies:
                cookies[cookie.name] = cookie.value
                if 'session' in cookie.name.lower() or cookie.name == 'JSESSIONID':
                    session_cookies.append(cookie.name)
            
            print(f"✅ 쿠키 {len(cookies)}개 수집됨")
            if session_cookies:
                print(f"   세션 쿠키: {session_cookies}")
            
            # 3. 쿠키 기반 인증 검증
            if self._verify_session_cookies(cookies):
                token_data = {
                    'token': None,  # 토큰 대신 쿠키 사용
                    'cookies': cookies,
                    'expires_at': datetime.now() + timedelta(hours=2),  # 세션은 2시간
                    'collected_at': datetime.now(),
                    'auth_type': 'cookie'
                }
                
                self.token = None
                self.cookies = cookies
                self.expires_at = token_data['expires_at']
                
                return token_data
            else:
                print("❌ 쿠키 기반 인증 검증 실패")
                return None
                
        except Exception as e:
            print(f"❌ 세션 수집 실패: {e}")
            return None
    
    def _verify_session_cookies(self, cookies: dict) -> bool:
        """쿠키 기반 세션 유효성 검증"""
        print("🔍 세션 쿠키 유효성 검증 중...")
        
        try:
            # 간단한 API 호출로 쿠키 검증 (토큰 없이)
            test_url = "https://new.land.naver.com/api/articles"
            params = {'cortarNo': '1168010700', 'page': 1, 'size': 1}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://land.naver.com/',
                'Origin': 'https://land.naver.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site'
            }
            
            response = requests.get(test_url, headers=headers, params=params, 
                                  cookies=cookies, timeout=10)
            
            print(f"   검증 응답: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'articleList' in data:
                        articles = data.get('articleList', [])
                        print(f"✅ 세션 검증 성공! (매물 {len(articles)}개 발견)")
                        return True
                    elif 'totalCount' in data:
                        print(f"✅ 세션 검증 성공! (totalCount: {data.get('totalCount')})")
                        return True
                except:
                    print("   JSON 파싱 실패하지만 200 응답")
                    return True  # 200이면 일단 성공으로 간주
                    
            elif response.status_code == 429:
                print("   ⚠️ Rate limit이지만 인증은 정상")
                return True  # Rate limit은 인증 문제가 아님
            
            print(f"❌ 세션 검증 실패 (상태코드: {response.status_code})")
            print(f"   응답: {response.text[:200]}")
            return False
            
        except Exception as e:
            print(f"❌ 세션 검증 중 오류: {e}")
            return False
    
    def get_valid_token(self) -> Optional[Dict]:
        """유효한 토큰 반환 (스마트 캐싱으로 불필요한 재수집 방지)"""
        now = datetime.now()
        
        # 최근에 검증했고 토큰이 유효하면 재사용 (5분간 캐시)
        if (self.last_validation_time and 
            (now - self.last_validation_time).seconds < self.validation_interval and
            self.jwt_token and self.expires_at and 
            now < self.expires_at - timedelta(minutes=self.token_refresh_buffer)):
            
            return {
                'token': self.jwt_token,
                'jwt_token': self.jwt_token, 
                'cookies': self.cookies,
                'expires_at': self.expires_at,
                'auth_type': 'jwt_bearer'
            }
        
        # 토큰 재검증/재수집이 필요한 경우
        print(f"🔄 JWT 토큰 검증 중... (마지막 검증: {self.last_validation_time})")
        self.last_validation_time = now
        
        # 기존 토큰이 아직 유효하면 재사용
        if (self.jwt_token and self.expires_at and 
            now < self.expires_at - timedelta(minutes=self.token_refresh_buffer)):
            return {
                'token': self.jwt_token,
                'jwt_token': self.jwt_token, 
                'cookies': self.cookies,
                'expires_at': self.expires_at,
                'auth_type': 'jwt_bearer'
            }
        
        # 토큰이 없거나 만료된 경우 새로 수집
        print("🔁 JWT 토큰 재수집 필요")
        return self.collect_token_from_page()
    
    def get_headers_with_token(self) -> Dict[str, str]:
        """JWT Bearer 토큰이 포함된 헤더 반환"""
        token_data = self.get_valid_token()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Ch-Ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Referer': 'https://new.land.naver.com/',
            'Origin': 'https://new.land.naver.com'
        }
        
        # JWT Bearer 토큰 추가
        if token_data and token_data.get('jwt_token'):
            headers['Authorization'] = f"Bearer {token_data['jwt_token']}"
            self.cookies = token_data.get('cookies', {})
        elif token_data and token_data.get('token'):  # 호환성을 위한 fallback
            headers['Authorization'] = f"Bearer {token_data['token']}"
            self.cookies = token_data.get('cookies', {})
        else:
            print("⚠️ 유효한 JWT 토큰이 없습니다")
        
        return headers