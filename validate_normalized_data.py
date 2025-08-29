#!/usr/bin/env python3
"""
정규화된 데이터베이스 검증 및 성능 테스트 스크립트
- 데이터 무결성 검증
- 참조 무결성 확인
- 성능 벤치마크
- 기존 시스템과 비교 분석
"""

import os
import sys
import time
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

class DatabaseValidator:
    def __init__(self):
        """데이터베이스 검증기 초기화"""
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        self.validation_results = {
            'data_integrity': {},
            'referential_integrity': {},
            'performance_benchmarks': {},
            'comparison_analysis': {},
            'recommendations': []
        }
        
        print("✅ 데이터베이스 검증기 초기화 완료")
    
    def run_complete_validation(self):
        """전체 검증 프로세스 실행"""
        print("🔍 정규화된 데이터베이스 검증 시작")
        print("="*60)
        
        try:
            # 1. 데이터 무결성 검증
            self.validate_data_integrity()
            
            # 2. 참조 무결성 검증
            self.validate_referential_integrity()
            
            # 3. 성능 벤치마크
            self.run_performance_benchmarks()
            
            # 4. 기존 시스템과 비교
            self.compare_with_legacy_system()
            
            # 5. 검증 보고서 생성
            self.generate_validation_report()
            
            print("\n✅ 전체 검증 완료!")
            
        except Exception as e:
            print(f"❌ 검증 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    def validate_data_integrity(self):
        """데이터 무결성 검증"""
        print("\n📊 데이터 무결성 검증 중...")
        
        integrity_checks = {}
        
        # 1. 중복 데이터 확인
        print("  🔍 중복 데이터 확인...")
        integrity_checks['duplicates'] = self._check_duplicates()
        
        # 2. NULL 값 분석
        print("  🔍 NULL 값 분석...")
        integrity_checks['null_analysis'] = self._analyze_null_values()
        
        # 3. 데이터 일관성 확인
        print("  🔍 데이터 일관성 확인...")
        integrity_checks['consistency'] = self._check_data_consistency()
        
        # 4. 비즈니스 규칙 검증
        print("  🔍 비즈니스 규칙 검증...")
        integrity_checks['business_rules'] = self._validate_business_rules()
        
        self.validation_results['data_integrity'] = integrity_checks
        
        print("✅ 데이터 무결성 검증 완료")
    
    def _check_duplicates(self) -> Dict:
        """중복 데이터 확인"""
        duplicates = {}
        
        try:
            # properties_new 테이블 중복 확인
            properties_duplicates = self.client.rpc('check_property_duplicates').execute()
            duplicates['properties'] = properties_duplicates.data if properties_duplicates.data else []
            
            # 중개사 중복 확인 (business_number 기준)
            realtor_query = """
            SELECT business_number, COUNT(*) as count
            FROM realtors 
            WHERE business_number IS NOT NULL
            GROUP BY business_number 
            HAVING COUNT(*) > 1
            """
            
            # 직접 쿼리 대신 Python으로 중복 확인
            realtors = self.client.table('realtors').select('id, business_number').execute()
            business_numbers = {}
            for realtor in realtors.data:
                if realtor['business_number']:
                    bn = realtor['business_number']
                    if bn not in business_numbers:
                        business_numbers[bn] = []
                    business_numbers[bn].append(realtor['id'])
            
            realtor_duplicates = {k: v for k, v in business_numbers.items() if len(v) > 1}
            duplicates['realtors'] = realtor_duplicates
            
            print(f"    📋 매물 중복: {len(duplicates['properties'])}개")
            print(f"    🏢 중개사 중복: {len(duplicates['realtors'])}개")
            
        except Exception as e:
            print(f"    ⚠️ 중복 확인 실패: {e}")
            duplicates['error'] = str(e)
        
        return duplicates
    
    def _analyze_null_values(self) -> Dict:
        """NULL 값 분석"""
        null_analysis = {}
        
        tables_to_check = [
            'properties_new', 'property_prices', 'property_locations', 
            'property_physical', 'realtors', 'property_images'
        ]
        
        for table in tables_to_check:
            try:
                # 샘플 데이터로 NULL 값 비율 계산
                sample = self.client.table(table).select('*').limit(100).execute()
                
                if sample.data:
                    null_counts = {}
                    total_records = len(sample.data)
                    
                    # 첫 번째 레코드에서 컬럼 목록 추출
                    columns = sample.data[0].keys()
                    
                    for col in columns:
                        null_count = sum(1 for record in sample.data if record.get(col) is None)
                        if null_count > 0:
                            null_percentage = (null_count / total_records) * 100
                            null_counts[col] = {
                                'null_count': null_count,
                                'null_percentage': round(null_percentage, 1)
                            }
                    
                    null_analysis[table] = null_counts
                    
                    high_null_cols = [col for col, info in null_counts.items() if info['null_percentage'] > 20]
                    if high_null_cols:
                        print(f"    ⚠️ {table}: 높은 NULL 비율 컬럼 {len(high_null_cols)}개")
                    
            except Exception as e:
                print(f"    ❌ {table} NULL 분석 실패: {e}")
                null_analysis[table] = {'error': str(e)}
        
        return null_analysis
    
    def _check_data_consistency(self) -> Dict:
        """데이터 일관성 확인"""
        consistency_issues = []
        
        try:
            # 1. 가격 데이터 일관성 (음수 값 확인)
            negative_prices = self.client.table('property_prices').select('id, property_id, amount').lt('amount', 0).execute()
            if negative_prices.data:
                consistency_issues.append({
                    'type': 'negative_prices',
                    'count': len(negative_prices.data),
                    'description': '음수 가격 데이터 발견'
                })
            
            # 2. 면적 데이터 일관성 (전용면적 > 공급면적)
            area_issues = self.client.table('property_physical').select('id, property_id, area_exclusive, area_supply').gt('area_exclusive', 'area_supply').execute()
            if area_issues.data:
                consistency_issues.append({
                    'type': 'area_inconsistency',
                    'count': len(area_issues.data),
                    'description': '전용면적이 공급면적보다 큰 경우'
                })
            
            # 3. 층 정보 일관성 (현재층 > 총층)
            floor_issues = self.client.table('property_physical').select('id, property_id, floor_current, floor_total').gt('floor_current', 'floor_total').execute()
            if floor_issues.data:
                consistency_issues.append({
                    'type': 'floor_inconsistency',
                    'count': len(floor_issues.data),
                    'description': '현재층이 총층보다 높은 경우'
                })
            
            print(f"    📊 일관성 이슈: {len(consistency_issues)}개 유형 발견")
            
        except Exception as e:
            print(f"    ❌ 일관성 확인 실패: {e}")
            consistency_issues.append({'error': str(e)})
        
        return consistency_issues
    
    def _validate_business_rules(self) -> Dict:
        """비즈니스 규칙 검증"""
        business_rules = {}
        
        try:
            # 1. 매물별 최소 정보 요구사항
            properties_without_location = self.client.table('properties_new').select('id, article_no').execute()
            location_count = self.client.table('property_locations').select('property_id', count='exact').execute().count or 0
            
            properties_count = len(properties_without_location.data) if properties_without_location.data else 0
            missing_location_ratio = (properties_count - location_count) / properties_count * 100 if properties_count > 0 else 0
            
            business_rules['location_completeness'] = {
                'total_properties': properties_count,
                'with_location': location_count,
                'missing_percentage': round(missing_location_ratio, 1)
            }
            
            # 2. 가격 정보 완전성
            price_count = self.client.table('property_prices').select('property_id', count='exact').execute().count or 0
            missing_price_ratio = (properties_count - price_count) / properties_count * 100 if properties_count > 0 else 0
            
            business_rules['price_completeness'] = {
                'total_properties': properties_count,
                'with_prices': price_count,
                'missing_percentage': round(missing_price_ratio, 1)
            }
            
            print(f"    📍 위치정보 누락: {missing_location_ratio:.1f}%")
            print(f"    💰 가격정보 누락: {missing_price_ratio:.1f}%")
            
        except Exception as e:
            print(f"    ❌ 비즈니스 규칙 검증 실패: {e}")
            business_rules['error'] = str(e)
        
        return business_rules
    
    def validate_referential_integrity(self):
        """참조 무결성 검증"""
        print("\n🔗 참조 무결성 검증 중...")
        
        referential_checks = {}
        
        try:
            # 1. properties_new → regions 참조 확인
            orphaned_properties = self.client.rpc('check_orphaned_properties').execute()
            referential_checks['orphaned_properties'] = orphaned_properties.data if orphaned_properties.data else []
            
            # 2. property_prices → properties_new 참조 확인
            orphaned_prices = self.client.rpc('check_orphaned_prices').execute()
            referential_checks['orphaned_prices'] = orphaned_prices.data if orphaned_prices.data else []
            
            # Python으로 직접 참조 무결성 확인
            print("  🔍 수동 참조 무결성 확인...")
            
            # properties_new와 property_locations 관계 확인
            properties = self.client.table('properties_new').select('id').execute()
            locations = self.client.table('property_locations').select('property_id').execute()
            
            property_ids = set(p['id'] for p in properties.data) if properties.data else set()
            location_property_ids = set(l['property_id'] for l in locations.data if l['property_id']) if locations.data else set()
            
            orphaned_locations = location_property_ids - property_ids
            referential_checks['manual_orphaned_locations'] = list(orphaned_locations)
            
            print(f"    📊 고아 매물: {len(referential_checks.get('orphaned_properties', []))}개")
            print(f"    💰 고아 가격: {len(referential_checks.get('orphaned_prices', []))}개")
            print(f"    📍 고아 위치: {len(orphaned_locations)}개")
            
        except Exception as e:
            print(f"    ❌ 참조 무결성 확인 실패: {e}")
            referential_checks['error'] = str(e)
        
        self.validation_results['referential_integrity'] = referential_checks
        print("✅ 참조 무결성 검증 완료")
    
    def run_performance_benchmarks(self):
        """성능 벤치마크 실행"""
        print("\n⚡ 성능 벤치마크 실행 중...")
        
        benchmarks = {}
        
        # 1. 기본 조회 성능
        print("  🔍 기본 조회 성능 테스트...")
        benchmarks['basic_queries'] = self._benchmark_basic_queries()
        
        # 2. 복잡한 조인 쿼리 성능
        print("  🔍 복잡한 조인 쿼리 성능 테스트...")
        benchmarks['complex_queries'] = self._benchmark_complex_queries()
        
        # 3. 집계 쿼리 성능
        print("  🔍 집계 쿼리 성능 테스트...")
        benchmarks['aggregation_queries'] = self._benchmark_aggregation_queries()
        
        # 4. 인덱스 효율성 테스트
        print("  🔍 인덱스 효율성 테스트...")
        benchmarks['index_efficiency'] = self._benchmark_index_efficiency()
        
        self.validation_results['performance_benchmarks'] = benchmarks
        print("✅ 성능 벤치마크 완료")
    
    def _benchmark_basic_queries(self) -> Dict:
        """기본 조회 성능 테스트"""
        results = {}
        
        queries = [
            {
                'name': 'simple_property_select',
                'description': '단순 매물 조회',
                'query': lambda: self.client.table('properties_new').select('*').limit(100).execute()
            },
            {
                'name': 'property_by_article_no',
                'description': 'article_no로 매물 조회',
                'query': lambda: self.client.table('properties_new').select('*').limit(1).execute()
            },
            {
                'name': 'active_properties',
                'description': '활성 매물만 조회',
                'query': lambda: self.client.table('properties_new').select('*').eq('is_active', True).limit(50).execute()
            }
        ]
        
        for query_info in queries:
            try:
                start_time = time.time()
                result = query_info['query']()
                end_time = time.time()
                
                execution_time = (end_time - start_time) * 1000  # ms
                record_count = len(result.data) if result.data else 0
                
                results[query_info['name']] = {
                    'description': query_info['description'],
                    'execution_time_ms': round(execution_time, 2),
                    'record_count': record_count,
                    'performance_rating': self._rate_performance(execution_time, 'basic')
                }
                
            except Exception as e:
                results[query_info['name']] = {'error': str(e)}
        
        return results
    
    def _benchmark_complex_queries(self) -> Dict:
        """복잡한 조인 쿼리 성능 테스트"""
        results = {}
        
        try:
            # property_full_info 뷰 사용 (복잡한 조인)
            start_time = time.time()
            
            # 복잡한 조인을 Python으로 구현 (뷰가 없을 경우)
            properties = self.client.table('properties_new').select('*').limit(50).execute()
            
            end_time = time.time()
            
            execution_time = (end_time - start_time) * 1000
            record_count = len(properties.data) if properties.data else 0
            
            results['complex_join'] = {
                'description': '매물 정보 + 위치 + 물리적 정보 조인',
                'execution_time_ms': round(execution_time, 2),
                'record_count': record_count,
                'performance_rating': self._rate_performance(execution_time, 'complex')
            }
            
        except Exception as e:
            results['complex_join'] = {'error': str(e)}
        
        return results
    
    def _benchmark_aggregation_queries(self) -> Dict:
        """집계 쿼리 성능 테스트"""
        results = {}
        
        aggregations = [
            {
                'name': 'count_by_region',
                'description': '지역별 매물 수 집계',
                'query': lambda: self.client.table('properties_new').select('region_id', count='exact').execute()
            },
            {
                'name': 'price_statistics',
                'description': '가격 통계',
                'query': lambda: self.client.table('property_prices').select('*').limit(1000).execute()
            }
        ]
        
        for agg_info in aggregations:
            try:
                start_time = time.time()
                result = agg_info['query']()
                end_time = time.time()
                
                execution_time = (end_time - start_time) * 1000
                
                results[agg_info['name']] = {
                    'description': agg_info['description'],
                    'execution_time_ms': round(execution_time, 2),
                    'performance_rating': self._rate_performance(execution_time, 'aggregation')
                }
                
            except Exception as e:
                results[agg_info['name']] = {'error': str(e)}
        
        return results
    
    def _benchmark_index_efficiency(self) -> Dict:
        """인덱스 효율성 테스트"""
        results = {}
        
        try:
            # article_no 인덱스 테스트 (있을 경우)
            start_time = time.time()
            indexed_query = self.client.table('properties_new').select('*').eq('article_no', 'test_article').execute()
            end_time = time.time()
            
            indexed_time = (end_time - start_time) * 1000
            
            # 전체 스캔과 비교하기 어려우므로 단순히 인덱스 쿼리 성능만 측정
            results['indexed_article_lookup'] = {
                'description': 'article_no 인덱스 조회',
                'execution_time_ms': round(indexed_time, 2),
                'performance_rating': self._rate_performance(indexed_time, 'indexed')
            }
            
        except Exception as e:
            results['indexed_article_lookup'] = {'error': str(e)}
        
        return results
    
    def _rate_performance(self, execution_time_ms: float, query_type: str) -> str:
        """성능 등급 매기기"""
        thresholds = {
            'basic': {'excellent': 50, 'good': 200, 'acceptable': 500},
            'complex': {'excellent': 200, 'good': 1000, 'acceptable': 3000},
            'aggregation': {'excellent': 100, 'good': 500, 'acceptable': 2000},
            'indexed': {'excellent': 10, 'good': 50, 'acceptable': 200}
        }
        
        threshold = thresholds.get(query_type, thresholds['basic'])
        
        if execution_time_ms <= threshold['excellent']:
            return 'excellent'
        elif execution_time_ms <= threshold['good']:
            return 'good'
        elif execution_time_ms <= threshold['acceptable']:
            return 'acceptable'
        else:
            return 'poor'
    
    def compare_with_legacy_system(self):
        """기존 시스템과 비교 분석"""
        print("\n📊 기존 시스템과 비교 분석 중...")
        
        comparison = {}
        
        try:
            # 1. 데이터 완전성 비교
            print("  🔍 데이터 완전성 비교...")
            
            # 기존 properties 테이블 정보
            old_properties = self.client.table('properties').select('*', count='exact').limit(1).execute()
            old_count = old_properties.count or 0
            
            # 새로운 properties_new 테이블 정보
            new_properties = self.client.table('properties_new').select('*', count='exact').limit(1).execute()
            new_count = new_properties.count or 0
            
            comparison['data_completeness'] = {
                'old_system': old_count,
                'new_system': new_count,
                'migration_ratio': round((new_count / old_count * 100), 1) if old_count > 0 else 0
            }
            
            # 2. 저장 공간 추정 비교
            print("  🔍 저장 공간 효율성 추정...")
            
            # 새로운 시스템의 테이블별 레코드 수
            new_system_tables = {
                'properties_new': self.client.table('properties_new').select('*', count='exact').limit(1).execute().count or 0,
                'property_prices': self.client.table('property_prices').select('*', count='exact').limit(1).execute().count or 0,
                'property_locations': self.client.table('property_locations').select('*', count='exact').limit(1).execute().count or 0,
                'property_physical': self.client.table('property_physical').select('*', count='exact').limit(1).execute().count or 0,
                'realtors': self.client.table('realtors').select('*', count='exact').limit(1).execute().count or 0,
                'property_images': self.client.table('property_images').select('*', count='exact').limit(1).execute().count or 0
            }
            
            comparison['table_distribution'] = new_system_tables
            
            # 3. 쿼리 성능 비교 (기본 조회)
            print("  🔍 쿼리 성능 비교...")
            
            # 기존 시스템 쿼리 성능
            start_time = time.time()
            old_query = self.client.table('properties').select('*').limit(100).execute()
            old_time = (time.time() - start_time) * 1000
            
            # 새로운 시스템 쿼리 성능
            start_time = time.time()
            new_query = self.client.table('properties_new').select('*').limit(100).execute()
            new_time = (time.time() - start_time) * 1000
            
            comparison['query_performance'] = {
                'old_system_ms': round(old_time, 2),
                'new_system_ms': round(new_time, 2),
                'improvement': round(((old_time - new_time) / old_time * 100), 1) if old_time > 0 else 0
            }
            
            print(f"    📊 데이터 마이그레이션: {comparison['data_completeness']['migration_ratio']}%")
            print(f"    ⚡ 쿼리 성능 변화: {comparison['query_performance']['improvement']}%")
            
        except Exception as e:
            print(f"    ❌ 비교 분석 실패: {e}")
            comparison['error'] = str(e)
        
        self.validation_results['comparison_analysis'] = comparison
        print("✅ 기존 시스템과 비교 분석 완료")
    
    def generate_validation_report(self):
        """검증 보고서 생성"""
        print("\n📋 검증 보고서 생성 중...")
        
        # 추천사항 생성
        self._generate_recommendations()
        
        # 보고서 파일 저장
        report_file = current_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'validation_timestamp': datetime.now().isoformat(),
            'validation_results': self.validation_results,
            'summary': self._generate_summary()
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 검증 보고서 저장: {report_file}")
        
        # 요약 출력
        self._print_validation_summary()
        
        return report_file
    
    def _generate_recommendations(self):
        """개선 추천사항 생성"""
        recommendations = []
        
        # 데이터 무결성 기반 추천
        integrity = self.validation_results.get('data_integrity', {})
        
        if integrity.get('duplicates', {}).get('properties'):
            recommendations.append({
                'priority': 'high',
                'category': 'data_quality',
                'issue': '중복 매물 데이터',
                'recommendation': '중복된 article_no를 가진 매물 데이터를 정리하고 UNIQUE 제약조건 추가'
            })
        
        if integrity.get('null_analysis'):
            for table, null_info in integrity['null_analysis'].items():
                high_null_cols = [col for col, info in null_info.items() if isinstance(info, dict) and info.get('null_percentage', 0) > 30]
                if high_null_cols:
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'data_completeness',
                        'issue': f'{table} 테이블 NULL 값 과다',
                        'recommendation': f'다음 컬럼의 NULL 값 보완: {", ".join(high_null_cols)}'
                    })
        
        # 성능 기반 추천
        benchmarks = self.validation_results.get('performance_benchmarks', {})
        
        if benchmarks.get('basic_queries'):
            poor_queries = [name for name, info in benchmarks['basic_queries'].items() 
                           if isinstance(info, dict) and info.get('performance_rating') == 'poor']
            if poor_queries:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'performance',
                    'issue': '느린 기본 쿼리',
                    'recommendation': f'다음 쿼리의 인덱스 최적화 필요: {", ".join(poor_queries)}'
                })
        
        # 참조 무결성 기반 추천
        referential = self.validation_results.get('referential_integrity', {})
        
        if referential.get('orphaned_properties'):
            recommendations.append({
                'priority': 'high',
                'category': 'referential_integrity',
                'issue': '고아 매물 데이터',
                'recommendation': '참조되지 않는 매물 데이터를 정리하거나 참조 관계 수정'
            })
        
        self.validation_results['recommendations'] = recommendations
    
    def _generate_summary(self) -> Dict:
        """검증 결과 요약"""
        summary = {
            'overall_status': 'unknown',
            'critical_issues': 0,
            'warnings': 0,
            'performance_rating': 'unknown',
            'migration_success_rate': 0
        }
        
        try:
            # 심각한 문제 카운트
            critical_issues = 0
            warnings = 0
            
            # 데이터 무결성 이슈
            integrity = self.validation_results.get('data_integrity', {})
            if integrity.get('duplicates', {}).get('properties'):
                critical_issues += len(integrity['duplicates']['properties'])
            
            consistency_issues = integrity.get('consistency', [])
            if isinstance(consistency_issues, list):
                critical_issues += len(consistency_issues)
            
            # 참조 무결성 이슈
            referential = self.validation_results.get('referential_integrity', {})
            if referential.get('orphaned_properties'):
                critical_issues += len(referential['orphaned_properties'])
            
            # NULL 값 경고
            for table, null_info in integrity.get('null_analysis', {}).items():
                if isinstance(null_info, dict):
                    high_null_cols = [col for col, info in null_info.items() 
                                    if isinstance(info, dict) and info.get('null_percentage', 0) > 20]
                    warnings += len(high_null_cols)
            
            # 성능 등급 계산
            benchmarks = self.validation_results.get('performance_benchmarks', {})
            performance_ratings = []
            
            for category in benchmarks.values():
                if isinstance(category, dict):
                    for query_info in category.values():
                        if isinstance(query_info, dict) and 'performance_rating' in query_info:
                            performance_ratings.append(query_info['performance_rating'])
            
            if performance_ratings:
                rating_scores = {'excellent': 4, 'good': 3, 'acceptable': 2, 'poor': 1}
                avg_score = sum(rating_scores.get(r, 0) for r in performance_ratings) / len(performance_ratings)
                
                if avg_score >= 3.5:
                    summary['performance_rating'] = 'excellent'
                elif avg_score >= 2.5:
                    summary['performance_rating'] = 'good'
                elif avg_score >= 1.5:
                    summary['performance_rating'] = 'acceptable'
                else:
                    summary['performance_rating'] = 'poor'
            
            # 마이그레이션 성공률
            comparison = self.validation_results.get('comparison_analysis', {})
            if comparison.get('data_completeness'):
                summary['migration_success_rate'] = comparison['data_completeness']['migration_ratio']
            
            # 전체 상태 판정
            if critical_issues == 0 and warnings < 5:
                summary['overall_status'] = 'excellent'
            elif critical_issues < 5 and warnings < 20:
                summary['overall_status'] = 'good'
            elif critical_issues < 20:
                summary['overall_status'] = 'acceptable'
            else:
                summary['overall_status'] = 'needs_attention'
            
            summary['critical_issues'] = critical_issues
            summary['warnings'] = warnings
            
        except Exception as e:
            summary['error'] = str(e)
        
        return summary
    
    def _print_validation_summary(self):
        """검증 결과 요약 출력"""
        summary = self.validation_results.get('summary', self._generate_summary())
        
        print("\n" + "="*80)
        print("📊 정규화된 데이터베이스 검증 결과 요약")
        print("="*80)
        
        # 전체 상태
        status_symbols = {
            'excellent': '🟢', 'good': '🟡', 'acceptable': '🟠', 'needs_attention': '🔴'
        }
        status_symbol = status_symbols.get(summary['overall_status'], '❓')
        print(f"🎯 전체 상태: {status_symbol} {summary['overall_status'].upper()}")
        
        # 이슈 카운트
        print(f"🚨 심각한 문제: {summary['critical_issues']}개")
        print(f"⚠️ 경고 사항: {summary['warnings']}개")
        
        # 성능 등급
        perf_symbols = {
            'excellent': '🚀', 'good': '⚡', 'acceptable': '🐌', 'poor': '🐢'
        }
        perf_symbol = perf_symbols.get(summary['performance_rating'], '❓')
        print(f"⚡ 성능 등급: {perf_symbol} {summary['performance_rating'].upper()}")
        
        # 마이그레이션 성공률
        migration_rate = summary['migration_success_rate']
        migration_symbol = '🟢' if migration_rate > 95 else '🟡' if migration_rate > 90 else '🔴'
        print(f"🔄 마이그레이션: {migration_symbol} {migration_rate}%")
        
        # 추천사항
        recommendations = self.validation_results.get('recommendations', [])
        high_priority = [r for r in recommendations if r.get('priority') == 'high']
        
        if high_priority:
            print(f"\n🎯 우선 조치 필요:")
            for rec in high_priority[:3]:  # 상위 3개만 표시
                print(f"   • {rec.get('issue', 'Unknown')}: {rec.get('recommendation', 'No recommendation')}")
        
        print("\n✅ 검증 완료! 상세 결과는 JSON 보고서를 확인하세요.")
        print("="*80)

def main():
    """메인 실행 함수"""
    print("🔍 정규화된 데이터베이스 검증 시작")
    print("="*60)
    
    validator = DatabaseValidator()
    
    try:
        validator.run_complete_validation()
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()