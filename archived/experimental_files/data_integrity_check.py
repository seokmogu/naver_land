#!/usr/bin/env python3
"""
데이터베이스 테이블 간 정합성 체크
- 각 테이블별 최신 데이터 일자 확인
- 테이블 간 데이터 불일치 분석
- 수집 프로세스 문제점 파악
"""

import json
from datetime import datetime, date, timedelta
from supabase_client import SupabaseHelper

class DataIntegrityChecker:
    def __init__(self):
        self.helper = SupabaseHelper()
        
    def check_latest_data_dates(self):
        """각 테이블별 최신 데이터 일자 조회"""
        print("=" * 60)
        print("📊 각 테이블별 최신 데이터 일자 체크")
        print("=" * 60)
        
        results = {}
        
        # 1. properties 테이블
        try:
            # 최신 수집일 (collected_date)
            latest_collected = self.helper.client.table('properties')\
                .select('collected_date')\
                .order('collected_date', desc=True)\
                .limit(1)\
                .execute()
            
            # 최신 확인일 (last_seen_date)  
            latest_seen = self.helper.client.table('properties')\
                .select('last_seen_date')\
                .order('last_seen_date', desc=True)\
                .limit(1)\
                .execute()
            
            # 최신 생성일 (created_at)
            latest_created = self.helper.client.table('properties')\
                .select('created_at')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            # 활성 매물 수
            active_count = self.helper.client.table('properties')\
                .select('*', count='exact')\
                .eq('is_active', True)\
                .execute()
            
            # 총 매물 수
            total_count = self.helper.client.table('properties')\
                .select('*', count='exact')\
                .execute()
                
            results['properties'] = {
                'latest_collected_date': latest_collected.data[0]['collected_date'] if latest_collected.data else None,
                'latest_seen_date': latest_seen.data[0]['last_seen_date'] if latest_seen.data else None,
                'latest_created_at': latest_created.data[0]['created_at'] if latest_created.data else None,
                'active_count': active_count.count,
                'total_count': total_count.count
            }
            
            print(f"🏠 properties 테이블:")
            print(f"   최신 수집일: {results['properties']['latest_collected_date']}")
            print(f"   최신 확인일: {results['properties']['latest_seen_date']}")
            print(f"   최신 생성일: {results['properties']['latest_created_at']}")
            print(f"   활성 매물수: {results['properties']['active_count']:,}개")
            print(f"   총 매물수:   {results['properties']['total_count']:,}개")
            
        except Exception as e:
            print(f"❌ properties 테이블 조회 실패: {e}")
            results['properties'] = {'error': str(e)}
        
        print()
        
        # 2. collection_logs 테이블
        try:
            # 최신 로그
            latest_log = self.helper.client.table('collection_logs')\
                .select('created_at, status, dong_name')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            # 최신 완료 로그
            latest_completed = self.helper.client.table('collection_logs')\
                .select('created_at, dong_name, total_collected')\
                .eq('status', 'completed')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            # 오늘 로그 수
            today = date.today().isoformat()
            today_logs = self.helper.client.table('collection_logs')\
                .select('*', count='exact')\
                .gte('created_at', today)\
                .execute()
            
            # 최근 7일 완료 로그 수
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            week_completed = self.helper.client.table('collection_logs')\
                .select('*', count='exact')\
                .eq('status', 'completed')\
                .gte('created_at', week_ago)\
                .execute()
                
            results['collection_logs'] = {
                'latest_log_date': latest_log.data[0]['created_at'] if latest_log.data else None,
                'latest_log_status': latest_log.data[0]['status'] if latest_log.data else None,
                'latest_log_dong': latest_log.data[0]['dong_name'] if latest_log.data else None,
                'latest_completed_date': latest_completed.data[0]['created_at'] if latest_completed.data else None,
                'latest_completed_dong': latest_completed.data[0]['dong_name'] if latest_completed.data else None,
                'latest_completed_count': latest_completed.data[0]['total_collected'] if latest_completed.data else 0,
                'today_logs': today_logs.count,
                'week_completed': week_completed.count
            }
            
            print(f"📋 collection_logs 테이블:")
            print(f"   최신 로그일: {results['collection_logs']['latest_log_date']}")
            print(f"   최신 로그상태: {results['collection_logs']['latest_log_status']}")
            print(f"   최신 로그지역: {results['collection_logs']['latest_log_dong']}")
            print(f"   최신 완료일: {results['collection_logs']['latest_completed_date']}")
            print(f"   최신 완료지역: {results['collection_logs']['latest_completed_dong']}")
            print(f"   최신 완료매물: {results['collection_logs']['latest_completed_count']:,}개")
            print(f"   오늘 로그수: {results['collection_logs']['today_logs']}개")
            print(f"   최근7일완료: {results['collection_logs']['week_completed']}개")
            
        except Exception as e:
            print(f"❌ collection_logs 테이블 조회 실패: {e}")
            results['collection_logs'] = {'error': str(e)}
        
        print()
        
        # 3. daily_stats 테이블
        try:
            # 최신 통계일
            latest_stats = self.helper.client.table('daily_stats')\
                .select('stat_date, cortar_no, total_count')\
                .order('stat_date', desc=True)\
                .limit(1)\
                .execute()
            
            # 최신 통계 레코드 수
            total_stats = self.helper.client.table('daily_stats')\
                .select('*', count='exact')\
                .execute()
            
            # 최근 7일 통계 수
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            week_stats = self.helper.client.table('daily_stats')\
                .select('*', count='exact')\
                .gte('stat_date', week_ago)\
                .execute()
                
            results['daily_stats'] = {
                'latest_stat_date': latest_stats.data[0]['stat_date'] if latest_stats.data else None,
                'latest_stat_cortar': latest_stats.data[0]['cortar_no'] if latest_stats.data else None,
                'latest_stat_count': latest_stats.data[0]['total_count'] if latest_stats.data else 0,
                'total_stats': total_stats.count,
                'week_stats': week_stats.count
            }
            
            print(f"📈 daily_stats 테이블:")
            print(f"   최신 통계일: {results['daily_stats']['latest_stat_date']}")
            print(f"   최신 통계지역: {results['daily_stats']['latest_stat_cortar']}")
            print(f"   최신 통계매물: {results['daily_stats']['latest_stat_count']:,}개")
            print(f"   총 통계레코드: {results['daily_stats']['total_stats']}개")
            print(f"   최근7일통계: {results['daily_stats']['week_stats']}개")
            
        except Exception as e:
            print(f"❌ daily_stats 테이블 조회 실패: {e}")
            results['daily_stats'] = {'error': str(e)}
        
        print()
        
        # 4. price_history 테이블
        try:
            # 최신 가격 변동일
            latest_price = self.helper.client.table('price_history')\
                .select('changed_date, article_no, change_amount')\
                .order('changed_date', desc=True)\
                .limit(1)\
                .execute()
            
            # 총 가격 변동 레코드 수
            total_price_history = self.helper.client.table('price_history')\
                .select('*', count='exact')\
                .execute()
            
            # 최근 7일 가격 변동 수
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            week_price_changes = self.helper.client.table('price_history')\
                .select('*', count='exact')\
                .gte('changed_date', week_ago)\
                .execute()
                
            results['price_history'] = {
                'latest_change_date': latest_price.data[0]['changed_date'] if latest_price.data else None,
                'latest_change_article': latest_price.data[0]['article_no'] if latest_price.data else None,
                'latest_change_amount': latest_price.data[0]['change_amount'] if latest_price.data else 0,
                'total_changes': total_price_history.count,
                'week_changes': week_price_changes.count
            }
            
            print(f"💰 price_history 테이블:")
            print(f"   최신 변동일: {results['price_history']['latest_change_date']}")
            print(f"   최신 변동매물: {results['price_history']['latest_change_article']}")
            print(f"   최신 변동액: {results['price_history']['latest_change_amount']:,}만원")
            print(f"   총 변동레코드: {results['price_history']['total_changes']}개")
            print(f"   최근7일변동: {results['price_history']['week_changes']}개")
            
        except Exception as e:
            print(f"❌ price_history 테이블 조회 실패: {e}")
            results['price_history'] = {'error': str(e)}
        
        print()
        
        # 5. deletion_history 테이블
        try:
            # 최신 삭제일
            latest_deletion = self.helper.client.table('deletion_history')\
                .select('deleted_date, article_no, days_active')\
                .order('deleted_date', desc=True)\
                .limit(1)\
                .execute()
            
            # 총 삭제 레코드 수
            total_deletions = self.helper.client.table('deletion_history')\
                .select('*', count='exact')\
                .execute()
            
            # 최근 7일 삭제 수
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            week_deletions = self.helper.client.table('deletion_history')\
                .select('*', count='exact')\
                .gte('deleted_date', week_ago)\
                .execute()
                
            results['deletion_history'] = {
                'latest_deletion_date': latest_deletion.data[0]['deleted_date'] if latest_deletion.data else None,
                'latest_deletion_article': latest_deletion.data[0]['article_no'] if latest_deletion.data else None,
                'latest_deletion_days': latest_deletion.data[0]['days_active'] if latest_deletion.data else 0,
                'total_deletions': total_deletions.count,
                'week_deletions': week_deletions.count
            }
            
            print(f"🗑️ deletion_history 테이블:")
            print(f"   최신 삭제일: {results['deletion_history']['latest_deletion_date']}")
            print(f"   최신 삭제매물: {results['deletion_history']['latest_deletion_article']}")
            print(f"   최신 활성기간: {results['deletion_history']['latest_deletion_days']}일")
            print(f"   총 삭제레코드: {results['deletion_history']['total_deletions']}개")
            print(f"   최근7일삭제: {results['deletion_history']['week_deletions']}개")
            
        except Exception as e:
            print(f"❌ deletion_history 테이블 조회 실패: {e}")
            results['deletion_history'] = {'error': str(e)}
        
        return results
    
    def analyze_data_consistency(self, results):
        """데이터 정합성 분석"""
        print("\n" + "=" * 60)
        print("🔍 데이터 정합성 분석")
        print("=" * 60)
        
        issues = []
        
        # 오늘 날짜
        today = date.today()
        
        # 1. 수집 vs 통계 일관성 체크
        if 'properties' in results and 'daily_stats' in results:
            properties_latest = results['properties'].get('latest_collected_date')
            stats_latest = results['daily_stats'].get('latest_stat_date')
            
            if properties_latest and stats_latest:
                from datetime import datetime
                prop_date = datetime.fromisoformat(properties_latest).date()
                stat_date = datetime.fromisoformat(stats_latest).date()
                
                date_diff = (prop_date - stat_date).days
                
                if date_diff > 1:
                    issues.append(f"⚠️  매물 최신일({properties_latest})과 통계 최신일({stats_latest}) 차이: {date_diff}일")
                    issues.append(f"    → daily_stats 업데이트가 {date_diff}일 지연되고 있습니다!")
        
        # 2. 수집 로그 vs 실제 데이터 일관성 체크
        if 'collection_logs' in results and 'properties' in results:
            log_latest = results['collection_logs'].get('latest_completed_date')
            prop_latest = results['properties'].get('latest_collected_date')
            
            if log_latest and prop_latest:
                from datetime import datetime
                log_date = datetime.fromisoformat(log_latest[:10]).date() if 'T' in log_latest else datetime.fromisoformat(log_latest).date()
                prop_date = datetime.fromisoformat(prop_latest).date()
                
                date_diff = abs((log_date - prop_date).days)
                
                if date_diff > 1:
                    issues.append(f"⚠️  수집로그 완료일({log_latest[:10]})과 매물 최신일({prop_latest}) 차이: {date_diff}일")
        
        # 3. 최근 활동 체크
        if 'collection_logs' in results:
            today_logs = results['collection_logs'].get('today_logs', 0)
            week_completed = results['collection_logs'].get('week_completed', 0)
            
            if today_logs == 0:
                issues.append("⚠️  오늘 수집 로그가 없습니다.")
            
            if week_completed == 0:
                issues.append("⚠️  최근 7일간 완료된 수집이 없습니다!")
        
        # 4. 통계 업데이트 체크
        if 'daily_stats' in results:
            week_stats = results['daily_stats'].get('week_stats', 0)
            
            if week_stats == 0:
                issues.append("⚠️  최근 7일간 daily_stats 업데이트가 없습니다!")
        
        # 5. 매물 활성 상태 체크  
        if 'properties' in results:
            active_count = results['properties'].get('active_count', 0)
            total_count = results['properties'].get('total_count', 0)
            
            if total_count > 0:
                active_ratio = active_count / total_count * 100
                if active_ratio < 50:
                    issues.append(f"⚠️  활성 매물 비율이 {active_ratio:.1f}%로 낮습니다. (활성: {active_count:,}, 전체: {total_count:,})")
        
        # 결과 출력
        if issues:
            print("🚨 발견된 문제점들:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("✅ 데이터 정합성에 문제가 없습니다.")
        
        return issues
    
    def suggest_fixes(self, issues):
        """문제점에 대한 해결책 제안"""
        if not issues:
            return
        
        print("\n" + "=" * 60)
        print("💡 해결책 제안")
        print("=" * 60)
        
        for issue in issues:
            if "daily_stats" in issue and "지연" in issue:
                print("📈 daily_stats 업데이트 지연 해결책:")
                print("   1. save_daily_stats() 함수가 제대로 호출되고 있는지 확인")
                print("   2. 수집 완료 후 통계 생성 로직 점검")
                print("   3. 수동으로 누락된 날짜의 통계 생성 실행")
                print()
            
            if "오늘 수집 로그가 없습니다" in issue:
                print("📋 수집 로그 없음 해결책:")
                print("   1. 크론탭 설정 확인: crontab -l")
                print("   2. 수집기 프로세스 상태 확인")
                print("   3. 수동 수집 실행 테스트")
                print()
            
            if "최근 7일간 완료된 수집이 없습니다" in issue:
                print("🚨 수집 중단 해결책:")
                print("   1. 수집기 프로세스 재시작")
                print("   2. 네트워크 연결 및 API 키 확인")  
                print("   3. 에러 로그 확인 및 디버깅")
                print()
            
            if "활성 매물 비율" in issue:
                print("🏠 비활성 매물 정리 해결책:")
                print("   1. 오래된 매물 데이터 정리")
                print("   2. is_active 플래그 업데이트 로직 확인")
                print("   3. 매물 상태 갱신 프로세스 점검")
                print()

def main():
    """메인 실행 함수"""
    print("🔍 데이터베이스 테이블 정합성 체크 시작...")
    
    checker = DataIntegrityChecker()
    
    # 1. 최신 데이터 일자 조회
    results = checker.check_latest_data_dates()
    
    # 2. 정합성 분석
    issues = checker.analyze_data_consistency(results)
    
    # 3. 해결책 제안
    checker.suggest_fixes(issues)
    
    # 4. 결과 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"data_integrity_report_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'issues': issues
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 상세 결과가 {result_file}에 저장되었습니다.")

if __name__ == "__main__":
    main()