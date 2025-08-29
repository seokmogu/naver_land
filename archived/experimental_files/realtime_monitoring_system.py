#!/usr/bin/env python3
"""
실시간 모니터링 및 알림 시스템 v2.0
- 웹 대시보드 (Flask 기반)
- 실시간 메트릭 수집
- Slack/이메일 알림
- 성능 트렌드 분석
- 자동 복구 트리거
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, render_template_string, jsonify, request
from threading import Thread
import time
import requests
from supabase_client import SupabaseHelper

@dataclass
class SystemMetric:
    """시스템 메트릭"""
    timestamp: str
    metric_name: str
    metric_value: float
    unit: str
    status: str  # NORMAL, WARNING, CRITICAL
    details: Dict

@dataclass
class Alert:
    """알림 정보"""
    alert_id: str
    timestamp: str
    alert_type: str  # INFO, WARNING, CRITICAL
    title: str
    message: str
    source: str
    resolved: bool = False

class RealtimeMonitoringSystem:
    """실시간 모니터링 시스템"""
    
    def __init__(self):
        self.helper = SupabaseHelper()
        self.app = Flask(__name__)
        self.metrics_history = []
        self.active_alerts = []
        self.running = False
        
        # 임계값 설정
        self.thresholds = {
            'collection_rate_min': 10,      # 최소 수집 속도 (건/분)
            'error_rate_max': 5,            # 최대 오류율 (%)
            'memory_usage_max': 85,         # 최대 메모리 사용률 (%)
            'response_time_max': 30,        # 최대 응답 시간 (초)
            'duplicate_rate_max': 2,        # 최대 중복률 (%)
            'massive_deletion_threshold': 50 # 대량 삭제 임계값
        }
        
        # Slack 웹훅 설정 (환경변수에서 가져오기)
        self.slack_webhook = None  # 실제 사용시 환경변수로 설정
        
        # 웹 대시보드 라우트 설정
        self._setup_web_routes()
    
    def start_monitoring(self, check_interval: int = 60):
        """모니터링 시작"""
        print("🚀 실시간 모니터링 시스템 시작")
        print(f"⏱️ 체크 간격: {check_interval}초")
        print("🌐 웹 대시보드: http://localhost:5000")
        
        self.running = True
        
        # 백그라운드 모니터링 스레드 시작
        monitor_thread = Thread(target=self._monitoring_loop, args=(check_interval,))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 웹 서버 시작
        self.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    def _monitoring_loop(self, interval: int):
        """모니터링 루프"""
        while self.running:
            try:
                # 메트릭 수집
                current_metrics = self._collect_system_metrics()
                
                # 메트릭 저장
                self.metrics_history.extend(current_metrics)
                
                # 최근 1시간 데이터만 유지
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if datetime.fromisoformat(m.timestamp) > cutoff_time
                ]
                
                # 알림 체크
                self._check_alerts(current_metrics)
                
                # 로그 출력
                self._print_current_status(current_metrics)
                
            except Exception as e:
                print(f"❌ 모니터링 오류: {e}")
            
            time.sleep(interval)
    
    def _collect_system_metrics(self) -> List[SystemMetric]:
        """시스템 메트릭 수집"""
        metrics = []
        current_time = datetime.now().isoformat()
        
        try:
            # 1. 수집 성능 메트릭
            collection_metrics = self._get_collection_performance()
            metrics.extend(collection_metrics)
            
            # 2. 데이터 품질 메트릭
            quality_metrics = self._get_data_quality_metrics()
            metrics.extend(quality_metrics)
            
            # 3. 시스템 리소스 메트릭
            resource_metrics = self._get_system_resource_metrics()
            metrics.extend(resource_metrics)
            
            # 4. 데이터베이스 메트릭
            db_metrics = self._get_database_metrics()
            metrics.extend(db_metrics)
            
        except Exception as e:
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="monitoring_error",
                metric_value=1,
                unit="count",
                status="CRITICAL",
                details={"error": str(e)}
            ))
        
        return metrics
    
    def _get_collection_performance(self) -> List[SystemMetric]:
        """수집 성능 메트릭"""
        metrics = []
        current_time = datetime.now().isoformat()
        
        try:
            # 최근 10분간 수집량
            ten_min_ago = datetime.now() - timedelta(minutes=10)
            
            recent_logs = self.helper.client.table('collection_logs')\
                .select('total_collected, status, created_at')\
                .gte('created_at', ten_min_ago.isoformat())\
                .execute()
            
            total_collected = sum(log.get('total_collected', 0) for log in recent_logs.data or [])
            total_attempts = len(recent_logs.data) if recent_logs.data else 0
            successful = sum(1 for log in recent_logs.data or [] if log.get('status') == 'completed')
            
            # 수집 속도 (건/분)
            collection_rate = total_collected / 10 if total_collected > 0 else 0
            status = "NORMAL" if collection_rate >= self.thresholds['collection_rate_min'] else "WARNING"
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="collection_rate",
                metric_value=collection_rate,
                unit="items/min", 
                status=status,
                details={
                    "total_collected": total_collected,
                    "period_minutes": 10
                }
            ))
            
            # 성공률
            success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
            success_status = "NORMAL" if success_rate >= 90 else "WARNING" if success_rate >= 70 else "CRITICAL"
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="success_rate",
                metric_value=success_rate,
                unit="percent",
                status=success_status,
                details={
                    "successful": successful,
                    "total_attempts": total_attempts
                }
            ))
            
        except Exception as e:
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="collection_performance_error",
                metric_value=0,
                unit="count",
                status="WARNING",
                details={"error": str(e)}
            ))
        
        return metrics
    
    def _get_data_quality_metrics(self) -> List[SystemMetric]:
        """데이터 품질 메트릭"""
        metrics = []
        current_time = datetime.now().isoformat()
        
        try:
            # 오늘 수집된 데이터의 품질
            today = datetime.now().date().isoformat()
            
            today_data = self.helper.client.table('properties')\
                .select('price, address_road, latitude, longitude')\
                .gte('collected_date', today)\
                .eq('is_active', True)\
                .execute()
            
            total = len(today_data.data) if today_data.data else 0
            
            if total > 0:
                missing_price = sum(1 for p in today_data.data if not p.get('price'))
                missing_address = sum(1 for p in today_data.data if not p.get('address_road'))
                missing_coords = sum(1 for p in today_data.data 
                                   if not p.get('latitude') or not p.get('longitude'))
                
                # 데이터 완성도
                completeness = ((total - missing_price - missing_address - missing_coords) / (total * 3)) * 100
                completeness_status = "NORMAL" if completeness >= 90 else "WARNING" if completeness >= 70 else "CRITICAL"
                
                metrics.append(SystemMetric(
                    timestamp=current_time,
                    metric_name="data_completeness",
                    metric_value=completeness,
                    unit="percent",
                    status=completeness_status,
                    details={
                        "total_records": total,
                        "missing_price": missing_price,
                        "missing_address": missing_address,
                        "missing_coords": missing_coords
                    }
                ))
        
        except Exception as e:
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="data_quality_error",
                metric_value=0,
                unit="count",
                status="WARNING", 
                details={"error": str(e)}
            ))
        
        return metrics
    
    def _get_system_resource_metrics(self) -> List[SystemMetric]:
        """시스템 리소스 메트릭"""
        metrics = []
        current_time = datetime.now().isoformat()
        
        try:
            import psutil
            
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = "NORMAL" if cpu_percent < 80 else "WARNING" if cpu_percent < 95 else "CRITICAL"
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="cpu_usage",
                metric_value=cpu_percent,
                unit="percent",
                status=cpu_status,
                details={"cpu_count": psutil.cpu_count()}
            ))
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_status = "NORMAL" if memory.percent < self.thresholds['memory_usage_max'] else "CRITICAL"
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="memory_usage",
                metric_value=memory.percent,
                unit="percent",
                status=memory_status,
                details={
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                }
            ))
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_status = "NORMAL" if disk.percent < 80 else "WARNING" if disk.percent < 90 else "CRITICAL"
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="disk_usage",
                metric_value=disk.percent,
                unit="percent",
                status=disk_status,
                details={
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                }
            ))
            
        except ImportError:
            # psutil 없는 경우 기본값
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="resource_monitoring_unavailable",
                metric_value=0,
                unit="count",
                status="WARNING",
                details={"message": "psutil not available"}
            ))
        
        return metrics
    
    def _get_database_metrics(self) -> List[SystemMetric]:
        """데이터베이스 메트릭"""
        metrics = []
        current_time = datetime.now().isoformat()
        
        try:
            # 활성 매물 수
            active_count = self.helper.client.table('properties')\
                .select('*', count='exact')\
                .eq('is_active', True)\
                .execute()
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="active_properties_count",
                metric_value=active_count.count or 0,
                unit="count",
                status="NORMAL",
                details={"table": "properties"}
            ))
            
            # 최근 24시간 변경 사항
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            
            recent_changes = self.helper.client.table('properties')\
                .select('*', count='exact')\
                .gte('updated_at', yesterday)\
                .execute()
            
            change_rate = recent_changes.count or 0
            change_status = "NORMAL" if change_rate > 0 else "WARNING"
            
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="daily_change_rate",
                metric_value=change_rate,
                unit="count",
                status=change_status,
                details={"period_hours": 24}
            ))
            
        except Exception as e:
            metrics.append(SystemMetric(
                timestamp=current_time,
                metric_name="database_metrics_error",
                metric_value=0,
                unit="count",
                status="WARNING",
                details={"error": str(e)}
            ))
        
        return metrics
    
    def _check_alerts(self, metrics: List[SystemMetric]):
        """알림 체크 및 발송"""
        for metric in metrics:
            if metric.status in ["WARNING", "CRITICAL"]:
                # 기존 알림이 있는지 확인
                existing_alert = next(
                    (a for a in self.active_alerts 
                     if a.source == metric.metric_name and not a.resolved), 
                    None
                )
                
                if not existing_alert:
                    # 새 알림 생성
                    alert = Alert(
                        alert_id=f"{metric.metric_name}_{int(time.time())}",
                        timestamp=metric.timestamp,
                        alert_type=metric.status,
                        title=f"{metric.metric_name.replace('_', ' ').title()} Alert",
                        message=f"{metric.metric_name}: {metric.metric_value}{metric.unit}",
                        source=metric.metric_name
                    )
                    
                    self.active_alerts.append(alert)
                    
                    # 알림 발송
                    self._send_notification(alert)
    
    def _send_notification(self, alert: Alert):
        """알림 발송"""
        print(f"🚨 {alert.alert_type} Alert: {alert.title}")
        print(f"   {alert.message}")
        
        # Slack 알림 (웹훅이 설정된 경우)
        if self.slack_webhook:
            self._send_slack_notification(alert)
        
        # 중요한 알림의 경우 자동 복구 트리거
        if alert.alert_type == "CRITICAL":
            self._trigger_auto_recovery(alert)
    
    def _send_slack_notification(self, alert: Alert):
        """Slack 알림 발송"""
        try:
            color = "#ff0000" if alert.alert_type == "CRITICAL" else "#ffaa00"
            
            payload = {
                "text": f"🚨 {alert.title}",
                "attachments": [{
                    "color": color,
                    "fields": [{
                        "title": "Details",
                        "value": alert.message,
                        "short": False
                    }, {
                        "title": "Time",
                        "value": alert.timestamp,
                        "short": True
                    }]
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload)
            if response.status_code == 200:
                print("📱 Slack 알림 발송 완료")
            
        except Exception as e:
            print(f"❌ Slack 알림 발송 실패: {e}")
    
    def _trigger_auto_recovery(self, alert: Alert):
        """자동 복구 트리거"""
        print(f"🔧 자동 복구 트리거: {alert.source}")
        
        # 메모리 부족시 가비지 컬렉션
        if alert.source == "memory_usage":
            import gc
            gc.collect()
            print("   🗑️ 가비지 컬렉션 실행")
        
        # 수집 성능 저하시 프로세스 재시작 제안
        elif alert.source == "collection_rate":
            print("   💡 수집기 재시작을 권장합니다")
        
        # 데이터베이스 연결 문제시 재연결 시도
        elif "database" in alert.source:
            try:
                self.helper = SupabaseHelper()  # 재연결
                print("   🔌 데이터베이스 재연결 완료")
            except Exception as e:
                print(f"   ❌ 재연결 실패: {e}")
    
    def _print_current_status(self, metrics: List[SystemMetric]):
        """현재 상태 출력"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 중요 메트릭만 출력
        key_metrics = ['collection_rate', 'success_rate', 'data_completeness', 'memory_usage']
        
        status_line = f"[{timestamp}] "
        for metric in metrics:
            if metric.metric_name in key_metrics:
                status_icon = "🟢" if metric.status == "NORMAL" else "🟡" if metric.status == "WARNING" else "🔴"
                status_line += f"{status_icon}{metric.metric_name}:{metric.metric_value:.1f}{metric.unit} "
        
        print(status_line)
    
    def _setup_web_routes(self):
        """웹 대시보드 라우트 설정"""
        
        @self.app.route('/')
        def dashboard():
            """메인 대시보드"""
            return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>네이버 수집기 모니터링</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; }
        .metric-normal { color: #4CAF50; }
        .metric-warning { color: #FF9800; }
        .metric-critical { color: #F44336; }
        .chart-container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .alert-item { padding: 10px; margin: 5px 0; border-radius: 5px; }
        .alert-warning { background: #fff3cd; border-left: 4px solid #ff9800; }
        .alert-critical { background: #f8d7da; border-left: 4px solid #f44336; }
        .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-normal { background-color: #4CAF50; }
        .status-warning { background-color: #FF9800; }
        .status-critical { background-color: #F44336; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 네이버 부동산 수집기 실시간 모니터링</h1>
            <p>마지막 업데이트: <span id="last-update"></span></p>
        </div>
        
        <div class="metrics-grid" id="metrics-grid">
            <!-- 메트릭 카드들이 동적으로 추가됩니다 -->
        </div>
        
        <div class="chart-container">
            <h3>📈 수집 성능 트렌드</h3>
            <canvas id="performanceChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>🚨 활성 알림</h3>
            <div id="alerts-container">
                <!-- 알림들이 동적으로 추가됩니다 -->
            </div>
        </div>
    </div>

    <script>
        // 차트 초기화
        const ctx = document.getElementById('performanceChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '수집 속도 (건/분)',
                    data: [],
                    borderColor: '#4CAF50',
                    tension: 0.1
                }, {
                    label: '성공률 (%)', 
                    data: [],
                    borderColor: '#2196F3',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        // 데이터 업데이트 함수
        async function updateDashboard() {
            try {
                // 메트릭 데이터 가져오기
                const metricsResponse = await fetch('/api/metrics');
                const metrics = await metricsResponse.json();
                
                // 알림 데이터 가져오기
                const alertsResponse = await fetch('/api/alerts');
                const alerts = await alertsResponse.json();
                
                // UI 업데이트
                updateMetricsGrid(metrics);
                updateChart(metrics);
                updateAlerts(alerts);
                
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                
            } catch (error) {
                console.error('데이터 업데이트 오류:', error);
            }
        }

        function updateMetricsGrid(metrics) {
            const grid = document.getElementById('metrics-grid');
            grid.innerHTML = '';
            
            const keyMetrics = ['collection_rate', 'success_rate', 'data_completeness', 'memory_usage'];
            const metricNames = {
                'collection_rate': '수집 속도',
                'success_rate': '성공률',
                'data_completeness': '데이터 완성도',
                'memory_usage': '메모리 사용률'
            };
            
            keyMetrics.forEach(metricName => {
                const metric = metrics.find(m => m.metric_name === metricName);
                if (metric) {
                    const card = document.createElement('div');
                    card.className = 'metric-card';
                    
                    const statusClass = `metric-${metric.status.toLowerCase()}`;
                    const statusIndicator = `status-${metric.status.toLowerCase()}`;
                    
                    card.innerHTML = `
                        <div>
                            <span class="status-indicator ${statusIndicator}"></span>
                            <strong>${metricNames[metricName] || metricName}</strong>
                        </div>
                        <div class="metric-value ${statusClass}">
                            ${metric.metric_value.toFixed(1)} ${metric.unit}
                        </div>
                    `;
                    
                    grid.appendChild(card);
                }
            });
        }

        function updateChart(metrics) {
            const collectionRateMetric = metrics.find(m => m.metric_name === 'collection_rate');
            const successRateMetric = metrics.find(m => m.metric_name === 'success_rate');
            
            if (collectionRateMetric && successRateMetric) {
                const now = new Date().toLocaleTimeString();
                
                // 최근 20개 데이터포인트만 유지
                if (chart.data.labels.length >= 20) {
                    chart.data.labels.shift();
                    chart.data.datasets[0].data.shift();
                    chart.data.datasets[1].data.shift();
                }
                
                chart.data.labels.push(now);
                chart.data.datasets[0].data.push(collectionRateMetric.metric_value);
                chart.data.datasets[1].data.push(successRateMetric.metric_value);
                
                chart.update('none');
            }
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            container.innerHTML = '';
            
            const activeAlerts = alerts.filter(a => !a.resolved);
            
            if (activeAlerts.length === 0) {
                container.innerHTML = '<p>✅ 현재 활성 알림이 없습니다.</p>';
                return;
            }
            
            activeAlerts.forEach(alert => {
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert-item alert-${alert.alert_type.toLowerCase()}`;
                alertDiv.innerHTML = `
                    <strong>${alert.title}</strong><br>
                    ${alert.message}<br>
                    <small>${new Date(alert.timestamp).toLocaleString()}</small>
                `;
                container.appendChild(alertDiv);
            });
        }

        // 주기적 업데이트
        updateDashboard();
        setInterval(updateDashboard, 10000); // 10초마다 업데이트
    </script>
</body>
</html>
            """)
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """메트릭 API"""
            # 최신 메트릭만 반환
            latest_metrics = []
            metric_names = set()
            
            # 최신 타임스탬프부터 역순으로 확인
            for metric in reversed(self.metrics_history):
                if metric.metric_name not in metric_names:
                    latest_metrics.append(asdict(metric))
                    metric_names.add(metric.metric_name)
            
            return jsonify(latest_metrics)
        
        @self.app.route('/api/alerts')
        def api_alerts():
            """알림 API"""
            return jsonify([asdict(alert) for alert in self.active_alerts])

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='실시간 모니터링 시스템 v2.0')
    parser.add_argument('--interval', type=int, default=60, help='모니터링 간격(초)')
    parser.add_argument('--slack-webhook', type=str, help='Slack 웹훅 URL')
    
    args = parser.parse_args()
    
    system = RealtimeMonitoringSystem()
    
    if args.slack_webhook:
        system.slack_webhook = args.slack_webhook
    
    try:
        system.start_monitoring(check_interval=args.interval)
    except KeyboardInterrupt:
        print("\n🛑 모니터링 시스템 종료")
        system.running = False

if __name__ == "__main__":
    main()