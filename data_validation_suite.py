#!/usr/bin/env python3
"""
데이터 품질 검증 및 모니터링 시스템
- 수집된 데이터의 완성도 검증
- 파싱 실패율 모니터링
- 데이터 일관성 체크
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

class DataValidationSuite:
    def __init__(self):
        """데이터 검증 시스템 초기화"""
        # Supabase 연결
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        # 검증 결과 저장
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'total_properties': 0,
            'section_completeness': {},
            'data_quality_issues': [],
            'parsing_failure_rates': {},
            'recommendations': []
        }
    
    def validate_data_completeness(self) -> Dict:
        """데이터 완성도 검증 - 8개 섹션별 데이터 존재율"""
        print("📊 데이터 완성도 검증 시작...")
        
        try:
            # 전체 매물 수 조회
            total_props = self.client.table('properties_new').select('id', count='exact').execute()
            total_count = total_props.count if hasattr(total_props, 'count') else len(total_props.data)
            self.validation_results['total_properties'] = total_count
            
            print(f"📈 총 매물 수: {total_count:,}개")
            
            # 섹션별 데이터 존재율 체크
            sections_to_check = {
                'basic_info': ('properties_new', ['article_name', 'description']),
                'location_info': ('property_locations', ['latitude', 'longitude', 'address_road']),
                'physical_info': ('property_physical', ['area_exclusive', 'area_supply']),
                'price_info': ('property_prices', ['amount']),
                'realtor_info': ('property_realtors', ['realtor_id']),
                'image_info': ('property_images', ['image_url']),
                'facility_info': ('property_facilities', ['facility_id']),
                'tax_info': ('property_taxes', ['total_tax', 'brokerage_fee']),
                'subway_info': ('property_subway_access', ['station_name'])
            }
            
            for section, (table, key_fields) in sections_to_check.items():
                try:
                    # 각 섹션별 데이터 존재율 계산
                    section_data = self.client.table(table).select('property_id', count='exact').execute()
                    section_count = section_data.count if hasattr(section_data, 'count') else len(section_data.data)
                    
                    completeness_rate = (section_count / total_count * 100) if total_count > 0 else 0
                    
                    self.validation_results['section_completeness'][section] = {
                        'table': table,
                        'properties_with_data': section_count,
                        'completeness_rate': round(completeness_rate, 2),
                        'missing_count': total_count - section_count
                    }
                    
                    print(f"  📋 {section}: {completeness_rate:.1f}% ({section_count:,}/{total_count:,})")
                    
                    # 완성도가 낮은 섹션 식별
                    if completeness_rate < 70:
                        self.validation_results['data_quality_issues'].append({
                            'type': 'low_completeness',
                            'section': section,
                            'rate': completeness_rate,
                            'severity': 'high' if completeness_rate < 50 else 'medium'
                        })
                
                except Exception as e:
                    print(f"⚠️ {section} 검증 실패: {e}")
                    self.validation_results['section_completeness'][section] = {
                        'error': str(e),
                        'completeness_rate': 0
                    }
            
            return self.validation_results
            
        except Exception as e:
            print(f"❌ 데이터 완성도 검증 실패: {e}")
            return {}
    
    def validate_data_quality(self) -> Dict:
        """데이터 품질 검증 - 데이터 일관성 및 유효성 체크"""
        print("\n🔍 데이터 품질 검증 시작...")
        
        quality_checks = []
        
        try:
            # 1. 가격 데이터 유효성 체크
            invalid_prices = self.client.table('property_prices').select('property_id', 'amount')\
                .lt('amount', 0).execute()
            
            if invalid_prices.data:
                quality_checks.append({
                    'type': 'invalid_price',
                    'count': len(invalid_prices.data),
                    'severity': 'high',
                    'description': '음수 가격 데이터 발견'
                })
            
            # 2. 면적 데이터 일관성 체크
            invalid_areas = self.client.table('property_physical').select('property_id', 'area_exclusive', 'area_supply')\
                .lt('area_exclusive', 1).execute()
            
            if invalid_areas.data:
                quality_checks.append({
                    'type': 'invalid_area',
                    'count': len(invalid_areas.data),
                    'severity': 'medium',
                    'description': '비현실적인 면적 데이터 발견 (1㎡ 미만)'
                })
            
            # 3. 좌표 유효성 체크
            invalid_coords = self.client.table('property_locations').select('property_id', 'latitude', 'longitude')\
                .or_('latitude.is.null,longitude.is.null').execute()
            
            if invalid_coords.data:
                quality_checks.append({
                    'type': 'missing_coordinates',
                    'count': len(invalid_coords.data),
                    'severity': 'medium',
                    'description': '좌표 정보 누락'
                })
            
            # 4. 중복 매물 체크
            duplicate_articles = self.client.table('properties_new')\
                .select('article_no', count='exact')\
                .execute()
            
            # 중복 체크 로직 (단순화)
            if duplicate_articles.data:
                article_counts = {}
                for prop in duplicate_articles.data:
                    article_no = prop.get('article_no')
                    if article_no:
                        article_counts[article_no] = article_counts.get(article_no, 0) + 1
                
                duplicates = {k: v for k, v in article_counts.items() if v > 1}
                if duplicates:
                    quality_checks.append({
                        'type': 'duplicate_articles',
                        'count': len(duplicates),
                        'severity': 'low',
                        'description': '중복 매물 번호 발견'
                    })
            
            self.validation_results['data_quality_issues'].extend(quality_checks)
            
            for check in quality_checks:
                print(f"  ⚠️ {check['description']}: {check['count']}건 ({check['severity']} 심각도)")
            
            if not quality_checks:
                print("  ✅ 데이터 품질 이슈 없음")
            
        except Exception as e:
            print(f"❌ 데이터 품질 검증 실패: {e}")
        
        return quality_checks
    
    def analyze_parsing_failures(self, log_file_pattern: str = "parsing_failures_*.log") -> Dict:
        """파싱 실패 분석"""
        print("\n📄 파싱 실패 로그 분석 시작...")
        
        try:
            import glob
            
            log_files = glob.glob(log_file_pattern)
            if not log_files:
                print("  ℹ️ 파싱 실패 로그 파일을 찾을 수 없습니다.")
                return {}
            
            parsing_stats = {}
            total_failures = 0
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        if '|' in line:  # 로그 라인 형식 체크
                            parts = line.strip().split('|')
                            if len(parts) >= 3:
                                section = parts[1].strip()
                                parsing_stats[section] = parsing_stats.get(section, 0) + 1
                                total_failures += 1
                
                except Exception as e:
                    print(f"⚠️ 로그 파일 {log_file} 읽기 실패: {e}")
            
            if parsing_stats:
                print(f"  📊 총 파싱 실패: {total_failures:,}건")
                
                for section, count in sorted(parsing_stats.items(), key=lambda x: x[1], reverse=True):
                    failure_rate = (count / total_failures * 100)
                    print(f"    - {section}: {count:,}건 ({failure_rate:.1f}%)")
                
                self.validation_results['parsing_failure_rates'] = parsing_stats
            else:
                print("  ✅ 파싱 실패 로그 없음")
            
            return parsing_stats
            
        except Exception as e:
            print(f"❌ 파싱 실패 분석 실패: {e}")
            return {}
    
    def generate_recommendations(self) -> List[str]:
        """데이터 개선 권장사항 생성"""
        print("\n💡 개선 권장사항 생성...")
        
        recommendations = []
        
        # 완성도 기반 권장사항
        for section, data in self.validation_results['section_completeness'].items():
            if isinstance(data, dict) and data.get('completeness_rate', 0) < 70:
                rate = data['completeness_rate']
                missing = data.get('missing_count', 0)
                
                if rate < 30:
                    recommendations.append(f"🚨 {section} 섹션 심각한 데이터 누락 ({rate:.1f}%) - 파서 구현 필요")
                elif rate < 70:
                    recommendations.append(f"⚠️ {section} 섹션 데이터 부족 ({rate:.1f}%) - 파싱 로직 개선 필요")
        
        # 데이터 품질 기반 권장사항
        for issue in self.validation_results['data_quality_issues']:
            if issue['severity'] == 'high':
                recommendations.append(f"🔴 {issue['description']} - 즉시 수정 필요 ({issue['count']}건)")
            elif issue['severity'] == 'medium':
                recommendations.append(f"🟡 {issue['description']} - 검토 필요 ({issue['count']}건)")
        
        # 파싱 실패 기반 권장사항
        parsing_failures = self.validation_results.get('parsing_failure_rates', {})
        high_failure_sections = [section for section, count in parsing_failures.items() if count > 100]
        
        for section in high_failure_sections:
            recommendations.append(f"📋 {section} 섹션 파싱 실패율 높음 - 에러 핸들링 강화 필요")
        
        # 전반적인 권장사항
        total_props = self.validation_results['total_properties']
        if total_props > 0:
            avg_completeness = sum(
                data.get('completeness_rate', 0) 
                for data in self.validation_results['section_completeness'].values()
                if isinstance(data, dict)
            ) / len(self.validation_results['section_completeness'])
            
            if avg_completeness < 70:
                recommendations.append("📈 전체 데이터 완성도 개선을 위한 파서 확장 필요")
            elif avg_completeness >= 90:
                recommendations.append("✨ 데이터 품질 우수 - 지속적인 모니터링 권장")
        
        self.validation_results['recommendations'] = recommendations
        
        for rec in recommendations:
            print(f"  {rec}")
        
        if not recommendations:
            print("  ✅ 특별한 개선사항 없음")
        
        return recommendations
    
    def save_validation_report(self, output_file: str = None) -> str:
        """검증 보고서 저장"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"data_validation_report_{timestamp}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 검증 보고서 저장: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ 보고서 저장 실패: {e}")
            return ""
    
    def run_full_validation(self) -> Dict:
        """전체 데이터 검증 실행"""
        print("🚀 전체 데이터 검증 시작")
        print("=" * 60)
        
        # 1. 데이터 완성도 검증
        self.validate_data_completeness()
        
        # 2. 데이터 품질 검증
        self.validate_data_quality()
        
        # 3. 파싱 실패 분석
        self.analyze_parsing_failures()
        
        # 4. 개선 권장사항 생성
        self.generate_recommendations()
        
        # 5. 보고서 저장
        report_file = self.save_validation_report()
        
        print("\n" + "=" * 60)
        print("✅ 전체 데이터 검증 완료")
        
        return self.validation_results

def main():
    """메인 실행 함수"""
    validator = DataValidationSuite()
    results = validator.run_full_validation()
    
    # 요약 출력
    print(f"\n📋 검증 요약:")
    print(f"  - 총 매물: {results['total_properties']:,}개")
    print(f"  - 검증된 섹션: {len(results['section_completeness'])}개")
    print(f"  - 품질 이슈: {len(results['data_quality_issues'])}건")
    print(f"  - 권장사항: {len(results['recommendations'])}개")

if __name__ == "__main__":
    main()