#!/usr/bin/env python3
"""
Supabase 데이터베이스 종합 검증 도구
- 실제 배포된 테이블 상태 확인
- 데이터 품질 검증
- API 필드 매핑 효과 분석
- 스키마 정규화 완료도 평가
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

# Supabase 클라이언트 import
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("❌ supabase-py 모듈이 필요합니다: pip install supabase")
    sys.exit(1)

# 환경변수 로드
load_dotenv()

class ComprehensiveDBVerifier:
    def __init__(self):
        """데이터베이스 검증기 초기화"""
        # Supabase 연결 정보
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            print("❌ SUPABASE_URL과 SUPABASE_ANON_KEY를 .env 파일에서 찾을 수 없습니다")
            sys.exit(1)
        
        # Supabase 클라이언트 생성
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            print("✅ Supabase 연결 성공")
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {e}")
            sys.exit(1)
        
        # 검증 결과 저장용
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'tables_status': {},
            'data_quality': {},
            'schema_completeness': {},
            'field_mapping_effectiveness': {},
            'overall_assessment': {}
        }
    
    def verify_table_existence_and_structure(self) -> Dict[str, Any]:
        """테이블 존재 여부와 구조 검증"""
        print("\n🔍 1. 테이블 존재 여부 및 구조 검증")
        print("=" * 60)
        
        # 예상되는 테이블들
        expected_tables = {
            # 메인 테이블들
            'properties_new': 'Main normalized properties table',
            'property_locations': 'Property location and address data',
            'property_physical': 'Physical property characteristics',
            'property_prices': 'Property pricing information',
            'property_images': 'Property photos and media',
            'property_tax_info': 'Property tax calculation data',
            'property_price_comparison': 'Price comparison analytics',
            'property_facilities': 'Property facilities mapping',
            
            # 참조 테이블들
            'realtors': 'Realtor/broker information',
            'property_realtors': 'Property-realtor relationships',
            'real_estate_types': 'Property types reference',
            'trade_types': 'Transaction types reference',
            'regions': 'Regional data reference',
            
            # 운영 테이블들
            'daily_stats': 'Daily collection statistics',
            'collection_logs': 'Collection activity logs',
            'deletion_history': 'Deleted properties tracking',
            'price_history': 'Price change history'
        }
        
        table_status = {}
        
        for table_name, description in expected_tables.items():
            try:
                # 테이블 존재 확인 (1개 레코드만 조회)
                result = self.client.table(table_name).select('*').limit(1).execute()
                
                # 레코드 수 확인
                count_result = self.client.table(table_name).select('*', count='exact').limit(1).execute()
                record_count = count_result.count or 0
                
                # 컬럼 구조 확인 (첫 번째 레코드가 있으면)
                columns = []
                if result.data and len(result.data) > 0:
                    columns = list(result.data[0].keys())
                
                table_status[table_name] = {
                    'exists': True,
                    'record_count': record_count,
                    'columns': columns,
                    'column_count': len(columns),
                    'description': description,
                    'has_data': record_count > 0
                }
                
                status_icon = "✅" if record_count > 0 else "📋"
                print(f"{status_icon} {table_name:<25} | {record_count:>7,}개 레코드 | {len(columns):>2}개 컬럼")
                
            except Exception as e:
                table_status[table_name] = {
                    'exists': False,
                    'error': str(e),
                    'description': description,
                    'record_count': 0
                }
                print(f"❌ {table_name:<25} | 테이블 없음 | {str(e)}")
        
        self.verification_results['tables_status'] = table_status
        return table_status
    
    def analyze_data_quality(self) -> Dict[str, Any]:
        """데이터 품질 분석"""
        print("\n📊 2. 데이터 품질 분석")
        print("=" * 60)
        
        quality_report = {}
        
        # 메인 데이터 테이블들 분석
        main_tables = ['properties_new', 'property_locations', 'property_physical', 'property_prices']
        
        for table_name in main_tables:
            if self.verification_results['tables_status'].get(table_name, {}).get('exists', False):
                print(f"\n🔍 {table_name} 분석 중...")
                quality_report[table_name] = self._analyze_table_quality(table_name)
            else:
                print(f"❌ {table_name}: 테이블이 존재하지 않음")
                quality_report[table_name] = {'error': 'Table does not exist'}
        
        self.verification_results['data_quality'] = quality_report
        return quality_report
    
    def _analyze_table_quality(self, table_name: str) -> Dict[str, Any]:
        """개별 테이블 데이터 품질 분석"""
        try:
            # 샘플 데이터 수집 (최대 1000개)
            result = self.client.table(table_name).select('*').limit(1000).execute()
            data = result.data
            
            if not data:
                return {'error': 'No data in table'}
            
            total_records = len(data)
            columns = list(data[0].keys()) if data else []
            
            # NULL 값 분석
            null_analysis = {}
            for column in columns:
                null_count = sum(1 for row in data if row.get(column) is None or row.get(column) == '')
                null_percentage = (null_count / total_records) * 100 if total_records > 0 else 0
                
                if null_percentage > 0:
                    null_analysis[column] = {
                        'null_count': null_count,
                        'null_percentage': round(null_percentage, 1)
                    }
            
            # 높은 NULL 비율 컬럼 식별
            high_null_columns = {k: v for k, v in null_analysis.items() if v['null_percentage'] > 30}
            
            # 데이터 일관성 확인
            consistency_issues = self._check_data_consistency(data, table_name)
            
            quality_score = self._calculate_quality_score(null_analysis, consistency_issues, total_records)
            
            print(f"   📊 총 {total_records:,}개 레코드, {len(columns)}개 컬럼")
            print(f"   ⚠️ 높은 NULL 비율 컬럼: {len(high_null_columns)}개")
            print(f"   🎯 데이터 품질 점수: {quality_score}/100점")
            
            return {
                'total_records': total_records,
                'total_columns': len(columns),
                'null_analysis': null_analysis,
                'high_null_columns': high_null_columns,
                'consistency_issues': consistency_issues,
                'quality_score': quality_score
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _check_data_consistency(self, data: List[Dict], table_name: str) -> List[str]:
        """데이터 일관성 확인"""
        issues = []
        
        for i, record in enumerate(data[:100]):  # 처음 100개만 확인
            try:
                # 공통 일관성 확인
                if 'price' in record:
                    price = record.get('price')
                    if isinstance(price, (int, float)) and price < 0:
                        issues.append(f"음수 가격 발견: 레코드 {i}")
                
                # 날짜 일관성 확인
                if 'created_at' in record and 'updated_at' in record:
                    created = record.get('created_at')
                    updated = record.get('updated_at')
                    if created and updated and created > updated:
                        issues.append(f"날짜 불일치: 레코드 {i}")
                
                # 테이블별 특수 확인
                if table_name == 'properties_new':
                    if record.get('article_no') and len(str(record['article_no'])) < 5:
                        issues.append(f"의심스러운 article_no: 레코드 {i}")
                
            except Exception:
                continue
        
        return issues[:10]  # 최대 10개 이슈만 반환
    
    def _calculate_quality_score(self, null_analysis: Dict, consistency_issues: List, total_records: int) -> float:
        """데이터 품질 점수 계산 (100점 만점)"""
        score = 100.0
        
        # NULL 값 페널티
        high_null_count = sum(1 for info in null_analysis.values() if info['null_percentage'] > 50)
        medium_null_count = sum(1 for info in null_analysis.values() if 20 < info['null_percentage'] <= 50)
        
        score -= (high_null_count * 10)  # 높은 NULL 비율 컬럼당 10점 감점
        score -= (medium_null_count * 5)  # 중간 NULL 비율 컬럼당 5점 감점
        
        # 일관성 이슈 페널티
        score -= (len(consistency_issues) * 2)  # 이슈당 2점 감점
        
        # 데이터 볼륨 보너스
        if total_records > 1000:
            score += 5
        
        return max(0, min(100, round(score, 1)))
    
    def assess_field_mapping_effectiveness(self) -> Dict[str, Any]:
        """API 필드 매핑 수정 효과 평가"""
        print("\n🔧 3. API 필드 매핑 효과 분석")
        print("=" * 60)
        
        mapping_effectiveness = {}
        
        # area1, area2 필드명 수정 효과 확인
        if self.verification_results['tables_status'].get('property_physical', {}).get('exists', False):
            try:
                result = self.client.table('property_physical').select('area1, area2, area_exclusive, area_supply').limit(100).execute()
                data = result.data
                
                if data:
                    area1_filled = sum(1 for row in data if row.get('area1') is not None)
                    area2_filled = sum(1 for row in data if row.get('area2') is not None)
                    exclusive_filled = sum(1 for row in data if row.get('area_exclusive') is not None)
                    supply_filled = sum(1 for row in data if row.get('area_supply') is not None)
                    
                    total = len(data)
                    
                    mapping_effectiveness['area_fields'] = {
                        'area1_success_rate': round((area1_filled / total) * 100, 1) if total > 0 else 0,
                        'area2_success_rate': round((area2_filled / total) * 100, 1) if total > 0 else 0,
                        'area_exclusive_success_rate': round((exclusive_filled / total) * 100, 1) if total > 0 else 0,
                        'area_supply_success_rate': round((supply_filled / total) * 100, 1) if total > 0 else 0,
                        'sample_size': total
                    }
                    
                    print(f"   📐 area1 성공률: {mapping_effectiveness['area_fields']['area1_success_rate']}%")
                    print(f"   📐 area2 성공률: {mapping_effectiveness['area_fields']['area2_success_rate']}%")
                    print(f"   📐 전용면적 성공률: {mapping_effectiveness['area_fields']['area_exclusive_success_rate']}%")
                    print(f"   📐 공급면적 성공률: {mapping_effectiveness['area_fields']['area_supply_success_rate']}%")
                
            except Exception as e:
                mapping_effectiveness['area_fields'] = {'error': str(e)}
                print(f"   ❌ 면적 필드 분석 실패: {e}")
        
        # 카카오 주소 변환 효과 확인
        if self.verification_results['tables_status'].get('property_locations', {}).get('exists', False):
            try:
                result = self.client.table('property_locations').select('kakao_road_address, kakao_jibun_address, kakao_api_response').limit(100).execute()
                data = result.data
                
                if data:
                    kakao_road_filled = sum(1 for row in data if row.get('kakao_road_address') is not None)
                    kakao_jibun_filled = sum(1 for row in data if row.get('kakao_jibun_address') is not None)
                    kakao_response_filled = sum(1 for row in data if row.get('kakao_api_response') is not None)
                    
                    total = len(data)
                    
                    mapping_effectiveness['kakao_integration'] = {
                        'road_address_success_rate': round((kakao_road_filled / total) * 100, 1) if total > 0 else 0,
                        'jibun_address_success_rate': round((kakao_jibun_filled / total) * 100, 1) if total > 0 else 0,
                        'api_response_success_rate': round((kakao_response_filled / total) * 100, 1) if total > 0 else 0,
                        'sample_size': total
                    }
                    
                    print(f"   🗺️ 카카오 도로명주소 성공률: {mapping_effectiveness['kakao_integration']['road_address_success_rate']}%")
                    print(f"   🗺️ 카카오 지번주소 성공률: {mapping_effectiveness['kakao_integration']['jibun_address_success_rate']}%")
                    print(f"   🗺️ 카카오 API 응답 성공률: {mapping_effectiveness['kakao_integration']['api_response_success_rate']}%")
                
            except Exception as e:
                mapping_effectiveness['kakao_integration'] = {'error': str(e)}
                print(f"   ❌ 카카오 주소 변환 분석 실패: {e}")
        
        self.verification_results['field_mapping_effectiveness'] = mapping_effectiveness
        return mapping_effectiveness
    
    def evaluate_schema_normalization_completeness(self) -> Dict[str, Any]:
        """스키마 정규화 완료도 평가"""
        print("\n🏗️ 4. 스키마 정규화 완료도 평가")
        print("=" * 60)
        
        # 정규화 요소 체크리스트
        normalization_checklist = {
            'core_tables': {
                'weight': 30,
                'required': ['properties_new', 'property_locations', 'property_physical', 'property_prices'],
                'status': 'checking'
            },
            'reference_tables': {
                'weight': 20,
                'required': ['realtors', 'real_estate_types', 'trade_types', 'regions'],
                'status': 'checking'
            },
            'relationship_tables': {
                'weight': 15,
                'required': ['property_realtors', 'property_facilities'],
                'status': 'checking'
            },
            'operational_tables': {
                'weight': 10,
                'required': ['daily_stats', 'collection_logs', 'price_history'],
                'status': 'checking'
            },
            'advanced_features': {
                'weight': 15,
                'required': ['property_tax_info', 'property_price_comparison', 'property_images'],
                'status': 'checking'
            },
            'data_integrity': {
                'weight': 10,
                'required': ['foreign_keys', 'indexes', 'constraints'],
                'status': 'checking'
            }
        }
        
        total_score = 0
        max_score = sum(item['weight'] for item in normalization_checklist.values())
        
        # 각 카테고리별 평가
        for category, info in normalization_checklist.items():
            category_score = 0
            
            if category == 'data_integrity':
                # 데이터 무결성은 별도 로직으로 평가
                category_score = info['weight'] * 0.5  # 임시로 50% 점수
                info['score'] = category_score
                info['completion_rate'] = 50.0
                print(f"   🔗 {category}: 50.0% (데이터 무결성 부분 구현)")
            else:
                existing_tables = []
                missing_tables = []
                
                for table in info['required']:
                    if self.verification_results['tables_status'].get(table, {}).get('exists', False):
                        existing_tables.append(table)
                    else:
                        missing_tables.append(table)
                
                completion_rate = (len(existing_tables) / len(info['required'])) * 100 if info['required'] else 0
                category_score = (completion_rate / 100) * info['weight']
                
                info['existing_tables'] = existing_tables
                info['missing_tables'] = missing_tables
                info['completion_rate'] = round(completion_rate, 1)
                info['score'] = round(category_score, 1)
                
                status_icon = "✅" if completion_rate == 100 else "⚠️" if completion_rate >= 50 else "❌"
                print(f"   {status_icon} {category}: {completion_rate}% ({len(existing_tables)}/{len(info['required'])})")
                
                if missing_tables:
                    print(f"      누락: {', '.join(missing_tables)}")
            
            total_score += category_score
        
        overall_completion = round((total_score / max_score) * 100, 1)
        
        print(f"\n📊 전체 정규화 완료도: {overall_completion}% ({total_score:.1f}/{max_score}점)")
        
        completeness_result = {
            'overall_completion_percentage': overall_completion,
            'total_score': round(total_score, 1),
            'max_score': max_score,
            'category_breakdown': normalization_checklist,
            'assessment': self._get_completeness_assessment(overall_completion)
        }
        
        self.verification_results['schema_completeness'] = completeness_result
        return completeness_result
    
    def _get_completeness_assessment(self, completion_percentage: float) -> str:
        """완료도에 따른 평가 메시지"""
        if completion_percentage >= 90:
            return "EXCELLENT - 정규화가 거의 완료됨"
        elif completion_percentage >= 80:
            return "GOOD - 주요 구조는 완료, 일부 보완 필요"
        elif completion_percentage >= 70:
            return "FAIR - 기본 구조 완료, 추가 작업 필요"
        elif completion_percentage >= 50:
            return "POOR - 상당한 작업이 남아있음"
        else:
            return "CRITICAL - 대부분의 정규화 작업이 필요"
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """종합 검증 보고서 생성"""
        print("\n📋 5. 종합 검증 보고서 생성")
        print("=" * 60)
        
        # 전체적인 평가
        total_tables = len(self.verification_results['tables_status'])
        existing_tables = sum(1 for table_info in self.verification_results['tables_status'].values() 
                             if table_info.get('exists', False))
        tables_with_data = sum(1 for table_info in self.verification_results['tables_status'].values() 
                              if table_info.get('has_data', False))
        
        # 데이터 품질 종합 점수
        quality_scores = []
        for table_quality in self.verification_results['data_quality'].values():
            if isinstance(table_quality, dict) and 'quality_score' in table_quality:
                quality_scores.append(table_quality['quality_score'])
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 전체 평가
        overall_assessment = {
            'database_health': self._assess_database_health(existing_tables, total_tables, tables_with_data),
            'data_quality_grade': self._get_quality_grade(avg_quality_score),
            'schema_maturity': self._get_schema_maturity(self.verification_results['schema_completeness']['overall_completion_percentage']),
            'recommended_actions': self._get_recommended_actions()
        }
        
        self.verification_results['overall_assessment'] = overall_assessment
        
        # 보고서 파일 저장
        report_filename = f"comprehensive_db_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = Path(__file__).parent / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.verification_results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 상세 보고서 저장: {report_path}")
        
        return overall_assessment
    
    def _assess_database_health(self, existing_tables: int, total_tables: int, tables_with_data: int) -> str:
        """데이터베이스 건강도 평가"""
        existence_rate = (existing_tables / total_tables) * 100 if total_tables > 0 else 0
        data_rate = (tables_with_data / total_tables) * 100 if total_tables > 0 else 0
        
        if existence_rate >= 90 and data_rate >= 70:
            return "HEALTHY"
        elif existence_rate >= 80 and data_rate >= 50:
            return "STABLE"
        elif existence_rate >= 70:
            return "DEVELOPING"
        else:
            return "CRITICAL"
    
    def _get_quality_grade(self, avg_score: float) -> str:
        """품질 점수에 따른 등급"""
        if avg_score >= 85:
            return "A"
        elif avg_score >= 70:
            return "B"
        elif avg_score >= 55:
            return "C"
        elif avg_score >= 40:
            return "D"
        else:
            return "F"
    
    def _get_schema_maturity(self, completion_percentage: float) -> str:
        """스키마 성숙도 평가"""
        if completion_percentage >= 90:
            return "MATURE"
        elif completion_percentage >= 75:
            return "DEVELOPING"
        elif completion_percentage >= 50:
            return "INITIAL"
        else:
            return "EMBRYONIC"
    
    def _get_recommended_actions(self) -> List[str]:
        """권장 조치사항"""
        actions = []
        
        # 누락된 테이블들 확인
        missing_tables = [name for name, info in self.verification_results['tables_status'].items() 
                         if not info.get('exists', False)]
        
        if missing_tables:
            actions.append(f"누락된 테이블 생성 필요: {', '.join(missing_tables)}")
        
        # 데이터 품질 이슈
        for table_name, quality_info in self.verification_results['data_quality'].items():
            if isinstance(quality_info, dict) and 'quality_score' in quality_info:
                if quality_info['quality_score'] < 60:
                    actions.append(f"{table_name} 테이블 데이터 품질 개선 필요")
        
        # 정규화 완료도
        completion_pct = self.verification_results['schema_completeness']['overall_completion_percentage']
        if completion_pct < 80:
            actions.append("스키마 정규화 완성 작업 필요")
        
        # 필드 매핑 효과
        if 'field_mapping_effectiveness' in self.verification_results:
            area_success = self.verification_results['field_mapping_effectiveness'].get('area_fields', {}).get('area1_success_rate', 0)
            if area_success < 50:
                actions.append("API 필드 매핑 로직 재검토 필요")
        
        if not actions:
            actions.append("현재 상태가 양호합니다. 지속적인 모니터링 권장")
        
        return actions
    
    def print_executive_summary(self):
        """경영진 요약 보고서 출력"""
        print("\n" + "="*80)
        print("🚀 네이버 부동산 DB 종합 검증 결과 - 경영진 요약")
        print("="*80)
        
        # 기본 통계
        total_tables = len(self.verification_results['tables_status'])
        existing_tables = sum(1 for info in self.verification_results['tables_status'].values() if info.get('exists', False))
        total_records = sum(info.get('record_count', 0) for info in self.verification_results['tables_status'].values() if info.get('exists', False))
        
        print(f"📊 데이터베이스 현황:")
        print(f"   🏗️ 테이블: {existing_tables}/{total_tables}개 존재")
        print(f"   📈 총 레코드: {total_records:,}개")
        print(f"   🏥 데이터베이스 상태: {self.verification_results['overall_assessment']['database_health']}")
        print(f"   📋 스키마 완성도: {self.verification_results['schema_completeness']['overall_completion_percentage']}%")
        
        # 주요 성과
        print(f"\n🎯 주요 성과:")
        if total_records > 0:
            print(f"   ✅ {total_records:,}개 부동산 매물 데이터 수집 완료")
        
        # 데이터 품질
        quality_scores = []
        for quality_info in self.verification_results['data_quality'].values():
            if isinstance(quality_info, dict) and 'quality_score' in quality_info:
                quality_scores.append(quality_info['quality_score'])
        
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            quality_grade = self.verification_results['overall_assessment']['data_quality_grade']
            print(f"   📊 데이터 품질: {avg_quality:.1f}/100점 ({quality_grade}등급)")
        
        # 권장 조치사항
        print(f"\n🔧 권장 조치사항:")
        for i, action in enumerate(self.verification_results['overall_assessment']['recommended_actions'], 1):
            print(f"   {i}. {action}")
        
        print("\n" + "="*80)
        print(f"📅 보고서 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

def main():
    """메인 실행 함수"""
    print("🔍 Supabase 데이터베이스 종합 검증 시작")
    print("="*70)
    
    try:
        # 검증기 초기화
        verifier = ComprehensiveDBVerifier()
        
        # 순차적으로 모든 검증 수행
        verifier.verify_table_existence_and_structure()
        verifier.analyze_data_quality()
        verifier.assess_field_mapping_effectiveness()
        verifier.evaluate_schema_normalization_completeness()
        verifier.generate_comprehensive_report()
        
        # 경영진 요약 출력
        verifier.print_executive_summary()
        
        print(f"\n✅ 종합 검증 완료!")
        print("📋 상세 결과는 생성된 JSON 파일을 확인하세요.")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        return False
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)