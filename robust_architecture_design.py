#!/usr/bin/env python3
"""
Robust, Scalable Architecture for Naver Real Estate Data Collection System
===========================================================================

This is the main architectural blueprint that orchestrates all components
for high-performance, fault-tolerant data collection with comprehensive monitoring.

Architecture Overview:
- Multi-processing worker pools for parallel collection
- Distributed task queue system with Redis backend
- Real-time monitoring and alerting
- Automatic error recovery and retry mechanisms
- Database connection pooling and transaction management
- Token rotation and rate limiting
- Comprehensive logging and performance tracking

Performance Targets:
- 10x speed improvement: 100 → 1000+ properties/hour
- 99.9% uptime with automatic failover
- 90% automated error recovery
- Real-time monitoring and alerting
"""

import asyncio
import multiprocessing as mp
import queue
import threading
import time
import redis
import psutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Generator, Tuple
from contextlib import asynccontextmanager
from pathlib import Path
import json
import logging
from enum import Enum

# Import our modular components
from collection_orchestrator import CollectionOrchestrator
from monitoring_dashboard import MonitoringDashboard  
from error_recovery_system import ErrorRecoverySystem
from scalability_framework import ScalabilityFramework

class SystemState(Enum):
    """System operational states"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    COLLECTING = "collecting"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"
    ERROR = "error"

class Priority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class SystemConfiguration:
    """Comprehensive system configuration"""
    # Performance Settings
    max_workers: int = mp.cpu_count() * 2
    max_threads_per_worker: int = 4
    batch_size: int = 50
    queue_timeout: int = 300
    
    # Rate Limiting
    requests_per_second: int = 10
    burst_capacity: int = 20
    token_rotation_interval: int = 3600  # 1 hour
    
    # Error Handling
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 10
    recovery_timeout: int = 1800  # 30 minutes
    
    # Monitoring
    health_check_interval: int = 30
    metrics_retention_days: int = 30
    alert_threshold_error_rate: float = 0.05  # 5%
    
    # Database
    connection_pool_size: int = 20
    db_timeout: int = 30
    transaction_timeout: int = 120
    
    # Memory Management
    memory_limit_gb: float = 8.0
    gc_interval: int = 300  # 5 minutes
    
    # Storage
    backup_retention_days: int = 7
    log_rotation_size_mb: int = 100

@dataclass
class CollectionTask:
    """Individual collection task definition"""
    task_id: str
    region_code: str
    region_name: str
    priority: Priority
    max_pages: Optional[int] = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'region_code': self.region_code,
            'region_name': self.region_name,
            'priority': self.priority.value,
            'max_pages': self.max_pages,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'worker_id': self.worker_id
        }

@dataclass
class SystemMetrics:
    """Real-time system performance metrics"""
    # Collection Performance
    properties_collected: int = 0
    properties_per_minute: float = 0.0
    collections_successful: int = 0
    collections_failed: int = 0
    
    # System Resources
    cpu_usage_percent: float = 0.0
    memory_usage_gb: float = 0.0
    disk_usage_percent: float = 0.0
    active_workers: int = 0
    
    # API Performance  
    api_requests_total: int = 0
    api_requests_successful: int = 0
    api_response_time_ms: float = 0.0
    api_rate_limit_hits: int = 0
    
    # Error Tracking
    error_rate: float = 0.0
    recovery_attempts: int = 0
    recovery_success_rate: float = 0.0
    
    # Database Performance
    db_connections_active: int = 0
    db_queries_per_second: float = 0.0
    db_transaction_success_rate: float = 0.0
    
    # Timestamp
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self):
        self.last_updated = datetime.now()

class RobustDataCollectionArchitecture:
    """
    Main orchestrator for the robust data collection system.
    
    This class coordinates all subsystems and provides the main API
    for controlling the data collection pipeline.
    """
    
    def __init__(self, config: SystemConfiguration = None):
        """Initialize the robust collection architecture"""
        self.config = config or SystemConfiguration()
        self.state = SystemState.INITIALIZING
        self.metrics = SystemMetrics()
        
        # Core Components
        self.orchestrator: Optional[CollectionOrchestrator] = None
        self.monitor: Optional[MonitoringDashboard] = None  
        self.recovery_system: Optional[ErrorRecoverySystem] = None
        self.scalability: Optional[ScalabilityFramework] = None
        
        # Task Management
        self.task_queue: Optional[redis.Redis] = None
        self.active_tasks: Dict[str, CollectionTask] = {}
        self.completed_tasks: List[CollectionTask] = []
        self.failed_tasks: List[CollectionTask] = []
        
        # Worker Management
        self.worker_pool: Optional[ProcessPoolExecutor] = None
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        self.worker_registry: Dict[str, Dict] = {}
        
        # Synchronization
        self.shutdown_event = threading.Event()
        self.metrics_lock = threading.Lock()
        self.task_lock = threading.Lock()
        
        # Setup logging
        self._setup_logging()
        
        print(f"🚀 Robust Data Collection Architecture initializing...")
        print(f"   Max Workers: {self.config.max_workers}")
        print(f"   Batch Size: {self.config.batch_size}")
        print(f"   Memory Limit: {self.config.memory_limit_gb}GB")
    
    async def initialize(self) -> bool:
        """
        Initialize all system components
        
        Returns:
            bool: True if initialization successful
        """
        try:
            print("🔧 Initializing system components...")
            
            # 1. Initialize Redis for task queue
            self.task_queue = redis.Redis(
                host='localhost', 
                port=6379, 
                decode_responses=True,
                socket_timeout=self.config.db_timeout
            )
            
            # Test Redis connection
            self.task_queue.ping()
            print("✅ Redis task queue connected")
            
            # 2. Initialize Collection Orchestrator
            self.orchestrator = CollectionOrchestrator(
                config=self.config,
                task_queue=self.task_queue
            )
            await self.orchestrator.initialize()
            print("✅ Collection Orchestrator initialized")
            
            # 3. Initialize Monitoring Dashboard
            self.monitor = MonitoringDashboard(
                config=self.config,
                metrics=self.metrics
            )
            await self.monitor.initialize()
            print("✅ Monitoring Dashboard initialized")
            
            # 4. Initialize Error Recovery System
            self.recovery_system = ErrorRecoverySystem(
                config=self.config,
                task_queue=self.task_queue
            )
            await self.recovery_system.initialize()
            print("✅ Error Recovery System initialized")
            
            # 5. Initialize Scalability Framework
            self.scalability = ScalabilityFramework(
                config=self.config
            )
            await self.scalability.initialize()
            print("✅ Scalability Framework initialized")
            
            # 6. Initialize Worker Pools
            self.worker_pool = ProcessPoolExecutor(
                max_workers=self.config.max_workers
            )
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.config.max_workers * self.config.max_threads_per_worker
            )
            print(f"✅ Worker pools initialized ({self.config.max_workers} processes)")
            
            # 7. Start background services
            await self._start_background_services()
            
            self.state = SystemState.IDLE
            print("🎉 System initialization complete!")
            return True
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            self.state = SystemState.ERROR
            return False
    
    async def start_collection_campaign(
        self, 
        regions: List[Dict[str, str]], 
        priority: Priority = Priority.NORMAL
    ) -> str:
        """
        Start a comprehensive data collection campaign
        
        Args:
            regions: List of regions to collect (format: [{"name": "역삼동", "cortar_no": "..."}])
            priority: Task priority level
            
        Returns:
            str: Campaign ID for tracking
        """
        if self.state != SystemState.IDLE:
            raise RuntimeError(f"System not ready for collection (state: {self.state.value})")
        
        campaign_id = f"campaign_{int(time.time())}"
        print(f"🚀 Starting collection campaign: {campaign_id}")
        print(f"   Regions: {len(regions)}")
        print(f"   Priority: {priority.name}")
        
        self.state = SystemState.COLLECTING
        
        try:
            # Create collection tasks for each region
            tasks = []
            for region in regions:
                task = CollectionTask(
                    task_id=f"{campaign_id}_{region['cortar_no']}",
                    region_code=region['cortar_no'],
                    region_name=region['name'],
                    priority=priority
                )
                tasks.append(task)
            
            # Queue tasks for processing
            queued_count = await self.orchestrator.queue_collection_tasks(tasks)
            print(f"✅ {queued_count} tasks queued for processing")
            
            # Start processing
            await self.orchestrator.start_processing()
            
            return campaign_id
            
        except Exception as e:
            print(f"❌ Failed to start collection campaign: {e}")
            self.state = SystemState.ERROR
            raise
    
    async def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a collection campaign
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Dict: Comprehensive campaign status
        """
        return await self.orchestrator.get_campaign_status(campaign_id)
    
    async def pause_collection(self, campaign_id: str = None):
        """Pause collection (specific campaign or all)"""
        await self.orchestrator.pause_processing(campaign_id)
        self.state = SystemState.IDLE
        print("⏸️ Collection paused")
    
    async def resume_collection(self, campaign_id: str = None):
        """Resume paused collection"""
        await self.orchestrator.resume_processing(campaign_id)
        self.state = SystemState.COLLECTING
        print("▶️ Collection resumed")
    
    async def emergency_stop(self):
        """Emergency stop all operations"""
        print("🛑 EMERGENCY STOP - Shutting down all operations...")
        
        self.state = SystemState.SHUTDOWN
        self.shutdown_event.set()
        
        # Stop all processing
        if self.orchestrator:
            await self.orchestrator.emergency_stop()
        
        # Close worker pools
        if self.worker_pool:
            self.worker_pool.shutdown(wait=False)
        if self.thread_pool:
            self.thread_pool.shutdown(wait=False)
        
        print("✅ Emergency stop complete")
    
    async def run_health_check(self) -> Dict[str, Any]:
        """
        Comprehensive system health check
        
        Returns:
            Dict: Health status of all components
        """
        health = {
            'system_state': self.state.value,
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'metrics': self.metrics.__dict__.copy(),
            'overall_health': 'unknown'
        }
        
        try:
            # Check each component
            if self.orchestrator:
                health['components']['orchestrator'] = await self.orchestrator.health_check()
            
            if self.monitor:
                health['components']['monitor'] = await self.monitor.health_check()
            
            if self.recovery_system:
                health['components']['recovery'] = await self.recovery_system.health_check()
            
            if self.scalability:
                health['components']['scalability'] = await self.scalability.health_check()
            
            # Check Redis connection
            try:
                self.task_queue.ping()
                health['components']['redis'] = 'healthy'
            except:
                health['components']['redis'] = 'unhealthy'
            
            # Check system resources
            health['system_resources'] = self._get_system_resources()
            
            # Determine overall health
            component_health = list(health['components'].values())
            if all(status == 'healthy' for status in component_health):
                health['overall_health'] = 'healthy'
            elif any(status == 'unhealthy' for status in component_health):
                health['overall_health'] = 'degraded'
            else:
                health['overall_health'] = 'critical'
            
            return health
            
        except Exception as e:
            health['error'] = str(e)
            health['overall_health'] = 'critical'
            return health
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return {
            'metrics': self.metrics.__dict__.copy(),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'worker_status': self._get_worker_status(),
            'system_resources': self._get_system_resources(),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _start_background_services(self):
        """Start background monitoring and maintenance services"""
        
        # Metrics collection service
        self.thread_pool.submit(self._metrics_collection_service)
        
        # Health monitoring service  
        self.thread_pool.submit(self._health_monitoring_service)
        
        # Memory management service
        self.thread_pool.submit(self._memory_management_service)
        
        # Error recovery service
        self.thread_pool.submit(self._error_recovery_service)
        
        print("✅ Background services started")
    
    def _metrics_collection_service(self):
        """Background service for collecting system metrics"""
        while not self.shutdown_event.is_set():
            try:
                with self.metrics_lock:
                    # Update system metrics
                    self.metrics.cpu_usage_percent = psutil.cpu_percent()
                    self.metrics.memory_usage_gb = psutil.virtual_memory().used / (1024**3)
                    self.metrics.disk_usage_percent = psutil.disk_usage('/').percent
                    self.metrics.active_workers = len([w for w in self.worker_registry.values() if w['status'] == 'active'])
                    self.metrics.update_timestamp()
                
                # Update dashboard
                if self.monitor:
                    asyncio.create_task(self.monitor.update_metrics(self.metrics))
                
            except Exception as e:
                print(f"⚠️ Metrics collection error: {e}")
            
            time.sleep(self.config.health_check_interval)
    
    def _health_monitoring_service(self):
        """Background service for health monitoring and alerting"""
        while not self.shutdown_event.is_set():
            try:
                # Run health check
                health = asyncio.run(self.run_health_check())
                
                # Check for alerts
                if health['overall_health'] == 'critical':
                    asyncio.create_task(self._trigger_alert('CRITICAL', 'System health is critical'))
                elif health['overall_health'] == 'degraded':
                    asyncio.create_task(self._trigger_alert('WARNING', 'System health is degraded'))
                
                # Check error rate
                if self.metrics.error_rate > self.config.alert_threshold_error_rate:
                    asyncio.create_task(self._trigger_alert('WARNING', f'Error rate high: {self.metrics.error_rate:.2%}'))
                
            except Exception as e:
                print(f"⚠️ Health monitoring error: {e}")
            
            time.sleep(self.config.health_check_interval)
    
    def _memory_management_service(self):
        """Background service for memory management"""
        while not self.shutdown_event.is_set():
            try:
                # Check memory usage
                memory_gb = psutil.virtual_memory().used / (1024**3)
                
                if memory_gb > self.config.memory_limit_gb:
                    print(f"⚠️ Memory usage high: {memory_gb:.1f}GB")
                    
                    # Trigger garbage collection
                    import gc
                    gc.collect()
                    
                    # If still high, trigger emergency memory cleanup
                    if psutil.virtual_memory().used / (1024**3) > self.config.memory_limit_gb:
                        asyncio.create_task(self._emergency_memory_cleanup())
                
            except Exception as e:
                print(f"⚠️ Memory management error: {e}")
            
            time.sleep(self.config.gc_interval)
    
    def _error_recovery_service(self):
        """Background service for automatic error recovery"""
        while not self.shutdown_event.is_set():
            try:
                if self.recovery_system:
                    asyncio.create_task(self.recovery_system.run_recovery_cycle())
                
            except Exception as e:
                print(f"⚠️ Error recovery service error: {e}")
            
            time.sleep(60)  # Check every minute
    
    async def _trigger_alert(self, level: str, message: str):
        """Trigger system alert"""
        alert = {
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'system_state': self.state.value,
            'metrics_snapshot': self.metrics.__dict__.copy()
        }
        
        if self.monitor:
            await self.monitor.send_alert(alert)
        
        print(f"🚨 ALERT [{level}]: {message}")
    
    async def _emergency_memory_cleanup(self):
        """Emergency memory cleanup procedures"""
        print("🧹 Running emergency memory cleanup...")
        
        # Clear completed task history
        if len(self.completed_tasks) > 100:
            self.completed_tasks = self.completed_tasks[-50:]
        
        # Clear failed task history  
        if len(self.failed_tasks) > 100:
            self.failed_tasks = self.failed_tasks[-50:]
        
        # Request cleanup from components
        if self.orchestrator:
            await self.orchestrator.cleanup_memory()
        
        import gc
        gc.collect()
        
        print("✅ Emergency memory cleanup complete")
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_gb': psutil.virtual_memory().used / (1024**3),
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    
    def _get_worker_status(self) -> Dict[str, Any]:
        """Get worker pool status"""
        return {
            'process_pool_active': len(self.worker_registry),
            'thread_pool_active': self.thread_pool._threads if self.thread_pool else 0,
            'max_workers': self.config.max_workers
        }
    
    def _setup_logging(self):
        """Setup comprehensive logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/architecture_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('RobustArchitecture')

# Example usage and testing
async def main():
    """Example usage of the robust architecture"""
    print("🧪 Testing Robust Data Collection Architecture")
    print("=" * 60)
    
    # Initialize system
    config = SystemConfiguration(
        max_workers=4,
        batch_size=25,
        requests_per_second=8
    )
    
    architecture = RobustDataCollectionArchitecture(config)
    
    # Initialize all components
    success = await architecture.initialize()
    if not success:
        print("❌ Failed to initialize system")
        return
    
    # Run health check
    health = await architecture.run_health_check()
    print(f"🏥 System Health: {health['overall_health']}")
    
    # Test collection (with sample regions)
    test_regions = [
        {"name": "역삼동", "cortar_no": "1168010100"},
        {"name": "삼성동", "cortar_no": "1168010500"}
    ]
    
    try:
        campaign_id = await architecture.start_collection_campaign(
            regions=test_regions,
            priority=Priority.HIGH
        )
        
        print(f"✅ Collection campaign started: {campaign_id}")
        
        # Monitor progress for 30 seconds
        for i in range(6):
            await asyncio.sleep(5)
            status = await architecture.get_campaign_status(campaign_id)
            print(f"📊 Progress: {status.get('progress', 'Unknown')}")
        
        # Get performance report
        report = await architecture.get_performance_report()
        print(f"📈 Performance Report: {json.dumps(report, indent=2, default=str)}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        await architecture.emergency_stop()

if __name__ == "__main__":
    asyncio.run(main())