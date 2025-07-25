import requests
import json
from urllib.parse import urlparse, parse_qs
import time


def analyze_url(url):
    """URL 파라미터 분석"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    print("URL 파라미터 분석:")
    
    # ms 파라미터 파싱 (ms=37.4990461,127.0309029,15)
    ms_param = params.get('ms', [''])[0]
    if ms_param:
        coords = ms_param.split(',')
        if len(coords) >= 3:
            print(f"  위도: {coords[0]}")
            print(f"  경도: {coords[1]}")
            print(f"  줌 레벨: {coords[2]}")
            
            return {
                'lat': float(coords[0]),
                'lng': float(coords[1]),
                'zoom': int(coords[2])
            }
    
    print(f"  부동산 타입: {params.get('a', [''])[0]}")  # SMS = 사무실
    print(f"  거래 타입: {params.get('e', [''])[0]}")  # RETAIL = 매매/임대
    
    # 기본값 반환
    return {
        'lat': 37.4990461,
        'lng': 127.0309029,
        'zoom': 15
    }


def get_bounds_from_center(lat, lng, zoom):
    """중심 좌표와 줌 레벨로부터 경계 계산"""
    # 네이버 지도의 줌 레벨별 대략적인 범위 (미터)
    zoom_to_meters = {
        10: 20000,   # 20km
        11: 10000,   # 10km
        12: 5000,    # 5km
        13: 2500,    # 2.5km
        14: 1250,    # 1.25km
        15: 625,     # 625m
        16: 312,     # 312m
        17: 156,     # 156m
        18: 78,      # 78m
        19: 39       # 39m
    }
    
    # 대략적인 위경도 변환 (1도 ≈ 111km)
    meters = zoom_to_meters.get(zoom, 1000)
    lat_diff = meters / 111000
    lng_diff = meters / (111000 * 0.89)  # 위도에 따른 보정
    
    return {
        'leftLon': lng - lng_diff,
        'rightLon': lng + lng_diff,
        'topLat': lat + lat_diff,
        'bottomLat': lat - lat_diff
    }


def analyze_api_structure():
    """네이버 부동산 API 구조 분석"""
    
    # 토큰 로드
    try:
        with open('token.txt', 'r') as f:
            token = f.read().strip()
    except:
        print("token.txt 파일을 찾을 수 없습니다.")
        return
    
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": "https://new.land.naver.com/offices"
    }
    
    # 1. 클러스터 API 분석
    print("\n=== 클러스터 API 분석 ===")
    
    # 역삼동 중심 좌표
    lat, lng = 37.4990461, 127.0309029
    zoom = 15
    
    bounds = get_bounds_from_center(lat, lng, zoom)
    
    cluster_params = {
        "cortarNo": "",
        "zoom": zoom,
        "priceMin": "0",
        "priceMax": "900000000",
        "rentPriceMin": "0", 
        "rentPriceMax": "900000000",
        "areaMin": "0",
        "areaMax": "900000000",
        "tagList": "",
        "realEstateType": "SMS",
        "tradeType": "",
        "bottomLat": bounds['bottomLat'],
        "leftLon": bounds['leftLon'],
        "topLat": bounds['topLat'],
        "rightLon": bounds['rightLon']
    }
    
    cluster_url = "https://new.land.naver.com/api/articles/clusters"
    
    print(f"\n클러스터 요청 파라미터:")
    print(f"  범위: ({bounds['bottomLat']:.6f}, {bounds['leftLon']:.6f}) ~ ({bounds['topLat']:.6f}, {bounds['rightLon']:.6f})")
    print(f"  줌 레벨: {zoom}")
    
    response = requests.get(cluster_url, params=cluster_params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n클러스터 응답:")
        print(f"  클러스터 수: {len(data)}")
        
        total_count = 0
        for cluster in data[:5]:  # 처음 5개만 표시
            count = cluster.get('count', 0)
            total_count += count
            print(f"  - 클러스터: {count}개 매물, 위치: ({cluster.get('lat')}, {cluster.get('lng')})")
        
        print(f"  ... 총 매물 수: {sum(c.get('count', 0) for c in data)}개")
        
        # 클러스터 데이터 저장
        with open('cluster_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return data
    else:
        print(f"클러스터 API 오류: {response.status_code}")
        return None


def analyze_article_list_api():
    """매물 목록 API 분석"""
    
    try:
        with open('token.txt', 'r') as f:
            token = f.read().strip()
    except:
        return
    
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://new.land.naver.com/offices"
    }
    
    print("\n=== 매물 목록 API 분석 ===")
    
    # 특정 지역(역삼동) 매물 조회
    list_params = {
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
        "page": "1"
    }
    
    list_url = "https://new.land.naver.com/api/articles"
    
    # 페이지별로 확인
    all_articles = []
    for page in range(1, 6):
        list_params['page'] = str(page)
        response = requests.get(list_url, params=list_params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articleList', [])
            all_articles.extend(articles)
            
            print(f"\n페이지 {page}:")
            print(f"  매물 수: {len(articles)}")
            print(f"  더 있음: {data.get('isMoreData', False)}")
            
            if not data.get('isMoreData', False):
                break
                
            time.sleep(0.5)
        else:
            print(f"API 오류: {response.status_code}")
            break
    
    print(f"\n총 수집된 매물: {len(all_articles)}개")
    
    # 좌표 분포 분석
    if all_articles:
        lats = [float(a['latitude']) for a in all_articles if a.get('latitude')]
        lngs = [float(a['longitude']) for a in all_articles if a.get('longitude')]
        
        print(f"\n좌표 범위:")
        print(f"  위도: {min(lats):.6f} ~ {max(lats):.6f}")
        print(f"  경도: {min(lngs):.6f} ~ {max(lngs):.6f}")


def propose_collection_strategy():
    """효율적인 수집 전략 제안"""
    
    print("\n=== 효율적인 수집 전략 ===")
    print("\n1. 클러스터 기반 수집:")
    print("   - 넓은 지역을 줌 레벨 13-14로 조회")
    print("   - 각 클러스터의 좌표를 수집")
    print("   - 클러스터별로 상세 매물 조회")
    
    print("\n2. 격자 분할 수집:")
    print("   - 전체 지역을 작은 격자로 분할")
    print("   - 각 격자별로 API 호출")
    print("   - 중복 제거 후 통합")
    
    print("\n3. cortarNo 기반 수집:")
    print("   - 법정동 코드(cortarNo) 리스트 확보")
    print("   - 각 동별로 전체 페이지 수집")
    print("   - 가장 정확하고 완전한 방법")
    
    print("\n4. 하이브리드 방식:")
    print("   - 클러스터로 매물 밀집 지역 파악")
    print("   - 밀집 지역은 상세 수집")
    print("   - 희박 지역은 넓게 수집")


if __name__ == "__main__":
    # URL 분석
    url = "https://new.land.naver.com/offices?ms=37.4990461,127.0309029,15&a=SMS&e=RETAIL"
    url_params = analyze_url(url)
    
    # API 구조 분석
    cluster_data = analyze_api_structure()
    
    # 매물 목록 API 분석
    analyze_article_list_api()
    
    # 수집 전략 제안
    propose_collection_strategy()