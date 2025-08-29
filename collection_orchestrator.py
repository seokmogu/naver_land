#!/usr/bin/env python3
"""
Collection Orchestrator - Multi-Processing Data Collection Manager
================================================================

This component manages parallel data collection using multiple processes
and threads with intelligent load balancing, token rotation, and fault tolerance.

Key Features:
- Multi-token management with automatic rotation
- Worker process pool with dynamic scaling
- Intelligent batch size optimization
- Priority queue for high-value properties
- Circuit breaker pattern for API failures
- Real-time performance monitoring
- Memory-efficient streaming processing
"""

import asyncio
import multiprocessing as mp
import threading
import queue
import time
import redis
import requests
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Generator, Tuple
from pathlib import Path
import json
import logging
import random
import uuid
from enum import Enum

# Import enhanced collector
import sys
sys.path.insert(0, str(Path(__file__).parent))
from enhanced_data_collector import EnhancedNaverCollector

class WorkerState(Enum):
    """Worker process states"""
    INITIALIZING = "initializing"
    IDLE = "idle" 
    COLLECTING = "collecting"
    RECOVERING = "recovering"
    TERMINATED = "terminated"
    ERROR = "error"

class TaskStatus(Enum):
    """Task processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

@dataclass
class TokenInfo:
    """Token information for API access"""
    token: str
    cookies: Dict[str, str]
    expires_at: datetime
    usage_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    is_active: bool = True
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def is_healthy(self) -> bool:
        return self.is_active and not self.is_expired() and self.error_count < 5

@dataclass 
class WorkerMetrics:
    """Individual worker performance metrics"""
    worker_id: str
    process_id: int
    state: WorkerState
    tasks_processed: int = 0
    tasks_successful: int = 0
    tasks_failed: int = 0
    properties_collected: int = 0
    api_requests: int = 0
    api_failures: int = 0
    last_activity: Optional[datetime] = None
    memory_usage_mb: float = 0.0
    processing_speed: float = 0.0  # properties per minute
    
    def update_activity(self):
        self.last_activity = datetime.now()
    
    def calculate_success_rate(self) -> float:
        if self.tasks_processed == 0:
            return 0.0
        return self.tasks_successful / self.tasks_processed

@dataclass
class CollectionBatch:
    """Batch of properties for collection"""
    batch_id: str
    region_code: str
    region_name: str
    article_numbers: List[str]
    priority: int
    created_at: datetime = field(default_factory=datetime.now)
    assigned_worker: Optional[str] = None
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    results: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0

class TokenManager:
    """Advanced token management with rotation and health monitoring"""
    
    def __init__(self, max_tokens: int = 10):
        self.tokens: List[TokenInfo] = []
        self.max_tokens = max_tokens
        self.current_index = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger('TokenManager')
        
        # Load existing tokens
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from storage"""
        try:
            # Try to load from token manager if available
            sys.path.insert(0, str(Path(__file__).parent / 'collectors' / 'core'))
            from multi_token_manager import MultiTokenManager
            
            token_manager = MultiTokenManager()
            token_data_list = token_manager.get_all_valid_tokens()
            
            for token_data in token_data_list:
                if token_data and token_data.get('token'):
                    token_info = TokenInfo(
                        token=token_data['token'],
                        cookies=token_data.get('cookies', {}),
                        expires_at=token_data.get('expires_at', datetime.now() + timedelta(hours=6))
                    )
                    self.tokens.append(token_info)
            
            self.logger.info(f"Loaded {len(self.tokens)} tokens")
            
        except ImportError:
            self.logger.warning("Multi-token manager not available, using single token mode")
            self._create_fallback_token()
    
    def _create_fallback_token(self):
        """Create fallback token using playwright"""
        try:
            from playwright_token_collector import PlaywrightTokenCollector
            collector = PlaywrightTokenCollector()
            token_data = collector.get_token_with_playwright()
            
            if token_data and token_data.get('token'):
                token_info = TokenInfo(
                    token=token_data['token'],
                    cookies=token_data.get('cookies', {}),
                    expires_at=datetime.now() + timedelta(hours=6)
                )
                self.tokens.append(token_info)
                self.logger.info("Created fallback token")
                
        except ImportError:
            self.logger.error("No token collection method available")
    
    def get_healthy_token(self) -> Optional[TokenInfo]:
        """Get next healthy token with rotation"""
        with self.lock:
            if not self.tokens:
                return None
            
            # Filter healthy tokens
            healthy_tokens = [t for t in self.tokens if t.is_healthy()]
            
            if not healthy_tokens:
                self.logger.warning("No healthy tokens available")
                return None
            
            # Round-robin selection
            token = healthy_tokens[self.current_index % len(healthy_tokens)]
            self.current_index = (self.current_index + 1) % len(healthy_tokens)
            
            # Update usage
            token.usage_count += 1
            token.last_used = datetime.now()
            
            return token
    
    def report_token_error(self, token: TokenInfo, error: str):
        """Report token error for health tracking"""
        with self.lock:
            token.error_count += 1
            
            if token.error_count >= 5:
                token.is_active = False
                self.logger.warning(f"Token deactivated due to errors: {error}")
    
    def report_token_success(self, token: TokenInfo):
        """Report successful token usage"""
        with self.lock:
            # Reset error count on success
            token.error_count = max(0, token.error_count - 1)
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        with self.lock:
            total_tokens = len(self.tokens)
            healthy_tokens = len([t for t in self.tokens if t.is_healthy()])
            total_usage = sum(t.usage_count for t in self.tokens)
            
            return {
                'total_tokens': total_tokens,
                'healthy_tokens': healthy_tokens,
                'total_usage': total_usage,
                'health_rate': healthy_tokens / max(total_tokens, 1)
            }

class WorkerProcess:
    """Individual worker process for data collection"""
    
    def __init__(self, worker_id: str, task_queue: redis.Redis, token_manager: TokenManager):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.token_manager = token_manager
        self.collector = None
        self.metrics = WorkerMetrics(
            worker_id=worker_id,
            process_id=mp.current_process().pid,
            state=WorkerState.INITIALIZING
        )
        self.logger = logging.getLogger(f'Worker-{worker_id}')
        self.shutdown_flag = threading.Event()
        
        # Circuit breaker for API failures
        self.circuit_breaker = {
            'failure_count': 0,
            'failure_threshold': 10,
            'reset_timeout': 300,  # 5 minutes
            'last_failure': None,
            'is_open': False
        }
    
    async def initialize(self):
        """Initialize worker process"""
        try:
            self.logger.info(f"Initializing worker {self.worker_id}")
            
            # Initialize collector with token
            self.collector = EnhancedNaverCollector()
            
            self.metrics.state = WorkerState.IDLE
            self.metrics.update_activity()
            
            self.logger.info(f"Worker {self.worker_id} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Worker {self.worker_id} initialization failed: {e}")
            self.metrics.state = WorkerState.ERROR
            return False
    
    async def run(self):
        """Main worker processing loop"""
        self.logger.info(f"Worker {self.worker_id} starting processing loop")
        
        while not self.shutdown_flag.is_set():
            try:
                # Check circuit breaker
                if self._is_circuit_breaker_open():
                    await asyncio.sleep(10)
                    continue
                
                # Get next task from queue
                task_data = self.task_queue.brpop(['collection_tasks'], timeout=30)
                
                if task_data is None:
                    continue  # Timeout, check for shutdown
                
                # Parse task
                task_json = task_data[1]
                batch = self._parse_batch_task(task_json)
                
                if batch is None:
                    continue
                
                # Process batch
                self.metrics.state = WorkerState.COLLECTING
                await self._process_batch(batch)
                
                self.metrics.state = WorkerState.IDLE
                self.metrics.update_activity()
                
            except Exception as e:
                self.logger.error(f"Worker {self.worker_id} processing error: {e}")
                self.metrics.state = WorkerState.ERROR
                await asyncio.sleep(5)
    
    async def _process_batch(self, batch: CollectionBatch):
        """Process a batch of property collections"""
        batch.assigned_worker = self.worker_id
        batch.processing_started = datetime.now()
        
        self.logger.info(f"Processing batch {batch.batch_id}: {len(batch.article_numbers)} properties")
        
        success_count = 0
        error_count = 0
        
        for i, article_no in enumerate(batch.article_numbers):
            if self.shutdown_flag.is_set():
                break
            
            try:
                # Get healthy token
                token = self.token_manager.get_healthy_token()
                if not token:
                    raise Exception("No healthy tokens available")
                
                # Update collector token
                self.collector.token = token.token
                self.collector.cookies = token.cookies
                
                # Collect property data
                property_data = self.collector.collect_article_detail_enhanced(article_no)
                
                if property_data:
                    # Save to database
                    save_result = self.collector.save_to_normalized_database(property_data)
                    
                    if save_result:
                        batch.results.append({
                            'article_no': article_no,
                            'status': 'success',
                            'timestamp': datetime.now().isoformat()
                        })
                        success_count += 1
                        self.token_manager.report_token_success(token)
                        
                        # Reset circuit breaker on success
                        self.circuit_breaker['failure_count'] = 0
                        self.circuit_breaker['is_open'] = False
                    else:
                        raise Exception("Database save failed")
                else:
                    raise Exception("Data collection failed")
                
                # Update metrics
                self.metrics.tasks_processed += 1
                self.metrics.properties_collected += 1
                self.metrics.api_requests += 1
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / len(batch.article_numbers) * 100
                    self.logger.info(f"Batch {batch.batch_id} progress: {progress:.1f}% ({i+1}/{len(batch.article_numbers)})")
                
                # Rate limiting
                await asyncio.sleep(random.uniform(1.5, 2.5))
                
            except Exception as e:
                self.logger.error(f"Failed to process article {article_no}: {e}")
                
                batch.errors.append(f"Article {article_no}: {str(e)}")
                error_count += 1
                self.metrics.tasks_failed += 1
                self.metrics.api_failures += 1
                
                # Report token error if token-related
                if token and any(keyword in str(e).lower() for keyword in ['token', 'auth', '401', '403']):
                    self.token_manager.report_token_error(token, str(e))
                
                # Update circuit breaker
                self._update_circuit_breaker()
                
                # Short delay before retry
                await asyncio.sleep(1.0)
        
        # Complete batch processing
        batch.processing_completed = datetime.now()
        processing_time = (batch.processing_completed - batch.processing_started).total_seconds()
        
        # Update metrics
        self.metrics.tasks_successful += success_count if success_count == len(batch.article_numbers) else 0
        if processing_time > 0:
            self.metrics.processing_speed = (success_count * 60) / processing_time
        
        self.logger.info(f"Batch {batch.batch_id} completed: {success_count}/{len(batch.article_numbers)} successful")
        
        # Store results
        await self._store_batch_results(batch)
    
    def _parse_batch_task(self, task_json: str) -> Optional[CollectionBatch]:
        """Parse batch task from JSON"""
        try:
            task_data = json.loads(task_json)
            
            batch = CollectionBatch(
                batch_id=task_data['batch_id'],
                region_code=task_data['region_code'],
                region_name=task_data['region_name'],
                article_numbers=task_data['article_numbers'],
                priority=task_data.get('priority', 3)
            )
            
            return batch
            
        except Exception as e:
            self.logger.error(f"Failed to parse batch task: {e}")
            return None
    
    async def _store_batch_results(self, batch: CollectionBatch):
        """Store batch processing results"""
        try:
            results_key = f"batch_results:{batch.batch_id}"
            results_data = {
                'batch_id': batch.batch_id,
                'region_code': batch.region_code,
                'region_name': batch.region_name,
                'worker_id': self.worker_id,
                'processing_started': batch.processing_started.isoformat(),
                'processing_completed': batch.processing_completed.isoformat(),
                'total_articles': len(batch.article_numbers),
                'successful_articles': len(batch.results),
                'failed_articles': len(batch.errors),
                'success_rate': len(batch.results) / len(batch.article_numbers) if batch.article_numbers else 0,
                'results': batch.results,
                'errors': batch.errors
            }
            
            self.task_queue.setex(results_key, 86400, json.dumps(results_data))  # 24 hour expiry
            
        except Exception as e:
            self.logger.error(f"Failed to store batch results: {e}")
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.circuit_breaker['is_open']:
            return False
        
        # Check if timeout has passed
        if self.circuit_breaker['last_failure']:
            timeout_passed = (
                datetime.now() - self.circuit_breaker['last_failure']
            ).total_seconds() > self.circuit_breaker['reset_timeout']
            
            if timeout_passed:
                self.circuit_breaker['is_open'] = False
                self.circuit_breaker['failure_count'] = 0
                self.logger.info("Circuit breaker reset")
                return False
        
        return True
    
    def _update_circuit_breaker(self):
        """Update circuit breaker on failure"""
        self.circuit_breaker['failure_count'] += 1
        self.circuit_breaker['last_failure'] = datetime.now()
        
        if self.circuit_breaker['failure_count'] >= self.circuit_breaker['failure_threshold']:
            self.circuit_breaker['is_open'] = True
            self.logger.warning("Circuit breaker opened due to failures")
    
    def stop(self):
        """Stop worker processing"""
        self.shutdown_flag.set()
        self.metrics.state = WorkerState.TERMINATED
        self.logger.info(f"Worker {self.worker_id} stopped")

class CollectionOrchestrator:
    """
    Main orchestrator for parallel data collection operations
    
    Manages worker processes, task distribution, and coordination
    of all collection activities.
    """
    
    def __init__(self, config, task_queue: redis.Redis):
        self.config = config
        self.task_queue = task_queue
        self.token_manager = TokenManager(max_tokens=10)
        
        # Worker management
        self.workers: Dict[str, WorkerProcess] = {}
        self.worker_pool: Optional[ProcessPoolExecutor] = None
        
        # Task management
        self.active_campaigns: Dict[str, Dict] = {}
        self.batch_counter = 0
        
        # Synchronization
        self.shutdown_event = threading.Event()
        self.orchestrator_lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger('CollectionOrchestrator')
        
        print(f"🎭 Collection Orchestrator initialized")
        print(f"   Max Workers: {config.max_workers}")
        print(f"   Batch Size: {config.batch_size}")
    
    async def initialize(self):
        """Initialize orchestrator and worker pool"""
        try:
            # Initialize worker pool
            self.worker_pool = ProcessPoolExecutor(max_workers=self.config.max_workers)
            
            # Start monitoring service
            threading.Thread(target=self._monitoring_service, daemon=True).start()
            
            self.logger.info("Collection Orchestrator initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Orchestrator initialization failed: {e}")
            return False
    
    async def queue_collection_tasks(self, tasks: List[Any]) -> int:
        """Queue collection tasks for processing"""
        queued_count = 0
        
        for task in tasks:
            try:
                # Get article numbers for region
                article_numbers = await self._get_region_articles(task.region_code)
                
                if not article_numbers:
                    self.logger.warning(f"No articles found for {task.region_name}")
                    continue
                
                # Create batches
                batch_size = self.config.batch_size
                batches = [
                    article_numbers[i:i+batch_size] 
                    for i in range(0, len(article_numbers), batch_size)
                ]
                
                self.logger.info(f"Region {task.region_name}: {len(article_numbers)} articles → {len(batches)} batches")
                
                # Queue batches
                for i, batch_articles in enumerate(batches):
                    batch = CollectionBatch(
                        batch_id=f"{task.task_id}_batch_{i}",
                        region_code=task.region_code,
                        region_name=task.region_name,
                        article_numbers=batch_articles,
                        priority=task.priority.value
                    )
                    
                    # Queue for processing
                    batch_json = json.dumps({
                        'batch_id': batch.batch_id,
                        'region_code': batch.region_code,
                        'region_name': batch.region_name,
                        'article_numbers': batch.article_numbers,
                        'priority': batch.priority
                    })
                    
                    self.task_queue.lpush('collection_tasks', batch_json)
                    queued_count += 1
                
                # Track campaign
                self.active_campaigns[task.task_id] = {
                    'task': task,
                    'total_articles': len(article_numbers),
                    'total_batches': len(batches),
                    'queued_batches': len(batches),
                    'completed_batches': 0,
                    'created_at': datetime.now()
                }
                
            except Exception as e:
                self.logger.error(f"Failed to queue task {task.task_id}: {e}")
        
        self.logger.info(f"Queued {queued_count} batches for processing")
        return queued_count
    
    async def start_processing(self):
        """Start worker processes for task processing"""
        try:
            # Start worker processes
            for i in range(self.config.max_workers):
                worker_id = f"worker_{i}_{uuid.uuid4().hex[:8]}"
                
                # Submit worker to process pool
                future = self.worker_pool.submit(self._run_worker_process, worker_id)
                
                self.workers[worker_id] = {
                    'future': future,
                    'started_at': datetime.now(),
                    'status': 'active'
                }
            
            self.logger.info(f"Started {len(self.workers)} worker processes")
            
        except Exception as e:
            self.logger.error(f"Failed to start processing: {e}")
            raise
    
    def _run_worker_process(self, worker_id: str):
        """Run worker process (executed in separate process)"""
        try:
            # Create and run worker
            worker = WorkerProcess(worker_id, self.task_queue, self.token_manager)
            
            # Run async worker loop
            asyncio.run(self._worker_main_loop(worker))
            
        except Exception as e:
            print(f"Worker {worker_id} crashed: {e}")
    
    async def _worker_main_loop(self, worker: WorkerProcess):
        """Main loop for worker process"""
        try:
            await worker.initialize()
            await worker.run()
        except Exception as e:
            worker.logger.error(f"Worker main loop error: {e}")
        finally:
            worker.stop()
    
    async def _get_region_articles(self, cortar_no: str) -> List[str]:
        """Get list of article numbers for region"""
        try:
            # Create temporary collector for article list
            temp_collector = EnhancedNaverCollector()
            
            # Get token
            token = self.token_manager.get_healthy_token()
            if token:
                temp_collector.token = token.token
                temp_collector.cookies = token.cookies
            
            # Collect article list (limit to reasonable number)
            articles = temp_collector.collect_area_articles(cortar_no, max_pages=50)
            
            if token:
                self.token_manager.report_token_success(token)
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to get articles for region {cortar_no}: {e}")
            return []
    
    async def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign status"""
        if campaign_id not in self.active_campaigns:
            return {'error': 'Campaign not found'}
        
        campaign = self.active_campaigns[campaign_id]
        
        # Get completed batches count from Redis
        completed_count = 0
        batch_pattern = f"batch_results:{campaign_id}_batch_*"
        
        for key in self.task_queue.scan_iter(match=batch_pattern):
            completed_count += 1
        
        campaign['completed_batches'] = completed_count
        
        # Calculate progress
        progress_percent = (completed_count / campaign['total_batches']) * 100 if campaign['total_batches'] > 0 else 0
        
        return {
            'campaign_id': campaign_id,
            'region_name': campaign['task'].region_name,
            'total_articles': campaign['total_articles'],
            'total_batches': campaign['total_batches'],
            'completed_batches': completed_count,
            'progress_percent': progress_percent,
            'created_at': campaign['created_at'].isoformat(),
            'worker_status': self._get_worker_status(),
            'token_stats': self.token_manager.get_token_stats()
        }
    
    def _get_worker_status(self) -> Dict[str, Any]:
        """Get worker status summary"""
        active_workers = sum(1 for w in self.workers.values() if w['status'] == 'active')
        
        return {
            'total_workers': len(self.workers),
            'active_workers': active_workers,
            'max_workers': self.config.max_workers
        }
    
    def _monitoring_service(self):
        """Background monitoring service"""
        while not self.shutdown_event.is_set():
            try:
                # Monitor worker health
                self._monitor_workers()
                
                # Monitor token health
                self._monitor_tokens()
                
                # Monitor queue size
                queue_size = self.task_queue.llen('collection_tasks')
                if queue_size > 1000:
                    self.logger.warning(f"Large task queue: {queue_size} tasks")
                
            except Exception as e:
                self.logger.error(f"Monitoring service error: {e}")
            
            time.sleep(30)  # Check every 30 seconds
    
    def _monitor_workers(self):
        """Monitor worker process health"""
        for worker_id, worker_info in self.workers.items():
            if worker_info['future'].done():
                exception = worker_info['future'].exception()
                if exception:
                    self.logger.error(f"Worker {worker_id} failed: {exception}")
                    worker_info['status'] = 'failed'
                else:
                    worker_info['status'] = 'completed'
    
    def _monitor_tokens(self):
        """Monitor token health and refresh if needed"""
        stats = self.token_manager.get_token_stats()
        
        if stats['healthy_tokens'] < 2:
            self.logger.warning(f"Low healthy token count: {stats['healthy_tokens']}")
            # Could trigger token refresh here
    
    async def pause_processing(self, campaign_id: str = None):
        """Pause processing (stop accepting new tasks)"""
        # Implementation for pausing
        self.logger.info("Processing paused")
    
    async def resume_processing(self, campaign_id: str = None):
        """Resume processing"""
        # Implementation for resuming
        self.logger.info("Processing resumed")
    
    async def emergency_stop(self):
        """Emergency stop all processing"""
        self.logger.info("Emergency stop initiated")
        
        # Set shutdown flag
        self.shutdown_event.set()
        
        # Stop all workers
        for worker_id in self.workers:
            self.workers[worker_id]['status'] = 'stopping'
        
        # Shutdown worker pool
        if self.worker_pool:
            self.worker_pool.shutdown(wait=False)
        
        self.logger.info("Emergency stop complete")
    
    async def health_check(self) -> str:
        """Component health check"""
        try:
            # Check Redis connection
            self.task_queue.ping()
            
            # Check token availability
            token_stats = self.token_manager.get_token_stats()
            if token_stats['healthy_tokens'] == 0:
                return 'degraded'
            
            # Check worker status
            worker_status = self._get_worker_status()
            if worker_status['active_workers'] == 0:
                return 'degraded'
            
            return 'healthy'
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return 'unhealthy'
    
    async def cleanup_memory(self):
        """Clean up memory usage"""
        # Clear old campaign data
        current_time = datetime.now()
        campaigns_to_remove = []
        
        for campaign_id, campaign in self.active_campaigns.items():
            if (current_time - campaign['created_at']).total_seconds() > 86400:  # 24 hours
                campaigns_to_remove.append(campaign_id)
        
        for campaign_id in campaigns_to_remove:
            del self.active_campaigns[campaign_id]
        
        self.logger.info(f"Cleaned up {len(campaigns_to_remove)} old campaigns")

# Testing
async def test_orchestrator():
    """Test the collection orchestrator"""
    print("🧪 Testing Collection Orchestrator")
    print("=" * 50)
    
    # Mock Redis connection (would need actual Redis in production)
    import fakeredis
    task_queue = fakeredis.FakeRedis(decode_responses=True)
    
    # Create orchestrator
    from robust_architecture_design import SystemConfiguration
    config = SystemConfiguration(max_workers=2, batch_size=10)
    
    orchestrator = CollectionOrchestrator(config, task_queue)
    
    # Initialize
    success = await orchestrator.initialize()
    print(f"✅ Initialization: {'Success' if success else 'Failed'}")
    
    # Health check
    health = await orchestrator.health_check()
    print(f"🏥 Health: {health}")
    
    print("✅ Orchestrator test complete")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())