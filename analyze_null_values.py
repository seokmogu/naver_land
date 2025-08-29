#!/usr/bin/env python3
"""
데이터베이스 NULL 값 분석 및 데이터 무결성 검증 스크립트
- enhanced_data_collector.py와 정규화된 스키마 기반 분석
- NULL 값 발생 원인 및 패턴 식별
- 데이터 품질 개선 방안 제시
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

# 환경변수 설정
os.environ['SUPABASE_URL'] = 'https://eslhavjipwbyvbbknixv.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'

class NullValueAnalyzer:
    def __init__(self):
        """NULL 값 분석기 초기화"""
        try:
            self.client = create_client(
                os.environ['SUPABASE_URL'], 
                os.environ['SUPABASE_KEY']
            )
            print("✅ Supabase 연결 성공")
            
            self.analysis_results = {}
            self.null_patterns = defaultdict(int)
            self.data_quality_issues = []
            
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            sys.exit(1)
    
    def analyze_legacy_properties_table(self):
        """기존 properties 테이블 NULL 값 분석"""
        print("\n🔍 기존 properties 테이블 NULL 값 분석...")
        
        try:
            # 전체 레코드 수 조회
            count_result = self.client.table('properties').select('*', count='exact').limit(1).execute()
            total_count = count_result.count or 0
            
            if total_count == 0:
                print("⚠️ properties 테이블이 비어있습니다.")
                return
            
            print(f"📊 전체 레코드: {total_count:,}개")
            
            # 샘플 데이터로 NULL 패턴 분석
            sample_size = min(1000, total_count)
            sample_result = self.client.table('properties').select('*').limit(sample_size).execute()
            sample_data = sample_result.data
            
            print(f"📈 분석 샘플: {len(sample_data):,}개")
            
            # 컬럼별 NULL 통계
            null_stats = {}
            column_names = list(sample_data[0].keys()) if sample_data else []
            
            for column in column_names:
                null_count = sum(1 for record in sample_data if record.get(column) is None or record.get(column) == '' or record.get(column) == '-')
                null_percentage = (null_count / len(sample_data)) * 100
                
                null_stats[column] = {
                    'null_count': null_count,
                    'total_count': len(sample_data),
                    'null_percentage': null_percentage,
                    'data_type': self._detect_data_type(sample_data, column)
                }
            
            # NULL이 많은 컬럼 순으로 정렬
            sorted_nulls = sorted(null_stats.items(), key=lambda x: x[1]['null_percentage'], reverse=True)
            
            print(f"\n📋 컬럼별 NULL 값 통계 (상위 20개):")
            print(f"{'컬럼명':<25} {'NULL 비율':<10} {'NULL 개수':<8} {'전체':<8} {'데이터 타입':<15}")
            print("-" * 75)
            
            for column, stats in sorted_nulls[:20]:
                print(f"{column:<25} {stats['null_percentage']:>6.1f}% {stats['null_count']:>8,} {stats['total_count']:>8,} {stats['data_type']:<15}")
            
            self.analysis_results['legacy_properties'] = {
                'total_records': total_count,
                'sample_size': len(sample_data),
                'null_statistics': null_stats,
                'high_null_columns': [col for col, stats in sorted_nulls if stats['null_percentage'] > 50]
            }
            
            return null_stats
            
        except Exception as e:
            print(f"❌ properties 테이블 분석 실패: {e}")
            return None
    
    def analyze_normalized_tables(self):
        """정규화된 테이블들의 NULL 값 분석"""
        print("\n🔍 정규화된 테이블들 NULL 값 분석...")
        
        normalized_tables = [
            'properties_new', 'property_locations', 'property_physical', 
            'property_prices', 'property_images', 'property_facilities',
            'realtors', 'property_realtors'
        ]
        
        normalized_results = {}
        
        for table_name in normalized_tables:
            try:
                print(f"\n📋 {table_name} 테이블 분석...")
                
                # 테이블 존재 및 레코드 수 확인
                count_result = self.client.table(table_name).select('*', count='exact').limit(1).execute()
                record_count = count_result.count or 0
                
                if record_count == 0:
                    print(f"   📋 빈 테이블 (0개 레코드)")
                    normalized_results[table_name] = {'status': 'empty', 'record_count': 0}
                    continue
                
                # 샘플 데이터로 NULL 분석
                sample_size = min(500, record_count)
                sample_result = self.client.table(table_name).select('*').limit(sample_size).execute()
                sample_data = sample_result.data
                
                if not sample_data:
                    continue
                
                # 컬럼별 NULL 통계
                columns = list(sample_data[0].keys())
                table_null_stats = {}
                
                for column in columns:
                    null_count = sum(1 for record in sample_data if record.get(column) is None)
                    null_percentage = (null_count / len(sample_data)) * 100
                    
                    table_null_stats[column] = {
                        'null_count': null_count,
                        'null_percentage': null_percentage,
                        'sample_values': [record.get(column) for record in sample_data[:5] if record.get(column) is not None][:3]
                    }
                
                # 문제가 있는 컬럼들 식별
                critical_nulls = [(col, stats) for col, stats in table_null_stats.items() 
                                if stats['null_percentage'] > 30 and col not in ['id', 'created_at', 'updated_at']]
                
                if critical_nulls:
                    print(f"   ⚠️ 높은 NULL 비율 컬럼들:")
                    for col, stats in critical_nulls:
                        print(f"     - {col}: {stats['null_percentage']:.1f}% NULL")
                
                print(f"   ✅ {record_count:,}개 레코드, {len(columns)}개 컬럼")
                
                normalized_results[table_name] = {
                    'record_count': record_count,
                    'sample_size': len(sample_data),
                    'null_statistics': table_null_stats,
                    'critical_null_columns': [col for col, stats in critical_nulls]
                }
                
            except Exception as e:
                print(f"   ❌ {table_name} 분석 실패: {e}")
                normalized_results[table_name] = {'status': 'error', 'error': str(e)}
        
        self.analysis_results['normalized_tables'] = normalized_results
        return normalized_results
    
    def analyze_foreign_key_issues(self):
        """외래키 관련 NULL 값 문제 분석"""
        print("\n🔍 외래키 관련 NULL 값 문제 분석...")
        
        foreign_key_issues = {}
        
        try:
            # properties_new 테이블의 외래키 필드 분석
            if 'properties_new' in self.analysis_results.get('normalized_tables', {}):
                props_result = self.client.table('properties_new').select('*').limit(200).execute()
                props_data = props_result.data
                
                if props_data:
                    fk_fields = ['real_estate_type_id', 'trade_type_id', 'region_id']
                    fk_analysis = {}
                    
                    for fk_field in fk_fields:
                        null_count = sum(1 for record in props_data if record.get(fk_field) is None)
                        null_percentage = (null_count / len(props_data)) * 100
                        
                        fk_analysis[fk_field] = {
                            'null_count': null_count,
                            'null_percentage': null_percentage,
                            'total_records': len(props_data)
                        }
                        
                        if null_percentage > 10:
                            print(f"   ⚠️ {fk_field}: {null_percentage:.1f}% NULL ({null_count}개)")
                    
                    foreign_key_issues['properties_new'] = fk_analysis
            
            # 참조 테이블들의 데이터 존재 여부 확인
            reference_tables = ['real_estate_types', 'trade_types', 'regions']
            ref_status = {}
            
            for ref_table in reference_tables:
                try:
                    count_result = self.client.table(ref_table).select('*', count='exact').limit(1).execute()
                    record_count = count_result.count or 0
                    ref_status[ref_table] = record_count
                    print(f"   📊 {ref_table}: {record_count:,}개 레코드")
                except Exception as e:
                    ref_status[ref_table] = f"오류: {e}"
                    print(f"   ❌ {ref_table}: {e}")
            
            foreign_key_issues['reference_table_status'] = ref_status
            
        except Exception as e:
            print(f"❌ 외래키 분석 실패: {e}")
        
        self.analysis_results['foreign_key_issues'] = foreign_key_issues
        return foreign_key_issues
    
    def analyze_enhanced_collector_null_handling(self):
        """enhanced_data_collector.py의 NULL 처리 로직 분석"""
        print("\n🔍 enhanced_data_collector.py NULL 처리 로직 분석...")
        
        collector_analysis = {
            'safe_functions': {},
            'null_handling_patterns': {},
            'potential_issues': []
        }
        
        try:
            # enhanced_data_collector.py 파일 읽기
            collector_file = current_dir / 'enhanced_data_collector.py'
            if collector_file.exists():
                with open(collector_file, 'r', encoding='utf-8') as f:
                    collector_code = f.read()
                
                # safe_* 함수들 분석
                safe_functions = [
                    'safe_coordinate', 'safe_int', 'safe_float', 'safe_price', 
                    'safe_int_for_image'
                ]
                
                for func_name in safe_functions:
                    if func_name in collector_code:
                        collector_analysis['safe_functions'][func_name] = 'found'
                        print(f"   ✅ {func_name} 함수 발견")
                    else:
                        collector_analysis['safe_functions'][func_name] = 'missing'
                        print(f"   ❌ {func_name} 함수 누락")
                
                # 기본값 설정 패턴 분석
                default_value_patterns = [
                    ('area_exclusive = 10.0', '최소 면적 기본값'),
                    ('cortar_no = "1168010100"', '기본 지역 설정'),
                    ('real_estate_type = "알 수 없음"', '기본 부동산 유형'),
                    ('trade_type = "알 수 없음"', '기본 거래 유형')
                ]
                
                for pattern, description in default_value_patterns:
                    if pattern in collector_code:
                        collector_analysis['null_handling_patterns'][description] = 'implemented'
                        print(f"   ✅ {description}: 구현됨")
                    else:
                        collector_analysis['null_handling_patterns'][description] = 'missing'
                        print(f"   ⚠️ {description}: 누락")
                        collector_analysis['potential_issues'].append(f"{description} 패턴이 누락됨")
            
            else:
                print("   ❌ enhanced_data_collector.py 파일을 찾을 수 없음")
                collector_analysis['potential_issues'].append("enhanced_data_collector.py 파일 없음")
        
        except Exception as e:
            print(f"   ❌ 코드 분석 실패: {e}")
            collector_analysis['potential_issues'].append(f"코드 분석 오류: {e}")
        
        self.analysis_results['collector_analysis'] = collector_analysis
        return collector_analysis
    
    def identify_null_root_causes(self):
        """NULL 값 발생 원인 분석"""
        print("\n🔍 NULL 값 발생 원인 분석...")
        
        root_causes = {
            'api_response_missing_fields': [],
            'parsing_failures': [],
            'validation_failures': [],
            'foreign_key_resolution_failures': [],
            'data_transformation_issues': []
        }
        
        # 1. API 응답 누락 필드 분석
        legacy_stats = self.analysis_results.get('legacy_properties', {}).get('null_statistics', {})
        
        high_null_fields = []
        for field, stats in legacy_stats.items():
            if stats['null_percentage'] > 70:
                high_null_fields.append((field, stats['null_percentage']))
        
        if high_null_fields:
            print(f"   📊 API 응답에서 자주 누락되는 필드들:")
            for field, percentage in sorted(high_null_fields, key=lambda x: x[1], reverse=True)[:10]:
                print(f"     - {field}: {percentage:.1f}% NULL")
                root_causes['api_response_missing_fields'].append({
                    'field': field,
                    'null_percentage': percentage,
                    'likely_cause': self._analyze_field_null_cause(field)
                })
        
        # 2. 외래키 해결 실패 분석
        fk_issues = self.analysis_results.get('foreign_key_issues', {})
        if fk_issues.get('properties_new'):
            print(f"   🔗 외래키 해결 실패:")
            for fk_field, stats in fk_issues['properties_new'].items():
                if stats['null_percentage'] > 5:
                    print(f"     - {fk_field}: {stats['null_percentage']:.1f}% NULL")
                    root_causes['foreign_key_resolution_failures'].append({
                        'field': fk_field,
                        'null_percentage': stats['null_percentage'],
                        'recommended_fix': self._get_fk_fix_recommendation(fk_field)
                    })
        
        # 3. 데이터 검증 실패 분석
        normalized_tables = self.analysis_results.get('normalized_tables', {})
        for table_name, table_data in normalized_tables.items():
            if table_data.get('critical_null_columns'):
                for column in table_data['critical_null_columns']:
                    root_causes['validation_failures'].append({
                        'table': table_name,
                        'column': column,
                        'issue': 'High NULL percentage',
                        'recommended_fix': self._get_validation_fix(table_name, column)
                    })
        
        self.analysis_results['root_causes'] = root_causes
        return root_causes
    
    def generate_data_quality_recommendations(self):
        """데이터 품질 개선 방안 생성"""
        print("\n💡 데이터 품질 개선 방안 생성...")
        
        recommendations = {
            'immediate_fixes': [],
            'collector_improvements': [],
            'schema_adjustments': [],
            'monitoring_enhancements': []
        }
        
        # 1. 즉시 수정 가능한 문제들
        root_causes = self.analysis_results.get('root_causes', {})
        
        for fk_failure in root_causes.get('foreign_key_resolution_failures', []):
            if fk_failure['null_percentage'] > 20:
                recommendations['immediate_fixes'].append({
                    'priority': 'HIGH',
                    'issue': f"{fk_failure['field']} 외래키 {fk_failure['null_percentage']:.1f}% NULL",
                    'fix': fk_failure['recommended_fix'],
                    'code_example': self._generate_fix_code(fk_failure['field'])
                })
        
        # 2. 수집기 개선 사항
        collector_issues = self.analysis_results.get('collector_analysis', {}).get('potential_issues', [])
        for issue in collector_issues:
            recommendations['collector_improvements'].append({
                'issue': issue,
                'fix': self._get_collector_improvement(issue)
            })
        
        # 3. 스키마 조정 사항
        for table_name, table_data in self.analysis_results.get('normalized_tables', {}).items():
            if table_data.get('critical_null_columns'):
                for column in table_data['critical_null_columns']:
                    recommendations['schema_adjustments'].append({
                        'table': table_name,
                        'column': column,
                        'suggestion': f"{column} 컬럼에 기본값 또는 NOT NULL 제약조건 추가 검토"
                    })
        
        # 4. 모니터링 강화
        recommendations['monitoring_enhancements'] = [
            "실시간 NULL 값 비율 모니터링 대시보드 구축",
            "외래키 해결 실패율 알림 시스템",
            "API 응답 필드 누락 패턴 추적",
            "데이터 품질 점수 자동 계산 및 리포트"
        ]
        
        self.analysis_results['recommendations'] = recommendations
        return recommendations
    
    def _detect_data_type(self, sample_data, column):
        """컬럼의 데이터 타입 추정"""
        non_null_values = [record.get(column) for record in sample_data 
                          if record.get(column) is not None and record.get(column) != '']
        
        if not non_null_values:
            return 'unknown'
        
        sample_value = non_null_values[0]
        
        if isinstance(sample_value, bool):
            return 'boolean'
        elif isinstance(sample_value, int):
            return 'integer'
        elif isinstance(sample_value, float):
            return 'float'
        elif isinstance(sample_value, dict):
            return 'json'
        elif isinstance(sample_value, list):
            return 'array'
        else:
            return 'text'
    
    def _analyze_field_null_cause(self, field):
        """필드별 NULL 원인 분석"""
        cause_mapping = {
            'price': 'API에서 가격 정보 미제공 (비공개 매물)',
            'area1': 'API에서 면적 정보 누락',
            'area2': 'API에서 공급면적 정보 누락',
            'floor_info': 'API에서 층 정보 미제공',
            'description': '상세 설명 작성하지 않은 매물',
            'tag_list': '태그 정보 없는 매물',
            'details': 'API 응답 구조 변경 또는 파싱 실패'
        }
        
        for key, cause in cause_mapping.items():
            if key in field.lower():
                return cause
        
        return 'API 응답 필드 누락 또는 파싱 실패'
    
    def _get_fk_fix_recommendation(self, fk_field):
        """외래키 수정 권장사항"""
        fix_mapping = {
            'real_estate_type_id': 'buildingUse, lawUsage 필드를 우선적으로 사용하고, 없으면 "기타" 타입으로 기본값 설정',
            'trade_type_id': 'price, rent_price, warrant_price 존재 여부로 거래 유형 추론',
            'region_id': 'cortarNo가 없으면 좌표 기반으로 지역 추정 또는 "미분류" 지역 생성'
        }
        
        return fix_mapping.get(fk_field, '기본값 설정 로직 강화 필요')
    
    def _get_validation_fix(self, table_name, column):
        """검증 수정 권장사항"""
        return f"{table_name}.{column}에 대한 NULL 검증 로직 강화 필요"
    
    def _generate_fix_code(self, fk_field):
        """수정 코드 예시 생성"""
        code_examples = {
            'real_estate_type_id': '''
def _resolve_real_estate_type_id(self, data: Dict) -> Optional[int]:
    # 1. buildingUse 우선 확인
    type_name = data.get('basic_info', {}).get('building_use')
    
    # 2. raw_sections에서 추출
    if not type_name:
        raw_sections = data.get('raw_sections', {})
        if 'articleDetail' in raw_sections:
            detail = raw_sections['articleDetail']
            type_name = (detail.get('realEstateTypeName') or 
                        detail.get('buildingUse') or
                        detail.get('lawUsage'))
    
    # 3. 기본값 설정 (NULL 방지)
    if not type_name:
        type_name = "기타"
        
    return self._get_or_create_real_estate_type(type_name)
''',
            'trade_type_id': '''
def _resolve_trade_type_id(self, data: Dict) -> Optional[int]:
    price_info = data.get('price_info', {})
    
    # 가격 정보 기반 거래 유형 추론
    if price_info.get('deal_price'):
        trade_type = "매매"
    elif price_info.get('rent_price'):
        trade_type = "월세"  
    elif price_info.get('warrant_price'):
        trade_type = "전세"
    else:
        trade_type = "기타"  # NULL 방지
        
    return self._get_or_create_trade_type(trade_type)
''',
            'region_id': '''
def _resolve_region_id(self, data: Dict) -> Optional[int]:
    # 1. cortarNo 직접 사용
    cortar_no = data.get('raw_sections', {}).get('articleDetail', {}).get('cortarNo')
    
    # 2. 좌표 기반 지역 추정
    if not cortar_no:
        lat = data.get('basic_info', {}).get('latitude')
        lon = data.get('basic_info', {}).get('longitude')
        if lat and lon:
            cortar_no = self._estimate_cortar_from_coordinates(lat, lon)
    
    # 3. 기본 지역 설정 (NULL 방지)
    if not cortar_no:
        cortar_no = "9999999999"  # "미분류" 지역
        
    return self._get_or_create_region(cortar_no)
'''
        }
        
        return code_examples.get(fk_field, '# 수정 코드 예시 없음')
    
    def _get_collector_improvement(self, issue):
        """수집기 개선 방안"""
        improvement_mapping = {
            '최소 면적 기본값 패턴이 누락됨': 'safe_float 함수에 최소값 검증 로직 추가',
            '기본 지역 설정 패턴이 누락됨': '_resolve_region_id에 기본 지역 설정 로직 추가',
            'enhanced_data_collector.py 파일 없음': '수집기 파일 경로 확인 및 복구 필요'
        }
        
        return improvement_mapping.get(issue, '개선 방안 검토 필요')
    
    def generate_comprehensive_report(self):
        """종합 분석 리포트 생성"""
        print("\n📊 종합 NULL 값 분석 리포트 생성...")
        
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'summary': {},
            'detailed_analysis': self.analysis_results,
            'executive_summary': {},
            'action_plan': {}
        }
        
        # 요약 통계
        legacy_stats = self.analysis_results.get('legacy_properties', {})
        if legacy_stats:
            high_null_count = len(legacy_stats.get('high_null_columns', []))
            report['summary'] = {
                'total_legacy_records': legacy_stats.get('total_records', 0),
                'high_null_columns_count': high_null_count,
                'data_quality_score': max(0, 100 - (high_null_count * 5))  # 간단한 점수 계산
            }
        
        # 경영진 요약
        recommendations = self.analysis_results.get('recommendations', {})
        high_priority_fixes = len([fix for fix in recommendations.get('immediate_fixes', []) 
                                 if fix.get('priority') == 'HIGH'])
        
        report['executive_summary'] = {
            'critical_issues_found': high_priority_fixes,
            'estimated_data_loss': self._estimate_data_loss(),
            'recommended_actions': len(recommendations.get('immediate_fixes', [])),
            'implementation_priority': 'HIGH' if high_priority_fixes > 0 else 'MEDIUM'
        }
        
        # 실행 계획
        report['action_plan'] = {
            'phase_1_immediate': recommendations.get('immediate_fixes', []),
            'phase_2_collector_improvements': recommendations.get('collector_improvements', []),
            'phase_3_schema_optimization': recommendations.get('schema_adjustments', []),
            'phase_4_monitoring': recommendations.get('monitoring_enhancements', [])
        }
        
        # 리포트 저장
        report_file = current_dir / f"null_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"💾 종합 리포트 저장: {report_file}")
        
        # 요약 출력
        self._print_executive_summary(report)
        
        return report
    
    def _estimate_data_loss(self):
        """데이터 손실 추정"""
        legacy_stats = self.analysis_results.get('legacy_properties', {}).get('null_statistics', {})
        
        critical_fields = ['price', 'area1', 'area2', 'real_estate_type', 'trade_type']
        total_loss_percentage = 0
        
        for field in critical_fields:
            if field in legacy_stats:
                total_loss_percentage += legacy_stats[field]['null_percentage']
        
        average_loss = total_loss_percentage / len(critical_fields) if critical_fields else 0
        return min(average_loss, 100)
    
    def _print_executive_summary(self, report):
        """경영진 요약 출력"""
        print("\n" + "="*80)
        print("📊 NULL 값 분석 종합 리포트 - 경영진 요약")
        print("="*80)
        
        summary = report['summary']
        exec_summary = report['executive_summary']
        
        print(f"📈 전체 레코드: {summary.get('total_legacy_records', 0):,}개")
        print(f"⚠️ 높은 NULL 비율 컬럼: {summary.get('high_null_columns_count', 0)}개")
        print(f"🎯 데이터 품질 점수: {summary.get('data_quality_score', 0):.1f}/100점")
        print(f"🚨 중요 문제: {exec_summary.get('critical_issues_found', 0)}개")
        print(f"📉 추정 데이터 손실: {exec_summary.get('estimated_data_loss', 0):.1f}%")
        print(f"🔧 권장 조치: {exec_summary.get('recommended_actions', 0)}개")
        print(f"⏰ 우선순위: {exec_summary.get('implementation_priority', 'UNKNOWN')}")
        
        print(f"\n💡 주요 권장사항:")
        phase_1 = report['action_plan'].get('phase_1_immediate', [])
        for i, fix in enumerate(phase_1[:3], 1):
            print(f"   {i}. {fix.get('issue', 'Unknown issue')}")
        
        if len(phase_1) > 3:
            print(f"   ... 외 {len(phase_1)-3}개 추가 권장사항")
        
        print("="*80)

def main():
    """메인 실행 함수"""
    print("🚀 데이터베이스 NULL 값 종합 분석 시작")
    print("="*60)
    
    analyzer = NullValueAnalyzer()
    
    try:
        # 1. 기존 properties 테이블 분석
        analyzer.analyze_legacy_properties_table()
        
        # 2. 정규화된 테이블들 분석
        analyzer.analyze_normalized_tables()
        
        # 3. 외래키 관련 문제 분석
        analyzer.analyze_foreign_key_issues()
        
        # 4. enhanced_data_collector.py 분석
        analyzer.analyze_enhanced_collector_null_handling()
        
        # 5. NULL 값 원인 분석
        analyzer.identify_null_root_causes()
        
        # 6. 개선 방안 생성
        analyzer.generate_data_quality_recommendations()
        
        # 7. 종합 리포트 생성
        report = analyzer.generate_comprehensive_report()
        
        print("\n✅ 분석 완료! 리포트를 확인하여 개선 작업을 진행하세요.")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()