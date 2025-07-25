import requests
import json
import time
from datetime import datetime
import pandas as pd


class NaverLandCollector:
    def __init__(self):
        self.base_url = "https://new.land.naver.com/api/articles"
        self.headers = {
            "Host": "new.land.naver.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://new.land.naver.com/offices",
            "authorization": ""  # JWT 토큰은 사용자가 설정
        }
        
    def set_authorization(self, token):
        """JWT 토큰 설정"""
        self.headers["authorization"] = f"Bearer {token}"
        
    def fetch_articles(self, params):
        """API 호출하여 매물 데이터 수집"""
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 호출 에러: {e}")
            return None
            
    def collect_all_pages(self, params, max_pages=None):
        """모든 페이지의 데이터 수집"""
        all_articles = []
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
                
            params['page'] = page
            print(f"페이지 {page} 수집 중...")
            
            data = self.fetch_articles(params)
            if not data or 'articleList' not in data:
                break
                
            articles = data.get('articleList', [])
            if not articles:
                break
                
            all_articles.extend(articles)
            
            # API 부하 방지를 위한 딜레이
            time.sleep(0.5)
            page += 1
            
        return all_articles
        
    def save_to_json(self, data, filename):
        """JSON 파일로 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def save_to_csv(self, data, filename):
        """CSV 파일로 저장"""
        if not data:
            print("저장할 데이터가 없습니다.")
            return
            
        # 매물 데이터를 플랫 구조로 변환
        flat_data = []
        for article in data:
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
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        

def main():
    # 수집기 초기화
    collector = NaverLandCollector()
    
    # JWT 토큰 설정 (실제 사용 시 유효한 토큰으로 교체 필요)
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTMzNDcyMjMsImV4cCI6MTc1MzM1ODAyM30.vUgyFI8PGfUDRl_pzFthR2PxHPNglBoPMQz16kfdAYo"
    collector.set_authorization(jwt_token)
    
    # API 파라미터 설정
    params = {
        "cortarNo": "1168010100",  # 지역코드 (강남구 역삼동)
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
        "page": 1,
        "articleState": ""
    }
    
    # 데이터 수집 (최대 10페이지)
    print("데이터 수집 시작...")
    articles = collector.collect_all_pages(params, max_pages=10)
    
    if articles:
        print(f"총 {len(articles)}개의 매물 수집 완료")
        
        # 현재 시간으로 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON으로 저장
        json_filename = f"naver_land_{timestamp}.json"
        collector.save_to_json(articles, json_filename)
        print(f"JSON 파일 저장: {json_filename}")
        
        # CSV로 저장
        csv_filename = f"naver_land_{timestamp}.csv"
        collector.save_to_csv(articles, csv_filename)
        print(f"CSV 파일 저장: {csv_filename}")
    else:
        print("수집된 데이터가 없습니다.")


if __name__ == "__main__":
    main()