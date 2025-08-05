#!/usr/bin/env python3
"""
카카오 로컬 API를 이용한 좌표 → 주소 변환기
"""

import requests
import json
import time
from typing import Dict, Optional, Tuple
import os

class KakaoAddressConverter:
    def __init__(self, api_key: str = None):
        """
        카카오 API 키 설정
        api_key: 카카오 REST API 키
        """
        self.api_key = api_key or self._load_api_key_from_config() or os.getenv('KAKAO_REST_API_KEY')
        if not self.api_key:
            raise ValueError("카카오 API 키가 필요합니다. config.json 파일 또는 환경변수 KAKAO_REST_API_KEY 설정하세요.")
        
        self.base_url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        self.headers = {
            'Authorization': f'KakaoAK {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 변환 결과 캐싱 (중복 호출 방지)
        self.address_cache = {}
        self.request_count = 0
        self.daily_limit = 100000  # 일일 제한 (여유있게 설정)
    
    def _load_api_key_from_config(self) -> Optional[str]:
        """설정 파일에서 API 키 로드"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config.get('kakao_api', {}).get('rest_api_key')
        except Exception:
            pass
        return None
    
    def convert_coord_to_address(self, latitude: str, longitude: str) -> Optional[Dict]:
        """
        좌표를 주소로 변환
        
        Args:
            latitude: 위도 (문자열)
            longitude: 경도 (문자열)
            
        Returns:
            주소 정보 딕셔너리 또는 None
        """
        # 캐시 확인
        cache_key = f"{latitude},{longitude}"
        if cache_key in self.address_cache:
            return self.address_cache[cache_key]
        
        # API 호출 제한 확인
        if self.request_count >= self.daily_limit:
            print(f"⚠️ 일일 API 호출 제한 도달: {self.daily_limit}")
            return None
        
        try:
            # API 호출
            params = {
                'x': longitude,  # 경도
                'y': latitude,   # 위도
                'input_coord': 'WGS84'
            }
            
            response = requests.get(self.base_url, headers=self.headers, params=params)
            self.request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('documents'):
                    address_info = self._parse_address_response(data['documents'][0])
                    
                    # 캐시에 저장
                    self.address_cache[cache_key] = address_info
                    
                    return address_info
                else:
                    print(f"⚠️ 주소 변환 실패: 좌표 ({latitude}, {longitude})")
                    return None
            
            elif response.status_code == 401:
                print("❌ 카카오 API 인증 실패. API 키를 확인하세요.")
                return None
            
            elif response.status_code == 429:
                print("⚠️ API 호출 한도 초과. 잠시 대기 후 재시도...")
                time.sleep(1)
                return self.convert_coord_to_address(latitude, longitude)
            
            else:
                print(f"❌ API 호출 오류: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 주소 변환 중 오류: {e}")
            return None
    
    def _parse_address_response(self, document: Dict) -> Dict:
        """카카오 API 응답을 파싱하여 주소 정보 추출"""
        
        road_address = document.get('road_address')  # 도로명주소
        address = document.get('address')            # 지번주소
        
        result = {
            "주소변환_성공": True,
            "API_제공자": "카카오맵"
        }
        
        # 도로명주소 정보
        if road_address:
            result.update({
                "도로명주소": road_address.get('address_name', ''),
                "도로명": road_address.get('road_name', ''),
                "건물번호": road_address.get('main_building_no', ''),
                "건물명": road_address.get('building_name', ''),
                "우편번호": road_address.get('zone_no', '')
            })
        
        # 지번주소 정보 
        if address:
            result.update({
                "지번주소": address.get('address_name', ''),
                "시도": address.get('region_1depth_name', ''),
                "시군구": address.get('region_2depth_name', ''), 
                "읍면동": address.get('region_3depth_name', ''),
                "지번": f"{address.get('main_address_no', '')}-{address.get('sub_address_no', '')}" if address.get('sub_address_no') else address.get('main_address_no', '')
            })
        
        # 대표 주소 결정 (도로명주소 우선)
        if road_address and road_address.get('address_name'):
            result["대표주소"] = road_address.get('address_name')
        elif address and address.get('address_name'):
            result["대표주소"] = address.get('address_name')
        else:
            result["대표주소"] = "주소 정보 없음"
        
        return result
    
    def get_usage_stats(self) -> Dict:
        """API 사용 통계"""
        return {
            "총_요청_수": self.request_count,
            "캐시_히트_수": len(self.address_cache),
            "남은_일일_한도": self.daily_limit - self.request_count,
            "사용률": f"{(self.request_count / self.daily_limit * 100):.2f}%"
        }
    
    def save_cache(self, filename: str = "address_cache.json"):
        """주소 캐시를 파일로 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.address_cache, f, ensure_ascii=False, indent=2)
        print(f"💾 주소 캐시 저장: {filename}")
    
    def load_cache(self, filename: str = "address_cache.json"):
        """주소 캐시를 파일에서 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.address_cache = json.load(f)
            print(f"📂 주소 캐시 로드: {len(self.address_cache)}개 항목")
        except FileNotFoundError:
            print("📂 캐시 파일이 없어 새로 시작합니다.")
        except Exception as e:
            print(f"❌ 캐시 로드 오류: {e}")

def test_kakao_converter():
    """카카오 주소 변환기 테스트"""
    print("🧪 카카오 주소 변환기 테스트")
    
    # API 키 입력 받기
    api_key = input("카카오 REST API 키를 입력하세요: ").strip()
    
    if not api_key:
        print("❌ API 키가 입력되지 않았습니다.")
        return
    
    try:
        converter = KakaoAddressConverter(api_key)
        
        # 테스트 좌표 (강남역 근처)
        test_coords = [
            ("37.5086823", "127.0568395"),  # 실제 데이터에서 가져온 좌표
            ("37.498095", "127.027610"),    # 강남역 근처
            ("37.517408", "127.047313")     # 강남구 중심
        ]
        
        for lat, lon in test_coords:
            print(f"\n🗺️ 좌표 변환 테스트: ({lat}, {lon})")
            
            result = converter.convert_coord_to_address(lat, lon)
            
            if result:
                print(f"✅ 성공!")
                print(f"   대표주소: {result.get('대표주소')}")
                print(f"   도로명주소: {result.get('도로명주소', 'N/A')}")
                print(f"   건물명: {result.get('건물명', 'N/A')}")
                print(f"   지번주소: {result.get('지번주소', 'N/A')}")
            else:
                print(f"❌ 변환 실패")
            
            time.sleep(0.1)  # API 호출 간격
        
        # 사용 통계
        stats = converter.get_usage_stats()
        print(f"\n📊 API 사용 통계:")
        print(f"   총 요청: {stats['총_요청_수']}회")
        print(f"   캐시 저장: {stats['캐시_히트_수']}개")
        print(f"   남은 한도: {stats['남은_일일_한도']}회")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    test_kakao_converter()