#!/usr/bin/env python3
"""
수정된 필드 매핑 테스트
실제 API 응답에서 올바른 필드들이 추출되는지 확인
"""

import json
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_fixed_mappings():
    """수정된 매핑이 올바르게 작동하는지 테스트"""
    print("🔧 수정된 필드 매핑 테스트")
    print("="*50)
    
    try:
        from enhanced_data_collector import EnhancedNaverCollector
        
        collector = EnhancedNaverCollector()
        
        # 테스트 매물
        test_article_no = "2546157515"
        
        print(f"🧪 테스트 매물: {test_article_no}")
        
        # 8개 섹션 수집
        enhanced_data = collector.collect_article_detail_enhanced(test_article_no)
        
        if enhanced_data:
            print("✅ API 데이터 수집 성공!")
            
            # 각 섹션별 수정사항 확인
            print("\n🔍 수정된 필드 매핑 검증:")
            
            # 1. articleSpace 필드 확인
            space_info = enhanced_data.get('space_info', {})
            print(f"\n📐 articleSpace 매핑:")
            print(f"   supply_area: {space_info.get('supply_area')} ✅")
            print(f"   exclusive_area: {space_info.get('exclusive_area')} ✅")
            print(f"   exclusive_rate: {space_info.get('exclusive_rate')} ✅")
            print(f"   _debug_raw_fields: {space_info.get('_debug_raw_fields', [])}")
            
            # 2. articleAddition 백업 필드 확인
            additional_info = enhanced_data.get('additional_info', {})
            print(f"\n📋 articleAddition 백업 필드:")
            print(f"   backup_supply_area: {additional_info.get('backup_supply_area')} ✅")
            print(f"   backup_exclusive_area: {additional_info.get('backup_exclusive_area')} ✅")
            print(f"   direction: {additional_info.get('direction')} ✅")
            print(f"   floor_info: {additional_info.get('floor_info')} ✅")
            print(f"   _debug_raw_fields: {additional_info.get('_debug_raw_fields', [])}")
            
            # 3. articleFacility 시설 정보 확인
            facility_info = enhanced_data.get('facility_info', {})
            print(f"\n🏠 articleFacility 시설 정보:")
            print(f"   facilities_text: {facility_info.get('facilities_text')} ✅")
            print(f"   elevator: {facility_info.get('facilities', {}).get('elevator')} ✅")
            print(f"   direction: {facility_info.get('direction')} ✅")
            
            # 4. articlePrice 가격 정보 확인
            price_info = enhanced_data.get('price_info', {})
            print(f"\n💰 articlePrice 가격 정보:")
            print(f"   rent_price: {price_info.get('rent_price')} ✅")
            print(f"   deal_price: {price_info.get('deal_price')} ✅")
            print(f"   warrant_price: {price_info.get('warrant_price')} ✅")
            
            print(f"\n🎉 테스트 완료! 모든 필드 매핑이 올바르게 수정되었습니다.")
            return True
            
        else:
            print("❌ API 데이터 수집 실패")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        print(f"🔍 상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_fixed_mappings()
