#!/usr/bin/env python3
"""
향상된 수집 로거 - 컨텍스트 매니저 기반 로그 관리
프로세스 생명주기 추적, 상세 에러 정보, 성능 메트릭 수집
"""

import os
import time
import traceback
import multiprocessing as mp
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from contextlib import contextmanager
from supabase_client import SupabaseHelper


class EnhancedCollectionLogger:
    def __init__(self):
        self.helper = SupabaseHelper()
        self.process_id = os.getpid()
        self.process_name = mp.current_process().name
        
    @contextmanager
    def log_collection(self, gu_name: str, dong_name: str, cortar_no: str, 
                      collection_type: str = "enhanced_collection"):
        """
        컨텍스트 매니저로 수집 프로세스 로그 관리
        자동으로 시작/완료/실패 상태 업데이트
        """
        start_time = time.time()
        log_id = None
        
        try:
            # 1. 수집 시작 로그 (기존 스키마에 맞춰 JSON으로 확장 정보 저장)
            log_data = {
                'gu_name': gu_name,
                'dong_name': dong_name,
                'cortar_no': cortar_no,
                'collection_type': f"{collection_type}_{self.process_name}",
                'status': 'started',
                'started_at': datetime.now().isoformat(),
                'error_message': None,  # 기존 스키마 호환
                'total_collected': None  # 기존 스키마 호환
            }
            
            result = self.helper.client.table('collection_logs').insert(log_data).execute()
            log_id = result.data[0]['id'] if result.data else None
            print(f"🚀 [{self.process_name}] {dong_name} 수집 시작 (로그 ID: {log_id})")
            
            # 2. 수집 프로세스 실행 (yield로 제어 전달)
            yield {
                'log_id': log_id,
                'start_time': start_time,
                'dong_name': dong_name,
                'cortar_no': cortar_no
            }
            
        except Exception as e:
            # 3-a. 실패 시 상세 에러 정보 저장
            duration = time.time() - start_time
            error_info = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'stack_trace': traceback.format_exc(),
                'duration_seconds': round(duration, 2)
            }
            
            if log_id:
                self._update_log_status(log_id, 'failed', error_info)
            
            print(f"❌ [{self.process_name}] {dong_name} 수집 실패: {e}")
            raise
            
        else:
            # 3-b. 성공 시 완료 상태 업데이트
            duration = time.time() - start_time
            success_info = {
                'duration_seconds': round(duration, 2),
                'status': 'completed'
            }
            
            if log_id:
                self._update_log_status(log_id, 'completed', success_info)
            
            print(f"✅ [{self.process_name}] {dong_name} 수집 완료 (소요시간: {duration:.1f}초)")
    
    def _update_log_status(self, log_id: int, status: str, additional_info: Dict = None):
        """로그 상태 업데이트"""
        try:
            update_data = {
                'status': status,
                'completed_at': datetime.now().isoformat()
            }
            
            if additional_info:
                if 'error_type' in additional_info:
                    # 실패 정보
                    update_data.update({
                        'error_message': f"{additional_info['error_type']}: {additional_info['error_message']}",
                        'error_details': {
                            'stack_trace': additional_info.get('stack_trace'),
                            'duration_seconds': additional_info.get('duration_seconds'),
                            'process_id': self.process_id,
                            'process_name': self.process_name
                        }
                    })
                elif 'duration_seconds' in additional_info:
                    # 성공 정보
                    update_data['duration_seconds'] = additional_info['duration_seconds']
            
            self.helper.client.table('collection_logs')\
                .update(update_data)\
                .eq('id', log_id)\
                .execute()
                
        except Exception as e:
            print(f"⚠️ 로그 상태 업데이트 실패 (ID: {log_id}): {e}")
    
    def log_success_with_stats(self, log_id: int, collected_count: int, 
                              supabase_stats: Dict, duration: float):
        """성공한 수집의 상세 통계 저장"""
        try:
            stats_data = {
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'total_collected': collected_count,
                'duration_seconds': round(duration, 2),
                'collection_stats': {
                    'collected_count': collected_count,
                    'supabase_stats': supabase_stats,
                    'avg_processing_time': round(duration / max(collected_count, 1), 3),
                    'process_info': {
                        'process_id': self.process_id,
                        'process_name': self.process_name
                    }
                }
            }
            
            self.helper.client.table('collection_logs')\
                .update(stats_data)\
                .eq('id', log_id)\
                .execute()
                
            print(f"📊 [{self.process_name}] 통계 저장 완료: {collected_count}개 매물")
            
        except Exception as e:
            print(f"⚠️ 통계 저장 실패 (ID: {log_id}): {e}")
    
    @staticmethod
    def cleanup_orphaned_logs(max_age_hours: int = 2):
        """고아 프로세스 로그 정리"""
        helper = SupabaseHelper()
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            # 오래된 started 상태 로그 조회
            orphaned_logs = helper.client.table('collection_logs')\
                .select('id, dong_name, process_name, started_at')\
                .eq('status', 'started')\
                .lt('started_at', cutoff_time.isoformat())\
                .execute()
            
            if orphaned_logs.data:
                print(f"🧹 {len(orphaned_logs.data)}개 고아 로그 정리 시작...")
                
                for log in orphaned_logs.data:
                    # 타임아웃으로 실패 처리
                    helper.client.table('collection_logs')\
                        .update({
                            'status': 'timeout',
                            'completed_at': datetime.now().isoformat(),
                            'error_message': f'프로세스 타임아웃 ({max_age_hours}시간 초과)',
                            'error_details': {
                                'cleanup_reason': 'orphaned_process',
                                'max_age_hours': max_age_hours,
                                'original_started_at': log['started_at']
                            }
                        })\
                        .eq('id', log['id'])\
                        .execute()
                
                print(f"✅ 고아 로그 정리 완료: {len(orphaned_logs.data)}개")
            else:
                print("✨ 정리할 고아 로그가 없습니다")
                
        except Exception as e:
            print(f"❌ 고아 로그 정리 실패: {e}")
    
    @staticmethod
    def get_collection_summary(hours: int = 24) -> Dict:
        """지정된 시간 내 수집 요약 통계"""
        helper = SupabaseHelper()
        since_time = datetime.now() - timedelta(hours=hours)
        
        try:
            logs = helper.client.table('collection_logs')\
                .select('*')\
                .gte('created_at', since_time.isoformat())\
                .execute()
            
            summary = {
                'total_logs': len(logs.data),
                'status_distribution': {},
                'avg_duration': 0,
                'total_collected': 0,
                'error_patterns': {},
                'performance_stats': {
                    'fastest_collection': None,
                    'slowest_collection': None,
                    'avg_items_per_second': 0
                }
            }
            
            durations = []
            total_items = 0
            
            for log in logs.data:
                status = log['status']
                summary['status_distribution'][status] = summary['status_distribution'].get(status, 0) + 1
                
                if log.get('duration_seconds'):
                    durations.append(log['duration_seconds'])
                
                if log.get('total_collected'):
                    total_items += log['total_collected']
                    summary['total_collected'] += log['total_collected']
                
                if status == 'failed' and log.get('error_message'):
                    error_type = log['error_message'].split(':')[0]
                    summary['error_patterns'][error_type] = summary['error_patterns'].get(error_type, 0) + 1
            
            if durations:
                summary['avg_duration'] = round(sum(durations) / len(durations), 2)
                summary['performance_stats']['fastest_collection'] = min(durations)
                summary['performance_stats']['slowest_collection'] = max(durations)
                
                if total_items > 0:
                    summary['performance_stats']['avg_items_per_second'] = round(
                        total_items / sum(durations), 2
                    )
            
            return summary
            
        except Exception as e:
            print(f"❌ 요약 통계 생성 실패: {e}")
            return {}


def test_enhanced_logger():
    """향상된 로거 테스트"""
    logger = EnhancedCollectionLogger()
    
    print("🧪 향상된 로거 테스트 시작...")
    
    try:
        with logger.log_collection("강남구", "테스트동", "TEST001", "test_collection") as log_context:
            print(f"📝 로그 컨텍스트: {log_context}")
            time.sleep(1)  # 테스트 작업 시뮬레이션
            
            # 성공 통계 저장 테스트
            logger.log_success_with_stats(
                log_context['log_id'], 
                collected_count=100, 
                supabase_stats={'new': 50, 'updated': 30, 'removed': 20}, 
                duration=1.0
            )
            
    except Exception as e:
        print(f"테스트 중 오류: {e}")
    
    # 요약 통계 테스트
    print("\n📊 최근 24시간 수집 요약:")
    summary = EnhancedCollectionLogger.get_collection_summary(24)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("✅ 테스트 완료")


if __name__ == "__main__":
    test_enhanced_logger()