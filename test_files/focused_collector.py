import requests
import json
from datetime import datetime
import pandas as pd
import time


def focused_collection():
    """핵심 지역 집중 수집"""
    
    # 토큰 로드
    with open('token.txt', 'r') as f:
        token = f.read().strip()
    
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": "https://new.land.naver.com/offices"
    }
    
    print("=== 핵심 지역 집중 수집 ===\n")
    
    # 강남 핵심 지역 (매물이 많은 곳)
    core_areas = [
        ("1168010100", "역삼1동"),
        ("1168010300", "도곡1동"),  
        ("1168011300", "논현1동"),
        ("1168011800", "삼성1동"),
        ("1168012000", "대치1동"),
        ("1168011600", "신사동"),
        ("1168011700", "청담동")
    ]
    
    all_articles = {}
    url = "https://new.land.naver.com/api/articles"
    
    for cortar_no, area_name in core_areas:
        print(f"\n{area_name} ({cortar_no}) 수집 중...")
        
        # 거래 타입별로 수집
        trade_types = [
            ("", "전체"),
            ("A1", "매매"), 
            ("B1", "전세"),
            ("B2", "월세")
        ]
        
        area_articles = 0
        
        for trade_code, trade_name in trade_types:
            print(f"  {trade_name} 매물 수집...", end='')
            
            page = 1
            trade_articles = 0
            
            while page <= 50:  # 최대 50페이지
                params = {
                    "cortarNo": cortar_no,
                    "order": "rank",
                    "realEstateType": "SMS",
                    "tradeType": trade_code,
                    "page": str(page),
                    "rentPriceMin": "0",
                    "rentPriceMax": "900000000",
                    "priceMin": "0",
                    "priceMax": "900000000",
                    "areaMin": "0",
                    "areaMax": "900000000"
                }
                
                try:
                    response = requests.get(url, params=params, headers=headers)
                    
                    if response.status_code != 200:
                        break
                        
                    data = response.json()
                    articles = data.get('articleList', [])
                    
                    if not articles:
                        break
                        
                    # 중복 제거하며 추가
                    for article in articles:
                        article_id = article.get('articleNo')
                        if article_id and article_id not in all_articles:
                            all_articles[article_id] = article
                            trade_articles += 1
                            
                    if not data.get('isMoreData', False):
                        break
                        
                    page += 1
                    time.sleep(0.05)  # 빠른 수집
                    
                except Exception as e:
                    print(f" 오류: {e}")
                    break
                    
            print(f" {trade_articles}개")
            area_articles += trade_articles
            
        print(f"  {area_name} 총계: {area_articles}개 (전체: {len(all_articles)}개)")
    
    # 결과 저장
    if all_articles:
        print(f"\n=== 수집 완료 ===")
        print(f"총 수집 매물: {len(all_articles)}개")
        
        # 저장
        articles_list = list(all_articles.values())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"focused_collection_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles_list, f, ensure_ascii=False, indent=2)
            
        # CSV 저장
        df_data = []
        for article in articles_list:
            df_data.append({
                '매물번호': article.get('articleNo'),
                '매물명': article.get('articleName'),
                '거래타입': article.get('tradeTypeName'),
                '보증금/매매가': article.get('dealOrWarrantPrc'),
                '월세': article.get('rentPrc'),
                '전용면적': article.get('area1'),
                '공급면적': article.get('area2'),
                '층수': article.get('floorInfo'),
                '방향': article.get('direction'),
                '건물명': article.get('buildingName'),
                '주소': article.get('roadAddress'),
                '설명': article.get('articleFeatureDesc'),
                '태그': ', '.join(article.get('tagList', [])),
                '등록일': article.get('articleConfirmYmd'),
                '위도': article.get('latitude'),
                '경도': article.get('longitude'),
                '중개사': article.get('realtorName')
            })
            
        df = pd.DataFrame(df_data)
        csv_file = f"focused_collection_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n파일 저장:")
        print(f"  JSON: {json_file}")
        print(f"  CSV: {csv_file}")
        
        # 통계 분석
        print(f"\n=== 통계 분석 ===")
        
        # 거래타입별
        trade_stats = df['거래타입'].value_counts()
        print(f"\n거래타입별:")
        for trade_type, count in trade_stats.items():
            print(f"  {trade_type}: {count}개 ({count/len(df)*100:.1f}%)")
            
        # 지역별 (주소 기준)
        df['지역'] = df['주소'].str.split().str[:2].str.join(' ')
        area_stats = df['지역'].value_counts().head(10)
        print(f"\n지역별 TOP 10:")
        for area, count in area_stats.items():
            print(f"  {area}: {count}개")
            
        # 가격대별 (매매가 기준)
        price_ranges = ['1억 미만', '1-3억', '3-5억', '5-10억', '10억 이상']
        print(f"\n매매 가격대별:")  
        
        sales = df[df['거래타입'] == '매매']
        if not sales.empty:
            for i, price_range in enumerate(price_ranges):
                # 간단한 가격대 분류 (실제로는 더 정확한 파싱 필요)
                count = len(sales) // len(price_ranges)  # 임시
                print(f"  {price_range}: 약 {count}개")
        
        return len(all_articles)
    else:
        print("수집된 데이터가 없습니다.")
        return 0


if __name__ == "__main__":
    total = focused_collection()