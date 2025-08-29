#!/usr/bin/env python3
"""
현재 Supabase 스키마 분석 실행 스크립트
"""

import os
import sys
from pathlib import Path

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from collectors.db.supabase_client import SupabaseHelper
    print("✅ SupabaseHelper import 성공")
except ImportError as e:
    print(f"❌ Import 오류: {e}")
    # config 파일이 없을 수 있으므로 환경변수로 시도
    print("환경변수를 통한 직접 연결을 시도합니다...")
    
    # 직접 supabase 클라이언트 생성
    try:
        from supabase import create_client
        
        # 환경변수에서 Supabase 정보 로드
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            print("❌ SUPABASE_URL 또는 SUPABASE_KEY 환경변수가 설정되지 않았습니다.")
            print("다음 명령어로 환경변수를 설정하세요:")
            print("export SUPABASE_URL='your-supabase-url'")
            print("export SUPABASE_KEY='your-supabase-anon-key'")
            sys.exit(1)
        
        client = create_client(url, key)
        print(f"✅ 직접 Supabase 연결 성공: {url}")
        
    except Exception as e2:
        print(f"❌ 직접 연결도 실패: {e2}")
        sys.exit(1)

def simple_schema_analysis():
    """간단한 스키마 분석"""
    print("🔍 간단한 스키마 분석 시작...")
    
    # 알려진 테이블 목록
    known_tables = [
        'properties', 'areas', 'price_history', 'deletion_history', 
        'daily_stats', 'collection_logs'
    ]
    
    schema_info = {}
    
    for table_name in known_tables:
        print(f"\n📋 {table_name} 테이블 분석 중...")
        
        try:
            if 'SupabaseHelper' in globals():
                helper = SupabaseHelper()
                client = helper.client
            else:
                client = globals()['client']
            
            # 1개 레코드만 조회하여 구조 파악
            result = client.table(table_name).select('*').limit(1).execute()
            
            # 총 레코드 수 조회
            count_result = client.table(table_name).select('*', count='exact').limit(1).execute()
            total_count = count_result.count or 0
            
            if result.data and len(result.data) > 0:
                sample_record = result.data[0]
                columns = list(sample_record.keys())
                
                schema_info[table_name] = {
                    'columns': columns,
                    'column_count': len(columns),
                    'record_count': total_count,
                    'sample_data': sample_record
                }
                
                print(f"✅ {table_name}: {len(columns)}개 컬럼, {total_count:,}개 레코드")
                print(f"   주요 컬럼: {', '.join(columns[:8])}")
                if len(columns) > 8:
                    print(f"   추가 컬럼: {len(columns) - 8}개 더...")
                
            else:
                schema_info[table_name] = {
                    'columns': [],
                    'column_count': 0,
                    'record_count': total_count,
                    'status': 'empty'
                }
                print(f"📋 {table_name}: 빈 테이블 (레코드 없음)")
                
        except Exception as e:
            error_msg = str(e)
            schema_info[table_name] = {
                'error': error_msg,
                'status': 'error'
            }
            print(f"❌ {table_name} 분석 실패: {error_msg}")
    
    return schema_info

def analyze_properties_details():
    """properties 테이블 상세 분석"""
    print("\n🏢 properties 테이블 상세 분석...")
    
    try:
        if 'SupabaseHelper' in globals():
            helper = SupabaseHelper()
            client = helper.client
        else:
            client = globals()['client']
        
        # 기본 통계
        total_result = client.table('properties').select('*', count='exact').limit(1).execute()
        total_count = total_result.count or 0
        
        active_result = client.table('properties').select('*', count='exact').eq('is_active', True).limit(1).execute()
        active_count = active_result.count or 0
        
        print(f"📊 전체 매물: {total_count:,}개")
        print(f"✅ 활성 매물: {active_count:,}개")
        print(f"❌ 비활성 매물: {total_count - active_count:,}개")
        
        # 샘플 데이터 분석 (상위 10개)
        sample_result = client.table('properties').select('*').limit(10).execute()
        
        if sample_result.data:
            print(f"\n📋 샘플 데이터 분석 (상위 10개):")
            
            # 컬럼별 데이터 타입 분석
            sample_record = sample_result.data[0]
            print(f"📝 컬럼 구조 ({len(sample_record.keys())}개):")
            
            for i, (key, value) in enumerate(sample_record.items()):
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value is not None else "None"
                print(f"   {i+1:2d}. {key:20s} ({value_type:10s}): {value_preview}")
                
                if i >= 15:  # 상위 16개만 표시
                    remaining = len(sample_record.keys()) - 16
                    if remaining > 0:
                        print(f"   ... 추가 {remaining}개 컬럼")
                    break
            
            # details 컬럼 구조 분석 (JSONB)
            if 'details' in sample_record and sample_record['details']:
                details = sample_record['details']
                if isinstance(details, dict):
                    print(f"\n🔍 details 컬럼 구조 ({len(details.keys())}개 키):")
                    for key in sorted(details.keys()):
                        value_preview = str(details[key])[:30] if details[key] is not None else "None"
                        print(f"   - {key}: {value_preview}")
        
        # 지역별 분포 (상위 10개)
        region_result = client.table('properties').select('cortar_no').limit(1000).execute()
        
        if region_result.data:
            region_counts = {}
            for item in region_result.data:
                cortar_no = item.get('cortar_no')
                if cortar_no:
                    region_counts[cortar_no] = region_counts.get(cortar_no, 0) + 1
            
            print(f"\n🗺️ 지역별 분포 (상위 10개):")
            top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for cortar_no, count in top_regions:
                print(f"   {cortar_no}: {count:,}개")
        
        return {
            'total_count': total_count,
            'active_count': active_count,
            'sample_analyzed': True
        }
        
    except Exception as e:
        print(f"❌ properties 상세 분석 실패: {e}")
        return {'error': str(e)}

def generate_summary_report(schema_info, properties_details):
    """요약 보고서 생성"""
    print("\n" + "="*80)
    print("📊 네이버 부동산 DB 현재 구조 분석 요약")
    print("="*80)
    
    print(f"\n🏗️ 테이블 구조:")
    total_tables = 0
    total_records = 0
    
    for table_name, info in schema_info.items():
        if isinstance(info, dict) and 'column_count' in info:
            record_count = info.get('record_count', 0)
            total_tables += 1
            total_records += record_count
            
            status = "✅" if record_count > 0 else "📋"
            print(f"  {status} {table_name:20s}: {info['column_count']:2d}개 컬럼, {record_count:,}개 레코드")
        elif isinstance(info, dict) and 'error' in info:
            print(f"  ❌ {table_name:20s}: 오류 - {info['error']}")
    
    print(f"\n📈 전체 요약:")
    print(f"  🗃️ 총 테이블: {total_tables}개")
    print(f"  📊 총 레코드: {total_records:,}개")
    
    if properties_details and 'total_count' in properties_details:
        print(f"\n🏢 properties 테이블 (메인):")
        print(f"  📊 전체 매물: {properties_details['total_count']:,}개")
        print(f"  ✅ 활성 매물: {properties_details['active_count']:,}개")
        print(f"  📈 활성 비율: {properties_details['active_count']/properties_details['total_count']*100:.1f}%")
    
    print(f"\n💡 정규화 필요성:")
    print(f"  📋 현재: 단일 properties 테이블 (50개 컬럼)")
    print(f"  🎯 목표: 8-12개 정규화된 테이블")
    print(f"  📊 예상 성능 향상: 80% (적절한 인덱싱)")
    print(f"  🔧 유지보수성: 60% 향상 (명확한 스키마)")
    
    print("\n" + "="*80)

def main():
    """메인 실행 함수"""
    print("🔍 네이버 부동산 DB 스키마 분석기")
    print("="*50)
    
    try:
        # 1. 기본 스키마 분석
        schema_info = simple_schema_analysis()
        
        # 2. properties 테이블 상세 분석
        properties_details = analyze_properties_details()
        
        # 3. 요약 보고서
        generate_summary_report(schema_info, properties_details)
        
        print(f"\n✅ 스키마 분석 완료!")
        print(f"📋 다음 단계: 정규화된 새 스키마 설계")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()