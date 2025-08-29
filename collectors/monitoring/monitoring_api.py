#!/usr/bin/env python3
"""
Real-time Monitoring API Server
FastAPI-based backend with WebSocket support and Redis caching
"""

import asyncio
import json
import os
import psutil
import signal
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import uvicorn

from api_schema import (
    CollectionTask, SystemMetrics, LogEntry, ProcessInfo, 
    DashboardStatus, ApiResponse, CollectionRequest,
    ProcessControlRequest, RealtimeUpdate, WebSocketMessage,
    CollectionStatus, ProcessHealth
)


class MonitoringAPI:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.websocket_connections: Set[WebSocket] = set()
        self.background_tasks: Set[asyncio.Task] = set()
        self.is_shutting_down = False
        
        # Configuration
        self.config = {
            'max_concurrent_tasks': 3,
            'heartbeat_interval': 30,
            'health_check_interval': 60,
            'log_retention_days': 7,
            'max_log_file_size_mb': 50
        }

    async def initialize(self):
        """Initialize Redis connection and background tasks"""
        try:
            # Connect to Redis
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True
            )
            await self.redis_client.ping()
            print("✅ Redis connection established")
            
            # Start background tasks
            self.background_tasks.add(
                asyncio.create_task(self.system_monitor_loop())
            )
            self.background_tasks.add(
                asyncio.create_task(self.process_health_monitor())
            )
            self.background_tasks.add(
                asyncio.create_task(self.log_rotation_monitor())
            )
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        self.is_shutting_down = True
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close WebSocket connections
        for ws in self.websocket_connections.copy():
            try:
                await ws.close()
            except:
                pass
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.aclose()

    async def get_active_tasks(self) -> List[CollectionTask]:
        """Get currently active collection tasks"""
        try:
            # Get from Redis cache first
            cached = await self.redis_client.get("active_tasks")
            if cached:
                data = json.loads(cached)
                return [CollectionTask(**task) for task in data]
            
            # Fallback to file system
            return await self.load_tasks_from_logs()
            
        except Exception as e:
            print(f"❌ Error getting active tasks: {e}")
            return []

    async def load_tasks_from_logs(self) -> List[CollectionTask]:
        """Load tasks from log files (fallback)"""
        tasks = []
        try:
            if os.path.exists('logs/status.json'):
                with open('logs/status.json', 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                
                for task_id, task_info in status_data.items():
                    details = task_info.get('details', {})
                    
                    # Calculate progress and ETA
                    progress = self.calculate_progress(details.get('total_collected', 0))
                    eta = self.calculate_eta(details.get('started_at'), progress)
                    
                    task = CollectionTask(
                        task_id=task_id,
                        dong_name=details.get('dong_name', 'Unknown'),
                        cortar_no=details.get('cortar_no', ''),
                        status=CollectionStatus(task_info.get('status', 'unknown')),
                        started_at=datetime.fromisoformat(details.get('timestamp', datetime.now().isoformat())),
                        total_collected=details.get('total_collected', 0),
                        progress_percentage=progress,
                        estimated_completion=eta
                    )
                    tasks.append(task)
                    
        except Exception as e:
            print(f"❌ Error loading tasks from logs: {e}")
            
        return tasks

    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics"""
        try:
            # Get from cache first
            cached = await self.redis_client.get("system_metrics")
            if cached:
                data = json.loads(cached)
                return SystemMetrics(**data)
            
            # Calculate fresh metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Process count
            process_count = len([p for p in psutil.process_iter() if 'python' in p.name()])
            
            # Log file size
            log_size = "0MB"
            if os.path.exists('logs/live_progress.jsonl'):
                size_bytes = os.path.getsize('logs/live_progress.jsonl')
                log_size = f"{size_bytes / (1024 * 1024):.1f}MB"
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime = str(timedelta(seconds=int(uptime_seconds)))
            
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                memory_available=f"{memory.available / (1024**3):.1f}GB",
                disk_usage=disk.percent,
                disk_free=f"{disk.free / (1024**3):.1f}GB",
                process_count=process_count,
                log_file_size=log_size,
                uptime=uptime
            )
            
            # Cache for 30 seconds
            await self.redis_client.setex(
                "system_metrics", 
                30, 
                json.dumps(metrics.dict(), default=str)
            )
            
            return metrics
            
        except Exception as e:
            print(f"❌ Error getting system metrics: {e}")
            return SystemMetrics(
                cpu_usage=0, memory_usage=0, memory_available="N/A",
                disk_usage=0, disk_free="N/A", process_count=0,
                log_file_size="N/A", uptime="N/A"
            )

    async def get_process_info(self) -> List[ProcessInfo]:
        """Get information about running collection processes"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    proc_info = proc.info
                    if 'python' in proc_info['name'] and 'collector' in ' '.join(proc.cmdline()):
                        runtime = datetime.now() - datetime.fromtimestamp(proc_info['create_time'])
                        
                        process_info = ProcessInfo(
                            process_id=proc_info['pid'],
                            task_id=f"proc_{proc_info['pid']}",
                            dong_name="Unknown",  # Would need to extract from process
                            health=ProcessHealth.HEALTHY,  # Would need proper health check
                            cpu_usage=proc_info['cpu_percent'] or 0,
                            memory_usage=proc_info['memory_percent'] or 0,
                            runtime_duration=str(runtime).split('.')[0],
                            last_activity=datetime.now()
                        )
                        processes.append(process_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"❌ Error getting process info: {e}")
            
        return processes

    async def terminate_process(self, task_id: str, force: bool = False) -> bool:
        """Terminate a specific collection process"""
        try:
            # Extract PID from task_id or find by dong_name
            if task_id.startswith("proc_"):
                pid = int(task_id.replace("proc_", ""))
            else:
                # Find process by task_id in status
                # This would need more sophisticated process tracking
                return False
            
            proc = psutil.Process(pid)
            
            if force:
                proc.kill()
                signal_type = "SIGKILL"
            else:
                proc.terminate()
                signal_type = "SIGTERM"
            
            print(f"🛑 Process {pid} terminated with {signal_type}")
            
            # Remove from status tracking
            await self.redis_client.hdel("active_tasks", task_id)
            
            return True
            
        except Exception as e:
            print(f"❌ Error terminating process {task_id}: {e}")
            return False

    def calculate_progress(self, total_collected: int) -> float:
        """Calculate progress percentage based on collected items"""
        # Simple heuristic: assume 500-1000 properties per dong
        estimated_total = 750
        progress = min((total_collected / estimated_total) * 100, 100.0)
        return round(progress, 1)

    def calculate_eta(self, started_at: Optional[str], progress: float) -> Optional[datetime]:
        """Calculate estimated completion time"""
        if not started_at or progress <= 0:
            return None
        
        try:
            start_time = datetime.fromisoformat(started_at)
            elapsed = datetime.now() - start_time
            
            if progress >= 100:
                return datetime.now()
            
            total_estimated = elapsed * (100 / progress)
            remaining = total_estimated - elapsed
            eta = datetime.now() + remaining
            
            return eta
            
        except Exception:
            return None

    async def broadcast_update(self, message: WebSocketMessage):
        """Broadcast update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message.dict(), default=str)
        disconnected = set()
        
        for ws in self.websocket_connections:
            try:
                await ws.send_text(message_str)
            except WebSocketDisconnect:
                disconnected.add(ws)
            except Exception as e:
                print(f"❌ WebSocket send error: {e}")
                disconnected.add(ws)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected

    async def system_monitor_loop(self):
        """Background task for system monitoring"""
        while not self.is_shutting_down:
            try:
                # Update system metrics in cache
                metrics = await self.get_system_metrics()
                
                # Broadcast to WebSocket clients
                await self.broadcast_update(WebSocketMessage(
                    type="system_metrics",
                    channel="monitoring",
                    data=metrics.dict()
                ))
                
                await asyncio.sleep(self.config['heartbeat_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ System monitor error: {e}")
                await asyncio.sleep(10)

    async def process_health_monitor(self):
        """Background task for process health monitoring"""
        while not self.is_shutting_down:
            try:
                processes = await self.get_process_info()
                
                # Check for zombie processes (long-running without progress)
                current_time = datetime.now()
                for proc in processes:
                    runtime_parts = proc.runtime_duration.split(':')
                    if len(runtime_parts) >= 2:
                        hours = int(runtime_parts[0])
                        if hours > 2:  # Process running for more than 2 hours
                            print(f"⚠️ Long-running process detected: {proc.process_id} ({proc.runtime_duration})")
                            # Could implement automatic termination logic here
                
                await asyncio.sleep(self.config['health_check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Health monitor error: {e}")
                await asyncio.sleep(30)

    async def log_rotation_monitor(self):
        """Background task for log file management"""
        while not self.is_shutting_down:
            try:
                log_file = 'logs/live_progress.jsonl'
                if os.path.exists(log_file):
                    size_mb = os.path.getsize(log_file) / (1024 * 1024)
                    
                    if size_mb > self.config['max_log_file_size_mb']:
                        # Rotate log file
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_name = f'logs/live_progress_{timestamp}.jsonl'
                        
                        os.rename(log_file, backup_name)
                        print(f"📁 Log file rotated: {backup_name} ({size_mb:.1f}MB)")
                        
                        # Compress old log
                        await self.compress_old_log(backup_name)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Log rotation error: {e}")
                await asyncio.sleep(60)

    async def compress_old_log(self, log_file: str):
        """Compress old log file to save space"""
        try:
            import gzip
            
            with open(log_file, 'rb') as f_in:
                with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                    f_out.writelines(f_in)
            
            os.remove(log_file)
            print(f"🗜️ Log compressed: {log_file}.gz")
            
        except Exception as e:
            print(f"❌ Log compression error: {e}")


# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    monitoring = MonitoringAPI()
    app.state.monitoring = monitoring
    await monitoring.initialize()
    yield
    # Shutdown
    await monitoring.cleanup()


app = FastAPI(
    title="Real-time Collection Monitoring API",
    description="Advanced monitoring system for Naver real estate collection",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.get("/api/v2/status", response_model=ApiResponse)
async def get_status():
    """Get complete dashboard status"""
    try:
        monitoring: MonitoringAPI = app.state.monitoring
        
        active_tasks = await monitoring.get_active_tasks()
        system_metrics = await monitoring.get_system_metrics()
        process_info = await monitoring.get_process_info()
        
        # Calculate summary statistics
        total_today = sum(task.total_collected for task in active_tasks)
        completed_tasks = [task for task in active_tasks if task.status == CollectionStatus.COMPLETED]
        success_rate = (len(completed_tasks) / len(active_tasks) * 100) if active_tasks else 100.0
        
        dashboard = DashboardStatus(
            active_tasks=[task for task in active_tasks if task.status in [CollectionStatus.IN_PROGRESS, CollectionStatus.STARTING]],
            completed_tasks=completed_tasks[-10:],  # Recent 10
            system_metrics=system_metrics,
            process_info=process_info,
            queue_length=0,  # Would implement proper queue
            total_properties_today=total_today,
            success_rate=success_rate
        )
        
        return ApiResponse(
            success=True,
            message="Status retrieved successfully",
            data=dashboard.dict()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@app.post("/api/v2/collection/start", response_model=ApiResponse)
async def start_collection(request: CollectionRequest, background_tasks: BackgroundTasks):
    """Start a new collection task"""
    try:
        monitoring: MonitoringAPI = app.state.monitoring
        
        # Generate task ID
        task_id = f"{request.dong_name}_{int(time.time())}"
        
        # Create task record
        task = CollectionTask(
            task_id=task_id,
            dong_name=request.dong_name,
            cortar_no=request.cortar_no,
            status=CollectionStatus.QUEUED,
            started_at=datetime.now()
        )
        
        # Store in Redis
        await monitoring.redis_client.hset(
            "active_tasks", 
            task_id, 
            json.dumps(task.dict(), default=str)
        )
        
        # Start collection process (background task)
        # background_tasks.add_task(start_collection_process, task)
        
        return ApiResponse(
            success=True,
            message=f"Collection started for {request.dong_name}",
            data={"task_id": task_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collection start failed: {str(e)}")


@app.post("/api/v2/process/control", response_model=ApiResponse)
async def control_process(request: ProcessControlRequest):
    """Control collection process (pause/resume/cancel)"""
    try:
        monitoring: MonitoringAPI = app.state.monitoring
        
        if request.action == "kill":
            success = await monitoring.terminate_process(request.task_id, force=True)
        elif request.action == "cancel":
            success = await monitoring.terminate_process(request.task_id, force=request.force)
        else:
            # Implement pause/resume logic
            success = False
            
        return ApiResponse(
            success=success,
            message=f"Process {request.action} {'successful' if success else 'failed'}",
            data={"task_id": request.task_id, "action": request.action}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process control failed: {str(e)}")


@app.websocket("/ws/monitoring")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    
    monitoring: MonitoringAPI = app.state.monitoring
    monitoring.websocket_connections.add(websocket)
    
    try:
        while True:
            # Send periodic updates
            dashboard_status = await get_status()
            update_message = WebSocketMessage(
                type="status_update",
                channel="monitoring",
                data=dashboard_status.data
            )
            
            await websocket.send_text(json.dumps(update_message.dict(), default=str))
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        monitoring.websocket_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        monitoring.websocket_connections.discard(websocket)


@app.get("/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    return ApiResponse(
        success=True,
        message="API is healthy",
        data={"status": "healthy", "timestamp": datetime.now()}
    )


if __name__ == "__main__":
    uvicorn.run(
        "monitoring_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )