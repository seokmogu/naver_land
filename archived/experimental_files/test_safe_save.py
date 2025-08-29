#!/usr/bin/env python3
"""
안전한 저장 기능 테스트
- 기존 JSON 파일을 사용하여 안전한 저장 테스트
- 삭제 로직 없이 upsert만 테스트
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import SupabaseHelper
from json_to_db_converter import convert_json_data_to_properties

def test_safe_save():
    """기존 JSON 파일로 안전한 저장 테스트"""
    print("🔧 안전한 저장 기능 테스트")
    print("=" * 40)
    
    try:
        helper = SupabaseHelper()
        
        # 기존 JSON 파일 사용 (수집된 것)
        json_files = [f for f in os.listdir('results') if f.endswith('.json')]
        
        if not json_files:
            print("❌ 테스트할 JSON 파일이 없습니다")
            return False
        
        # 좋은 크기의 파일 선택 (50KB 정도)
        good_files = [f for f in json_files if 'naver_optimized_역삼동_1168010100_20250827_073929' in f]
        if good_files:
            test_json = good_files[0]
        else:
            test_json = json_files[0]
        
        json_path = f"results/{test_json}"
        
        print(f"📄 테스트 파일: {test_json}")
        
        # JSON 로드
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # DB 형식으로 변환
        test_cortar_no = "1168010100"  # 역삼동
        db_properties = convert_json_data_to_properties(json_data, test_cortar_no)
        
        if not db_properties:
            print("❌ 변환된 매물이 없습니다")
            return False
        
        print(f"📊 변환된 매물: {len(db_properties)}개")
        
        # 테스트용으로 일부만 사용 (처음 10개)
        test_properties = db_properties[:10]
        print(f"🧪 테스트 매물: {len(test_properties)}개")
        
        # 저장 전 상태
        before_count = helper.get_property_count_by_region(test_cortar_no)
        print(f"📊 저장 전 매물 수: {before_count}개")
        
        # 안전한 저장 실행
        save_result = helper.safe_save_converted_properties(test_properties, test_cortar_no)
        
        # 저장 후 상태
        after_count = helper.get_property_count_by_region(test_cortar_no)
        print(f"📊 저장 후 매물 수: {after_count}개")
        
        # 결과 분석
        print(f"\n📈 저장 결과:")
        print(f"   처리된 매물: {save_result.get('total_saved', 0)}개")
        print(f"   매물 수 변화: {before_count} → {after_count}")
        
        if save_result.get('total_saved', 0) > 0:
            print("✅ 안전한 저장 테스트 성공!")
            return True
        else:
            print("⚠️ 저장이 완전히 수행되지 않았습니다")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_safe_save()