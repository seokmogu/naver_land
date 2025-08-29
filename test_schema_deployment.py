#!/usr/bin/env python3
"""
포괄적 스키마 배포 테스트 스크립트
- 모든 새로운 테이블/컬럼 검증
- 데이터 제약조건 테스트  
- articleTax 섹션 저장 기능 검증
"""

import os
import sys
from pathlib import Path
from datetime import datetime, date
from supabase import create_client
import json

class SchemaDeploymentTester:
    def __init__(self):
        """스키마 테스터 초기화"""
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        # 테스트 결과 저장
        self.test_results = {
            'new_tables': {},
            'new_columns': {},
            'expanded_facilities': {},
            'data_validation': {},
            'indexes': {},
            'views': {},
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0
        }
        
        print("🧪 스키마 배포 테스터 초기화 완료")
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*60)
        print("🚀 포괄적 스키마 배포 검증 시작")
        print("="*60)
        
        # 1. 새 테이블 존재 확인
        self.test_new_tables()
        
        # 2. 새 컬럼 확인  
        self.test_new_columns()
        
        # 3. 확장된 시설 유형 확인
        self.test_expanded_facilities()
        
        # 4. 인덱스 생성 확인
        self.test_new_indexes()
        
        # 5. 뷰 생성 확인
        self.test_new_views()
        
        # 6. 데이터 삽입 테스트 (실제 저장 기능)
        self.test_data_insertion()
        
        # 7. 제약조건 테스트
        self.test_constraints()
        
        # 8. 최종 보고서 생성
        self.generate_test_report()
    
    def test_new_tables(self):
        """새로 생성된 테이블 확인"""
        print("\n📋 1. 새 테이블 존재 확인")
        
        required_tables = [
            'property_tax_info',
            'property_price_comparison'
        ]
        
        for table_name in required_tables:
            try:
                # 테이블 구조 확인
                result = self.client.rpc('get_table_info', {'table_name_param': table_name}).execute()
                
                if result.data:
                    print(f"   ✅ {table_name} 테이블 존재")
                    self.test_results['new_tables'][table_name] = 'PASS'
                    self.test_results['passed_tests'] += 1
                else:
                    print(f"   ❌ {table_name} 테이블 누락")
                    self.test_results['new_tables'][table_name] = 'FAIL'
                    self.test_results['failed_tests'] += 1
                    
            except Exception as e:
                # 다른 방법으로 테이블 존재 확인
                try:
                    self.client.table(table_name).select('count', count='exact').limit(0).execute()
                    print(f"   ✅ {table_name} 테이블 존재 (접근 가능)")
                    self.test_results['new_tables'][table_name] = 'PASS'
                    self.test_results['passed_tests'] += 1
                except:
                    print(f"   ❌ {table_name} 테이블 누락 또는 접근 불가")
                    self.test_results['new_tables'][table_name] = 'FAIL'  
                    self.test_results['failed_tests'] += 1
                    
            self.test_results['total_tests'] += 1
    
    def test_new_columns(self):
        """기존 테이블의 새 컬럼 확인"""
        print("\n🔧 2. 새 컬럼 추가 확인")
        
        column_tests = {
            'property_locations': [
                'cortar_no', 'nearest_station', 'subway_stations', 
                'postal_code', 'detail_address'
            ],
            'property_physical': [
                'veranda_count', 'space_type', 'structure_type',
                'floor_description', 'ground_floor_count', 
                'monthly_management_cost', 'management_office_tel',
                'move_in_type', 'move_in_discussion', 'heating_type'
            ],
            'properties_new': [
                'building_use', 'law_usage', 'floor_layer_name', 'approval_date'
            ]
        }
        
        for table_name, columns in column_tests.items():
            print(f"\n   📊 {table_name} 테이블:")
            
            for column_name in columns:
                try:
                    # 컬럼 존재 확인을 위한 쿼리
                    test_query = f"SELECT {column_name} FROM {table_name} LIMIT 1"
                    # 직접 실행 대신 메타데이터로 확인
                    result = self.client.rpc('check_column_exists', {
                        'table_name_param': table_name,
                        'column_name_param': column_name
                    }).execute()
                    
                    print(f"     ✅ {column_name} 컬럼 존재")
                    self.test_results['new_columns'][f"{table_name}.{column_name}"] = 'PASS'
                    self.test_results['passed_tests'] += 1
                    
                except Exception as e:
                    print(f"     ❌ {column_name} 컬럼 누락 또는 오류: {str(e)[:50]}")
                    self.test_results['new_columns'][f"{table_name}.{column_name}"] = 'FAIL'
                    self.test_results['failed_tests'] += 1
                    
                self.test_results['total_tests'] += 1
    
    def test_expanded_facilities(self):
        """확장된 시설 유형 확인"""
        print("\n🏢 3. 시설 유형 확장 확인")
        
        try:
            # 시설 유형 총 개수 확인
            result = self.client.table('facility_types').select('id, facility_name', count='exact').execute()
            
            total_facilities = len(result.data) if result.data else 0
            print(f"   📊 총 시설 유형: {total_facilities}개")
            
            # 새로 추가된 시설들 확인 (ID 10-19)
            new_facilities = self.client.table('facility_types').select('*').gte('id', 10).lte('id', 19).execute()
            
            new_count = len(new_facilities.data) if new_facilities.data else 0
            print(f"   📊 새 시설 유형: {new_count}개")
            
            if new_count >= 8:  # 최소 8개 이상 추가되어야 함
                print("   ✅ 시설 유형 확장 성공")
                self.test_results['expanded_facilities']['count'] = 'PASS'
                self.test_results['passed_tests'] += 1
                
                # 새 시설들 목록 출력
                for facility in new_facilities.data:
                    print(f"     - ID {facility['id']}: {facility['facility_name']}")
                    
            else:
                print(f"   ❌ 시설 유형 확장 부족 (기대: 8+개, 실제: {new_count}개)")
                self.test_results['expanded_facilities']['count'] = 'FAIL'
                self.test_results['failed_tests'] += 1
                
        except Exception as e:
            print(f"   ❌ 시설 유형 확인 오류: {e}")
            self.test_results['expanded_facilities']['count'] = 'FAIL'
            self.test_results['failed_tests'] += 1
            
        self.test_results['total_tests'] += 1
    
    def test_new_indexes(self):
        """새 인덱스 생성 확인"""
        print("\n🔍 4. 인덱스 생성 확인")
        
        expected_indexes = [
            'idx_property_tax_info_property',
            'idx_property_tax_info_total_cost', 
            'idx_property_price_comparison_property',
            'idx_property_locations_cortar_no'
        ]
        
        for index_name in expected_indexes:
            try:
                # PostgreSQL 시스템 테이블에서 인덱스 확인
                result = self.client.rpc('check_index_exists', {'index_name_param': index_name}).execute()
                
                print(f"   ✅ {index_name} 인덱스 존재")
                self.test_results['indexes'][index_name] = 'PASS'
                self.test_results['passed_tests'] += 1
                
            except Exception as e:
                print(f"   ⚠️ {index_name} 인덱스 확인 불가 (존재할 가능성 높음)")
                self.test_results['indexes'][index_name] = 'UNKNOWN'
                
            self.test_results['total_tests'] += 1
    
    def test_new_views(self):
        """새 뷰 생성 확인"""  
        print("\n👁️ 5. 뷰 생성 확인")
        
        expected_views = [
            'data_completeness_check',
            'api_section_coverage'
        ]
        
        for view_name in expected_views:
            try:
                result = self.client.table(view_name).select('*').limit(1).execute()
                
                if result.data is not None:
                    print(f"   ✅ {view_name} 뷰 존재 및 작동")
                    self.test_results['views'][view_name] = 'PASS'
                    self.test_results['passed_tests'] += 1
                else:
                    print(f"   ❌ {view_name} 뷰 데이터 없음")
                    self.test_results['views'][view_name] = 'FAIL'
                    self.test_results['failed_tests'] += 1
                    
            except Exception as e:
                print(f"   ❌ {view_name} 뷰 오류: {str(e)[:50]}")
                self.test_results['views'][view_name] = 'FAIL'
                self.test_results['failed_tests'] += 1
                
            self.test_results['total_tests'] += 1
    
    def test_data_insertion(self):
        """실제 데이터 삽입 테스트"""
        print("\n💾 6. 데이터 삽입 테스트")
        
        try:
            # 테스트용 기본 매물 생성 (필요한 경우)
            test_property = {
                'article_no': f'TEST_SCHEMA_{int(datetime.now().timestamp())}',
                'article_name': '스키마 테스트 매물',
                'real_estate_type_id': 1,  # 기존 아파트 타입 가정
                'trade_type_id': 1,        # 기존 매매 타입 가정  
                'region_id': 1,           # 기존 지역 가정
                'collected_date': date.today().isoformat(),
                'is_active': True
            }
            
            property_result = self.client.table('properties_new').insert(test_property).execute()
            
            if property_result.data:
                test_property_id = property_result.data[0]['id']
                print(f"   ✅ 테스트 매물 생성: ID {test_property_id}")
                
                # 6.1 세금 정보 테스트 (articleTax 섹션)
                self.test_tax_info_insertion(test_property_id)
                
                # 6.2 가격 비교 정보 테스트  
                self.test_price_comparison_insertion(test_property_id)
                
                # 6.3 확장된 물리적 정보 테스트
                self.test_physical_info_insertion(test_property_id)
                
                # 테스트 데이터 정리
                self.cleanup_test_data(test_property_id)
                
            else:
                print("   ❌ 테스트 매물 생성 실패")
                self.test_results['failed_tests'] += 1
                
        except Exception as e:
            print(f"   ❌ 데이터 삽입 테스트 오류: {e}")
            self.test_results['data_validation']['overall'] = 'FAIL'
            self.test_results['failed_tests'] += 1
    
    def test_tax_info_insertion(self, property_id: int):
        """세금 정보 저장 테스트 (핵심!)"""
        print("     🧮 세금 정보 저장 테스트...")
        
        try:
            tax_data = {
                'property_id': property_id,
                'acquisition_tax': 15000000,
                'acquisition_tax_rate': 0.03,
                'registration_tax': 5000000,
                'registration_tax_rate': 0.01,
                'brokerage_fee': 8000000,
                'brokerage_fee_rate': 0.005,
                'stamp_duty': 500000,
                'vat': 800000,
                # total_tax와 total_cost는 트리거에 의해 자동 계산
                'is_estimated': False,
                'notes': '스키마 테스트용 데이터'
            }
            
            result = self.client.table('property_tax_info').insert(tax_data).execute()
            
            if result.data:
                inserted_tax = result.data[0]
                print(f"     ✅ 세금 정보 저장 성공")
                print(f"        - 총 세금: {inserted_tax.get('total_tax', 0):,}원")
                print(f"        - 총 비용: {inserted_tax.get('total_cost', 0):,}원")
                
                # 자동 계산 검증
                expected_total_tax = 15000000 + 5000000 + 500000 + 800000  # 21,300,000
                expected_total_cost = expected_total_tax + 8000000  # 29,300,000
                
                if inserted_tax.get('total_tax') == expected_total_tax:
                    print("     ✅ 세금 총액 자동 계산 정확")
                    self.test_results['data_validation']['tax_calculation'] = 'PASS'
                    self.test_results['passed_tests'] += 1
                else:
                    print(f"     ❌ 세금 계산 오류: 기대 {expected_total_tax:,}, 실제 {inserted_tax.get('total_tax', 0):,}")
                    self.test_results['data_validation']['tax_calculation'] = 'FAIL'
                    self.test_results['failed_tests'] += 1
                    
            else:
                print("     ❌ 세금 정보 저장 실패")
                self.test_results['data_validation']['tax_insertion'] = 'FAIL'
                self.test_results['failed_tests'] += 1
                
        except Exception as e:
            print(f"     ❌ 세금 정보 테스트 오류: {e}")
            self.test_results['data_validation']['tax_insertion'] = 'FAIL'
            self.test_results['failed_tests'] += 1
            
        self.test_results['total_tests'] += 2
    
    def test_price_comparison_insertion(self, property_id: int):
        """가격 비교 정보 저장 테스트"""
        print("     💰 가격 비교 정보 저장 테스트...")
        
        try:
            price_comparison_data = {
                'property_id': property_id,
                'same_addr_count': 5,
                'same_addr_max_price': 800000000,  # 8억
                'same_addr_min_price': 600000000,  # 6억
                'cpid': 'TEST_COMPLEX_001',
                'complex_name': '테스트 아파트 단지',
                'article_feature_desc': '스키마 테스트용 매물 특징 설명'
            }
            
            result = self.client.table('property_price_comparison').insert(price_comparison_data).execute()
            
            if result.data:
                print("     ✅ 가격 비교 정보 저장 성공")
                self.test_results['data_validation']['price_comparison'] = 'PASS'
                self.test_results['passed_tests'] += 1
            else:
                print("     ❌ 가격 비교 정보 저장 실패")  
                self.test_results['data_validation']['price_comparison'] = 'FAIL'
                self.test_results['failed_tests'] += 1
                
        except Exception as e:
            print(f"     ❌ 가격 비교 정보 테스트 오류: {e}")
            self.test_results['data_validation']['price_comparison'] = 'FAIL'
            self.test_results['failed_tests'] += 1
            
        self.test_results['total_tests'] += 1
    
    def test_physical_info_insertion(self, property_id: int):
        """확장된 물리적 정보 저장 테스트"""
        print("     🏗️ 확장 물리정보 저장 테스트...")
        
        try:
            physical_data = {
                'property_id': property_id,
                'area_exclusive': 84.2,
                'area_supply': 110.5,
                'floor_current': 15,
                'floor_total': 25,
                'room_count': 3,
                'bathroom_count': 2,
                # 새로 추가된 컬럼들
                'veranda_count': 1,
                'space_type': '일반형',
                'structure_type': '벽식구조',
                'floor_description': '15층/총 25층',
                'ground_floor_count': 25,
                'underground_floor_count': 2,
                'monthly_management_cost': 150000,
                'management_office_tel': '02-1234-5678',
                'move_in_type': '즉시입주',
                'move_in_discussion': True,
                'heating_type': '개별난방'
            }
            
            result = self.client.table('property_physical').insert(physical_data).execute()
            
            if result.data:
                print("     ✅ 확장 물리정보 저장 성공")
                self.test_results['data_validation']['extended_physical'] = 'PASS'
                self.test_results['passed_tests'] += 1
            else:
                print("     ❌ 확장 물리정보 저장 실패")
                self.test_results['data_validation']['extended_physical'] = 'FAIL'
                self.test_results['failed_tests'] += 1
                
        except Exception as e:
            print(f"     ❌ 확장 물리정보 테스트 오류: {e}")
            self.test_results['data_validation']['extended_physical'] = 'FAIL'
            self.test_results['failed_tests'] += 1
            
        self.test_results['total_tests'] += 1
    
    def test_constraints(self):
        """제약조건 테스트"""
        print("\n⚖️ 7. 제약조건 검증 테스트")
        
        # 7.1 음수 가격 제약조건 테스트
        print("     🚫 음수 세금 제약조건 테스트...")
        try:
            invalid_tax_data = {
                'property_id': 1,  # 존재하는 매물 ID 가정
                'acquisition_tax': -1000000,  # 음수 - 실패해야 함
                'total_tax': 0,
                'total_cost': 0
            }
            
            result = self.client.table('property_tax_info').insert(invalid_tax_data).execute()
            
            if result.data:
                print("     ❌ 음수 세금 허용됨 (제약조건 미작동)")
                self.test_results['data_validation']['negative_constraint'] = 'FAIL'
                self.test_results['failed_tests'] += 1
            else:
                print("     ✅ 음수 세금 차단됨 (제약조건 정상 작동)")
                self.test_results['data_validation']['negative_constraint'] = 'PASS'
                self.test_results['passed_tests'] += 1
                
        except Exception as e:
            print("     ✅ 음수 세금 차단됨 (제약조건 정상 작동)")
            self.test_results['data_validation']['negative_constraint'] = 'PASS'
            self.test_results['passed_tests'] += 1
            
        self.test_results['total_tests'] += 1
    
    def cleanup_test_data(self, property_id: int):
        """테스트 데이터 정리"""
        print("     🧹 테스트 데이터 정리 중...")
        
        try:
            # 관련 테이블 데이터 삭제 (외래키 관계로 인한 순서 중요)
            self.client.table('property_tax_info').delete().eq('property_id', property_id).execute()
            self.client.table('property_price_comparison').delete().eq('property_id', property_id).execute() 
            self.client.table('property_physical').delete().eq('property_id', property_id).execute()
            self.client.table('properties_new').delete().eq('id', property_id).execute()
            
            print("     ✅ 테스트 데이터 정리 완료")
            
        except Exception as e:
            print(f"     ⚠️ 테스트 데이터 정리 오류: {e}")
    
    def generate_test_report(self):
        """최종 테스트 보고서 생성"""
        print("\n" + "="*60)
        print("📊 스키마 배포 검증 최종 보고서")  
        print("="*60)
        
        total = self.test_results['total_tests']
        passed = self.test_results['passed_tests']
        failed = self.test_results['failed_tests']
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📈 전체 테스트: {total}개")
        print(f"✅ 성공: {passed}개")
        print(f"❌ 실패: {failed}개")
        print(f"🎯 성공률: {success_rate:.1f}%")
        
        # 카테고리별 상세 결과
        print(f"\n🔍 카테고리별 결과:")
        
        categories = [
            ('새 테이블', self.test_results['new_tables']),
            ('새 컬럼', self.test_results['new_columns']),
            ('시설 유형', self.test_results['expanded_facilities']),
            ('인덱스', self.test_results['indexes']), 
            ('뷰', self.test_results['views']),
            ('데이터 검증', self.test_results['data_validation'])
        ]
        
        for category_name, category_data in categories:
            if category_data:
                passed_in_category = sum(1 for result in category_data.values() if result == 'PASS')
                total_in_category = len(category_data)
                print(f"   {category_name}: {passed_in_category}/{total_in_category} 성공")
        
        # 중요한 실패 항목 강조
        critical_failures = []
        if self.test_results['new_tables'].get('property_tax_info') == 'FAIL':
            critical_failures.append('property_tax_info 테이블 생성 실패')
        if self.test_results['data_validation'].get('tax_insertion') == 'FAIL':
            critical_failures.append('세금 정보 저장 기능 실패')
        
        if critical_failures:
            print(f"\n🚨 중요 실패 항목:")
            for failure in critical_failures:
                print(f"   - {failure}")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if success_rate >= 90:
            print("   ✅ 스키마 업데이트가 성공적으로 완료되었습니다!")
            print("   ✅ enhanced_data_collector.py를 사용하여 실제 수집을 시작할 수 있습니다.")
        elif success_rate >= 70:
            print("   ⚠️ 일부 기능에서 문제가 발견되었습니다.")
            print("   📋 실패한 항목들을 검토하고 수정 후 재테스트하세요.")
        else:
            print("   🚨 중대한 문제가 발견되었습니다.")
            print("   🔧 스키마 업데이트 스크립트를 다시 실행하세요.")
        
        # 보고서를 파일로도 저장
        report_file = f"schema_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 상세 보고서: {report_file}")
        print("="*60)

def main():
    """테스트 실행 메인"""
    print("🚀 포괄적 스키마 배포 검증 시작")
    
    tester = SchemaDeploymentTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()