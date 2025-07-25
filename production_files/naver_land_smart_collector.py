import requests
import json
import time
import os
from datetime import datetime, timedelta
import pandas as pd
import base64


class NaverLandSmartCollector:
    """토큰 재사용이 가능한 스마트 네이버 부동산 수집기"""
    
    def __init__(self, token_file="token.txt"):
        self.token_file = token_file
        self.token = None
        self.token_expiry = None
        self.base_url = "https://new.land.naver.com/api/articles"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://new.land.naver.com/offices"
        }
        
    def decode_jwt(self, token):
        """JWT 토큰 디코딩"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
                
            # Base64 패딩 추가
            payload_part = parts[1]
            missing_padding = len(payload_part) % 4
            if missing_padding:
                payload_part += '=' * (4 - missing_padding)
                
            payload = json.loads(base64.urlsafe_b64decode(payload_part))
            return payload
        except:
            return None
    
    def is_token_valid(self, token):
        """토큰 유효성 확인"""
        if not token:
            return False
            
        payload = self.decode_jwt(token)
        if not payload:
            return False
            
        # 만료 시간 확인 (5분 여유)
        exp_time = datetime.fromtimestamp(payload.get('exp', 0))
        current_time = datetime.now()
        
        if exp_time > current_time + timedelta(minutes=5):
            self.token_expiry = exp_time
            return True
            
        return False
    
    def load_token(self):
        """저장된 토큰 로드"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token = f.read().strip()
                    
                if self.is_token_valid(token):
                    self.token = token
                    print(f"✓ 저장된 토큰 로드 성공 (만료: {self.token_expiry})")
                    return True
                else:
                    print("✗ 저장된 토큰이 만료됨")
            except:
                pass
                
        return False
    
    def save_token(self, token):
        """토큰 저장"""
        with open(self.token_file, 'w') as f:
            f.write(token)
        print(f"✓ 토큰 저장: {self.token_file}")
    
    def get_token_from_selenium(self):
        """Selenium으로 토큰 획득 (필요시에만)"""
        print("\n새 토큰이 필요합니다. Selenium으로 획득 중...")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # 토큰 캡처 스크립트
            capture_script = """
            window.__token = null;
            const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
            XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                if (header.toLowerCase() === 'authorization' && value.includes('Bearer')) {
                    window.__token = value.replace('Bearer ', '');
                }
                return originalSetRequestHeader.apply(this, arguments);
            };
            """
            
            driver.get("https://new.land.naver.com/offices")
            driver.execute_script(capture_script)
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            
            token = driver.execute_script("return window.__token;")
            driver.quit()
            
            if token:
                self.token = token
                self.save_token(token)
                self.is_token_valid(token)  # expiry 시간 설정
                print(f"✓ 새 토큰 획득 성공!")
                return True
                
        except Exception as e:
            print(f"✗ Selenium 토큰 획득 실패: {e}")
            
        return False
    
    def ensure_valid_token(self):
        """유효한 토큰 확보"""
        # 1. 기존 토큰 확인
        if self.token and self.is_token_valid(self.token):
            return True
            
        # 2. 저장된 토큰 로드
        if self.load_token():
            return True
            
        # 3. 새 토큰 획득 (Selenium)
        if self.get_token_from_selenium():
            return True
            
        # 4. 수동 입력
        print("\n토큰을 자동으로 획득할 수 없습니다.")
        print("브라우저에서 수동으로 토큰을 가져와주세요:")
        print("1. https://new.land.naver.com/offices 접속")
        print("2. F12 → Network 탭 → 'articles' 요청 찾기")
        print("3. Request Headers의 'authorization: Bearer ...' 복사")
        
        token = input("\n토큰 입력 (Bearer 제외): ").strip()
        if token and self.is_token_valid(token):
            self.token = token
            self.save_token(token)
            return True
            
        return False
    
    def collect_data(self, params, max_pages=10):
        """데이터 수집"""
        if not self.ensure_valid_token():
            print("유효한 토큰을 얻을 수 없습니다.")
            return None
            
        self.headers["authorization"] = f"Bearer {self.token}"
        all_articles = []
        page = 1
        
        print(f"\n데이터 수집 시작 (최대 {max_pages}페이지)")
        
        while page <= max_pages:
            params['page'] = page
            print(f"  페이지 {page} 수집 중...", end='')
            
            try:
                response = requests.get(self.base_url, headers=self.headers, params=params)
                
                if response.status_code == 401:
                    print("\n✗ 토큰 만료됨. 새 토큰 획득 필요")
                    self.token = None
                    if self.ensure_valid_token():
                        self.headers["authorization"] = f"Bearer {self.token}"
                        continue
                    else:
                        break
                        
                response.raise_for_status()
                data = response.json()
                articles = data.get('articleList', [])
                
                if not articles:
                    print(" (데이터 없음)")
                    break
                    
                all_articles.extend(articles)
                print(f" ✓ ({len(articles)}개)")
                
                if not data.get('isMoreData', False):
                    print("  더 이상 데이터가 없습니다.")
                    break
                    
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                print(f"\n✗ 에러: {e}")
                break
                
        print(f"\n총 {len(all_articles)}개 매물 수집 완료")
        return all_articles
    
    def save_data(self, articles, prefix="naver_land"):
        """데이터 저장"""
        if not articles:
            return None, None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"{prefix}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
            
        # CSV 저장
        flat_data = []
        for article in articles:
            flat_data.append({
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
                '중개사': article.get('realtorName')
            })
            
        df = pd.DataFrame(flat_data)
        csv_file = f"{prefix}_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"JSON 저장: {json_file}")
        print(f"CSV 저장: {csv_file}")
        
        return json_file, csv_file


def main():
    print("=== 네이버 부동산 스마트 수집기 ===")
    print("(토큰 재사용 가능, Selenium 최소화)\n")
    
    collector = NaverLandSmartCollector()
    
    # 검색 조건
    params = {
        "cortarNo": "1168010100",  # 강남구 역삼동
        "order": "rank",
        "realEstateType": "SMS",  # 사무실
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
    
    # 데이터 수집
    articles = collector.collect_data(params, max_pages=5)
    
    # 데이터 저장
    if articles:
        collector.save_data(articles)
        
        # 토큰 만료 시간 표시
        if collector.token_expiry:
            remaining = collector.token_expiry - datetime.now()
            hours = remaining.total_seconds() // 3600
            minutes = (remaining.total_seconds() % 3600) // 60
            print(f"\n토큰 남은 시간: {int(hours)}시간 {int(minutes)}분")


if __name__ == "__main__":
    main()