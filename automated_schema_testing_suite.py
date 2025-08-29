#!/usr/bin/env python3
"""
자동화된 스키마 테스트 스위트
- 스키마 배포 후 자동 검증
- 성능 벤치마킹
- 데이터 완성도 모니터링
- 실패 시 상세 리포트 생성
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import traceback

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('schema_testing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AutomatedSchemaTestSuite:
    def __init__(self):
        """자동화된 스키마 테스트 스위트 초기화"""
        # Supabase 연결
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("✅ Supabase 연결 성공")
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {e}")
            sys.exit(1)
        
        # 테스트 결과 저장
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'test_suites': [],
            'performance_metrics': {},
            'critical_failures': [],
            'recommendations': []
        }
    
    def run_sql_validation_function(self, function_name: str, params: Dict = None) -> List[Dict]:
        """SQL 검증 함수 실행"""
        try:
            if params:
                # 매개변수가 있는 함수 호출
                result = self.client.rpc(function_name, params).execute()
            else:
                # 매개변수 없는 함수 호출 (직접 SQL 쿼리)
                query = f"SELECT * FROM {function_name}();"
                result = self.client.rpc('exec_sql', {'query': query}).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"SQL 함수 {function_name} 실행 실패: {e}")
            return [{'error': str(e)}]
    
    def test_schema_structure_validation(self) -> Dict:
        """스키마 구조 검증 테스트"""
        logger.info("🔍 스키마 구조 검증 시작...")
        
        test_suite = {
            'name': 'Schema Structure Validation',
            'status': 'UNKNOWN',
            'tests': [],
            'duration_seconds': 0,
            'critical_issues': []
        }
        
        start_time = time.time()
        
        try:
            # 1. 필수 테이블 존재 확인
            required_tables = [
                'real_estate_types', 'trade_types', 'regions', 'facility_types',
                'properties_new', 'property_prices', 'property_locations',
                'property_physical', 'property_realtors', 'property_images',
                'property_facilities', 'realtors', 'property_tax_info',
                'property_price_comparison'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in required_tables:
                try:
                    result = self.client.table(table).select('*').limit(1).execute()
                    existing_tables.append(table)
                except:
                    missing_tables.append(table)
            
            table_test = {
                'name': 'Required Tables Existence',
                'status': 'PASS' if not missing_tables else 'FAIL',
                'details': f"{len(existing_tables)}/{len(required_tables)} tables exist",
                'missing_tables': missing_tables
            }
            test_suite['tests'].append(table_test)
            
            if missing_tables:
                test_suite['critical_issues'].append(f"Missing tables: {', '.join(missing_tables)}")
            
            # 2. 핵심 컬럼 존재 확인
            critical_columns = {
                'property_tax_info': ['total_tax', 'brokerage_fee', 'acquisition_tax'],
                'property_price_comparison': ['cpid', 'same_addr_count'],
                'property_locations': ['subway_stations', 'cortar_no'],
                'property_physical': ['veranda_count', 'space_type', 'monthly_management_cost']
            }
            
            missing_columns = []
            for table_name, columns in critical_columns.items():
                if table_name in existing_tables:
                    try:
                        # 테이블 구조 확인
                        sample = self.client.table(table_name).select('*').limit(1).execute()
                        if sample.data:
                            existing_cols = set(sample.data[0].keys()) if sample.data else set()
                            for col in columns:
                                if col not in existing_cols:
                                    missing_columns.append(f"{table_name}.{col}")
                    except Exception as e:
                        missing_columns.append(f"{table_name}.* (table access error)")
            
            column_test = {
                'name': 'Critical Columns Existence',
                'status': 'PASS' if not missing_columns else 'FAIL',
                'details': f"Critical columns check: {len(missing_columns)} missing",
                'missing_columns': missing_columns
            }
            test_suite['tests'].append(column_test)
            
            if missing_columns:
                test_suite['critical_issues'].extend([f"Missing column: {col}" for col in missing_columns])
            
            # 3. 참조 데이터 검증
            reference_data_status = {}
            for ref_table in ['real_estate_types', 'trade_types', 'regions', 'facility_types']:
                if ref_table in existing_tables:
                    try:
                        count_result = self.client.table(ref_table).select('*', count='exact').limit(1).execute()
                        count = count_result.count if hasattr(count_result, 'count') else 0
                        reference_data_status[ref_table] = count
                    except:
                        reference_data_status[ref_table] = 0
            
            ref_data_test = {
                'name': 'Reference Data Population',
                'status': 'PASS' if all(count > 0 for count in reference_data_status.values()) else 'FAIL',
                'details': f"Reference tables populated: {reference_data_status}",
                'reference_counts': reference_data_status
            }
            test_suite['tests'].append(ref_data_test)
            
            # 전체 스위트 상태 결정
            failed_tests = [t for t in test_suite['tests'] if t['status'] == 'FAIL']
            test_suite['status'] = 'FAIL' if failed_tests else 'PASS'
            
        except Exception as e:
            logger.error(f"스키마 구조 검증 오류: {e}")
            test_suite['status'] = 'ERROR'
            test_suite['critical_issues'].append(f"Validation error: {str(e)}")
        
        test_suite['duration_seconds'] = time.time() - start_time
        return test_suite
    
    def test_data_insertion_all_sections(self) -> Dict:
        """모든 API 섹션 데이터 삽입 테스트"""
        logger.info("📝 API 섹션 데이터 삽입 테스트 시작...")
        
        test_suite = {
            'name': 'API Section Data Insertion',
            'status': 'UNKNOWN',
            'tests': [],
            'duration_seconds': 0,
            'critical_issues': []
        }
        
        start_time = time.time()
        test_property_id = None
        test_realtor_id = None
        
        try:
            # 테스트용 매물 생성
            test_property = {
                'article_no': f'AUTOTEST_{int(time.time())}',
                'article_name': '자동화 테스트 매물',
                'real_estate_type_id': 1,
                'trade_type_id': 1,
                'region_id': 1,
                'collected_date': date.today().isoformat(),
                'last_seen_date': date.today().isoformat(),
                'is_active': True,
                'building_use': '공동주택',
                'law_usage': '주거용'
            }
            
            property_result = self.client.table('properties_new').insert(test_property).execute()
            if property_result.data:
                test_property_id = property_result.data[0]['id']
                logger.info(f"✅ 테스트 매물 생성 성공: ID {test_property_id}")
            else:
                raise Exception("테스트 매물 생성 실패")
            
            # 테스트용 중개사 생성
            test_realtor = {
                'realtor_name': '자동화 테스트 중개사',
                'phone_number': '010-0000-0000',
                'business_number': 'TEST-123-45-67890'
            }
            
            realtor_result = self.client.table('realtors').insert(test_realtor).execute()
            if realtor_result.data:
                test_realtor_id = realtor_result.data[0]['id']
                logger.info(f"✅ 테스트 중개사 생성 성공: ID {test_realtor_id}")
            
            # 각 API 섹션별 데이터 삽입 테스트
            api_sections = [
                {
                    'name': 'articlePrice',
                    'table': 'property_prices',
                    'data': {
                        'property_id': test_property_id,
                        'price_type': 'sale',
                        'amount': 500000000,
                        'currency': 'KRW',
                        'valid_from': date.today().isoformat()
                    }
                },
                {
                    'name': 'articleLocation',
                    'table': 'property_locations',
                    'data': {
                        'property_id': test_property_id,
                        'latitude': 37.5665,
                        'longitude': 126.9780,
                        'address_road': '서울시 강남구 테스트로 123',
                        'address_jibun': '서울시 강남구 테스트동 123',
                        'building_name': '테스트빌딩',
                        'postal_code': '06123',
                        'cortar_no': '1168010100',
                        'subway_stations': json.dumps([
                            {'name': '강남역', 'line': '2호선', 'distance': 500}
                        ])
                    }
                },
                {
                    'name': 'articlePhysical',
                    'table': 'property_physical',
                    'data': {
                        'property_id': test_property_id,
                        'area_exclusive': 84.5,
                        'area_supply': 120.0,
                        'area_utilization_rate': 70.42,
                        'floor_current': 5,
                        'floor_total': 15,
                        'room_count': 3,
                        'bathroom_count': 2,
                        'direction': '남향',
                        'parking_count': 1,
                        'parking_possible': True,
                        'elevator_available': True,
                        'veranda_count': 1,
                        'space_type': '복층',
                        'heating_type': '중앙난방',
                        'monthly_management_cost': 150000
                    }
                },
                {
                    'name': 'articleRealtor',
                    'table': 'property_realtors',
                    'data': {
                        'property_id': test_property_id,
                        'realtor_id': test_realtor_id,
                        'listing_date': date.today().isoformat(),
                        'listing_type': 'exclusive',
                        'is_primary': True,
                        'commission_rate': 0.5,
                        'contact_phone': '010-1234-5678',
                        'contact_person': '테스트 담당자',
                        'is_active': True
                    }
                },
                {
                    'name': 'articleImage',
                    'table': 'property_images',
                    'data': {
                        'property_id': test_property_id,
                        'image_url': 'https://example.com/test-image-1.jpg',
                        'image_type': 'main',
                        'image_order': 1,
                        'caption': '테스트 메인 이미지',
                        'alt_text': '자동화 테스트용 이미지',
                        'width': 800,
                        'height': 600,
                        'is_high_quality': True,
                        'is_verified': True,
                        'captured_date': date.today().isoformat()
                    }
                },
                {
                    'name': 'articleFacility',
                    'table': 'property_facilities',
                    'data': {
                        'property_id': test_property_id,
                        'facility_id': 1,  # 엘리베이터
                        'available': True,
                        'condition_grade': 4,
                        'notes': '자동화 테스트 시설',
                        'last_checked': date.today().isoformat()
                    }
                },
                {
                    'name': 'articleTax',
                    'table': 'property_tax_info',
                    'data': {
                        'property_id': test_property_id,
                        'acquisition_tax': 5000000,
                        'acquisition_tax_rate': 0.01,
                        'registration_tax': 2000000,
                        'registration_tax_rate': 0.004,
                        'brokerage_fee': 3000000,
                        'brokerage_fee_rate': 0.006,
                        'stamp_duty': 150000,
                        'vat': 300000,
                        'calculation_date': date.today().isoformat(),
                        'is_estimated': True,
                        'notes': '자동화 테스트용 세금 정보'
                    }
                },
                {
                    'name': 'articleAddition',
                    'table': 'property_price_comparison',
                    'data': {
                        'property_id': test_property_id,
                        'same_addr_count': 5,
                        'same_addr_max_price': 600000000,
                        'same_addr_min_price': 400000000,
                        'cpid': 'TEST_CPID_123456',
                        'complex_name': '테스트아파트',
                        'article_feature_desc': '자동화 테스트용 특징 설명',
                        'market_data_date': date.today().isoformat()
                    }
                }
            ]
            
            # 각 섹션별 테스트 실행
            successful_sections = []
            failed_sections = []
            
            for section in api_sections:
                try:
                    result = self.client.table(section['table']).insert(section['data']).execute()
                    if result.data:
                        successful_sections.append(section['name'])
                        section_test = {
                            'name': f"{section['name']} Insertion",
                            'status': 'PASS',
                            'details': f"Successfully inserted data into {section['table']}",
                            'table': section['table']
                        }
                    else:
                        failed_sections.append(section['name'])
                        section_test = {
                            'name': f"{section['name']} Insertion",
                            'status': 'FAIL',
                            'details': f"Failed to insert data into {section['table']} - no data returned",
                            'table': section['table']
                        }
                        
                except Exception as e:
                    failed_sections.append(section['name'])
                    section_test = {
                        'name': f"{section['name']} Insertion",
                        'status': 'FAIL',
                        'details': f"Exception during insertion: {str(e)}",
                        'table': section['table'],
                        'error': str(e)
                    }
                    test_suite['critical_issues'].append(f"{section['name']}: {str(e)}")
                
                test_suite['tests'].append(section_test)
                time.sleep(0.1)  # 부하 방지를 위한 짧은 대기
            
            # 결과 요약
            summary_test = {
                'name': 'API Sections Summary',
                'status': 'PASS' if len(failed_sections) == 0 else ('PARTIAL' if len(successful_sections) > 0 else 'FAIL'),
                'details': f"Successful: {len(successful_sections)}/{len(api_sections)} sections",
                'successful_sections': successful_sections,
                'failed_sections': failed_sections
            }
            test_suite['tests'].append(summary_test)
            
            # 전체 상태 결정
            if len(failed_sections) == 0:
                test_suite['status'] = 'PASS'
            elif len(successful_sections) > len(failed_sections):
                test_suite['status'] = 'PARTIAL'
            else:
                test_suite['status'] = 'FAIL'
                
        except Exception as e:
            logger.error(f"데이터 삽입 테스트 오류: {e}")
            test_suite['status'] = 'ERROR'
            test_suite['critical_issues'].append(f"Test setup error: {str(e)}")
            
        finally:
            # 테스트 데이터 정리
            if test_property_id:
                try:
                    self.client.table('properties_new').delete().eq('id', test_property_id).execute()
                    logger.info(f"🧹 테스트 매물 정리 완료: ID {test_property_id}")
                except Exception as e:
                    logger.warning(f"테스트 매물 정리 실패: {e}")
            
            if test_realtor_id:
                try:
                    self.client.table('realtors').delete().eq('id', test_realtor_id).execute()
                    logger.info(f"🧹 테스트 중개사 정리 완료: ID {test_realtor_id}")
                except Exception as e:
                    logger.warning(f"테스트 중개사 정리 실패: {e}")
        
        test_suite['duration_seconds'] = time.time() - start_time
        return test_suite
    
    def test_performance_benchmarking(self) -> Dict:
        """성능 벤치마킹 테스트"""
        logger.info("⚡ 성능 벤치마킹 테스트 시작...")
        
        test_suite = {
            'name': 'Performance Benchmarking',
            'status': 'UNKNOWN',
            'tests': [],
            'duration_seconds': 0,
            'performance_metrics': {},
            'critical_issues': []
        }
        
        start_time = time.time()
        
        try:
            # 성능 테스트 쿼리들
            performance_tests = [
                {
                    'name': 'Simple Property Count',
                    'description': '기본 매물 개수 조회',
                    'table': 'properties_new',
                    'query_type': 'count'
                },
                {
                    'name': 'Property Search with Filters',
                    'description': '필터링된 매물 검색',
                    'table': 'properties_new', 
                    'query_type': 'filtered_search'
                },
                {
                    'name': 'Complex Join Query',
                    'description': '복잡한 조인 쿼리',
                    'table': 'property_full_info',
                    'query_type': 'complex_join'
                },
                {
                    'name': 'Aggregation Query',
                    'description': '집계 쿼리',
                    'table': 'properties_new',
                    'query_type': 'aggregation'
                }
            ]
            
            for perf_test in performance_tests:
                test_start = time.time()
                
                try:
                    if perf_test['query_type'] == 'count':
                        result = self.client.table(perf_test['table']).select('*', count='exact').limit(1).execute()
                        row_count = result.count if hasattr(result, 'count') else 0
                        
                    elif perf_test['query_type'] == 'filtered_search':
                        result = self.client.table(perf_test['table'])\
                            .select('*')\
                            .eq('is_active', True)\
                            .limit(100)\
                            .execute()
                        row_count = len(result.data) if result.data else 0
                        
                    elif perf_test['query_type'] == 'complex_join':
                        # property_full_info 뷰 사용 (복잡한 조인)
                        result = self.client.table('property_full_info')\
                            .select('*')\
                            .limit(50)\
                            .execute()
                        row_count = len(result.data) if result.data else 0
                        
                    elif perf_test['query_type'] == 'aggregation':
                        # 지역별 매물 수 집계
                        result = self.client.rpc('get_properties_by_region').execute()
                        row_count = len(result.data) if result.data else 0
                    
                    execution_time = time.time() - test_start
                    
                    # 성능 등급 결정
                    if execution_time < 0.5:
                        performance_grade = 'EXCELLENT'
                    elif execution_time < 1.0:
                        performance_grade = 'GOOD'
                    elif execution_time < 2.0:
                        performance_grade = 'ACCEPTABLE'
                    else:
                        performance_grade = 'SLOW'
                    
                    perf_result = {
                        'name': perf_test['name'],
                        'status': 'PASS' if performance_grade != 'SLOW' else 'SLOW',
                        'execution_time_seconds': round(execution_time, 3),
                        'rows_processed': row_count,
                        'performance_grade': performance_grade,
                        'details': perf_test['description']
                    }
                    
                    test_suite['tests'].append(perf_result)
                    test_suite['performance_metrics'][perf_test['name']] = {
                        'execution_time': execution_time,
                        'rows': row_count,
                        'grade': performance_grade
                    }
                    
                    if performance_grade == 'SLOW':
                        test_suite['critical_issues'].append(f"Slow query: {perf_test['name']} ({execution_time:.2f}s)")
                    
                except Exception as e:
                    error_result = {
                        'name': perf_test['name'],
                        'status': 'ERROR',
                        'details': f"Performance test failed: {str(e)}",
                        'error': str(e)
                    }
                    test_suite['tests'].append(error_result)
                    test_suite['critical_issues'].append(f"Performance test error: {perf_test['name']}")
            
            # 전체 성능 등급 결정
            slow_queries = [t for t in test_suite['tests'] if t.get('status') == 'SLOW']
            error_queries = [t for t in test_suite['tests'] if t.get('status') == 'ERROR']
            
            if error_queries:
                test_suite['status'] = 'ERROR'
            elif slow_queries:
                test_suite['status'] = 'SLOW'
            else:
                test_suite['status'] = 'PASS'
                
        except Exception as e:
            logger.error(f"성능 벤치마킹 오류: {e}")
            test_suite['status'] = 'ERROR'
            test_suite['critical_issues'].append(f"Benchmarking error: {str(e)}")
        
        test_suite['duration_seconds'] = time.time() - start_time
        return test_suite
    
    def test_data_completeness_monitoring(self) -> Dict:
        """데이터 완성도 모니터링 테스트"""
        logger.info("📊 데이터 완성도 모니터링 테스트 시작...")
        
        test_suite = {
            'name': 'Data Completeness Monitoring',
            'status': 'UNKNOWN',
            'tests': [],
            'duration_seconds': 0,
            'completeness_metrics': {},
            'critical_issues': []
        }
        
        start_time = time.time()
        
        try:
            # 핵심 테이블들의 데이터 완성도 체크
            tables_to_monitor = [
                {
                    'table': 'properties_new',
                    'required_fields': ['article_no', 'article_name', 'real_estate_type_id', 'region_id'],
                    'optional_fields': ['description', 'tag_list']
                },
                {
                    'table': 'property_locations',
                    'required_fields': ['property_id', 'latitude', 'longitude'],
                    'optional_fields': ['address_road', 'subway_stations', 'nearest_station']
                },
                {
                    'table': 'property_physical',
                    'required_fields': ['property_id', 'area_exclusive'],
                    'optional_fields': ['area_supply', 'floor_current', 'room_count']
                },
                {
                    'table': 'property_prices',
                    'required_fields': ['property_id', 'amount', 'price_type'],
                    'optional_fields': ['valid_from', 'valid_to']
                }
            ]
            
            overall_completeness = []
            
            for table_info in tables_to_monitor:
                try:
                    # 전체 레코드 수 조회
                    total_result = self.client.table(table_info['table']).select('*', count='exact').limit(1).execute()
                    total_count = total_result.count if hasattr(total_result, 'count') else 0
                    
                    if total_count == 0:
                        completeness_test = {
                            'name': f"{table_info['table']} Completeness",
                            'status': 'EMPTY',
                            'details': 'Table has no records',
                            'total_records': 0,
                            'completeness_percentage': 0
                        }
                        test_suite['tests'].append(completeness_test)
                        test_suite['critical_issues'].append(f"Empty table: {table_info['table']}")
                        continue
                    
                    # 샘플 데이터로 필드 완성도 체크 (성능 고려)
                    sample_size = min(100, total_count)
                    sample_result = self.client.table(table_info['table']).select('*').limit(sample_size).execute()
                    
                    if not sample_result.data:
                        continue
                    
                    # 필수 필드 완성도 계산
                    field_completeness = {}
                    for field in table_info['required_fields'] + table_info['optional_fields']:
                        non_null_count = sum(1 for record in sample_result.data 
                                           if record.get(field) is not None and record.get(field) != '')
                        field_completeness[field] = (non_null_count / len(sample_result.data)) * 100
                    
                    # 필수 필드 평균 완성도
                    required_completeness = sum(field_completeness.get(field, 0) 
                                              for field in table_info['required_fields']) / len(table_info['required_fields'])
                    
                    # 전체 평균 완성도
                    all_fields = table_info['required_fields'] + table_info['optional_fields']
                    overall_table_completeness = sum(field_completeness.get(field, 0) 
                                                   for field in all_fields) / len(all_fields)
                    
                    # 완성도 등급 결정
                    if required_completeness >= 95:
                        status = 'EXCELLENT'
                    elif required_completeness >= 80:
                        status = 'GOOD'
                    elif required_completeness >= 60:
                        status = 'FAIR'
                    else:
                        status = 'POOR'
                    
                    completeness_test = {
                        'name': f"{table_info['table']} Completeness",
                        'status': status,
                        'details': f"Required fields: {required_completeness:.1f}%, Overall: {overall_table_completeness:.1f}%",
                        'total_records': total_count,
                        'sample_size': sample_size,
                        'required_completeness': round(required_completeness, 2),
                        'overall_completeness': round(overall_table_completeness, 2),
                        'field_completeness': field_completeness
                    }
                    
                    test_suite['tests'].append(completeness_test)
                    test_suite['completeness_metrics'][table_info['table']] = {
                        'required_completeness': required_completeness,
                        'overall_completeness': overall_table_completeness,
                        'status': status
                    }
                    
                    overall_completeness.append(overall_table_completeness)
                    
                    if status in ['POOR', 'FAIR']:
                        test_suite['critical_issues'].append(
                            f"Low completeness in {table_info['table']}: {required_completeness:.1f}%"
                        )
                
                except Exception as e:
                    error_test = {
                        'name': f"{table_info['table']} Completeness",
                        'status': 'ERROR',
                        'details': f"Completeness check failed: {str(e)}",
                        'error': str(e)
                    }
                    test_suite['tests'].append(error_test)
                    test_suite['critical_issues'].append(f"Completeness check error: {table_info['table']}")
            
            # 전체 데이터 완성도 요약
            if overall_completeness:
                avg_completeness = sum(overall_completeness) / len(overall_completeness)
                summary_test = {
                    'name': 'Overall Data Completeness',
                    'status': 'PASS' if avg_completeness >= 70 else 'NEEDS_IMPROVEMENT',
                    'details': f"Average completeness across all tables: {avg_completeness:.1f}%",
                    'average_completeness': round(avg_completeness, 2),
                    'tables_monitored': len(tables_to_monitor)
                }
                test_suite['tests'].append(summary_test)
                
                if avg_completeness < 70:
                    test_suite['status'] = 'NEEDS_IMPROVEMENT'
                else:
                    test_suite['status'] = 'PASS'
            else:
                test_suite['status'] = 'ERROR'
                
        except Exception as e:
            logger.error(f"데이터 완성도 모니터링 오류: {e}")
            test_suite['status'] = 'ERROR'
            test_suite['critical_issues'].append(f"Completeness monitoring error: {str(e)}")
        
        test_suite['duration_seconds'] = time.time() - start_time
        return test_suite
    
    def generate_comprehensive_report(self) -> Dict:
        """종합 테스트 리포트 생성"""
        logger.info("📋 종합 테스트 리포트 생성 중...")
        
        try:
            # 모든 테스트 스위트 실행
            schema_validation = self.test_schema_structure_validation()
            self.test_results['test_suites'].append(schema_validation)
            
            data_insertion = self.test_data_insertion_all_sections()
            self.test_results['test_suites'].append(data_insertion)
            
            performance_bench = self.test_performance_benchmarking()
            self.test_results['test_suites'].append(performance_bench)
            
            completeness_monitor = self.test_data_completeness_monitoring()
            self.test_results['test_suites'].append(completeness_monitor)
            
            # 전체 결과 분석
            all_suites_passed = all(suite['status'] in ['PASS', 'PARTIAL'] for suite in self.test_results['test_suites'])
            critical_failures = []
            
            for suite in self.test_results['test_suites']:
                if suite.get('critical_issues'):
                    critical_failures.extend(suite['critical_issues'])
            
            # 성능 메트릭스 통합
            for suite in self.test_results['test_suites']:
                if suite.get('performance_metrics'):
                    self.test_results['performance_metrics'].update(suite['performance_metrics'])
                if suite.get('completeness_metrics'):
                    self.test_results['performance_metrics'].update(suite['completeness_metrics'])
            
            self.test_results['critical_failures'] = critical_failures
            
            # 전체 상태 결정
            if not critical_failures and all_suites_passed:
                self.test_results['overall_status'] = 'ALL_PASS'
            elif len([s for s in self.test_results['test_suites'] if s['status'] in ['PASS', 'PARTIAL']]) >= 3:
                self.test_results['overall_status'] = 'MOSTLY_PASS'
            else:
                self.test_results['overall_status'] = 'NEEDS_ATTENTION'
            
            # 권장사항 생성
            recommendations = []
            
            if critical_failures:
                recommendations.append("🔴 Critical issues found - immediate attention required")
                recommendations.extend([f"  - {issue}" for issue in critical_failures[:5]])  # 상위 5개만
            
            performance_issues = [suite for suite in self.test_results['test_suites'] 
                                if suite['status'] in ['SLOW', 'NEEDS_IMPROVEMENT']]
            if performance_issues:
                recommendations.append("⚡ Performance optimization recommended")
            
            if self.test_results['overall_status'] == 'ALL_PASS':
                recommendations.append("✅ All tests passed - schema deployment successful")
                recommendations.append("📊 Continue with regular monitoring")
            
            self.test_results['recommendations'] = recommendations
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"종합 리포트 생성 오류: {e}")
            self.test_results['overall_status'] = 'ERROR'
            self.test_results['critical_failures'] = [f"Report generation error: {str(e)}"]
            return self.test_results
    
    def save_report_to_file(self, filename: str = None) -> str:
        """테스트 리포트를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"schema_validation_report_{timestamp}.json"
        
        try:
            filepath = current_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 테스트 리포트 저장: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"리포트 저장 실패: {e}")
            return ""
    
    def print_summary_report(self):
        """요약 리포트 콘솔 출력"""
        print("\n" + "="*80)
        print("📊 AUTOMATED SCHEMA VALIDATION SUMMARY")
        print("="*80)
        
        print(f"\n🎯 Overall Status: {self.test_results['overall_status']}")
        print(f"📅 Test Timestamp: {self.test_results['timestamp']}")
        
        print(f"\n📋 Test Suites Results:")
        for suite in self.test_results['test_suites']:
            status_emoji = {
                'PASS': '✅', 'PARTIAL': '🟡', 'FAIL': '❌', 
                'ERROR': '🔥', 'SLOW': '🐌', 'NEEDS_IMPROVEMENT': '⚠️'
            }.get(suite['status'], '❓')
            
            print(f"  {status_emoji} {suite['name']}: {suite['status']}")
            print(f"     Duration: {suite['duration_seconds']:.2f}s, Tests: {len(suite['tests'])}")
            
            if suite.get('critical_issues'):
                print(f"     Issues: {len(suite['critical_issues'])} critical")
        
        if self.test_results['critical_failures']:
            print(f"\n🚨 Critical Issues ({len(self.test_results['critical_failures'])}):")
            for issue in self.test_results['critical_failures'][:10]:  # 상위 10개만
                print(f"  - {issue}")
        
        if self.test_results['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in self.test_results['recommendations']:
                print(f"  {rec}")
        
        print(f"\n📈 Performance Metrics:")
        for metric_name, metric_data in self.test_results['performance_metrics'].items():
            if isinstance(metric_data, dict) and 'execution_time' in metric_data:
                print(f"  {metric_name}: {metric_data['execution_time']:.3f}s ({metric_data.get('grade', 'N/A')})")
        
        print("\n" + "="*80)

def main():
    """메인 실행 함수"""
    print("🚀 자동화된 스키마 테스트 스위트 시작")
    print("="*60)
    
    # 테스트 스위트 인스턴스 생성
    test_suite = AutomatedSchemaTestSuite()
    
    try:
        # 종합 테스트 실행
        logger.info("전체 테스트 스위트 실행 시작...")
        results = test_suite.generate_comprehensive_report()
        
        # 리포트 저장
        report_file = test_suite.save_report_to_file()
        
        # 요약 리포트 출력
        test_suite.print_summary_report()
        
        # 실행 결과에 따른 exit code 결정
        if results['overall_status'] == 'ALL_PASS':
            print("\n🎉 모든 테스트 통과! 스키마 배포가 성공적으로 완료되었습니다.")
            exit_code = 0
        elif results['overall_status'] == 'MOSTLY_PASS':
            print("\n⚠️ 대부분의 테스트 통과. 일부 개선사항이 있습니다.")
            exit_code = 0
        else:
            print("\n❌ 테스트 실패. 스키마 배포에 문제가 있습니다.")
            exit_code = 1
        
        if report_file:
            print(f"\n📄 상세 리포트: {report_file}")
        
        return exit_code
        
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 테스트가 중단되었습니다.")
        return 1
    except Exception as e:
        logger.error(f"테스트 스위트 실행 중 오류: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)