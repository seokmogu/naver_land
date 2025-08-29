#!/usr/bin/env python3
"""
네이버 부동산 수집기 일일 건강성 체크 시스템

매일 데이터 품질, 수집 상태, 삭제 이상 징후를 체크하여
유사한 문제 재발 방지

사용법:
python daily_health_monitor.py [옵션]
    --alert-threshold: 대량 삭제 경고 임계값 (기본: 50개)
    --check-days: 검사할 과거 일수 (기본: 7일)
    --auto-fix: 자동 복구 모드 활성화
"""

import argparse
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from supabase_client import SupabaseHelper

class DailyHealthMonitor:
    def __init__(self, alert_threshold: int = 50):
        self.helper = SupabaseHelper()
        self.alert_threshold = alert_threshold
        self.health_score = 100.0  # 초기 건강도 점수
        
    def check_collection_health(self, check_days: int = 7) -> Dict:
        """수집 건강성 종합 체크"""
        print("🏥 네이버 부동산 수집기 건강성 체크 시작")
        print("=" * 60)
        
        health_report = {
            'check_date': date.today().isoformat(),
            'check_days': check_days,
            'overall_health': 'HEALTHY',
            'health_score': 100.0,
            'issues': [],
            'recommendations': [],
            'stats': {}
        }
        
        # 1. 대량 삭제 이상 징후 체크
        deletion_check = self.check_mass_deletion_anomaly(check_days)
        health_report['stats']['deletion_check'] = deletion_check
        
        # 2. 수집 빈도 및 일관성 체크
        collection_check = self.check_collection_consistency(check_days)
        health_report['stats']['collection_check'] = collection_check
        
        # 3. 데이터 품질 체크
        quality_check = self.check_data_quality(check_days)
        health_report['stats']['quality_check'] = quality_check
        
        # 4. 시스템 성능 체크
        performance_check = self.check_system_performance(check_days)
        health_report['stats']['performance_check'] = performance_check
        
        # 5. 종합 건강도 계산
        health_report = self.calculate_overall_health(health_report)
        
        # 6. 건강성 리포트 출력
        self.print_health_report(health_report)
        
        return health_report
    
    def check_mass_deletion_anomaly(self, days: int) -> Dict:
        """대량 삭제 이상 징후 검사"""
        print("🚨 대량 삭제 이상 징후 검사")
        
        try:
            # 최근 n일간 삭제 통계
            since_date = (date.today() - timedelta(days=days)).isoformat()
            
            deletion_stats = self.helper.client.table('deletion_history')\
                .select('deleted_date, article_no, deletion_reason')\
                .gte('deleted_date', since_date)\
                .execute()
            
            # 날짜별 삭제 수 집계
            daily_deletions = {}
            total_deletions = len(deletion_stats.data) if deletion_stats.data else 0
            
            for record in deletion_stats.data or []:
                del_date = record['deleted_date'][:10]
                daily_deletions[del_date] = daily_deletions.get(del_date, 0) + 1
            
            # 대량 삭제일 탐지
            anomaly_days = []
            for del_date, count in daily_deletions.items():
                if count >= self.alert_threshold:
                    anomaly_days.append({
                        'date': del_date,
                        'deletion_count': count,
                        'severity': 'CRITICAL' if count >= self.alert_threshold * 2 else 'WARNING'
                    })
            
            result = {
                'status': 'CRITICAL' if anomaly_days else 'HEALTHY',
                'total_deletions': total_deletions,
                'daily_deletions': daily_deletions,
                'anomaly_days': anomaly_days,
                'alert_threshold': self.alert_threshold,
                'avg_daily_deletions': total_deletions / days if days > 0 else 0
            }
            
            print(f"  📊 최근 {days}일간 총 삭제: {total_deletions}개")
            print(f"  📈 일평균 삭제: {result['avg_daily_deletions']:.1f}개")
            
            if anomaly_days:
                print(f"  🚨 대량 삭제 감지: {len(anomaly_days)}일")
                for anomaly in anomaly_days:
                    severity_icon = "🔴" if anomaly['severity'] == 'CRITICAL' else "🟡"
                    print(f"    {severity_icon} {anomaly['date']}: {anomaly['deletion_count']}개 삭제")
            else:
                print(f"  ✅ 정상: 대량 삭제 없음")
                
            return result
            
        except Exception as e:
            print(f"❌ 대량 삭제 검사 오류: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_collection_consistency(self, days: int) -> Dict:
        """수집 빈도 및 일관성 체크"""
        print("📊 수집 빈도 및 일관성 체크")
        
        try:
            since_date = (date.today() - timedelta(days=days)).isoformat()
            
            # daily_stats에서 수집 통계 확인
            stats_result = self.helper.client.table('daily_stats')\
                .select('stat_date, total_count, new_count, cortar_no')\
                .gte('stat_date', since_date)\
                .execute()
            
            daily_collections = {}
            area_coverage = set()
            total_collected = 0
            
            for record in stats_result.data or []:
                stat_date = record['stat_date']
                total_count = record.get('total_count', 0)
                cortar_no = record.get('cortar_no', '')
                
                daily_collections[stat_date] = daily_collections.get(stat_date, 0) + total_count
                area_coverage.add(cortar_no)
                total_collected += total_count
            
            # 수집 공백일 탐지
            missing_days = []
            current_date = date.today() - timedelta(days=days-1)
            
            for i in range(days):
                check_date = current_date + timedelta(days=i)
                if check_date.isoformat() not in daily_collections:
                    missing_days.append(check_date.isoformat())
            
            result = {
                'status': 'WARNING' if missing_days else 'HEALTHY',
                'total_collected': total_collected,
                'daily_collections': daily_collections,
                'area_coverage': len(area_coverage),
                'missing_days': missing_days,
                'avg_daily_collection': total_collected / days if days > 0 else 0
            }
            
            print(f"  📊 최근 {days}일간 총 수집: {total_collected}개")
            print(f"  📈 일평균 수집: {result['avg_daily_collection']:.1f}개")
            print(f"  🏘️ 커버리지: {len(area_coverage)}개 지역")
            
            if missing_days:
                print(f"  ⚠️ 수집 공백: {len(missing_days)}일")
                for missing_day in missing_days[:3]:  # 최대 3일만 표시
                    print(f"    - {missing_day}")
                if len(missing_days) > 3:
                    print(f"    ... 외 {len(missing_days)-3}일")
            else:
                print(f"  ✅ 정상: 연속 수집 유지")
                
            return result
            
        except Exception as e:
            print(f"❌ 수집 일관성 검사 오류: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_data_quality(self, days: int) -> Dict:
        """데이터 품질 체크"""
        print("🔍 데이터 품질 체크")
        
        try:
            since_date = (date.today() - timedelta(days=days)).isoformat()
            
            # 최근 수집된 매물 품질 검사
            recent_properties = self.helper.client.table('properties')\
                .select('article_no, article_name, price, address_road, address_jibun, latitude, longitude')\
                .gte('collected_date', since_date)\
                .eq('is_active', True)\
                .execute()
            
            total_properties = len(recent_properties.data) if recent_properties.data else 0
            quality_issues = {
                'missing_price': 0,
                'missing_address': 0,
                'missing_coordinates': 0,
                'missing_name': 0
            }
            
            for prop in recent_properties.data or []:
                if not prop.get('price'):
                    quality_issues['missing_price'] += 1
                if not prop.get('address_road') and not prop.get('address_jibun'):
                    quality_issues['missing_address'] += 1
                if not prop.get('latitude') or not prop.get('longitude'):
                    quality_issues['missing_coordinates'] += 1
                if not prop.get('article_name'):
                    quality_issues['missing_name'] += 1
            
            # 품질 점수 계산
            quality_score = 100.0
            if total_properties > 0:
                for issue, count in quality_issues.items():
                    quality_score -= (count / total_properties) * 20  # 각 이슈당 최대 20점 감점
            
            quality_score = max(0, quality_score)
            
            result = {
                'status': 'HEALTHY' if quality_score >= 80 else 'WARNING' if quality_score >= 60 else 'CRITICAL',
                'quality_score': quality_score,
                'total_properties': total_properties,
                'quality_issues': quality_issues,
                'issue_rates': {k: (v/total_properties*100 if total_properties > 0 else 0) for k, v in quality_issues.items()}
            }
            
            print(f"  📊 최근 {days}일 수집 매물: {total_properties}개")
            print(f"  🏆 품질 점수: {quality_score:.1f}/100")
            print(f"  📋 데이터 완성도:")
            print(f"    - 가격 누락: {result['issue_rates']['missing_price']:.1f}%")
            print(f"    - 주소 누락: {result['issue_rates']['missing_address']:.1f}%")
            print(f"    - 좌표 누락: {result['issue_rates']['missing_coordinates']:.1f}%")
            print(f"    - 매물명 누락: {result['issue_rates']['missing_name']:.1f}%")
            
            return result
            
        except Exception as e:
            print(f"❌ 데이터 품질 검사 오류: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_system_performance(self, days: int) -> Dict:
        """시스템 성능 체크"""
        print("⚡ 시스템 성능 체크")
        
        try:
            since_date = (date.today() - timedelta(days=days)).isoformat()
            
            # collection_logs에서 성능 데이터 확인 (있다면)
            # 여기서는 간단히 properties 테이블 업데이트 빈도로 성능 추정
            recent_updates = self.helper.client.table('properties')\
                .select('updated_at')\
                .gte('updated_at', since_date + 'T00:00:00')\
                .execute()
            
            update_count = len(recent_updates.data) if recent_updates.data else 0
            
            result = {
                'status': 'HEALTHY',
                'recent_updates': update_count,
                'avg_daily_updates': update_count / days if days > 0 else 0,
                'performance_score': min(100, update_count / 10)  # 간단한 성능 점수
            }
            
            print(f"  📊 최근 {days}일간 업데이트: {update_count}개")
            print(f"  📈 일평균 업데이트: {result['avg_daily_updates']:.1f}개")
            print(f"  ⚡ 성능 점수: {result['performance_score']:.1f}/100")
            
            return result
            
        except Exception as e:
            print(f"❌ 시스템 성능 검사 오류: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def calculate_overall_health(self, report: Dict) -> Dict:
        """종합 건강도 계산"""
        health_score = 100.0
        issues = []
        recommendations = []
        
        # 각 체크 결과에 따른 점수 조정
        checks = ['deletion_check', 'collection_check', 'quality_check', 'performance_check']
        
        for check_name in checks:
            check_result = report['stats'].get(check_name, {})
            status = check_result.get('status', 'UNKNOWN')
            
            if status == 'CRITICAL':
                health_score -= 30
                issues.append(f"{check_name}: 치명적 문제 발견")
            elif status == 'WARNING':
                health_score -= 15
                issues.append(f"{check_name}: 주의 필요")
            elif status == 'ERROR':
                health_score -= 20
                issues.append(f"{check_name}: 검사 오류")
        
        health_score = max(0, health_score)
        
        # 건강도에 따른 전체 상태 결정
        if health_score >= 80:
            overall_health = 'HEALTHY'
        elif health_score >= 60:
            overall_health = 'WARNING'
        else:
            overall_health = 'CRITICAL'
        
        # 권장사항 생성
        deletion_check = report['stats'].get('deletion_check', {})
        if deletion_check.get('anomaly_days'):
            recommendations.append("긴급 데이터 복구 스크립트 실행 검토")
            recommendations.append("삭제 로직 3일 유예 기간 적용 확인")
        
        quality_check = report['stats'].get('quality_check', {})
        if quality_check.get('quality_score', 100) < 80:
            recommendations.append("데이터 수집기 주소 변환 기능 점검")
            recommendations.append("카카오 API 키 및 호출 한도 확인")
        
        collection_check = report['stats'].get('collection_check', {})
        if collection_check.get('missing_days'):
            recommendations.append("크론탭 스케줄링 상태 확인")
            recommendations.append("수집 스크립트 오류 로그 점검")
        
        report['health_score'] = health_score
        report['overall_health'] = overall_health
        report['issues'] = issues
        report['recommendations'] = recommendations
        
        return report
    
    def print_health_report(self, report: Dict):
        """건강성 리포트 출력"""
        print("\n" + "="*60)
        print("🏥 종합 건강성 리포트")
        print("="*60)
        
        # 건강도 점수 및 상태
        health_score = report['health_score']
        status = report['overall_health']
        
        status_icon = {
            'HEALTHY': '🟢',
            'WARNING': '🟡', 
            'CRITICAL': '🔴'
        }.get(status, '⚪')
        
        print(f"{status_icon} 전체 건강도: {health_score:.1f}/100 ({status})")
        print(f"📅 검사일: {report['check_date']}")
        print(f"📊 검사 기간: 최근 {report['check_days']}일")
        
        # 발견된 문제들
        if report['issues']:
            print(f"\n🚨 발견된 문제 ({len(report['issues'])}개):")
            for i, issue in enumerate(report['issues'], 1):
                print(f"  {i}. {issue}")
        
        # 권장사항
        if report['recommendations']:
            print(f"\n💡 권장사항 ({len(report['recommendations'])}개):")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        # 건강도별 메시지
        if status == 'HEALTHY':
            print(f"\n✅ 수집기가 정상적으로 작동하고 있습니다!")
        elif status == 'WARNING':
            print(f"\n⚠️ 일부 문제가 발견되었습니다. 점검을 권장합니다.")
        else:
            print(f"\n🚨 심각한 문제가 발견되었습니다. 즉시 조치가 필요합니다!")
    
    def save_health_report(self, report: Dict):
        """건강성 리포트를 데이터베이스에 저장"""
        try:
            # health_reports 테이블에 저장 (테이블이 있다면)
            health_record = {
                'check_date': report['check_date'],
                'health_score': report['health_score'],
                'overall_health': report['overall_health'],
                'check_days': report['check_days'],
                'issues_count': len(report['issues']),
                'recommendations_count': len(report['recommendations']),
                'full_report': report,
                'created_at': datetime.now().isoformat()
            }
            
            # 실제 테이블이 없을 수 있으므로 try-catch로 처리
            self.helper.client.table('health_reports').insert(health_record).execute()
            print(f"💾 건강성 리포트 저장 완료")
            
        except Exception as e:
            print(f"⚠️ 건강성 리포트 저장 실패: {e}")
            # JSON 파일로 백업 저장
            import json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_report_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"📁 백업 파일로 저장: {filename}")

def main():
    parser = argparse.ArgumentParser(description='네이버 부동산 수집기 일일 건강성 체크')
    parser.add_argument('--alert-threshold', type=int, default=50, help='대량 삭제 경고 임계값 (기본: 50개)')
    parser.add_argument('--check-days', type=int, default=7, help='검사할 과거 일수 (기본: 7일)')
    parser.add_argument('--auto-fix', action='store_true', help='자동 복구 모드 활성화')
    parser.add_argument('--save-report', action='store_true', help='리포트를 DB에 저장')
    
    args = parser.parse_args()
    
    # 건강성 모니터 실행
    monitor = DailyHealthMonitor(alert_threshold=args.alert_threshold)
    health_report = monitor.check_collection_health(check_days=args.check_days)
    
    # 리포트 저장
    if args.save_report:
        monitor.save_health_report(health_report)
    
    # 자동 복구 (크리티컬한 문제가 있을 때)
    if args.auto_fix and health_report['overall_health'] == 'CRITICAL':
        print(f"\n🔧 자동 복구 모드 활성화")
        
        # 대량 삭제 문제가 있으면 복구 제안
        deletion_check = health_report['stats'].get('deletion_check', {})
        if deletion_check.get('anomaly_days'):
            print(f"💡 긴급 데이터 복구 스크립트 실행을 권장합니다:")
            print(f"   python emergency_data_recovery.py --dry-run")
    
    # 종료 코드 반환
    if health_report['overall_health'] == 'HEALTHY':
        exit(0)
    elif health_report['overall_health'] == 'WARNING':
        exit(1)
    else:
        exit(2)

if __name__ == "__main__":
    main()