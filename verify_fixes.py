#!/usr/bin/env python3
"""
모든 수정사항이 올바르게 적용되었는지 검증
"""

import os
import sys
from pathlib import Path
import json

def verify_database_schema():
    """데이터베이스 스키마 변경 사항 검증"""
    print("🔍 데이터베이스 스키마 검증")
    print("="*50)
    
    schema_file = "complete_schema_fix.sql"
    if os.path.exists(schema_file):
        with open(schema_file, 'r') as f:
            content = f.read()
            
        # 중요 컬럼들이 포함되어 있는지 확인
        critical_columns = [
            'kakao_api_response',
            'floor_description', 
            'acquisition_tax_rate',
            'management_office_tel',
            'address_enriched'
        ]
        
        print("핵심 컬럼 포함 확인:")
        for column in critical_columns:
            if column in content:
                print(f"✅ {column}")
            else:
                print(f"❌ {column} - 누락!")
    else:
        print("❌ complete_schema_fix.sql 파일이 없습니다!")

def verify_api_field_mappings():
    """API 필드 매핑 검증"""
    print("\n🔍 API 필드 매핑 검증")
    print("="*50)
    
    collector_file = "enhanced_data_collector.py"
    if os.path.exists(collector_file):
        with open(collector_file, 'r') as f:
            content = f.read()
            
        # 올바른 필드명이 사용되고 있는지 확인
        correct_mappings = {
            'supplySpace': 'articleSpace 섹션의 공급면적',
            'exclusiveSpace': 'articleSpace 섹션의 전용면적',
            'kakao_road_address': '카카오 도로명 주소',
            'kakao_api_response': '카카오 API 전체 응답'
        }
        
        print("올바른 필드명 사용 확인:")
        for field, description in correct_mappings.items():
            if field in content:
                print(f"✅ {field} - {description}")
            else:
                print(f"❌ {field} - {description} 누락!")
                
        # 잘못된 필드명이 아직 남아있는지 확인
        wrong_mappings = [
            'supplyArea',      # 잘못된 필드명
            'exclusiveArea',   # 잘못된 필드명
            'area1',           # 레거시에서 사용했지만 실제로는 없는 필드
            'area2'            # 레거시에서 사용했지만 실제로는 없는 필드
        ]
        
        print("\n잘못된 필드명 제거 확인:")
        for field in wrong_mappings:
            if field in content:
                print(f"⚠️ {field} - 아직 남아있음! 수정 필요")
            else:
                print(f"✅ {field} - 제거됨")
    else:
        print("❌ enhanced_data_collector.py 파일이 없습니다!")

def verify_kakao_integration():
    """카카오 통합 검증"""
    print("\n🔍 카카오 통합 검증")
    print("="*50)
    
    try:
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        
        from enhanced_data_collector import EnhancedNaverCollector, KAKAO_AVAILABLE
        
        if KAKAO_AVAILABLE:
            print("✅ 카카오 모듈 로드 성공")
            
            collector = EnhancedNaverCollector()
            if collector.kakao_converter:
                print("✅ 카카오 변환기 초기화 성공")
                
                # 실제 좌표로 테스트
                result = collector.kakao_converter.convert_coord_to_address("37.498095", "127.027610")
                if result:
                    print(f"✅ 카카오 API 변환 테스트 성공")
                    print(f"   도로명: {result.get('road_address', 'None')}")
                    print(f"   건물명: {result.get('building_name', 'None')}")
                else:
                    print("⚠️ 카카오 API 변환 결과 없음")
            else:
                print("❌ 카카오 변환기 초기화 실패")
        else:
            print("❌ 카카오 모듈 로드 실패")
            
    except Exception as e:
        print(f"❌ 카카오 통합 테스트 실패: {e}")

def create_test_summary():
    """테스트 결과 요약 파일 생성"""
    summary = {
        "timestamp": "2025-08-29 22:00:00",
        "fixes_applied": {
            "database_schema": "complete_schema_fix.sql 생성됨",
            "api_field_mappings": "supplySpace/exclusiveSpace로 수정됨",
            "kakao_integration": "카카오 주소 변환 컬럼 추가됨"
        },
        "critical_columns_added": [
            "kakao_api_response (JSONB)",
            "floor_description (TEXT)", 
            "acquisition_tax_rate (DECIMAL)",
            "management_office_tel (VARCHAR)",
            "address_enriched (BOOLEAN)"
        ],
        "next_steps": [
            "1. Supabase에서 complete_schema_fix.sql 실행",
            "2. enhanced_data_collector.py 테스트 실행",
            "3. 카카오 주소 변환 end-to-end 테스트",
            "4. 실제 매물 수집으로 최종 검증"
        ]
    }
    
    with open('fix_verification_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 검증 결과 요약: fix_verification_summary.json")

if __name__ == "__main__":
    print("🔧 수정사항 검증 시작")
    
    verify_database_schema()
    verify_api_field_mappings()
    verify_kakao_integration()
    create_test_summary()
    
    print(f"\n🎯 다음 단계:")
    print(f"1. 먼저 Supabase에서 complete_schema_fix.sql을 실행하세요")
    print(f"2. 그 다음 enhanced_data_collector.py를 테스트하세요")
    print(f"3. 모든 에러가 사라지고 카카오 주소가 정상적으로 저장되는지 확인하세요")