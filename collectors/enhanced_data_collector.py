#!/usr/bin/env python3
"""
향상된 네이버 부동산 데이터 수집기
- 8개 섹션 완전 활용 (articleDetail, articleAddition, articleFacility, etc.)
- 정규화된 데이터베이스 구조 지원
- 누락 데이터 보완 (중개사, 현장사진, 상세가격)
"""

import os
import sys
import json
import time
import requests
import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

# 카카오 주소 변환 모듈 추가
try:
    sys.path.insert(0, str(current_dir / 'collectors' / 'core'))
    from kakao_address_converter import KakaoAddressConverter
    KAKAO_AVAILABLE = True
    print("✅ 카카오 주소 변환기 로드 성공")
except ImportError as e:
    print(f"⚠️ 카카오 주소 변환기 로드 실패: {e}")
    KAKAO_AVAILABLE = False

class EnhancedNaverCollector:
    def __init__(self):
        """향상된 수집기 초기화"""
        # Supabase 연결
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        # 카카오 주소 변환기 초기화
        if KAKAO_AVAILABLE:
            try:
                self.kakao_converter = KakaoAddressConverter()
                print("✅ 카카오 API 연결 성공")
            except Exception as e:
                print(f"⚠️ 카카오 API 초기화 실패: {e}")
                self.kakao_converter = None
        else:
            self.kakao_converter = None
        
        # 통계 초기화
        self.stats = {
            'properties_processed': 0,
            'images_collected': 0,
            'realtors_processed': 0,
            'facilities_mapped': 0,
            'tax_info_saved': 0,        # 새로 추가
            'price_comparisons_saved': 0,  # 새로 추가
            'addresses_enriched': 0,    # 카카오 주소 변환 통계
            'errors': 0,
            'parsing_failures': {
                'article_detail': 0,
                'article_addition': 0,
                'article_facility': 0,
                'article_floor': 0,
                'article_price': 0,
                'article_realtor': 0,
                'article_space': 0,
                'article_tax': 0,
                'article_photos': 0
            }
        }
        
        # 파싱 실패 로그 파일
        self.parsing_log_file = f"parsing_failures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # 토큰 관리 - 기존 토큰 시스템 연동
        sys.path.insert(0, str(current_dir / 'collectors' / 'core'))
        try:
            from multi_token_manager import MultiTokenManager
            self.token_manager = MultiTokenManager()
            token_data = self.token_manager.get_random_token()
            if token_data:
                self.token = token_data['token']
                self.cookies = token_data['cookies']
                self.token_expires_at = token_data['expires_at']
                print(f"✅ 토큰 로드 성공 (만료: {self.token_expires_at})")
            else:
                print("⚠️ 사용 가능한 토큰이 없습니다. 자동 토큰 수집 시도...")
                self._collect_new_token()
        except ImportError:
            print("⚠️ 토큰 관리자를 찾을 수 없습니다. 자동 토큰 수집 시도...")
            self._collect_new_token()
    
    def _collect_new_token(self):
        """새로운 토큰 자동 수집"""
        try:
            from playwright_token_collector import PlaywrightTokenCollector
            print("🤖 Playwright로 토큰 자동 수집 중...")
            
            token_collector = PlaywrightTokenCollector()
            token_data = token_collector.get_token_with_playwright()
            
            if token_data and token_data.get('token'):
                self.token = token_data['token']
                self.cookies = token_data.get('cookies', {})
                # 6시간 후 만료로 설정
                self.token_expires_at = datetime.now() + timedelta(hours=6)
                print("✅ 새 토큰 수집 성공!")
                
                # 토큰 캐시 저장
                if hasattr(self, 'token_manager'):
                    self.token_manager.save_token(token_data)
            else:
                print("❌ 토큰 자동 수집 실패. 수동 설정이 필요합니다.")
                self.token = None
                self.cookies = {}
                self.token_expires_at = None
                
        except ImportError:
            print("❌ Playwright 토큰 수집기를 찾을 수 없습니다.")
            self.token = None
            self.cookies = {}
            self.token_expires_at = None
        
        print("✅ 향상된 네이버 수집기 초기화 완료")
    
    def setup_headers(self) -> Dict[str, str]:
        """API 요청 헤더 설정"""
        return {
            'authorization': f'Bearer {self.token}' if self.token else '',
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://new.land.naver.com/',
            'Origin': 'https://new.land.naver.com',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache'
        }
    
    def _get_random_user_agent(self) -> str:
        """랜덤 User-Agent"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
        ]
        return random.choice(agents)
    
    def collect_article_detail_enhanced(self, article_no: str) -> Optional[Dict]:
        """개별 매물 상세정보 수집 (8개 섹션 완전 활용)"""
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        params = {'complexNo': ''}
        
        try:
            headers = self.setup_headers()
            time.sleep(random.uniform(1.0, 2.0))  # 적절한 딜레이
            
            response = requests.get(url, headers=headers, params=params, 
                                  cookies=self.cookies, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # 디버깅: 특정 매물의 전체 API 응답 확인
                if article_no == "2546339433":
                    print(f"🔍 DEBUG: 매물 {article_no} API 응답 키들: {list(data.keys())}")
                    if 'articlePhotos' in data:
                        photos = data.get('articlePhotos', [])
                        print(f"🔍 DEBUG: articlePhotos 존재? {photos is not None}")
                        print(f"🔍 DEBUG: articlePhotos 타입: {type(photos)}")
                        print(f"🔍 DEBUG: articlePhotos 길이: {len(photos) if photos else 0}")
                        if photos:
                            print(f"🔍 DEBUG: 첫 번째 photo: {photos[0]}")
                    else:
                        print(f"🔍 DEBUG: articlePhotos 키가 API 응답에 없음!")
                
                # 8개 섹션 완전 처리 (article_no 전달하여 파싱 실패 추적)
                enhanced_data = {
                    'article_no': article_no,
                    'collection_timestamp': datetime.now().isoformat(),
                    'raw_sections': data,  # 원본 데이터 보존
                    
                    # 처리된 섹션별 데이터
                    'basic_info': self._process_article_detail(data.get('articleDetail', {}), article_no),
                    'additional_info': self._process_article_addition(data.get('articleAddition', {}), article_no),
                    'facility_info': self._process_article_facility(data.get('articleFacility', {}), article_no),
                    'floor_info': self._process_article_floor(data.get('articleFloor', {}), article_no),
                    'price_info': self._process_article_price(data.get('articlePrice', {}), article_no),
                    'realtor_info': self._process_article_realtor(data.get('articleRealtor', {}), article_no),
                    'space_info': self._process_article_space(data.get('articleSpace', {}), article_no),
                    'tax_info': self._process_article_tax(data.get('articleTax', {}), article_no),
                    'photo_info': self._process_article_photos(data.get('articlePhotos', []), article_no)
                }
                
                return enhanced_data
                
            else:
                print(f"⚠️ 매물 {article_no} 상세정보 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 매물 {article_no} 상세정보 오류: {e}")
            self.stats['errors'] += 1
            return None
    
    def log_parsing_failure(self, section: str, article_no: str, error_msg: str, raw_data: any = None):
        """파싱 실패 상세 로그"""
        self.stats['parsing_failures'][section] += 1
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'article_no': article_no,
            'section': section,
            'error': error_msg,
            'raw_data_sample': str(raw_data)[:500] if raw_data else 'No data'
        }
        
        # 콘솔 로그
        print(f"⚠️ 파싱 실패 [{section}] 매물 {article_no}: {error_msg}")
        
        # 파일 로그
        try:
            with open(self.parsing_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | {section} | {article_no} | {error_msg}\n")
                if raw_data:
                    f.write(f"  Raw Data Sample: {str(raw_data)[:200]}...\n")
                f.write("-" * 80 + "\n")
        except Exception as e:
            print(f"⚠️ 로그 파일 쓰기 실패: {e}")
    
    def _process_article_detail(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleDetail 섹션 처리"""
        try:
            if not data:
                self.log_parsing_failure('article_detail', article_no, "Empty data received", data)
                return {}
            
            # 건물명 추출 (여러 필드 시도)
            building_name = (data.get('buildingName') or 
                           data.get('articleName') or 
                           data.get('buildingTypeName') or
                           data.get('exposureAddress') or
                           f"매물_{article_no}")
            
            if not building_name:
                self.log_parsing_failure('article_detail', article_no, "No building name found in any field", data)
            
            return {
                # 건물 기본 정보
                'building_name': building_name,
            'building_use': data.get('buildingUse'),
            'law_usage': data.get('lawUsage'),
            
            # 위치 정보
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'exposure_address': data.get('exposureAddress'),
            'detail_address': data.get('detailAddress'),
            
            # 교통 정보 (완전한 지하철 데이터 처리)
            'walking_to_subway': data.get('walkingTimeToNearSubway'),
            'near_subway_list': self._process_subway_list(data.get('nearSubwayList', [])),
            
            # 주차 정보
            'parking_count': data.get('parkingCount'),
            'parking_possible': data.get('parkingPossibleYN') == 'Y',
            
            # 기타 시설
            'elevator_count': data.get('elevatorCount'),
            'floor_layer_name': data.get('floorLayerName'),
            
            # 관리 정보
            'monthly_management_cost': data.get('monthlyManagementCost'),
            'management_office_tel': data.get('managementOfficeTel'),
            
            # 입주 정보
            'move_in_type': data.get('moveInTypeName'),
            'move_in_discussion': data.get('moveInDiscussionPossibleYN') == 'Y',
            
            # 상세 설명
            'detail_description': data.get('detailDescription'),
            'tag_list': data.get('tagList', [])
        }
        except Exception as e:
            self.log_parsing_failure('article_detail', article_no, f"Processing error: {str(e)}", data)
            return {}
    
    def _process_subway_list(self, subway_list: List[Dict]) -> List[Dict]:
        """지하철역 목록 처리 - nearSubwayList 배열 완전 파싱"""
        try:
            if not subway_list or not isinstance(subway_list, list):
                return []
            
            processed_stations = []
            for station in subway_list:
                if not isinstance(station, dict):
                    continue
                    
                station_info = {
                    'station_name': station.get('stationName'),
                    'line_name': station.get('lineName'),
                    'line_number': station.get('lineNumber'),
                    'walking_time': station.get('walkingTime'),
                    'distance_meters': station.get('distance'),
                    'transfer_count': station.get('transferCount', 0),
                    'line_color': station.get('lineColor'),
                    'station_code': station.get('stationCode')
                }
                
                # 유효한 역명이 있는 경우만 추가
                if station_info['station_name']:
                    processed_stations.append(station_info)
            
            # 도보 시간 순으로 정렬
            processed_stations.sort(key=lambda x: x.get('walking_time', 999) or 999)
            
            return processed_stations
            
        except Exception as e:
            print(f"⚠️ 지하철 목록 처리 실패: {e}")
            return []
    
    def _process_article_addition(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleAddition 섹션 처리 - 완전한 구현"""
        try:
            if not data:
                self.log_parsing_failure('article_addition', article_no, "Empty data received", data)
                return {}
            
            def safe_price_comparison(value):
                """가격 비교 데이터 안전하게 변환"""
                if value is None or value == "" or value == "-":
                    return None
                try:
                    return int(float(str(value)))
                except (ValueError, TypeError):
                    return None
            
            return {
                # 이미지 정보
                'representative_img_url': data.get('representativeImgUrl'),
                'site_image_count': data.get('siteImageCount', 0),
                
                # 시세 정보 (완전한 가격 비교 데이터)
                'same_addr_count': data.get('sameAddrCnt', 0),
                'same_addr_max_price': safe_price_comparison(data.get('sameAddrMaxPrc')),
                'same_addr_min_price': safe_price_comparison(data.get('sameAddrMinPrc')),
                
                # 추가 정보
                'article_feature_desc': data.get('articleFeatureDesc'),
                'cpid': data.get('cpid'),  # 복합단지 ID
                'complex_name': data.get('complexName'),
                
                # 추가된 가격 분석 데이터
                'price_range': {
                    'min_price': safe_price_comparison(data.get('sameAddrMinPrc')),
                    'max_price': safe_price_comparison(data.get('sameAddrMaxPrc')),
                    'sample_count': data.get('sameAddrCnt', 0)
                },
                
                # 매물 특징 분석
                'has_price_comparison': data.get('sameAddrCnt', 0) > 0,
                'is_complex_property': data.get('cpid') is not None,
                'has_feature_description': bool(data.get('articleFeatureDesc'))
            }
        except Exception as e:
            self.log_parsing_failure('article_addition', article_no, f"Processing error: {str(e)}", data)
            return {}
    
    def _process_article_facility(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleFacility 섹션 처리 - ✅ 실제 API 구조에 맞게 완전히 재작성"""
        try:
            if not data:
                self.log_parsing_failure('article_facility', article_no, "Empty data received", data)
                return {'facilities': {}, 'available_facilities': [], 'facility_count': 0, 'direction': None}

            # ✅ FIXED: 실제 API에서 시설정보는 etcFacilities 텍스트로 제공됨
            facilities_text = data.get('etcFacilities', '')
            facility_list = data.get('etcFacilityList', [])
            
            # 텍스트에서 시설 파싱 (실제 네이버 API 방식)
            facilities = {
                'parking': '주차' in facilities_text,
                'elevator': '엘리베이터' in facilities_text,
                'air_conditioner': '에어컨' in facilities_text or '냉방' in facilities_text,
                'heating': '난방' in facilities_text,
                'security': '보안' in facilities_text or '경비' in facilities_text,
                'internet': '인터넷' in facilities_text or '네트워크' in facilities_text,
                'cable_tv': 'TV' in facilities_text or '케이블' in facilities_text,
                'water_purifier': '정수기' in facilities_text,
                'gas_range': '가스레인지' in facilities_text,
                'induction': '인덕션' in facilities_text,
                'microwave': '전자레인지' in facilities_text,
                'refrigerator': '냉장고' in facilities_text,
                'washing_machine': '세탁기' in facilities_text,
                'dish_washer': '식기세척기' in facilities_text,
                'shoe_closet': '신발장' in facilities_text,
            }
            
            # ✅ ADDED: 실제 API에 존재하는 추가 정보들
            direction = data.get('directionTypeName')  # 방향 정보
            building_coverage_ratio = data.get('buildingCoverageRatio')  # 건폐율
            floor_area_ratio = data.get('floorAreaRatio')  # 용적률
            
            # 사용 가능한 시설 목록 생성
            available_facilities = [k for k, v in facilities.items() if v]
            
            return {
                'facilities': facilities,
                'available_facilities': available_facilities,
                'facility_count': len(available_facilities),
                'facilities_text': facilities_text,  # 원본 텍스트도 보존
                'facility_list': facility_list,      # 원본 리스트도 보존
                
                # ✅ 추가된 실제 API 필드들
                'direction': direction,                           # 방향
                'building_coverage_ratio': building_coverage_ratio,  # 건폐율
                'floor_area_ratio': floor_area_ratio,            # 용적률
                'direction_type_code': data.get('directionTypeCode'),
                'building_use_approval_date': data.get('buildingUseAprvYmd')
            }
        except Exception as e:
            self.log_parsing_failure('article_facility', article_no, f"Processing error: {str(e)}", data)
            return {'facilities': {}, 'available_facilities': [], 'facility_count': 0, 'direction': None}
    
    def _process_article_floor(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleFloor 섹션 처리 - ✅ 실제 API 필드명으로 수정"""
        try:
            if not data:
                self.log_parsing_failure('article_floor', article_no, "Empty data received", data)
                return {}
            
            return {
                # ✅ VERIFIED: 실제 API에 존재하는 필드들
                'total_floor_count': data.get('totalFloorCount'),
                'underground_floor_count': data.get('undergroundFloorCount'), 
                'upperground_floor_count': data.get('uppergroundFloorCount'),  # ✅ FIXED 필드명
                'floor_type_code': data.get('floorTypeCode'),
                'floor_input_method_code': data.get('floorInputMethodCode'),
                'corresponding_floor_count': data.get('correspondingFloorCount'),
                
                # 기존 필드들 (API에 없을 수도 있음)
                'current_floor': data.get('currentFloor'),  # articleDetail에 있을 수 있음
                'floor_description': data.get('floorDescription')
            }
        except Exception as e:
            self.log_parsing_failure('article_floor', article_no, f"Processing error: {str(e)}", data)
            return {}
    
    def _process_article_price(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articlePrice 섹션 처리 (상세 가격 정보)"""
        return {
            # 매매/전세 가격
            'deal_price': data.get('dealPrice'),
            'warrant_price': data.get('warrantPrice'),
            
            # 월세 정보
            'rent_price': data.get('rentPrice'),
            'deposit': data.get('deposit'),
            
            # 관리비
            'monthly_management_cost': data.get('monthlyManagementCost'),
            'management_cost_include': data.get('managementCostInclude', []),
            
            # 기타 비용
            'premium': data.get('premium'),  # 권리금
            'loan': data.get('loan'),        # 대출 정보
            
            # 가격 정보 메타데이터
            'price_type': data.get('priceType'),
            'price_title': data.get('priceTitle')
        }
    
    def _process_article_realtor(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleRealtor 섹션 처리 (중개사 정보) - ✅ 실제 API 필드명으로 수정"""
        return {
            # ✅ FIXED: 실제 API 필드명 사용
            'office_name': data.get('realtorName'),              # 중개사무소명
            'realtor_name': data.get('representativeName'),      # 대표자명
            
            # ✅ FIXED: 연락처 정보 - 올바른 필드명
            'mobile_number': data.get('cellPhoneNo'),            # 휴대폰번호
            'telephone': data.get('representativeTelNo'),        # 대표전화
            
            # ✅ VERIFIED: 주소 정보
            'office_address': data.get('address'),               # 주소
            
            # ✅ FIXED: 사업자 정보 - 올바른 필드명  
            'business_registration_number': data.get('establishRegistrationNo'),  # 개업등록번호
            
            # ✅ ADDED: 실제 API에 존재하는 유용한 필드들
            'trade_complete_count': data.get('tradeCompleteCount', 0),    # 거래완료건수
            'owner_article_count': data.get('ownerArticleCount', 0),      # 보유매물수
            'expose_tel_type_code': data.get('exposeTelTypeCode'),        # 연락처노출타입
            
            # 기존 필드들 (API에 없지만 기본값으로 유지)
            'grade': None,
            'review_count': 0,
            'certified_realtor': False,
            'naver_verified': False
        }
    
    def _extract_area_from_description(self, description: str) -> Dict:
        """매물 설명에서 면적 정보 추출"""
        import re
        
        result = {
            'extracted_exclusive_area': None,
            'extracted_supply_area': None,
            'extracted_total_area': None,
            'area_unit': '㎡'
        }
        
        if not description:
            return result
            
        # 면적 패턴들
        patterns = [
            # "전용면적 : 약 80평", "임대면적 약 53평"  
            (r'전용면적.*?(\d+(?:\.\d+)?)\s*평', 'exclusive_area_pyeong'),
            (r'임대면적.*?(\d+(?:\.\d+)?)\s*평', 'supply_area_pyeong'),
            (r'연면적.*?(\d+(?:\.\d+)?)\s*평', 'total_area_pyeong'),
            
            # "192.28㎡", "49.6㎡"
            (r'전용.*?(\d+(?:\.\d+)?)\s*㎡', 'exclusive_area'),
            (r'공급.*?(\d+(?:\.\d+)?)\s*㎡', 'supply_area'),  
            (r'연면적.*?(\d+(?:\.\d+)?)\s*㎡', 'total_area'),
            
            # "192.28㎡/49.6㎡", "102/49㎡"
            (r'(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\s*㎡', 'dual_area'),
            
            # 기타 패턴
            (r'(\d+(?:\.\d+)?)\s*㎡', 'any_area')
        ]
        
        for pattern, area_type in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                if area_type == 'dual_area':
                    # "192.28/49.6㎡" 형태
                    result['extracted_supply_area'] = float(matches[0][0])
                    result['extracted_exclusive_area'] = float(matches[0][1])
                    break
                elif 'pyeong' in area_type:
                    # 평수 → ㎡ 변환 (1평 ≈ 3.3058㎡)
                    pyeong_value = float(matches[0])
                    area_value = round(pyeong_value * 3.3058, 2)
                    if 'exclusive' in area_type:
                        result['extracted_exclusive_area'] = area_value
                    elif 'supply' in area_type:
                        result['extracted_supply_area'] = area_value
                    elif 'total' in area_type:
                        result['extracted_total_area'] = area_value
                    break
                else:
                    # ㎡ 값 직접 사용
                    area_value = float(matches[0])
                    if 'exclusive' in area_type:
                        result['extracted_exclusive_area'] = area_value
                    elif 'supply' in area_type:
                        result['extracted_supply_area'] = area_value
                    elif 'total' in area_type:
                        result['extracted_total_area'] = area_value
                    elif 'any' in area_type and not any(result.values()):
                        # 첫 번째로 발견된 면적값 사용
                        result['extracted_exclusive_area'] = area_value
                    break
        
        return result

    def _process_article_space(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleSpace 섹션 처리 (공간 정보) - 완전한 필드 추가"""
        try:
            if not data:
                self.log_parsing_failure('article_space', article_no, "Empty data received", data)
                return {}
            
            return {
                # ✅ FIXED: Support both field name formats
                'supply_area': data.get('supplyArea') or data.get('supplySpace'),      # 공급면적
                'exclusive_area': data.get('exclusiveArea') or data.get('exclusiveSpace'),  # 전용면적
                'exclusive_rate': data.get('exclusiveRate'),     # 전용률
                'room_count': data.get('roomCount'),             # 방 개수
                'bathroom_count': data.get('bathRoomCount'),     # 욕실 개수
                'veranda_count': data.get('verandaCount'),       # 베란다 개수 ⚡ ADDED
                'space_type': data.get('spaceType'),             # 공간 유형 ⚡ ADDED
                'structure_type': data.get('structureType'),     # 구조 유형 ⚡ ADDED
                
                # 기존 필드들
                'ground_space': data.get('groundSpace'),         # 토지면적
                'total_space': data.get('totalSpace'),           # 총면적
                'building_space': data.get('buildingSpace'),     # 건물면적
                'ground_share_space': data.get('groundShareSpace'),
                'expect_space': data.get('expectSpace'),
                
                # 면적 단위 (API에서 ㎡로 제공됨)
                'area_unit': '㎡'
            }
        except Exception as e:
            self.log_parsing_failure('article_space', article_no, f"Processing error: {str(e)}", data)
            return {}
    
    def _process_article_tax(self, data: Dict, article_no: str = "unknown") -> Dict:
        """articleTax 섹션 처리 (세금 정보) - 완전한 구현 및 데이터 검증"""
        try:
            if not data:
                self.log_parsing_failure('article_tax', article_no, "Empty data received", data)
                return {}
            
            def safe_tax_amount(value):
                """세금 금액 안전하게 변환 (양수 검증)"""
                if value is None or value == "" or value == "-":
                    return None
                try:
                    tax_value = float(str(value))
                    # 음수 세금은 무효 처리
                    return tax_value if tax_value >= 0 else None
                except (ValueError, TypeError):
                    return None
            
            def safe_tax_rate(value):
                """세금률 안전하게 변환 (0-100% 범위 검증)"""
                if value is None or value == "" or value == "-":
                    return None
                try:
                    rate_value = float(str(value))
                    # 세율은 0-100% 범위 내여야 함
                    if 0 <= rate_value <= 100:
                        return rate_value
                    else:
                        print(f"⚠️ 비정상 세율: {rate_value}% - 매물 {article_no}")
                        return None
                except (ValueError, TypeError):
                    return None

            tax_data = {
                # ✅ FIXED: 실제 API 필드명 사용 (테스트로 확인됨)
                'acquisition_tax': safe_tax_amount(data.get('acquisitionTax')),
                'acquisition_tax_rate': safe_tax_rate(data.get('acquisitionTaxRate')),  # ⚡ ADDED
                
                # ✅ FIXED: 등록세 - 올바른 필드명
                'registration_tax': safe_tax_amount(data.get('registTax')),        # registrationTax가 아님!
                'registration_tax_rate': safe_tax_rate(data.get('registrationTaxRate')),  # ⚡ ADDED
                'registration_fee': safe_tax_amount(data.get('registFee')),
                
                # ✅ FIXED: 중개보수 - 올바른 필드명
                'brokerage_fee': safe_tax_amount(data.get('brokerFee')),           # brokerageFee가 아님!
                'brokerage_fee_rate': safe_tax_rate(data.get('brokerageFeeRate')),  # ⚡ ADDED
                'max_brokerage_fee': safe_tax_amount(data.get('maxBrokerFee')),    # API에 존재
                
                # ✅ ADDED: 실제 API에 존재하는 세금 항목들
                'education_tax': safe_tax_amount(data.get('eduTax')),
                'special_tax': safe_tax_amount(data.get('specialTax')),
                'registration_apply_fee': safe_tax_amount(data.get('registApplyFee')),
                'digital_revenue_stamp': safe_tax_amount(data.get('digitalRevenuStamp')),
                'nation_house_bond': safe_tax_amount(data.get('nationHouseBond')),
                'stamp_duty': safe_tax_amount(data.get('stampDuty')),             # ⚡ ADDED
                'vat': safe_tax_amount(data.get('vat')),                          # ⚡ ADDED
                
                # 총 비용 계산
                'total_tax': safe_tax_amount(data.get('totalTax')),               # ⚡ ADDED
                'total_cost': safe_tax_amount(data.get('totalCost')),             # ⚡ ADDED  
                'total_price': safe_tax_amount(data.get('totalPrice'))            # 기존 필드
            }
            
            # 유효한 세금 정보가 있는지 확인
            has_tax_data = any(value is not None for value in tax_data.values())
            if not has_tax_data:
                self.log_parsing_failure('article_tax', article_no, "No valid tax data found", data)
            
            return tax_data
        except Exception as e:
            self.log_parsing_failure('article_tax', article_no, f"Processing error: {str(e)}", data)
            return {}
    
    def _process_article_photos(self, data: List[Dict], article_no: str = "unknown") -> Dict:
        """articlePhotos 섹션 처리 (사진 정보)"""
        if not data:
            print(f"⚠️ DEBUG: articlePhotos 데이터가 비어있음")
            return {'photos': [], 'photo_count': 0}
        
        print(f"🔍 DEBUG: articlePhotos 원본 데이터 수: {len(data)}")
        print(f"🔍 DEBUG: 첫 번째 photo 키들: {list(data[0].keys()) if data else 'None'}")
        
        processed_photos = []
        
        for idx, photo in enumerate(data):
            # 🔧 네이버 API 실제 필드명으로 수정
            image_url = None
            
            # 여러 가능한 필드명 시도
            if photo.get('imageUrl'):
                image_url = photo.get('imageUrl')
            elif photo.get('imageSrc'):
                # imageSrc를 완전한 URL로 변환
                image_src = photo.get('imageSrc')
                if image_src and image_src.startswith('/'):
                    image_url = f"https://new.land.naver.com{image_src}"
                else:
                    image_url = image_src
            elif photo.get('imageKey'):
                # imageKey 기반 URL 생성 (필요시)
                image_key = photo.get('imageKey')
                if image_key:
                    image_url = f"https://new.land.naver.com/api/article/image/{image_key}"
            
            print(f"🔍 DEBUG: photo[{idx}] -> URL: {image_url}")
            
            photo_info = {
                'order': idx + 1,
                'image_url': image_url,
                'thumbnail_url': photo.get('thumbnailUrl'),
                'image_type': photo.get('imageType', 'general').lower(),  # 소문자로 통일
                'width': photo.get('width'),
                'height': photo.get('height'),
                'file_size': photo.get('fileSize'),
                'caption': photo.get('caption', ''),
                'is_representative': photo.get('isRepresentative') == 'Y'
            }
            processed_photos.append(photo_info)
        
        # 사진 유형별 분류
        photo_types = {}
        for photo in processed_photos:
            photo_type = photo['image_type']
            if photo_type not in photo_types:
                photo_types[photo_type] = []
            photo_types[photo_type].append(photo)
        
        return {
            'photos': processed_photos,
            'photo_count': len(processed_photos),
            'photo_types': photo_types,
            'has_representative': any(p['is_representative'] for p in processed_photos)
        }
    
    def save_to_normalized_database(self, enhanced_data: Dict) -> bool:
        """정규화된 데이터베이스에 저장"""
        try:
            article_no = enhanced_data['article_no']
            print(f"💾 매물 {article_no} 정규화된 DB 저장 중...")
            
            # 1. 기본 매물 정보 저장
            property_id = self._save_property_basic(enhanced_data)
            
            if not property_id:
                return False
            
            # 2. 위치 정보 저장
            self._save_property_location(property_id, enhanced_data)
            
            # 3. 물리적 정보 저장
            self._save_property_physical(property_id, enhanced_data)
            
            # 4. 가격 정보 저장
            self._save_property_prices(property_id, enhanced_data)
            
            # 5. 중개사 정보 저장
            self._save_realtor_info(property_id, enhanced_data)
            
            # 6. 이미지 정보 저장
            self._save_property_images(property_id, enhanced_data)
            
            # 7. 시설 정보 저장
            self._save_property_facilities(property_id, enhanced_data)
            
            # 8. 세금 정보 저장 (새로 추가 - articleTax 섹션)
            self._save_property_tax_info(property_id, enhanced_data)
            
            # 9. 가격 비교 정보 저장 (새로 추가 - articleAddition 섹션)
            self._save_property_price_comparison(property_id, enhanced_data)
            
            print(f"✅ 매물 {article_no} 정규화된 DB 저장 완료 (8개 섹션 완전 처리)")
            self.stats['properties_processed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ 매물 {enhanced_data.get('article_no')} 저장 실패: {e}")
            self.stats['errors'] += 1
            return False
    
    def _save_property_basic(self, data: Dict) -> Optional[int]:
        """기본 매물 정보 저장 (UPSERT - 항상 최신 정보로 업데이트)"""
        try:
            article_no = data['article_no']
            basic_info = data['basic_info']
            
            # 🔧 CRITICAL: 외래키 ID 조회 추가
            real_estate_type_id = self._resolve_real_estate_type_id(data)
            trade_type_id = self._resolve_trade_type_id(data) 
            region_id = self._resolve_region_id(data)
            
            # 필수 외래키 검증
            if not all([real_estate_type_id, trade_type_id, region_id]):
                missing_keys = []
                if not real_estate_type_id: missing_keys.append('real_estate_type_id')
                if not trade_type_id: missing_keys.append('trade_type_id')
                if not region_id: missing_keys.append('region_id')
                print(f"❌ 필수 외래키 누락: {', '.join(missing_keys)} - 매물 {article_no}")
                return None
            
            # 먼저 기존 매물이 있는지 확인
            existing = self.client.table('properties_new').select('id, created_at').eq('article_no', article_no).execute()
            
            property_data = {
                'article_no': article_no,
                'article_name': basic_info.get('building_name'),
                'real_estate_type_id': real_estate_type_id,  # 🔧 추가
                'trade_type_id': trade_type_id,              # 🔧 추가
                'region_id': region_id,                      # 🔧 추가
                'last_seen_date': date.today().isoformat(),
                'is_active': True,
                'tag_list': basic_info.get('tag_list', []),
                'description': basic_info.get('detail_description'),
                # 새로 추가된 컬럼들 (스키마 배포 후 활성화)
                # 'building_use': basic_info.get('building_use'),
                # 'law_usage': basic_info.get('law_usage'),
                # 'floor_layer_name': basic_info.get('floor_layer_name'),
                # 'approval_date': basic_info.get('approval_date'),
                'updated_at': datetime.now().isoformat()
            }
            
            if existing.data:
                # 기존 매물 - 모든 정보 업데이트 (가격 변동, 상태 변경 등 반영)
                property_id = existing.data[0]['id']
                original_created_at = existing.data[0]['created_at']
                
                # created_at은 유지, collected_date는 최초 수집일 유지
                property_data['created_at'] = original_created_at
                
                self.client.table('properties_new').update(property_data).eq('id', property_id).execute()
                print(f"🔄 매물 {article_no} 정보 업데이트 (가격/상태 변동 반영)")
                return property_id
            else:
                # 새로운 매물
                property_data['collected_date'] = date.today().isoformat()
                property_data['created_at'] = datetime.now().isoformat()
                
                result = self.client.table('properties_new').insert(property_data).execute()
                if result.data:
                    print(f"✨ 매물 {article_no} 신규 저장")
                    return result.data[0]['id']
            
        except Exception as e:
            print(f"⚠️ 기본 매물 정보 저장 실패: {e}")
        
        return None
    
    def _save_property_location(self, property_id: int, data: Dict):
        """위치 정보 저장"""
        try:
            basic_info = data['basic_info']
            
            # 🔧 region_id 조회 (이미 property_basic에서 사용한 값 재사용)
            region_id = self._resolve_region_id(data)
            
            # 🔧 좌표 검증 (DECIMAL 범위 준수)
            def safe_coordinate(value, coord_type='lat'):
                """좌표를 안전하게 변환 (위도/경도 범위 검증)"""
                if value is None:
                    return None
                try:
                    coord = float(value)
                    if coord_type == 'lat' and not (-90 <= coord <= 90):
                        print(f"⚠️ 위도 범위 초과: {coord} - NULL로 처리")
                        return None
                    elif coord_type == 'lon' and not (-180 <= coord <= 180):
                        print(f"⚠️ 경도 범위 초과: {coord} - NULL로 처리")
                        return None
                    return coord
                except (ValueError, TypeError):
                    return None
            
            # 지하철 정보 처리 (nearSubwayList 배열)
            subway_list = basic_info.get('near_subway_list', [])
            nearest_station = None
            if subway_list and len(subway_list) > 0:
                # 첫 번째 역을 가장 가까운 역으로 설정
                nearest_station = subway_list[0].get('stationName') if isinstance(subway_list[0], dict) else str(subway_list[0])
            
            location_data = {
                'property_id': property_id,
                'latitude': safe_coordinate(basic_info.get('latitude'), 'lat'),
                'longitude': safe_coordinate(basic_info.get('longitude'), 'lon'),
                'address_road': basic_info.get('exposure_address'),
                'address_jibun': basic_info.get('detail_address'),  # 새로 추가
                'building_name': basic_info.get('building_name'),
                'walking_to_subway': basic_info.get('walking_to_subway'),
                'nearest_station': nearest_station,  # 새로 추가
                'subway_stations': subway_list if subway_list else None,  # 새로 추가 (JSONB)
                'region_id': region_id,
                'address_verified': False
            }
            
            # 🚀 카카오 API로 상세 주소 변환 (핵심 기능!)
            if self.kakao_converter and location_data['latitude'] and location_data['longitude']:
                try:
                    print(f"🔄 카카오 API로 상세 주소 변환 중... ({location_data['latitude']}, {location_data['longitude']})")
                    kakao_result = self.kakao_converter.convert_coord_to_address(
                        str(location_data['latitude']), 
                        str(location_data['longitude'])
                    )
                    
                    if kakao_result:
                        # 카카오 상세 정보로 업데이트
                        location_data.update({
                            'kakao_road_address': kakao_result.get('road_address'),
                            'kakao_jibun_address': kakao_result.get('jibun_address'), 
                            'kakao_building_name': kakao_result.get('building_name'),
                            'kakao_zone_no': kakao_result.get('zone_no'),
                            'kakao_api_response': kakao_result,  # 전체 응답 저장 (JSONB)
                            'address_enriched': True
                        })
                        
                        self.stats['addresses_enriched'] += 1
                        print(f"✅ 카카오 상세주소: {kakao_result.get('road_address', '정보없음')}")
                        print(f"🏢 건물명: {kakao_result.get('building_name', '정보없음')}")
                    else:
                        print("⚠️ 카카오 주소 변환 결과 없음")
                        location_data['address_enriched'] = False
                        
                except Exception as e:
                    print(f"❌ 카카오 주소 변환 실패: {e}")
                    location_data['address_enriched'] = False
            else:
                location_data['address_enriched'] = False
                print("⚠️ 카카오 변환 건너뛰기 (변환기 없음 또는 좌표 없음)")
            
            print(f"📍 최종 위치정보: {location_data.get('kakao_road_address', location_data['address_road'])}")
            
            self.client.table('property_locations').insert(location_data).execute()
            
        except Exception as e:
            print(f"❌ 위치 정보 저장 실패: {e}")
            print(f"🔍 DEBUG: basic_info={data.get('basic_info')}")
            if 'location_data' in locals():
                print(f"🔍 DEBUG: location_data keys={list(location_data.keys())}")
                # 카카오 API 응답 크기 체크
                if 'kakao_api_response' in location_data and location_data['kakao_api_response']:
                    import sys
                    kakao_size = sys.getsizeof(str(location_data['kakao_api_response']))
                    print(f"🔍 DEBUG: kakao_api_response size={kakao_size} bytes")
            import traceback
            print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    def _save_property_physical(self, property_id: int, data: Dict):
        """물리적 정보 저장 (데이터 검증 포함)"""
        try:
            space_info = data['space_info']
            floor_info = data['floor_info']
            facility_info = data['facility_info']
            
            def safe_int(value):
                """안전하게 정수로 변환 (-, None, 빈 문자열 처리)"""
                if value is None or value == "" or value == "-":
                    return None
                try:
                    return int(float(str(value)))
                except (ValueError, TypeError):
                    return None
            
            def safe_float(value):
                """안전하게 실수로 변환"""
                if value is None or value == "" or value == "-":
                    return None
                try:
                    return float(str(value))
                except (ValueError, TypeError):
                    return None
            
            # 🔧 면적 데이터 검증 및 보정 (제약조건 준수)
            area_exclusive = safe_float(space_info.get('exclusive_area'))
            area_supply = safe_float(space_info.get('supply_area'))
            
            # 면적이 0 이하이거나 NULL이면 최소값 설정 (constraint 위반 방지)
            if area_exclusive is None or area_exclusive <= 0:
                area_exclusive = 10.0  # 최소 10㎡ 기본값
                print(f"⚠️ 전용면적 보정: 10㎡ 기본값 적용")
                
            if area_supply is None or area_supply <= 0:
                area_supply = area_exclusive * 1.2  # 전용면적의 120%로 추정
                print(f"⚠️ 공급면적 보정: {area_supply}㎡ 추정값 적용")
            
            # 🔧 층수 데이터 검증 (floor_current <= floor_total 제약조건)
            floor_current = safe_int(floor_info.get('current_floor'))
            floor_total = safe_int(floor_info.get('total_floor_count'))
            
            # 층수 로직 검증 및 보정
            if floor_current is not None and floor_total is not None:
                if floor_current > floor_total:
                    print(f"⚠️ 층수 로직 오류: 현재층({floor_current}) > 총층수({floor_total}) - 수정")
                    floor_total = max(floor_current, floor_total)
            
            # 기본 정보 추가 (basic_info에서 가져오기)
            basic_info = data.get('basic_info', {})
            
            physical_data = {
                'property_id': property_id,
                'area_exclusive': area_exclusive,        # 🔧 검증된 값
                'area_supply': area_supply,              # 🔧 검증된 값  
                'area_utilization_rate': safe_float(space_info.get('exclusive_rate')),
                'floor_current': floor_current,
                'floor_total': floor_total,
                'floor_underground': safe_int(floor_info.get('underground_floor_count')),
                'room_count': safe_int(space_info.get('room_count')),
                'bathroom_count': safe_int(space_info.get('bathroom_count')),
                'parking_possible': facility_info['facilities'].get('parking', False),
                'elevator_available': facility_info['facilities'].get('elevator', False),
                # 🔧 FIXED: 방향 정보 추가 (facility_info에서 가져오기)
                'direction': facility_info.get('direction'),
                # 새로 추가된 컬럼들
                'veranda_count': safe_int(space_info.get('veranda_count')),
                'space_type': space_info.get('space_type'),
                'structure_type': space_info.get('structure_type'),
                'floor_description': floor_info.get('floor_description'),
                'ground_floor_count': safe_int(floor_info.get('ground_floor_count')),
                'monthly_management_cost': safe_int(basic_info.get('monthly_management_cost')),
                'management_office_tel': basic_info.get('management_office_tel'),
                'move_in_type': basic_info.get('move_in_type'),
                'move_in_discussion': basic_info.get('move_in_discussion', False),
                'heating_type': basic_info.get('heating_type')
            }
            
            # 🔧 최종 데이터 검증 로그
            print(f"📐 물리정보: 전용면적={area_exclusive}㎡, 공급면적={area_supply}㎡, {floor_current}/{floor_total}층")
            
            self.client.table('property_physical').insert(physical_data).execute()
            
        except Exception as e:
            print(f"❌ 물리적 정보 저장 실패: {e}")
            print(f"🔍 DEBUG: space_info={data.get('space_info')}")
            print(f"🔍 DEBUG: floor_info={data.get('floor_info')}")
            print(f"🔍 DEBUG: facility_info={data.get('facility_info')}")
            if 'physical_data' in locals():
                print(f"🔍 DEBUG: physical_data keys={list(physical_data.keys())}")
                missing_cols = [k for k, v in physical_data.items() if k not in ['property_id', 'created_at'] and v is not None]
                print(f"🔍 DEBUG: non_null_columns={missing_cols}")
            import traceback
            print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    def _save_property_prices(self, property_id: int, data: Dict):
        """가격 정보 저장 (변동 사항 체크 후 업데이트)"""
        try:
            price_info = data['price_info']
            today = date.today().isoformat()
            article_no = data['article_no']
            
            def safe_price(value):
                """가격을 안전하게 변환 (양수 검증)"""
                if value is None:
                    return None
                try:
                    price = int(float(value))
                    return price if price > 0 else None
                except (ValueError, TypeError):
                    return None
            
            prices = []
            
            # 🔧 매매가 (검증 후 저장)
            deal_price = safe_price(price_info.get('deal_price'))
            if deal_price:
                prices.append({
                    'property_id': property_id,
                    'price_type': 'sale',
                    'amount': deal_price,
                    'valid_from': today
                })
            
            # 🔧 전세 (검증 후 저장)
            warrant_price = safe_price(price_info.get('warrant_price'))
            if warrant_price:
                prices.append({
                    'property_id': property_id,
                    'price_type': 'deposit',
                    'amount': warrant_price,
                    'valid_from': today
                })
            
            # 🔧 월세 (검증 후 저장)
            rent_price = safe_price(price_info.get('rent_price'))
            if rent_price:
                prices.append({
                    'property_id': property_id,
                    'price_type': 'rent',
                    'amount': rent_price,
                    'valid_from': today
                })
            
            # 🔧 관리비 (검증 후 저장)
            management_cost = safe_price(price_info.get('monthly_management_cost'))
            if management_cost:
                prices.append({
                    'property_id': property_id,
                    'price_type': 'management',
                    'amount': management_cost,
                    'valid_from': today
                })
            
            if prices:
                price_summary = [f"{p['price_type']}:{p['amount']:,}만원" for p in prices]
                print(f"💰 가격정보: {', '.join(price_summary)}")
                self.client.table('property_prices').insert(prices).execute()
            else:
                print(f"💰 유효한 가격 정보 없음 - 매물 {article_no}")
                
        except Exception as e:
            print(f"❌ 가격 정보 저장 실패: {e}")
            print(f"🔍 DEBUG: price_info={data.get('price_info')}")
    
    def _save_realtor_info(self, property_id: int, data: Dict):
        """중개사 정보 저장"""
        try:
            realtor_info = data['realtor_info']
            
            if not realtor_info.get('office_name'):
                return
            
            # 중개사 정보 upsert
            realtor_data = {
                'realtor_name': realtor_info.get('office_name'),
                'business_number': realtor_info.get('business_registration_number'),
                'license_number': realtor_info.get('license_number'),
                'phone_number': realtor_info.get('telephone'),
                'mobile_number': realtor_info.get('mobile_number'),
                'office_address': realtor_info.get('office_address'),
                'profile_image_url': realtor_info.get('profile_image_url'),
                'rating': realtor_info.get('grade'),
                'review_count': realtor_info.get('review_count', 0),
                'total_listings': realtor_info.get('total_article_count', 0),
                'is_verified': realtor_info.get('naver_verified', False),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # 중개사 저장 (중복 확인)
            existing_realtor = self.client.table('realtors').select('id').eq('realtor_name', realtor_data['realtor_name']).execute()
            
            if existing_realtor.data:
                realtor_id = existing_realtor.data[0]['id']
            else:
                new_realtor = self.client.table('realtors').insert(realtor_data).execute()
                realtor_id = new_realtor.data[0]['id']
            
            # 매물-중개사 관계 저장
            property_realtor = {
                'property_id': property_id,
                'realtor_id': realtor_id,
                'listing_date': date.today().isoformat(),
                'is_primary': True,
                'contact_phone': realtor_info.get('mobile_number'),
                'contact_person': realtor_info.get('realtor_name')
            }
            
            self.client.table('property_realtors').insert(property_realtor).execute()
            self.stats['realtors_processed'] += 1
            
        except Exception as e:
            print(f"⚠️ 중개사 정보 저장 실패: {e}")
            print(f"🔍 DEBUG: realtor_info={realtor_info}")
            if 'new_realtor' in locals():
                print(f"🔍 DEBUG: realtor_data={realtor_data}")
            import traceback
            print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    def _save_property_images(self, property_id: int, data: Dict):
        """이미지 정보 저장"""
        try:
            photo_info = data['photo_info']
            
            if not photo_info['photos']:
                return
            
            images = []
            for photo in photo_info['photos']:
                def safe_int_for_image(value):
                    """이미지용 안전 정수 변환"""
                    if value is None or value == "" or value == "-":
                        return 0
                    try:
                        return int(float(str(value)))
                    except (ValueError, TypeError):
                        return 0
                
                # 필수 필드 검증: image_url이 없으면 스킵
                image_url = photo.get('image_url')
                if not image_url or image_url.strip() == "":
                    print(f"⚠️ 이미지 URL 없음 - 스킵")
                    continue
                
                image_type = photo.get('image_type')
                if not image_type or image_type.strip() == "":
                    print(f"⚠️ 이미지 타입 없음 - 스킵")
                    continue
                
                width = safe_int_for_image(photo.get('width'))
                height = safe_int_for_image(photo.get('height'))
                file_size = safe_int_for_image(photo.get('file_size'))
                
                image_data = {
                    'property_id': property_id,
                    'image_url': image_url.strip(),
                    'image_type': image_type.strip(),
                    'image_order': safe_int_for_image(photo.get('order', 0)),
                    'caption': photo.get('caption', ''),
                    'width': width,
                    'height': height,
                    'file_size': file_size,
                    'is_high_quality': width >= 800,
                    'captured_date': date.today().isoformat()
                }
                images.append(image_data)
            
            # 유효한 이미지가 있을 때만 DB에 저장
            if images:
                self.client.table('property_images').insert(images).execute()
                self.stats['images_collected'] += len(images)
                print(f"📷 {len(images)}개 이미지 저장 완료")
            else:
                print(f"📷 저장할 유효한 이미지 없음")
            
        except Exception as e:
            print(f"⚠️ 이미지 정보 저장 실패: {e}")
    
    def _save_property_facilities(self, property_id: int, data: Dict):
        """시설 정보 저장 - 완전한 시설 매핑"""
        try:
            facility_info = data['facility_info']
            
            # 시설 유형 매핑 (완전한 매핑으로 확장)
            facility_mapping = {
                'elevator': 1,         # ELEVATOR
                'parking': 2,          # PARKING  
                'air_conditioner': 7,  # AIR_CON
                'internet': 8,         # INTERNET
                'cable_tv': 9,         # CABLE_TV
                'security_system': 4,  # SECURITY
                'interphone': 6,       # INTERCOM
                'fire_alarm': 10,      # FIRE_ALARM
                'water_purifier': 11,  # WATER_PURIFIER
                'gas_range': 12,       # GAS_RANGE
                'induction': 13,       # INDUCTION
                'microwave': 14,       # MICROWAVE
                'refrigerator': 15,    # REFRIGERATOR
                'washing_machine': 16, # WASHING_MACHINE
                'dish_washer': 17,     # DISH_WASHER
                'shoe_closet': 18,     # SHOE_CLOSET
                'full_option': 19      # FULL_OPTION
            }
            
            facilities = []
            for facility_name, available in facility_info['facilities'].items():
                if available and facility_name in facility_mapping:
                    facility_data = {
                        'property_id': property_id,
                        'facility_id': facility_mapping[facility_name],
                        'available': True,
                        'condition_grade': 5,  # 기본값
                        'last_checked': date.today().isoformat()
                    }
                    facilities.append(facility_data)
            
            if facilities:
                self.client.table('property_facilities').insert(facilities).execute()
                self.stats['facilities_mapped'] += len(facilities)
                
        except Exception as e:
            print(f"⚠️ 시설 정보 저장 실패: {e}")
            print(f"🔍 DEBUG: facility_info={facility_info}")
            if facilities:
                print(f"🔍 DEBUG: facilities_to_save={facilities}")
            import traceback
            print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    def _save_property_tax_info(self, property_id: int, data: Dict):
        """세금 정보 저장 (새로 추가된 메서드)"""
        try:
            tax_info = data.get('tax_info', {})
            
            # 유효한 세금 정보가 없으면 스킵
            if not tax_info or not any(value is not None for value in tax_info.values()):
                return
            
            # 세금 정보를 별도 테이블에 저장 (property_taxes)
            tax_data = {
                'property_id': property_id,
                'acquisition_tax': tax_info.get('acquisition_tax'),
                'acquisition_tax_rate': tax_info.get('acquisition_tax_rate'),
                'registration_tax': tax_info.get('registration_tax'),
                'registration_tax_rate': tax_info.get('registration_tax_rate'),
                'brokerage_fee': tax_info.get('brokerage_fee'),
                'brokerage_fee_rate': tax_info.get('brokerage_fee_rate'),
                'stamp_duty': tax_info.get('stamp_duty'),
                'vat': tax_info.get('vat'),
                'total_tax': tax_info.get('total_tax'),
                'total_cost': tax_info.get('total_cost'),
                'calculated_date': date.today().isoformat()
            }
            
            # NULL 값만 있는 레코드는 저장하지 않음
            non_null_values = {k: v for k, v in tax_data.items() 
                             if v is not None and k not in ['property_id', 'calculated_date']}
            
            if non_null_values:
                self.client.table('property_tax_info').insert(tax_data).execute()
                tax_summary = ', '.join([f"{k.replace('_', ' ')}: {v}" for k, v in non_null_values.items() if isinstance(v, (int, float))])
                print(f"💰 세금정보 저장: {tax_summary}")
                self.stats['tax_info_saved'] += 1  # 통계 업데이트
            
        except Exception as e:
            print(f"⚠️ 세금 정보 저장 실패: {e}")
            print(f"🔍 DEBUG: tax_info={tax_info}")
            if 'tax_data' in locals():
                print(f"🔍 DEBUG: tax_data={tax_data}")
            import traceback
            print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    def _save_property_price_comparison(self, property_id: int, data: Dict):
        """가격 비교 정보 저장 (새로 추가된 메서드 - articleAddition 섹션)"""
        try:
            additional_info = data.get('additional_info', {})
            
            # 가격 비교 데이터가 없으면 스킵
            same_addr_count = additional_info.get('same_addr_count', 0)
            if same_addr_count == 0:
                return
            
            price_comparison_data = {
                'property_id': property_id,
                'same_addr_count': same_addr_count,
                'same_addr_max_price': additional_info.get('same_addr_max_price'),
                'same_addr_min_price': additional_info.get('same_addr_min_price'),
                'cpid': additional_info.get('cpid'),
                'complex_name': additional_info.get('complex_name'),
                'article_feature_desc': additional_info.get('article_feature_desc'),
                'market_data_date': date.today().isoformat()
            }
            
            # 유효한 가격 정보가 있을 때만 저장
            has_price_data = (price_comparison_data['same_addr_max_price'] is not None or 
                            price_comparison_data['same_addr_min_price'] is not None)
            
            if has_price_data:
                self.client.table('property_price_comparison').insert(price_comparison_data).execute()
                
                max_price = price_comparison_data.get('same_addr_max_price')
                min_price = price_comparison_data.get('same_addr_min_price')
                price_range = f"{min_price:,}~{max_price:,}만원" if max_price and min_price else "가격정보"
                print(f"📊 시세비교 저장: {same_addr_count}개 매물, 시세범위 {price_range}")
                self.stats['price_comparisons_saved'] += 1  # 통계 업데이트
            
        except Exception as e:
            print(f"⚠️ 가격 비교 정보 저장 실패: {e}")
    
    def _resolve_real_estate_type_id(self, data: Dict) -> Optional[int]:
        """수정된 부동산 유형 ID 조회 - NULL 반환 방지 (CRITICAL FIX)"""
        try:
            # 1. 다양한 소스에서 부동산 유형 추출
            real_estate_type = None
            
            # raw_sections 우선
            raw_sections = data.get('raw_sections', {})
            if 'articleDetail' in raw_sections:
                detail = raw_sections['articleDetail']
                real_estate_type = (detail.get('realEstateTypeName') or 
                                  detail.get('buildingUse') or
                                  detail.get('lawUsage'))
            
            # basic_info에서 추가 시도
            if not real_estate_type:
                basic_info = data.get('basic_info', {})
                real_estate_type = basic_info.get('building_use')
                
            # 마지막 수단: 알 수 없음으로 설정 (NULL 방지!)
            if not real_estate_type or real_estate_type.strip() == '':
                real_estate_type = "알 수 없음"
                print(f"⚠️ 부동산 유형 미확인 → '알 수 없음' 사용: {data.get('article_no', 'N/A')}")
            
            # 데이터베이스에서 조회
            existing = self.client.table('real_estate_types').select('id').eq('type_name', real_estate_type).execute()
            
            if existing.data:
                return existing.data[0]['id']
            else:
                # CRITICAL: '알 수 없음' 타입이 없으면 생성
                if real_estate_type == "알 수 없음":
                    fallback_type = {
                        'type_code': 'UNKNOWN',
                        'type_name': '알 수 없음',
                        'category': 'unknown',
                        'is_active': True
                    }
                else:
                    # 새로운 유형 자동 생성
                    type_code = real_estate_type[:8].upper().replace(' ', '_')
                    fallback_type = {
                        'type_code': type_code,
                        'type_name': real_estate_type,
                        'category': self._classify_real_estate_type(real_estate_type),
                        'is_active': True
                    }
                
                result = self.client.table('real_estate_types').insert(fallback_type).execute()
                if result.data:
                    new_id = result.data[0]['id']
                    print(f"✨ 새 부동산 유형 생성: {real_estate_type} (ID: {new_id})")
                    return new_id
                else:
                    print(f"❌ 부동산 유형 생성 실패: {real_estate_type}")
                    # 최후의 수단: ID=1 (첫 번째 유형) 반환
                    return 1
                    
        except Exception as e:
            print(f"❌ 부동산 유형 ID 조회 중 오류: {e}")
            print(f"🚨 FALLBACK: ID=1 (기본 유형) 반환")
            return 1  # NULL 대신 기본값 반환
    
    def _resolve_trade_type_id(self, data: Dict) -> Optional[int]:
        """거래 유형 ID 조회/생성 (캐싱 최적화 버전)"""
        try:
            # Naver API에서 거래 유형 추출
            trade_type = None
            
            # 1. raw_sections에서 추출
            raw_sections = data.get('raw_sections', {})
            if 'articlePrice' in raw_sections:
                price_info = raw_sections['articlePrice']
                trade_type = price_info.get('tradeTypeName')
            
            # 2. price_info에서 추출
            if not trade_type:
                price_info = data.get('price_info', {})
                if price_info.get('deal_price'):
                    trade_type = "매매"
                elif price_info.get('rent_price'):
                    trade_type = "월세"
                elif price_info.get('warrant_price'):
                    trade_type = "전세"
            
            # 3. 기본값 설정
            if not trade_type:
                trade_type = "알 수 없음"
                print(f"⚠️ 거래 유형을 찾을 수 없음 - 기본값 사용: {data['article_no']}")
            
            # 🚀 OPTIMIZATION: 캐시 확인
            if hasattr(self, 'cache_manager') and self.cache_manager:
                cached_id = self.cache_manager.get_foreign_key_lookup(
                    'trade_types', 'type_name', trade_type
                )
                if cached_id:
                    return cached_id
            
            # 데이터베이스 조회
            existing = self.client.table('trade_types').select('id').eq('type_name', trade_type).execute()
            
            if existing.data:
                result_id = existing.data[0]['id']
                # 캐시에 저장
                if hasattr(self, 'cache_manager') and self.cache_manager:
                    self.cache_manager.cache_foreign_key_lookup(
                        'trade_types', 'type_name', trade_type, result_id
                    )
                return result_id
            else:
                # 새로운 거래 유형 생성
                type_code = trade_type[:10].upper().replace(' ', '_').replace('알', 'UNKNOWN')
                requires_deposit = trade_type in ['전세', '월세', '단기임대']
                
                new_type = {
                    'type_code': type_code,
                    'type_name': trade_type,
                    'requires_deposit': requires_deposit
                }
                
                result = self.client.table('trade_types').insert(new_type).execute()
                result_id = result.data[0]['id']
                
                # 새로 생성된 ID 캐시에 저장
                if hasattr(self, 'cache_manager') and self.cache_manager:
                    self.cache_manager.cache_foreign_key_lookup(
                        'trade_types', 'type_name', trade_type, result_id
                    )
                
                print(f"✨ 새 거래 유형 생성: {trade_type} (ID: {result_id})")
                return result_id
                
        except Exception as e:
            print(f"❌ 거래 유형 ID 조회 실패: {e}")
            print(f"🚨 FALLBACK: ID=1 (기본 거래유형) 반환")
            return 1  # NULL 대신 기본값 반환
    
    def _resolve_region_id(self, data: Dict) -> Optional[int]:
        """지역 ID 조회/생성 (캐싱 최적화 버전)"""
        try:
            # 위치 정보에서 cortar_no 추출
            cortar_no = None
            
            # 1. basic_info에서 추출
            basic_info = data.get('basic_info', {})
            # 좌표로부터 지역 추정 (향후 구현)
            
            # 2. raw_sections에서 추출
            raw_sections = data.get('raw_sections', {})
            if 'articleDetail' in raw_sections:
                detail = raw_sections['articleDetail']
                cortar_no = detail.get('cortarNo')
            
            # 3. NULL 방지 기본값 설정
            if not cortar_no or cortar_no.strip() == '':
                cortar_no = "UNKNOWN"
                print(f"⚠️ 지역 정보 미확인 → 'UNKNOWN' 사용: {data.get('article_no', 'N/A')}")
            
            # 🚀 OPTIMIZATION: 캐시 확인
            if hasattr(self, 'cache_manager') and self.cache_manager:
                cached_id = self.cache_manager.get_foreign_key_lookup(
                    'regions', 'cortar_no', cortar_no
                )
                if cached_id:
                    return cached_id
            
            # 데이터베이스 조회
            existing = self.client.table('regions').select('id').eq('cortar_no', cortar_no).execute()
            
            if existing.data:
                result_id = existing.data[0]['id']
                # 캐시에 저장
                if hasattr(self, 'cache_manager') and self.cache_manager:
                    self.cache_manager.cache_foreign_key_lookup(
                        'regions', 'cortar_no', cortar_no, result_id
                    )
                return result_id
            else:
                # 새로운 지역 생성
                dong_name = f"지역_{cortar_no}"
                gu_name = "강남구"  # 임시 기본값
                
                new_region = {
                    'cortar_no': cortar_no,
                    'dong_name': dong_name,
                    'gu_name': gu_name
                }
                
                result = self.client.table('regions').insert(new_region).execute()
                result_id = result.data[0]['id']
                
                # 새로 생성된 ID 캐시에 저장
                if hasattr(self, 'cache_manager') and self.cache_manager:
                    self.cache_manager.cache_foreign_key_lookup(
                        'regions', 'cortar_no', cortar_no, result_id
                    )
                
                print(f"✨ 새 지역 생성: {dong_name} (ID: {result_id})")
                return result_id
                
        except Exception as e:
            print(f"❌ 지역 ID 조회 실패: {e}")
            print(f"🚨 FALLBACK: UNKNOWN 지역 ID 찾기 시도")
            # 최후의 수단으로 UNKNOWN 지역 ID 찾기
            try:
                unknown_region = self.client.table('regions').select('id').eq('cortar_no', 'UNKNOWN').execute()
                return unknown_region.data[0]['id'] if unknown_region.data else 1
            except:
                return 1  # 정말 마지막 수단
    
    def _classify_real_estate_type(self, type_name: str) -> str:
        """부동산 유형 분류"""
        type_name_lower = type_name.lower()
        if any(keyword in type_name_lower for keyword in ['아파트', '빌라', '주택', '다세대']):
            return 'residential'
        elif any(keyword in type_name_lower for keyword in ['상가', '사무실', '건물', '매장']):
            return 'commercial'
        elif '오피스텔' in type_name_lower:
            return 'mixed'
        elif '공장' in type_name_lower:
            return 'industrial'
        elif '토지' in type_name_lower:
            return 'land'
        else:
            return 'other'
    
    def collect_area_articles(self, cortar_no: str, max_pages: int = None) -> List[str]:
        """지역별 매물 목록 수집"""
        # 올바른 네이버 API URL 사용 (기존 동작하는 수집기와 동일)
        url = "https://new.land.naver.com/api/articles"
        all_articles = []
        
        page = 1
        while max_pages is None or page <= max_pages:
            # 기존 검증된 수집기와 동일한 파라미터 사용
            params = {
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
                'page': page,
                'pageSize': 20
            }
            
            try:
                headers = self.setup_headers()
                time.sleep(random.uniform(0.5, 1.0))
                
                response = requests.get(url, headers=headers, params=params, 
                                      cookies=self.cookies, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articleList', [])
                    is_more_data = data.get('isMoreData', False)
                    
                    if not articles:
                        print(f"📄 {page}페이지: 더 이상 매물 없음")
                        break
                        
                    article_nos = [article['articleNo'] for article in articles]
                    all_articles.extend(article_nos)
                    print(f"📄 {page}페이지: {len(article_nos)}개 매물")
                    
                    # API가 더 이상 데이터가 없다고 알려주면 중단
                    if not is_more_data:
                        print(f"📄 API에서 더 이상 데이터가 없다고 응답 (isMoreData: {is_more_data})")
                        break
                    
                else:
                    print(f"⚠️ {page}페이지 조회 실패: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"❌ {page}페이지 오류: {e}")
                break
            
            page += 1  # 다음 페이지로
        
        return all_articles
    
    def collect_single_page_articles(self, cortar_no: str, page: int) -> List[str]:
        """단일 페이지 매물 목록 수집 - 메모리 효율적인 배치 처리용"""
        url = "https://new.land.naver.com/api/articles"
        
        params = {
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
            'page': page,
            'pageSize': 20
        }
        
        try:
            headers = self.setup_headers()
            time.sleep(random.uniform(0.5, 1.0))
            
            response = requests.get(url, headers=headers, params=params, 
                                  cookies=self.cookies, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articleList', [])
                is_more_data = data.get('isMoreData', False)
                
                if not articles:
                    return []
                    
                article_nos = [article['articleNo'] for article in articles]
                return article_nos
                
            else:
                print(f"⚠️ {page}페이지 조회 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ {page}페이지 오류: {e}")
            return []
    
    def collect_gangnam_all_enhanced(self, gangnam_dongs: List[Dict]):
        """강남구 전체 8개 섹션 완전 수집 - 배치 처리 방식"""
        total_properties = 0
        
        for dong_info in gangnam_dongs:
            dong_name = dong_info["name"]
            cortar_no = dong_info["cortar_no"]
            
            print(f"\n🏠 {dong_name} 수집 시작...")
            
            # 배치 방식으로 페이지별 즉시 처리
            dong_success = 0
            page = 1
            total_articles_in_dong = 0
            
            while True:
                print(f"\n📄 {dong_name} {page}페이지 처리 중...")
                
                # 1. 한 페이지 매물 목록 수집
                page_articles = self.collect_single_page_articles(cortar_no, page)
                
                if not page_articles:
                    print(f"📄 {page}페이지: 더 이상 매물 없음")
                    break
                
                print(f"📄 {page}페이지: {len(page_articles)}개 매물 → 즉시 상세 수집 시작")
                total_articles_in_dong += len(page_articles)
                
                # 2. 이 페이지 매물들의 8개 섹션 즉시 수집
                page_success = 0
                for i, article_no in enumerate(page_articles, 1):
                    print(f"🔍 [{i}/{len(page_articles)}] P{page} 매물 {article_no} 상세 수집...")
                    
                    # 8개 섹션 완전 수집
                    enhanced_data = self.collect_article_detail_enhanced(article_no)
                    
                    if enhanced_data:
                        # 정규화된 DB에 저장
                        save_result = self.save_to_normalized_database(enhanced_data)
                        if save_result:
                            page_success += 1
                            dong_success += 1
                            total_properties += 1
                            print(f"✅ 매물 {article_no} DB 저장 성공!")
                        else:
                            print(f"❌ 매물 {article_no} DB 저장 실패!")
                    else:
                        print(f"❌ 매물 {article_no} 데이터 수집 실패!")
                    
                    # 적절한 딜레이
                    time.sleep(random.uniform(1.5, 2.5))
                
                print(f"✅ {dong_name} P{page} 완료: {page_success}/{len(page_articles)}개 성공")
                
                # 진행 상황 체크포인트
                if page % 10 == 0:
                    print(f"🔖 체크포인트: {dong_name} {page}페이지까지 완료 (총 {dong_success}개 수집)")
                
                page += 1
                
                # 안전장치: 너무 많은 페이지 방지
                if page > 1000:
                    print(f"⚠️ {dong_name} 1000페이지 도달 - 수집 중단")
                    break
            
            print(f"✅ {dong_name} 전체 완료: {dong_success}/{total_articles_in_dong}개 성공 (총 {page-1}페이지)")
        
        print(f"\n🎉 강남구 전체 수집 완료!")
        print(f"📊 총 수집 매물: {total_properties}개")
        self.print_collection_stats()

    def print_collection_stats(self):
        """수집 통계 출력"""
        print("\n" + "="*60)
        print("📊 향상된 데이터 수집 통계")
        print("="*60)
        print(f"✅ 처리된 매물: {self.stats.get('properties_processed', 0):,}개")
        print(f"📷 수집된 이미지: {self.stats.get('images_collected', 0):,}개")
        print(f"🏢 처리된 중개사: {self.stats.get('realtors_processed', 0):,}개")
        print(f"🔧 매핑된 시설: {self.stats.get('facilities_mapped', 0):,}개")
        print(f"💰 저장된 세금정보: {self.stats.get('tax_info_saved', 0):,}개")
        print(f"📊 저장된 시세비교: {self.stats.get('price_comparisons_saved', 0):,}개")
        print(f"🗺️ 카카오 주소 변환: {self.stats.get('addresses_enriched', 0):,}개")
        print(f"❌ 오류 발생: {self.stats.get('errors', 0):,}개")
        
        # 카카오 변환 성공률 표시
        properties_processed = self.stats.get('properties_processed', 0)
        addresses_enriched = self.stats.get('addresses_enriched', 0)
        if properties_processed > 0:
            success_rate = (addresses_enriched / properties_processed) * 100
            print(f"📈 주소 변환 성공률: {success_rate:.1f}%")
        
        # 파싱 실패 통계
        parsing_failures = self.stats.get('parsing_failures', {})
        total_parsing_failures = sum(parsing_failures.values())
        if total_parsing_failures > 0:
            print(f"\n⚠️ 파싱 실패 통계 (총 {total_parsing_failures}개):")
            for section, count in parsing_failures.items():
                if count > 0:
                    print(f"   - {section}: {count}개")
            print(f"📄 상세 로그 파일: {self.parsing_log_file}")
        
        print("="*60)

def main():
    """테스트용 메인 함수"""
    print("🚀 향상된 네이버 부동산 수집기 테스트")
    print("="*50)
    
    collector = EnhancedNaverCollector()
    
    # 강남구 전체 수집
    print("🏢 강남구 전체 매물 8개 섹션 완전 수집 시작...")
    
    # 기존 log_based_collector의 동 정보 활용
    gangnam_dongs = [
        {"name": "역삼동", "cortar_no": "1168010100"},
        {"name": "삼성동", "cortar_no": "1168010500"}, 
        {"name": "논현동", "cortar_no": "1168010800"},
        {"name": "대치동", "cortar_no": "1168010600"},
        {"name": "신사동", "cortar_no": "1168010700"},
        {"name": "압구정동", "cortar_no": "1168011000"},
        {"name": "청담동", "cortar_no": "1168010400"},
        {"name": "도곡동", "cortar_no": "1168011800"},
        {"name": "개포동", "cortar_no": "1168010300"},
        {"name": "수서동", "cortar_no": "1168011500"},
        {"name": "일원동", "cortar_no": "1168011400"},
        {"name": "자곡동", "cortar_no": "1168011200"},
        {"name": "세곡동", "cortar_no": "1168011100"},
        {"name": "율현동", "cortar_no": "1168011300"}
    ]
    
    collector.collect_gangnam_all_enhanced(gangnam_dongs)

if __name__ == "__main__":
    main()