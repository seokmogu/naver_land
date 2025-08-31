#!/usr/bin/env python3
"""
네이버 부동산 매물 데이터 파싱기
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

class ArticleParser:
    def __init__(self):
        self.parsing_errors = []
    
    def parse_article_detail(self, raw_data: Dict, article_no: str) -> Optional[Dict]:
        try:
            if not raw_data or 'articleDetail' not in raw_data:
                return None
                
            parsed = {
                'article_no': article_no,
                'parsing_timestamp': datetime.now().isoformat(),
                'sections': {}
            }
            
            # 먼저 모든 섹션 파싱
            for section_name, section_data in raw_data.items():
                if section_data:
                    parser_method = getattr(self, f'_parse_{section_name}', None)
                    if parser_method:
                        parsed['sections'][section_name] = parser_method(section_data, article_no)
                    else:
                        parsed['sections'][section_name] = section_data
            
            # 크로스 섹션 데이터 매핑 - articleDetail의 None 필드들을 다른 섹션에서 채움
            self._fill_cross_section_data(parsed['sections'])
            
            return parsed
            
        except Exception as e:
            self._log_parsing_error('article_detail', article_no, str(e), raw_data)
            return None
    
    def _parse_articleDetail(self, data: Dict, article_no: str) -> Dict:
        return {
            'article_no': self._safe_extract(data, 'articleNo', str),
            'real_estate_type': self._safe_extract(data, 'realestateTypeName', str),
            'trade_type': self._safe_extract(data, 'tradeTypeName', str),
            'floor_info': self._safe_extract(data, 'floorLayerName', str),
            'building_name': self._safe_extract(data, 'buildingTypeName', str),
            'deal_or_warrant_price': None,  # articlePrice 섹션에서 처리
            'rent_price': None,  # articlePrice 섹션에서 처리
            'space_size': None,  # articleSpace 섹션에서 처리
            'supply_size': None,  # articleSpace 섹션에서 처리
            'direction': None,  # articleFacility 섹션에서 처리
            'construction_completion_date': self._safe_extract(data, 'moveInPossibleYmd', str),
            'manage_cost': self._safe_extract(data, 'monthlyManagementCost', int),
            'tags': self._safe_extract(data, 'tagList', list, []),
            'latitude': self._safe_extract(data, 'latitude', str),
            'longitude': self._safe_extract(data, 'longitude', str),
            'law_usage': self._safe_extract(data, 'lawUsage', str),
            'exposure_address': self._safe_extract(data, 'exposureAddress', str),
            'detail_address': self._safe_extract(data, 'detailAddress', str),
            'detail_description': self._safe_extract(data, 'detailDescription', str),
            'parking_count': self._safe_extract(data, 'parkingCount', int),
            'parking_possible': self._safe_extract(data, 'parkingPossibleYN', str),
            'walking_to_subway': self._safe_extract(data, 'walkingTimeToNearSubway', int),
            'move_in_type': self._safe_extract(data, 'moveInTypeName', str),
            # 실제 API 응답에 없는 필드들 - 다른 섹션에서 가져올 것
            'elevator_count': None,  # articleFacility에서 처리
            'management_office_tel': None,  # 실제 필드명을 찾지 못함
        }
    
    def _parse_articleAddition(self, data: Dict, article_no: str) -> Dict:
        return {
            'same_address_direct_deal': self._safe_extract(data, 'sameAddrDirectCnt', int, 0),
            'same_address_hash': self._safe_extract(data, 'sameAddrHash', str),
            'price_by_area': self._safe_extract(data, 'prcPerSpace', str),
            'nearby_sales': self._parse_price_comparison(data.get('prcInfo', {}))
        }
    
    def _parse_articleFacility(self, data: Dict, article_no: str) -> Dict:
        # etcFacilities에서 엘리베이터 정보 추출
        etc_facilities = self._safe_extract(data, 'etcFacilities', list, [])
        elevator_count = 1 if '엘리베이터' in etc_facilities else None
        
        return {
            'near_subway': self._parse_subway_list(data.get('subwayList', [])),
            'convenience_facilities': self._safe_extract(data, 'airconFacilities', list, []),
            'security_facilities': self._safe_extract(data, 'securityFacilities', list, []),
            'direction': self._safe_extract(data, 'directionTypeName', str),
            'heat_method': self._safe_extract(data, 'heatMethodTypeName', str),
            'elevator_count': elevator_count,  # 엘리베이터 정보 추가
            'etc_facilities': etc_facilities  # 기타 편의시설 목록 추가
        }
    
    def _parse_articleFloor(self, data: Dict, article_no: str) -> Dict:
        total_floor = self._safe_extract(data, 'totalFloorCount', int)
        
        # correspondingFloorCount는 "B1", "1", "2" 등의 형식으로 올 수 있음
        current_floor_raw = self._safe_extract(data, 'correspondingFloorCount', str)
        current_floor = self._parse_floor_number(current_floor_raw)
        
        # floor_description 생성 (5층/20층 형식)
        floor_description = None
        if current_floor_raw and total_floor:
            floor_description = f"{current_floor_raw}/{total_floor}층"
        elif current_floor_raw:
            floor_description = f"{current_floor_raw}층"
            
        return {
            'total_floor': total_floor,
            'current_floor': current_floor,
            'current_floor_raw': current_floor_raw,  # 원본 층수 문자열
            'underground_floor': self._safe_extract(data, 'undergroundFloorCount', str),
            'aboveground_floor': self._safe_extract(data, 'uppergroundFloorCount', str),
            'floor_description': floor_description  # 생성된 층수 설명
        }
    
    def _parse_articlePrice(self, data: Dict, article_no: str) -> Dict:
        return {
            'deal_price': self._safe_extract(data, 'dealPrice', int, 0),  # 기본값 0
            'warrant_price': self._safe_extract(data, 'warrantPrice', int, 0),  # 기본값 0 
            'rent_price': self._safe_extract(data, 'rentPrice', int, 0),  # 기본값 0
            'manage_cost': None,  # 별도 필드 없음, articleDetail에서 처리
            'price_per_area': self._safe_extract(data, 'priceBySpace', float, 0.0),  # 기본값 0.0
            'all_warrant_price': self._safe_extract(data, 'allWarrantPrice', int, 0),  # 추가 필드
            'all_rent_price': self._safe_extract(data, 'allRentPrice', int, 0),  # 추가 필드
            'finance_price': self._safe_extract(data, 'financePrice', int, 0),  # 추가 필드
            'premium_price': self._safe_extract(data, 'premiumPrice', int, 0),  # 추가 필드
        }
    
    def _parse_articleRealtor(self, data: Dict, article_no: str) -> Dict:
        return {
            'office_name': self._safe_extract(data, 'address', str),  # 수정됨 
            'agent_name': self._safe_extract(data, 'realtorName', str),  # 이미 올바름
            'phone_number': self._safe_extract(data, 'representativeTelNo', str),  # 수정됨
            'office_certified': False,  # 별도 필드 없음
            'representative_mobile': self._safe_extract(data, 'cellPhoneNo', str)  # 수정됨
        }
    
    def _parse_articleSpace(self, data: Dict, article_no: str) -> Dict:
        return {
            'supply_area': self._safe_extract(data, 'supplySpace', float),
            'exclusive_area': self._safe_extract(data, 'exclusiveSpace', float),
            'common_area': self._safe_extract(data, 'groundShareSpace', float, 0.0),  # 기본값 0.0
            'total_area': self._safe_extract(data, 'totalSpace', float, 0.0),  # 기본값 0.0
            'building_area': self._safe_extract(data, 'buildingSpace', float, 0.0),  # 기본값 0.0
            'ground_space': self._safe_extract(data, 'groundSpace', float, 0.0),  # 추가 필드
            'expect_space': self._safe_extract(data, 'expectSpace', float, 0.0),  # 추가 필드
            'exclusive_rate': self._safe_extract(data, 'exclusiveRate', str)
        }
    
    def _parse_articleTax(self, data: Dict, article_no: str) -> Dict:
        return {
            'acquisition_tax': self._safe_extract(data, 'acquisitionTax', int, 0),  # 기본값 0
            'brokerage_fee': self._safe_extract(data, 'brokerFee', float, 0.0),  # 기본값 0.0
            'etc_cost': self._safe_extract(data, 'registFee', float, 0.0),  # 기본값 0.0
            'regist_tax': self._safe_extract(data, 'registTax', float, 0.0),  # 추가 필드
            'total_price': self._safe_extract(data, 'totalPrice', int, 0),  # 추가 필드
            'max_broker_fee': self._safe_extract(data, 'maxBrokerFee', float, 0.0),  # 추가 필드
        }
    
    def _parse_articlePhotos(self, data: List[Dict], article_no: str) -> Dict:
        photos = []
        for photo in data:
            # imageSrc가 실제 API 필드명
            image_url = self._safe_extract(photo, 'imageSrc', str)
            if image_url:  # null, 빈 문자열, None 필터링
                photos.append({
                    'url': image_url,
                    'thumbnail_url': self._safe_extract(photo, 'thumbnailUrl', str),
                    'description': self._safe_extract(photo, 'smallCategoryName', str),
                    'order': self._safe_extract(photo, 'imageOrder', int),
                    'image_type': self._safe_extract(photo, 'imageType', str),
                    'image_id': self._safe_extract(photo, 'imageId', str)
                })
        return {'photos': photos, 'total_count': len(photos)}
    
    def _parse_subway_list(self, subway_list: List[Dict]) -> List[Dict]:
        parsed_subways = []
        for subway in subway_list:
            parsed_subways.append({
                'line_name': self._safe_extract(subway, 'subwayName', str),
                'station_name': self._safe_extract(subway, 'stationName', str),
                'distance': self._safe_extract(subway, 'distance', int),
                'walking_time': self._safe_extract(subway, 'walkingTime', int)
            })
        return parsed_subways
    
    def _parse_price_comparison(self, price_info: Dict) -> Dict:
        return {
            'lower_price_count': self._safe_extract(price_info, 'lowerPrcCnt', int, 0),
            'similar_price_count': self._safe_extract(price_info, 'samePrcCnt', int, 0),
            'higher_price_count': self._safe_extract(price_info, 'higherPrcCnt', int, 0)
        }
    
    def _fill_cross_section_data(self, sections: Dict):
        """다른 섹션의 데이터를 articleDetail의 NULL 필드에 채움"""
        if 'articleDetail' not in sections:
            return
        
        article_detail = sections['articleDetail']
        article_price = sections.get('articlePrice', {})
        article_space = sections.get('articleSpace', {})
        article_facility = sections.get('articleFacility', {})
        
        # direction: articleFacility에서 가져오기
        if article_detail.get('direction') is None and article_facility.get('direction'):
            article_detail['direction'] = article_facility['direction']
        
        # elevator_count: articleFacility에서 가져오기
        if article_detail.get('elevator_count') is None and article_facility.get('elevator_count'):
            article_detail['elevator_count'] = article_facility['elevator_count']
        
        # space_size, supply_size: articleSpace에서 가져오기
        if article_detail.get('space_size') is None and article_space.get('supply_area'):
            article_detail['space_size'] = article_space['supply_area']
        
        if article_detail.get('supply_size') is None and article_space.get('exclusive_area'):
            article_detail['supply_size'] = article_space['exclusive_area']
        
        # deal_or_warrant_price, rent_price: articlePrice에서 가져오기
        if article_detail.get('deal_or_warrant_price') is None:
            if article_price.get('deal_price', 0) > 0:
                article_detail['deal_or_warrant_price'] = article_price['deal_price']
            elif article_price.get('warrant_price', 0) > 0:
                article_detail['deal_or_warrant_price'] = article_price['warrant_price']
        
        if article_detail.get('rent_price') is None and article_price.get('rent_price'):
            article_detail['rent_price'] = article_price['rent_price']
        
        # manage_cost: articleDetail에서 articlePrice로 복사
        if article_price.get('manage_cost') is None and article_detail.get('manage_cost'):
            article_price['manage_cost'] = article_detail['manage_cost']
        
        # building_use: real_estate_type을 building_use에 복사
        if article_detail.get('building_use') is None and article_detail.get('real_estate_type'):
            article_detail['building_use'] = article_detail['real_estate_type']
        
        # deal_price가 0이거나 None일 때 월세 매물의 경우 warrant_price를 deal_price에 설정
        if article_price.get('deal_price', 0) == 0 and article_price.get('warrant_price', 0) > 0:
            # 월세 매물의 경우 보증금을 deal_price에도 저장 (호환성을 위해)
            article_price['deal_price'] = article_price['warrant_price']

    def _parse_floor_number(self, floor_str: str) -> Optional[int]:
        """층수 문자열을 정수로 변환 (B1 -> -1, 1 -> 1 등)"""
        if not floor_str:
            return None
            
        try:
            # 지하층 처리 (B1, B2 등)
            if floor_str.upper().startswith('B'):
                floor_num = floor_str[1:]  # B 제거
                return -int(floor_num) if floor_num.isdigit() else None
            
            # 일반 층수 처리
            if floor_str.isdigit():
                return int(floor_str)
                
            # 기타 경우는 None 반환
            return None
            
        except (ValueError, TypeError):
            return None
    
    def _safe_extract(self, data: Dict, key: str, data_type: type = str, default: Any = None) -> Any:
        try:
            value = data.get(key, default)
            if value is None or (isinstance(value, str) and value == ''):
                return default
            
            if data_type == str:
                return str(value).strip() if value is not None else default
            elif data_type == int:
                if isinstance(value, (int, float)):
                    return int(value)
                elif isinstance(value, str) and value.replace('-', '').replace('.', '').isdigit():
                    return int(float(value))
                else:
                    return default
            elif data_type == float:
                if isinstance(value, (int, float)):
                    return float(value)  # 0.0도 유효한 값으로 처리
                elif isinstance(value, str) and value.replace('-', '').replace('.', '').isdigit():
                    return float(value)
                else:
                    return default
            elif data_type == bool:
                return bool(value)
            elif data_type == list:
                return list(value) if isinstance(value, list) else default
            else:
                return value
                
        except (ValueError, TypeError, AttributeError):
            return default
    
    def _log_parsing_error(self, section: str, article_no: str, error_msg: str, raw_data: Any = None):
        error_record = {
            'section': section,
            'article_no': article_no,
            'error': error_msg,
            'timestamp': datetime.now().isoformat(),
            'has_raw_data': raw_data is not None
        }
        self.parsing_errors.append(error_record)
        print(f"❌ Parsing error in {section} for article {article_no}: {error_msg}")
    
    def get_parsing_stats(self) -> Dict[str, Any]:
        return {
            'total_errors': len(self.parsing_errors),
            'errors_by_section': self._group_errors_by_section()
        }
    
    def _group_errors_by_section(self) -> Dict[str, int]:
        section_counts = {}
        for error in self.parsing_errors:
            section = error['section']
            section_counts[section] = section_counts.get(section, 0) + 1
        return section_counts