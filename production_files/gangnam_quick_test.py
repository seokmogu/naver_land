import requests
import json
import time
import os
from datetime import datetime
import pandas as pd


def quick_gangnam_test():
    """강남구 핵심 지역 빠른 테스트"""
    
    # 토큰 로드
    with open('token.txt', 'r') as f:
        token = f.read().strip()
    
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": "https://new.land.naver.com/offices"
    }
    
    # 강남구 핵심 3개 동만 테스트
    test_areas = [
        ("1168010100", "역삼1동"),
        ("1168011300", "논현1동"),
        ("1168011800", "삼성1동")
    ]
    
    print("🏢 강남구 핵심 지역 빠른 수집 테스트")
    print("=" * 45)
    
    all_articles = {}
    url = "https://new.land.naver.com/api/articles"
    
    for cortar_no, dong_name in test_areas:
        print(f"\n📍 {dong_name} ({cortar_no}) 수집 중...")
        
        page = 1
        dong_articles = 0
        
        while page <= 50:  # 최대 50페이지
            params = {
                "cortarNo": cortar_no,
                "order": "rank",
                "realEstateType": "SMS",
                "page": str(page),
                "rentPriceMin": "0",
                "rentPriceMax": "900000000",
                "priceMin": "0",
                "priceMax": "900000000"
            }
            
            try:
                response = requests.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    print(f"    페이지 {page}: HTTP {response.status_code}")
                    break
                    
                data = response.json()
                articles = data.get('articleList', [])
                
                if not articles:
                    print(f"    페이지 {page}: 빈 페이지")
                    break
                    
                # 중복 제거하며 추가
                new_count = 0
                for article in articles:
                    article_id = article.get('articleNo')
                    if article_id and article_id not in all_articles:
                        all_articles[article_id] = article
                        new_count += 1
                        dong_articles += 1
                        
                if page % 10 == 0 or page <= 5:
                    print(f"    페이지 {page}: {len(articles)}개 (신규: {new_count}개)")
                
                if not data.get('isMoreData', False):
                    print(f"    더 이상 데이터 없음")
                    break
                    
                page += 1
                time.sleep(0.05)
                
            except Exception as e:
                print(f"    페이지 {page} 오류: {e}")
                break
                
        print(f"  ✓ {dong_name}: {dong_articles}개 매물 (전체: {len(all_articles)}개)")
    
    # 결과 저장
    if all_articles:
        articles_list = list(all_articles.values())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"gangnam_quick_{timestamp}.json"
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
                '건물명': article.get('buildingName'),
                '주소': article.get('roadAddress'),
                '위도': article.get('latitude'),
                '경도': article.get('longitude'),
                '중개사': article.get('realtorName'),
                '등록일': article.get('articleConfirmYmd')
            })
            
        df = pd.DataFrame(df_data)
        csv_file = f"gangnam_quick_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n📁 결과 저장 완료:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")
        print(f"   총 매물: {len(articles_list)}개")
        
        # 간단한 통계
        print(f"\n📊 거래타입별 통계:")
        trade_stats = df['거래타입'].value_counts()
        for trade_type, count in trade_stats.items():
            print(f"   {trade_type}: {count}개")
            
        return len(articles_list)
    else:
        print("수집된 데이터가 없습니다.")
        return 0


if __name__ == "__main__":
    total = quick_gangnam_test()