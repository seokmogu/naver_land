import requests
import json


def test_kakao_address_apis():
    """카카오 API로 상세 주소 정보 테스트"""
    
    api_key = "640ac7eb1709ff36aa818f09e8dfbe7d"
    headers = {
        "Authorization": f"KakaoAK {api_key}"
    }
    
    # 테스트 좌표 (역삼동의 실제 건물)
    test_coords = [
        (127.0309029, 37.4990461, "역삼동"),
        (127.1086228, 37.4012191, "성남 삼평동"),
        (127.027584, 37.497175, "강남역 근처")
    ]
    
    print("=== 카카오 API 상세 주소 테스트 ===\n")
    
    for lng, lat, desc in test_coords:
        print(f"📍 {desc} 좌표: ({lng}, {lat})")
        print("-" * 50)
        
        # 1. 좌표 → 행정구역 정보
        print("1️⃣ 행정구역 정보:")
        coord2region_url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
        params = {"x": lng, "y": lat}
        
        try:
            response = requests.get(coord2region_url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for doc in data.get('documents', []):
                    region_type = "법정동" if doc.get('region_type') == 'H' else "행정동"
                    print(f"  [{region_type}] {doc.get('region_1depth_name')} {doc.get('region_2depth_name')} {doc.get('region_3depth_name')} {doc.get('region_4depth_name', '')}")
                    print(f"    코드: {doc.get('code')}")
            else:
                print(f"  오류: {response.status_code}")
        except Exception as e:
            print(f"  예외: {e}")
        
        # 2. 좌표 → 주소 (지번 포함)
        print("\n2️⃣ 상세 주소 정보:")
        coord2address_url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        params = {"x": lng, "y": lat, "input_coord": "WGS84"}
        
        try:
            response = requests.get(coord2address_url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                
                if documents:
                    doc = documents[0]  # 첫 번째 결과
                    
                    # 도로명 주소
                    if 'road_address' in doc and doc['road_address']:
                        road = doc['road_address']
                        print(f"  🛣️ 도로명: {road.get('address_name', '')}")
                        print(f"    건물명: {road.get('building_name', '없음')}")
                        print(f"    우편번호: {road.get('zone_no', '')}")
                        print(f"    지하: {'Y' if road.get('underground') == 'Y' else 'N'}")
                    
                    # 지번 주소 
                    if 'address' in doc and doc['address']:
                        addr = doc['address']
                        print(f"  🏠 지번: {addr.get('address_name', '')}")
                        print(f"    지역: {addr.get('region_1depth_name')} {addr.get('region_2depth_name')} {addr.get('region_3depth_name')}")
                        print(f"    상세: {addr.get('main_address_no', '')}-{addr.get('sub_address_no', '') if addr.get('sub_address_no') else '0'}")
                        print(f"    산: {'Y' if addr.get('mountain_yn') == 'Y' else 'N'}")
                        print(f"    우편번호: {addr.get('zip_code', '')}")
                else:
                    print("  주소 정보 없음")
            else:
                print(f"  오류: {response.status_code}")
        except Exception as e:
            print(f"  예외: {e}")
        
        print("\n" + "="*60 + "\n")


def test_with_real_building():
    """실제 건물 좌표로 테스트"""
    
    api_key = "640ac7eb1709ff36aa818f09e8dfbe7d"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    
    # 수집된 데이터에서 실제 좌표 가져오기
    try:
        with open('quick_test_20250724_183854.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
            
        print("=== 실제 매물 좌표 테스트 ===\n")
        
        # 처음 3개 매물 테스트
        for i, article in enumerate(articles[:3]):
            lng = article.get('longitude')
            lat = article.get('latitude')
            name = article.get('articleName', '매물명 없음')
            existing_addr = article.get('roadAddress', '기존주소 없음')
            
            if not lng or not lat:
                continue
                
            print(f"📋 매물 {i+1}: {name}")
            print(f"   기존 주소: {existing_addr}")
            print(f"   좌표: ({lng}, {lat})")
            print("-" * 50)
            
            # 상세 주소 API 호출
            coord2address_url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
            params = {"x": lng, "y": lat}
            
            try:
                response = requests.get(coord2address_url, params=params, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    documents = data.get('documents', [])
                    
                    if documents:
                        doc = documents[0]
                        
                        # 도로명 주소
                        if doc.get('road_address'):
                            road = doc['road_address']
                            print(f"🛣️ 도로명: {road.get('address_name', '')}")
                            if road.get('building_name'):
                                print(f"   건물명: {road.get('building_name')}")
                        
                        # 지번 주소
                        if doc.get('address'):
                            addr = doc['address']
                            main_no = addr.get('main_address_no', '')
                            sub_no = addr.get('sub_address_no', '')
                            jibun = f"{main_no}-{sub_no}" if sub_no else main_no
                            
                            print(f"🏠 지번: {addr.get('address_name', '')}")
                            print(f"   상세지번: {jibun}")
                            print(f"   법정동: {addr.get('region_3depth_name', '')}")
                            
                        print()
                else:
                    print(f"API 오류: {response.status_code}")
                    
            except Exception as e:
                print(f"예외 발생: {e}")
                
            print("="*60)
            
    except FileNotFoundError:
        print("수집된 데이터 파일을 찾을 수 없습니다.")


if __name__ == "__main__":
    # 일반 좌표 테스트
    test_kakao_address_apis()
    
    # 실제 매물 좌표 테스트  
    test_with_real_building()