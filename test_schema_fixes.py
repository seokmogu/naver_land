#!/usr/bin/env python3
"""
데이터베이스 스키마 수정 사항 테스트 스크립트
- 외래키 조회 테스트
- 제약조건 검증 테스트
- 실제 데이터 삽입 테스트
"""

import os
import sys
from pathlib import Path
from datetime import datetime, date

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

class SchemaTester:
    def __init__(self):
        """스키마 테스터 초기화"""
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            print("✅ Supabase 연결 성공")
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {e}")
            sys.exit(1)

    def test_schema_existence(self):
        """정규화된 스키마 테이블 존재 확인"""
        print("\n🔍 스키마 존재 확인 테스트")
        print("=" * 50)
        
        required_tables = [
            'real_estate_types',
            'trade_types', 
            'regions',
            'properties_new',
            'property_locations',
            'property_physical',
            'property_prices',
            'realtors',
            'property_realtors',
            'property_images',
            'property_facilities'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in required_tables:
            try:
                result = self.client.table(table).select('*').limit(1).execute()
                existing_tables.append(table)
                print(f"✅ {table}: 존재")
            except Exception as e:
                missing_tables.append(table)
                print(f"❌ {table}: 없음 ({str(e)[:50]}...)")
        
        print(f"\n📊 결과: {len(existing_tables)}/{len(required_tables)} 테이블 존재")
        
        if missing_tables:
            print(f"⚠️ 누락된 테이블: {', '.join(missing_tables)}")
            return False
        
        return True

    def test_reference_data(self):
        """참조 데이터 존재 확인"""
        print("\n🔍 참조 데이터 확인 테스트") 
        print("=" * 50)
        
        success_count = 0
        
        # 1. 부동산 유형
        try:
            real_estate_types = self.client.table('real_estate_types').select('*').execute()
            print(f"✅ 부동산 유형: {len(real_estate_types.data)}개")
            if real_estate_types.data:
                for rt in real_estate_types.data[:3]:  # 처음 3개만 출력
                    print(f"   - {rt['type_name']} ({rt['category']})")
                success_count += 1
        except Exception as e:
            print(f"❌ 부동산 유형: {e}")
        
        # 2. 거래 유형
        try:
            trade_types = self.client.table('trade_types').select('*').execute()
            print(f"✅ 거래 유형: {len(trade_types.data)}개")
            if trade_types.data:
                for tt in trade_types.data:
                    print(f"   - {tt['type_name']} (보증금 필요: {tt['requires_deposit']})")
                success_count += 1
        except Exception as e:
            print(f"❌ 거래 유형: {e}")
        
        # 3. 지역 정보
        try:
            regions = self.client.table('regions').select('*').limit(10).execute()
            print(f"✅ 지역 정보: {len(regions.data)}개 (샘플)")
            if regions.data:
                for region in regions.data[:3]:  # 처음 3개만 출력
                    print(f"   - {region['dong_name']} ({region['gu_name']})")
                success_count += 1
        except Exception as e:
            print(f"❌ 지역 정보: {e}")
        
        # 모든 참조 테이블이 데이터를 가지고 있으면 성공
        return success_count >= 3

    def test_foreign_key_resolution(self):
        """외래키 조회 테스트"""
        print("\n🔍 외래키 조회 테스트")
        print("=" * 50)
        
        from enhanced_data_collector import EnhancedNaverCollector
        
        collector = EnhancedNaverCollector()
        
        # 테스트 데이터
        test_data = {
            'article_no': 'TEST_001',
            'raw_sections': {
                'articleDetail': {
                    'realEstateTypeName': '아파트',
                    'buildingUse': '공동주택'
                },
                'articlePrice': {
                    'tradeTypeName': '매매'
                }
            },
            'basic_info': {
                'building_use': '아파트'
            },
            'price_info': {
                'deal_price': 50000  # 5억
            }
        }
        
        # 1. 부동산 유형 ID 조회
        real_estate_type_id = collector._resolve_real_estate_type_id(test_data)
        print(f"✅ 부동산 유형 ID: {real_estate_type_id}")
        
        # 2. 거래 유형 ID 조회  
        trade_type_id = collector._resolve_trade_type_id(test_data)
        print(f"✅ 거래 유형 ID: {trade_type_id}")
        
        # 3. 지역 ID 조회
        region_id = collector._resolve_region_id(test_data)
        print(f"✅ 지역 ID: {region_id}")
        
        if all([real_estate_type_id, trade_type_id, region_id]):
            print("🎉 모든 외래키 조회 성공!")
            return True
        else:
            print("❌ 일부 외래키 조회 실패")
            return False

    def test_constraint_validation(self):
        """제약조건 검증 테스트"""
        print("\n🔍 제약조건 검증 테스트")
        print("=" * 50)
        
        # 테스트용 임시 데이터
        test_property = {
            'article_no': f'SCHEMA_TEST_{int(datetime.now().timestamp())}',
            'article_name': '스키마 테스트 매물',
            'real_estate_type_id': 1,  # 존재한다고 가정
            'trade_type_id': 1,        # 존재한다고 가정  
            'region_id': 1,            # 존재한다고 가정
            'collected_date': date.today().isoformat(),
            'last_seen_date': date.today().isoformat(),
            'is_active': True
        }
        
        try:
            # 1. properties_new 테이블 삽입 테스트
            result = self.client.table('properties_new').insert(test_property).execute()
            if result.data:
                property_id = result.data[0]['id']
                print(f"✅ properties_new 삽입 성공: ID {property_id}")
                
                # 2. property_physical 제약조건 테스트
                try:
                    physical_data = {
                        'property_id': property_id,
                        'area_exclusive': 84.5,  # 양수
                        'area_supply': 120.3,    # 양수
                        'floor_current': 5,
                        'floor_total': 15        # floor_current <= floor_total
                    }
                    
                    self.client.table('property_physical').insert(physical_data).execute()
                    print("✅ property_physical 제약조건 통과")
                    
                except Exception as e:
                    print(f"❌ property_physical 제약조건 실패: {e}")
                
                # 3. property_prices 제약조건 테스트
                try:
                    price_data = {
                        'property_id': property_id,
                        'price_type': 'sale',
                        'amount': 50000,  # 양수
                        'valid_from': date.today().isoformat()
                    }
                    
                    self.client.table('property_prices').insert(price_data).execute()
                    print("✅ property_prices 제약조건 통과")
                    
                except Exception as e:
                    print(f"❌ property_prices 제약조건 실패: {e}")
                
                # 테스트 데이터 정리
                self.client.table('properties_new').delete().eq('id', property_id).execute()
                print(f"🧹 테스트 데이터 정리 완료: ID {property_id}")
                
        except Exception as e:
            print(f"❌ properties_new 삽입 실패: {e}")
            return False
        
        return True

    def test_single_property_insert(self):
        """단일 매물 실제 삽입 테스트"""
        print("\n🔍 실제 매물 삽입 테스트")
        print("=" * 50)
        
        from enhanced_data_collector import EnhancedNaverCollector
        
        collector = EnhancedNaverCollector()
        
        # 실제 API 호출로 매물 하나 수집
        test_article_no = "2546339433"  # 실제 존재하는 매물 번호
        
        print(f"🔍 테스트 매물 {test_article_no} 상세 정보 수집 중...")
        
        enhanced_data = collector.collect_article_detail_enhanced(test_article_no)
        
        if enhanced_data:
            print("✅ 매물 데이터 수집 성공")
            print(f"🔍 수집된 섹션: {list(enhanced_data.keys())}")
            
            # 정규화된 DB에 저장 시도
            print(f"💾 정규화된 DB 저장 테스트...")
            save_result = collector.save_to_normalized_database(enhanced_data)
            
            if save_result:
                print("🎉 매물 저장 성공!")
                return True
            else:
                print("❌ 매물 저장 실패")
                return False
        else:
            print("❌ 매물 데이터 수집 실패")
            return False

    def generate_test_report(self):
        """테스트 결과 종합 보고서"""
        print("\n📊 스키마 테스트 결과 보고서")
        print("=" * 60)
        
        tests = [
            ("스키마 존재 확인", self.test_schema_existence),
            ("참조 데이터 확인", self.test_reference_data),
            ("외래키 조회 테스트", self.test_foreign_key_resolution),
            ("제약조건 검증 테스트", self.test_constraint_validation),
            ("실제 매물 삽입 테스트", self.test_single_property_insert)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} 오류: {e}")
                results.append((test_name, False))
        
        # 최종 보고서
        print(f"\n{'='*60}")
        print("📋 최종 테스트 결과")
        print(f"{'='*60}")
        
        passed = 0
        for test_name, result in results:
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{status} {test_name}")
            if result:
                passed += 1
        
        print(f"\n🎯 전체 결과: {passed}/{len(results)} 테스트 통과")
        
        if passed == len(results):
            print("🎉 모든 스키마 수정 사항이 정상 작동합니다!")
        else:
            print("⚠️ 일부 수정사항에 문제가 있습니다. 로그를 확인하세요.")
        
        return passed == len(results)

def main():
    """메인 테스트 실행"""
    print("🚀 데이터베이스 스키마 수정사항 검증 테스트")
    print("=" * 60)
    
    tester = SchemaTester()
    success = tester.generate_test_report()
    
    if success:
        print("\n✅ 스키마 수정 완료 - 실제 수집 작업을 시작할 수 있습니다!")
    else:
        print("\n❌ 스키마 수정이 완전하지 않습니다. 문제를 해결한 후 다시 테스트하세요.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)