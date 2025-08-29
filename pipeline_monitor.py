#!/usr/bin/env python3
"""
실시간 데이터 파이프라인 모니터링
- 외래키 해결 성공률 추적
- NULL 값 비율 모니터링
- 카카오 API 변환 성공률
"""

from supabase import create_client
from datetime import datetime, timedelta

class PipelineMonitor:
    def __init__(self):
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def check_foreign_key_health(self):
        """외래키 의존성 건강 상태 체크"""
        print("🔗 외래키 건강 상태 체크")
        print("-" * 30)
        
        # 1. 참조 테이블 레코드 수
        ref_tables = ['real_estate_types', 'trade_types', 'regions']
        for table in ref_tables:
            try:
                count = self.client.table(table).select('id', count='exact').execute()
                print(f"  {table}: {count.count}개")
            except Exception as e:
                print(f"  ❌ {table}: 조회 실패 - {e}")
        
        # 2. properties_new 테이블의 NULL 외래키 비율
        try:
            total_props = self.client.table('properties_new').select('id', count='exact').execute()
            null_ret = self.client.table('properties_new').select('id', count='exact').is_('real_estate_type_id', 'null').execute()
            null_trade = self.client.table('properties_new').select('id', count='exact').is_('trade_type_id', 'null').execute()
            null_region = self.client.table('properties_new').select('id', count='exact').is_('region_id', 'null').execute()
            
            if total_props.count > 0:
                print(f"\n📊 외래키 NULL 비율:")
                print(f"  전체 매물: {total_props.count}개")
                print(f"  부동산유형 NULL: {null_ret.count}개 ({null_ret.count/total_props.count*100:.1f}%)")
                print(f"  거래유형 NULL: {null_trade.count}개 ({null_trade.count/total_props.count*100:.1f}%)")
                print(f"  지역 NULL: {null_region.count}개 ({null_region.count/total_props.count*100:.1f}%)")
            
        except Exception as e:
            print(f"  ❌ 외래키 분석 실패: {e}")
    
    def check_kakao_integration_health(self):
        """카카오 API 통합 상태 체크"""
        print("\n🗺️ 카카오 API 통합 상태")
        print("-" * 30)
        
        try:
            # property_locations 테이블에서 address_enriched 상태 확인
            total_locations = self.client.table('property_locations').select('id', count='exact').execute()
            enriched = self.client.table('property_locations').select('id', count='exact').eq('address_enriched', True).execute()
            
            if total_locations.count > 0:
                success_rate = enriched.count / total_locations.count * 100
                print(f"  전체 위치 정보: {total_locations.count}개")
                print(f"  카카오 변환 성공: {enriched.count}개")
                print(f"  성공률: {success_rate:.1f}%")
                
                if success_rate < 50:
                    print("  ⚠️ 카카오 변환 성공률 낮음 - API 키 또는 컬럼 문제 확인 필요")
            else:
                print("  📭 위치 데이터 없음")
                
        except Exception as e:
            print(f"  ❌ 카카오 통합 분석 실패: {e}")
            print("  💡 property_locations 테이블에 address_enriched 컬럼이 없을 수 있습니다")
    
    def check_data_quality_metrics(self):
        """데이터 품질 메트릭 체크"""
        print("\n📈 데이터 품질 메트릭")
        print("-" * 30)
        
        # 최근 24시간 수집 통계
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        try:
            # 최근 수집된 매물 수
            recent = self.client.table('properties_new').select('id', count='exact').gte('created_at', yesterday).execute()
            print(f"  최근 24시간 수집: {recent.count}개")
            
            # 활성 매물 비율
            active = self.client.table('properties_new').select('id', count='exact').eq('is_active', True).execute()
            total = self.client.table('properties_new').select('id', count='exact').execute()
            
            if total.count > 0:
                active_rate = active.count / total.count * 100
                print(f"  활성 매물 비율: {active_rate:.1f}%")
            
        except Exception as e:
            print(f"  ❌ 데이터 품질 분석 실패: {e}")
    
    def run_comprehensive_check(self):
        """종합 상태 점검"""
        print("=" * 60)
        print("🔍 데이터 파이프라인 종합 상태 점검")
        print(f"📅 점검 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        self.check_foreign_key_health()
        self.check_kakao_integration_health() 
        self.check_data_quality_metrics()
        
        print("\n" + "=" * 60)
        print("✅ 종합 상태 점검 완료")
        print("💡 문제 발견 시 fix_data_pipeline.py 실행 권장")
        print("=" * 60)

if __name__ == "__main__":
    monitor = PipelineMonitor()
    monitor.run_comprehensive_check()
