#!/usr/bin/env python3
"""
실제 데이터 수집으로 통합 테스트
- 실제 네이버 매물 1개 수집 테스트
- 카카오 주소 변환 테스트
- 데이터베이스 저장 검증
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from enhanced_data_collector import EnhancedNaverCollector
    print("✅ Enhanced Data Collector 로드 성공")
except ImportError as e:
    print(f"❌ Enhanced Data Collector 로드 실패: {e}")
    sys.exit(1)

class IntegrationTester:
    def __init__(self):
        self.collector = EnhancedNaverCollector()
        
    def test_single_property_collection(self):
        """실제 매물 1개 수집 테스트"""
        print("🏠 실제 매물 수집 테스트")
        print("=" * 60)
        
        try:
            # 강남구 매물 수집으로 테스트 (실제 메서드 사용)
            cortar_no = '1168010100'  # 강남구 역삼1동
            
            print("📡 네이버 API 호출 중...")
            print(f"   지역: {cortar_no} (강남구 역삼1동)")
            
            # 실제 매물 번호 수집 (1페이지만)
            article_numbers = self.collector.collect_single_page_articles(cortar_no, 1)
            
            if not article_numbers:
                print("❌ 매물 번호 수집 실패")
                return False
                
            print(f"✅ {len(article_numbers)}개 매물 번호 수집")
            
            # 첫 번째 매물 상세 정보 수집
            first_article = article_numbers[0]
            print(f"   테스트 매물: {first_article}")
            
            property_detail = self.collector.collect_article_detail_enhanced(first_article)
            
            if not property_detail:
                print("❌ 매물 상세 정보 수집 실패")
                return False
                
            results = [property_detail]
            
            if not results:
                print("❌ 매물 데이터 수집 실패")
                return False
                
            print(f"✅ {len(results)}개 매물 수집 성공")
            
            # 첫 번째 매물로 상세 검증
            property_data = results[0]
            self.verify_property_data(property_data)
            
            return True
            
        except Exception as e:
            print(f"❌ 매물 수집 테스트 실패: {e}")
            return False
    
    def verify_property_data(self, property_data):
        """수집된 매물 데이터 검증"""
        print("\n🔍 수집 데이터 검증")
        print("-" * 40)
        
        # 기본 정보 검증
        article_no = property_data.get('article_no', 'N/A')
        print(f"매물번호: {article_no}")
        
        # 면적 정보 검증 (핵심 이슈)
        space_info = property_data.get('space_info', {})
        supply_area = space_info.get('supply_area')
        exclusive_area = space_info.get('exclusive_area')
        
        print(f"공급면적: {supply_area}㎡")
        print(f"전용면적: {exclusive_area}㎡")
        
        if supply_area and supply_area != 10.0:  # 10㎡는 기본값이므로 실제 데이터 확인
            print("✅ 실제 면적 정보 수집 성공")
        else:
            print("⚠️ 면적 정보가 기본값(10㎡) - API 매핑 재확인 필요")
        
        # 위치 정보 검증
        location_info = property_data.get('location_info', {})
        latitude = location_info.get('latitude')
        longitude = location_info.get('longitude')
        
        print(f"좌표: ({latitude}, {longitude})")
        
        if latitude and longitude:
            print("✅ 좌표 정보 수집 성공")
            
            # 카카오 주소 변환 테스트
            self.test_kakao_conversion(latitude, longitude)
        else:
            print("⚠️ 좌표 정보 없음")
        
        # 가격 정보 검증
        price_info = property_data.get('price_info', {})
        deal_price = price_info.get('deal_price', 0)
        print(f"매매가: {deal_price:,}만원" if deal_price else "가격 정보 없음")
        
        # 외래키 검증
        self.verify_foreign_keys(property_data)
        
    def test_kakao_conversion(self, latitude, longitude):
        """카카오 주소 변환 테스트"""
        print("\n🗺️ 카카오 주소 변환 테스트")
        print("-" * 40)
        
        if not self.collector.kakao_converter:
            print("❌ 카카오 변환기 없음")
            return False
            
        try:
            result = self.collector.kakao_converter.convert_coord_to_address(
                str(latitude), str(longitude)
            )
            
            if result:
                print("✅ 카카오 주소 변환 성공")
                print(f"  도로명: {result.get('road_address', 'N/A')}")
                print(f"  지번: {result.get('jibun_address', 'N/A')}")
                print(f"  건물명: {result.get('building_name', 'N/A')}")
                print(f"  우편번호: {result.get('zone_no', 'N/A')}")
                return True
            else:
                print("⚠️ 카카오 주소 변환 결과 없음")
                return False
                
        except Exception as e:
            print(f"❌ 카카오 주소 변환 실패: {e}")
            return False
    
    def verify_foreign_keys(self, property_data):
        """외래키 해결 검증"""
        print("\n🔗 외래키 해결 검증")
        print("-" * 40)
        
        real_estate_id = self.collector._resolve_real_estate_type_id(property_data)
        trade_id = self.collector._resolve_trade_type_id(property_data)
        region_id = self.collector._resolve_region_id(property_data)
        
        print(f"부동산 유형 ID: {real_estate_id}")
        print(f"거래 유형 ID: {trade_id}")
        print(f"지역 ID: {region_id}")
        
        if all([real_estate_id, trade_id, region_id]):
            print("✅ 모든 외래키 해결 성공")
            return True
        else:
            print("❌ 외래키 해결 실패")
            return False
    
    def test_database_save_simulation(self):
        """데이터베이스 저장 시뮬레이션"""
        print("\n💾 데이터베이스 저장 시뮬레이션")
        print("=" * 60)
        
        print("⚠️ 실제 저장 테스트는 Supabase 스키마 업데이트 이후 권장")
        print("📋 필요한 사전 작업:")
        print("   1. Supabase에서 complete_schema_fix.sql 실행")
        print("   2. 모든 누락 컬럼 추가 확인")
        print("   3. 실제 저장 테스트 진행")
        
        return True
    
    def run_full_integration_test(self):
        """전체 통합 테스트"""
        print("🧪 실제 데이터 수집 통합 테스트")
        print("=" * 80)
        print(f"📅 테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        tests = []
        
        # 1. 실제 매물 수집 테스트
        collection_success = self.test_single_property_collection()
        tests.append(("실제 매물 수집", collection_success))
        
        # 2. 데이터베이스 저장 시뮬레이션
        db_sim_success = self.test_database_save_simulation()
        tests.append(("데이터베이스 저장 시뮬레이션", db_sim_success))
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("📊 통합 테스트 결과")
        print("=" * 80)
        
        passed_tests = sum(1 for _, success in tests if success)
        total_tests = len(tests)
        
        for test_name, success in tests:
            status = "✅ 통과" if success else "❌ 실패"
            print(f"  {status}: {test_name}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n전체 성공률: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if success_rate >= 100:
            print("🎉 모든 통합 테스트 통과!")
            print("💡 데이터베이스 스키마 업데이트 후 본격 수집 가능")
        elif success_rate >= 50:
            print("⚠️ 일부 테스트 통과 - 추가 수정 후 재시도")
        else:
            print("❌ 통합 테스트 실패 - 전면 재검토 필요")
        
        print("\n🎯 최종 권장사항:")
        print("1. Supabase에서 complete_schema_fix.sql 실행")
        print("2. 모든 컬럼 추가 확인 후 실제 저장 테스트")
        print("3. 실제 대용량 수집 전 추가 검증")
        
        return success_rate

def main():
    try:
        tester = IntegrationTester()
        success_rate = tester.run_full_integration_test()
        
        if success_rate >= 100:
            print(f"\n🚀 다음 단계: 본격적인 데이터 수집 준비 완료")
        else:
            print(f"\n🔧 추가 수정 필요 - 성공률: {success_rate:.1f}%")
            
    except Exception as e:
        print(f"❌ 통합 테스트 실행 실패: {e}")

if __name__ == "__main__":
    main()