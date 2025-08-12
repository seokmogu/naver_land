#!/usr/bin/env python3
"""
스마트 경계 기반 수집기
네이버의 줌 레벨별 경계 데이터를 활용한 완전한 지역 수집
"""

import json
import requests
import time
import os
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from playwright_token_collector import PlaywrightTokenCollector

class SmartBoundaryCollector:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'authorization': f'Bearer {self.token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://new.land.naver.com/',
        }
        
        # 캐시 디렉토리
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def collect_gu_complete_areas(self, gu_name: str, gu_config: Dict) -> Dict:
        """구의 모든 동을 완전 수집 (경계 기반)"""
        print(f"🗺️ {gu_name} 스마트 경계 기반 완전 수집 시작...")
        
        # 캐시 확인
        cache_file = os.path.join(self.cache_dir, f"smart_areas_{gu_name}.json")
        if os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < 86400 * 3:  # 3일 이내 (행정구역은 자주 안 바뀜)
                print(f"💾 캐시된 데이터 사용 (생성된지 {cache_age/3600:.1f}시간)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        center_lat, center_lon, _ = gu_config['center_coordinate']
        gu_code = gu_config['gu_code']
        
        # 1단계: 구 경계 획득 (줌 14)
        print("📐 1단계: 구 전체 경계 데이터 획득...")
        gu_boundary = self._get_gu_boundary(center_lat, center_lon, gu_code)
        
        if not gu_boundary:
            print("❌ 구 경계 데이터 획득 실패")
            return {}
        
        print(f"✅ 구 경계 확보: {gu_boundary['cortarName']} ({len(gu_boundary.get('boundary_points', []))}개 경계점)")
        
        # 2단계: 구 경계 내부의 격자점들에서 동 수집 (줌 15-16)
        print("🎯 2단계: 구 경계 내부에서 모든 동 탐지...")
        discovered_dongs = self._discover_dongs_within_boundary(gu_boundary, gu_name)
        
        # 3단계: 각 동의 상세 정보 수집
        print(f"📊 3단계: 발견된 {len(discovered_dongs)}개 동의 상세 정보 수집...")
        areas_info = {
            "gu_name": gu_name,
            "gu_code": gu_code,
            "discovery_time": datetime.now().isoformat(),
            "discovery_method": "smart_boundary_based",
            "gu_boundary": gu_boundary,
            "areas": [],
            "total_areas": 0,
            "coverage_analysis": {}
        }
        
        for dong_code in discovered_dongs:
            dong_detail = self._get_dong_detail_with_properties(dong_code)
            if dong_detail:
                areas_info["areas"].append(dong_detail)
        
        areas_info["total_areas"] = len(areas_info["areas"])
        
        # 4단계: 커버리지 분석
        expected_count = gu_config.get('expected_dong_count', 20)
        coverage_rate = (areas_info["total_areas"] / expected_count) * 100
        areas_info["coverage_analysis"] = {
            "expected_areas": expected_count,
            "discovered_areas": areas_info["total_areas"],
            "coverage_rate": f"{coverage_rate:.1f}%",
            "status": "완료" if coverage_rate >= 95 else "부분완료",
            "boundary_method": "네이버_경계_데이터_활용"
        }
        
        print(f"✅ 스마트 수집 완료: {areas_info['total_areas']}개 동 ({coverage_rate:.1f}%)")
        
        # 캐시 저장
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(areas_info, f, ensure_ascii=False, indent=2)
        print(f"💾 결과 캐시 저장: {cache_file}")
        
        return areas_info
    
    def _get_gu_boundary(self, center_lat: float, center_lon: float, gu_code: str) -> Optional[Dict]:
        """구 전체 경계 데이터 획득 (줌 14)"""
        try:
            response = requests.get(
                "https://new.land.naver.com/api/cortars",
                headers=self.headers,
                params={
                    'zoom': 14,  # 구 단위 줌 레벨
                    'centerLat': center_lat,
                    'centerLon': center_lon
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if (isinstance(data, dict) and 
                    data.get('cortarNo') == gu_code and 
                    data.get('cortarVertexLists')):
                    
                    return {
                        "cortarNo": data.get('cortarNo'),
                        "cortarName": data.get('cortarName'),
                        "divisionName": data.get('divisionName'),
                        "centerLat": data.get('centerLat'),
                        "centerLon": data.get('centerLon'),
                        "boundary_points": data.get('cortarVertexLists', [[]])[0],
                        "total_boundary_points": len(data.get('cortarVertexLists', [[]])[0])
                    }
        
        except Exception as e:
            print(f"⚠️ 구 경계 획득 오류: {e}")
        
        return None
    
    def _discover_dongs_within_boundary(self, gu_boundary: Dict, gu_name: str) -> Set[str]:
        """구 경계 내부에서 모든 동 탐지"""
        boundary_points = gu_boundary.get('boundary_points', [])
        if not boundary_points:
            return set()
        
        # 경계 상자 계산
        lats = [point[0] for point in boundary_points]
        lons = [point[1] for point in boundary_points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        print(f"   경계 상자: 위도 {min_lat:.4f}~{max_lat:.4f}, 경도 {min_lon:.4f}~{max_lon:.4f}")
        
        discovered_dongs = set()
        
        # 경계 내부를 촘촘한 격자로 스캔
        lat_step = (max_lat - min_lat) / 15  # 15x15 격자
        lon_step = (max_lon - min_lon) / 15
        
        scan_count = 0
        found_count = 0
        
        print(f"   15x15 격자로 경계 내부 스캔 (총 225개 포인트)")
        
        for i in range(16):  # 0~15
            for j in range(16):
                scan_lat = min_lat + (i * lat_step)
                scan_lon = min_lon + (j * lon_step)
                scan_count += 1
                
                # 경계 내부 점인지 확인 (간단한 방법)
                if self._is_point_in_boundary(scan_lat, scan_lon, boundary_points):
                    
                    # 줌 15, 16으로 동 레벨 정보 조회
                    for zoom in [15, 16]:
                        try:
                            response = requests.get(
                                "https://new.land.naver.com/api/cortars",
                                headers=self.headers,
                                params={
                                    'zoom': zoom,
                                    'centerLat': scan_lat,
                                    'centerLon': scan_lon
                                }
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                if (isinstance(data, dict) and 
                                    data.get('divisionName') == gu_name and
                                    data.get('cortarType') == 'sec'):  # 동 레벨
                                    
                                    before_size = len(discovered_dongs)
                                    discovered_dongs.add(data['cortarNo'])
                                    
                                    if len(discovered_dongs) > before_size:
                                        found_count += 1
                                        print(f"   ✅ 발견 {found_count}: {data.get('cortarName')} ({data['cortarNo']})")
                            
                            time.sleep(0.05)  # 짧은 딜레이
                            
                        except Exception as e:
                            continue
                
                # 진행률 표시
                if scan_count % 50 == 0:
                    print(f"   진행률: {scan_count}/225 ({scan_count/225*100:.1f}%) - 발견: {found_count}개")
        
        print(f"   스캔 완료: {scan_count}개 포인트, {found_count}개 동 발견")
        return discovered_dongs
    
    def _is_point_in_boundary(self, lat: float, lon: float, boundary_points: List[List[float]]) -> bool:
        """점이 경계 내부에 있는지 확인 (Ray Casting Algorithm)"""
        if not boundary_points or len(boundary_points) < 3:
            return False
        
        x, y = lon, lat  # 경도, 위도
        n = len(boundary_points)
        inside = False
        
        p1x, p1y = boundary_points[0][1], boundary_points[0][0]  # 경도, 위도 순서
        
        for i in range(1, n + 1):
            p2x, p2y = boundary_points[i % n][1], boundary_points[i % n][0]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _get_dong_detail_with_properties(self, dong_code: str) -> Optional[Dict]:
        """동의 상세 정보 + 매물 수 조회"""
        try:
            # 매물 수 조회
            property_count = self._get_property_count(dong_code)
            
            # 동 상세 정보 조회 (중심 좌표로 다시 호출)
            dong_info = self._get_dong_info_by_code(dong_code)
            
            if dong_info:
                return {
                    "cortarNo": dong_code,
                    "cortarName": dong_info.get('cortarName'),
                    "divisionName": dong_info.get('divisionName'),
                    "centerLat": dong_info.get('centerLat'),
                    "centerLon": dong_info.get('centerLon'),
                    "property_count": property_count,
                    "analysis_time": datetime.now().isoformat(),
                    "collection_method": "smart_boundary_discovery"
                }
        
        except Exception as e:
            print(f"⚠️ 동 {dong_code} 상세 정보 획득 실패: {e}")
        
        return None
    
    def _get_property_count(self, cortar_no: str) -> int:
        """지역의 매물 수 조회"""
        try:
            response = requests.get(
                "https://new.land.naver.com/api/articles",
                headers=self.headers,
                params={
                    'cortarNo': cortar_no,
                    'order': 'rank',
                    'realEstateType': 'SG:SMS:GJCG:APTHGJ:GM:TJ',
                    'tradeType': '',
                    'tag': '::::::::',
                    'rentPriceMin': '0',
                    'rentPriceMax': '900000000',
                    'priceMin': '0',
                    'priceMax': '900000000',
                    'areaMin': '0',
                    'areaMax': '900000000',
                    'oldBuildYears': '',
                    'recentlyBuildYears': '',
                    'minHouseHoldCount': '',
                    'maxHouseHoldCount': '',
                    'showArticle': 'false',
                    'sameAddressGroup': 'false',
                    'minMaintenanceCost': '',
                    'maxMaintenanceCost': '',
                    'priceType': 'RETAIL',
                    'directions': '',
                    'articleState': '',
                    'page': 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('articleCount', 0)
        
        except Exception as e:
            pass
        
        return 0
    
    def _get_dong_info_by_code(self, dong_code: str) -> Optional[Dict]:
        """동 코드로 상세 정보 조회"""
        # 실제로는 캐시된 정보나 별도 API 필요
        # 지금은 기본 정보만 반환
        return {
            "cortarNo": dong_code,
            "cortarName": f"동_{dong_code[-4:]}",
            "analysis_method": "smart_boundary_based"
        }

def main():
    """스마트 경계 기반 수집기 실행"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python smart_boundary_collector.py <구이름>")
        print("예시: python smart_boundary_collector.py 강남구")
        return
    
    gu_name = sys.argv[1]
    
    # 토큰 수집
    print("🔑 토큰 수집 중...")
    token_collector = PlaywrightTokenCollector()
    token = token_collector.get_token_with_playwright()
    
    if not token:
        print("❌ 토큰 획득 실패")
        return
    
    # 구 설정 로드
    with open('gu_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if gu_name not in config['supported_gu']:
        print(f"❌ 지원하지 않는 구: {gu_name}")
        print(f"지원 구역: {list(config['supported_gu'].keys())}")
        return
    
    gu_config = config['supported_gu'][gu_name]
    
    # 스마트 경계 기반 수집
    collector = SmartBoundaryCollector(token)
    areas_info = collector.collect_gu_complete_areas(gu_name, gu_config)
    
    if areas_info:
        print(f"\n🎯 스마트 수집 결과:")
        print(f"   발견 지역: {areas_info['total_areas']}개")
        print(f"   커버리지: {areas_info['coverage_analysis']['coverage_rate']}")
        print(f"   수집 방법: {areas_info['discovery_method']}")
        
        # 결과 저장
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"smart_areas_{gu_name}_{timestamp}.json"
        result_filepath = os.path.join(results_dir, result_filename)
        
        with open(result_filepath, 'w', encoding='utf-8') as f:
            json.dump(areas_info, f, ensure_ascii=False, indent=2)
        
        print(f"   결과 파일: {result_filepath}")

if __name__ == "__main__":
    main()