#!/usr/bin/env python3
"""
Real-time Monitoring API Schema
FastAPI-based REST API with WebSocket support
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class CollectionStatus(str, Enum):
    """Collection status enumeration"""
    QUEUED = "queued"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ProcessHealth(str, Enum):
    """Process health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"


# API Response Models
class CollectionTask(BaseModel):
    """Collection task data model"""
    task_id: str = Field(..., description="Unique task identifier")
    dong_name: str = Field(..., description="District name")
    cortar_no: str = Field(..., description="Administrative code")
    status: CollectionStatus = Field(..., description="Current status")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    total_collected: int = Field(0, description="Number of properties collected")
    progress_percentage: float = Field(0.0, description="Progress percentage (0-100)")
    estimated_completion: Optional[datetime] = Field(None, description="ETA")
    error_message: Optional[str] = Field(None, description="Error details")
    process_id: Optional[int] = Field(None, description="System process ID")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SystemMetrics(BaseModel):
    """System performance metrics"""
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    memory_available: str = Field(..., description="Available memory")
    disk_usage: float = Field(..., description="Disk usage percentage")
    disk_free: str = Field(..., description="Free disk space")
    process_count: int = Field(..., description="Active process count")
    log_file_size: str = Field(..., description="Current log file size")
    uptime: str = Field(..., description="System uptime")
    
    class Config:
        schema_extra = {
            "example": {
                "cpu_usage": 25.3,
                "memory_usage": 68.1,
                "memory_available": "2.4GB",
                "disk_usage": 45.2,
                "disk_free": "15.8GB",
                "process_count": 3,
                "log_file_size": "1.2MB",
                "uptime": "2h 15m"
            }
        }


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: datetime = Field(..., description="Log entry timestamp")
    level: str = Field(..., description="Log level (INFO, ERROR, etc.)")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    dong_name: Optional[str] = Field(None, description="District name")
    message: str = Field(..., description="Log message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProcessInfo(BaseModel):
    """Process monitoring information"""
    process_id: int = Field(..., description="System process ID")
    task_id: str = Field(..., description="Associated task ID")
    dong_name: str = Field(..., description="District being processed")
    health: ProcessHealth = Field(..., description="Process health status")
    cpu_usage: float = Field(..., description="Process CPU usage")
    memory_usage: float = Field(..., description="Process memory usage")
    runtime_duration: str = Field(..., description="How long process has been running")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# API Request Models
class CollectionRequest(BaseModel):
    """Collection request payload"""
    dong_name: str = Field(..., description="District name to collect")
    cortar_no: str = Field(..., description="Administrative code")
    max_workers: int = Field(1, ge=1, le=5, description="Maximum parallel workers")
    timeout_minutes: int = Field(60, ge=5, le=300, description="Timeout in minutes")
    priority: int = Field(5, ge=1, le=10, description="Task priority (1=highest)")


class ProcessControlRequest(BaseModel):
    """Process control request"""
    action: str = Field(..., regex="^(pause|resume|cancel|kill)$")
    task_id: Optional[str] = Field(None, description="Specific task ID")
    force: bool = Field(False, description="Force action even if risky")


# API Response Wrappers
class ApiResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DashboardStatus(BaseModel):
    """Complete dashboard status"""
    active_tasks: List[CollectionTask] = Field(..., description="Currently active tasks")
    completed_tasks: List[CollectionTask] = Field(..., description="Recently completed tasks")
    system_metrics: SystemMetrics = Field(..., description="System performance metrics")
    process_info: List[ProcessInfo] = Field(..., description="Process monitoring data")
    queue_length: int = Field(..., description="Pending tasks in queue")
    total_properties_today: int = Field(..., description="Properties collected today")
    success_rate: float = Field(..., description="Success rate percentage")
    
    class Config:
        schema_extra = {
            "example": {
                "active_tasks": [],
                "completed_tasks": [],
                "system_metrics": {},
                "process_info": [],
                "queue_length": 0,
                "total_properties_today": 1250,
                "success_rate": 95.2
            }
        }


# WebSocket Models
class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: str = Field(..., description="Message type")
    channel: str = Field(..., description="Channel name")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RealtimeUpdate(BaseModel):
    """Real-time status update"""
    task_id: str = Field(..., description="Task identifier")
    dong_name: str = Field(..., description="District name")
    status: CollectionStatus = Field(..., description="Current status")
    total_collected: int = Field(..., description="Properties collected so far")
    progress_percentage: float = Field(..., description="Progress percentage")
    estimated_completion: Optional[datetime] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Error Models
class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    task_id: Optional[str] = Field(None, description="Related task ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Configuration Models  
class SystemConfig(BaseModel):
    """System configuration"""
    max_concurrent_tasks: int = Field(3, ge=1, le=10)
    default_timeout_minutes: int = Field(60, ge=5, le=300)
    log_retention_days: int = Field(7, ge=1, le=30)
    heartbeat_interval_seconds: int = Field(30, ge=5, le=300)
    health_check_interval_seconds: int = Field(60, ge=10, le=600)
    max_log_file_size_mb: int = Field(50, ge=1, le=500)
    websocket_keepalive_seconds: int = Field(30, ge=10, le=300)