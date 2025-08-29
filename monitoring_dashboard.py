#!/usr/bin/env python3
"""
Advanced Monitoring Dashboard for Robust Data Collection System
==============================================================

This component provides comprehensive real-time monitoring, alerting,
and performance analytics for the data collection system.

Key Features:
- Real-time metrics collection and visualization
- Multi-channel alerting (Slack, email, webhook)
- Performance analytics and trending
- System health monitoring
- Custom dashboard widgets
- Historical data analysis
- Automated report generation
"""

import asyncio
import aiohttp
import smtplib
from aiohttp import web, WSMsgType
import aiohttp_cors
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import logging
import threading
import queue
from pathlib import Path
import psutil
from collections import deque, defaultdict

@dataclass
class Alert:
    """Alert message structure"""
    id: str
    level: str  # CRITICAL, WARNING, INFO
    title: str
    message: str
    source: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'level': self.level,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }

@dataclass
class PerformanceMetrics:
    """Detailed performance metrics"""
    timestamp: datetime
    
    # Collection Performance
    properties_per_minute: float
    collections_success_rate: float
    avg_response_time_ms: float
    
    # System Resources
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_usage_gb: float
    disk_usage_percent: float
    network_io_mbps: float
    
    # Worker Performance
    active_workers: int
    idle_workers: int
    failed_workers: int
    avg_worker_efficiency: float
    
    # API Performance
    api_requests_per_second: float
    api_error_rate: float
    token_health_score: float
    
    # Database Performance  
    db_queries_per_second: float
    db_connection_pool_usage: float
    db_avg_query_time_ms: float
    
    def to_dict(self) -> Dict:
        return asdict(self)

class MetricsCollector:
    """Advanced metrics collection and aggregation"""
    
    def __init__(self, retention_hours: int = 48):
        self.retention_hours = retention_hours
        self.metrics_buffer = deque(maxlen=retention_hours * 60)  # 1 minute intervals
        self.aggregated_metrics = {
            'hourly': defaultdict(list),
            'daily': defaultdict(list)
        }
        self.lock = threading.Lock()
        
        # Initialize SQLite for persistence
        self.db_path = Path("monitoring.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp TEXT PRIMARY KEY,
                    properties_per_minute REAL,
                    collections_success_rate REAL,
                    avg_response_time_ms REAL,
                    cpu_usage_percent REAL,
                    memory_usage_percent REAL,
                    memory_usage_gb REAL,
                    disk_usage_percent REAL,
                    network_io_mbps REAL,
                    active_workers INTEGER,
                    idle_workers INTEGER,
                    failed_workers INTEGER,
                    avg_worker_efficiency REAL,
                    api_requests_per_second REAL,
                    api_error_rate REAL,
                    token_health_score REAL,
                    db_queries_per_second REAL,
                    db_connection_pool_usage REAL,
                    db_avg_query_time_ms REAL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    level TEXT,
                    title TEXT,
                    message TEXT,
                    source TEXT,
                    timestamp TEXT,
                    acknowledged INTEGER,
                    acknowledged_by TEXT,
                    acknowledged_at TEXT
                )
            ''')
    
    def add_metrics(self, metrics: PerformanceMetrics):
        """Add new metrics data point"""
        with self.lock:
            # Add to buffer
            self.metrics_buffer.append(metrics)
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                values = (
                    metrics.timestamp.isoformat(),
                    metrics.properties_per_minute,
                    metrics.collections_success_rate,
                    metrics.avg_response_time_ms,
                    metrics.cpu_usage_percent,
                    metrics.memory_usage_percent,
                    metrics.memory_usage_gb,
                    metrics.disk_usage_percent,
                    metrics.network_io_mbps,
                    metrics.active_workers,
                    metrics.idle_workers,
                    metrics.failed_workers,
                    metrics.avg_worker_efficiency,
                    metrics.api_requests_per_second,
                    metrics.api_error_rate,
                    metrics.token_health_score,
                    metrics.db_queries_per_second,
                    metrics.db_connection_pool_usage,
                    metrics.db_avg_query_time_ms
                )
                conn.execute('''
                    INSERT OR REPLACE INTO metrics VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                ''', values)
            
            # Update aggregations
            self._update_aggregations(metrics)
    
    def _update_aggregations(self, metrics: PerformanceMetrics):
        """Update hourly and daily aggregations"""
        hour_key = metrics.timestamp.strftime('%Y-%m-%d-%H')
        day_key = metrics.timestamp.strftime('%Y-%m-%d')
        
        self.aggregated_metrics['hourly'][hour_key].append(metrics)
        self.aggregated_metrics['daily'][day_key].append(metrics)
        
        # Cleanup old aggregations
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        # Remove old hourly data
        old_hours = [k for k in self.aggregated_metrics['hourly'] 
                    if datetime.strptime(k, '%Y-%m-%d-%H') < cutoff_time]
        for hour in old_hours:
            del self.aggregated_metrics['hourly'][hour]
    
    def get_recent_metrics(self, minutes: int = 60) -> List[PerformanceMetrics]:
        """Get recent metrics for specified time window"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            return [m for m in self.metrics_buffer if m.timestamp >= cutoff_time]
    
    def get_aggregated_metrics(self, period: str = 'hourly', count: int = 24) -> Dict[str, Any]:
        """Get aggregated metrics for specified period"""
        if period not in self.aggregated_metrics:
            return {}
        
        data = self.aggregated_metrics[period]
        
        # Get most recent periods
        sorted_keys = sorted(data.keys(), reverse=True)[:count]
        
        result = {}
        for key in sorted_keys:
            metrics_list = data[key]
            if metrics_list:
                # Calculate averages
                result[key] = {
                    'avg_properties_per_minute': sum(m.properties_per_minute for m in metrics_list) / len(metrics_list),
                    'avg_success_rate': sum(m.collections_success_rate for m in metrics_list) / len(metrics_list),
                    'avg_cpu_usage': sum(m.cpu_usage_percent for m in metrics_list) / len(metrics_list),
                    'avg_memory_usage': sum(m.memory_usage_percent for m in metrics_list) / len(metrics_list),
                    'max_active_workers': max(m.active_workers for m in metrics_list),
                    'avg_api_error_rate': sum(m.api_error_rate for m in metrics_list) / len(metrics_list),
                    'count': len(metrics_list)
                }
        
        return result

class AlertManager:
    """Advanced alert management with multiple notification channels"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict] = []
        self.notification_channels = {
            'slack': None,
            'email': None,
            'webhook': None
        }
        self.alert_queue = queue.Queue()
        self.lock = threading.Lock()
        self.logger = logging.getLogger('AlertManager')
        
        # Start alert processing thread
        threading.Thread(target=self._process_alerts, daemon=True).start()
    
    def configure_slack(self, webhook_url: str):
        """Configure Slack notifications"""
        self.notification_channels['slack'] = webhook_url
        self.logger.info("Slack notifications configured")
    
    def configure_email(self, smtp_host: str, smtp_port: int, username: str, password: str):
        """Configure email notifications"""
        self.notification_channels['email'] = {
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'username': username,
            'password': password
        }
        self.logger.info("Email notifications configured")
    
    def configure_webhook(self, webhook_url: str):
        """Configure webhook notifications"""
        self.notification_channels['webhook'] = webhook_url
        self.logger.info("Webhook notifications configured")
    
    def add_alert_rule(self, rule: Dict):
        """Add alert rule for automatic triggering"""
        required_fields = ['name', 'condition', 'level', 'message']
        if not all(field in rule for field in required_fields):
            raise ValueError(f"Alert rule must contain: {required_fields}")
        
        self.alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {rule['name']}")
    
    def create_alert(self, level: str, title: str, message: str, source: str = "system") -> str:
        """Create new alert"""
        alert_id = f"alert_{int(time.time() * 1000)}_{hash(message) % 10000}"
        
        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.now()
        )
        
        with self.lock:
            self.alerts[alert_id] = alert
        
        # Queue for notification
        self.alert_queue.put(alert)
        
        self.logger.info(f"Created alert [{level}]: {title}")
        return alert_id
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        with self.lock:
            if alert_id in self.alerts:
                alert = self.alerts[alert_id]
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        
        return False
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active (unacknowledged) alerts"""
        with self.lock:
            return [alert.to_dict() for alert in self.alerts.values() if not alert.acknowledged]
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts within specified time window"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            return [
                alert.to_dict() for alert in self.alerts.values() 
                if alert.timestamp >= cutoff_time
            ]
    
    def evaluate_rules(self, metrics: PerformanceMetrics):
        """Evaluate alert rules against current metrics"""
        for rule in self.alert_rules:
            try:
                condition = rule['condition']
                
                # Simple condition evaluation (can be enhanced)
                if self._evaluate_condition(condition, metrics):
                    self.create_alert(
                        level=rule['level'],
                        title=rule['name'],
                        message=rule['message'].format(**metrics.to_dict()),
                        source="auto_rule"
                    )
                    
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.get('name', 'unknown')}: {e}")
    
    def _evaluate_condition(self, condition: str, metrics: PerformanceMetrics) -> bool:
        """Evaluate alert condition (simple implementation)"""
        try:
            # Replace metric names with actual values
            condition_eval = condition
            for key, value in metrics.to_dict().items():
                if isinstance(value, (int, float)):
                    condition_eval = condition_eval.replace(key, str(value))
            
            # Evaluate the condition
            return eval(condition_eval)
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _process_alerts(self):
        """Background thread for processing alert notifications"""
        while True:
            try:
                alert = self.alert_queue.get(timeout=1)
                
                # Send notifications
                asyncio.run(self._send_notifications(alert))
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing alert notifications: {e}")
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications to configured channels"""
        tasks = []
        
        if self.notification_channels['slack']:
            tasks.append(self._send_slack_notification(alert))
        
        if self.notification_channels['email']:
            tasks.append(self._send_email_notification(alert))
        
        if self.notification_channels['webhook']:
            tasks.append(self._send_webhook_notification(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        try:
            webhook_url = self.notification_channels['slack']
            
            color_map = {
                'CRITICAL': '#ff0000',
                'WARNING': '#ffaa00',
                'INFO': '#00aa00'
            }
            
            payload = {
                'attachments': [{
                    'color': color_map.get(alert.level, '#cccccc'),
                    'title': f"🚨 {alert.title}",
                    'text': alert.message,
                    'fields': [
                        {'title': 'Level', 'value': alert.level, 'short': True},
                        {'title': 'Source', 'value': alert.source, 'short': True},
                        {'title': 'Time', 'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'short': True}
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack notification sent for alert {alert.id}")
                    else:
                        self.logger.error(f"Failed to send Slack notification: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")
    
    async def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        try:
            config = self.notification_channels['email']
            
            msg = MimeMultipart()
            msg['From'] = config['username']
            msg['To'] = config.get('recipients', config['username'])
            msg['Subject'] = f"[{alert.level}] {alert.title}"
            
            body = f"""
Alert Details:
- Level: {alert.level}
- Title: {alert.title}
- Message: {alert.message}
- Source: {alert.source}
- Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Alert ID: {alert.id}

This is an automated alert from the Naver Real Estate Collection System.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email notification sent for alert {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
    
    async def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification"""
        try:
            webhook_url = self.notification_channels['webhook']
            
            payload = alert.to_dict()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook notification sent for alert {alert.id}")
                    else:
                        self.logger.error(f"Failed to send webhook notification: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")

class MonitoringDashboard:
    """
    Advanced monitoring dashboard with real-time updates and comprehensive analytics
    """
    
    def __init__(self, config, metrics):
        self.config = config
        self.system_metrics = metrics
        
        # Components
        self.metrics_collector = MetricsCollector(retention_hours=48)
        self.alert_manager = AlertManager()
        
        # Web application
        self.app = web.Application()
        self.websocket_connections: Set[web.WebSocketResponse] = set()
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        
        # Logging
        self.logger = logging.getLogger('MonitoringDashboard')
        
        # Setup routes
        self._setup_routes()
        
        # Configure default alert rules
        self._setup_default_alert_rules()
        
        print("📊 Advanced Monitoring Dashboard initialized")
    
    def _setup_routes(self):
        """Setup web application routes"""
        # Static files
        self.app.router.add_static('/', 'static/', name='static')
        
        # API routes
        self.app.router.add_get('/', self._dashboard_handler)
        self.app.router.add_get('/api/metrics/current', self._current_metrics_handler)
        self.app.router.add_get('/api/metrics/history', self._metrics_history_handler)
        self.app.router.add_get('/api/alerts/active', self._active_alerts_handler)
        self.app.router.add_get('/api/alerts/recent', self._recent_alerts_handler)
        self.app.router.add_post('/api/alerts/{alert_id}/acknowledge', self._acknowledge_alert_handler)
        self.app.router.add_get('/api/system/health', self._system_health_handler)
        self.app.router.add_get('/api/performance/report', self._performance_report_handler)
        
        # WebSocket for real-time updates
        self.app.router.add_get('/ws', self._websocket_handler)
        
        # CORS configuration
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules"""
        default_rules = [
            {
                'name': 'High CPU Usage',
                'condition': 'cpu_usage_percent > 80',
                'level': 'WARNING',
                'message': 'CPU usage is high: {cpu_usage_percent:.1f}%'
            },
            {
                'name': 'Critical CPU Usage',
                'condition': 'cpu_usage_percent > 95',
                'level': 'CRITICAL',
                'message': 'CPU usage is critical: {cpu_usage_percent:.1f}%'
            },
            {
                'name': 'High Memory Usage',
                'condition': 'memory_usage_percent > 85',
                'level': 'WARNING',
                'message': 'Memory usage is high: {memory_usage_percent:.1f}%'
            },
            {
                'name': 'Low Collection Rate',
                'condition': 'properties_per_minute < 5',
                'level': 'WARNING',
                'message': 'Collection rate is low: {properties_per_minute:.1f} properties/min'
            },
            {
                'name': 'High Error Rate',
                'condition': 'api_error_rate > 0.1',
                'level': 'WARNING',
                'message': 'API error rate is high: {api_error_rate:.2%}'
            },
            {
                'name': 'No Active Workers',
                'condition': 'active_workers == 0',
                'level': 'CRITICAL',
                'message': 'No active workers detected!'
            }
        ]
        
        for rule in default_rules:
            self.alert_manager.add_alert_rule(rule)
    
    async def initialize(self):
        """Initialize monitoring dashboard"""
        try:
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._metrics_collection_task()),
                asyncio.create_task(self._websocket_broadcast_task()),
                asyncio.create_task(self._alert_evaluation_task())
            ])
            
            self.logger.info("Monitoring Dashboard initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard initialization failed: {e}")
            return False
    
    async def start_server(self, host: str = '0.0.0.0', port: int = 8080):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        self.logger.info(f"Monitoring Dashboard started on http://{host}:{port}")
        return runner
    
    async def _dashboard_handler(self, request):
        """Serve main dashboard HTML"""
        dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Robust Data Collection - Monitoring Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .metric-label { color: #666; font-size: 0.9em; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .alert { padding: 15px; border-radius: 8px; margin-bottom: 10px; }
        .alert-critical { background: #ffebee; border-left: 4px solid #f44336; }
        .alert-warning { background: #fff3e0; border-left: 4px solid #ff9800; }
        .alert-info { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-healthy { background: #4caf50; }
        .status-warning { background: #ff9800; }
        .status-critical { background: #f44336; }
        #connection-status { float: right; }
        .refresh-btn { background: #2196f3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Robust Data Collection System - Monitoring Dashboard</h1>
        <p>Real-time monitoring and performance analytics</p>
        <div id="connection-status">
            <span class="status-indicator status-healthy"></span>
            <span>Connected</span>
        </div>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value" id="properties-per-minute">-</div>
            <div class="metric-label">Properties/Minute</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="success-rate">-</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="active-workers">-</div>
            <div class="metric-label">Active Workers</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="cpu-usage">-</div>
            <div class="metric-label">CPU Usage</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="memory-usage">-</div>
            <div class="metric-label">Memory Usage</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="api-error-rate">-</div>
            <div class="metric-label">API Error Rate</div>
        </div>
    </div>
    
    <div class="chart-container">
        <h3>Performance Trends</h3>
        <canvas id="performance-chart" width="400" height="200"></canvas>
    </div>
    
    <div class="chart-container">
        <h3>Active Alerts</h3>
        <div id="alerts-container">Loading alerts...</div>
    </div>
    
    <script>
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onopen = function() {
            console.log('WebSocket connected');
            document.getElementById('connection-status').innerHTML = 
                '<span class="status-indicator status-healthy"></span><span>Connected</span>';
        };
        
        ws.onclose = function() {
            console.log('WebSocket disconnected');
            document.getElementById('connection-status').innerHTML = 
                '<span class="status-indicator status-critical"></span><span>Disconnected</span>';
        };
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'metrics_update') {
                updateMetrics(data.metrics);
            } else if (data.type === 'alerts_update') {
                updateAlerts(data.alerts);
            }
        };
        
        // Performance chart
        const ctx = document.getElementById('performance-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Properties/Min',
                    data: [],
                    borderColor: '#2196f3',
                    fill: false
                }, {
                    label: 'Success Rate %',
                    data: [],
                    borderColor: '#4caf50',
                    fill: false
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        function updateMetrics(metrics) {
            document.getElementById('properties-per-minute').textContent = 
                metrics.properties_per_minute ? metrics.properties_per_minute.toFixed(1) : '-';
            document.getElementById('success-rate').textContent = 
                metrics.collections_success_rate ? (metrics.collections_success_rate * 100).toFixed(1) + '%' : '-';
            document.getElementById('active-workers').textContent = metrics.active_workers || '-';
            document.getElementById('cpu-usage').textContent = 
                metrics.cpu_usage_percent ? metrics.cpu_usage_percent.toFixed(1) + '%' : '-';
            document.getElementById('memory-usage').textContent = 
                metrics.memory_usage_percent ? metrics.memory_usage_percent.toFixed(1) + '%' : '-';
            document.getElementById('api-error-rate').textContent = 
                metrics.api_error_rate ? (metrics.api_error_rate * 100).toFixed(2) + '%' : '-';
            
            // Update chart
            const time = new Date().toLocaleTimeString();
            chart.data.labels.push(time);
            chart.data.datasets[0].data.push(metrics.properties_per_minute || 0);
            chart.data.datasets[1].data.push((metrics.collections_success_rate || 0) * 100);
            
            if (chart.data.labels.length > 20) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
                chart.data.datasets[1].data.shift();
            }
            
            chart.update('none');
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<p>No active alerts</p>';
                return;
            }
            
            container.innerHTML = alerts.map(alert => `
                <div class="alert alert-${alert.level.toLowerCase()}">
                    <strong>${alert.title}</strong><br>
                    ${alert.message}<br>
                    <small>${alert.source} - ${new Date(alert.timestamp).toLocaleString()}</small>
                </div>
            `).join('');
        }
        
        // Initial data load
        fetch('/api/metrics/current')
            .then(response => response.json())
            .then(data => updateMetrics(data));
        
        fetch('/api/alerts/active')
            .then(response => response.json())
            .then(data => updateAlerts(data));
    </script>
</body>
</html>
        """
        
        return web.Response(text=dashboard_html, content_type='text/html')
    
    async def _current_metrics_handler(self, request):
        """API endpoint for current metrics"""
        # Generate current metrics from system_metrics
        current_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            properties_per_minute=self.system_metrics.properties_per_minute,
            collections_success_rate=self.system_metrics.collections_successful / max(
                self.system_metrics.collections_successful + self.system_metrics.collections_failed, 1
            ),
            avg_response_time_ms=self.system_metrics.api_response_time_ms,
            cpu_usage_percent=self.system_metrics.cpu_usage_percent,
            memory_usage_percent=(self.system_metrics.memory_usage_gb / 16.0) * 100,  # Assuming 16GB total
            memory_usage_gb=self.system_metrics.memory_usage_gb,
            disk_usage_percent=self.system_metrics.disk_usage_percent,
            network_io_mbps=0.0,  # Would need to calculate
            active_workers=self.system_metrics.active_workers,
            idle_workers=0,  # Would need to calculate
            failed_workers=0,  # Would need to calculate
            avg_worker_efficiency=0.8,  # Would need to calculate
            api_requests_per_second=self.system_metrics.api_requests_total / 60,  # Rough estimate
            api_error_rate=self.system_metrics.error_rate,
            token_health_score=0.9,  # Would need to calculate
            db_queries_per_second=self.system_metrics.db_queries_per_second,
            db_connection_pool_usage=self.system_metrics.db_connections_active / 20,  # Assuming pool of 20
            db_avg_query_time_ms=50.0  # Would need to calculate
        )
        
        return web.json_response(current_metrics.to_dict())
    
    async def _metrics_history_handler(self, request):
        """API endpoint for metrics history"""
        minutes = int(request.query.get('minutes', 60))
        recent_metrics = self.metrics_collector.get_recent_metrics(minutes)
        
        return web.json_response([m.to_dict() for m in recent_metrics])
    
    async def _active_alerts_handler(self, request):
        """API endpoint for active alerts"""
        alerts = self.alert_manager.get_active_alerts()
        return web.json_response(alerts)
    
    async def _recent_alerts_handler(self, request):
        """API endpoint for recent alerts"""
        hours = int(request.query.get('hours', 24))
        alerts = self.alert_manager.get_recent_alerts(hours)
        return web.json_response(alerts)
    
    async def _acknowledge_alert_handler(self, request):
        """API endpoint to acknowledge alerts"""
        alert_id = request.match_info['alert_id']
        acknowledged_by = request.query.get('user', 'anonymous')
        
        success = self.alert_manager.acknowledge_alert(alert_id, acknowledged_by)
        
        return web.json_response({'success': success})
    
    async def _system_health_handler(self, request):
        """API endpoint for system health"""
        health_data = {
            'overall_health': 'healthy',  # Would calculate from components
            'components': {
                'dashboard': 'healthy',
                'metrics_collector': 'healthy',
                'alert_manager': 'healthy'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return web.json_response(health_data)
    
    async def _performance_report_handler(self, request):
        """API endpoint for performance reports"""
        report = {
            'current_metrics': self.system_metrics.__dict__.copy(),
            'aggregated_metrics': self.metrics_collector.get_aggregated_metrics(),
            'active_alerts_count': len(self.alert_manager.get_active_alerts()),
            'generated_at': datetime.now().isoformat()
        }
        
        return web.json_response(report)
    
    async def _websocket_handler(self, request):
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    if msg.data == 'close':
                        await ws.close()
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            self.websocket_connections.discard(ws)
        
        return ws
    
    async def _metrics_collection_task(self):
        """Background task for collecting metrics"""
        while not self.shutdown_event.is_set():
            try:
                # Create performance metrics from system metrics
                metrics = PerformanceMetrics(
                    timestamp=datetime.now(),
                    properties_per_minute=self.system_metrics.properties_per_minute,
                    collections_success_rate=self.system_metrics.collections_successful / max(
                        self.system_metrics.collections_successful + self.system_metrics.collections_failed, 1
                    ),
                    avg_response_time_ms=self.system_metrics.api_response_time_ms,
                    cpu_usage_percent=psutil.cpu_percent(),
                    memory_usage_percent=psutil.virtual_memory().percent,
                    memory_usage_gb=psutil.virtual_memory().used / (1024**3),
                    disk_usage_percent=psutil.disk_usage('/').percent,
                    network_io_mbps=0.0,  # Would need to implement
                    active_workers=self.system_metrics.active_workers,
                    idle_workers=0,  # Would need to implement
                    failed_workers=0,  # Would need to implement
                    avg_worker_efficiency=0.8,  # Would need to implement
                    api_requests_per_second=self.system_metrics.api_requests_total / 60,
                    api_error_rate=self.system_metrics.error_rate,
                    token_health_score=0.9,  # Would need to implement
                    db_queries_per_second=self.system_metrics.db_queries_per_second,
                    db_connection_pool_usage=self.system_metrics.db_connections_active / 20,
                    db_avg_query_time_ms=50.0  # Would need to implement
                )
                
                # Add to collector
                self.metrics_collector.add_metrics(metrics)
                
                # Evaluate alert rules
                self.alert_manager.evaluate_rules(metrics)
                
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
            
            await asyncio.sleep(60)  # Collect every minute
    
    async def _websocket_broadcast_task(self):
        """Background task for broadcasting updates to WebSocket clients"""
        while not self.shutdown_event.is_set():
            try:
                if self.websocket_connections:
                    # Get current metrics and alerts
                    metrics = await self._current_metrics_handler(None)
                    alerts = self.alert_manager.get_active_alerts()
                    
                    # Broadcast to all connections
                    for ws in self.websocket_connections.copy():
                        try:
                            await ws.send_str(json.dumps({
                                'type': 'metrics_update',
                                'metrics': json.loads(metrics.body)
                            }))
                            
                            await ws.send_str(json.dumps({
                                'type': 'alerts_update',
                                'alerts': alerts
                            }))
                        except Exception as e:
                            self.logger.warning(f"Failed to send WebSocket update: {e}")
                            self.websocket_connections.discard(ws)
                
            except Exception as e:
                self.logger.error(f"WebSocket broadcast error: {e}")
            
            await asyncio.sleep(30)  # Broadcast every 30 seconds
    
    async def _alert_evaluation_task(self):
        """Background task for alert evaluation"""
        while not self.shutdown_event.is_set():
            try:
                # This would be done in metrics collection, but keeping separate for clarity
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Alert evaluation error: {e}")
    
    async def update_metrics(self, metrics):
        """Update system metrics (called from architecture)"""
        self.system_metrics = metrics
    
    async def send_alert(self, alert_data: Dict):
        """Send alert (called from architecture)"""
        self.alert_manager.create_alert(
            level=alert_data['level'],
            title=alert_data.get('title', 'System Alert'),
            message=alert_data['message'],
            source=alert_data.get('source', 'system')
        )
    
    async def health_check(self) -> str:
        """Component health check"""
        try:
            # Check if background tasks are running
            if any(task.done() for task in self.background_tasks):
                return 'degraded'
            
            return 'healthy'
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return 'unhealthy'
    
    async def shutdown(self):
        """Shutdown dashboard"""
        self.shutdown_event.set()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Close WebSocket connections
        for ws in self.websocket_connections:
            await ws.close()
        
        self.logger.info("Monitoring Dashboard shut down")

# Testing
async def test_monitoring_dashboard():
    """Test monitoring dashboard"""
    print("🧪 Testing Monitoring Dashboard")
    print("=" * 50)
    
    # Mock configuration and metrics
    from robust_architecture_design import SystemConfiguration, SystemMetrics
    
    config = SystemConfiguration()
    metrics = SystemMetrics()
    
    # Create dashboard
    dashboard = MonitoringDashboard(config, metrics)
    
    # Initialize
    success = await dashboard.initialize()
    print(f"✅ Initialization: {'Success' if success else 'Failed'}")
    
    # Start server (would run in production)
    print("🌐 Dashboard would be available at http://localhost:8080")
    
    # Health check
    health = await dashboard.health_check()
    print(f"🏥 Health: {health}")
    
    # Test alert creation
    dashboard.alert_manager.create_alert(
        level='INFO',
        title='Test Alert',
        message='This is a test alert',
        source='test'
    )
    
    alerts = dashboard.alert_manager.get_active_alerts()
    print(f"🚨 Active Alerts: {len(alerts)}")
    
    await dashboard.shutdown()
    print("✅ Dashboard test complete")

if __name__ == "__main__":
    asyncio.run(test_monitoring_dashboard())