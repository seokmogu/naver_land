#!/usr/bin/env python3
"""
로그 기반 수집 진행 상황 추적기
- DB 업데이트 최소화 (시작/완료만)
- 실시간 진행 상황은 JSON 로그 파일에 기록
- 웹 대시보드가 로그 파일을 실시간으로 읽어서 표시
"""

import json
import os
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any, Optional
import threading
import pytz
from supabase_client import SupabaseHelper

class LogBasedProgressTracker:
    def __init__(self, log_dir: str = "/home/ubuntu/naver_land/logs"):
        self.log_dir = log_dir
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 로그 파일 경로들
        self.progress_log = os.path.join(log_dir, "live_progress.jsonl")  # 실시간 진행 상황
        self.collection_log = os.path.join(log_dir, "collection_data.jsonl")  # 수집된 데이터 로그
        self.status_log = os.path.join(log_dir, "status.json")  # 현재 상태 요약
        
        # 로그 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 진행 상황 업데이트 스레드
        self.progress_thread = None
        self.stop_progress_update = False
    
    def get_kst_now(self):
        """KST 현재 시간 반환"""
        return datetime.now(self.kst)
    
    def write_log(self, file_path: str, data: Dict[str, Any]):
        """JSON 로그 파일에 데이터 추가"""
        with open(file_path, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=str)
            f.write('\n')
    
    def update_status_summary(self, task_id: str, status: str, details: Dict[str, Any]):
        """현재 상태 요약 파일 업데이트"""
        status_data = {
            'task_id': task_id,
            'status': status,
            'details': details,
            'last_updated': self.get_kst_now().isoformat(),
            'timestamp': time.time()
        }
        
        # 기존 상태 파일 읽기
        current_status = {}
        if os.path.exists(self.status_log):
            try:
                with open(self.status_log, 'r', encoding='utf-8') as f:
                    current_status = json.load(f)
            except:
                current_status = {}
        
        # 상태 업데이트
        current_status[task_id] = status_data
        
        # 완료된 작업은 10분 후 정리
        cutoff_time = time.time() - 600  # 10분
        current_status = {
            k: v for k, v in current_status.items()
            if v.get('status') in ['started', 'in_progress'] or v.get('timestamp', 0) > cutoff_time
        }
        
        # 상태 파일 쓰기
        with open(self.status_log, 'w', encoding='utf-8') as f:
            json.dump(current_status, f, ensure_ascii=False, indent=2, default=str)
    
    def log_collection_data(self, task_id: str, data_type: str, data: Dict[str, Any]):
        """수집된 데이터 로그 기록"""
        log_entry = {
            'timestamp': self.get_kst_now().isoformat(),
            'task_id': task_id,
            'type': data_type,  # 'property', 'summary', 'error' 등
            'data': data
        }
        self.write_log(self.collection_log, log_entry)
    
    def start_progress_updates(self, task_id: str, update_callback=None):
        """진행 상황 자동 업데이트 시작"""
        def progress_updater():
            while not self.stop_progress_update:
                try:
                    # 진행 상황 로그 기록
                    progress_entry = {
                        'timestamp': self.get_kst_now().isoformat(),
                        'task_id': task_id,
                        'type': 'heartbeat',
                        'status': 'in_progress'
                    }
                    
                    if update_callback:
                        extra_info = update_callback()
                        if extra_info:
                            progress_entry.update(extra_info)
                    
                    self.write_log(self.progress_log, progress_entry)
                    
                    # 상태 요약 업데이트
                    self.update_status_summary(task_id, 'in_progress', progress_entry)
                    
                except Exception as e:
                    print(f"진행 상황 업데이트 오류: {e}")
                
                time.sleep(10)  # 10초마다 업데이트
        
        self.progress_thread = threading.Thread(target=progress_updater, daemon=True)
        self.progress_thread.start()
    
    def stop_progress_updates(self):
        """진행 상황 업데이트 중지"""
        self.stop_progress_update = True
        if self.progress_thread:
            self.progress_thread.join(timeout=1)

@contextmanager
def log_based_collection(dong_name: str, cortar_no: str, tracker: LogBasedProgressTracker):
    """로그 기반 수집 컨텍스트 매니저"""
    task_id = f"{dong_name}_{int(time.time())}"
    helper = SupabaseHelper()
    log_id = None
    
    try:
        # 1. DB에 시작 로그 기록
        start_data = {
            'gu_name': '강남구',  # 필수 컬럼 추가
            'dong_name': dong_name,
            'cortar_no': cortar_no,
            'status': 'started',
            'started_at': datetime.utcnow().isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = helper.client.table('collection_logs').insert(start_data).execute()
        if result.data:
            log_id = result.data[0]['id']
        
        # 2. 로그 파일에 시작 기록
        start_log = {
            'timestamp': tracker.get_kst_now().isoformat(),
            'task_id': task_id,
            'dong_name': dong_name,
            'cortar_no': cortar_no,
            'type': 'start',
            'status': 'started',
            'log_id': log_id
        }
        tracker.write_log(tracker.progress_log, start_log)
        tracker.update_status_summary(task_id, 'started', start_log)
        
        print(f"🚀 {dong_name} 수집 시작 (Task ID: {task_id})")
        
        # 3. 진행 상황 추적 시작
        collection_stats = {'total_collected': 0, 'last_property': None}
        
        def update_callback():
            return {
                'total_collected': collection_stats['total_collected'],
                'last_property': collection_stats['last_property']
            }
        
        tracker.start_progress_updates(task_id, update_callback)
        
        # 4. 수집 작업 실행을 위해 yield
        yield {
            'task_id': task_id,
            'log_id': log_id,
            'stats': collection_stats,
            'log_property': lambda prop: tracker.log_collection_data(task_id, 'property', prop),
            'log_summary': lambda summary: tracker.log_collection_data(task_id, 'summary', summary)
        }
        
        # 5. 성공 완료 처리
        tracker.stop_progress_updates()
        
        completion_log = {
            'timestamp': tracker.get_kst_now().isoformat(),
            'task_id': task_id,
            'dong_name': dong_name,
            'cortar_no': cortar_no,
            'type': 'complete',
            'status': 'completed',
            'total_collected': collection_stats['total_collected']
        }
        tracker.write_log(tracker.progress_log, completion_log)
        tracker.update_status_summary(task_id, 'completed', completion_log)
        
        # DB에 완료 상태 업데이트
        if log_id:
            helper.client.table('collection_logs').update({
                'status': 'completed',
                'completed_at': datetime.utcnow().isoformat(),
                'total_collected': collection_stats['total_collected']
            }).eq('id', log_id).execute()
        
        print(f"✅ {dong_name} 수집 완료 - {collection_stats['total_collected']}개 매물")
        
    except Exception as e:
        # 6. 실패 처리
        tracker.stop_progress_updates()
        
        error_log = {
            'timestamp': tracker.get_kst_now().isoformat(),
            'task_id': task_id,
            'dong_name': dong_name,
            'cortar_no': cortar_no,
            'type': 'error',
            'status': 'failed',
            'error': str(e)
        }
        tracker.write_log(tracker.progress_log, error_log)
        tracker.update_status_summary(task_id, 'failed', error_log)
        
        # DB에 실패 상태 업데이트
        if log_id:
            helper.client.table('collection_logs').update({
                'status': 'failed',
                'completed_at': datetime.utcnow().isoformat(),
                'error_message': str(e)
            }).eq('id', log_id).execute()
        
        print(f"❌ {dong_name} 수집 실패: {e}")
        raise

# 사용 예제
if __name__ == "__main__":
    # 로그 기반 추적기 초기화
    tracker = LogBasedProgressTracker()
    
    # 수집 시뮬레이션
    with log_based_collection("역삼동", "1168010100", tracker) as ctx:
        # 수집 작업 시뮬레이션
        for i in range(5):
            time.sleep(2)
            
            # 가상의 매물 데이터
            property_data = {
                'article_no': f'test_{i+1}',
                'title': f'테스트 매물 {i+1}',
                'price': f'{(i+1) * 50000}만원',
                'area': f'{20 + i*5}평'
            }
            
            # 매물 데이터 로그
            ctx['log_property'](property_data)
            ctx['stats']['total_collected'] += 1
            ctx['stats']['last_property'] = property_data['title']
            
            print(f"수집 중... {ctx['stats']['total_collected']}개 완료")
        
        # 수집 요약 로그
        ctx['log_summary']({
            'total_properties': ctx['stats']['total_collected'],
            'collection_time': '10초',
            'data_types': ['원룸', '투룸', '상가']
        })