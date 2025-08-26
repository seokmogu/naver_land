#!/usr/bin/env python3
"""
빠른 수집 상태 확인 도구
실시간 상황을 간단히 확인
"""

from datetime import datetime, timedelta
import pytz
from supabase_client import SupabaseHelper


def get_current_status():
    """현재 수집 상태 조회"""
    helper = SupabaseHelper()
    kst = pytz.timezone('Asia/Seoul')
    
    print("🔍 현재 수집 상태 확인 중... (KST 기준)")
    print("=" * 60)
    
    try:
        # 1. 진행 중인 수집 (최근 30분)
        since_time = datetime.now() - timedelta(minutes=30)
        active_result = helper.client.table('collection_logs')\
            .select('dong_name, status, started_at, error_message')\
            .in_('status', ['started', 'in_progress'])\
            .gte('created_at', since_time.isoformat())\
            .order('created_at', desc=True)\
            .execute()
        
        print(f"\n🔄 진행 중인 수집 ({len(active_result.data)}개)")
        print("-" * 70)
        print("     동명               상태           시작시간    경과시간")
        
        if not active_result.data:
            print("   현재 진행 중인 수집이 없습니다.")
        else:
            for i, log in enumerate(active_result.data, 1):
                dong_name = log.get('dong_name', 'N/A')
                status = log.get('status', 'N/A')
                started_at = log.get('started_at', '')
                error_message = log.get('error_message', '')
                
                # 시작 시간 및 경과 시간 계산 (KST)
                try:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    kst_start = start_time.astimezone(kst)
                    kst_now = datetime.now(kst)
                    duration = kst_now - kst_start
                    duration_str = f"{int(duration.total_seconds())}초"
                    
                    # 시작 시간 KST 포맷
                    start_time_str = kst_start.strftime('%m/%d %H:%M')
                except:
                    duration_str = "N/A"
                    start_time_str = "N/A"
                
                # 상태 아이콘
                icon = "🟡" if status == "started" else "🔵"
                
                print(f"   {i:2d}. {icon} {dong_name:15s} | {status:12s} | {start_time_str:8s} | {duration_str:10s}")
                
                # 진행 메시지
                if error_message and 'PROGRESS' in error_message:
                    progress = error_message.replace('PROGRESS: ', '').strip()
                    print(f"       💬 {progress}")
        
        # 2. 오늘의 요약 (KST 기준)
        kst_now = datetime.now(kst)
        kst_midnight = kst.localize(datetime.combine(kst_now.date(), datetime.min.time()))
        utc_midnight = kst_midnight.astimezone(pytz.UTC)
        
        today_result = helper.client.table('collection_logs')\
            .select('status, total_collected')\
            .gte('created_at', utc_midnight.isoformat())\
            .execute()
        
        summary = {'total': 0, 'completed': 0, 'failed': 0, 'in_progress': 0, 'total_items': 0}
        
        for log in today_result.data:
            summary['total'] += 1
            status = log['status']
            
            if status == 'completed':
                summary['completed'] += 1
                if log.get('total_collected'):
                    summary['total_items'] += log['total_collected']
            elif status in ['failed', 'timeout']:
                summary['failed'] += 1
            elif status in ['started', 'in_progress']:
                summary['in_progress'] += 1
        
        success_rate = (summary['completed'] / summary['total'] * 100) if summary['total'] > 0 else 0
        
        print(f"\n📊 오늘의 요약")
        print("-" * 60)
        print(f"   전체: {summary['total']:3d}개  |  완료: {summary['completed']:3d}개  |  실패: {summary['failed']:3d}개  |  진행중: {summary['in_progress']:3d}개")
        print(f"   성공률: {success_rate:5.1f}%  |  수집 매물: {summary['total_items']:,}개")
        
        # 3. 최근 완료/실패 (5개)
        recent_result = helper.client.table('collection_logs')\
            .select('dong_name, status, completed_at, total_collected')\
            .in_('status', ['completed', 'failed', 'timeout'])\
            .order('completed_at', desc=True)\
            .limit(5)\
            .execute()
        
        print(f"\n📋 최근 완료된 수집 ({len(recent_result.data)}개)")
        print("-" * 60)
        
        for i, log in enumerate(recent_result.data, 1):
            dong_name = log.get('dong_name', 'N/A')
            status = log.get('status', 'N/A')
            completed_at = log.get('completed_at', '')
            total_collected = log.get('total_collected', 0)
            
            # 완료 시간 (KST)
            try:
                completed_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                kst_time = completed_time.astimezone(kst)
                time_str = kst_time.strftime('%H:%M:%S')
            except:
                time_str = 'N/A'
            
            # 상태 아이콘
            icon = {"completed": "✅", "failed": "❌", "timeout": "⏰"}.get(status, "⚪")
            
            items_str = f"{total_collected}개" if total_collected else "0개"
            
            print(f"   {i:2d}. {icon} {dong_name:15s} | {time_str} | {items_str:8s} | {status}")
        
        print(f"\n🕐 업데이트 시간: {datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S KST')}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 상태 조회 실패: {e}")


if __name__ == "__main__":
    get_current_status()