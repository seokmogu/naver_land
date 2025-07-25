import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime


class CoordinateToAddressConverter:
    """카카오 API를 이용한 좌표-주소 변환기"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
        self.headers = {
            "Authorization": f"KakaoAK {api_key}"
        }
        self.request_count = 0
        self.cache = {}  # 좌표 캐시
        
    def convert_coordinate(self, longitude, latitude):
        """단일 좌표를 주소로 변환"""
        # 캐시 확인
        coord_key = f"{longitude},{latitude}"
        if coord_key in self.cache:
            return self.cache[coord_key]
            
        params = {
            "x": longitude,
            "y": latitude
        }
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers)
            self.request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                
                if documents:
                    # 법정동 정보 (H 타입)
                    legal_dong = None
                    # 행정동 정보 (B 타입)
                    admin_dong = None
                    
                    for doc in documents:
                        if doc.get('region_type') == 'H':  # 법정동
                            legal_dong = doc
                        elif doc.get('region_type') == 'B':  # 행정동
                            admin_dong = doc
                    
                    # 우선순위: 법정동 > 행정동
                    target_doc = legal_dong if legal_dong else admin_dong
                    
                    if target_doc:
                        address_info = {
                            'region_1depth_name': target_doc.get('region_1depth_name', ''),  # 시도
                            'region_2depth_name': target_doc.get('region_2depth_name', ''),  # 시군구
                            'region_3depth_name': target_doc.get('region_3depth_name', ''),  # 읍면동
                            'region_4depth_name': target_doc.get('region_4depth_name', ''),  # 리
                            'full_address': f"{target_doc.get('region_1depth_name', '')} {target_doc.get('region_2depth_name', '')} {target_doc.get('region_3depth_name', '')}".strip(),
                            'region_type': target_doc.get('region_type', ''),
                            'code': target_doc.get('code', '')
                        }
                        
                        # 캐시에 저장
                        self.cache[coord_key] = address_info
                        return address_info
                        
            elif response.status_code == 429:  # 너무 많은 요청
                print(f"  API 제한 초과, 잠시 대기...")
                time.sleep(1)
                return self.convert_coordinate(longitude, latitude)  # 재시도
            else:
                print(f"  API 오류: {response.status_code}")
                
        except Exception as e:
            print(f"  좌표 변환 오류: {e}")
            
        # 실패 시 기본값
        return {
            'region_1depth_name': '',
            'region_2depth_name': '',
            'region_3depth_name': '',
            'region_4depth_name': '',
            'full_address': '주소 불명',
            'region_type': '',
            'code': ''
        }
        
    def convert_batch(self, coordinates, max_workers=5, delay=0.1):
        """배치로 좌표들을 주소로 변환"""
        print(f"배치 변환 시작: {len(coordinates)}개 좌표")
        
        results = []
        processed = 0
        
        # 병렬 처리 (API 제한을 고려하여 적은 수의 워커)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_coord = {}
            for i, (lng, lat) in enumerate(coordinates):
                future = executor.submit(self.convert_coordinate, lng, lat)
                future_to_coord[future] = (i, lng, lat)
                
                # API 제한을 피하기 위한 딜레이
                if i % 10 == 0 and i > 0:
                    time.sleep(delay)
            
            # 결과 수집
            for future in as_completed(future_to_coord):
                i, lng, lat = future_to_coord[future]
                try:
                    address_info = future.result()
                    results.append((i, lng, lat, address_info))
                    processed += 1
                    
                    if processed % 50 == 0:
                        print(f"  진행률: {processed}/{len(coordinates)} ({processed/len(coordinates)*100:.1f}%)")
                        
                except Exception as e:
                    print(f"  좌표 ({lng}, {lat}) 처리 실패: {e}")
                    # 실패 시 빈 정보
                    results.append((i, lng, lat, {
                        'region_1depth_name': '', 'region_2depth_name': '',
                        'region_3depth_name': '', 'region_4depth_name': '',
                        'full_address': '변환 실패', 'region_type': '', 'code': ''
                    }))
        
        # 원래 순서대로 정렬
        results.sort(key=lambda x: x[0])
        
        print(f"배치 변환 완료: {len(results)}개 처리, API 호출 {self.request_count}회")
        return [result[3] for result in results]  # 주소 정보만 반환
        
    def add_address_to_articles(self, articles):
        """매물 데이터에 주소 정보 추가"""
        print(f"매물 데이터에 주소 정보 추가: {len(articles)}개")
        
        # 좌표 추출
        coordinates = []
        valid_indices = []
        
        for i, article in enumerate(articles):
            lng = article.get('longitude')
            lat = article.get('latitude')
            
            if lng and lat:
                try:
                    coordinates.append((float(lng), float(lat)))
                    valid_indices.append(i)
                except:
                    continue
        
        print(f"  유효한 좌표: {len(coordinates)}개")
        
        if not coordinates:
            print("  변환할 좌표가 없습니다.")
            return articles
        
        # 배치 변환
        address_results = self.convert_batch(coordinates)
        
        # 결과를 원본 데이터에 추가
        for idx, address_info in zip(valid_indices, address_results):
            articles[idx].update({
                'address_sido': address_info['region_1depth_name'],
                'address_sigungu': address_info['region_2depth_name'],
                'address_dong': address_info['region_3depth_name'],
                'address_ri': address_info['region_4depth_name'],
                'address_full': address_info['full_address'],
                'address_code': address_info['code']
            })
        
        return articles


def test_coordinate_conversion():
    """좌표 변환 테스트"""
    print("=== 좌표 변환 테스트 ===")
    
    api_key = "640ac7eb1709ff36aa818f09e8dfbe7d"
    converter = CoordinateToAddressConverter(api_key)
    
    # 테스트 좌표 (역삼동)
    test_coordinates = [
        (127.0309029, 37.4990461),  # 역삼동
        (127.1086228, 37.4012191),  # 예시 좌표
        (127.027584, 37.497175)     # 강남역 근처
    ]
    
    print("\n단일 좌표 변환 테스트:")
    for lng, lat in test_coordinates:
        print(f"\n좌표: ({lng}, {lat})")
        address = converter.convert_coordinate(lng, lat)
        print(f"  주소: {address['full_address']}")
        print(f"  상세: {address['region_1depth_name']} {address['region_2depth_name']} {address['region_3depth_name']}")


def process_collected_data():
    """수집된 데이터 처리"""
    print("=== 수집된 데이터 처리 ===")
    
    # 수집된 JSON 파일 로드
    json_file = "quick_test_20250724_183854.json"
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"데이터 로드 완료: {len(articles)}개 매물")
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {json_file}")
        return
    
    # 좌표 변환기 초기화
    api_key = "640ac7eb1709ff36aa818f09e8dfbe7d"
    converter = CoordinateToAddressConverter(api_key)
    
    # 주소 정보 추가 (처음 50개만 테스트)
    test_articles = articles[:50]  # 테스트용
    print(f"\n테스트 처리: {len(test_articles)}개 매물")
    
    enhanced_articles = converter.add_address_to_articles(test_articles)
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON 저장
    output_json = f"enhanced_articles_{timestamp}.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(enhanced_articles, f, ensure_ascii=False, indent=2)
    
    # CSV 저장
    df_data = []
    for article in enhanced_articles:
        df_data.append({
            '매물번호': article.get('articleNo'),
            '매물명': article.get('articleName'),
            '거래타입': article.get('tradeTypeName'),
            '보증금/매매가': article.get('dealOrWarrantPrc'),
            '월세': article.get('rentPrc'),
            '전용면적': article.get('area1'),
            '건물명': article.get('buildingName'),
            '기존주소': article.get('roadAddress'),
            '위도': article.get('latitude'),
            '경도': article.get('longitude'),
            '시도': article.get('address_sido'),
            '시군구': article.get('address_sigungu'),
            '읍면동': article.get('address_dong'),
            '상세주소': article.get('address_full'),
            '주소코드': article.get('address_code'),
            '중개사': article.get('realtorName')
        })
    
    df = pd.DataFrame(df_data)
    output_csv = f"enhanced_articles_{timestamp}.csv"
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print(f"\n=== 결과 저장 ===")
    print(f"JSON: {output_json}")
    print(f"CSV: {output_csv}")
    
    # 주소 통계
    print(f"\n=== 주소 통계 ===")
    address_stats = df['시군구'].value_counts()
    print("시군구별 매물 수:")
    for sigungu, count in address_stats.head(10).items():
        print(f"  {sigungu}: {count}개")


if __name__ == "__main__":
    # 테스트 실행
    test_coordinate_conversion()
    
    print("\n" + "="*50)
    
    # 실제 데이터 처리
    process_collected_data()