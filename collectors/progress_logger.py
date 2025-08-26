#!/usr/bin/env python3
"""
진행 상황 추적 로거 - 시작/진행중/종료 상태 모두 기록
"""

import os
import time
import threading
import multiprocessing as mp
from datetime import datetime
from typing import Dict, Optional
from contextlib import contextmanager
from supabase_client import SupabaseHelper


class ProgressLogger:
    def __init__(self):
        self.helper = SupabaseHelper()
        self.process_id = os.getpid()
        self.process_name = mp.current_process().name
        self._progress_thread = None
        self._stop_progress = False
        
    @contextmanager
    def log_collection(self, gu_name: str, dong_name: str, cortar_no: str, 
                      collection_type: str = "progress_collection"):
        """
        진행 상황 추적 컨텍스트 매니저
        시작 -> 진행중(주기적 업데이트) -> 종료
        """
        start_time = time.time()
        log_id = None
        
        try:
            # 1. 수집 시작 로그
            log_data = {
                'gu_name': gu_name,
                'dong_name': dong_name,
                'cortar_no': cortar_no,
                'collection_type': f"{collection_type}_{self.process_name}",
                'status': 'started',
                'started_at': datetime.now().isoformat()
            }
            
            result = self.helper.client.table('collection_logs').insert(log_data).execute()
            log_id = result.data[0]['id'] if result.data else None
            print(f"🚀 [{self.process_name}] {dong_name} 수집 시작 (로그 ID: {log_id})")
            
            # 2. 진행 상황 업데이트 스레드 시작
            self._stop_progress = False
            self._start_progress_thread(log_id, start_time, dong_name)
            
            # 3. 수집 프로세스 실행
            yield {
                'log_id': log_id,
                'start_time': start_time,
                'dong_name': dong_name,
                'cortar_no': cortar_no,
                'update_progress': lambda msg: self._update_progress_message(log_id, msg)
            }
            
        except Exception as e:
            # 4-a. 실패 시 처리
            self._stop_progress = True
            duration = time.time() - start_time
            
            error_summary = f"{type(e).__name__}: {str(e)}"
            if len(error_summary) > 500:
                error_summary = error_summary[:497] + "..."
            
            if log_id:
                try:
                    self.helper.client.table('collection_logs')\
                        .update({
                            'status': 'failed',
                            'completed_at': datetime.now().isoformat(),
                            'error_message': f"FAILED after {duration:.1f}s: {error_summary}"
                        })\
                        .eq('id', log_id)\
                        .execute()
                except Exception as update_e:
                    print(f"⚠️ 실패 로그 업데이트 실패: {update_e}")
            
            print(f"❌ [{self.process_name}] {dong_name} 수집 실패: {e}")
            raise
            
        else:
            # 4-b. 성공 시 처리
            self._stop_progress = True
            duration = time.time() - start_time
            
            if log_id:
                try:
                    self.helper.client.table('collection_logs')\
                        .update({
                            'status': 'completed',
                            'completed_at': datetime.now().isoformat(),
                            'error_message': f"SUCCESS: 완료, 소요시간 {duration:.1f}초"
                        })\
                        .eq('id', log_id)\
                        .execute()
                except Exception as update_e:
                    print(f"⚠️ 성공 로그 업데이트 실패: {update_e}")
            
            print(f"✅ [{self.process_name}] {dong_name} 수집 완료 (소요시간: {duration:.1f}초)")
        
        finally:
            # 진행 상황 스레드 종료
            self._stop_progress = True
            if self._progress_thread and self._progress_thread.is_alive():
                self._progress_thread.join(timeout=1)
    
    def _start_progress_thread(self, log_id: int, start_time: float, dong_name: str):
        """진행 상황 업데이트 스레드 시작"""
        def update_progress():
            update_count = 0
            while not self._stop_progress:
                time.sleep(30)  # 30초마다 업데이트
                if self._stop_progress:
                    break
                
                update_count += 1
                elapsed = time.time() - start_time
                
                try:
                    # 진행중 상태로 업데이트
                    self.helper.client.table('collection_logs')\
                        .update({
                            'status': 'in_progress',
                            'error_message': f"PROGRESS: {elapsed:.0f}초 경과, 업데이트 #{update_count}"
                        })\
                        .eq('id', log_id)\
                        .execute()
                    
                    print(f"🔄 [{self.process_name}] {dong_name} 진행 중... ({elapsed:.0f}초 경과)")
                    
                except Exception as e:
                    print(f"⚠️ 진행 상황 업데이트 실패: {e}")
        
        self._progress_thread = threading.Thread(target=update_progress, daemon=True)
        self._progress_thread.start()
    
    def _update_progress_message(self, log_id: int, message: str):
        """수동 진행 상황 업데이트"""
        try:
            self.helper.client.table('collection_logs')\
                .update({
                    'status': 'in_progress',
                    'error_message': f"PROGRESS: {message}"
                })\
                .eq('id', log_id)\
                .execute()
        except Exception as e:
            print(f"⚠️ 진행 메시지 업데이트 실패: {e}")
    
    def log_final_stats(self, log_id: int, collected_count: int, 
                       supabase_stats: Dict, duration: float):
        """최종 통계 저장"""
        try:
            stats_summary = f"SUCCESS: {collected_count}개 매물, {duration:.1f}초, 통계={supabase_stats}"
            if len(stats_summary) > 500:
                stats_summary = f"SUCCESS: {collected_count}개 매물, {duration:.1f}초"
            
            self.helper.client.table('collection_logs')\
                .update({
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'total_collected': collected_count,
                    'error_message': stats_summary
                })\
                .eq('id', log_id)\
                .execute()
                
            print(f"📊 [{self.process_name}] 최종 통계 저장: {collected_count}개 매물")
            
        except Exception as e:
            print(f"⚠️ 최종 통계 저장 실패: {e}")


def test_progress_logger():
    """진행 상황 로거 테스트"""
    logger = ProgressLogger()
    
    print("🧪 진행 상황 로거 테스트 시작...")
    
    try:
        with logger.log_collection("강남구", "테스트동", "TEST002", "progress_test") as log_context:
            print(f"📝 로그 컨텍스트: {log_context}")
            
            # 단계별 진행 상황 업데이트 테스트
            log_context['update_progress']("토큰 수집 중...")
            time.sleep(2)
            
            log_context['update_progress']("매물 데이터 수집 중...")
            time.sleep(3)
            
            log_context['update_progress']("DB 저장 중...")
            time.sleep(2)
            
            # 최종 통계 저장
            logger.log_final_stats(
                log_context['log_id'], 
                collected_count=150, 
                supabase_stats={'new': 80, 'updated': 50, 'removed': 20}, 
                duration=7.0
            )
            
    except Exception as e:
        print(f"테스트 중 오류: {e}")
    
    print("✅ 테스트 완료")


if __name__ == "__main__":
    test_progress_logger()