#!/usr/bin/env python3
"""
실시간 경고 시스템
대량 삭제 감지시 즉시 중단 및 알림

사용법:
python alert_system.py [옵션]
    --monitor: 실시간 모니터링 모드 시작
    --check-interval: 체크 간격 (초, 기본: 300초/5분)
    --emergency-threshold: 긴급 중단 임계값 (기본: 100개)
"""

import time
import json
import argparse
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from supabase_client import SupabaseHelper

class AlertSystem:
    def __init__(self, emergency_threshold: int = 100):
        self.helper = SupabaseHelper()
        self.emergency_threshold = emergency_threshold
        self.alert_log_file = f"alert_log_{date.today().isoformat()}.json"
        self.last_check_time = None
        
    def start_monitoring(self, check_interval: int = 300):
        """실시간 모니터링 시작"""
        print("🚨 실시간 경고 시스템 시작")
        print("=" * 50)
        print(f"⏰ 체크 간격: {check_interval}초 ({check_interval//60}분)")
        print(f"🚨 긴급 임계값: {self.emergency_threshold}개")
        print(f"📝 로그 파일: {self.alert_log_file}")
        print("💡 Ctrl+C로 중단 가능")
        print("=" * 50)
        
        try:
            while True:
                current_time = datetime.now()
                print(f"\n🔍 [{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 시스템 체크 중...")
                
                # 1. 대량 삭제 감지
                deletion_alert = self.check_mass_deletion()
                
                # 2. 수집 중단 감지
                collection_alert = self.check_collection_halt()
                
                # 3. 데이터 품질 급락 감지
                quality_alert = self.check_quality_drop()
                
                # 4. 경고 처리
                self.handle_alerts([deletion_alert, collection_alert, quality_alert])
                
                # 5. 다음 체크까지 대기
                print(f"😴 다음 체크까지 {check_interval}초 대기...")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print(f"\n⚠️ 사용자에 의해 모니터링 중단됨")
            print(f"📊 최종 체크 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def check_mass_deletion(self) -> Dict:
        """대량 삭제 감지"""
        try:
            # 최근 1시간 내 삭제 수 확인
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            
            recent_deletions = self.helper.client.table('deletion_history')\
                .select('article_no, deleted_date')\
                .gte('deleted_date', one_hour_ago)\
                .execute()
            
            deletion_count = len(recent_deletions.data) if recent_deletions.data else 0
            
            alert = {
                'type': 'MASS_DELETION',
                'severity': 'LOW',
                'count': deletion_count,
                'threshold': self.emergency_threshold,
                'time_window': '1시간',
                'triggered': False,
                'message': ''
            }
            
            if deletion_count >= self.emergency_threshold:
                alert['severity'] = 'CRITICAL'
                alert['triggered'] = True
                alert['message'] = f"긴급! 최근 1시간 내 {deletion_count}개 매물 삭제 감지"
            elif deletion_count >= self.emergency_threshold // 2:
                alert['severity'] = 'WARNING'
                alert['triggered'] = True
                alert['message'] = f"주의! 최근 1시간 내 {deletion_count}개 매물 삭제"
            else:
                alert['message'] = f"정상: 최근 1시간 삭제 {deletion_count}개"
            
            if not alert['triggered']:
                print(f"  ✅ 대량 삭제: {alert['message']}")
            
            return alert
            
        except Exception as e:
            return {
                'type': 'MASS_DELETION',
                'severity': 'ERROR',
                'triggered': True,
                'message': f"대량 삭제 검사 오류: {e}",
                'error': str(e)
            }
    
    def check_collection_halt(self) -> Dict:
        """수집 중단 감지"""
        try:
            # 최근 6시간 내 수집 활동 확인
            six_hours_ago = (datetime.now() - timedelta(hours=6)).isoformat()
            
            recent_collections = self.helper.client.table('properties')\
                .select('collected_date')\
                .gte('collected_date', six_hours_ago[:10])\ # 날짜만 비교
                .execute()
            
            collection_count = len(recent_collections.data) if recent_collections.data else 0
            
            alert = {
                'type': 'COLLECTION_HALT',
                'severity': 'LOW',
                'count': collection_count,
                'time_window': '6시간',
                'triggered': False,
                'message': ''
            }
            
            if collection_count == 0:
                alert['severity'] = 'CRITICAL'
                alert['triggered'] = True
                alert['message'] = "긴급! 최근 6시간 내 수집 활동 없음"
            elif collection_count < 10:
                alert['severity'] = 'WARNING'
                alert['triggered'] = True
                alert['message'] = f"주의! 최근 6시간 수집량 부족: {collection_count}개"
            else:
                alert['message'] = f"정상: 최근 수집 {collection_count}개"
            
            if not alert['triggered']:
                print(f"  ✅ 수집 상태: {alert['message']}")
            
            return alert
            
        except Exception as e:
            return {
                'type': 'COLLECTION_HALT',
                'severity': 'ERROR',
                'triggered': True,
                'message': f"수집 상태 검사 오류: {e}",
                'error': str(e)
            }
    
    def check_quality_drop(self) -> Dict:
        """데이터 품질 급락 감지"""
        try:
            # 최근 1시간 내 수집된 매물의 품질 확인
            one_hour_ago = datetime.now() - timedelta(hours=1)
            today_str = date.today().isoformat()
            
            recent_properties = self.helper.client.table('properties')\
                .select('article_no, address_road, address_jibun, latitude, longitude, price')\
                .eq('collected_date', today_str)\
                .execute()
            
            if not recent_properties.data:
                return {
                    'type': 'QUALITY_DROP',
                    'severity': 'LOW',
                    'triggered': False,
                    'message': '품질 체크: 최근 데이터 없음'
                }
            
            total_count = len(recent_properties.data)
            missing_address = 0
            missing_coordinates = 0
            missing_price = 0
            
            for prop in recent_properties.data:
                if not prop.get('address_road') and not prop.get('address_jibun'):
                    missing_address += 1
                if not prop.get('latitude') or not prop.get('longitude'):
                    missing_coordinates += 1
                if not prop.get('price'):
                    missing_price += 1
            
            address_rate = (missing_address / total_count * 100) if total_count > 0 else 0
            coord_rate = (missing_coordinates / total_count * 100) if total_count > 0 else 0
            price_rate = (missing_price / total_count * 100) if total_count > 0 else 0
            
            alert = {
                'type': 'QUALITY_DROP',
                'severity': 'LOW',
                'total_count': total_count,
                'missing_rates': {
                    'address': address_rate,
                    'coordinates': coord_rate,
                    'price': price_rate
                },
                'triggered': False,
                'message': ''
            }
            
            # 품질 저하 임계값
            if address_rate >= 50 or coord_rate >= 50:
                alert['severity'] = 'CRITICAL'
                alert['triggered'] = True
                alert['message'] = f"긴급! 데이터 품질 급락 - 주소 누락: {address_rate:.1f}%, 좌표 누락: {coord_rate:.1f}%"
            elif address_rate >= 20 or coord_rate >= 20:
                alert['severity'] = 'WARNING'
                alert['triggered'] = True
                alert['message'] = f"주의! 데이터 품질 저하 - 주소 누락: {address_rate:.1f}%, 좌표 누락: {coord_rate:.1f}%"
            else:
                alert['message'] = f"정상: 품질 양호 (주소: {address_rate:.1f}%, 좌표: {coord_rate:.1f}% 누락)"
            
            if not alert['triggered']:
                print(f"  ✅ 데이터 품질: {alert['message']}")
            
            return alert
            
        except Exception as e:
            return {
                'type': 'QUALITY_DROP',
                'severity': 'ERROR',
                'triggered': True,
                'message': f"데이터 품질 검사 오류: {e}",
                'error': str(e)
            }
    
    def handle_alerts(self, alerts: List[Dict]):
        """경고 처리 및 대응"""
        triggered_alerts = [alert for alert in alerts if alert.get('triggered')]
        
        if not triggered_alerts:
            print(f"  🟢 모든 시스템 정상")
            return
        
        # 심각도별 분류
        critical_alerts = [a for a in triggered_alerts if a['severity'] == 'CRITICAL']
        warning_alerts = [a for a in triggered_alerts if a['severity'] == 'WARNING']
        error_alerts = [a for a in triggered_alerts if a['severity'] == 'ERROR']
        
        # 경고 출력
        print(f"\n🚨 경고 감지: {len(triggered_alerts)}개 알림")
        print("=" * 50)
        
        for alert in critical_alerts:
            print(f"🔴 [CRITICAL] {alert['message']}")
            
        for alert in warning_alerts:
            print(f"🟡 [WARNING] {alert['message']}")
            
        for alert in error_alerts:
            print(f"⚪ [ERROR] {alert['message']}")
        
        # 긴급 대응 조치
        if critical_alerts:
            print(f"\n🚨 긴급 대응 조치:")
            
            # 대량 삭제 감지시
            mass_deletion_alerts = [a for a in critical_alerts if a['type'] == 'MASS_DELETION']
            if mass_deletion_alerts:
                print(f"  1. json_to_supabase.py 프로세스 즉시 중단")
                print(f"  2. 긴급 데이터 복구 스크립트 실행:")
                print(f"     python emergency_data_recovery.py --dry-run")
                
                # 자동 중단 (프로세스 킬)
                self.emergency_stop_dangerous_processes()
            
            # 수집 중단 감지시
            halt_alerts = [a for a in critical_alerts if a['type'] == 'COLLECTION_HALT']
            if halt_alerts:
                print(f"  3. 수집기 프로세스 상태 점검")
                print(f"  4. 크론탭 및 스케줄러 상태 확인")
        
        # 알림 로그 저장
        self.save_alert_log(triggered_alerts)
    
    def emergency_stop_dangerous_processes(self):
        """위험한 프로세스 긴급 중단"""
        import subprocess
        import os
        import signal
        
        try:
            print(f"🛑 위험한 프로세스 검색 중...")
            
            # json_to_supabase.py 프로세스 찾기
            result = subprocess.run(['pgrep', '-f', 'json_to_supabase.py'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                print(f"🛑 json_to_supabase.py 프로세스 발견: {len(pids)}개")
                
                for pid in pids:
                    if pid.strip():
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"  ✅ PID {pid} 종료됨")
                        except ProcessLookupError:
                            print(f"  ⚠️ PID {pid} 이미 종료됨")
                        except Exception as e:
                            print(f"  ❌ PID {pid} 종료 실패: {e}")
            else:
                print(f"  ✅ json_to_supabase.py 프로세스 없음")
                
        except Exception as e:
            print(f"❌ 프로세스 중단 실패: {e}")
    
    def save_alert_log(self, alerts: List[Dict]):
        """알림 로그 저장"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'alerts': alerts,
                'alert_count': len(alerts),
                'critical_count': len([a for a in alerts if a['severity'] == 'CRITICAL']),
                'warning_count': len([a for a in alerts if a['severity'] == 'WARNING'])
            }
            
            # 기존 로그 읽기
            try:
                with open(self.alert_log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except FileNotFoundError:
                logs = []
            
            # 새 로그 추가
            logs.append(log_entry)
            
            # 최근 100개만 유지
            if len(logs) > 100:
                logs = logs[-100:]
            
            # 로그 저장
            with open(self.alert_log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 로그 저장 실패: {e}")
    
    def send_notification(self, alert: Dict):
        """알림 발송 (이메일, 슬랙 등)"""
        # TODO: 실제 알림 시스템 연동
        # 예: 이메일, 슬랙, 디스코드, 텔레그램 등
        pass
    
    def get_system_status(self) -> Dict:
        """현재 시스템 상태 조회"""
        try:
            # 간단한 상태 체크
            deletion_alert = self.check_mass_deletion()
            collection_alert = self.check_collection_halt()
            quality_alert = self.check_quality_drop()
            
            alerts = [deletion_alert, collection_alert, quality_alert]
            triggered_alerts = [a for a in alerts if a.get('triggered')]
            
            status = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'CRITICAL' if any(a['severity'] == 'CRITICAL' for a in triggered_alerts) else
                               'WARNING' if any(a['severity'] == 'WARNING' for a in triggered_alerts) else 'HEALTHY',
                'alerts': alerts,
                'triggered_count': len(triggered_alerts)
            }
            
            return status
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'ERROR',
                'error': str(e)
            }

def main():
    parser = argparse.ArgumentParser(description='실시간 경고 시스템')
    parser.add_argument('--monitor', action='store_true', help='실시간 모니터링 모드 시작')
    parser.add_argument('--check-interval', type=int, default=300, help='체크 간격 (초, 기본: 300초/5분)')
    parser.add_argument('--emergency-threshold', type=int, default=100, help='긴급 중단 임계값 (기본: 100개)')
    parser.add_argument('--status', action='store_true', help='현재 시스템 상태만 확인')
    
    args = parser.parse_args()
    
    # 경고 시스템 초기화
    alert_system = AlertSystem(emergency_threshold=args.emergency_threshold)
    
    if args.status:
        # 현재 상태만 확인
        print("📊 시스템 상태 체크")
        print("=" * 30)
        status = alert_system.get_system_status()
        
        status_icon = {
            'HEALTHY': '🟢',
            'WARNING': '🟡',
            'CRITICAL': '🔴',
            'ERROR': '⚪'
        }.get(status['overall_status'], '⚪')
        
        print(f"{status_icon} 전체 상태: {status['overall_status']}")
        print(f"⏰ 체크 시간: {status['timestamp']}")
        
        if status.get('triggered_count', 0) > 0:
            print(f"🚨 활성 경고: {status['triggered_count']}개")
    
    elif args.monitor:
        # 실시간 모니터링 시작
        alert_system.start_monitoring(check_interval=args.check_interval)
    else:
        # 단일 체크 실행
        print("🔍 시스템 단일 체크 실행")
        status = alert_system.get_system_status()
        
        print(f"📊 상태: {status['overall_status']}")
        if status.get('triggered_count', 0) > 0:
            triggered_alerts = [a for a in status['alerts'] if a.get('triggered')]
            alert_system.handle_alerts(triggered_alerts)

if __name__ == "__main__":
    main()