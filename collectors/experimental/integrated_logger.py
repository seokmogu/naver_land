#!/usr/bin/env python3
"""
통합 로그 시스템
- 기존 log_based_logger의 기능 유지
- enhanced_logger의 고급 기능 통합
- 호환성 보장하면서 향상된 디버깅 제공
"""

import json
import os
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any
import threading
import pytz
from supabase_client import SupabaseHelper
from enhanced_logger import EnhancedLogger, LogLevel, enhanced_logging


class IntegratedProgressTracker:
    """통합 진행 상황 추적기"""
    
    def __init__(self, log_dir: str = "./logs", log_level: LogLevel = LogLevel.INFO):
        self.log_dir = log_dir
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 향상된 로거 초기화
        self.enhanced_logger = EnhancedLogger(log_dir=log_dir, log_level=log_level)
        
        # 기존 호환성을 위한 로그 파일 경로들
        self.progress_log = os.path.join(log_dir, "live_progress.jsonl")
        self.collection_log = os.path.join(log_dir, "collection_data.jsonl")
        self.status_log = os.path.join(log_dir, "status.json")
        
        # 로그 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 진행 상황 업데이트 스레드
        self.progress_thread = None
        self.stop_progress_update = False
        
        self.enhanced_logger.info("integrated_tracker", "통합 로그 시스템 초기화 완료")
    
    def get_kst_now(self):
        """KST 현재 시간 반환"""
        return datetime.now(self.kst)
    
    def write_log(self, file_path: str, data: Dict[str, Any]):
        """JSON 로그 파일에 데이터 추가 (호환성)"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
                f.write('\n')
            
            # 향상된 로거에도 기록
            log_type = os.path.basename(file_path).replace('.jsonl', '').replace('.json', '')
            self.enhanced_logger.debug("file_write", f"파일 로그 기록: {log_type}", data)
            
        except Exception as e:
            self.enhanced_logger.error("file_write", f"로그 파일 쓰기 실패: {file_path}", e)
    
    def update_status_summary(self, task_id: str, status: str, details: Dict[str, Any]):
        """현재 상태 요약 파일 업데이트 (향상된 버전)"""
        status_data = {
            'task_id': task_id,
            'status': status,
            'details': details,
            'last_updated': self.get_kst_now().isoformat(),
            'timestamp': time.time()
        }
        
        try:
            # 기존 상태 파일 읽기
            current_status = {}
            if os.path.exists(self.status_log):
                try:
                    with open(self.status_log, 'r', encoding='utf-8') as f:
                        current_status = json.load(f)
                except Exception as e:
                    self.enhanced_logger.warn("status_update", f"기존 상태 파일 읽기 실패: {e}")
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
            
            # 향상된 로거에 기록
            self.enhanced_logger.debug("status_update", 
                                     f"상태 업데이트: {task_id} -> {status}",
                                     {'task_id': task_id, 'status': status})
            
        except Exception as e:
            self.enhanced_logger.error("status_update", f"상태 요약 업데이트 실패", e,
                                     {'task_id': task_id, 'status': status})
    
    def log_collection_data(self, task_id: str, data_type: str, data: Dict[str, Any]):
        """수집된 데이터 로그 기록 (향상된 버전)"""
        log_entry = {
            'timestamp': self.get_kst_now().isoformat(),
            'task_id': task_id,
            'type': data_type,
            'data': data
        }
        
        try:
            self.write_log(self.collection_log, log_entry)
            
            # 향상된 로거에 타입별로 적절한 로그 레벨로 기록
            if data_type == 'error':
                self.enhanced_logger.error("collection_data", f"수집 오류: {task_id}", 
                                         extra={'data_type': data_type, 'data': data})
            elif data_type == 'property':
                self.enhanced_logger.trace("collection_data", f"매물 수집: {data.get('article_no', 'unknown')}", 
                                         extra={'task_id': task_id, 'property': data})
            elif data_type == 'summary':
                self.enhanced_logger.info("collection_data", f"수집 요약: {task_id}", 
                                        extra={'summary': data})
            else:
                self.enhanced_logger.debug("collection_data", f"데이터 기록: {task_id} ({data_type})", 
                                         extra={'data': data})
        
        except Exception as e:
            self.enhanced_logger.error("collection_data", f"수집 데이터 로그 실패: {task_id}", e)
    
    def start_progress_updates(self, task_id: str, update_callback=None):
        """진행 상황 자동 업데이트 시작 (향상된 버전)"""
        def progress_updater():
            self.enhanced_logger.debug("progress_monitor", f"진행 상황 모니터링 시작: {task_id}")
            
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
                    self.update_status_summary(task_id, 'in_progress', progress_entry)
                    
                    # 성능 메트릭과 함께 기록
                    metrics = self.enhanced_logger.performance_monitor.get_current_metrics()
                    self.enhanced_logger.trace("progress_heartbeat", 
                                             f"진행 상황 업데이트: {task_id}",
                                             {'progress': progress_entry, 'metrics': metrics})
                    
                except Exception as e:
                    self.enhanced_logger.error("progress_monitor", f"진행 상황 업데이트 오류: {task_id}", e)
                
                time.sleep(10)  # 10초마다 업데이트
            
            self.enhanced_logger.debug("progress_monitor", f"진행 상황 모니터링 종료: {task_id}")
        
        self.progress_thread = threading.Thread(target=progress_updater, daemon=True)
        self.progress_thread.start()
    
    def stop_progress_updates(self):
        """진행 상황 업데이트 중지"""
        self.stop_progress_update = True
        if self.progress_thread:
            self.progress_thread.join(timeout=1)
        
        self.enhanced_logger.debug("progress_monitor", "진행 상황 업데이트 중지 완료")
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, duration: float, 
                     request_size: int = 0, response_size: int = 0, extra: Dict = None):
        """API 호출 로그 (새로운 기능)"""
        self.enhanced_logger.api_call(endpoint, method, status_code, duration, 
                                    request_size, response_size, extra)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보 (새로운 기능)"""
        return self.enhanced_logger.get_performance_summary()
    
    def close(self):
        """로그 시스템 종료"""
        self.stop_progress_updates()
        self.enhanced_logger.close()


@contextmanager
def integrated_log_based_collection(dong_name: str, cortar_no: str, 
                                   tracker: IntegratedProgressTracker):
    """통합 로그 기반 수집 컨텍스트 매니저"""
    task_id = f"{dong_name}_{int(time.time())}"
    helper = SupabaseHelper()
    log_id = None
    
    # 향상된 로깅으로 전체 컨텍스트 감싸기
    with enhanced_logging(f"collection_{dong_name}", tracker.enhanced_logger):
        try:
            # 1. DB에 시작 로그 기록
            start_data = {
                'gu_name': '강남구',
                'dong_name': dong_name,
                'cortar_no': cortar_no,
                'status': 'started',
                'started_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            tracker.enhanced_logger.info("db_operation", f"수집 시작 DB 기록: {dong_name}")
            
            result = helper.client.table('collection_logs').insert(start_data).execute()
            if result.data:
                log_id = result.data[0]['id']
                tracker.enhanced_logger.debug("db_operation", f"DB 로그 ID: {log_id}")
            
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
            
            tracker.enhanced_logger.info("collection_start", 
                                       f"{dong_name} 수집 시작 (Task ID: {task_id})",
                                       {'task_id': task_id, 'log_id': log_id})
            
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
                'log_summary': lambda summary: tracker.log_collection_data(task_id, 'summary', summary),
                'log_api_call': tracker.log_api_call,  # 새로운 기능 추가
                'enhanced_logger': tracker.enhanced_logger  # 직접 접근 가능
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
            
            tracker.enhanced_logger.info("collection_complete", 
                                       f"{dong_name} 수집 완료 - {collection_stats['total_collected']}개 매물",
                                       {'total_collected': collection_stats['total_collected']})
            
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
            
            tracker.enhanced_logger.error("collection_failed", f"{dong_name} 수집 실패", e,
                                        {'task_id': task_id, 'dong_name': dong_name})
            raise


# 호환성을 위한 별칭 및 래퍼
LogBasedProgressTracker = IntegratedProgressTracker
log_based_collection = integrated_log_based_collection


# 사용 예제
if __name__ == "__main__":
    # 통합 로그 시스템 테스트
    tracker = IntegratedProgressTracker(log_level=LogLevel.DEBUG)
    
    # 기존 방식으로도 사용 가능 (호환성)
    with log_based_collection("테스트동", "1234567890", tracker) as ctx:
        # 수집 작업 시뮬레이션
        for i in range(3):
            time.sleep(1)
            
            # 가상의 매물 데이터
            property_data = {
                'article_no': f'test_{i+1}',
                'title': f'테스트 매물 {i+1}',
                'price': f'{(i+1) * 50000}만원',
                'area': f'{20 + i*5}평'
            }
            
            # 기존 방식
            ctx['log_property'](property_data)
            
            # 새로운 API 호출 로그 기능
            ctx['log_api_call']('/api/test', 'GET', 200, 0.5)
            
            # 향상된 로거 직접 사용
            ctx['enhanced_logger'].debug("test", f"매물 {i+1} 처리 완료", 
                                       {'property': property_data})
            
            ctx['stats']['total_collected'] += 1
            ctx['stats']['last_property'] = property_data['title']
        
        # 수집 요약 로그
        ctx['log_summary']({
            'total_properties': ctx['stats']['total_collected'],
            'collection_time': '3초',
            'data_types': ['테스트']
        })
    
    # 성능 요약 출력
    summary = tracker.get_performance_summary()
    print("\n통합 로그 시스템 성능 요약:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    tracker.close()