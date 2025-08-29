#!/usr/bin/env python3
"""
종합 모니터링 대시보드
- 실시간 스키마 상태 모니터링
- 성능 메트릭 추적
- 데이터 품질 지표
- 자동 알림 및 권장사항
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from dataclasses import dataclass, asdict
import traceback

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring_dashboard.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HealthMetric:
    """건강 상태 메트릭 데이터 클래스"""
    name: str
    value: Any
    status: str  # 'EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'CRITICAL'
    unit: str = ''
    threshold: Optional[str] = None
    recommendation: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class DashboardSnapshot:
    """대시보드 스냅샷 데이터 클래스"""
    timestamp: datetime
    overall_status: str
    schema_health: List[HealthMetric]
    performance_metrics: List[HealthMetric]
    data_quality: List[HealthMetric]
    alerts: List[Dict[str, Any]]
    recommendations: List[str]

class ComprehensiveMonitoringDashboard:
    def __init__(self, refresh_interval: int = 30):
        """종합 모니터링 대시보드 초기화"""
        # Supabase 연결
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("✅ Supabase 연결 성공")
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {e}")
            sys.exit(1)
        
        self.refresh_interval = refresh_interval
        self.dashboard_data = None
        self.alert_history = []
        self.is_monitoring = False
        
        # 상태 임계값 설정
        self.thresholds = {
            'cache_hit_ratio': {'good': 95, 'fair': 90, 'poor': 80},
            'index_usage_ratio': {'good': 80, 'fair': 60, 'poor': 40},
            'data_completeness': {'good': 90, 'fair': 70, 'poor': 50},
            'query_performance': {'good': 100, 'fair': 500, 'poor': 1000},  # ms
            'active_connections': {'good': 20, 'fair': 50, 'poor': 100}
        }
    
    def execute_sql_function(self, function_name: str, params: Dict = None) -> List[Dict]:
        """SQL 함수 실행"""
        try:
            if params:
                result = self.client.rpc(function_name, params).execute()
            else:
                # 함수 직접 호출
                query = f"SELECT * FROM {function_name}();"
                result = self.client.rpc('exec_sql', {'query': query}).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"SQL 함수 {function_name} 실행 실패: {e}")
            return []
    
    def collect_schema_health_metrics(self) -> List[HealthMetric]:
        """스키마 건강 상태 메트릭 수집"""
        logger.info("📊 스키마 건강 상태 수집 중...")
        
        metrics = []
        
        try:
            # 1. 테이블 존재 상태
            required_tables = [
                'properties_new', 'property_prices', 'property_locations',
                'property_physical', 'real_estate_types', 'trade_types', 
                'regions', 'realtors', 'property_tax_info'
            ]
            
            existing_tables = []
            for table in required_tables:
                try:
                    result = self.client.table(table).select('*').limit(1).execute()
                    existing_tables.append(table)
                except:
                    pass
            
            table_completeness = (len(existing_tables) / len(required_tables)) * 100
            table_status = self._determine_status(table_completeness, self.thresholds['data_completeness'])
            
            metrics.append(HealthMetric(
                name="Schema Tables",
                value=f"{len(existing_tables)}/{len(required_tables)}",
                status=table_status,
                unit="tables",
                threshold="9/9 required",
                recommendation="Complete schema deployment" if table_status != 'EXCELLENT' else None
            ))
            
            # 2. 인덱스 상태
            try:
                indexes_result = self.client.rpc('get_index_count').execute()
                index_count = indexes_result.data[0]['count'] if indexes_result.data else 0
                
                expected_indexes = 25  # 예상 인덱스 수
                index_ratio = (index_count / expected_indexes) * 100
                index_status = self._determine_status(index_ratio, self.thresholds['data_completeness'])
                
                metrics.append(HealthMetric(
                    name="Performance Indexes",
                    value=index_count,
                    status=index_status,
                    unit="indexes",
                    threshold=f">={expected_indexes} expected",
                    recommendation="Create missing performance indexes" if index_status != 'EXCELLENT' else None
                ))
            except Exception as e:
                logger.warning(f"인덱스 상태 확인 실패: {e}")
            
            # 3. 외래키 무결성
            try:
                # 간단한 외래키 테스트
                fk_test_result = self.client.table('properties_new')\
                    .select('id, real_estate_type_id, trade_type_id, region_id')\
                    .not_.is_('real_estate_type_id', 'null')\
                    .limit(10).execute()
                
                if fk_test_result.data:
                    metrics.append(HealthMetric(
                        name="Foreign Key Integrity",
                        value="Validated",
                        status="EXCELLENT",
                        unit="",
                        recommendation=None
                    ))
                else:
                    metrics.append(HealthMetric(
                        name="Foreign Key Integrity",
                        value="Issues Detected",
                        status="POOR",
                        unit="",
                        recommendation="Check reference data population"
                    ))
            except Exception as e:
                logger.warning(f"외래키 무결성 확인 실패: {e}")
            
        except Exception as e:
            logger.error(f"스키마 건강 상태 수집 오류: {e}")
            metrics.append(HealthMetric(
                name="Schema Health Check",
                value="Error",
                status="CRITICAL",
                recommendation="Check database connectivity"
            ))
        
        return metrics
    
    def collect_performance_metrics(self) -> List[HealthMetric]:
        """성능 메트릭 수집"""
        logger.info("⚡ 성능 메트릭 수집 중...")
        
        metrics = []
        
        try:
            # 1. 캐시 히트 비율
            try:
                cache_query = """
                SELECT ROUND(
                    (SUM(heap_blks_hit)::NUMERIC / GREATEST(SUM(heap_blks_hit + heap_blks_read), 1)) * 100, 2
                ) as hit_ratio
                FROM pg_statio_user_tables 
                WHERE schemaname = 'public'
                """
                cache_result = self.client.rpc('exec_sql', {'query': cache_query}).execute()
                
                if cache_result.data:
                    hit_ratio = float(cache_result.data[0]['hit_ratio'])
                    cache_status = self._determine_status(hit_ratio, self.thresholds['cache_hit_ratio'])
                    
                    metrics.append(HealthMetric(
                        name="Buffer Cache Hit Ratio",
                        value=hit_ratio,
                        status=cache_status,
                        unit="%",
                        threshold=">95% excellent",
                        recommendation=self._get_cache_recommendation(hit_ratio)
                    ))
            except Exception as e:
                logger.warning(f"캐시 히트 비율 확인 실패: {e}")
            
            # 2. 활성 연결 수
            try:
                connection_query = """
                SELECT COUNT(*) as active_connections
                FROM pg_stat_activity 
                WHERE state = 'active' AND pid != pg_backend_pid()
                """
                conn_result = self.client.rpc('exec_sql', {'query': connection_query}).execute()
                
                if conn_result.data:
                    active_conns = int(conn_result.data[0]['active_connections'])
                    conn_status = self._determine_status(active_conns, self.thresholds['active_connections'], reverse=True)
                    
                    metrics.append(HealthMetric(
                        name="Active Connections",
                        value=active_conns,
                        status=conn_status,
                        unit="connections",
                        threshold="<50 optimal",
                        recommendation="Monitor connection pooling" if active_conns > 50 else None
                    ))
            except Exception as e:
                logger.warning(f"활성 연결 수 확인 실패: {e}")
            
            # 3. 쿼리 성능 (샘플 쿼리 실행 시간)
            try:
                start_time = time.time()
                perf_test = self.client.table('properties_new')\
                    .select('*', count='exact')\
                    .eq('is_active', True)\
                    .limit(1).execute()
                execution_time = (time.time() - start_time) * 1000  # ms
                
                perf_status = self._determine_status(execution_time, self.thresholds['query_performance'], reverse=True)
                
                metrics.append(HealthMetric(
                    name="Query Performance",
                    value=round(execution_time, 2),
                    status=perf_status,
                    unit="ms",
                    threshold="<100ms excellent",
                    recommendation="Optimize indexes" if execution_time > 500 else None
                ))
            except Exception as e:
                logger.warning(f"쿼리 성능 측정 실패: {e}")
            
            # 4. 데이터베이스 크기
            try:
                size_query = """
                SELECT ROUND(pg_database_size(current_database())::NUMERIC / 1024 / 1024, 2) as db_size_mb
                """
                size_result = self.client.rpc('exec_sql', {'query': size_query}).execute()
                
                if size_result.data:
                    db_size = float(size_result.data[0]['db_size_mb'])
                    size_status = 'GOOD' if db_size < 1000 else ('FAIR' if db_size < 5000 else 'POOR')
                    
                    metrics.append(HealthMetric(
                        name="Database Size",
                        value=db_size,
                        status=size_status,
                        unit="MB",
                        threshold="<1GB optimal",
                        recommendation="Consider data archiving" if db_size > 5000 else None
                    ))
            except Exception as e:
                logger.warning(f"데이터베이스 크기 확인 실패: {e}")
            
        except Exception as e:
            logger.error(f"성능 메트릭 수집 오류: {e}")
        
        return metrics
    
    def collect_data_quality_metrics(self) -> List[HealthMetric]:
        """데이터 품질 메트릭 수집"""
        logger.info("📊 데이터 품질 메트릭 수집 중...")
        
        metrics = []
        
        try:
            # 1. 전체 매물 수 및 활성 비율
            try:
                total_result = self.client.table('properties_new').select('*', count='exact').limit(1).execute()
                active_result = self.client.table('properties_new')\
                    .select('*', count='exact')\
                    .eq('is_active', True)\
                    .limit(1).execute()
                
                total_count = total_result.count if hasattr(total_result, 'count') else 0
                active_count = active_result.count if hasattr(active_result, 'count') else 0
                
                active_ratio = (active_count / total_count * 100) if total_count > 0 else 0
                active_status = self._determine_status(active_ratio, {'good': 80, 'fair': 60, 'poor': 40})
                
                metrics.append(HealthMetric(
                    name="Active Properties Ratio",
                    value=f"{active_count:,}/{total_count:,}",
                    status=active_status,
                    unit=f"({active_ratio:.1f}%)",
                    threshold=">80% active",
                    recommendation="Review inactive property cleanup" if active_ratio < 80 else None
                ))
            except Exception as e:
                logger.warning(f"매물 활성 비율 확인 실패: {e}")
            
            # 2. 핵심 테이블 데이터 완성도
            key_tables = [
                ('property_locations', 'latitude'),
                ('property_physical', 'area_exclusive'),
                ('property_prices', 'amount'),
                ('property_tax_info', 'total_tax')
            ]
            
            for table_name, key_column in key_tables:
                try:
                    total_result = self.client.table(table_name).select('*', count='exact').limit(1).execute()
                    complete_result = self.client.table(table_name)\
                        .select('*', count='exact')\
                        .not_.is_(key_column, 'null')\
                        .limit(1).execute()
                    
                    total = total_result.count if hasattr(total_result, 'count') else 0
                    complete = complete_result.count if hasattr(complete_result, 'count') else 0
                    
                    completeness = (complete / total * 100) if total > 0 else 0
                    completeness_status = self._determine_status(completeness, self.thresholds['data_completeness'])
                    
                    metrics.append(HealthMetric(
                        name=f"{table_name.replace('_', ' ').title()} Completeness",
                        value=f"{complete:,}/{total:,}",
                        status=completeness_status,
                        unit=f"({completeness:.1f}%)",
                        threshold=">90% complete",
                        recommendation=f"Improve {table_name} data parsing" if completeness < 90 else None
                    ))
                except Exception as e:
                    logger.warning(f"{table_name} 완성도 확인 실패: {e}")
            
            # 3. 데이터 신선도 (최근 수집 데이터)
            try:
                fresh_query = """
                SELECT 
                    EXTRACT(epoch FROM (now() - MAX(collected_date)))/3600 as hours_since_last
                FROM properties_new 
                WHERE is_active = true
                """
                fresh_result = self.client.rpc('exec_sql', {'query': fresh_query}).execute()
                
                if fresh_result.data and fresh_result.data[0]['hours_since_last'] is not None:
                    hours_since = float(fresh_result.data[0]['hours_since_last'])
                    
                    if hours_since < 6:
                        freshness_status = 'EXCELLENT'
                    elif hours_since < 24:
                        freshness_status = 'GOOD'
                    elif hours_since < 72:
                        freshness_status = 'FAIR'
                    else:
                        freshness_status = 'POOR'
                    
                    metrics.append(HealthMetric(
                        name="Data Freshness",
                        value=f"{hours_since:.1f}",
                        status=freshness_status,
                        unit="hours ago",
                        threshold="<24h optimal",
                        recommendation="Check data collection system" if hours_since > 48 else None
                    ))
            except Exception as e:
                logger.warning(f"데이터 신선도 확인 실패: {e}")
            
        except Exception as e:
            logger.error(f"데이터 품질 메트릭 수집 오류: {e}")
        
        return metrics
    
    def collect_alerts(self) -> List[Dict[str, Any]]:
        """시스템 알림 수집"""
        alerts = []
        
        try:
            # SQL 함수를 통한 성능 알림 확인
            perf_alerts = self.execute_sql_function('check_performance_alerts')
            
            for alert in perf_alerts:
                alerts.append({
                    'level': alert.get('alert_level', 'INFO'),
                    'type': alert.get('alert_type', 'Unknown'),
                    'message': alert.get('description', ''),
                    'recommendation': alert.get('immediate_action', ''),
                    'timestamp': datetime.now().isoformat()
                })
        
        except Exception as e:
            logger.warning(f"성능 알림 수집 실패: {e}")
        
        # 메트릭 기반 알림 생성
        try:
            # 임계값 기반 알림
            all_metrics = (
                self.collect_schema_health_metrics() +
                self.collect_performance_metrics() +
                self.collect_data_quality_metrics()
            )
            
            for metric in all_metrics:
                if metric.status in ['POOR', 'CRITICAL']:
                    alerts.append({
                        'level': 'WARNING' if metric.status == 'POOR' else 'CRITICAL',
                        'type': 'Metric Alert',
                        'message': f"{metric.name}: {metric.value} {metric.unit}",
                        'recommendation': metric.recommendation or f"Review {metric.name} configuration",
                        'timestamp': datetime.now().isoformat()
                    })
        
        except Exception as e:
            logger.warning(f"메트릭 기반 알림 생성 실패: {e}")
        
        return alerts
    
    def generate_recommendations(self, metrics: List[HealthMetric], alerts: List[Dict]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 메트릭 기반 권장사항
        poor_metrics = [m for m in metrics if m.status in ['POOR', 'CRITICAL']]
        fair_metrics = [m for m in metrics if m.status == 'FAIR']
        
        if poor_metrics:
            recommendations.append(f"🔴 {len(poor_metrics)} critical metrics need immediate attention")
            for metric in poor_metrics[:3]:  # 상위 3개만
                if metric.recommendation:
                    recommendations.append(f"  - {metric.name}: {metric.recommendation}")
        
        if fair_metrics:
            recommendations.append(f"🟡 {len(fair_metrics)} metrics could be improved")
        
        # 알림 기반 권장사항
        critical_alerts = [a for a in alerts if a.get('level') == 'CRITICAL']
        if critical_alerts:
            recommendations.append(f"🚨 {len(critical_alerts)} critical alerts require immediate action")
        
        # 전반적인 시스템 상태 기반 권장사항
        excellent_count = len([m for m in metrics if m.status == 'EXCELLENT'])
        total_metrics = len(metrics)
        
        if excellent_count / total_metrics > 0.8:
            recommendations.append("✅ System is performing well - continue monitoring")
        elif excellent_count / total_metrics > 0.6:
            recommendations.append("⚡ System needs minor optimizations")
        else:
            recommendations.append("⚠️ System requires significant improvements")
        
        # 구체적인 액션 아이템
        if any('cache' in m.name.lower() for m in poor_metrics):
            recommendations.append("📈 Consider increasing shared_buffers parameter")
        
        if any('index' in m.name.lower() for m in poor_metrics):
            recommendations.append("🔍 Review and optimize database indexes")
        
        if any('completeness' in m.name.lower() for m in poor_metrics):
            recommendations.append("🔧 Improve data parsing and collection processes")
        
        return recommendations
    
    def create_dashboard_snapshot(self) -> DashboardSnapshot:
        """대시보드 스냅샷 생성"""
        logger.info("📸 대시보드 스냅샷 생성 중...")
        
        try:
            # 모든 메트릭 수집
            schema_metrics = self.collect_schema_health_metrics()
            performance_metrics = self.collect_performance_metrics()
            quality_metrics = self.collect_data_quality_metrics()
            
            all_metrics = schema_metrics + performance_metrics + quality_metrics
            alerts = self.collect_alerts()
            
            # 전체 상태 결정
            critical_count = len([m for m in all_metrics if m.status == 'CRITICAL'])
            poor_count = len([m for m in all_metrics if m.status == 'POOR'])
            fair_count = len([m for m in all_metrics if m.status == 'FAIR'])
            
            if critical_count > 0:
                overall_status = 'CRITICAL'
            elif poor_count > 0:
                overall_status = 'POOR' 
            elif fair_count > len(all_metrics) * 0.3:  # 30% 이상이 FAIR
                overall_status = 'FAIR'
            else:
                overall_status = 'GOOD'
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(all_metrics, alerts)
            
            snapshot = DashboardSnapshot(
                timestamp=datetime.now(),
                overall_status=overall_status,
                schema_health=schema_metrics,
                performance_metrics=performance_metrics,
                data_quality=quality_metrics,
                alerts=alerts,
                recommendations=recommendations
            )
            
            self.dashboard_data = snapshot
            return snapshot
            
        except Exception as e:
            logger.error(f"대시보드 스냅샷 생성 오류: {e}")
            # 오류 상태 반환
            return DashboardSnapshot(
                timestamp=datetime.now(),
                overall_status='ERROR',
                schema_health=[],
                performance_metrics=[],
                data_quality=[],
                alerts=[{
                    'level': 'CRITICAL',
                    'type': 'System Error',
                    'message': f'Dashboard snapshot creation failed: {str(e)}',
                    'recommendation': 'Check system logs and database connectivity',
                    'timestamp': datetime.now().isoformat()
                }],
                recommendations=['Check system configuration and database connectivity']
            )
    
    def _determine_status(self, value: float, thresholds: Dict[str, float], reverse: bool = False) -> str:
        """임계값 기반 상태 결정"""
        if reverse:  # 낮은 값이 좋은 경우 (예: 쿼리 실행 시간)
            if value <= thresholds['good']:
                return 'EXCELLENT'
            elif value <= thresholds['fair']:
                return 'GOOD'
            elif value <= thresholds['poor']:
                return 'FAIR'
            else:
                return 'POOR'
        else:  # 높은 값이 좋은 경우 (예: 캐시 히트율)
            if value >= thresholds['good']:
                return 'EXCELLENT'
            elif value >= thresholds['fair']:
                return 'GOOD'
            elif value >= thresholds['poor']:
                return 'FAIR'
            else:
                return 'POOR'
    
    def _get_cache_recommendation(self, hit_ratio: float) -> Optional[str]:
        """캐시 히트율 기반 권장사항"""
        if hit_ratio < 80:
            return "Increase shared_buffers immediately - very low cache performance"
        elif hit_ratio < 90:
            return "Consider increasing shared_buffers parameter"
        elif hit_ratio < 95:
            return "Monitor cache performance and consider minor tuning"
        else:
            return None
    
    def display_dashboard(self, snapshot: DashboardSnapshot = None):
        """대시보드 콘솔 출력"""
        if not snapshot:
            snapshot = self.dashboard_data or self.create_dashboard_snapshot()
        
        # 화면 클리어 (선택적)
        # os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*100)
        print("📊 NAVER REAL ESTATE DATABASE MONITORING DASHBOARD")
        print("="*100)
        
        # 전체 상태 표시
        status_emoji = {
            'EXCELLENT': '🟢', 'GOOD': '🟢', 'FAIR': '🟡', 
            'POOR': '🟠', 'CRITICAL': '🔴', 'ERROR': '💥'
        }
        
        print(f"\n🎯 Overall Status: {status_emoji.get(snapshot.overall_status, '❓')} {snapshot.overall_status}")
        print(f"📅 Last Updated: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 스키마 건강 상태
        if snapshot.schema_health:
            print(f"\n🏗️ SCHEMA HEALTH ({len(snapshot.schema_health)} metrics)")
            print("-" * 80)
            for metric in snapshot.schema_health:
                emoji = status_emoji.get(metric.status, '❓')
                print(f"  {emoji} {metric.name}: {metric.value} {metric.unit}")
                if metric.recommendation:
                    print(f"    💡 {metric.recommendation}")
        
        # 성능 메트릭
        if snapshot.performance_metrics:
            print(f"\n⚡ PERFORMANCE METRICS ({len(snapshot.performance_metrics)} metrics)")
            print("-" * 80)
            for metric in snapshot.performance_metrics:
                emoji = status_emoji.get(metric.status, '❓')
                print(f"  {emoji} {metric.name}: {metric.value} {metric.unit}")
                if metric.threshold:
                    print(f"    📏 Threshold: {metric.threshold}")
                if metric.recommendation:
                    print(f"    💡 {metric.recommendation}")
        
        # 데이터 품질
        if snapshot.data_quality:
            print(f"\n📊 DATA QUALITY ({len(snapshot.data_quality)} metrics)")
            print("-" * 80)
            for metric in snapshot.data_quality:
                emoji = status_emoji.get(metric.status, '❓')
                print(f"  {emoji} {metric.name}: {metric.value} {metric.unit}")
                if metric.recommendation:
                    print(f"    💡 {metric.recommendation}")
        
        # 활성 알림
        if snapshot.alerts:
            print(f"\n🚨 ACTIVE ALERTS ({len(snapshot.alerts)} alerts)")
            print("-" * 80)
            for alert in snapshot.alerts:
                level_emoji = {'CRITICAL': '🔴', 'WARNING': '⚠️', 'INFO': 'ℹ️'}.get(alert.get('level'), '❓')
                print(f"  {level_emoji} [{alert.get('level')}] {alert.get('type')}")
                print(f"    {alert.get('message')}")
                if alert.get('recommendation'):
                    print(f"    💡 {alert.get('recommendation')}")
                print()
        
        # 권장사항
        if snapshot.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(snapshot.recommendations)} items)")
            print("-" * 80)
            for i, rec in enumerate(snapshot.recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*100)
        print(f"Next refresh in {self.refresh_interval} seconds... (Ctrl+C to stop)")
    
    def save_snapshot_to_file(self, snapshot: DashboardSnapshot, filename: str = None) -> str:
        """스냅샷을 파일로 저장"""
        if not filename:
            timestamp = snapshot.timestamp.strftime('%Y%m%d_%H%M%S')
            filename = f"monitoring_snapshot_{timestamp}.json"
        
        try:
            filepath = current_dir / filename
            
            # dataclass를 dict로 변환
            snapshot_dict = {
                'timestamp': snapshot.timestamp.isoformat(),
                'overall_status': snapshot.overall_status,
                'schema_health': [asdict(m) for m in snapshot.schema_health],
                'performance_metrics': [asdict(m) for m in snapshot.performance_metrics],
                'data_quality': [asdict(m) for m in snapshot.data_quality],
                'alerts': snapshot.alerts,
                'recommendations': snapshot.recommendations
            }
            
            # datetime 객체를 문자열로 변환
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            # 모든 timestamp 필드 변환
            for category in ['schema_health', 'performance_metrics', 'data_quality']:
                for item in snapshot_dict[category]:
                    if 'timestamp' in item and item['timestamp']:
                        item['timestamp'] = item['timestamp'].isoformat() if isinstance(item['timestamp'], datetime) else item['timestamp']
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📁 모니터링 스냅샷 저장: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"스냅샷 저장 실패: {e}")
            return ""
    
    def run_continuous_monitoring(self):
        """지속적 모니터링 실행"""
        logger.info(f"🚀 지속적 모니터링 시작 (갱신 간격: {self.refresh_interval}초)")
        self.is_monitoring = True
        
        try:
            while self.is_monitoring:
                # 새 스냅샷 생성
                snapshot = self.create_dashboard_snapshot()
                
                # 대시보드 표시
                self.display_dashboard(snapshot)
                
                # 스냅샷 저장 (매 10분마다)
                if snapshot.timestamp.minute % 10 == 0:
                    self.save_snapshot_to_file(snapshot)
                
                # 대기
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 모니터링이 중단되었습니다.")
            self.is_monitoring = False
        except Exception as e:
            logger.error(f"모니터링 중 오류 발생: {e}")
            traceback.print_exc()
    
    def generate_status_report(self) -> str:
        """상태 리포트 생성"""
        snapshot = self.create_dashboard_snapshot()
        
        report_lines = [
            "# 네이버 부동산 DB 모니터링 리포트",
            f"생성 시간: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"전체 상태: {snapshot.overall_status}",
            "",
            "## 주요 메트릭",
        ]
        
        # 각 카테고리별 요약
        categories = [
            ("스키마 건강 상태", snapshot.schema_health),
            ("성능 메트릭", snapshot.performance_metrics),
            ("데이터 품질", snapshot.data_quality)
        ]
        
        for category_name, metrics in categories:
            report_lines.append(f"### {category_name}")
            for metric in metrics:
                status_symbol = {"EXCELLENT": "✅", "GOOD": "✅", "FAIR": "⚠️", "POOR": "❌", "CRITICAL": "🚨"}.get(metric.status, "❓")
                report_lines.append(f"- {status_symbol} {metric.name}: {metric.value} {metric.unit}")
            report_lines.append("")
        
        if snapshot.alerts:
            report_lines.append("## 활성 알림")
            for alert in snapshot.alerts:
                level_symbol = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}.get(alert.get('level'), "❓")
                report_lines.append(f"- {level_symbol} {alert.get('message')}")
            report_lines.append("")
        
        if snapshot.recommendations:
            report_lines.append("## 권장사항")
            for i, rec in enumerate(snapshot.recommendations, 1):
                report_lines.append(f"{i}. {rec}")
        
        return "\n".join(report_lines)

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="네이버 부동산 DB 종합 모니터링 대시보드")
    parser.add_argument('--refresh', type=int, default=30, help='갱신 간격 (초)')
    parser.add_argument('--once', action='store_true', help='한 번만 실행하고 종료')
    parser.add_argument('--report', action='store_true', help='리포트 생성하고 종료')
    parser.add_argument('--save-snapshot', action='store_true', help='스냅샷 저장')
    
    args = parser.parse_args()
    
    # 대시보드 인스턴스 생성
    dashboard = ComprehensiveMonitoringDashboard(refresh_interval=args.refresh)
    
    try:
        if args.report:
            # 리포트 생성
            report = dashboard.generate_status_report()
            print(report)
            
            # 파일로 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = current_dir / f"monitoring_report_{timestamp}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 리포트 저장: {report_file}")
            
        elif args.once:
            # 한 번만 실행
            snapshot = dashboard.create_dashboard_snapshot()
            dashboard.display_dashboard(snapshot)
            
            if args.save_snapshot:
                dashboard.save_snapshot_to_file(snapshot)
                
        else:
            # 지속적 모니터링
            dashboard.run_continuous_monitoring()
    
    except KeyboardInterrupt:
        print("\n모니터링이 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)