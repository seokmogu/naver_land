import requests
import json
from datetime import datetime

def final_collection_test():
    """최종 수집 테스트"""
    
    # 토큰 로드
    with open('token.txt', 'r') as f:
        token = f.read().strip()
    
    # 올바른 헤더 설정
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://new.land.naver.com/offices?ms=37.4990461,127.0309029,15&a=SMS&e=RETAIL",
        "Origin": "https://new.land.naver.com"
    }
    
    print("=== 최종 수집 테스트 ===\n")
    
    # 역삼동 전체 페이지 수집
    url = "https://new.land.naver.com/api/articles"
    all_articles = {}
    
    # 기본 파라미터
    base_params = {
        "cortarNo": "1168010100",  # 역삼동
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
    
    print("역삼동 전체 페이지 수집 중...")
    page = 1
    max_pages = 200
    
    while page <= max_pages:
        params = base_params.copy()
        params['page'] = str(page)
        
        try:
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 403:
                print(f"  페이지 {page}: 403 Forbidden (Referrer 문제)")
                break
            elif response.status_code == 401:
                print(f"  페이지 {page}: 401 Unauthorized (토큰 만료)")
                break
            elif response.status_code != 200:
                print(f"  페이지 {page}: HTTP {response.status_code}")
                break
                
            data = response.json()
            articles = data.get('articleList', [])
            
            if not articles:
                print(f"  페이지 {page}: 빈 페이지")
                break
                
            # 중복 제거하며 추가
            new_count = 0
            for article in articles:
                article_id = article.get('articleNo')
                if article_id and article_id not in all_articles:
                    all_articles[article_id] = article
                    new_count += 1
                    
            print(f"  페이지 {page}: {len(articles)}개 (신규: {new_count}개, 전체: {len(all_articles)}개)")
            
            # 더 이상 데이터가 없으면 중단
            if not data.get('isMoreData', False):
                print(f"  더 이상 데이터가 없습니다.")
                break
                
            page += 1
            
            # 10페이지마다 잠시 대기
            if page % 10 == 0:
                import time
                time.sleep(0.5)
                
        except Exception as e:
            print(f"  페이지 {page} 오류: {e}")
            break
    
    print(f"\n수집 완료: 총 {len(all_articles)}개 매물")
    
    # 결과 저장
    if all_articles:
        articles_list = list(all_articles.values())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"yeoksam_final_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles_list, f, ensure_ascii=False, indent=2)
        
        # 간단한 CSV 저장
        csv_lines = ["매물번호,매물명,거래타입,가격,면적,주소"]
        for article in articles_list[:10]:  # 처음 10개만 미리보기
            line = f"{article.get('articleNo','')},{article.get('articleName','')},{article.get('tradeTypeName','')},{article.get('dealOrWarrantPrc','')},{article.get('area1','')},{article.get('roadAddress','')}"
            csv_lines.append(line)
            
        csv_file = f"yeoksam_sample_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(csv_lines))
        
        print(f"\n파일 저장:")
        print(f"  전체 JSON: {json_file}")
        print(f"  샘플 CSV: {csv_file}")
        
        # 통계
        trade_types = {}
        for article in articles_list:
            trade_type = article.get('tradeTypeName', 'Unknown')
            trade_types[trade_type] = trade_types.get(trade_type, 0) + 1
            
        print(f"\n거래타입별 통계:")
        for trade_type, count in trade_types.items():
            print(f"  {trade_type}: {count}개")
            
        return len(all_articles)
    else:
        print("수집된 데이터가 없습니다.")
        return 0

if __name__ == "__main__":
    final_collection_test()