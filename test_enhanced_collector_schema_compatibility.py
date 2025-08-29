#!/usr/bin/env python3
"""
Enhanced Data Collector Schema Compatibility Test
Tests the updated collector with the new database schema
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from enhanced_data_collector import EnhancedNaverCollector


def test_schema_compatibility():
    """Test that all schema mappings work correctly"""
    print("🚀 Enhanced Data Collector 스키마 호환성 테스트 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Initialize collector
        collector = EnhancedNaverCollector()
        print("✅ 수집기 초기화 성공")
        
        # Create mock data that tests all the new schema columns
        mock_api_response = {
            "articleDetail": {
                "articleNo": "TEST_SCHEMA_2024001",
                "articleName": "스키마 테스트 매물",
                "realEstateTypeCode": "APT",
                "tradeTypeCode": "A1",
                "exposureAddress": "서울 강남구 역삼동 123-45",
                "detailAddress": "역삼동 123-45번지",
                "buildingName": "테스트 아파트",
                "latitude": 37.5,
                "longitude": 127.0,
                "nearSubwayList": [
                    {"stationName": "강남역", "distance": "도보 5분"},
                    {"stationName": "역삼역", "distance": "도보 10분"}
                ],
                "walkingToSubway": 5,
                "dealPrice": 50000,
                "warrantPrice": 35000,
                "rentPrice": 150,
                "monthlyManagementCost": 15,
                "buildingUseApprovalDate": "2020-01-15",
                "articleFeatureDesc": "깨끗하고 좋은 매물입니다.",
                "tagList": ["NEW", "HOT"]
            },
            "articleAddition": {
                "sameAddrMaxPrc": 60000,
                "sameAddrMinPrc": 40000,
                "sameAddrCnt": 5
            },
            "articleFacility": {
                "etcFacilities": "주차가능, 엘리베이터, 에어컨, 인터넷, 보안시설, 정수기",
                "directionTypeName": "남향",
                "directionTypeCode": "S",
                "buildingCoverageRatio": 60.5,
                "floorAreaRatio": 200.0,
                "buildingUseAprvYmd": "2020-01-15"
            },
            "articleFloor": {
                "totalFloorCount": 15,
                "undergroundFloorCount": 2,
                "uppergroundFloorCount": 15,
                "correspondingFloorCount": 8,
                "floorDescription": "중간층, 조용함"
            },
            "articlePrice": {
                "dealPrice": 50000,
                "warrantPrice": 35000,
                "rentPrice": 150,
                "monthlyManagementCost": 15
            },
            "articleRealtor": {
                "realtorName": "테스트 공인중개사",
                "representativeName": "김부동산",
                "telephone": "02-123-4567",
                "mobileNumber": "010-1234-5678",
                "officeAddress": "서울 강남구 테스트로 123",
                "businessRegistrationNumber": "123-45-67890",
                "licenseNumber": "서울-12345",
                "profileImageUrl": "https://example.com/profile.jpg",
                "grade": 4.5,
                "reviewCount": 25,
                "totalArticleCount": 100,
                "naverVerified": True
            },
            "articleSpace": {
                "exclusiveArea": 84.5,
                "supplyArea": 101.2,
                "exclusiveRate": 83.5,
                "roomCount": 3,
                "bathRoomCount": 2,
                "verandaCount": 2,
                "spaceType": "아파트",
                "structureType": "철근콘크리트"
            },
            "articleTax": {
                "acquisitionTax": 1500000,
                "acquisitionTaxRate": 0.03,
                "registrationTax": 600000,
                "registrationTaxRate": 0.012,
                "brokerageFee": 750000,
                "brokerageFeeRate": 0.015,
                "stampDuty": 150000,
                "vat": 75000
            },
            "articlePhotos": [
                {
                    "imageUrl": "https://example.com/photo1.jpg",
                    "imageType": "main",
                    "order": 1,
                    "caption": "거실 전경",
                    "width": 1200,
                    "height": 800,
                    "fileSize": 250000
                },
                {
                    "imageUrl": "https://example.com/photo2.jpg",
                    "imageType": "interior",
                    "order": 2,
                    "caption": "침실",
                    "width": 1024,
                    "height": 768,
                    "fileSize": 180000
                }
            ]
        }
        
        print("✅ Mock 데이터 생성 완료")
        
        # Test data processing directly with mock data
        print("🔄 Mock 데이터로 섹션별 처리 테스트")
        enhanced_data = {
            'article_no': mock_api_response['articleDetail']['articleNo'],
            'basic_info': collector._process_article_detail(mock_api_response['articleDetail']),
            'space_info': collector._process_article_space(mock_api_response['articleSpace']),
            'floor_info': collector._process_article_floor(mock_api_response['articleFloor']),
            'facility_info': collector._process_article_facility(mock_api_response['articleFacility']),
            'price_info': collector._process_article_price(mock_api_response['articlePrice']),
            'realtor_info': collector._process_article_realtor(mock_api_response['articleRealtor']),
            'photo_info': collector._process_article_photos(mock_api_response['articlePhotos']),
            'tax_info': collector._process_article_tax(mock_api_response['articleTax']),
            'additional_info': collector._process_article_addition(mock_api_response['articleAddition'])
        }
        
        print(f"✅ 데이터 처리 완료: {enhanced_data['article_no']}")
        
        # Verify all required fields are present
        required_sections = [
            'article_no', 'basic_info', 'space_info', 'floor_info', 
            'facility_info', 'price_info', 'realtor_info', 'photo_info', 'tax_info'
        ]
        
        missing_sections = [section for section in required_sections if section not in enhanced_data]
        if missing_sections:
            print(f"⚠️ 누락된 섹션: {missing_sections}")
        else:
            print("✅ 모든 필수 섹션 존재")
        
        # Test schema-specific fields
        schema_tests = {
            "kakao_api_response": enhanced_data['basic_info'].get('latitude') is not None,
            "floor_description": enhanced_data['floor_info'].get('floor_description') is not None,
            "direction": enhanced_data['facility_info'].get('direction') is not None,
            "veranda_count": enhanced_data['space_info'].get('veranda_count') is not None,
            "acquisition_tax_rate": enhanced_data['tax_info'].get('acquisition_tax_rate') is not None,
            "subway_stations": enhanced_data['basic_info'].get('near_subway_list') is not None
        }
        
        print("\n📋 스키마 필드 테스트 결과:")
        for field, present in schema_tests.items():
            status = "✅" if present else "❌"
            print(f"  {status} {field}: {'존재' if present else '누락'}")
        
        # Test actual database insertion (dry run)
        print("\n🔄 데이터베이스 삽입 테스트 (실제 저장하지 않음)")
        
        # Print what would be saved
        print(f"📍 위치정보 필드: {list(enhanced_data['basic_info'].keys())}")
        print(f"📐 물리정보 필드: {list(enhanced_data['space_info'].keys())} + {list(enhanced_data['floor_info'].keys())}")
        print(f"🏢 시설정보: {enhanced_data['facility_info']['facility_count']}개 시설")
        print(f"💰 가격정보: {len([k for k, v in enhanced_data['price_info'].items() if v is not None])}개 가격 타입")
        print(f"🏪 중개사정보: {enhanced_data['realtor_info'].get('office_name', 'N/A')}")
        print(f"📷 이미지: {len(enhanced_data['photo_info']['photos'])}장")
        print(f"💸 세금정보: {len([k for k, v in enhanced_data['tax_info'].items() if v is not None])}개 세금 항목")
        
        # Detailed field validation
        print("\n🔍 상세 필드 검증:")
        
        # Test location data
        location_fields = ['latitude', 'longitude', 'exposure_address', 'detail_address', 'building_name']
        for field in location_fields:
            value = enhanced_data['basic_info'].get(field)
            print(f"  📍 {field}: {value}")
        
        # Test physical data
        physical_fields = ['exclusive_area', 'supply_area', 'room_count', 'bathroom_count', 'veranda_count']
        for field in physical_fields:
            value = enhanced_data['space_info'].get(field)
            print(f"  📐 {field}: {value}")
        
        # Test facility data
        facilities = enhanced_data['facility_info']['facilities']
        available_facilities = [k for k, v in facilities.items() if v]
        print(f"  🏢 사용가능 시설: {', '.join(available_facilities)}")
        print(f"  🏢 방향: {enhanced_data['facility_info'].get('direction')}")
        
        # Test tax data
        tax_fields = ['acquisition_tax', 'acquisition_tax_rate', 'brokerage_fee', 'total_cost']
        for field in tax_fields:
            value = enhanced_data['tax_info'].get(field)
            print(f"  💸 {field}: {value}")
        
        print("\n" + "=" * 80)
        print("✅ 스키마 호환성 테스트 완료!")
        print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Final validation summary
        all_tests_passed = all(schema_tests.values())
        if all_tests_passed:
            print("🎉 모든 스키마 필드가 올바르게 처리됨!")
        else:
            failed_tests = [field for field, passed in schema_tests.items() if not passed]
            print(f"⚠️ 다음 필드들이 누락됨: {', '.join(failed_tests)}")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = test_schema_compatibility()
    sys.exit(0 if success else 1)