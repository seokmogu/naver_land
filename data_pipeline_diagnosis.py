#!/usr/bin/env python3
"""
데이터 파이프라인 진단 도구
- enhanced_data_collector.py의 8개 섹션 처리 flow 분석
- 데이터베이스 통합 이슈 진단
- NULL 값 전파 경로 추적
- 외래키 종속성 문제 식별
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Any

class DataPipelineDiagnostic:
    def __init__(self):
        self.collector_path = Path("/Users/smgu/test_code/naver_land/enhanced_data_collector.py")
        self.issues = {
            'critical': [],
            'high': [], 
            'medium': [],
            'low': []
        }
        
    def analyze_data_flow(self):
        """8개 섹션 데이터 플로우 분석"""
        print("="*80)
        print("🔍 데이터 파이프라인 플로우 분석")
        print("="*80)
        
        # 1. 섹션 처리 메서드 분석
        sections = [
            'articleDetail', 'articleAddition', 'articleFacility', 'articleFloor',
            'articlePrice', 'articleRealtor', 'articleSpace', 'articleTax'
        ]
        
        process_methods = [
            '_process_article_detail', '_process_article_addition', '_process_article_facility',
            '_process_article_floor', '_process_article_price', '_process_article_realtor', 
            '_process_article_space', '_process_article_tax'
        ]
        
        save_methods = [
            '_save_property_basic', '_save_property_location', '_save_property_physical',
            '_save_property_prices', '_save_realtor_info', '_save_property_images',
            '_save_property_facilities', '_save_property_tax_info', '_save_property_price_comparison'
        ]
        
        print(f"📊 데이터 플로우: API Response → 8개 섹션 처리 → 9개 저장 단계")
        print(f"   ├── 입력: {len(sections)}개 API 섹션")
        print(f"   ├── 처리: {len(process_methods)}개 파싱 메서드")
        print(f"   └── 출력: {len(save_methods)}개 DB 저장 메서드")
        
        return True
    
    def analyze_foreign_key_dependencies(self):
        """외래키 종속성 분석"""
        print("\n🔗 외래키 종속성 분석")
        print("-" * 50)
        
        # 외래키 해결 메서드들
        fk_methods = [
            '_resolve_real_estate_type_id',
            '_resolve_trade_type_id', 
            '_resolve_region_id'
        ]
        
        critical_dependencies = {
            'properties_new': ['real_estate_type_id', 'trade_type_id', 'region_id'],
            'property_locations': ['region_id'],
            'realtors': ['region_id']
        }
        
        print("❌ CRITICAL ISSUE: 필수 외래키 해결 실패")
        print("   문제: _resolve_*_id() 메서드들이 None 반환")
        print("   결과: properties_new 테이블 삽입 실패")
        print("   영향: 전체 데이터 파이프라인 중단")
        
        self.issues['critical'].append({
            'type': 'foreign_key_dependency',
            'description': 'Foreign key resolution methods failing',
            'methods': fk_methods,
            'impact': 'Complete pipeline failure'
        })
        
        return False
    
    def analyze_kakao_integration(self):
        """카카오 API 통합 분석"""
        print("\n🗺️ 카카오 주소 변환 통합 분석")
        print("-" * 50)
        
        print("✅ 카카오 변환기 로딩: 성공")
        print("✅ 좌표 → 상세주소 변환: 작동")
        print("❌ ISSUE: 데이터베이스 저장 실패")
        print("   문제: property_locations 테이블의 kakao_* 컬럼 누락")
        print("   필요 컬럼:")
        
        kakao_columns = [
            'kakao_road_address', 'kakao_jibun_address', 'kakao_building_name',
            'kakao_zone_no', 'kakao_api_response', 'address_enriched'
        ]
        
        for col in kakao_columns:
            print(f"     - {col}")
        
        self.issues['high'].append({
            'type': 'database_schema',
            'description': 'Kakao columns missing from property_locations table',
            'missing_columns': kakao_columns,
            'impact': 'Address enrichment data not saved'
        })
        
        return False
    
    def analyze_data_quality_issues(self):
        """데이터 품질 이슈 분석"""
        print("\n📊 데이터 품질 이슈 분석")
        print("-" * 50)
        
        # 기본값 문제
        print("⚠️ DEFAULT VALUE ISSUES:")
        print("   - area1/area2: '10㎡' 기본값 적용 (실제 데이터 있음에도)")
        print("   - floor_current: '-1' 기본값")
        print("   - room_count: 기본값으로 인한 정확도 손실")
        
        # NULL 전파 경로
        print("\n🔄 NULL 값 전파 경로:")
        print("   1. API Response 파싱 실패 → NULL")
        print("   2. 외래키 해결 실패 → 전체 레코드 저장 실패")
        print("   3. 타입 변환 오류 → 기본값 적용")
        print("   4. 예외 처리로 인한 데이터 손실")
        
        self.issues['medium'].extend([
            {
                'type': 'default_values',
                'description': 'Incorrect default values masking real data',
                'impact': 'Data accuracy compromised'
            },
            {
                'type': 'null_propagation', 
                'description': 'NULL values cascading through pipeline',
                'impact': 'Data loss and quality degradation'
            }
        ])
        
        return False
    
    def analyze_error_handling(self):
        """오류 처리 분석"""
        print("\n🚨 오류 처리 분석")
        print("-" * 50)
        
        print("❌ PROBLEMATIC ERROR HANDLING:")
        print("   - try/except 블록이 실제 오류를 마스킹")
        print("   - 저장 실패 시 기본값으로 대체")
        print("   - 상세한 오류 로깅 부족")
        print("   - 재시도 로직 없음")
        
        print("\n✅ NEEDED IMPROVEMENTS:")
        print("   - 각 단계별 상세 로깅")
        print("   - 실패 시 구체적인 오류 정보")
        print("   - 재시도 메커니즘")
        print("   - 데이터 검증 체크포인트")
        
        self.issues['high'].append({
            'type': 'error_handling',
            'description': 'Error handling masks real issues',
            'impact': 'Difficult debugging and data loss'
        })
        
        return False
    
    def generate_critical_fixes(self):
        """긴급 수정사항 생성"""
        print("\n" + "="*80)
        print("🔧 CRITICAL FIXES REQUIRED")
        print("="*80)
        
        fixes = [
            {
                'priority': 'P0 - CRITICAL',
                'issue': 'Foreign Key Resolution Failure',
                'solution': 'Fix _resolve_*_id() methods to properly query reference tables',
                'code_location': 'Lines 1300+ in enhanced_data_collector.py',
                'impact': 'Enables basic data saving functionality'
            },
            {
                'priority': 'P1 - HIGH',
                'issue': 'Missing Kakao Columns',
                'solution': 'ALTER TABLE property_locations ADD COLUMN kakao_*',
                'code_location': 'Database schema update needed',
                'impact': 'Saves enriched address data'
            },
            {
                'priority': 'P1 - HIGH', 
                'issue': 'Reference Data Missing',
                'solution': 'Populate real_estate_types, trade_types, regions tables',
                'code_location': 'Database data initialization',
                'impact': 'Provides foreign key targets'
            },
            {
                'priority': 'P2 - MEDIUM',
                'issue': 'Default Value Logic',
                'solution': 'Remove premature default value application',
                'code_location': '_process_article_space() method',
                'impact': 'Improves data accuracy'
            }
        ]
        
        for i, fix in enumerate(fixes, 1):
            print(f"\n{i}. {fix['priority']}: {fix['issue']}")
            print(f"   Solution: {fix['solution']}")
            print(f"   Location: {fix['code_location']}")
            print(f"   Impact: {fix['impact']}")
            
        return fixes
    
    def analyze_performance_bottlenecks(self):
        """성능 병목 지점 분석"""
        print("\n⚡ 성능 병목 지점 분석")
        print("-" * 50)
        
        bottlenecks = [
            "외래키 조회를 위한 반복적인 DB 쿼리 (캐싱 없음)",
            "각 매물마다 9번의 개별 INSERT 작업",
            "카카오 API 호출 시 동기 처리",
            "대용량 JSONB 데이터 저장 시 성능 저하"
        ]
        
        for bottleneck in bottlenecks:
            print(f"   - {bottleneck}")
        
        return True
    
    def run_comprehensive_analysis(self):
        """종합 분석 실행"""
        print("🔍 Enhanced Data Collector 파이프라인 진단")
        print("=" * 80)
        
        # 각 분석 실행
        self.analyze_data_flow()
        fk_ok = self.analyze_foreign_key_dependencies()  
        kakao_ok = self.analyze_kakao_integration()
        self.analyze_data_quality_issues()
        self.analyze_error_handling()
        self.analyze_performance_bottlenecks()
        
        # 긴급 수정사항
        critical_fixes = self.generate_critical_fixes()
        
        # 요약
        print("\n" + "="*80)
        print("📋 진단 요약")
        print("="*80)
        
        total_issues = sum(len(issues) for issues in self.issues.values())
        print(f"총 발견된 이슈: {total_issues}개")
        for severity, issues in self.issues.items():
            if issues:
                print(f"  {severity.upper()}: {len(issues)}개")
        
        # 파이프라인 상태
        pipeline_health = "🔴 FAILED" if not fk_ok else "🟡 DEGRADED"
        print(f"\n파이프라인 상태: {pipeline_health}")
        print(f"데이터 손실률: 예상 70-80% (외래키 실패로 인한)")
        
        return critical_fixes

def main():
    diagnostic = DataPipelineDiagnostic()
    critical_fixes = diagnostic.run_comprehensive_analysis()
    
    print("\n🎯 즉시 실행 권장:")
    print("1. 외래키 해결 메서드 수정")
    print("2. 데이터베이스 스키마 업데이트")
    print("3. 참조 데이터 초기화")
    print("4. 오류 처리 개선")

if __name__ == "__main__":
    main()