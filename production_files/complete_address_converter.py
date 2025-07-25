import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime


class CompleteAddressConverter:
    """카카오 API를 이용한 완전한 좌표-주소 변환기 (지번, 건물명 포함)"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"KakaoAK {api_key}"}
        self.region_url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
        self.address_url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        self.request_count = 0
        self.cache = {}
        
    def convert_coordinate_complete(self, longitude, latitude):
        """완전한 좌표→주소 변환 (지번, 건물명 포함)"""
        coord_key = f"{longitude},{latitude}"
        if coord_key in self.cache:
            return self.cache[coord_key]
            
        result = {
            # 기본 정보
            'longitude': longitude,
            'latitude': latitude,
            
            # 행정구역 정보
            'sido': '',
            'sigungu': '',
            'eupmyeondong': '',
            'ri': '',
            'legal_dong_code': '',
            'admin_dong_code': '',
            
            # 지번 주소
            'jibun_address': '',
            'jibun_main': '',
            'jibun_sub': '',
            'jibun_full': '',
            'is_mountain': False,
            'zip_code': '',
            
            # 도로명 주소
            'road_address': '',
            'building_name': '',
            'road_zip_code': '',
            'is_underground': False,
            
            # 통합 정보
            'full_address': '',
            'address_type': ''  # 'road' or 'jibun'
        }
        
        try:
            # 1. 행정구역 정보 조회
            region_params = {"x": longitude, "y": latitude}
            region_response = requests.get(self.region_url, params=region_params, headers=self.headers)
            self.request_count += 1
            
            if region_response.status_code == 200:
                region_data = region_response.json()
                for doc in region_data.get('documents', []):
                    if doc.get('region_type') == 'H':  # 법정동
                        result['sido'] = doc.get('region_1depth_name', '')
                        result['sigungu'] = doc.get('region_2depth_name', '')
                        result['eupmyeondong'] = doc.get('region_3depth_name', '')
                        result['ri'] = doc.get('region_4depth_name', '')
                        result['legal_dong_code'] = doc.get('code', '')
                    elif doc.get('region_type') == 'B':  # 행정동
                        result['admin_dong_code'] = doc.get('code', '')
            
            # 2. 상세 주소 정보 조회
            address_params = {"x": longitude, "y": latitude, "input_coord": "WGS84"}
            address_response = requests.get(self.address_url, params=address_params, headers=self.headers) 
            self.request_count += 1
            
            if address_response.status_code == 200:
                address_data = address_response.json()
                documents = address_data.get('documents', [])
                
                if documents:
                    doc = documents[0]
                    
                    # 도로명 주소 (우선)
                    if doc.get('road_address'):
                        road = doc['road_address']
                        result['road_address'] = road.get('address_name', '')
                        result['building_name'] = road.get('building_name', '')
                        result['road_zip_code'] = road.get('zone_no', '')
                        result['is_underground'] = road.get('underground') == 'Y'
                        result['full_address'] = result['road_address']
                        result['address_type'] = 'road'
                    
                    # 지번 주소
                    if doc.get('address'):
                        addr = doc['address']
                        result['jibun_address'] = addr.get('address_name', '')
                        result['jibun_main'] = addr.get('main_address_no', '')
                        result['jibun_sub'] = addr.get('sub_address_no', '')
                        result['is_mountain'] = addr.get('mountain_yn') == 'Y'
                        result['zip_code'] = addr.get('zip_code', '')
                        
                        # 지번 전체 표기
                        if result['jibun_main']:
                            if result['jibun_sub']:
                                result['jibun_full'] = f"{result['jibun_main']}-{result['jibun_sub']}"
                            else:
                                result['jibun_full'] = result['jibun_main']
                        
                        # 도로명이 없으면 지번 사용
                        if not result['full_address']:
                            result['full_address'] = result['jibun_address']
                            result['address_type'] = 'jibun'
            
            # API 제한 처리
            if region_response.status_code == 429 or address_response.status_code == 429:
                time.sleep(1)
                return self.convert_coordinate_complete(longitude, latitude)
                
        except Exception as e:
            print(f"좌표 변환 오류 ({longitude}, {latitude}): {e}")
        
        # 캐시 저장
        self.cache[coord_key] = result
        return result
    
    def enhance_articles_with_complete_address(self, articles, max_workers=3):
        """매물 데이터에 완전한 주소 정보 추가"""
        print(f"완전한 주소 정보 추가: {len(articles)}개 매물")
        
        # 유효한 좌표 추출
        valid_articles = []
        for i, article in enumerate(articles):
            lng = article.get('longitude')
            lat = article.get('latitude')
            
            if lng and lat:
                try:
                    float(lng)
                    float(lat)
                    valid_articles.append((i, article, float(lng), float(lat)))
                except:
                    continue
        
        print(f"유효한 좌표: {len(valid_articles)}개")
        
        if not valid_articles:
            return articles
        
        # 병렬 처리
        enhanced_articles = articles.copy()
        processed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_article = {}
            for i, article, lng, lat in valid_articles:
                future = executor.submit(self.convert_coordinate_complete, lng, lat)
                future_to_article[future] = (i, article)
                
                # API 제한을 위한 딜레이
                if len(future_to_article) % 10 == 0:
                    time.sleep(0.2)
            
            # 결과 수집
            for future in as_completed(future_to_article):
                i, article = future_to_article[future]
                try:
                    address_info = future.result()
                    
                    # 원본 매물에 주소 정보 추가
                    enhanced_articles[i].update({
                        # 행정구역
                        'address_sido': address_info['sido'],
                        'address_sigungu': address_info['sigungu'],
                        'address_dong': address_info['eupmyeondong'],
                        'address_ri': address_info['ri'],
                        'legal_dong_code': address_info['legal_dong_code'],
                        
                        # 지번 주소
                        'jibun_address': address_info['jibun_address'],
                        'jibun_number': address_info['jibun_full'],
                        'jibun_main': address_info['jibun_main'],
                        'jibun_sub': address_info['jibun_sub'],
                        'is_mountain': address_info['is_mountain'],
                        
                        # 도로명 주소
                        'road_address': address_info['road_address'],
                        'building_name': address_info['building_name'],
                        'is_underground': address_info['is_underground'],
                        
                        # 통합 정보
                        'complete_address': address_info['full_address'],
                        'address_type': address_info['address_type'],
                        'zip_code': address_info['road_zip_code'] or address_info['zip_code']
                    })
                    
                    processed += 1
                    if processed % 20 == 0:
                        print(f"  진행률: {processed}/{len(valid_articles)} ({processed/len(valid_articles)*100:.1f}%)")
                        
                except Exception as e:
                    print(f"  매물 {i} 처리 실패: {e}")
        
        print(f"완료: {processed}개 처리, API 호출 {self.request_count}회")
        return enhanced_articles


def process_all_collected_data():
    """수집된 모든 데이터에 완전한 주소 정보 추가"""
    print("=== 전체 데이터 완전 주소 변환 ===")
    
    # 데이터 로드
    json_file = "quick_test_20250724_183854.json"
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"데이터 로드: {len(articles)}개 매물")
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {json_file}")
        return
    
    # 변환기 초기화
    api_key = "640ac7eb1709ff36aa818f09e8dfbe7d"
    converter = CompleteAddressConverter(api_key)
    
    # 테스트용으로 처음 100개만 (전체 하려면 articles 전체 사용)
    test_articles = articles[:100]
    print(f"테스트 처리: {len(test_articles)}개 매물")
    
    # 완전한 주소 정보 추가
    enhanced_articles = converter.enhance_articles_with_complete_address(test_articles)
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON 저장
    output_json = f"complete_address_{timestamp}.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(enhanced_articles, f, ensure_ascii=False, indent=2)
    
    # CSV 저장 (상세 정보 포함)
    df_data = []
    for article in enhanced_articles:
        df_data.append({
            '매물번호': article.get('articleNo'),
            '매물명': article.get('articleName'),
            '거래타입': article.get('tradeTypeName'),
            '보증금/매매가': article.get('dealOrWarrantPrc'),
            '월세': article.get('rentPrc'),
            '전용면적': article.get('area1'),
            '건물명_원본': article.get('buildingName'),
            '기존주소': article.get('roadAddress'),
            
            # 좌표
            '위도': article.get('latitude'),
            '경도': article.get('longitude'),
            
            # 행정구역
            '시도': article.get('address_sido'),
            '시군구': article.get('address_sigungu'),
            '읍면동': article.get('address_dong'),
            '법정동코드': article.get('legal_dong_code'),
            
            # 지번 주소  
            '지번주소': article.get('jibun_address'),
            '지번': article.get('jibun_number'),
            '본번': article.get('jibun_main'),
            '부번': article.get('jibun_sub'),
            '산여부': 'Y' if article.get('is_mountain') else 'N',
            
            # 도로명 주소
            '도로명주소': article.get('road_address'),
            '건물명_카카오': article.get('building_name'),
            '지하여부': 'Y' if article.get('is_underground') else 'N',
            
            # 통합 정보
            '완전주소': article.get('complete_address'),
            '주소타입': article.get('address_type'),
            '우편번호': article.get('zip_code'),
            
            '중개사': article.get('realtorName')
        })
    
    df = pd.DataFrame(df_data)
    output_csv = f"complete_address_{timestamp}.csv"
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print(f"\n=== 저장 완료 ===")
    print(f"JSON: {output_json}")
    print(f"CSV: {output_csv}")
    
    # 주소 타입 통계
    address_type_stats = df['주소타입'].value_counts()
    print(f"\n주소 타입별 통계:")
    for addr_type, count in address_type_stats.items():
        print(f"  {addr_type}: {count}개")
    
    # 건물명 비교 (원본 vs 카카오)
    building_comparison = df[['건물명_원본', '건물명_카카오']].head(10)
    print(f"\n건물명 비교 (상위 10개):")
    for i, row in building_comparison.iterrows():
        original = row['건물명_원본'] or '없음'
        kakao = row['건물명_카카오'] or '없음'
        print(f"  원본: {original} → 카카오: {kakao}")


if __name__ == "__main__":
    process_all_collected_data()