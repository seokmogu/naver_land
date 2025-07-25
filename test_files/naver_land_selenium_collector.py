import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import time
import json
import pandas as pd
from datetime import datetime
import os


class NaverLandSeleniumCollector:
    """Selenium을 사용한 네이버 부동산 데이터 수집기"""
    
    def __init__(self, headless=True):
        self.token = None
        self.base_url = "https://new.land.naver.com/api/articles"
        self.setup_driver(headless)
        
    def setup_driver(self, headless):
        """Chrome 드라이버 설정"""
        options = webdriver.ChromeOptions()
        
        # 기본 옵션
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        
        # 네트워크 로그 활성화
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        try:
            # webdriver-manager를 사용하여 자동으로 ChromeDriver 다운로드
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Chrome 드라이버 설정 실패: {e}")
            print("\nChrome 브라우저가 설치되어 있는지 확인하세요.")
            print("Chrome이 설치되어 있지 않다면:")
            print("sudo apt-get install google-chrome-stable")
            raise
            
    def wait_and_get_token(self, url="https://new.land.naver.com/offices", max_wait=30):
        """페이지 로드 후 토큰 획득"""
        print(f"1. 페이지 접속: {url}")
        self.driver.get(url)
        
        # 토큰 캡처를 위한 JavaScript 주입
        capture_script = """
        // 토큰 저장 변수
        window.__captured_token = null;
        window.__captured_requests = [];
        
        // XMLHttpRequest 가로채기
        (function() {
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
            
            XMLHttpRequest.prototype.open = function(method, url) {
                this.__url = url;
                this.__method = method;
                return originalOpen.apply(this, arguments);
            };
            
            XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                if (header.toLowerCase() === 'authorization' && value.includes('Bearer')) {
                    window.__captured_token = value.replace('Bearer ', '');
                    window.__captured_requests.push({
                        url: this.__url,
                        method: this.__method,
                        token: window.__captured_token,
                        timestamp: new Date().toISOString()
                    });
                }
                return originalSetRequestHeader.apply(this, arguments);
            };
        })();
        
        // Fetch API 가로채기
        (function() {
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                if (options && options.headers && options.headers.authorization) {
                    const token = options.headers.authorization.replace('Bearer ', '');
                    window.__captured_token = token;
                    window.__captured_requests.push({
                        url: url,
                        method: options.method || 'GET',
                        token: token,
                        timestamp: new Date().toISOString()
                    });
                }
                return originalFetch.apply(this, arguments);
            };
        })();
        
        console.log('Token capture script injected');
        """
        
        self.driver.execute_script(capture_script)
        print("2. 토큰 캡처 스크립트 주입 완료")
        
        # 페이지 로드 대기
        time.sleep(3)
        
        # API 호출 유도 (스크롤, 클릭 등)
        print("3. API 호출 유도 중...")
        self.driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        # 지역 선택 시도 (API 호출 트리거)
        try:
            # 지역 버튼 클릭 시도
            region_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[class*='area_'] button, [class*='filter'] button"))
            )
            region_button.click()
            time.sleep(1)
        except:
            pass
        
        # 토큰 확인
        print("4. 토큰 확인 중...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # JavaScript에서 캡처한 토큰 확인
            captured_token = self.driver.execute_script("return window.__captured_token;")
            if captured_token:
                print(f"✓ 토큰 획득 성공!")
                self.token = captured_token
                
                # 캡처된 요청 정보 출력
                requests_info = self.driver.execute_script("return window.__captured_requests;")
                if requests_info:
                    print(f"  캡처된 API 요청 수: {len(requests_info)}")
                    for req in requests_info[-3:]:  # 최근 3개만 표시
                        print(f"  - {req['method']} {req['url'][:50]}...")
                
                return captured_token
            
            # 네트워크 로그 확인
            logs = self.driver.get_log('performance')
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if message['message']['method'] == 'Network.requestWillBeSentExtraInfo':
                        headers = message['message']['params'].get('headers', {})
                        auth = headers.get('authorization', '')
                        
                        if auth.startswith('Bearer '):
                            self.token = auth[7:]
                            print(f"✓ 네트워크 로그에서 토큰 획득!")
                            return self.token
                except:
                    continue
            
            time.sleep(1)
        
        print("✗ 토큰 획득 실패")
        return None
    
    def collect_data(self, params, max_pages=5):
        """토큰을 사용하여 데이터 수집"""
        if not self.token:
            print("토큰이 없습니다. 먼저 토큰을 획득하세요.")
            return None
        
        headers = {
            "authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://new.land.naver.com/offices"
        }
        
        all_articles = []
        page = 1
        
        print(f"\n데이터 수집 시작 (최대 {max_pages}페이지)")
        
        while page <= max_pages:
            params['page'] = page
            print(f"  페이지 {page} 수집 중...", end='')
            
            try:
                response = requests.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                articles = data.get('articleList', [])
                
                if not articles:
                    print(" (데이터 없음)")
                    break
                
                all_articles.extend(articles)
                print(f" ✓ ({len(articles)}개 매물)")
                
                # 더 이상 데이터가 없으면 중단
                if not data.get('isMoreData', False):
                    print("  더 이상 데이터가 없습니다.")
                    break
                
                page += 1
                time.sleep(0.5)  # API 부하 방지
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print(f"\n✗ 토큰이 만료되었습니다. 새 토큰을 획득하세요.")
                else:
                    print(f"\n✗ HTTP 에러: {e}")
                break
            except Exception as e:
                print(f"\n✗ 에러: {e}")
                break
        
        print(f"\n총 {len(all_articles)}개 매물 수집 완료")
        return all_articles
    
    def save_data(self, articles, prefix="naver_land"):
        """데이터 저장"""
        if not articles:
            print("저장할 데이터가 없습니다.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"{prefix}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"JSON 저장: {json_file}")
        
        # CSV 저장
        flat_data = []
        for article in articles:
            flat_article = {
                '매물번호': article.get('articleNo'),
                '매물명': article.get('articleName'),
                '매물타입': article.get('realEstateTypeName'),
                '거래타입': article.get('tradeTypeName'),
                '보증금/매매가': article.get('dealOrWarrantPrc'),
                '월세': article.get('rentPrc'),
                '전용면적': article.get('area1'),
                '공급면적': article.get('area2'),
                '층': article.get('floorInfo'),
                '방향': article.get('direction'),
                '건물명': article.get('buildingName'),
                '주소': article.get('roadAddress', article.get('address')),
                '설명': article.get('articleFeatureDesc'),
                '태그': ', '.join(article.get('tagList', [])),
                '등록일': article.get('articleConfirmYmd'),
                '위도': article.get('latitude'),
                '경도': article.get('longitude'),
                '중개사': article.get('realtorName'),
                '이미지수': article.get('siteImageCount')
            }
            flat_data.append(flat_article)
        
        df = pd.DataFrame(flat_data)
        csv_file = f"{prefix}_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"CSV 저장: {csv_file}")
        
        return json_file, csv_file
    
    def close(self):
        """드라이버 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("브라우저 종료")


def main():
    # 수집기 초기화
    print("=== 네이버 부동산 데이터 수집기 (Selenium) ===\n")
    
    # headless=False로 브라우저 표시 (디버깅용)
    collector = NaverLandSeleniumCollector(headless=False)
    
    try:
        # 1. 토큰 획득
        token = collector.wait_and_get_token()
        
        if not token:
            print("토큰 획득에 실패했습니다.")
            return
        
        print(f"\n획득한 토큰: {token[:50]}...")
        
        # 토큰 저장
        with open('token.txt', 'w') as f:
            f.write(token)
        print("토큰이 token.txt에 저장되었습니다.")
        
        # 2. 데이터 수집
        params = {
            "cortarNo": "1168010100",  # 강남구 역삼동
            "order": "rank",
            "realEstateType": "SMS",  # 소형 오피스텔
            "tradeType": "",
            "tag": "::::::::",
            "rentPriceMin": 0,
            "rentPriceMax": 900000000,
            "priceMin": 0,
            "priceMax": 900000000,
            "areaMin": 0,
            "areaMax": 900000000,
            "showArticle": "false",
            "sameAddressGroup": "false",
            "priceType": "RETAIL",
            "articleState": ""
        }
        
        articles = collector.collect_data(params, max_pages=5)
        
        # 3. 데이터 저장
        if articles:
            collector.save_data(articles)
        
    except Exception as e:
        print(f"\n예외 발생: {e}")
        
    finally:
        collector.close()


if __name__ == "__main__":
    main()