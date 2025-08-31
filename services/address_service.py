#!/usr/bin/env python3
"""
주소 변환 서비스 (카카오 API 기반)
"""

import requests
import json
import time
from typing import Dict, Optional
from config.settings import settings

class AddressService:
    def __init__(self):
        if not settings.kakao_api_key:
            raise ValueError("카카오 API 키가 필요합니다. KAKAO_REST_API_KEY 환경변수를 설정하세요.")
        
        self.api_key = settings.kakao_api_key
        self.base_url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        self.headers = {
            'Authorization': f'KakaoAK {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        self.address_cache = {}
        self.request_count = 0
        self.daily_limit = 100000
    
    def convert_coordinates_to_address(self, latitude: str, longitude: str) -> Optional[Dict]:
        cache_key = f"{latitude},{longitude}"
        if cache_key in self.address_cache:
            return self.address_cache[cache_key]
        
        if self.request_count >= self.daily_limit:
            print(f"⚠️ 일일 API 호출 제한 도달: {self.daily_limit}")
            return None
        
        try:
            params = {
                'x': longitude,
                'y': latitude,
                'input_coord': 'WGS84'
            }
            
            response = requests.get(self.base_url, headers=self.headers, params=params)
            self.request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('documents'):
                    address_info = self._parse_address_response(data['documents'][0])
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
                return self.convert_coordinates_to_address(latitude, longitude)
            
            else:
                print(f"❌ API 호출 오류: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 주소 변환 중 오류: {e}")
            return None
    
    def _parse_address_response(self, document: Dict) -> Dict:
        road_address = document.get('road_address')
        address = document.get('address')
        
        result = {
            "success": True,
            "provider": "kakao"
        }
        
        if road_address:
            result.update({
                "road_address": road_address.get('address_name', ''),
                "road_name": road_address.get('road_name', ''),
                "building_number": road_address.get('main_building_no', ''),
                "building_name": road_address.get('building_name', ''),
                "zone_no": road_address.get('zone_no', '')
            })
        
        if address:
            jibun = f"{address.get('main_address_no', '')}-{address.get('sub_address_no', '')}" if address.get('sub_address_no') else address.get('main_address_no', '')
            
            result.update({
                "jibun_address": address.get('address_name', ''),
                "region_1depth": address.get('region_1depth_name', ''),
                "region_2depth": address.get('region_2depth_name', ''), 
                "region_3depth": address.get('region_3depth_name', ''),
                "jibun_number": jibun
            })
        
        if road_address and road_address.get('address_name'):
            result["primary_address"] = road_address.get('address_name')
        elif address and address.get('address_name'):
            result["primary_address"] = address.get('address_name')
        else:
            result["primary_address"] = "주소 정보 없음"
        
        return result
    
    def get_usage_stats(self) -> Dict:
        return {
            "total_requests": self.request_count,
            "cache_hits": len(self.address_cache),
            "remaining_daily_limit": self.daily_limit - self.request_count,
            "usage_percentage": f"{(self.request_count / self.daily_limit * 100):.2f}%"
        }
    
    def save_cache(self, filename: str = "address_cache.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.address_cache, f, ensure_ascii=False, indent=2)
        print(f"💾 주소 캐시 저장: {filename}")
    
    def load_cache(self, filename: str = "address_cache.json"):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.address_cache = json.load(f)
            print(f"📂 주소 캐시 로드: {len(self.address_cache)}개 항목")
        except FileNotFoundError:
            print("📂 캐시 파일이 없어 새로 시작합니다.")
        except Exception as e:
            print(f"❌ 캐시 로드 오류: {e}")