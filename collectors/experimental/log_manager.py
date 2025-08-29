#!/usr/bin/env python3
"""
Intelligent Log Management System
Handles log rotation, compression, archival, and real-time streaming
"""

import asyncio
import gzip
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, AsyncIterator, Set
from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler
import aiofiles
import structlog

# Structured logging setup
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@dataclass
class LogRotationConfig:
    """Log rotation configuration"""
    max_file_size_mb: int = 50
    max_files_per_type: int = 10
    compression_enabled: bool = True
    cleanup_older_than_days: int = 7
    real_time_buffer_size: int = 1000


@dataclass
class LogFile:
    """Log file information"""
    path: str
    size_mb: float
    created_at: datetime
    last_modified: datetime
    line_count: int
    is_compressed: bool = False


class LogManager:
    """Advanced log management with rotation, compression, and real-time streaming"""
    
    def __init__(self, log_dir: str = "logs", config: LogRotationConfig = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.config = config or LogRotationConfig()
        self.is_running = False
        
        # Real-time log streaming
        self.log_subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.log_buffer: Dict[str, List[Dict]] = {}
        
        # File monitoring
        self.monitored_files: Dict[str, LogFile] = {}
        self.rotation_task: Optional[asyncio.Task] = None
        self.streaming_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_logs_processed': 0,
            'files_rotated': 0,
            'files_compressed': 0,
            'bytes_compressed': 0,
            'cleanup_operations': 0
        }
        
        # Setup structured logging
        self.setup_structured_logging()
    
    def setup_structured_logging(self):
        """Setup structured logging for the application"""
        # Main application log
        app_handler = RotatingFileHandler(
            self.log_dir / "application.log",
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.max_files_per_type
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Error log
        error_handler = RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.max_files_per_type
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d'
        ))
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)
    
    async def start(self):
        """Start log management services"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start background tasks
        self.rotation_task = asyncio.create_task(self._rotation_loop())
        self.streaming_task = asyncio.create_task(self._streaming_loop())
        
        # Scan existing log files
        await self._scan_log_files()
        
        logger.info("📚 Log management started", 
                   log_dir=str(self.log_dir),
                   config=self.config.__dict__)
    
    async def stop(self):
        """Stop log management services"""
        self.is_running = False
        
        # Cancel background tasks
        if self.rotation_task:
            self.rotation_task.cancel()
        if self.streaming_task:
            self.streaming_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            self.rotation_task, self.streaming_task, 
            return_exceptions=True
        )
        
        logger.info("📚 Log management stopped")
    
    async def write_structured_log(self, 
                                 log_type: str, 
                                 level: str, 
                                 message: str,
                                 task_id: Optional[str] = None,
                                 dong_name: Optional[str] = None,
                                 **kwargs):
        """Write structured log entry"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'type': log_type,
            'message': message,
            'task_id': task_id,
            'dong_name': dong_name,
            **kwargs
        }
        
        # Write to file
        log_file = self.log_dir / f"{log_type}.jsonl"
        async with aiofiles.open(log_file, 'a', encoding='utf-8') as f:
            await f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + '\n')
        
        # Add to real-time buffer
        if log_type not in self.log_buffer:
            self.log_buffer[log_type] = []
        
        self.log_buffer[log_type].append(log_entry)
        
        # Keep buffer size manageable
        if len(self.log_buffer[log_type]) > self.config.real_time_buffer_size:
            self.log_buffer[log_type] = self.log_buffer[log_type][-self.config.real_time_buffer_size:]
        
        # Notify subscribers
        await self._notify_subscribers(log_type, log_entry)
        
        self.stats['total_logs_processed'] += 1
    
    async def subscribe_to_logs(self, log_type: str) -> asyncio.Queue:
        """Subscribe to real-time log updates"""
        if log_type not in self.log_subscribers:
            self.log_subscribers[log_type] = set()
        
        queue = asyncio.Queue(maxsize=100)
        self.log_subscribers[log_type].add(queue)
        
        logger.info("📡 New log subscriber", log_type=log_type)
        return queue
    
    async def unsubscribe_from_logs(self, log_type: str, queue: asyncio.Queue):
        """Unsubscribe from log updates"""
        if log_type in self.log_subscribers:
            self.log_subscribers[log_type].discard(queue)
    
    async def get_recent_logs(self, log_type: str, limit: int = 100) -> List[Dict]:
        """Get recent logs from buffer"""
        if log_type not in self.log_buffer:
            return []
        
        return self.log_buffer[log_type][-limit:]
    
    async def search_logs(self, 
                         log_type: str,
                         query: str = None,
                         task_id: str = None,
                         level: str = None,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         limit: int = 1000) -> List[Dict]:
        """Search logs with filters"""
        results = []
        log_file = self.log_dir / f"{log_type}.jsonl"
        
        if not log_file.exists():
            return results
        
        try:
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                line_count = 0
                async for line in f:
                    if line_count >= limit:
                        break
                    
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply filters
                        if task_id and entry.get('task_id') != task_id:
                            continue
                        
                        if level and entry.get('level') != level:
                            continue
                        
                        if start_time or end_time:
                            entry_time = datetime.fromisoformat(entry['timestamp'])
                            if start_time and entry_time < start_time:
                                continue
                            if end_time and entry_time > end_time:
                                continue
                        
                        if query and query.lower() not in entry.get('message', '').lower():
                            continue
                        
                        results.append(entry)
                        line_count += 1
                        
                    except json.JSONDecodeError:
                        continue
                    
        except Exception as e:
            logger.error("🔍 Log search error", error=str(e), log_type=log_type)
        
        return list(reversed(results))  # Most recent first
    
    async def rotate_log_file(self, log_file_path: str) -> bool:
        """Rotate a specific log file"""
        try:
            log_path = Path(log_file_path)
            
            if not log_path.exists():
                return False
            
            # Check if rotation is needed
            size_mb = log_path.stat().st_size / (1024 * 1024)
            if size_mb < self.config.max_file_size_mb:
                return False
            
            # Create rotated filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            rotated_path = log_path.parent / f"{log_path.stem}_{timestamp}{log_path.suffix}"
            
            # Move current file to rotated name
            shutil.move(str(log_path), str(rotated_path))
            
            # Compress if enabled
            if self.config.compression_enabled:
                await self._compress_file(rotated_path)
            
            self.stats['files_rotated'] += 1
            logger.info("🔄 Log file rotated", 
                       original=str(log_path),
                       rotated=str(rotated_path),
                       size_mb=round(size_mb, 2))
            
            return True
            
        except Exception as e:
            logger.error("🔄 Log rotation failed", 
                        file=log_file_path, error=str(e))
            return False
    
    async def _compress_file(self, file_path: Path) -> bool:
        """Compress a log file"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original file
            original_size = file_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            file_path.unlink()
            
            self.stats['files_compressed'] += 1
            self.stats['bytes_compressed'] += original_size - compressed_size
            
            logger.info("🗜️ File compressed",
                       file=str(file_path),
                       original_size_mb=round(original_size / (1024*1024), 2),
                       compressed_size_mb=round(compressed_size / (1024*1024), 2),
                       compression_ratio=round(compression_ratio, 1))
            
            return True
            
        except Exception as e:
            logger.error("🗜️ Compression failed", 
                        file=str(file_path), error=str(e))
            return False
    
    async def cleanup_old_logs(self) -> int:
        """Clean up old log files"""
        cutoff_date = datetime.now() - timedelta(days=self.config.cleanup_older_than_days)
        cleaned_files = 0
        
        try:
            for log_file in self.log_dir.glob('**/*'):
                if not log_file.is_file():
                    continue
                
                # Check file age
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if file_mtime < cutoff_date:
                    try:
                        log_file.unlink()
                        cleaned_files += 1
                        logger.info("🗑️ Old log file removed", 
                                   file=str(log_file),
                                   age_days=(datetime.now() - file_mtime).days)
                    except Exception as e:
                        logger.error("🗑️ Failed to remove old log", 
                                   file=str(log_file), error=str(e))
            
            self.stats['cleanup_operations'] += 1
            logger.info("🧹 Log cleanup completed", removed_files=cleaned_files)
            
        except Exception as e:
            logger.error("🧹 Log cleanup failed", error=str(e))
        
        return cleaned_files
    
    async def _rotation_loop(self):
        """Background task for log rotation and cleanup"""
        while self.is_running:
            try:
                # Scan and update monitored files
                await self._scan_log_files()
                
                # Rotate files that exceed size limit
                for file_path, log_file in self.monitored_files.items():
                    if log_file.size_mb > self.config.max_file_size_mb:
                        await self.rotate_log_file(file_path)
                
                # Cleanup old files (daily)
                current_hour = datetime.now().hour
                if current_hour == 2:  # Run cleanup at 2 AM
                    await self.cleanup_old_logs()
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("🔄 Rotation loop error", error=str(e))
                await asyncio.sleep(60)
    
    async def _streaming_loop(self):
        """Background task for real-time log streaming"""
        while self.is_running:
            try:
                # Monitor log files for new entries
                await self._monitor_file_changes()
                await asyncio.sleep(1)  # Check every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("📡 Streaming loop error", error=str(e))
                await asyncio.sleep(5)
    
    async def _scan_log_files(self):
        """Scan log directory and update file information"""
        for log_file_path in self.log_dir.glob('**/*.jsonl'):
            if log_file_path.is_file():
                try:
                    stat = log_file_path.stat()
                    
                    # Count lines (approximate)
                    line_count = 0
                    try:
                        with open(log_file_path, 'r', encoding='utf-8') as f:
                            line_count = sum(1 for _ in f)
                    except:
                        line_count = 0
                    
                    log_file = LogFile(
                        path=str(log_file_path),
                        size_mb=stat.st_size / (1024 * 1024),
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        line_count=line_count,
                        is_compressed=str(log_file_path).endswith('.gz')
                    )
                    
                    self.monitored_files[str(log_file_path)] = log_file
                    
                except Exception as e:
                    logger.error("📊 File scan error", 
                               file=str(log_file_path), error=str(e))
    
    async def _monitor_file_changes(self):
        """Monitor files for changes and stream new entries"""
        # This is a simplified version - in production, use inotify or similar
        pass
    
    async def _notify_subscribers(self, log_type: str, log_entry: Dict):
        """Notify all subscribers of new log entry"""
        if log_type not in self.log_subscribers:
            return
        
        disconnected_queues = set()
        
        for queue in self.log_subscribers[log_type]:
            try:
                queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                # Remove full queues (client not consuming fast enough)
                disconnected_queues.add(queue)
            except Exception:
                disconnected_queues.add(queue)
        
        # Clean up disconnected subscribers
        self.log_subscribers[log_type] -= disconnected_queues
    
    def get_stats(self) -> Dict:
        """Get log management statistics"""
        stats = dict(self.stats)
        stats.update({
            'monitored_files': len(self.monitored_files),
            'active_subscribers': sum(len(subs) for subs in self.log_subscribers.values()),
            'buffer_size': sum(len(buf) for buf in self.log_buffer.values()),
            'total_files_size_mb': sum(lf.size_mb for lf in self.monitored_files.values())
        })
        return stats
    
    def get_file_info(self) -> List[Dict]:
        """Get information about all monitored files"""
        return [
            {
                'path': lf.path,
                'size_mb': round(lf.size_mb, 2),
                'line_count': lf.line_count,
                'created_at': lf.created_at.isoformat(),
                'last_modified': lf.last_modified.isoformat(),
                'is_compressed': lf.is_compressed
            }
            for lf in self.monitored_files.values()
        ]


# Usage examples and CLI
async def main():
    """CLI interface for log manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Log Manager CLI")
    parser.add_argument("--start", action="store_true", help="Start log management")
    parser.add_argument("--rotate", help="Rotate specific log file")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old logs")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--search", help="Search logs")
    parser.add_argument("--log-type", default="progress", help="Log type to search")
    
    args = parser.parse_args()
    
    log_manager = LogManager()
    
    if args.start:
        print("📚 Starting log manager...")
        await log_manager.start()
        
        try:
            # Example: write some test logs
            for i in range(5):
                await log_manager.write_structured_log(
                    "test", "INFO", f"Test message {i}",
                    task_id=f"test_{i}", dong_name="테스트동"
                )
                await asyncio.sleep(1)
            
            # Keep running
            await asyncio.sleep(60)
            
        except KeyboardInterrupt:
            pass
        finally:
            await log_manager.stop()
    
    elif args.rotate:
        success = await log_manager.rotate_log_file(args.rotate)
        print(f"{'✅' if success else '❌'} Rotate: {args.rotate}")
    
    elif args.cleanup:
        await log_manager.start()
        cleaned = await log_manager.cleanup_old_logs()
        print(f"🗑️ Cleaned up {cleaned} old files")
        await log_manager.stop()
    
    elif args.stats:
        await log_manager.start()
        stats = log_manager.get_stats()
        files = log_manager.get_file_info()
        
        print("📊 Log Manager Statistics:")
        print(json.dumps(stats, indent=2))
        print("\n📁 Monitored Files:")
        for file_info in files:
            print(f"  {file_info['path']}: {file_info['size_mb']}MB ({file_info['line_count']} lines)")
        
        await log_manager.stop()
    
    elif args.search:
        await log_manager.start()
        results = await log_manager.search_logs(args.log_type, query=args.search, limit=20)
        
        print(f"🔍 Search Results ({len(results)} found):")
        for entry in results:
            print(f"  {entry['timestamp']}: {entry.get('message', '')}")
        
        await log_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())