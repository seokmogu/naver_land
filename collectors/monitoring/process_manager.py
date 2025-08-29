#!/usr/bin/env python3
"""
Advanced Process Manager
Handles process lifecycle, health monitoring, and zombie detection
"""

import asyncio
import json
import os
import signal
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"


@dataclass
class ProcessInfo:
    """Process information and health data"""
    task_id: str
    dong_name: str
    process_id: int
    status: ProcessStatus
    health: HealthStatus
    
    # Timing
    started_at: datetime
    last_activity: datetime
    runtime_seconds: int
    
    # Resource usage
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    
    # Health indicators
    heartbeat_count: int
    consecutive_failures: int
    total_collected: int
    
    # Process details
    command_line: str
    working_directory: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['status'] = self.status.value
        data['health'] = self.health.value
        return data


class ProcessManager:
    """Advanced process manager with health monitoring and lifecycle management"""
    
    def __init__(self, config: Dict = None):
        self.processes: Dict[str, ProcessInfo] = {}
        self.config = config or {
            'health_check_interval': 30,    # seconds
            'heartbeat_timeout': 120,       # seconds
            'max_runtime_hours': 6,         # hours
            'cpu_threshold': 80.0,          # percentage
            'memory_threshold': 1024,       # MB
            'max_consecutive_failures': 3,
            'zombie_detection_enabled': True,
            'auto_cleanup_enabled': True
        }
        
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_processes': 0,
            'completed_processes': 0,
            'failed_processes': 0,
            'killed_processes': 0,
            'total_runtime_hours': 0.0
        }
    
    async def start_monitoring(self):
        """Start the process monitoring loop"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🔍 Process monitoring started")
    
    async def stop_monitoring(self):
        """Stop process monitoring"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Process monitoring stopped")
    
    def register_process(self, task_id: str, dong_name: str, pid: int) -> bool:
        """Register a new process for monitoring"""
        try:
            proc = psutil.Process(pid)
            
            process_info = ProcessInfo(
                task_id=task_id,
                dong_name=dong_name,
                process_id=pid,
                status=ProcessStatus.STARTING,
                health=HealthStatus.HEALTHY,
                started_at=datetime.now(),
                last_activity=datetime.now(),
                runtime_seconds=0,
                cpu_percent=0.0,
                memory_mb=0.0,
                memory_percent=0.0,
                heartbeat_count=0,
                consecutive_failures=0,
                total_collected=0,
                command_line=' '.join(proc.cmdline()) if proc.cmdline() else '',
                working_directory=proc.cwd() if proc.is_running() else ''
            )
            
            self.processes[task_id] = process_info
            self.stats['total_processes'] += 1
            
            logger.info(f"📋 Process registered: {task_id} (PID: {pid})")
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"❌ Failed to register process {task_id} (PID: {pid}): {e}")
            return False
    
    def update_process_progress(self, task_id: str, total_collected: int) -> bool:
        """Update process progress information"""
        if task_id not in self.processes:
            return False
        
        process_info = self.processes[task_id]
        process_info.total_collected = total_collected
        process_info.last_activity = datetime.now()
        process_info.heartbeat_count += 1
        process_info.consecutive_failures = 0  # Reset failure count on successful update
        
        # Update status to running if it was starting
        if process_info.status == ProcessStatus.STARTING:
            process_info.status = ProcessStatus.RUNNING
        
        return True
    
    def mark_process_completed(self, task_id: str, success: bool = True):
        """Mark a process as completed"""
        if task_id not in self.processes:
            return
        
        process_info = self.processes[task_id]
        process_info.status = ProcessStatus.COMPLETED if success else ProcessStatus.FAILED
        process_info.last_activity = datetime.now()
        
        # Update statistics
        if success:
            self.stats['completed_processes'] += 1
        else:
            self.stats['failed_processes'] += 1
        
        # Calculate total runtime
        runtime_hours = process_info.runtime_seconds / 3600.0
        self.stats['total_runtime_hours'] += runtime_hours
        
        logger.info(f"✅ Process marked as {'completed' if success else 'failed'}: {task_id}")
    
    async def terminate_process(self, task_id: str, force: bool = False) -> bool:
        """Terminate a specific process"""
        if task_id not in self.processes:
            logger.warning(f"⚠️ Process not found for termination: {task_id}")
            return False
        
        process_info = self.processes[task_id]
        
        try:
            proc = psutil.Process(process_info.process_id)
            
            if not proc.is_running():
                logger.info(f"💀 Process already dead: {task_id}")
                process_info.status = ProcessStatus.KILLED
                return True
            
            if force:
                proc.kill()  # SIGKILL
                signal_type = "SIGKILL"
            else:
                proc.terminate()  # SIGTERM
                signal_type = "SIGTERM"
            
            # Wait for process to die
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                if not force:
                    # Escalate to SIGKILL
                    proc.kill()
                    signal_type = "SIGKILL (escalated)"
                    proc.wait(timeout=5)
            
            process_info.status = ProcessStatus.KILLED
            process_info.last_activity = datetime.now()
            self.stats['killed_processes'] += 1
            
            logger.info(f"🔫 Process terminated: {task_id} (PID: {process_info.process_id}) with {signal_type}")
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"❌ Failed to terminate process {task_id}: {e}")
            return False
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._check_process_health()
                await self._detect_zombies()
                await self._cleanup_dead_processes()
                
                await asyncio.sleep(self.config['health_check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    async def _check_process_health(self):
        """Check health of all registered processes"""
        current_time = datetime.now()
        
        for task_id, process_info in self.processes.items():
            if process_info.status not in [ProcessStatus.RUNNING, ProcessStatus.STARTING]:
                continue
            
            try:
                # Check if process still exists
                proc = psutil.Process(process_info.process_id)
                
                if not proc.is_running():
                    logger.warning(f"💀 Process died unexpectedly: {task_id}")
                    process_info.status = ProcessStatus.FAILED
                    process_info.health = HealthStatus.DEAD
                    continue
                
                # Update resource usage
                process_info.cpu_percent = proc.cpu_percent()
                memory_info = proc.memory_info()
                process_info.memory_mb = memory_info.rss / (1024 * 1024)
                process_info.memory_percent = proc.memory_percent()
                
                # Update runtime
                process_info.runtime_seconds = int((current_time - process_info.started_at).total_seconds())
                
                # Check heartbeat timeout
                time_since_activity = (current_time - process_info.last_activity).total_seconds()
                heartbeat_timeout = self.config['heartbeat_timeout']
                
                if time_since_activity > heartbeat_timeout:
                    process_info.consecutive_failures += 1
                    logger.warning(f"💔 Heartbeat timeout for {task_id}: {time_since_activity:.0f}s")
                    
                    if process_info.consecutive_failures >= self.config['max_consecutive_failures']:
                        process_info.health = HealthStatus.UNHEALTHY
                        logger.error(f"🚨 Process marked unhealthy: {task_id}")
                
                # Check resource usage
                health_issues = []
                
                if process_info.cpu_percent > self.config['cpu_threshold']:
                    health_issues.append(f"High CPU: {process_info.cpu_percent:.1f}%")
                
                if process_info.memory_mb > self.config['memory_threshold']:
                    health_issues.append(f"High Memory: {process_info.memory_mb:.0f}MB")
                
                # Check maximum runtime
                max_runtime_seconds = self.config['max_runtime_hours'] * 3600
                if process_info.runtime_seconds > max_runtime_seconds:
                    health_issues.append(f"Long runtime: {process_info.runtime_seconds / 3600:.1f}h")
                
                # Update health status
                if health_issues:
                    if process_info.health == HealthStatus.HEALTHY:
                        process_info.health = HealthStatus.DEGRADED
                        logger.warning(f"⚠️ Process health degraded: {task_id} - {', '.join(health_issues)}")
                    elif process_info.health == HealthStatus.DEGRADED and len(health_issues) > 2:
                        process_info.health = HealthStatus.UNHEALTHY
                        logger.error(f"🚨 Process health critical: {task_id} - {', '.join(health_issues)}")
                else:
                    # Recover health if no issues
                    if process_info.health in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                        process_info.health = HealthStatus.HEALTHY
                        logger.info(f"💚 Process health recovered: {task_id}")
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.warning(f"💀 Process no longer exists: {task_id}")
                process_info.status = ProcessStatus.FAILED
                process_info.health = HealthStatus.DEAD
            except Exception as e:
                logger.error(f"❌ Health check error for {task_id}: {e}")
                process_info.consecutive_failures += 1
    
    async def _detect_zombies(self):
        """Detect and handle zombie processes"""
        if not self.config['zombie_detection_enabled']:
            return
        
        current_time = datetime.now()
        max_runtime = timedelta(hours=self.config['max_runtime_hours'])
        
        for task_id, process_info in self.processes.items():
            if process_info.status != ProcessStatus.RUNNING:
                continue
            
            runtime = current_time - process_info.started_at
            time_since_activity = current_time - process_info.last_activity
            
            # Zombie detection criteria
            is_zombie = (
                runtime > max_runtime or  # Running too long
                time_since_activity > timedelta(minutes=30) or  # No activity
                (process_info.total_collected == 0 and runtime > timedelta(minutes=10)) or  # No progress
                process_info.health == HealthStatus.UNHEALTHY
            )
            
            if is_zombie:
                logger.warning(f"🧟 Zombie process detected: {task_id} (Runtime: {runtime}, Last activity: {time_since_activity})")
                
                if self.config['auto_cleanup_enabled']:
                    logger.info(f"🧹 Auto-terminating zombie process: {task_id}")
                    await self.terminate_process(task_id, force=True)
    
    async def _cleanup_dead_processes(self):
        """Remove dead processes from tracking"""
        dead_tasks = []
        
        for task_id, process_info in self.processes.items():
            if process_info.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.KILLED]:
                # Keep for 1 hour for debugging, then remove
                if (datetime.now() - process_info.last_activity) > timedelta(hours=1):
                    dead_tasks.append(task_id)
        
        for task_id in dead_tasks:
            del self.processes[task_id]
            logger.info(f"🗑️ Cleaned up dead process: {task_id}")
    
    def get_active_processes(self) -> List[Dict]:
        """Get list of active processes"""
        active = []
        for process_info in self.processes.values():
            if process_info.status in [ProcessStatus.STARTING, ProcessStatus.RUNNING]:
                active.append(process_info.to_dict())
        return active
    
    def get_process_summary(self) -> Dict:
        """Get summary statistics"""
        summary = dict(self.stats)
        
        # Current status counts
        status_counts = {}
        health_counts = {}
        
        for process_info in self.processes.values():
            status = process_info.status.value
            health = process_info.health.value
            
            status_counts[status] = status_counts.get(status, 0) + 1
            health_counts[health] = health_counts.get(health, 0) + 1
        
        summary.update({
            'current_processes': len(self.processes),
            'status_breakdown': status_counts,
            'health_breakdown': health_counts,
            'avg_runtime_hours': summary['total_runtime_hours'] / max(summary['total_processes'], 1),
            'success_rate': (summary['completed_processes'] / max(summary['total_processes'], 1)) * 100
        })
        
        return summary
    
    def get_long_running_processes(self, hours_threshold: int = 2) -> List[Dict]:
        """Get processes running longer than threshold"""
        long_running = []
        threshold_seconds = hours_threshold * 3600
        
        for process_info in self.processes.values():
            if (process_info.status in [ProcessStatus.RUNNING, ProcessStatus.STARTING] and 
                process_info.runtime_seconds > threshold_seconds):
                data = process_info.to_dict()
                data['runtime_hours'] = process_info.runtime_seconds / 3600.0
                long_running.append(data)
        
        return sorted(long_running, key=lambda x: x['runtime_seconds'], reverse=True)
    
    async def emergency_shutdown(self):
        """Emergency shutdown - terminate all processes"""
        logger.warning("🚨 Emergency shutdown initiated")
        
        tasks = []
        for task_id in list(self.processes.keys()):
            tasks.append(self.terminate_process(task_id, force=True))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        await self.stop_monitoring()
        logger.info("🛑 Emergency shutdown completed")


# CLI interface for process management
async def main():
    """CLI interface for process manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process Manager CLI")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring mode")
    parser.add_argument("--status", action="store_true", help="Show process status")
    parser.add_argument("--kill", help="Kill process by task_id")
    parser.add_argument("--kill-all", action="store_true", help="Kill all processes")
    parser.add_argument("--zombies", action="store_true", help="Show zombie processes")
    
    args = parser.parse_args()
    
    pm = ProcessManager()
    
    if args.monitor:
        print("🔍 Starting process monitor...")
        await pm.start_monitoring()
        try:
            while True:
                await asyncio.sleep(60)
                summary = pm.get_process_summary()
                print(f"📊 Active: {summary['current_processes']}, "
                      f"Success Rate: {summary['success_rate']:.1f}%")
        except KeyboardInterrupt:
            await pm.stop_monitoring()
    
    elif args.status:
        active = pm.get_active_processes()
        summary = pm.get_process_summary()
        
        print("📋 Process Status:")
        print(json.dumps(summary, indent=2))
        print("\n🔄 Active Processes:")
        for proc in active:
            print(f"  {proc['task_id']}: {proc['status']} ({proc['runtime_seconds']}s)")
    
    elif args.kill:
        success = await pm.terminate_process(args.kill)
        print(f"{'✅' if success else '❌'} Kill process: {args.kill}")
    
    elif args.kill_all:
        await pm.emergency_shutdown()
        print("🛑 All processes terminated")
    
    elif args.zombies:
        zombies = pm.get_long_running_processes(hours_threshold=1)
        print("🧟 Long-running processes:")
        for proc in zombies:
            print(f"  {proc['task_id']}: {proc['runtime_hours']:.1f}h, {proc['total_collected']} items")


if __name__ == "__main__":
    asyncio.run(main())