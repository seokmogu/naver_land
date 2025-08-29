#!/usr/bin/env python3
"""
현재 Supabase 데이터베이스 스키마 분석 도구
실제 테이블 구조, 컬럼, 인덱스, 데이터 분포를 분석
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from collectors.db.supabase_client import SupabaseHelper
except ImportError as e:
    print(f"❌ Import 오류: {e}")
    print("collectors/db/supabase_client.py 파일을 확인해주세요.")
    sys.exit(1)

class SchemaAnalyzer:
    def __init__(self):
        """스키마 분석기 초기화"""
        try:
            self.helper = SupabaseHelper()
            print("✅ Supabase 연결 성공")
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {e}")
            sys.exit(1)
    
    def analyze_table_structure(self):
        """테이블 구조 분석"""
        print("\n🔍 테이블 구조 분석 중...")
        
        # PostgreSQL 시스템 테이블을 통한 스키마 분석
        schema_query = """
        SELECT 
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        ORDER BY table_name, ordinal_position
        """
        
        try:
            # Raw SQL 쿼리 실행
            result = self.helper.client.rpc('get_schema_info', {'query': schema_query}).execute()
            
            if result.data:
                return self._organize_schema_data(result.data)
            else:
                print("⚠️ 스키마 정보를 가져올 수 없습니다. 직접 테이블 조회를 시도합니다.")
                return self._analyze_known_tables()
                
        except Exception as e:
            print(f"⚠️ 시스템 테이블 조회 실패: {e}")
            return self._analyze_known_tables()
    
    def _analyze_known_tables(self):
        """알려진 테이블들 직접 분석"""
        print("📋 알려진 테이블 직접 분석 중...")
        
        known_tables = ['properties', 'areas', 'price_history', 'deletion_history', 'daily_stats', 'collection_logs']
        schema_info = {}
        
        for table_name in known_tables:
            try:
                # 각 테이블에서 1개 레코드만 조회하여 구조 파악
                result = self.helper.client.table(table_name).select('*').limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    sample_record = result.data[0]
                    schema_info[table_name] = {
                        'columns': list(sample_record.keys()),
                        'sample_data': sample_record,
                        'record_count': self._get_table_count(table_name)
                    }
                    print(f"✅ {table_name}: {len(sample_record.keys())}개 컬럼, {schema_info[table_name]['record_count']:,}개 레코드")
                else:
                    schema_info[table_name] = {
                        'columns': [],
                        'sample_data': None,
                        'record_count': 0
                    }
                    print(f"📋 {table_name}: 빈 테이블")
                    
            except Exception as e:
                print(f"❌ {table_name} 분석 실패: {e}")
                schema_info[table_name] = {'error': str(e)}
        
        return schema_info
    
    def _get_table_count(self, table_name):
        """테이블 레코드 수 조회"""
        try:
            result = self.helper.client.table(table_name).select('*', count='exact').limit(1).execute()
            return result.count or 0
        except:
            return 0
    
    def analyze_properties_table_details(self):
        """properties 테이블 상세 분석"""
        print("\n🏢 properties 테이블 상세 분석...")
        
        try:
            # 기본 통계
            total_count = self._get_table_count('properties')
            active_count = self.helper.client.table('properties').select('*', count='exact').eq('is_active', True).limit(1).execute().count or 0
            
            # 날짜별 분포
            date_distribution = self.helper.client.table('properties').select('collected_date').execute()
            
            # 지역별 분포
            region_distribution = self.helper.client.table('properties').select('cortar_no').limit(100).execute()
            
            # 가격 분포 (상위 100개만)
            price_sample = self.helper.client.table('properties').select('price, rent_price').limit(100).execute()
            
            # details 컬럼 구조 분석
            details_sample = self.helper.client.table('properties').select('details').limit(10).execute()
            
            analysis = {
                'total_records': total_count,
                'active_records': active_count,
                'inactive_records': total_count - active_count,
                'date_range': self._analyze_date_range(date_distribution.data) if date_distribution.data else None,
                'region_sample': self._analyze_region_distribution(region_distribution.data) if region_distribution.data else None,
                'price_analysis': self._analyze_price_distribution(price_sample.data) if price_sample.data else None,
                'details_structure': self._analyze_details_structure(details_sample.data) if details_sample.data else None
            }
            
            return analysis
            
        except Exception as e:
            print(f"❌ properties 테이블 상세 분석 실패: {e}")
            return {'error': str(e)}
    
    def _analyze_date_range(self, date_data):
        """날짜 범위 분석"""
        if not date_data:
            return None
            
        dates = [item.get('collected_date') for item in date_data if item.get('collected_date')]
        if dates:
            return {
                'earliest': min(dates),
                'latest': max(dates),
                'total_days': len(set(dates))
            }
        return None
    
    def _analyze_region_distribution(self, region_data):
        """지역 분포 분석"""
        if not region_data:
            return None
            
        regions = {}
        for item in region_data:
            cortar_no = item.get('cortar_no')
            if cortar_no:
                regions[cortar_no] = regions.get(cortar_no, 0) + 1
        
        return {
            'total_regions': len(regions),
            'top_regions': sorted(regions.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _analyze_price_distribution(self, price_data):
        """가격 분포 분석"""
        if not price_data:
            return None
        
        prices = [item.get('price', 0) for item in price_data if isinstance(item.get('price'), (int, float)) and item.get('price') > 0]
        rent_prices = [item.get('rent_price', 0) for item in price_data if isinstance(item.get('rent_price'), (int, float)) and item.get('rent_price') > 0]
        
        analysis = {}
        
        if prices:
            analysis['sale_prices'] = {
                'min': min(prices),
                'max': max(prices),
                'avg': sum(prices) / len(prices),
                'count': len(prices)
            }
        
        if rent_prices:
            analysis['rent_prices'] = {
                'min': min(rent_prices),
                'max': max(rent_prices),
                'avg': sum(rent_prices) / len(rent_prices),
                'count': len(rent_prices)
            }
        
        return analysis
    
    def _analyze_details_structure(self, details_data):
        """details JSONB 컬럼 구조 분석"""
        if not details_data:
            return None
        
        all_keys = set()
        structure_examples = {}
        
        for item in details_data:
            details = item.get('details', {})
            if isinstance(details, dict):
                for key in details.keys():
                    all_keys.add(key)
                    if key not in structure_examples:
                        structure_examples[key] = details[key]
        
        return {
            'total_unique_keys': len(all_keys),
            'all_keys': list(all_keys),
            'structure_examples': structure_examples
        }
    
    def analyze_data_quality(self):
        """데이터 품질 분석"""
        print("\n📊 데이터 품질 분석 중...")
        
        try:
            # 필수 필드 누락 분석
            quality_issues = {}
            
            # NULL 값 분석
            properties_sample = self.helper.client.table('properties').select('*').limit(1000).execute()
            
            if properties_sample.data:
                quality_issues['null_analysis'] = self._analyze_null_values(properties_sample.data)
                quality_issues['duplicate_analysis'] = self._check_duplicates()
                quality_issues['data_consistency'] = self._check_data_consistency(properties_sample.data)
            
            return quality_issues
            
        except Exception as e:
            print(f"❌ 데이터 품질 분석 실패: {e}")
            return {'error': str(e)}
    
    def _analyze_null_values(self, data):
        """NULL 값 분석"""
        if not data:
            return None
            
        null_counts = {}
        total_records = len(data)
        
        # 첫 번째 레코드에서 컬럼 목록 추출
        if data:
            columns = data[0].keys()
            
            for col in columns:
                null_count = sum(1 for record in data if record.get(col) is None or record.get(col) == '')
                if null_count > 0:
                    null_counts[col] = {
                        'null_count': null_count,
                        'null_percentage': (null_count / total_records) * 100
                    }
        
        return null_counts
    
    def _check_duplicates(self):
        """중복 데이터 확인"""
        try:
            # article_no 중복 확인
            duplicates = self.helper.client.rpc('check_article_duplicates').execute()
            return duplicates.data if duplicates.data else "중복 검사 함수 없음"
        except:
            return "중복 검사 불가"
    
    def _check_data_consistency(self, data):
        """데이터 일관성 확인"""
        issues = []
        
        for record in data[:100]:  # 상위 100개만 검사
            # 가격 일관성 (음수 값 확인)
            price = record.get('price', 0)
            rent_price = record.get('rent_price', 0)
            
            if isinstance(price, (int, float)) and price < 0:
                issues.append(f"음수 매매가: {record.get('article_no')}")
            
            if isinstance(rent_price, (int, float)) and rent_price < 0:
                issues.append(f"음수 월세: {record.get('article_no')}")
            
            # 날짜 일관성 확인
            collected_date = record.get('collected_date')
            last_seen_date = record.get('last_seen_date')
            
            if collected_date and last_seen_date:
                if collected_date > last_seen_date:
                    issues.append(f"날짜 불일치: {record.get('article_no')}")
        
        return issues[:20]  # 상위 20개 이슈만 반환
    
    def generate_report(self):
        """전체 분석 보고서 생성"""
        print("📋 종합 분석 보고서 생성 중...")
        
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'schema_structure': self.analyze_table_structure(),
            'properties_details': self.analyze_properties_table_details(),
            'data_quality': self.analyze_data_quality()
        }
        
        # 보고서 파일 저장
        report_file = current_dir / f"current_database_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 분석 보고서 저장: {report_file}")
        
        return report
    
    def print_summary(self, report):
        """분석 결과 요약 출력"""
        print("\n" + "="*80)
        print("📊 네이버 부동산 DB 스키마 분석 결과 요약")
        print("="*80)
        
        # 테이블 구조 요약
        schema = report.get('schema_structure', {})
        print(f"\n🏗️ 테이블 구조:")
        for table_name, info in schema.items():
            if isinstance(info, dict) and 'columns' in info:
                print(f"  📋 {table_name}: {len(info['columns'])}개 컬럼, {info['record_count']:,}개 레코드")
                if table_name == 'properties':
                    print(f"     주요 컬럼: {', '.join(info['columns'][:10])}...")
        
        # properties 테이블 상세
        properties = report.get('properties_details', {})
        if properties and 'total_records' in properties:
            print(f"\n🏢 properties 테이블 상세:")
            print(f"  📊 전체 매물: {properties['total_records']:,}개")
            print(f"  ✅ 활성 매물: {properties['active_records']:,}개")
            print(f"  ❌ 비활성 매물: {properties['inactive_records']:,}개")
            
            if properties.get('date_range'):
                date_info = properties['date_range']
                print(f"  📅 수집 기간: {date_info['earliest']} ~ {date_info['latest']} ({date_info['total_days']}일)")
            
            if properties.get('region_sample', {}).get('total_regions'):
                print(f"  🗺️ 수집 지역: {properties['region_sample']['total_regions']}개 지역")
            
            if properties.get('details_structure'):
                details_info = properties['details_structure']
                print(f"  📝 상세정보 키: {details_info['total_unique_keys']}개 고유 키")
        
        # 데이터 품질
        quality = report.get('data_quality', {})
        if quality and 'null_analysis' in quality:
            print(f"\n🔍 데이터 품질:")
            null_analysis = quality['null_analysis']
            if null_analysis:
                print(f"  ⚠️ NULL 값이 있는 컬럼: {len(null_analysis)}개")
                high_null_cols = [col for col, info in null_analysis.items() if info['null_percentage'] > 10]
                if high_null_cols:
                    print(f"  ❌ 높은 NULL 비율 컬럼: {', '.join(high_null_cols)}")
            
            consistency_issues = quality.get('data_consistency', [])
            if consistency_issues:
                print(f"  🚨 일관성 문제: {len(consistency_issues)}개 발견")
        
        print("\n" + "="*80)

def main():
    """메인 실행 함수"""
    print("🔍 네이버 부동산 DB 스키마 분석기")
    print("="*50)
    
    analyzer = SchemaAnalyzer()
    
    try:
        # 전체 분석 실행
        report = analyzer.generate_report()
        
        # 결과 요약 출력
        analyzer.print_summary(report)
        
        print("\n✅ 분석 완료! 상세 결과는 JSON 파일을 확인하세요.")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()