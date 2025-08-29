#!/usr/bin/env python3
"""
네이버 수집 라이브 모니터링 도구
실시간으로 수집 현황을 보여주는 CLI 대시보드
"""

import os
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from supabase_client import SupabaseHelper


class LiveCollectionMonitor:
    def __init__(self):
        self.helper = SupabaseHelper()
        self.running = True
        self.refresh_interval = 3  # 3초마다 업데이트
        self.kst = pytz.timezone('Asia/Seoul')
        
    def signal_handler(self, _, __):
        """Ctrl+C 처리"""
        print("\n\n🛑 모니터링 종료 중...")
        self.running = False
    
    def get_active_collections(self) -> List[Dict]:
        """현재 진행 중인 수집 작업들"""
        try:
            # 최근 30분 이내의 started, in_progress 상태 조회
            since_time = datetime.now() - timedelta(minutes=30)
            
            result = self.helper.client.table('collection_logs')\
                .select('*')\
                .in_('status', ['started', 'in_progress'])\
                .gte('created_at', since_time.isoformat())\
                .order('created_at', desc=True)\
                .execute()
            
            return result.data
            
        except Exception as e:
            print(f"❌ 활성 수집 조회 실패: {e}")
            return []
    
    def get_recent_completed(self, limit: int = 5) -> List[Dict]:
        """최근 완료된 수집들"""
        try:
            result = self.helper.client.table('collection_logs')\
                .select('*')\
                .in_('status', ['completed', 'failed', 'timeout'])\
                .order('completed_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data
            
        except Exception as e:
            print(f"❌ 완료된 수집 조회 실패: {e}")
            return []
    
    def get_today_summary(self) -> Dict:
        """오늘의 수집 요약 (KST 기준)"""
        try:
            # KST 기준 오늘 자정
            kst_now = datetime.now(self.kst)
            kst_midnight = self.kst.localize(datetime.combine(kst_now.date(), datetime.min.time()))
            utc_midnight = kst_midnight.astimezone(pytz.UTC)
            
            result = self.helper.client.table('collection_logs')\
                .select('status, total_collected')\
                .gte('created_at', utc_midnight.isoformat())\
                .execute()
            
            summary = {
                'total': len(result.data),
                'completed': 0,
                'failed': 0,
                'in_progress': 0,
                'total_items': 0
            }
            
            for log in result.data:
                status = log['status']
                if status == 'completed':
                    summary['completed'] += 1
                    if log.get('total_collected'):
                        summary['total_items'] += log['total_collected']
                elif status in ['failed', 'timeout']:
                    summary['failed'] += 1
                elif status in ['started', 'in_progress']:
                    summary['in_progress'] += 1
            
            return summary
            
        except Exception as e:
            print(f"❌ 오늘 요약 조회 실패: {e}")
            return {}
    
    def get_system_status(self) -> Dict:
        """시스템 상태 정보"""
        try:
            # CPU, 메모리 사용률 (psutil이 있다면)
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                return {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': f"{memory.available / (1024**3):.1f}GB",
                    'disk_percent': disk.percent,
                    'disk_free': f"{disk.free / (1024**3):.1f}GB"
                }
            except ImportError:
                # psutil이 없으면 기본 정보만
                return {
                    'cpu_percent': 0,
                    'memory_percent': 0,
                    'memory_available': "N/A",
                    'disk_percent': 0,
                    'disk_free': "N/A"
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def clear_screen(self):
        """화면 지우기"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def format_duration(self, start_time_str: str) -> str:
        """경과 시간 포맷팅"""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            # KST로 변환
            kst_start = start_time.astimezone(self.kst)
            kst_now = datetime.now(self.kst)
            duration = kst_now - kst_start
            
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}시간 {minutes}분 {seconds}초"
            elif minutes > 0:
                return f"{minutes}분 {seconds}초"
            else:
                return f"{seconds}초"
                
        except Exception:
            return "N/A"
    
    def print_header(self):
        """헤더 출력"""
        now = datetime.now(self.kst).strftime('%Y-%m-%d %H:%M:%S KST')
        print("🔴 LIVE" + " " * 45 + f"업데이트: {now}")
        print("=" * 80)
        print("         🚀 네이버 부동산 수집 라이브 모니터링 (KST)")
        print("=" * 80)
    
    def print_active_collections(self, active_collections: List[Dict]):
        """진행 중인 수집 출력"""
        print(f"\n📊 진행 중인 수집 ({len(active_collections)}개)")
        print("-" * 80)
        print("     동명          상태         시작시간     경과시간")
        
        if not active_collections:
            print("   현재 진행 중인 수집이 없습니다.")
        else:
            for i, log in enumerate(active_collections, 1):
                dong_name = log.get('dong_name', 'N/A')
                status = log.get('status', 'N/A')
                collection_type = log.get('collection_type', 'N/A')
                started_at = log.get('started_at', '')
                error_message = log.get('error_message', '')
                
                duration = self.format_duration(started_at)
                
                # 시작 시간 KST 포맷
                try:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    kst_start = start_time.astimezone(self.kst)
                    start_time_str = kst_start.strftime('%m/%d %H:%M')
                except:
                    start_time_str = "N/A"
                
                # 상태별 아이콘
                status_icon = {
                    'started': '🟡',
                    'in_progress': '🔵',
                    'completed': '🟢',
                    'failed': '🔴'
                }.get(status, '⚪')
                
                print(f"  {i:2d}. {status_icon} {dong_name:12s} | {status:12s} | {start_time_str:9s} | {duration:15s}")
                
                # 진행 메시지가 있으면 표시
                if error_message and 'PROGRESS' in error_message:
                    progress_msg = error_message.replace('PROGRESS: ', '').strip()
                    print(f"      💬 {progress_msg}")
                
                # 프로세스 정보
                if 'Process' in collection_type:
                    process_info = collection_type.split('_')[-1] if '_' in collection_type else 'N/A'
                    print(f"      🔧 프로세스: {process_info}")
    
    def print_recent_completed(self, recent_completed: List[Dict]):
        """최근 완료된 수집 출력"""
        print(f"\n📋 최근 완료된 수집 ({len(recent_completed)}개)")
        print("-" * 80)
        
        for i, log in enumerate(recent_completed, 1):
            dong_name = log.get('dong_name', 'N/A')
            status = log.get('status', 'N/A')
            completed_at = log.get('completed_at', '')
            total_collected = log.get('total_collected', 0)
            
            # 완료 시간 포맷팅 (KST)
            try:
                completed_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                kst_time = completed_time.astimezone(self.kst)
                time_str = kst_time.strftime('%H:%M:%S')
            except:
                time_str = 'N/A'
            
            # 상태별 아이콘
            status_icon = {
                'completed': '✅',
                'failed': '❌',
                'timeout': '⏰'
            }.get(status, '⚪')
            
            items_str = f"{total_collected}개" if total_collected else "0개"
            
            print(f"  {i:2d}. {status_icon} {dong_name:12s} | {time_str} | {items_str:8s} | {status}")
    
    def print_today_summary(self, summary: Dict):
        """오늘의 요약 출력"""
        print(f"\n📈 오늘의 수집 요약")
        print("-" * 80)
        
        total = summary.get('total', 0)
        completed = summary.get('completed', 0)
        failed = summary.get('failed', 0)
        in_progress = summary.get('in_progress', 0)
        total_items = summary.get('total_items', 0)
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        print(f"  📊 전체: {total:3d}개  |  ✅ 성공: {completed:3d}개  |  ❌ 실패: {failed:3d}개  |  🔵 진행중: {in_progress:3d}개")
        print(f"  🎯 성공률: {success_rate:5.1f}%  |  📦 총 수집: {total_items:,}개 매물")
    
    def print_system_status(self, system_info: Dict):
        """시스템 상태 출력"""
        print(f"\n💻 시스템 상태")
        print("-" * 80)
        
        if 'error' in system_info:
            print(f"  ⚠️ 시스템 정보 조회 실패: {system_info['error']}")
        else:
            cpu = system_info.get('cpu_percent', 0)
            memory = system_info.get('memory_percent', 0)
            memory_avail = system_info.get('memory_available', 'N/A')
            disk = system_info.get('disk_percent', 0)
            disk_free = system_info.get('disk_free', 'N/A')
            
            print(f"  🖥️  CPU: {cpu:5.1f}%  |  💾 메모리: {memory:5.1f}% (여유: {memory_avail})  |  💿 디스크: {disk:5.1f}% (여유: {disk_free})")
    
    def print_controls(self):
        """컨트롤 안내 출력"""
        print(f"\n🎮 컨트롤")
        print("-" * 80)
        print("  Ctrl+C: 종료  |  자동 새로고침: 3초마다")
    
    def run_monitor(self):
        """메인 모니터링 루프"""
        # Ctrl+C 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print("🚀 네이버 수집 라이브 모니터링 시작...")
        print("Ctrl+C를 눌러 종료하세요.\n")
        
        while self.running:
            try:
                # 데이터 수집
                active_collections = self.get_active_collections()
                recent_completed = self.get_recent_completed(5)
                today_summary = self.get_today_summary()
                system_info = self.get_system_status()
                
                # 화면 출력
                self.clear_screen()
                self.print_header()
                self.print_active_collections(active_collections)
                self.print_recent_completed(recent_completed)
                self.print_today_summary(today_summary)
                self.print_system_status(system_info)
                self.print_controls()
                
                # 다음 업데이트까지 대기
                time.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n❌ 모니터링 오류: {e}")
                time.sleep(5)
        
        print("\n✅ 라이브 모니터링 종료")


def main():
    """메인 함수"""
    monitor = LiveCollectionMonitor()
    monitor.run_monitor()


if __name__ == "__main__":
    main()