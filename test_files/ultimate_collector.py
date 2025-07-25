import requests
import json
import time
from datetime import datetime
import pandas as pd
import concurrent.futures


class UltimateNaverLandCollector:
    """궁극의 네이버 부동산 전체 데이터 수집기"""
    
    def __init__(self, token_file="token.txt"):
        self.load_token(token_file)
        self.headers = {
            "authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://new.land.naver.com/offices"
        }
        self.collected_articles = {}
        
    def load_token(self, token_file):
        with open(token_file, 'r') as f:
            self.token = f.read().strip()
            
    def get_all_cortar_codes(self):
        """강남구 전체 법정동 코드 (더 포괄적)"""
        # 강남구 주요 법정동 코드들
        return [
            "1168010100",  # 역삼1동
            "1168010200",  # 역삼2동  
            "1168010300",  # 도곡1동
            "1168010400",  # 도곡2동
            "1168010500",  # 개포1동
            "1168010600",  # 개포2동
            "1168010700",  # 개포4동
            "1168010800",  # 세곡동
            "1168010900",  # 일원본동
            "1168011000",  # 일원1동
            "1168011100",  # 일원2동
            "1168011200",  # 수서동
            "1168011300",  # 논현1동
            "1168011400",  # 논현2동
            "1168011500",  # 압구정동
            "1168011600",  # 신사동
            "1168011700",  # 청담동
            "1168011800",  # 삼성1동
            "1168011900",  # 삼성2동
            "1168012000",  # 대치1동
            "1168012100",  # 대치2동
            "1168012200",  # 대치4동
        ]
        
    def collect_all_pages(self, cortar_no, max_pages=500):
        """법정동의 모든 페이지 수집"""
        print(f"\n{cortar_no} 전체 수집 중...")
        
        base_params = {
            "cortarNo": cortar_no,
            "order": "rank",
            "realEstateType": "SMS",
            "tradeType": "",
            "tag": "::::::::",
            "rentPriceMin": "0",
            "rentPriceMax": "900000000",
            "priceMin": "0", 
            "priceMax": "900000000",
            "areaMin": "0",
            "areaMax": "900000000",
            "showArticle": "false",
            "sameAddressGroup": "false",
            "priceType": "RETAIL",
            "articleState": ""
        }
        
        articles = []
        page = 1
        consecutive_empty = 0
        
        while page <= max_pages and consecutive_empty < 3:
            base_params['page'] = str(page)
            
            try:
                response = requests.get(
                    "https://new.land.naver.com/api/articles",
                    params=base_params,
                    headers=self.headers
                )
                
                if response.status_code == 401:
                    print(f"  토큰 만료됨 (페이지 {page})")
                    break
                elif response.status_code != 200:
                    print(f"  HTTP {response.status_code} 오류 (페이지 {page})")
                    consecutive_empty += 1
                    page += 1
                    continue
                    
                data = response.json()
                page_articles = data.get('articleList', [])
                
                if not page_articles:
                    consecutive_empty += 1
                    if consecutive_empty == 1:
                        print(f"  페이지 {page}: 빈 페이지 시작")
                else:
                    consecutive_empty = 0
                    articles.extend(page_articles)
                    if page % 10 == 0 or page <= 5:
                        print(f"  페이지 {page}: {len(page_articles)}개 (누적: {len(articles)}개)")
                
                # isMoreData 확인
                if not data.get('isMoreData', False) and not page_articles:
                    print(f"  페이지 {page}: 더 이상 데이터 없음")
                    break
                    
                page += 1
                time.sleep(0.1)  # 빠른 수집
                
            except Exception as e:
                print(f"  페이지 {page} 오류: {e}")
                consecutive_empty += 1
                page += 1
                continue
                
        print(f"  {cortar_no} 완료: {len(articles)}개 매물")
        return articles
        
    def collect_with_different_filters(self, cortar_no):
        """다양한 필터 조건으로 수집"""
        print(f"\n{cortar_no} 다중 필터 수집...")
        
        # 다양한 거래 타입으로 수집
        trade_types = ["", "A1", "B1", "B2"]  # 전체, 매매, 전세, 월세
        all_articles = []
        
        for trade_type in trade_types:
            print(f"  거래타입 '{trade_type}' 수집 중...")
            
            params = {
                "cortarNo": cortar_no,
                "order": "rank", 
                "realEstateType": "SMS",
                "tradeType": trade_type,
                "page": "1"
            }
            
            # 첫 페이지만 확인해서 데이터 있는지 체크
            try:
                response = requests.get(
                    "https://new.land.naver.com/api/articles",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('articleList'):
                        # 데이터가 있으면 전체 수집
                        articles = self.collect_all_pages_with_trade_type(cortar_no, trade_type)
                        all_articles.extend(articles)
                        
            except Exception as e:
                print(f"    거래타입 {trade_type} 오류: {e}")
                continue
                
        return all_articles
        
    def collect_all_pages_with_trade_type(self, cortar_no, trade_type, max_pages=200):
        """특정 거래타입으로 모든 페이지 수집"""
        params = {
            "cortarNo": cortar_no,
            "order": "rank",
            "realEstateType": "SMS", 
            "tradeType": trade_type,
            "rentPriceMin": "0",
            "rentPriceMax": "900000000",
            "priceMin": "0",
            "priceMax": "900000000"
        }
        
        articles = []
        page = 1
        
        while page <= max_pages:
            params['page'] = str(page)
            
            try:
                response = requests.get(
                    "https://new.land.naver.com/api/articles",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    break
                    
                data = response.json()
                page_articles = data.get('articleList', [])
                
                if not page_articles:
                    break
                    
                articles.extend(page_articles)
                
                if not data.get('isMoreData', False):
                    break
                    
                page += 1
                time.sleep(0.1)
                
            except:
                break
                
        print(f"    거래타입 {trade_type}: {len(articles)}개")
        return articles
        
    def ultimate_collection(self):
        """궁극의 전체 수집"""
        print("=== 궁극의 전체 데이터 수집 ===\n")
        
        cortar_codes = self.get_all_cortar_codes()
        print(f"수집 대상 법정동: {len(cortar_codes)}개")
        
        start_time = time.time()
        total_collected = 0
        
        for i, cortar in enumerate(cortar_codes, 1):
            print(f"\n[{i}/{len(cortar_codes)}] {cortar} 처리 중...")
            
            # 방법 1: 기본 수집
            articles1 = self.collect_all_pages(cortar, max_pages=100)
            
            # 방법 2: 거래타입별 수집 (더 많은 데이터를 위해)
            articles2 = self.collect_with_different_filters(cortar)
            
            # 중복 제거하며 통합
            for article in articles1 + articles2:
                article_id = article.get('articleNo')
                if article_id and article_id not in self.collected_articles:
                    self.collected_articles[article_id] = article
                    
            current_total = len(self.collected_articles)
            new_count = current_total - total_collected
            total_collected = current_total
            
            print(f"  {cortar}: +{new_count}개 (전체: {total_collected}개)")
            
        elapsed = time.time() - start_time
        print(f"\n수집 완료! 총 {total_collected}개 매물 ({elapsed:.1f}초)")
        
        return list(self.collected_articles.values())
        
    def save_ultimate_results(self, articles):
        """최종 결과 저장"""
        if not articles:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"ultimate_collection_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
            
        # CSV 저장  
        df_data = []
        for article in articles:
            df_data.append({
                '매물번호': article.get('articleNo'),
                '매물명': article.get('articleName'),
                '거래타입': article.get('tradeTypeName'),
                '매매가': article.get('dealOrWarrantPrc'),
                '월세': article.get('rentPrc'),
                '전용면적': article.get('area1'),
                '층수': article.get('floorInfo'),
                '건물명': article.get('buildingName'),
                '주소': article.get('roadAddress'),
                '등록일': article.get('articleConfirmYmd'),
                '중개사': article.get('realtorName'),
                '위도': article.get('latitude'),
                '경도': article.get('longitude')
            })
            
        df = pd.DataFrame(df_data)
        csv_file = f"ultimate_collection_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n=== 최종 저장 ===")
        print(f"JSON: {json_file}")
        print(f"CSV: {csv_file}")
        print(f"총 매물: {len(articles)}개")
        
        # 통계
        stats = df['거래타입'].value_counts()
        print(f"\n거래타입별 통계:")
        for trade_type, count in stats.items():
            print(f"  {trade_type}: {count}개")
            
        return json_file, csv_file


def main():
    collector = UltimateNaverLandCollector()
    
    try:
        # 궁극의 수집 실행
        all_articles = collector.ultimate_collection()
        
        # 결과 저장
        collector.save_ultimate_results(all_articles)
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        # 부분 결과라도 저장
        if collector.collected_articles:
            collector.save_ultimate_results(list(collector.collected_articles.values()))


if __name__ == "__main__":
    main()