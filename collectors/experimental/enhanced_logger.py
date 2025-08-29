#!/usr/bin/env python3
"""
향상된 디버깅 로그 시스템
- 다중 레벨 로깅 (ERROR, WARN, INFO, DEBUG, TRACE)
- 구조화된 로그 포맷 (JSON + 사람 친화적)
- 실시간 성능 모니터링 및 메모리 추적
- 오류 패턴 분석 및 자동 복구 제안
- 로그 압축 및 자동 정리
"""

import json
import os
import time
import threading
import traceback
import psutil
import gc
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from enum import Enum
import pytz
from collections import defaultdict, deque
import gzip
import shutil


class LogLevel(Enum):
    """로그 레벨 정의"""
    ERROR = 1    # 오류 - 즉시 주의 필요
    WARN = 2     # 경고 - 모니터링 필요
    INFO = 3     # 정보 - 일반적인 진행 상황
    DEBUG = 4    # 디버그 - 상세한 실행 추적
    TRACE = 5    # 추적 - 매우 상세한 내부 동작


class PerformanceMonitor:
    """실시간 성능 모니터링"""
    
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()
        self.metrics_history = deque(maxlen=1000)  # 최근 1000개 메트릭만 보관
        self.api_call_stats = defaultdict(list)
        self.error_patterns = defaultdict(int)
        
    def get_current_metrics(self) -> Dict[str, Any]:
        """현재 시스템 메트릭 수집"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            # 메모리 사용량 (MB 단위)
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # 네트워크 통계 (가능한 경우)
            try:
                connections = len(self.process.connections())
            except:
                connections = 0
            
            metrics = {
                'timestamp': time.time(),
                'memory_mb': round(memory_mb, 2),
                'memory_percent': round(memory_percent, 2),
                'cpu_percent': round(cpu_percent, 2),
                'connections': connections,
                'uptime_seconds': round(time.time() - self.start_time, 2),
                'threads_count': threading.active_count()
            }
            
            # 메트릭 히스토리에 추가
            self.metrics_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            return {
                'timestamp': time.time(),
                'error': str(e),
                'memory_mb': 0,
                'cpu_percent': 0
            }
    
    def record_api_call(self, endpoint: str, duration: float, status_code: int):
        """API 호출 통계 기록"""
        self.api_call_stats[endpoint].append({
            'duration': duration,
            'status_code': status_code,
            'timestamp': time.time()
        })
        
        # 최근 100개 호출만 보관
        if len(self.api_call_stats[endpoint]) > 100:
            self.api_call_stats[endpoint] = self.api_call_stats[endpoint][-100:]
    
    def record_error_pattern(self, error_type: str, error_msg: str):
        """오류 패턴 기록"""
        pattern_key = f"{error_type}:{error_msg[:50]}"  # 오류 타입과 메시지 앞 50자
        self.error_patterns[pattern_key] += 1
    
    def get_api_stats(self) -> Dict[str, Any]:
        """API 호출 통계 반환"""
        stats = {}
        for endpoint, calls in self.api_call_stats.items():
            if calls:
                durations = [call['duration'] for call in calls]
                status_codes = [call['status_code'] for call in calls]
                
                stats[endpoint] = {
                    'total_calls': len(calls),
                    'avg_duration': round(sum(durations) / len(durations), 3),
                    'max_duration': round(max(durations), 3),
                    'min_duration': round(min(durations), 3),
                    'success_rate': round(sum(1 for code in status_codes if 200 <= code < 300) / len(status_codes) * 100, 2),
                    'recent_calls': len([call for call in calls if time.time() - call['timestamp'] < 300])  # 최근 5분
                }
        return stats
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """오류 패턴 분석"""
        if not self.error_patterns:
            return {}
        
        # 가장 빈번한 오류 패턴
        most_common = sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)
        
        analysis = {
            'total_errors': sum(self.error_patterns.values()),
            'unique_patterns': len(self.error_patterns),
            'most_common_errors': most_common[:5],
            'recommendations': self._generate_recommendations(most_common)
        }
        
        return analysis
    
    def _generate_recommendations(self, error_patterns: List) -> List[str]:
        """오류 패턴 기반 자동 복구 제안"""
        recommendations = []
        
        for pattern, count in error_patterns[:3]:  # 상위 3개 패턴만 분석
            error_type, error_msg = pattern.split(':', 1)
            
            if 'timeout' in error_msg.lower():
                recommendations.append(f"타임아웃 오류 {count}회 - API 호출 간격을 늘려보세요")
            elif 'memory' in error_msg.lower():
                recommendations.append(f"메모리 오류 {count}회 - 배치 크기를 줄이거나 가비지 컬렉션을 늘려보세요")
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                recommendations.append(f"인증 오류 {count}회 - 토큰 갱신 로직을 점검해보세요")
            elif 'connection' in error_msg.lower():
                recommendations.append(f"연결 오류 {count}회 - 네트워크 상태를 확인하거나 재시도 로직을 추가해보세요")
            else:
                recommendations.append(f"{error_type} 오류 {count}회 발생 - 로그를 자세히 확인해보세요")
        
        return recommendations


class EnhancedLogger:
    """향상된 로그 시스템"""
    
    def __init__(self, log_dir: str = "./logs", log_level: LogLevel = LogLevel.INFO):
        self.log_dir = log_dir
        self.log_level = log_level
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 로그 파일 경로들
        self.error_log = os.path.join(log_dir, "error.jsonl")
        self.debug_log = os.path.join(log_dir, "debug.jsonl")
        self.performance_log = os.path.join(log_dir, "performance.jsonl")
        self.api_log = os.path.join(log_dir, "api_calls.jsonl")
        self.human_readable_log = os.path.join(log_dir, "readable.log")
        
        # 로그 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 성능 모니터
        self.performance_monitor = PerformanceMonitor()
        
        # 자동 정리 스레드
        self.cleanup_thread = None
        self.stop_cleanup = False
        
        # 로그 압축 설정
        self.max_log_size_mb = 50  # 50MB 이상이면 압축
        self.max_compressed_days = 7  # 7일 이후 압축 파일 삭제
        
        self._start_performance_monitoring()
        self._start_auto_cleanup()
    
    def _start_performance_monitoring(self):
        """성능 모니터링 시작"""
        def monitor():
            while not self.stop_cleanup:
                try:
                    metrics = self.performance_monitor.get_current_metrics()
                    self._write_performance_log(metrics)
                    
                    # 메모리 사용량이 높으면 가비지 컬렉션 실행
                    if metrics.get('memory_percent', 0) > 80:
                        gc.collect()
                        self.warn("high_memory_usage", 
                                f"메모리 사용량 {metrics['memory_percent']}% - 가비지 컬렉션 실행")
                    
                except Exception as e:
                    self.error("performance_monitoring", f"성능 모니터링 오류: {e}")
                
                time.sleep(30)  # 30초마다 모니터링
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _start_auto_cleanup(self):
        """자동 로그 정리 시작"""
        def cleanup():
            while not self.stop_cleanup:
                try:
                    self._compress_old_logs()
                    self._delete_old_compressed_logs()
                except Exception as e:
                    self.error("log_cleanup", f"로그 정리 오류: {e}")
                
                time.sleep(3600)  # 1시간마다 정리
        
        self.cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        self.cleanup_thread.start()
    
    def _get_kst_now(self) -> datetime:
        """KST 현재 시간"""
        return datetime.now(self.kst)
    
    def _should_log(self, level: LogLevel) -> bool:
        """로그 레벨 확인"""
        return level.value <= self.log_level.value
    
    def _write_log(self, file_path: str, data: Dict[str, Any]):
        """JSON 로그 파일에 데이터 추가"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
                f.write('\n')
        except Exception as e:
            print(f"로그 쓰기 실패 ({file_path}): {e}")
    
    def _write_human_readable(self, level: str, component: str, message: str, extra: Dict = None):
        """사람이 읽기 쉬운 로그"""
        try:
            timestamp = self._get_kst_now().strftime('%Y-%m-%d %H:%M:%S')
            log_line = f"[{timestamp}] {level:5s} | {component:15s} | {message}"
            
            if extra:
                log_line += f" | {json.dumps(extra, ensure_ascii=False)}"
            
            with open(self.human_readable_log, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print(f"사람 친화적 로그 쓰기 실패: {e}")
    
    def _write_performance_log(self, metrics: Dict[str, Any]):
        """성능 로그 기록"""
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'type': 'performance',
            'metrics': metrics
        }
        self._write_log(self.performance_log, log_entry)
    
    def error(self, component: str, message: str, exception: Exception = None, extra: Dict = None):
        """오류 로그"""
        if not self._should_log(LogLevel.ERROR):
            return
        
        # 오류 패턴 기록
        error_type = exception.__class__.__name__ if exception else "GeneralError"
        self.performance_monitor.record_error_pattern(error_type, message)
        
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'level': 'ERROR',
            'component': component,
            'message': message,
            'extra': extra or {}
        }
        
        if exception:
            log_entry['exception'] = {
                'type': exception.__class__.__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }
        
        self._write_log(self.error_log, log_entry)
        self._write_human_readable('ERROR', component, message, extra)
        
        print(f"❌ ERROR [{component}] {message}")
    
    def warn(self, component: str, message: str, extra: Dict = None):
        """경고 로그"""
        if not self._should_log(LogLevel.WARN):
            return
        
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'level': 'WARN',
            'component': component,
            'message': message,
            'extra': extra or {}
        }
        
        self._write_log(self.debug_log, log_entry)
        self._write_human_readable('WARN', component, message, extra)
        
        print(f"⚠️ WARN [{component}] {message}")
    
    def info(self, component: str, message: str, extra: Dict = None):
        """정보 로그"""
        if not self._should_log(LogLevel.INFO):
            return
        
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'level': 'INFO',
            'component': component,
            'message': message,
            'extra': extra or {}
        }
        
        self._write_log(self.debug_log, log_entry)
        self._write_human_readable('INFO', component, message, extra)
        
        print(f"ℹ️ INFO [{component}] {message}")
    
    def debug(self, component: str, message: str, extra: Dict = None):
        """디버그 로그"""
        if not self._should_log(LogLevel.DEBUG):
            return
        
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'level': 'DEBUG',
            'component': component,
            'message': message,
            'extra': extra or {}
        }
        
        self._write_log(self.debug_log, log_entry)
        self._write_human_readable('DEBUG', component, message, extra)
    
    def trace(self, component: str, message: str, extra: Dict = None):
        """추적 로그"""
        if not self._should_log(LogLevel.TRACE):
            return
        
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'level': 'TRACE',
            'component': component,
            'message': message,
            'extra': extra or {}
        }
        
        self._write_log(self.debug_log, log_entry)
        self._write_human_readable('TRACE', component, message, extra)
    
    def api_call(self, endpoint: str, method: str, status_code: int, duration: float, 
                 request_size: int = 0, response_size: int = 0, extra: Dict = None):
        """API 호출 로그"""
        # 성능 모니터에 기록
        self.performance_monitor.record_api_call(endpoint, duration, status_code)
        
        log_entry = {
            'timestamp': self._get_kst_now().isoformat(),
            'type': 'api_call',
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_seconds': round(duration, 3),
            'request_size_bytes': request_size,
            'response_size_bytes': response_size,
            'extra': extra or {}
        }
        
        self._write_log(self.api_log, log_entry)
        
        # 상태 코드에 따른 로그 레벨 결정
        if status_code >= 500:
            self.error("api_call", f"{method} {endpoint} - {status_code} ({duration:.3f}s)", 
                      extra={'status_code': status_code, 'duration': duration})
        elif status_code >= 400:
            self.warn("api_call", f"{method} {endpoint} - {status_code} ({duration:.3f}s)", 
                     extra={'status_code': status_code, 'duration': duration})
        else:
            self.debug("api_call", f"{method} {endpoint} - {status_code} ({duration:.3f}s)", 
                      extra={'status_code': status_code, 'duration': duration})
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보"""
        current_metrics = self.performance_monitor.get_current_metrics()
        api_stats = self.performance_monitor.get_api_stats()
        error_analysis = self.performance_monitor.get_error_analysis()
        
        return {
            'current_metrics': current_metrics,
            'api_statistics': api_stats,
            'error_analysis': error_analysis,
            'log_files_status': self._get_log_files_status()
        }
    
    def _get_log_files_status(self) -> Dict[str, Any]:
        """로그 파일 상태 정보"""
        status = {}
        log_files = [
            self.error_log, self.debug_log, self.performance_log, 
            self.api_log, self.human_readable_log
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                stat = os.stat(log_file)
                status[os.path.basename(log_file)] = {
                    'size_mb': round(stat.st_size / 1024 / 1024, 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'lines': self._count_lines(log_file) if log_file.endswith('.log') else None
                }
            else:
                status[os.path.basename(log_file)] = {'exists': False}
        
        return status
    
    def _count_lines(self, file_path: str) -> int:
        """파일의 라인 수 계산"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def _compress_old_logs(self):
        """오래된 로그 파일 압축"""
        log_files = [
            self.error_log, self.debug_log, self.performance_log, self.api_log
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                size_mb = os.path.getsize(log_file) / 1024 / 1024
                
                if size_mb > self.max_log_size_mb:
                    compressed_name = f"{log_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.gz"
                    
                    try:
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(compressed_name, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # 원본 파일 삭제
                        os.remove(log_file)
                        
                        self.info("log_management", f"로그 파일 압축 완료: {compressed_name}")
                    except Exception as e:
                        self.error("log_management", f"로그 압축 실패: {e}")
    
    def _delete_old_compressed_logs(self):
        """오래된 압축 로그 파일 삭제"""
        cutoff_time = time.time() - (self.max_compressed_days * 24 * 3600)
        
        try:
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.gz'):
                    file_path = os.path.join(self.log_dir, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        self.info("log_management", f"오래된 압축 로그 삭제: {filename}")
        except Exception as e:
            self.error("log_management", f"압축 로그 정리 실패: {e}")
    
    def close(self):
        """로그 시스템 종료"""
        self.stop_cleanup = True
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=1)
        
        self.info("logger", "향상된 로그 시스템 종료")


@contextmanager
def enhanced_logging(component: str, logger: EnhancedLogger, 
                     log_start: bool = True, log_end: bool = True):
    """향상된 로깅 컨텍스트 매니저"""
    start_time = time.time()
    
    if log_start:
        logger.info(component, "작업 시작")
    
    try:
        yield logger
        
        if log_end:
            duration = time.time() - start_time
            logger.info(component, f"작업 완료 ({duration:.2f}초)", 
                       {'duration': duration, 'status': 'success'})
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(component, f"작업 실패 ({duration:.2f}초)", e, 
                    {'duration': duration, 'status': 'failed'})
        raise


# 글로벌 로거 인스턴스
_global_logger = None

def get_logger(log_level: LogLevel = LogLevel.INFO) -> EnhancedLogger:
    """글로벌 로거 인스턴스 반환"""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = EnhancedLogger(log_level=log_level)
    
    return _global_logger


# 사용 예제
if __name__ == "__main__":
    # 테스트 코드
    logger = EnhancedLogger(log_level=LogLevel.DEBUG)
    
    # 다양한 로그 레벨 테스트
    logger.info("test", "테스트 시작")
    logger.debug("test", "디버그 정보", {'step': 1, 'data': 'sample'})
    logger.warn("test", "경고 메시지", {'warning_type': 'memory'})
    
    # API 호출 로그 테스트
    logger.api_call("/api/articles", "GET", 200, 1.234, 1024, 5120)
    logger.api_call("/api/articles", "GET", 401, 0.456)
    
    # 예외 처리 테스트
    try:
        raise ValueError("테스트 오류")
    except Exception as e:
        logger.error("test", "테스트 오류 발생", e)
    
    # 컨텍스트 매니저 테스트
    with enhanced_logging("context_test", logger):
        time.sleep(1)
        logger.info("context_test", "컨텍스트 내부에서 실행")
    
    # 성능 요약 출력
    summary = logger.get_performance_summary()
    print("\n성능 요약:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    time.sleep(2)  # 성능 모니터링 확인
    
    logger.close()