#!/usr/bin/env python3
"""
네이버 부동산 수집기 응급 복구 스크립트
- 누락된 daily_stats 자동 생성
- 데이터 품질 응급 복구
- 시스템 건강성 복원
"""

from datetime import date, timedelta, datetime
from supabase_client import SupabaseHelper
import json

class EmergencyRecoverySystem:
    def __init__(self):
        self.helper = SupabaseHelper()
        
    def recover_missing_daily_stats(self):
        """누락된 daily_stats 복구"""
        print("=" * 60)
        print("📈 누락된 daily_stats 복구 시작")
        print("=" * 60)
        
        # 8월 17일~19일 (3일간 누락 추정)
        missing_dates = []
        for days_ago in [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]:
            target_date = date.today() - timedelta(days=days_ago)
            missing_dates.append(target_date)
        
        recovered_count = 0
        
        for target_date in missing_dates:
            print(f"\n🔍 {target_date} 통계 복구 중...")
            
            # 해당 날짜 매물 조회
            try:
                properties_query = self.helper.client.table('properties')\
                    .select('*')\
                    .eq('collected_date', target_date.isoformat())\
                    .execute()
                
                if not properties_query.data:
                    print(f"   ⏭️ {target_date}: 매물 데이터 없음")
                    continue
                
                # 지역별로 그룹핑
                by_cortar = {}
                for prop in properties_query.data:
                    cortar_no = prop['cortar_no']
                    if cortar_no not in by_cortar:
                        by_cortar[cortar_no] = []
                    by_cortar[cortar_no].append(prop)
                
                # 각 지역별 통계 생성
                for cortar_no, props in by_cortar.items():
                    try:
                        # 기존 통계 확인
                        existing_stats = self.helper.client.table('daily_stats')\
                            .select('*')\
                            .eq('stat_date', target_date.isoformat())\
                            .eq('cortar_no', cortar_no)\
                            .execute()
                        
                        if existing_stats.data:
                            print(f"   ✅ {cortar_no}: 통계 이미 존재")
                            continue
                        
                        # 통계 생성
                        fake_save_stats = {
                            'new_count': len(props),
                            'updated_count': 0, 
                            'removed_count': 0
                        }
                        
                        self.helper.save_daily_stats(target_date, cortar_no, props, fake_save_stats)
                        print(f"   ✅ {cortar_no}: 통계 생성 완료 ({len(props)}개 매물)")
                        recovered_count += 1
                        
                    except Exception as e:
                        print(f"   ❌ {cortar_no}: 통계 생성 실패 - {e}")
                
            except Exception as e:
                print(f"   ❌ {target_date}: 매물 조회 실패 - {e}")
        
        print(f"\n✅ daily_stats 복구 완료: {recovered_count}개 통계 복구")
        return recovered_count
    
    def repair_data_quality_issues(self):
        """데이터 품질 응급 복구"""
        print("\n" + "=" * 60) 
        print("🔧 데이터 품질 응급 복구 시작")
        print("=" * 60)
        
        # 8월 16일 이후 품질 문제 데이터 조회
        try:
            problematic_query = self.helper.client.table('properties')\
                .select('article_no, details, address_road, latitude, longitude')\
                .gte('collected_date', '2025-08-16')\
                .is_('address_road', 'null')\
                .limit(200)\
                .execute()
            
            if not problematic_query.data:
                print("✅ 복구할 데이터가 없습니다.")
                return 0
            
            repaired_count = 0
            
            for prop in problematic_query.data:
                article_no = prop['article_no']
                details = prop.get('details', {})
                
                if not isinstance(details, dict):
                    continue
                
                # details에서 주소 정보 추출 시도
                repair_data = {}
                
                # 위치정보에서 주소 추출
                location_info = details.get('위치정보', {})
                if location_info:
                    if location_info.get('도로명주소'):
                        repair_data['address_road'] = location_info['도로명주소']
                    if location_info.get('지번주소'):
                        repair_data['address_jibun'] = location_info['지번주소']
                    if location_info.get('정확한_위도'):
                        repair_data['latitude'] = float(location_info['정확한_위도'])
                    if location_info.get('정확한_경도'):
                        repair_data['longitude'] = float(location_info['정확한_경도'])
                
                # 카카오 주소 변환 결과에서 추출
                kakao_info = details.get('카카오주소변환', {})
                if kakao_info:
                    if kakao_info.get('도로명주소') and not repair_data.get('address_road'):
                        repair_data['address_road'] = kakao_info['도로명주소']
                    if kakao_info.get('지번주소') and not repair_data.get('address_jibun'):
                        repair_data['address_jibun'] = kakao_info['지번주소']
                    if kakao_info.get('건물명'):
                        repair_data['building_name'] = kakao_info['건물명']
                
                # 복구할 데이터가 있으면 업데이트
                if repair_data:
                    try:
                        self.helper.client.table('properties')\
                            .update(repair_data)\
                            .eq('article_no', article_no)\
                            .execute()
                        
                        repaired_fields = list(repair_data.keys())
                        print(f"   ✅ {article_no}: {repaired_fields} 복구")
                        repaired_count += 1
                        
                    except Exception as e:
                        print(f"   ❌ {article_no}: 복구 실패 - {e}")
            
            print(f"\n✅ 데이터 품질 복구 완료: {repaired_count}개 매물 복구")
            return repaired_count
            
        except Exception as e:
            print(f"❌ 데이터 품질 복구 실패: {e}")
            return 0
    
    def generate_recovery_report(self, stats_recovered, data_repaired):
        """복구 보고서 생성"""
        print("\n" + "=" * 60)
        print("📊 응급 복구 완료 보고서")
        print("=" * 60)
        
        # 현재 상태 재확인
        try:
            # 최신 daily_stats 확인
            latest_stats = self.helper.client.table('daily_stats')\
                .select('stat_date')\
                .order('stat_date', desc=True)\
                .limit(1)\
                .execute()
            
            latest_stats_date = latest_stats.data[0]['stat_date'] if latest_stats.data else "없음"
            
            # 최신 매물 확인  
            latest_properties = self.helper.client.table('properties')\
                .select('collected_date')\
                .order('collected_date', desc=True)\
                .limit(1)\
                .execute()
            
            latest_prop_date = latest_properties.data[0]['collected_date'] if latest_properties.data else "없음"
            
            # 품질 재확인
            quality_check = self.helper.client.table('properties')\
                .select('article_no')\
                .gte('collected_date', '2025-08-16')\
                .not_('address_road', 'is', 'null')\
                .limit(1)\
                .execute()
            
            quality_improved = len(quality_check.data) > 0
            
            print(f"📈 Statistics 복구:     {stats_recovered}개")
            print(f"🔧 데이터 품질 복구:    {data_repaired}개 매물")  
            print(f"📅 최신 통계 날짜:      {latest_stats_date}")
            print(f"📅 최신 매물 날짜:      {latest_prop_date}")
            print(f"✅ 주소 품질 개선:      {'예' if quality_improved else '아니오'}")
            
            # 보고서 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"recovery_report_{timestamp}.json"
            
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'recovery_summary': {
                    'stats_recovered': stats_recovered,
                    'data_repaired': data_repaired,
                    'latest_stats_date': latest_stats_date,
                    'latest_prop_date': latest_prop_date,
                    'quality_improved': quality_improved
                }
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"📄 상세 보고서:        {report_file}")
            
            if stats_recovered > 0 or data_repaired > 0:
                print("\n🎉 응급 복구가 성공적으로 완료되었습니다!")
                
                print("\n📋 후속 작업 권장사항:")
                print("1. 수집기 구조 개선 (통합 수집기 구현)")
                print("2. 자동 품질 검증 시스템 도입")
                print("3. 실시간 모니터링 대시보드 구축")
                print("4. 카카오 API 의존성 최소화")
            else:
                print("\n⚠️ 복구할 데이터가 없었습니다. 시스템 점검이 필요할 수 있습니다.")
                
        except Exception as e:
            print(f"❌ 보고서 생성 실패: {e}")
    
    def quick_health_check(self):
        """빠른 시스템 건강성 체크"""
        print("🔍 시스템 건강성 체크...")
        
        health_issues = []
        
        try:
            # 1. 최근 수집 활동 체크
            recent_logs = self.helper.client.table('collection_logs')\
                .select('*')\
                .gte('created_at', (datetime.now() - timedelta(hours=24)).isoformat())\
                .execute()
            
            if not recent_logs.data:
                health_issues.append("❌ 최근 24시간 수집 로그 없음")
            else:
                print(f"✅ 최근 24시간 수집 로그: {len(recent_logs.data)}개")
            
            # 2. 데이터 품질 체크
            quality_sample = self.helper.client.table('properties')\
                .select('address_road, latitude')\
                .gte('collected_date', (date.today() - timedelta(days=3)).isoformat())\
                .limit(10)\
                .execute()
            
            if quality_sample.data:
                null_count = sum(1 for p in quality_sample.data if not p.get('address_road'))
                if null_count > 5:
                    health_issues.append(f"⚠️ 최근 데이터 품질 저하: {null_count}/10 NULL")
                else:
                    print(f"✅ 최근 데이터 품질: {10-null_count}/10 정상")
            
            # 3. 통계 업데이트 체크
            recent_stats = self.helper.client.table('daily_stats')\
                .select('stat_date')\
                .order('stat_date', desc=True)\
                .limit(1)\
                .execute()
            
            if recent_stats.data:
                latest_stat_date = datetime.fromisoformat(recent_stats.data[0]['stat_date']).date()
                days_behind = (date.today() - latest_stat_date).days
                
                if days_behind > 2:
                    health_issues.append(f"⚠️ 통계 업데이트 {days_behind}일 지연")
                else:
                    print(f"✅ 통계 업데이트: {days_behind}일 지연 (정상)")
            else:
                health_issues.append("❌ 통계 데이터 없음")
            
        except Exception as e:
            health_issues.append(f"❌ 건강성 체크 실패: {e}")
        
        if health_issues:
            print("\n🚨 발견된 건강성 문제:")
            for issue in health_issues:
                print(f"   {issue}")
        else:
            print("\n✅ 시스템이 정상 상태입니다.")
        
        return health_issues

def main():
    """응급 복구 메인 프로세스"""
    print("🚨 네이버 부동산 수집기 응급 복구 시작")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    recovery_system = EmergencyRecoverySystem()
    
    # 1. 시스템 건강성 사전 체크
    health_issues = recovery_system.quick_health_check()
    
    # 2. 누락된 통계 복구
    stats_recovered = recovery_system.recover_missing_daily_stats()
    
    # 3. 데이터 품질 복구
    data_repaired = recovery_system.repair_data_quality_issues()
    
    # 4. 복구 보고서 생성
    recovery_system.generate_recovery_report(stats_recovered, data_repaired)
    
    print("\n" + "="*60)
    print("🏁 응급 복구 프로세스 완료")
    print("="*60)

if __name__ == "__main__":
    main()