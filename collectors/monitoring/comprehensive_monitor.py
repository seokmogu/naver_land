#!/usr/bin/env python3
"""
Comprehensive Monitoring System - Real-time monitoring and alerting
Provides visibility into collection pipeline health and performance
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import threading
from collections import deque
import statistics

# Configure comprehensive logging
logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Individual metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class AlertRule:
    """Alert configuration"""
    name: str
    metric: str
    condition: Callable[[float], bool]
    message: str
    severity: str = "WARNING"
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None

class ComprehensiveMonitor:
    """Comprehensive monitoring system for data collection pipeline"""
    
    def __init__(self, retention_hours: int = 24):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.retention_hours = retention_hours
        
        # Metrics storage
        self.metrics: Dict[str, deque] = {}
        self.alert_rules: List[AlertRule] = []
        self.alerts_history: List[Dict] = []
        
        # System state tracking
        self.system_state = {
            'start_time': datetime.now(),
            'current_operation': None,
            'operations_completed': 0,
            'total_errors': 0,
            'last_activity': datetime.now(),
            'health_status': 'STARTING'
        }
        
        # Performance tracking
        self.performance_metrics = {
            'articles_per_minute': deque(maxlen=60),
            'api_response_time': deque(maxlen=100),
            'database_save_time': deque(maxlen=100),
            'memory_usage': deque(maxlen=120),
            'error_rate': deque(maxlen=60),
            'success_rate': deque(maxlen=60)
        }
        
        # Initialize alert rules
        self._setup_default_alerts()
        
        # Start background monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("✅ Comprehensive Monitor initialized")
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        
        # High error rate alert
        self.alert_rules.append(AlertRule(
            name="high_error_rate",
            metric="error_rate",
            condition=lambda x: x > 10.0,  # >10% error rate
            message="Error rate exceeded 10%",
            severity="CRITICAL"
        ))
        
        # Low success rate alert
        self.alert_rules.append(AlertRule(
            name="low_success_rate",
            metric="success_rate", 
            condition=lambda x: x < 80.0,  # <80% success rate
            message="Success rate dropped below 80%",
            severity="WARNING"
        ))
        
        # Slow API response alert
        self.alert_rules.append(AlertRule(
            name="slow_api_response",
            metric="api_response_time",
            condition=lambda x: x > 5.0,  # >5 seconds
            message="API response time exceeded 5 seconds",
            severity="WARNING"
        ))
        
        # High memory usage alert
        self.alert_rules.append(AlertRule(
            name="high_memory_usage",
            metric="memory_usage",
            condition=lambda x: x > 500.0,  # >500MB
            message="Memory usage exceeded 500MB",
            severity="WARNING"
        ))
        
        # No activity alert
        self.alert_rules.append(AlertRule(
            name="no_activity",
            metric="time_since_last_activity",
            condition=lambda x: x > 300.0,  # >5 minutes
            message="No collection activity for over 5 minutes",
            severity="WARNING"
        ))
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = deque(maxlen=1000)
        
        metric_point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            tags=tags or {}
        )
        
        self.metrics[metric_name].append(metric_point)
        
        # Update performance metrics if applicable
        if metric_name in self.performance_metrics:
            self.performance_metrics[metric_name].append(value)
        
        # Update system activity
        self.system_state['last_activity'] = datetime.now()
        
        # Check alerts
        self._check_alerts(metric_name, value)
    
    def record_operation_start(self, operation_name: str, context: Dict = None):
        """Record start of an operation"""
        self.system_state['current_operation'] = operation_name
        self.system_state['last_activity'] = datetime.now()
        
        self.logger.info(f"🚀 Operation started: {operation_name}")
        
        # Record operation metric
        self.record_metric("operations_started", 1, {"operation": operation_name})
    
    def record_operation_success(self, operation_name: str, duration: float, context: Dict = None):
        """Record successful completion of an operation"""
        self.system_state['operations_completed'] += 1
        self.system_state['current_operation'] = None
        self.system_state['last_activity'] = datetime.now()
        
        # Record metrics
        self.record_metric("operation_duration", duration, {"operation": operation_name})
        self.record_metric("operation_success", 1, {"operation": operation_name})
        
        # Update success rate
        self._update_success_rate(True)
        
        self.logger.info(f"✅ Operation completed: {operation_name} ({duration:.2f}s)")
    
    def record_operation_failure(self, operation_name: str, error: Exception, context: Dict = None):
        """Record failed operation"""
        self.system_state['total_errors'] += 1
        self.system_state['current_operation'] = None
        self.system_state['last_activity'] = datetime.now()
        
        # Record metrics
        self.record_metric("operation_failure", 1, {
            "operation": operation_name,
            "error_type": type(error).__name__
        })
        
        # Update success rate
        self._update_success_rate(False)
        
        self.logger.error(f"❌ Operation failed: {operation_name} - {error}")
    
    def record_article_collection(self, article_no: str, success: bool, duration: float, 
                                 data_quality_score: float = None):
        """Record article collection attempt"""
        
        # Record basic metrics
        self.record_metric("article_collection", 1, {
            "article_no": article_no,
            "success": str(success)
        })
        
        if success:
            self.record_metric("article_success_duration", duration)
            if data_quality_score is not None:
                self.record_metric("data_quality_score", data_quality_score)
        else:
            self.record_metric("article_failure_duration", duration)
        
        # Update articles per minute
        self._update_articles_per_minute()
        
        self.logger.debug(f"📊 Article {article_no}: {'✅' if success else '❌'} ({duration:.2f}s)")
    
    def record_api_call(self, endpoint: str, status_code: int, response_time: float):
        """Record API call metrics"""
        
        self.record_metric("api_call", 1, {
            "endpoint": endpoint,
            "status_code": str(status_code)
        })
        
        self.record_metric("api_response_time", response_time, {"endpoint": endpoint})
        
        # Update API response time performance metric
        self.performance_metrics['api_response_time'].append(response_time)
        
        # Record API success/failure
        if 200 <= status_code < 300:
            self.record_metric("api_success", 1, {"endpoint": endpoint})
        else:
            self.record_metric("api_failure", 1, {
                "endpoint": endpoint,
                "status_code": str(status_code)
            })
    
    def record_database_operation(self, operation: str, success: bool, duration: float, 
                                 records_affected: int = 0):
        """Record database operation metrics"""
        
        self.record_metric("database_operation", 1, {
            "operation": operation,
            "success": str(success)
        })
        
        self.record_metric("database_duration", duration, {"operation": operation})
        
        if records_affected > 0:
            self.record_metric("database_records_affected", records_affected, {"operation": operation})
        
        # Update database performance metric
        self.performance_metrics['database_save_time'].append(duration)
        
        self.logger.debug(f"🗄️ DB {operation}: {'✅' if success else '❌'} ({duration:.2f}s, {records_affected} records)")
    
    def record_memory_usage(self, memory_mb: float):
        """Record current memory usage"""
        self.record_metric("memory_usage", memory_mb)
        self.performance_metrics['memory_usage'].append(memory_mb)
    
    def _update_success_rate(self, success: bool):
        """Update rolling success rate"""
        current_rate = self.performance_metrics['success_rate']
        current_rate.append(100.0 if success else 0.0)
        
        # Calculate error rate
        error_rate = 100.0 - (sum(current_rate) / len(current_rate) if current_rate else 0.0)
        self.performance_metrics['error_rate'].append(error_rate)
    
    def _update_articles_per_minute(self):
        """Update articles per minute metric"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Count articles in the last minute
        article_metrics = self.metrics.get("article_collection", deque())
        recent_articles = sum(1 for m in article_metrics if m.timestamp >= minute_ago)
        
        self.performance_metrics['articles_per_minute'].append(recent_articles)
    
    def _check_alerts(self, metric_name: str, value: float):
        """Check if any alerts should be triggered"""
        
        for rule in self.alert_rules:
            if rule.metric == metric_name or rule.metric == "time_since_last_activity":
                
                # Calculate metric value for time-based metrics
                if rule.metric == "time_since_last_activity":
                    time_diff = (datetime.now() - self.system_state['last_activity']).total_seconds()
                    check_value = time_diff
                else:
                    check_value = value
                
                # Check condition and cooldown
                if rule.condition(check_value) and self._is_alert_ready(rule):
                    self._trigger_alert(rule, check_value)
    
    def _is_alert_ready(self, rule: AlertRule) -> bool:
        """Check if alert is ready to trigger (not in cooldown)"""
        if rule.last_triggered is None:
            return True
        
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() - rule.last_triggered >= cooldown_period
    
    def _trigger_alert(self, rule: AlertRule, value: float):
        """Trigger an alert"""
        rule.last_triggered = datetime.now()
        
        alert = {
            'timestamp': rule.last_triggered,
            'rule_name': rule.name,
            'metric': rule.metric,
            'value': value,
            'message': rule.message,
            'severity': rule.severity
        }
        
        self.alerts_history.append(alert)
        
        self.logger.warning(f"🚨 ALERT [{rule.severity}] {rule.name}: {rule.message} (value: {value})")
        
        # Update system health based on alerts
        self._update_health_status()
    
    def _update_health_status(self):
        """Update overall system health status"""
        recent_alerts = [a for a in self.alerts_history 
                        if a['timestamp'] >= datetime.now() - timedelta(minutes=15)]
        
        critical_alerts = [a for a in recent_alerts if a['severity'] == 'CRITICAL']
        warning_alerts = [a for a in recent_alerts if a['severity'] == 'WARNING']
        
        if critical_alerts:
            self.system_state['health_status'] = 'CRITICAL'
        elif len(warning_alerts) >= 3:
            self.system_state['health_status'] = 'DEGRADED'
        elif warning_alerts:
            self.system_state['health_status'] = 'WARNING'
        else:
            # Check performance metrics
            avg_success_rate = self._get_average_metric('success_rate')
            if avg_success_rate and avg_success_rate > 95:
                self.system_state['health_status'] = 'HEALTHY'
            elif avg_success_rate and avg_success_rate > 80:
                self.system_state['health_status'] = 'DEGRADED'
            else:
                self.system_state['health_status'] = 'WARNING'
    
    def _get_average_metric(self, metric_name: str, minutes: int = 5) -> Optional[float]:
        """Get average value for a metric over specified minutes"""
        if metric_name not in self.performance_metrics:
            return None
        
        values = list(self.performance_metrics[metric_name])
        if not values:
            return None
        
        # For simplicity, return recent average
        recent_values = values[-min(len(values), minutes):]
        return statistics.mean(recent_values) if recent_values else None
    
    def _background_monitor(self):
        """Background monitoring thread"""
        while self.monitoring_active:
            try:
                # Record current memory usage
                memory_usage = self._get_memory_usage()
                if memory_usage:
                    self.record_memory_usage(memory_usage)
                
                # Check for inactive system
                time_since_activity = (datetime.now() - self.system_state['last_activity']).total_seconds()
                if time_since_activity > 300:  # 5 minutes
                    self._check_alerts("time_since_last_activity", time_since_activity)
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
                # Update health status
                self._update_health_status()
                
                time.sleep(30)  # Run every 30 seconds
                
            except Exception as e:
                self.logger.error(f"❌ Background monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return None
    
    def _cleanup_old_metrics(self):
        """Clean up old metric data points"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        for metric_name, metric_data in self.metrics.items():
            # Remove old data points
            while metric_data and metric_data[0].timestamp < cutoff_time:
                metric_data.popleft()
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data"""
        
        # Calculate uptime
        uptime = datetime.now() - self.system_state['start_time']
        
        # Get recent performance metrics
        performance_summary = {}
        for metric_name, values in self.performance_metrics.items():
            if values:
                performance_summary[metric_name] = {
                    'current': values[-1] if values else 0,
                    'average': statistics.mean(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0
                }
        
        # Recent alerts
        recent_alerts = [a for a in self.alerts_history 
                        if a['timestamp'] >= datetime.now() - timedelta(hours=1)]
        
        # Top error patterns
        error_patterns = {}
        for metric_data in self.metrics.values():
            for point in metric_data:
                if 'error_type' in point.tags:
                    error_type = point.tags['error_type']
                    error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
        
        return {
            'system_state': self.system_state,
            'uptime_seconds': uptime.total_seconds(),
            'performance_metrics': performance_summary,
            'recent_alerts': recent_alerts,
            'active_alert_rules': len(self.alert_rules),
            'total_metrics': sum(len(data) for data in self.metrics.values()),
            'error_patterns': dict(sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def print_status_report(self):
        """Print comprehensive status report"""
        dashboard = self.get_dashboard_data()
        
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE MONITORING REPORT")
        print("="*60)
        
        # System State
        print(f"🏥 System Health: {self.system_state['health_status']}")
        print(f"⏱️ Uptime: {timedelta(seconds=int(dashboard['uptime_seconds']))}")
        print(f"🔄 Operations Completed: {self.system_state['operations_completed']}")
        print(f"❌ Total Errors: {self.system_state['total_errors']}")
        
        # Performance Metrics
        print(f"\n📈 Performance Metrics:")
        for metric, stats in dashboard['performance_metrics'].items():
            print(f"   {metric}: {stats['current']:.2f} (avg: {stats['average']:.2f})")
        
        # Recent Alerts
        if dashboard['recent_alerts']:
            print(f"\n🚨 Recent Alerts ({len(dashboard['recent_alerts'])}):")
            for alert in dashboard['recent_alerts'][-5:]:  # Show last 5
                print(f"   {alert['timestamp'].strftime('%H:%M:%S')} [{alert['severity']}] {alert['message']}")
        
        # Error Patterns
        if dashboard['error_patterns']:
            print(f"\n🔍 Top Error Patterns:")
            for error_type, count in list(dashboard['error_patterns'].items())[:3]:
                print(f"   {error_type}: {count} occurrences")
        
        print("="*60)
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'system_state': self.system_state,
            'metrics': {},
            'alerts_history': self.alerts_history,
            'dashboard_data': self.get_dashboard_data()
        }
        
        # Convert metrics to serializable format
        for metric_name, metric_data in self.metrics.items():
            export_data['metrics'][metric_name] = [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'value': point.value,
                    'tags': point.tags
                }
                for point in list(metric_data)[-100:]  # Last 100 points per metric
            ]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 Metrics exported to {filepath}")
    
    def shutdown(self):
        """Shutdown monitoring system"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("🛑 Comprehensive Monitor shutdown")

# Context manager for operation monitoring
class OperationMonitor:
    """Context manager for monitoring operations"""
    
    def __init__(self, monitor: ComprehensiveMonitor, operation_name: str, 
                 context: Dict = None):
        self.monitor = monitor
        self.operation_name = operation_name
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.monitor.record_operation_start(self.operation_name, self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.monitor.record_operation_success(self.operation_name, duration, self.context)
        else:
            self.monitor.record_operation_failure(self.operation_name, exc_val, self.context)

# Test function
def test_comprehensive_monitor():
    """Test the comprehensive monitor"""
    print("🧪 Testing Comprehensive Monitor")
    print("=" * 50)
    
    monitor = ComprehensiveMonitor()
    
    try:
        # Simulate some operations
        with OperationMonitor(monitor, "test_collection", {"region": "gangnam"}):
            time.sleep(0.1)
            monitor.record_article_collection("12345", True, 1.2, 0.95)
            monitor.record_api_call("/api/articles/12345", 200, 0.5)
            monitor.record_database_operation("insert", True, 0.3, 1)
        
        # Simulate an error
        try:
            with OperationMonitor(monitor, "test_error", {"test": True}):
                raise Exception("Test error")
        except Exception:
            pass
        
        # Wait a bit for background monitoring
        time.sleep(2)
        
        # Print status report
        monitor.print_status_report()
        
        # Export metrics
        export_path = "/tmp/test_metrics.json"
        monitor.export_metrics(export_path)
        
        print("✅ Monitor test completed successfully")
        
    finally:
        monitor.shutdown()

if __name__ == "__main__":
    test_comprehensive_monitor()