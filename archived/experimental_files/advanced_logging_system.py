#!/usr/bin/env python3
"""
고도화된 로그 수집 및 분석 체계
- 구조화된 로깅 (JSON 형식)
- 로그 레벨별 분류
- 자동 로그 분석 및 인사이트
- 로그 기반 성능 최적화
- ELK 스택 연동 준비
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import gzip
import threading
from collections import defaultdict, Counter
from supabase_client import SupabaseHelper

@dataclass
class LogEntry:
    """구조화된 로그 엔트리"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    context: Dict[str, Any]
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None

class StructuredLogger:
    """구조화된 로거"""
    
    def __init__(self, name: str, session_id: str = None):
        self.name = name
        self.session_id = session_id or f"session_{int(datetime.now().timestamp())}"
        self.trace_id = None
        
        # 로그 파일 설정
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 일별 로그 파일
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = self.log_dir / f"collector_{today}.jsonl"
        self.error_log_file = self.log_dir / f"errors_{today}.jsonl"
        
        # 로그 버퍼 (배치 처리용)
        self.log_buffer = []
        self.buffer_lock = threading.Lock()
        self.buffer_size = 100
        
        # 기본 Python 로거도 설정 (호환성)
        self._setup_python_logger()
    
    def _setup_python_logger(self):
        """기본 Python 로거 설정"""
        self.python_logger = logging.getLogger(self.name)
        self.python_logger.setLevel(logging.DEBUG)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        if not self.python_logger.handlers:
            self.python_logger.addHandler(console_handler)
    
    def _create_log_entry(self, level: str, message: str, **context) -> LogEntry:
        """로그 엔트리 생성"""
        return LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            logger_name=self.name,
            message=message,
            context=context,
            session_id=self.session_id,
            trace_id=self.trace_id
        )
    
    def _write_log(self, entry: LogEntry):
        """로그 파일에 기록"""
        with self.buffer_lock:
            self.log_buffer.append(entry)
            
            # 버퍼가 가득 차면 플러시
            if len(self.log_buffer) >= self.buffer_size:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """버퍼를 파일에 플러시"""
        if not self.log_buffer:
            return
        
        # 일반 로그와 에러 로그 분리
        normal_logs = []
        error_logs = []
        
        for entry in self.log_buffer:
            if entry.level in ['ERROR', 'CRITICAL']:
                error_logs.append(entry)
            normal_logs.append(entry)
        
        # 파일에 기록
        if normal_logs:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                for entry in normal_logs:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + '\n')
        
        if error_logs:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                for entry in error_logs:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + '\n')
        
        self.log_buffer.clear()
    
    def info(self, message: str, **context):
        """정보 로그"""
        entry = self._create_log_entry('INFO', message, **context)
        self._write_log(entry)
        self.python_logger.info(message)
    
    def error(self, message: str, **context):
        """에러 로그"""
        entry = self._create_log_entry('ERROR', message, **context)
        self._write_log(entry)
        self.python_logger.error(message)
    
    def warning(self, message: str, **context):
        """경고 로그"""
        entry = self._create_log_entry('WARNING', message, **context)
        self._write_log(entry)
        self.python_logger.warning(message)
    
    def debug(self, message: str, **context):
        """디버그 로그"""
        entry = self._create_log_entry('DEBUG', message, **context)
        self._write_log(entry)
        self.python_logger.debug(message)
    
    def critical(self, message: str, **context):
        """중요 로그"""
        entry = self._create_log_entry('CRITICAL', message, **context)
        self._write_log(entry)
        self.python_logger.critical(message)
    
    def collection_start(self, cortar_no: str, max_pages: int):
        """수집 시작 로그"""
        self.info("Collection started", 
                 event_type="collection_start",
                 cortar_no=cortar_no,
                 max_pages=max_pages,
                 start_time=datetime.now().isoformat())
    
    def collection_page(self, cortar_no: str, page: int, properties_count: int):
        """페이지 수집 로그"""
        self.info("Page collected",
                 event_type="page_collected",
                 cortar_no=cortar_no,
                 page=page,
                 properties_count=properties_count)
    
    def collection_complete(self, cortar_no: str, total_collected: int, duration: float):
        """수집 완료 로그"""
        self.info("Collection completed",
                 event_type="collection_complete",
                 cortar_no=cortar_no,
                 total_collected=total_collected,
                 duration_seconds=duration,
                 collection_rate=total_collected/duration if duration > 0 else 0)
    
    def data_quality_check(self, total_records: int, quality_issues: Dict):
        """데이터 품질 체크 로그"""
        self.info("Data quality checked",
                 event_type="quality_check",
                 total_records=total_records,
                 quality_issues=quality_issues)
    
    def database_operation(self, operation: str, table: str, record_count: int, 
                          duration: float):
        """데이터베이스 작업 로그"""
        self.info("Database operation",
                 event_type="db_operation", 
                 operation=operation,
                 table=table,
                 record_count=record_count,
                 duration_seconds=duration)
    
    def performance_metric(self, metric_name: str, metric_value: float, unit: str):
        """성능 메트릭 로그"""
        self.info("Performance metric",
                 event_type="performance_metric",
                 metric_name=metric_name,
                 metric_value=metric_value,
                 unit=unit)
    
    def flush(self):
        """버퍼 강제 플러시"""
        with self.buffer_lock:
            self._flush_buffer()
    
    def __del__(self):
        """소멸자 - 버퍼 플러시"""
        try:
            self.flush()
        except:
            pass

class LogAnalyzer:
    """로그 분석기"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.helper = SupabaseHelper()
    
    def analyze_daily_logs(self, target_date: str = None) -> Dict:
        """일별 로그 분석"""
        if not target_date:
            target_date = datetime.now().strftime("%Y%m%d")
        
        print(f"📊 {target_date} 로그 분석 시작")
        
        log_file = self.log_dir / f"collector_{target_date}.jsonl"
        error_file = self.log_dir / f"errors_{target_date}.jsonl"
        
        analysis = {
            'date': target_date,
            'summary': {},
            'collection_performance': {},
            'error_analysis': {},
            'quality_metrics': {},
            'recommendations': []
        }
        
        # 기본 로그 분석
        if log_file.exists():
            analysis['summary'] = self._analyze_general_logs(log_file)
            analysis['collection_performance'] = self._analyze_collection_performance(log_file)
            analysis['quality_metrics'] = self._analyze_quality_metrics(log_file)
        
        # 에러 로그 분석  
        if error_file.exists():
            analysis['error_analysis'] = self._analyze_error_logs(error_file)
        
        # 권장사항 생성
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        self._print_analysis_report(analysis)
        return analysis
    
    def _analyze_general_logs(self, log_file: Path) -> Dict:
        """일반 로그 분석"""
        log_counts = defaultdict(int)
        event_types = defaultdict(int)
        sessions = set()
        loggers = defaultdict(int)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    log_counts[entry['level']] += 1
                    
                    if 'event_type' in entry['context']:
                        event_types[entry['context']['event_type']] += 1
                    
                    if entry['session_id']:
                        sessions.add(entry['session_id'])
                    
                    loggers[entry['logger_name']] += 1
                    
                except json.JSONDecodeError:
                    continue
        
        return {
            'total_logs': sum(log_counts.values()),
            'log_level_distribution': dict(log_counts),
            'event_type_distribution': dict(event_types),
            'session_count': len(sessions),
            'logger_distribution': dict(loggers)
        }
    
    def _analyze_collection_performance(self, log_file: Path) -> Dict:
        """수집 성능 분석"""
        collection_sessions = {}
        page_collections = []
        completion_times = []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    context = entry['context']
                    event_type = context.get('event_type')
                    
                    if event_type == 'collection_start':
                        session_id = entry['session_id']
                        collection_sessions[session_id] = {
                            'cortar_no': context.get('cortar_no'),
                            'start_time': entry['timestamp'],
                            'max_pages': context.get('max_pages')
                        }
                    
                    elif event_type == 'page_collected':
                        page_collections.append({
                            'properties_count': context.get('properties_count', 0),
                            'page': context.get('page', 0)
                        })
                    
                    elif event_type == 'collection_complete':
                        completion_times.append({
                            'duration': context.get('duration_seconds', 0),
                            'total_collected': context.get('total_collected', 0),
                            'collection_rate': context.get('collection_rate', 0)
                        })
                
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # 성능 메트릭 계산
        avg_collection_rate = 0
        avg_page_properties = 0
        
        if completion_times:
            avg_collection_rate = sum(c['collection_rate'] for c in completion_times) / len(completion_times)
        
        if page_collections:
            avg_page_properties = sum(p['properties_count'] for p in page_collections) / len(page_collections)
        
        return {
            'total_sessions': len(collection_sessions),
            'total_pages_collected': len(page_collections),
            'total_completions': len(completion_times),
            'avg_collection_rate': round(avg_collection_rate, 2),
            'avg_properties_per_page': round(avg_page_properties, 1),
            'completion_rate': (len(completion_times) / len(collection_sessions) * 100) if collection_sessions else 0
        }
    
    def _analyze_error_logs(self, error_file: Path) -> Dict:
        """에러 로그 분석"""
        error_types = defaultdict(int)
        error_messages = Counter()
        error_contexts = []
        
        with open(error_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    error_types[entry['level']] += 1
                    error_messages[entry['message']] += 1
                    
                    # 컨텍스트 정보 수집
                    if 'cortar_no' in entry['context']:
                        error_contexts.append({
                            'cortar_no': entry['context']['cortar_no'],
                            'message': entry['message'],
                            'timestamp': entry['timestamp']
                        })
                
                except json.JSONDecodeError:
                    continue
        
        # 가장 빈번한 에러들
        top_errors = error_messages.most_common(5)
        
        return {
            'total_errors': sum(error_types.values()),
            'error_level_distribution': dict(error_types),
            'top_error_messages': [{'message': msg, 'count': count} for msg, count in top_errors],
            'errors_by_region': self._group_errors_by_region(error_contexts)
        }
    
    def _group_errors_by_region(self, error_contexts: List[Dict]) -> Dict:
        """지역별 에러 그룹핑"""
        region_errors = defaultdict(int)
        for error in error_contexts:
            if error['cortar_no']:
                region_errors[error['cortar_no']] += 1
        
        return dict(region_errors)
    
    def _analyze_quality_metrics(self, log_file: Path) -> Dict:
        """품질 메트릭 분석"""
        quality_checks = []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    context = entry['context']
                    
                    if context.get('event_type') == 'quality_check':
                        quality_checks.append({
                            'total_records': context.get('total_records', 0),
                            'quality_issues': context.get('quality_issues', {})
                        })
                
                except (json.JSONDecodeError, KeyError):
                    continue
        
        if not quality_checks:
            return {}
        
        # 평균 품질 메트릭 계산
        total_records = sum(q['total_records'] for q in quality_checks)
        
        # 품질 이슈 집계
        aggregated_issues = defaultdict(int)
        for check in quality_checks:
            for issue_type, count in check['quality_issues'].items():
                aggregated_issues[issue_type] += count
        
        return {
            'total_quality_checks': len(quality_checks),
            'total_records_checked': total_records,
            'quality_issue_summary': dict(aggregated_issues),
            'avg_records_per_check': round(total_records / len(quality_checks), 1) if quality_checks else 0
        }
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """분석 결과 기반 권장사항 생성"""
        recommendations = []
        
        # 에러 분석 기반 권장사항
        error_analysis = analysis.get('error_analysis', {})
        if error_analysis.get('total_errors', 0) > 10:
            recommendations.append("🚨 에러 발생량이 높습니다. 주요 에러 패턴을 점검하세요.")
        
        # 성능 분석 기반 권장사항
        performance = analysis.get('collection_performance', {})
        completion_rate = performance.get('completion_rate', 0)
        if completion_rate < 90:
            recommendations.append(f"⚠️ 수집 완료율이 {completion_rate:.1f}%입니다. 안정성 개선이 필요합니다.")
        
        avg_rate = performance.get('avg_collection_rate', 0)
        if avg_rate < 5:
            recommendations.append(f"🐌 평균 수집 속도가 {avg_rate:.1f}건/초로 낮습니다. 성능 최적화를 고려하세요.")
        
        # 품질 분석 기반 권장사항
        quality = analysis.get('quality_metrics', {})
        quality_issues = quality.get('quality_issue_summary', {})
        if quality_issues:
            major_issue = max(quality_issues, key=quality_issues.get)
            recommendations.append(f"📊 {major_issue} 품질 이슈가 {quality_issues[major_issue]}건 발견되었습니다.")
        
        if not recommendations:
            recommendations.append("✅ 시스템이 정상적으로 운영되고 있습니다.")
        
        return recommendations
    
    def _print_analysis_report(self, analysis: Dict):
        """분석 보고서 출력"""
        print(f"\n📋 {analysis['date']} 로그 분석 보고서")
        print("=" * 60)
        
        # 요약 정보
        summary = analysis.get('summary', {})
        if summary:
            print(f"📊 로그 요약:")
            print(f"   총 로그: {summary.get('total_logs', 0):,}개")
            print(f"   세션수: {summary.get('session_count', 0)}개")
            
            level_dist = summary.get('log_level_distribution', {})
            for level, count in level_dist.items():
                print(f"   {level}: {count:,}개")
        
        # 수집 성능
        performance = analysis.get('collection_performance', {})
        if performance:
            print(f"\n⚡ 수집 성능:")
            print(f"   완료율: {performance.get('completion_rate', 0):.1f}%")
            print(f"   평균 수집속도: {performance.get('avg_collection_rate', 0):.2f}건/초")
            print(f"   페이지당 매물: {performance.get('avg_properties_per_page', 0):.1f}개")
        
        # 에러 분석
        error_analysis = analysis.get('error_analysis', {})
        if error_analysis and error_analysis.get('total_errors', 0) > 0:
            print(f"\n❌ 에러 분석:")
            print(f"   총 에러: {error_analysis.get('total_errors', 0)}개")
            
            top_errors = error_analysis.get('top_error_messages', [])
            if top_errors:
                print(f"   주요 에러:")
                for error in top_errors[:3]:
                    print(f"     • {error['message'][:50]}... ({error['count']}회)")
        
        # 권장사항
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\n💡 권장사항:")
            for rec in recommendations:
                print(f"   {rec}")
        
        print("=" * 60)
    
    def create_log_insights_dashboard(self, days: int = 7) -> Dict:
        """로그 인사이트 대시보드 데이터 생성"""
        print(f"📈 최근 {days}일 로그 인사이트 대시보드 생성")
        
        insights = {
            'period_days': days,
            'daily_summaries': [],
            'trends': {},
            'anomalies': [],
            'performance_insights': {}
        }
        
        # 일별 분석 수행
        for i in range(days):
            target_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            daily_analysis = self.analyze_daily_logs(target_date)
            
            # 요약 정보만 저장
            daily_summary = {
                'date': target_date,
                'total_logs': daily_analysis.get('summary', {}).get('total_logs', 0),
                'error_count': daily_analysis.get('error_analysis', {}).get('total_errors', 0),
                'collection_rate': daily_analysis.get('collection_performance', {}).get('avg_collection_rate', 0),
                'completion_rate': daily_analysis.get('collection_performance', {}).get('completion_rate', 0)
            }
            insights['daily_summaries'].append(daily_summary)
        
        # 트렌드 분석
        insights['trends'] = self._analyze_trends(insights['daily_summaries'])
        
        # 이상 징후 탐지
        insights['anomalies'] = self._detect_anomalies(insights['daily_summaries'])
        
        # 성능 인사이트
        insights['performance_insights'] = self._generate_performance_insights(insights['daily_summaries'])
        
        return insights
    
    def _analyze_trends(self, daily_summaries: List[Dict]) -> Dict:
        """트렌드 분석"""
        if len(daily_summaries) < 3:
            return {}
        
        # 최근 3일 vs 이전 기간 비교
        recent = daily_summaries[:3]
        previous = daily_summaries[3:6] if len(daily_summaries) >= 6 else daily_summaries[3:]
        
        if not previous:
            return {}
        
        recent_avg_rate = sum(d['collection_rate'] for d in recent) / len(recent)
        previous_avg_rate = sum(d['collection_rate'] for d in previous) / len(previous)
        
        rate_change = ((recent_avg_rate - previous_avg_rate) / previous_avg_rate * 100) if previous_avg_rate > 0 else 0
        
        recent_avg_errors = sum(d['error_count'] for d in recent) / len(recent)
        previous_avg_errors = sum(d['error_count'] for d in previous) / len(previous)
        
        error_change = ((recent_avg_errors - previous_avg_errors) / previous_avg_errors * 100) if previous_avg_errors > 0 else 0
        
        return {
            'collection_rate_change_percent': round(rate_change, 1),
            'error_rate_change_percent': round(error_change, 1),
            'trend_direction': 'improving' if rate_change > 5 and error_change < -10 else 'declining' if rate_change < -5 or error_change > 20 else 'stable'
        }
    
    def _detect_anomalies(self, daily_summaries: List[Dict]) -> List[Dict]:
        """이상 징후 탐지"""
        anomalies = []
        
        if len(daily_summaries) < 3:
            return anomalies
        
        # 에러 급증 감지
        error_counts = [d['error_count'] for d in daily_summaries]
        avg_errors = sum(error_counts) / len(error_counts)
        
        for i, summary in enumerate(daily_summaries):
            if summary['error_count'] > avg_errors * 3:  # 평균의 3배 이상
                anomalies.append({
                    'type': 'error_spike',
                    'date': summary['date'],
                    'value': summary['error_count'],
                    'threshold': avg_errors * 3,
                    'severity': 'high'
                })
        
        # 수집 성능 급락 감지
        collection_rates = [d['collection_rate'] for d in daily_summaries if d['collection_rate'] > 0]
        if collection_rates:
            avg_rate = sum(collection_rates) / len(collection_rates)
            
            for summary in daily_summaries:
                if summary['collection_rate'] < avg_rate * 0.5:  # 평균의 50% 미만
                    anomalies.append({
                        'type': 'performance_drop',
                        'date': summary['date'],
                        'value': summary['collection_rate'],
                        'threshold': avg_rate * 0.5,
                        'severity': 'medium'
                    })
        
        return anomalies
    
    def _generate_performance_insights(self, daily_summaries: List[Dict]) -> Dict:
        """성능 인사이트 생성"""
        if not daily_summaries:
            return {}
        
        # 최고/최저 성능일 찾기
        best_day = max(daily_summaries, key=lambda x: x['collection_rate'])
        worst_day = min(daily_summaries, key=lambda x: x['collection_rate']) if daily_summaries else best_day
        
        # 평균 성능
        avg_rate = sum(d['collection_rate'] for d in daily_summaries) / len(daily_summaries)
        avg_completion = sum(d['completion_rate'] for d in daily_summaries) / len(daily_summaries)
        
        return {
            'avg_collection_rate': round(avg_rate, 2),
            'avg_completion_rate': round(avg_completion, 1),
            'best_performance_date': best_day['date'],
            'best_performance_rate': best_day['collection_rate'],
            'worst_performance_date': worst_day['date'],
            'worst_performance_rate': worst_day['collection_rate'],
            'performance_consistency': self._calculate_consistency(daily_summaries)
        }
    
    def _calculate_consistency(self, daily_summaries: List[Dict]) -> str:
        """성능 일관성 계산"""
        rates = [d['collection_rate'] for d in daily_summaries if d['collection_rate'] > 0]
        if len(rates) < 2:
            return 'insufficient_data'
        
        avg = sum(rates) / len(rates)
        variance = sum((r - avg) ** 2 for r in rates) / len(rates)
        std_dev = variance ** 0.5
        
        cv = (std_dev / avg) * 100 if avg > 0 else 0  # 변동계수
        
        if cv < 20:
            return 'highly_consistent'
        elif cv < 40:
            return 'moderately_consistent'
        else:
            return 'inconsistent'

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='고도화된 로그 분석 시스템')
    parser.add_argument('--analyze', action='store_true', help='오늘 로그 분석')
    parser.add_argument('--date', type=str, help='분석할 날짜 (YYYYMMDD)')
    parser.add_argument('--dashboard', type=int, default=7, help='대시보드 기간 (일)')
    parser.add_argument('--compress-old', action='store_true', help='오래된 로그 압축')
    
    args = parser.parse_args()
    
    print("📊 고도화된 로그 분석 시스템 v2.0")
    print("=" * 50)
    
    analyzer = LogAnalyzer()
    
    if args.analyze:
        analysis = analyzer.analyze_daily_logs(args.date)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"log_analysis_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"📄 분석 결과 저장: {result_file}")
    
    elif args.dashboard:
        insights = analyzer.create_log_insights_dashboard(args.dashboard)
        
        # 대시보드 데이터 저장
        with open('log_insights_dashboard.json', 'w', encoding='utf-8') as f:
            json.dump(insights, f, ensure_ascii=False, indent=2)
        
        print("📊 대시보드 데이터 생성 완료: log_insights_dashboard.json")
    
    if args.compress_old:
        # 7일 이전 로그 압축
        log_dir = Path("logs")
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for log_file in log_dir.glob("*.jsonl"):
            # 파일명에서 날짜 추출
            try:
                file_date_str = log_file.stem.split('_')[-1]
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    # 압축
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                            f_out.writelines(f_in)
                    
                    # 원본 삭제
                    log_file.unlink()
                    print(f"📦 {log_file.name} 압축 완료")
            
            except (ValueError, IndexError):
                continue
        
        print("✅ 오래된 로그 압축 완료")

if __name__ == "__main__":
    main()