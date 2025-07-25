import requests
import json
from datetime import datetime


def quick_comprehensive_test():
    """빠른 종합 수집 테스트"""
    
    # 토큰 로드
    with open('token.txt', 'r') as f:
        token = f.read().strip()
    
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": "https://new.land.naver.com/offices"
    }
    
    print("=== 빠른 종합 수집 테스트 ===\n")
    
    # 1. 클러스터 API로 전체 매물 수 파악
    print("1. 클러스터 분석...")
    cluster_params = {
        "zoom": 15,
        "realEstateType": "SMS",
        "bottomLat": 37.493415,
        "leftLon": 127.024576,
        "topLat": 37.504677,
        "rightLon": 127.037229
    }
    
    cluster_url = "https://new.land.naver.com/api/articles/clusters"
    response = requests.get(cluster_url, params=cluster_params, headers=headers)
    
    if response.status_code == 200:
        clusters = response.json()
        total_from_clusters = sum(c.get('count', 0) for c in clusters)
        print(f"  클러스터에서 발견된 총 매물: {total_from_clusters}개")
        print(f"  클러스터 수: {len(clusters)}개")
    else:
        print(f"  클러스터 API 오류: {response.status_code}")
        return
    
    # 2. 법정동별 수집 비교
    print("\n2. 법정동별 수집...")
    
    cortar_codes = ["1168010100", "1168010200", "1168010300"]  # 역삼동 및 인근
    
    article_url = "https://new.land.naver.com/api/articles"
    total_from_articles = 0
    all_articles = []
    
    for cortar in cortar_codes:
        print(f"\n  법정동 {cortar} 수집:")
        page = 1
        cortar_articles = []
        
        while page <= 10:  # 최대 10페이지만 테스트
            params = {
                "cortarNo": cortar,
                "order": "rank",
                "realEstateType": "SMS",
                "page": str(page),
                "rentPriceMin": "0",
                "rentPriceMax": "900000000",
                "priceMin": "0", 
                "priceMax": "900000000"
            }
            
            response = requests.get(article_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articleList', [])
                
                if not articles:
                    print(f"    페이지 {page}: 데이터 없음")
                    break
                    
                cortar_articles.extend(articles)
                print(f"    페이지 {page}: {len(articles)}개")
                
                if not data.get('isMoreData', False):
                    print(f"    더 이상 데이터 없음")
                    break
                    
                page += 1
            else:
                print(f"    페이지 {page} 오류: {response.status_code}")
                break
        
        print(f"  {cortar} 총 매물: {len(cortar_articles)}개")
        all_articles.extend(cortar_articles)
        total_from_articles += len(cortar_articles)
    
    # 3. 결과 비교
    print(f"\n=== 수집 결과 비교 ===")
    print(f"클러스터 API 예상 매물: {total_from_clusters}개")
    print(f"법정동별 실제 수집: {total_from_articles}개")
    print(f"수집률: {(total_from_articles/total_from_clusters*100):.1f}%" if total_from_clusters > 0 else "N/A")
    
    # 4. 중복 확인
    unique_articles = {}
    for article in all_articles:
        article_id = article.get('articleNo')
        if article_id:
            unique_articles[article_id] = article
    
    print(f"중복 제거 후: {len(unique_articles)}개")
    
    # 5. 샘플 데이터 저장
    if unique_articles:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quick_test_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(list(unique_articles.values()), f, ensure_ascii=False, indent=2)
        
        print(f"샘플 데이터 저장: {filename}")
        
        # 지역별 분포 확인
        area_count = {}
        for article in unique_articles.values():
            area = article.get('roadAddress', '').split()[0:2]  # 구 동
            area_key = ' '.join(area) if area else 'Unknown'
            area_count[area_key] = area_count.get(area_key, 0) + 1
        
        print(f"\n지역별 분포:")
        for area, count in sorted(area_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {area}: {count}개")


if __name__ == "__main__":
    quick_comprehensive_test()