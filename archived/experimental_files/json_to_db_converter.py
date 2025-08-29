#!/usr/bin/env python3
"""
JSON 데이터를 Supabase DB 형식으로 변환하는 모듈

JSON 수집 데이터 구조를 properties 테이블 스키마에 맞게 변환합니다.
"""

import json
import re
from datetime import date, datetime
from typing import Dict, List, Any, Optional

def parse_price(price_input) -> Optional[int]:
    """
    가격을 숫자로 변환 (문자열 또는 숫자)
    
    Args:
        price_input: "1억 2,000만원", "5,000만원", 1000 (정수), 등
    
    Returns:
        int: 만원 단위 가격 (예: "1억 2,000만원" -> 12000)
        None: 파싱 실패시
    """
    # 이미 숫자인 경우 그대로 반환
    if isinstance(price_input, (int, float)):
        return int(price_input)
    
    # 문자열이 아닌 경우 문자열로 변환
    price_str = str(price_input) if price_input is not None else ''
    
    if not price_str or price_str == '-' or price_str == '' or price_str == 'None':
        return None
    
    try:
        # 숫자와 단위만 추출
        cleaned = re.sub(r'[^\d억만천백십원,]', '', price_str)
        
        total_value = 0
        
        # 억 단위 처리
        if '억' in cleaned:
            eok_match = re.search(r'(\d+)억', cleaned)
            if eok_match:
                total_value += int(eok_match.group(1)) * 10000  # 1억 = 10000만원
        
        # 만원 단위 처리
        if '만' in cleaned:
            man_match = re.search(r'(?:억\s*)?(\d+(?:,\d+)?)만', cleaned)
            if man_match:
                man_value = int(man_match.group(1).replace(',', ''))
                total_value += man_value
        
        # 만원 단위가 없고 숫자만 있는 경우 (원 단위)
        elif total_value == 0:
            number_match = re.search(r'(\d+(?:,\d+)*)', cleaned)
            if number_match:
                won_value = int(number_match.group(1).replace(',', ''))
                total_value = won_value // 10000  # 원을 만원으로 변환
        
        return total_value if total_value > 0 else None
        
    except (ValueError, AttributeError) as e:
        print(f"⚠️ 가격 파싱 오류: '{price_str}' -> {e}")
        return None

def parse_area(area_input) -> Optional[float]:
    """
    면적을 숫자로 변환 (문자열 또는 숫자)
    
    Args:
        area_input: "84.36㎡", "25평", 84.36 (숫자) 등
    
    Returns:
        float: 제곱미터 단위 면적
        None: 파싱 실패시
    """
    # 이미 숫자인 경우 그대로 반환
    if isinstance(area_input, (int, float)):
        return float(area_input)
    
    # 문자열이 아닌 경우 문자열로 변환
    area_str = str(area_input) if area_input is not None else ''
    
    if not area_str or area_str == '-' or area_str == '' or area_str == 'None':
        return None
    
    try:
        # 숫자만 추출
        number_match = re.search(r'(\d+(?:\.\d+)?)', area_str)
        if number_match:
            value = float(number_match.group(1))
            
            # 평 단위인 경우 제곱미터로 변환 (1평 = 3.3058㎡)
            if '평' in area_str:
                value = value * 3.3058
            
            return round(value, 2)
        
        return None
        
    except (ValueError, AttributeError):
        return None

def extract_floor_number(floor_info: str) -> Optional[int]:
    """층 정보에서 층수만 추출"""
    if not floor_info:
        return None
    
    try:
        # "3층/15층", "지하1층", "옥탑층" 등에서 숫자 추출
        floor_match = re.search(r'(\d+)층', floor_info)
        if floor_match:
            floor_num = int(floor_match.group(1))
            # 지하층 처리
            if '지하' in floor_info:
                floor_num = -floor_num
            return floor_num
        
        # 옥탑층 등 특수 케이스
        if '옥탑' in floor_info:
            return 99  # 옥탑층을 99층으로 표시
        
        return None
        
    except (ValueError, AttributeError):
        return None

def convert_property_to_db_format(property_data: Dict, cortar_no: str) -> Dict:
    """
    단일 매물 데이터를 DB 형식으로 변환
    
    Args:
        property_data: JSON 수집 데이터 중 한 매물
        cortar_no: 행정구역 코드
    
    Returns:
        Dict: DB 테이블에 맞는 형식의 데이터
    """
    
    # 기본 매물 정보
    article_no = property_data.get('매물번호', '')
    if not article_no:
        return None  # 매물번호가 없으면 None 반환
    
    db_property = {
        'article_no': str(article_no),
        'article_name': property_data.get('매물명', ''),
        'real_estate_type': property_data.get('부동산타입', ''),
        'trade_type': property_data.get('거래타입', ''),
        'cortar_no': cortar_no,
        'collected_date': date.today().isoformat(),
        'is_active': True,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    # 가격 정보 변환
    sale_price = property_data.get('매매가격', '')
    rent_price = property_data.get('월세', '')
    # deposit_price 컬럼이 없으므로 제거
    # deposit_price = property_data.get('전세보증금', '') or property_data.get('보증금', '')
    
    db_property['price'] = parse_price(sale_price)
    db_property['rent_price'] = parse_price(rent_price)
    # db_property['deposit_price'] = parse_price(deposit_price)
    
    # 면적 정보 변환
    db_property['area1'] = parse_area(property_data.get('전용면적', ''))
    db_property['area2'] = parse_area(property_data.get('공급면적', ''))
    
    # 층 정보 변환
    floor_info = property_data.get('층정보', '')
    db_property['floor_info'] = floor_info
    db_property['floor'] = extract_floor_number(floor_info)
    
    # 기타 정보
    db_property['direction'] = property_data.get('방향', '')
    db_property['tag_list'] = property_data.get('태그', [])
    db_property['description'] = property_data.get('설명', '')
    
    # 상세정보에서 추가 데이터 추출
    details = property_data.get('상세정보', {})
    if isinstance(details, dict):
        db_property['details'] = details
        
        # 카카오 주소 정보
        kakao_info = details.get('카카오주소변환', {})
        if kakao_info:
            db_property['address_road'] = kakao_info.get('도로명주소', '')
            db_property['address_jibun'] = kakao_info.get('지번주소', '')
            db_property['building_name'] = kakao_info.get('건물명', '')
            db_property['postal_code'] = kakao_info.get('우편번호', '')
        
        # 위치 정보
        location_info = details.get('위치정보', {})
        if location_info:
            try:
                lat = location_info.get('정확한_위도', '')
                lon = location_info.get('정확한_경도', '')
                if lat and lon:
                    db_property['latitude'] = float(lat)
                    db_property['longitude'] = float(lon)
            except (ValueError, TypeError):
                pass
        
        # 추가 상세정보
        if '방수' in details:
            db_property['room_count'] = details.get('방수')
        if '욕실수' in details:
            db_property['bathroom_count'] = details.get('욕실수')
        if '주차' in details:
            db_property['parking_info'] = details.get('주차')
        if '난방' in details:
            db_property['heating_type'] = details.get('난방')
        if '승인일' in details:
            db_property['approval_date'] = details.get('승인일')
    
    return db_property

def convert_json_to_properties(json_file_path: str, cortar_no: str) -> List[Dict]:
    """
    JSON 파일을 읽어서 properties 테이블 형식으로 변환
    
    Args:
        json_file_path: JSON 파일 경로
        cortar_no: 행정구역 코드
    
    Returns:
        List[Dict]: DB에 저장할 수 있는 형식의 매물 데이터 리스트
    """
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # JSON 구조 확인
        if 'collected_properties' in data:
            properties = data['collected_properties']
        elif '매물목록' in data:
            properties = data['매물목록']
        elif isinstance(data, list):
            properties = data
        else:
            print(f"⚠️ 알 수 없는 JSON 구조: {json_file_path}")
            print(f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            return []
        
        # 각 매물을 DB 형식으로 변환
        db_properties = []
        for property_data in properties:
            try:
                db_property = convert_property_to_db_format(property_data, cortar_no)
                
                # 변환 결과 검증
                if db_property and db_property.get('article_no'):
                    db_properties.append(db_property)
                else:
                    print(f"⚠️ 매물번호 누락으로 스킵")
                    
            except Exception as e:
                print(f"❌ 매물 변환 오류: {e}")
                continue
        
        print(f"✅ JSON 변환 완료: {len(db_properties)}개 매물")
        return db_properties
        
    except Exception as e:
        print(f"❌ JSON 파일 읽기 오류: {e}")
        return []

def convert_json_data_to_properties(json_data: Dict, cortar_no: str) -> List[Dict]:
    """
    메모리상의 JSON 데이터를 properties 테이블 형식으로 변환
    
    Args:
        json_data: 메모리상의 JSON 데이터
        cortar_no: 행정구역 코드
    
    Returns:
        List[Dict]: DB에 저장할 수 있는 형식의 매물 데이터 리스트
    """
    
    try:
        # JSON 구조 확인
        if 'collected_properties' in json_data:
            properties = json_data['collected_properties']
        elif '매물목록' in json_data:
            properties = json_data['매물목록']
        elif isinstance(json_data, list):
            properties = json_data
        else:
            print(f"⚠️ 알 수 없는 JSON 구조")
            print(f"Available keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
            return []
        
        # 각 매물을 DB 형식으로 변환
        db_properties = []
        for property_data in properties:
            try:
                db_property = convert_property_to_db_format(property_data, cortar_no)
                
                # 필수 필드 검증
                if db_property['article_no']:
                    db_properties.append(db_property)
                else:
                    print(f"⚠️ 매물번호 누락으로 스킵")
                    
            except Exception as e:
                print(f"❌ 매물 변환 오류: {e}")
                continue
        
        print(f"✅ JSON 데이터 변환 완료: {len(db_properties)}개 매물")
        return db_properties
        
    except Exception as e:
        print(f"❌ JSON 데이터 변환 오류: {e}")
        return []

def test_conversion():
    """변환 기능 테스트"""
    
    # 테스트 데이터
    test_property = {
        "매물번호": "2542368337",
        "매물명": "강남구 역삼동 아파트",
        "부동산타입": "아파트",
        "거래타입": "매매",
        "매매가격": "15억 5,000만원",
        "월세": "",
        "전세보증금": "",
        "전용면적": "84.36㎡",
        "공급면적": "114.21㎡",
        "층정보": "3층/15층",
        "방향": "남향",
        "태그": ["신축", "역세권"],
        "설명": "깨끗한 아파트입니다",
        "상세정보": {
            "카카오주소변환": {
                "도로명주소": "서울특별시 강남구 테헤란로26길 10",
                "지번주소": "서울 강남구 역삼동 736-55",
                "건물명": "테스트빌딩",
                "우편번호": "06234"
            },
            "위치정보": {
                "정확한_위도": "37.4996424",
                "정확한_경도": "127.0358454"
            },
            "방수": "3",
            "욕실수": "2",
            "주차": "1대",
            "난방": "개별난방"
        }
    }
    
    print("🧪 JSON to DB 변환 테스트")
    print("=" * 40)
    
    # 변환 테스트
    db_property = convert_property_to_db_format(test_property, "1168010100")
    
    print("📊 변환 결과:")
    for key, value in db_property.items():
        print(f"  {key}: {value}")
    
    # 가격 파싱 테스트
    print("\n💰 가격 파싱 테스트:")
    test_prices = [
        "15억 5,000만원",
        "3억원",
        "5,000만원",
        "2,500만원",
        "1억 2천만원",
        "-",
        ""
    ]
    
    for price_str in test_prices:
        parsed = parse_price(price_str)
        print(f"  '{price_str}' -> {parsed}만원")

if __name__ == "__main__":
    test_conversion()