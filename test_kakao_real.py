#!/usr/bin/env python3
"""
실제 카카오 API 키로 주소 변환 테스트
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

def test_real_kakao_api():
    """실제 카카오 API 키로 테스트"""
    
    print("🗺️ 실제 카카오 API 테스트")
    print("="*40)
    
    # .env 파일 로드
    load_dotenv()
    api_key = os.getenv('KAKAO_REST_API_KEY')
    
    if not api_key:
        print("❌ KAKAO_REST_API_KEY 환경변수를 찾을 수 없습니다")
        return False
    
    print(f"✅ API 키 로드: {api_key[:10]}...")
    
    # API 호출 설정
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {
        'Authorization': f'KakaoAK {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 테스트 좌표들 (강남역, 광화문, 삼성역)
    test_locations = [
        ("37.498095", "127.027610", "강남역"),
        ("37.566535", "126.977969", "광화문"),
        ("37.517235", "127.047325", "삼성역")
    ]
    
    success_count = 0
    
    for lat, lon, location_name in test_locations:
        print(f"\n📍 {location_name} 테스트 ({lat}, {lon})")
        
        params = {
            'x': lon,  # 경도
            'y': lat,  # 위도
            'input_coord': 'WGS84'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"   HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('documents'):
                    doc = data['documents'][0]
                    
                    # 도로명 주소
                    road_address = doc.get('road_address')
                    if road_address:
                        print(f"   🛣️ 도로명: {road_address['address_name']}")
                        print(f"   🏢 건물명: {road_address.get('building_name', '없음')}")
                        print(f"   📮 우편번호: {road_address.get('zone_no', '없음')}")
                    
                    # 지번 주소
                    jibun_address = doc.get('address')
                    if jibun_address:
                        print(f"   🏠 지번: {jibun_address['address_name']}")
                    
                    success_count += 1
                    print("   ✅ 변환 성공!")
                else:
                    print("   ⚠️ 변환 결과 없음")
            
            elif response.status_code == 401:
                print("   ❌ 인증 실패 - API 키 확인 필요")
                print(f"   응답: {response.text}")
            
            elif response.status_code == 429:
                print("   ⚠️ API 호출 제한 초과")
            
            else:
                print(f"   ❌ API 오류: {response.status_code}")
                print(f"   응답: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 요청 실패: {e}")
    
    print(f"\n📊 결과: {success_count}/{len(test_locations)} 성공")
    
    if success_count > 0:
        print("✅ 카카오 API 정상 작동!")
        return True
    else:
        print("❌ 카카오 API 문제 있음")
        return False

def test_converter_class():
    """카카오 변환기 클래스 테스트"""
    print(f"\n🔧 카카오 변환기 클래스 테스트")
    print("-"*30)
    
    try:
        # 경로 설정
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir / 'collectors' / 'core'))
        
        from kakao_address_converter import KakaoAddressConverter
        
        converter = KakaoAddressConverter()
        print("✅ 변환기 초기화 성공")
        
        # 강남역 좌표로 테스트
        result = converter.convert_coord_to_address("37.498095", "127.027610")
        
        if result:
            print("✅ 클래스 변환 성공!")
            print(f"   도로명: {result.get('road_address', '없음')}")
            print(f"   지번: {result.get('jibun_address', '없음')}")
            print(f"   건물명: {result.get('building_name', '없음')}")
            print(f"   우편번호: {result.get('zone_no', '없음')}")
            return True
        else:
            print("❌ 클래스 변환 실패")
            return False
            
    except Exception as e:
        print(f"❌ 변환기 클래스 오류: {e}")
        return False

if __name__ == "__main__":
    print("🧪 카카오 API 실제 키 테스트")
    
    # 1. 직접 API 호출 테스트
    api_success = test_real_kakao_api()
    
    # 2. 변환기 클래스 테스트  
    class_success = test_converter_class()
    
    if api_success and class_success:
        print("\n🎉 모든 테스트 성공! 카카오 API 준비 완료!")
    else:
        print("\n💥 일부 테스트 실패. 설정 확인 필요.")