#!/usr/bin/env python3
"""
Advanced Error Recovery System for Robust Data Collection
=========================================================

This component provides comprehensive error handling, automatic recovery,
and resilience mechanisms for the data collection system.

Key Features:
- Intelligent error classification and handling
- Automatic retry with exponential backoff
- Circuit breaker pattern for API failures
- Data reconciliation and consistency checks
- Checkpoint and resume capabilities
- Transaction rollback and recovery
- Manual override mechanisms for critical failures
"""

import asyncio
import time
import json
import redis
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import hashlib
import pickle
from pathlib import Path

class ErrorType(Enum):
    """Classification of different error types"""
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    API_AUTH_ERROR = "api_auth_error"
    API_SERVER_ERROR = "api_server_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    PARSING_ERROR = "parsing_error"
    VALIDATION_ERROR = "validation_error"
    MEMORY_ERROR = "memory_error"
    DISK_ERROR = "disk_error"
    TOKEN_ERROR = "token_error"
    UNKNOWN_ERROR = "unknown_error"

class RecoveryAction(Enum):
    """Types of recovery actions"""
    RETRY = "retry"
    WAIT_AND_RETRY = "wait_and_retry"
    SKIP = "skip"
    CIRCUIT_BREAK = "circuit_break"
    MANUAL_INTERVENTION = "manual_intervention"
    ESCALATE = "escalate"
    RESTART_WORKER = "restart_worker"
    RESTART_SYSTEM = "restart_system"

@dataclass
class ErrorInstance:
    """Individual error instance with context"""
    id: str
    error_type: ErrorType
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    source: str  # worker_id, component name, etc.
    stack_trace: Optional[str] = None
    recovery_action: Optional[RecoveryAction] = None
    retry_count: int = 0
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    resolution_method: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'error_type': self.error_type.value,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'stack_trace': self.stack_trace,
            'recovery_action': self.recovery_action.value if self.recovery_action else None,
            'retry_count': self.retry_count,
            'resolved': self.resolved,
            'resolution_timestamp': self.resolution_timestamp.isoformat() if self.resolution_timestamp else None,
            'resolution_method': self.resolution_method
        }

@dataclass
class RecoveryStrategy:
    """Recovery strategy for specific error types"""
    error_type: ErrorType
    max_retries: int
    retry_delays: List[float]  # Exponential backoff delays
    circuit_breaker_threshold: int
    recovery_actions: List[RecoveryAction]
    timeout_seconds: int
    escalation_threshold: int  # Number of failures before escalation
    
    def get_retry_delay(self, attempt: int) -> float:
        """Get delay for specific retry attempt"""
        if attempt >= len(self.retry_delays):
            return self.retry_delays[-1]  # Use last delay for subsequent attempts
        return self.retry_delays[attempt]

@dataclass
class Checkpoint:
    """System checkpoint for recovery purposes"""
    checkpoint_id: str
    timestamp: datetime
    system_state: Dict[str, Any]
    active_tasks: List[Dict]
    completed_tasks: int
    failed_tasks: int
    metrics_snapshot: Dict[str, Any]
    file_path: Optional[str] = None
    
    def save_to_file(self, base_path: str):
        """Save checkpoint to file"""
        checkpoint_file = Path(base_path) / f"checkpoint_{self.checkpoint_id}.pkl"
        
        with open(checkpoint_file, 'wb') as f:
            pickle.dump(self, f)
        
        self.file_path = str(checkpoint_file)
        return self.file_path
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Checkpoint':
        """Load checkpoint from file"""
        with open(file_path, 'rb') as f:
            return pickle.load(f)

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""
    
    def __init__(
        self, 
        failure_threshold: int = 10,
        recovery_timeout: int = 300,  # 5 minutes
        expected_exception: Exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()
    
    def __call__(self, func):
        """Decorator for circuit breaker"""
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == "OPEN":
                    if self._should_attempt_reset():
                        self.state = "HALF_OPEN"
                    else:
                        raise Exception("Circuit breaker is OPEN")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
            'recovery_timeout': self.recovery_timeout
        }

class DataReconciler:
    """Data consistency and reconciliation manager"""
    
    def __init__(self, database_client):
        self.db = database_client
        self.logger = logging.getLogger('DataReconciler')
        self.reconciliation_rules = []
    
    def add_reconciliation_rule(self, rule: Dict):
        """Add data reconciliation rule"""
        required_fields = ['name', 'check_function', 'fix_function']
        if not all(field in rule for field in required_fields):
            raise ValueError(f"Reconciliation rule must contain: {required_fields}")
        
        self.reconciliation_rules.append(rule)
        self.logger.info(f"Added reconciliation rule: {rule['name']}")
    
    async def run_reconciliation(self, scope: str = "full") -> Dict[str, Any]:
        """Run data reconciliation checks and fixes"""
        results = {
            'scope': scope,
            'started_at': datetime.now(),
            'rules_executed': 0,
            'issues_found': 0,
            'issues_fixed': 0,
            'errors': [],
            'details': []
        }
        
        self.logger.info(f"Starting data reconciliation: {scope}")
        
        for rule in self.reconciliation_rules:
            try:
                rule_result = await self._execute_reconciliation_rule(rule, scope)
                
                results['rules_executed'] += 1
                results['issues_found'] += rule_result.get('issues_found', 0)
                results['issues_fixed'] += rule_result.get('issues_fixed', 0)
                results['details'].append(rule_result)
                
            except Exception as e:
                error_msg = f"Error in reconciliation rule '{rule['name']}': {str(e)}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        results['completed_at'] = datetime.now()
        results['duration_seconds'] = (results['completed_at'] - results['started_at']).total_seconds()
        
        self.logger.info(f"Reconciliation complete: {results['issues_found']} issues found, {results['issues_fixed']} fixed")
        return results
    
    async def _execute_reconciliation_rule(self, rule: Dict, scope: str) -> Dict[str, Any]:
        """Execute individual reconciliation rule"""
        rule_name = rule['name']
        check_function = rule['check_function']
        fix_function = rule['fix_function']
        
        self.logger.info(f"Executing reconciliation rule: {rule_name}")
        
        # Run check function
        issues = await check_function(self.db, scope)
        
        result = {
            'rule_name': rule_name,
            'issues_found': len(issues) if issues else 0,
            'issues_fixed': 0,
            'details': []
        }
        
        if issues:
            self.logger.warning(f"Found {len(issues)} issues for rule: {rule_name}")
            
            # Attempt to fix issues
            for issue in issues:
                try:
                    fix_result = await fix_function(self.db, issue)
                    if fix_result:
                        result['issues_fixed'] += 1
                        result['details'].append(f"Fixed: {issue}")
                    else:
                        result['details'].append(f"Could not fix: {issue}")
                        
                except Exception as e:
                    result['details'].append(f"Fix failed for {issue}: {str(e)}")
        
        return result

class TransactionManager:
    """Database transaction management with rollback capabilities"""
    
    def __init__(self, database_client):
        self.db = database_client
        self.logger = logging.getLogger('TransactionManager')
        self.active_transactions = {}
        self.transaction_history = []
        self.lock = threading.Lock()
    
    @asynccontextmanager
    async def transaction(self, transaction_id: str = None):
        """Async context manager for database transactions"""
        if not transaction_id:
            transaction_id = f"txn_{int(time.time() * 1000)}_{hash(threading.current_thread()) % 10000}"
        
        transaction_start = datetime.now()
        
        with self.lock:
            self.active_transactions[transaction_id] = {
                'started_at': transaction_start,
                'operations': [],
                'rollback_data': []
            }
        
        try:
            yield transaction_id
            
            # Commit transaction
            await self._commit_transaction(transaction_id)
            self.logger.info(f"Transaction {transaction_id} committed successfully")
            
        except Exception as e:
            # Rollback transaction
            await self._rollback_transaction(transaction_id)
            self.logger.error(f"Transaction {transaction_id} rolled back due to error: {e}")
            raise
        
        finally:
            # Clean up transaction
            with self.lock:
                if transaction_id in self.active_transactions:
                    transaction_data = self.active_transactions[transaction_id]
                    transaction_data['completed_at'] = datetime.now()
                    transaction_data['duration'] = (
                        transaction_data['completed_at'] - transaction_start
                    ).total_seconds()
                    
                    # Move to history
                    self.transaction_history.append(transaction_data)
                    del self.active_transactions[transaction_id]
                    
                    # Keep only recent history
                    if len(self.transaction_history) > 100:
                        self.transaction_history = self.transaction_history[-50:]
    
    def add_operation(self, transaction_id: str, operation: str, data: Dict, rollback_data: Dict = None):
        """Add operation to transaction for potential rollback"""
        with self.lock:
            if transaction_id in self.active_transactions:
                self.active_transactions[transaction_id]['operations'].append({
                    'operation': operation,
                    'data': data,
                    'timestamp': datetime.now()
                })
                
                if rollback_data:
                    self.active_transactions[transaction_id]['rollback_data'].append(rollback_data)
    
    async def _commit_transaction(self, transaction_id: str):
        """Commit transaction operations"""
        # In a real implementation, this would commit all database operations
        pass
    
    async def _rollback_transaction(self, transaction_id: str):
        """Rollback transaction operations"""
        with self.lock:
            if transaction_id not in self.active_transactions:
                return
            
            transaction = self.active_transactions[transaction_id]
            rollback_operations = transaction.get('rollback_data', [])
            
            # Execute rollback operations in reverse order
            for rollback_op in reversed(rollback_operations):
                try:
                    await self._execute_rollback_operation(rollback_op)
                except Exception as e:
                    self.logger.error(f"Rollback operation failed: {e}")
    
    async def _execute_rollback_operation(self, rollback_op: Dict):
        """Execute individual rollback operation"""
        # Implementation would depend on the specific database operations
        # This is a placeholder for the actual rollback logic
        self.logger.info(f"Executing rollback operation: {rollback_op}")

class ErrorRecoverySystem:
    """
    Main error recovery system coordinating all recovery mechanisms
    """
    
    def __init__(self, config, task_queue: redis.Redis):
        self.config = config
        self.task_queue = task_queue
        
        # Components
        self.data_reconciler = None  # Will be initialized with database client
        self.transaction_manager = None  # Will be initialized with database client
        
        # Error tracking
        self.error_instances: Dict[str, ErrorInstance] = {}
        self.error_history: List[ErrorInstance] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Recovery strategies
        self.recovery_strategies = self._create_default_recovery_strategies()
        
        # Checkpointing
        self.checkpoints: List[Checkpoint] = []
        self.checkpoint_interval = timedelta(minutes=30)
        self.last_checkpoint = None
        self.checkpoint_dir = Path("checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Background tasks
        self.background_tasks = []
        self.shutdown_event = asyncio.Event()
        
        # Logging
        self.logger = logging.getLogger('ErrorRecoverySystem')
        
        print("🛡️ Error Recovery System initialized")
    
    def _create_default_recovery_strategies(self) -> Dict[ErrorType, RecoveryStrategy]:
        """Create default recovery strategies for different error types"""
        strategies = {
            ErrorType.API_RATE_LIMIT: RecoveryStrategy(
                error_type=ErrorType.API_RATE_LIMIT,
                max_retries=5,
                retry_delays=[30, 60, 120, 300, 600],  # 30s, 1m, 2m, 5m, 10m
                circuit_breaker_threshold=3,
                recovery_actions=[RecoveryAction.WAIT_AND_RETRY],
                timeout_seconds=600,
                escalation_threshold=10
            ),
            
            ErrorType.API_TIMEOUT: RecoveryStrategy(
                error_type=ErrorType.API_TIMEOUT,
                max_retries=3,
                retry_delays=[5, 15, 30],
                circuit_breaker_threshold=5,
                recovery_actions=[RecoveryAction.RETRY],
                timeout_seconds=60,
                escalation_threshold=15
            ),
            
            ErrorType.API_AUTH_ERROR: RecoveryStrategy(
                error_type=ErrorType.API_AUTH_ERROR,
                max_retries=2,
                retry_delays=[10, 60],
                circuit_breaker_threshold=2,
                recovery_actions=[RecoveryAction.MANUAL_INTERVENTION],
                timeout_seconds=300,
                escalation_threshold=3
            ),
            
            ErrorType.DATABASE_ERROR: RecoveryStrategy(
                error_type=ErrorType.DATABASE_ERROR,
                max_retries=3,
                retry_delays=[2, 5, 10],
                circuit_breaker_threshold=5,
                recovery_actions=[RecoveryAction.RETRY],
                timeout_seconds=30,
                escalation_threshold=10
            ),
            
            ErrorType.NETWORK_ERROR: RecoveryStrategy(
                error_type=ErrorType.NETWORK_ERROR,
                max_retries=5,
                retry_delays=[1, 2, 5, 10, 20],
                circuit_breaker_threshold=10,
                recovery_actions=[RecoveryAction.RETRY],
                timeout_seconds=60,
                escalation_threshold=20
            ),
            
            ErrorType.PARSING_ERROR: RecoveryStrategy(
                error_type=ErrorType.PARSING_ERROR,
                max_retries=1,
                retry_delays=[0],  # Immediate retry once
                circuit_breaker_threshold=100,  # High threshold for parsing errors
                recovery_actions=[RecoveryAction.SKIP],
                timeout_seconds=10,
                escalation_threshold=50
            ),
            
            ErrorType.MEMORY_ERROR: RecoveryStrategy(
                error_type=ErrorType.MEMORY_ERROR,
                max_retries=2,
                retry_delays=[30, 120],  # Wait for garbage collection
                circuit_breaker_threshold=3,
                recovery_actions=[RecoveryAction.RESTART_WORKER],
                timeout_seconds=300,
                escalation_threshold=5
            ),
            
            ErrorType.TOKEN_ERROR: RecoveryStrategy(
                error_type=ErrorType.TOKEN_ERROR,
                max_retries=3,
                retry_delays=[5, 30, 120],
                circuit_breaker_threshold=5,
                recovery_actions=[RecoveryAction.RETRY],
                timeout_seconds=300,
                escalation_threshold=10
            )
        }
        
        return strategies
    
    async def initialize(self):
        """Initialize error recovery system"""
        try:
            # Start background services
            self.background_tasks.extend([
                asyncio.create_task(self._recovery_monitoring_service()),
                asyncio.create_task(self._checkpoint_service()),
                asyncio.create_task(self._reconciliation_service())
            ])
            
            self.logger.info("Error Recovery System initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error Recovery System initialization failed: {e}")
            return False
    
    def classify_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorType:
        """Classify error based on type and context"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # API-related errors
        if "429" in error_str or "rate limit" in error_str:
            return ErrorType.API_RATE_LIMIT
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorType.API_TIMEOUT
        elif any(code in error_str for code in ["401", "403", "unauthorized", "forbidden"]):
            return ErrorType.API_AUTH_ERROR
        elif any(code in error_str for code in ["500", "502", "503", "504"]):
            return ErrorType.API_SERVER_ERROR
        elif "token" in error_str:
            return ErrorType.TOKEN_ERROR
        
        # Network errors
        elif any(term in error_str for term in ["connection", "network", "dns", "resolve"]):
            return ErrorType.NETWORK_ERROR
        
        # Database errors
        elif any(term in error_str for term in ["database", "sql", "connection pool", "deadlock"]):
            return ErrorType.DATABASE_ERROR
        
        # Memory errors
        elif any(term in error_str for term in ["memory", "out of memory", "memoryerror"]):
            return ErrorType.MEMORY_ERROR
        
        # Parsing errors
        elif any(term in error_str for term in ["json", "parse", "decode", "invalid format"]):
            return ErrorType.PARSING_ERROR
        
        # Validation errors
        elif any(term in error_str for term in ["validation", "invalid", "constraint"]):
            return ErrorType.VALIDATION_ERROR
        
        # Disk errors
        elif any(term in error_str for term in ["disk", "space", "no space left"]):
            return ErrorType.DISK_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    async def handle_error(
        self, 
        error: Exception, 
        context: Dict[str, Any], 
        source: str
    ) -> Tuple[RecoveryAction, Dict[str, Any]]:
        """
        Handle error with appropriate recovery strategy
        
        Returns:
            Tuple of (recovery_action, recovery_context)
        """
        # Classify error
        error_type = self.classify_error(error, context)
        
        # Create error instance
        error_id = f"err_{int(time.time() * 1000)}_{hash(str(error)) % 10000}"
        error_instance = ErrorInstance(
            id=error_id,
            error_type=error_type,
            message=str(error),
            context=context,
            timestamp=datetime.now(),
            source=source,
            stack_trace=self._get_stack_trace(error)
        )
        
        # Store error instance
        self.error_instances[error_id] = error_instance
        self.error_history.append(error_instance)
        
        # Get recovery strategy
        strategy = self.recovery_strategies.get(error_type)
        if not strategy:
            strategy = self.recovery_strategies[ErrorType.UNKNOWN_ERROR]
        
        # Determine recovery action
        recovery_action, recovery_context = await self._determine_recovery_action(
            error_instance, strategy
        )
        
        error_instance.recovery_action = recovery_action
        
        self.logger.info(
            f"Error handled: {error_type.value} -> {recovery_action.value} "
            f"(Source: {source}, ID: {error_id})"
        )
        
        return recovery_action, recovery_context
    
    async def _determine_recovery_action(
        self, 
        error: ErrorInstance, 
        strategy: RecoveryStrategy
    ) -> Tuple[RecoveryAction, Dict[str, Any]]:
        """Determine appropriate recovery action based on strategy and context"""
        
        recovery_context = {
            'error_id': error.id,
            'retry_count': error.retry_count,
            'max_retries': strategy.max_retries,
            'strategy': strategy
        }
        
        # Check if max retries exceeded
        if error.retry_count >= strategy.max_retries:
            return RecoveryAction.ESCALATE, recovery_context
        
        # Check circuit breaker
        circuit_breaker_key = f"{error.error_type.value}_{error.source}"
        if circuit_breaker_key not in self.circuit_breakers:
            self.circuit_breakers[circuit_breaker_key] = CircuitBreaker(
                failure_threshold=strategy.circuit_breaker_threshold,
                recovery_timeout=strategy.timeout_seconds
            )
        
        circuit_breaker = self.circuit_breakers[circuit_breaker_key]
        circuit_breaker._on_failure()  # Update circuit breaker state
        
        if circuit_breaker.state == "OPEN":
            return RecoveryAction.CIRCUIT_BREAK, recovery_context
        
        # Determine recovery action based on error type and context
        primary_action = strategy.recovery_actions[0] if strategy.recovery_actions else RecoveryAction.RETRY
        
        # Add retry delay if needed
        if primary_action in [RecoveryAction.RETRY, RecoveryAction.WAIT_AND_RETRY]:
            recovery_context['retry_delay'] = strategy.get_retry_delay(error.retry_count)
        
        return primary_action, recovery_context
    
    async def execute_recovery_action(
        self, 
        action: RecoveryAction, 
        context: Dict[str, Any],
        recovery_function: Callable = None
    ) -> bool:
        """
        Execute recovery action
        
        Returns:
            bool: True if recovery successful, False otherwise
        """
        error_id = context.get('error_id')
        error_instance = self.error_instances.get(error_id)
        
        if not error_instance:
            self.logger.error(f"Error instance not found: {error_id}")
            return False
        
        try:
            if action == RecoveryAction.RETRY:
                return await self._execute_retry(error_instance, context, recovery_function)
            
            elif action == RecoveryAction.WAIT_AND_RETRY:
                return await self._execute_wait_and_retry(error_instance, context, recovery_function)
            
            elif action == RecoveryAction.SKIP:
                return await self._execute_skip(error_instance, context)
            
            elif action == RecoveryAction.CIRCUIT_BREAK:
                return await self._execute_circuit_break(error_instance, context)
            
            elif action == RecoveryAction.RESTART_WORKER:
                return await self._execute_restart_worker(error_instance, context)
            
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                return await self._execute_manual_intervention(error_instance, context)
            
            elif action == RecoveryAction.ESCALATE:
                return await self._execute_escalate(error_instance, context)
            
            else:
                self.logger.warning(f"Unknown recovery action: {action}")
                return False
                
        except Exception as e:
            self.logger.error(f"Recovery action execution failed: {e}")
            return False
    
    async def _execute_retry(
        self, 
        error: ErrorInstance, 
        context: Dict[str, Any], 
        recovery_function: Callable
    ) -> bool:
        """Execute immediate retry"""
        if not recovery_function:
            self.logger.warning("No recovery function provided for retry")
            return False
        
        error.retry_count += 1
        
        try:
            result = await recovery_function(error.context)
            
            if result:
                error.resolved = True
                error.resolution_timestamp = datetime.now()
                error.resolution_method = "retry"
                self.logger.info(f"Error {error.id} resolved via retry")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Retry failed for error {error.id}: {e}")
            return False
    
    async def _execute_wait_and_retry(
        self, 
        error: ErrorInstance, 
        context: Dict[str, Any], 
        recovery_function: Callable
    ) -> bool:
        """Execute retry after waiting"""
        retry_delay = context.get('retry_delay', 30)
        
        self.logger.info(f"Waiting {retry_delay}s before retry for error {error.id}")
        await asyncio.sleep(retry_delay)
        
        return await self._execute_retry(error, context, recovery_function)
    
    async def _execute_skip(self, error: ErrorInstance, context: Dict[str, Any]) -> bool:
        """Skip the failed operation"""
        error.resolved = True
        error.resolution_timestamp = datetime.now()
        error.resolution_method = "skipped"
        
        self.logger.info(f"Error {error.id} resolved by skipping")
        return True
    
    async def _execute_circuit_break(self, error: ErrorInstance, context: Dict[str, Any]) -> bool:
        """Handle circuit breaker activation"""
        circuit_breaker_key = f"{error.error_type.value}_{error.source}"
        circuit_breaker = self.circuit_breakers.get(circuit_breaker_key)
        
        if circuit_breaker:
            timeout = circuit_breaker.recovery_timeout
            self.logger.warning(
                f"Circuit breaker activated for {circuit_breaker_key}, "
                f"recovery timeout: {timeout}s"
            )
            
            # Schedule circuit breaker reset check
            asyncio.create_task(self._schedule_circuit_breaker_check(circuit_breaker_key, timeout))
        
        return False  # Operation not recovered, circuit is open
    
    async def _execute_restart_worker(self, error: ErrorInstance, context: Dict[str, Any]) -> bool:
        """Restart worker process"""
        worker_id = error.source
        
        self.logger.warning(f"Requesting worker restart: {worker_id}")
        
        # Send restart signal via Redis
        restart_message = {
            'type': 'restart_worker',
            'worker_id': worker_id,
            'reason': f"Error recovery: {error.error_type.value}",
            'timestamp': datetime.now().isoformat()
        }
        
        self.task_queue.lpush('control_messages', json.dumps(restart_message))
        
        error.resolution_method = "worker_restart_requested"
        return True
    
    async def _execute_manual_intervention(self, error: ErrorInstance, context: Dict[str, Any]) -> bool:
        """Request manual intervention"""
        intervention_message = {
            'type': 'manual_intervention_required',
            'error_id': error.id,
            'error_type': error.error_type.value,
            'message': error.message,
            'context': error.context,
            'source': error.source,
            'timestamp': error.timestamp.isoformat()
        }
        
        # Store in Redis for manual intervention queue
        self.task_queue.lpush('manual_intervention_queue', json.dumps(intervention_message))
        
        self.logger.critical(
            f"Manual intervention required for error {error.id}: {error.message}"
        )
        
        # TODO: Send alert to administrators
        
        return False  # Not automatically resolved
    
    async def _execute_escalate(self, error: ErrorInstance, context: Dict[str, Any]) -> bool:
        """Escalate error to system administrators"""
        escalation_message = {
            'type': 'error_escalation',
            'error_id': error.id,
            'error_type': error.error_type.value,
            'message': error.message,
            'retry_count': error.retry_count,
            'context': error.context,
            'source': error.source,
            'timestamp': error.timestamp.isoformat(),
            'escalation_timestamp': datetime.now().isoformat()
        }
        
        # Store in Redis for escalation queue
        self.task_queue.lpush('escalation_queue', json.dumps(escalation_message))
        
        self.logger.critical(
            f"Error escalated {error.id}: {error.message} "
            f"(Retries exhausted: {error.retry_count})"
        )
        
        # TODO: Send high-priority alert to administrators
        
        return False  # Not automatically resolved
    
    async def create_checkpoint(self, system_state: Dict[str, Any]) -> str:
        """Create system checkpoint"""
        checkpoint_id = f"checkpoint_{int(time.time() * 1000)}"
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            system_state=system_state,
            active_tasks=system_state.get('active_tasks', []),
            completed_tasks=system_state.get('completed_tasks', 0),
            failed_tasks=system_state.get('failed_tasks', 0),
            metrics_snapshot=system_state.get('metrics', {})
        )
        
        # Save checkpoint to file
        checkpoint.save_to_file(str(self.checkpoint_dir))
        
        # Add to checkpoint list
        self.checkpoints.append(checkpoint)
        self.last_checkpoint = checkpoint
        
        # Clean up old checkpoints
        self._cleanup_old_checkpoints()
        
        self.logger.info(f"Checkpoint created: {checkpoint_id}")
        return checkpoint_id
    
    async def restore_from_checkpoint(self, checkpoint_id: str = None) -> Optional[Dict[str, Any]]:
        """Restore system from checkpoint"""
        if checkpoint_id:
            # Find specific checkpoint
            checkpoint = next(
                (cp for cp in self.checkpoints if cp.checkpoint_id == checkpoint_id),
                None
            )
        else:
            # Use latest checkpoint
            checkpoint = self.last_checkpoint
        
        if not checkpoint:
            self.logger.error("No checkpoint available for restoration")
            return None
        
        try:
            if checkpoint.file_path and Path(checkpoint.file_path).exists():
                checkpoint = Checkpoint.load_from_file(checkpoint.file_path)
            
            self.logger.info(f"Restoring from checkpoint: {checkpoint.checkpoint_id}")
            
            return {
                'checkpoint_id': checkpoint.checkpoint_id,
                'timestamp': checkpoint.timestamp,
                'system_state': checkpoint.system_state,
                'active_tasks': checkpoint.active_tasks,
                'completed_tasks': checkpoint.completed_tasks,
                'failed_tasks': checkpoint.failed_tasks
            }
            
        except Exception as e:
            self.logger.error(f"Failed to restore from checkpoint {checkpoint.checkpoint_id}: {e}")
            return None
    
    def _cleanup_old_checkpoints(self):
        """Clean up old checkpoint files"""
        # Keep only last 10 checkpoints
        if len(self.checkpoints) > 10:
            old_checkpoints = self.checkpoints[:-10]
            
            for checkpoint in old_checkpoints:
                if checkpoint.file_path and Path(checkpoint.file_path).exists():
                    try:
                        Path(checkpoint.file_path).unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete old checkpoint file: {e}")
            
            self.checkpoints = self.checkpoints[-10:]
    
    async def run_recovery_cycle(self):
        """Run periodic recovery cycle"""
        try:
            # Check for unresolved errors
            unresolved_errors = [
                error for error in self.error_instances.values() 
                if not error.resolved and error.retry_count > 0
            ]
            
            if unresolved_errors:
                self.logger.info(f"Running recovery cycle for {len(unresolved_errors)} unresolved errors")
                
                for error in unresolved_errors:
                    strategy = self.recovery_strategies.get(error.error_type)
                    if strategy and error.retry_count < strategy.max_retries:
                        # Attempt recovery if within retry limits
                        self.logger.info(f"Attempting recovery for error {error.id}")
                        # This would trigger the recovery process
            
            # Check circuit breakers
            for key, breaker in self.circuit_breakers.items():
                if breaker.state == "OPEN" and breaker._should_attempt_reset():
                    breaker.state = "HALF_OPEN"
                    self.logger.info(f"Circuit breaker {key} reset to HALF_OPEN")
            
        except Exception as e:
            self.logger.error(f"Recovery cycle error: {e}")
    
    async def _schedule_circuit_breaker_check(self, breaker_key: str, timeout: int):
        """Schedule circuit breaker reset check"""
        await asyncio.sleep(timeout)
        
        if breaker_key in self.circuit_breakers:
            breaker = self.circuit_breakers[breaker_key]
            if breaker.state == "OPEN" and breaker._should_attempt_reset():
                breaker.state = "HALF_OPEN"
                self.logger.info(f"Circuit breaker {breaker_key} reset to HALF_OPEN after timeout")
    
    async def _recovery_monitoring_service(self):
        """Background service for recovery monitoring"""
        while not self.shutdown_event.is_set():
            try:
                await self.run_recovery_cycle()
            except Exception as e:
                self.logger.error(f"Recovery monitoring service error: {e}")
            
            await asyncio.sleep(60)  # Run every minute
    
    async def _checkpoint_service(self):
        """Background service for creating checkpoints"""
        while not self.shutdown_event.is_set():
            try:
                if (
                    not self.last_checkpoint or 
                    datetime.now() - self.last_checkpoint.timestamp > self.checkpoint_interval
                ):
                    # Create checkpoint with current system state
                    system_state = {
                        'timestamp': datetime.now().isoformat(),
                        'active_errors': len([e for e in self.error_instances.values() if not e.resolved]),
                        'circuit_breaker_states': {
                            k: v.get_state() for k, v in self.circuit_breakers.items()
                        }
                    }
                    
                    await self.create_checkpoint(system_state)
                
            except Exception as e:
                self.logger.error(f"Checkpoint service error: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def _reconciliation_service(self):
        """Background service for data reconciliation"""
        while not self.shutdown_event.is_set():
            try:
                if self.data_reconciler:
                    # Run reconciliation every 6 hours
                    await asyncio.sleep(21600)
                    await self.data_reconciler.run_reconciliation("incremental")
                else:
                    await asyncio.sleep(3600)  # Wait 1 hour if no reconciler
                    
            except Exception as e:
                self.logger.error(f"Reconciliation service error: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        recent_errors = [e for e in self.error_history if e.timestamp >= last_24h]
        
        stats = {
            'total_errors': len(self.error_history),
            'recent_errors_24h': len(recent_errors),
            'unresolved_errors': len([e for e in self.error_instances.values() if not e.resolved]),
            'error_types': {},
            'recovery_actions': {},
            'circuit_breaker_states': {k: v.get_state() for k, v in self.circuit_breakers.items()},
            'resolution_rates': {}
        }
        
        # Error type distribution
        for error in recent_errors:
            error_type = error.error_type.value
            stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1
            
            if error.recovery_action:
                action = error.recovery_action.value
                stats['recovery_actions'][action] = stats['recovery_actions'].get(action, 0) + 1
        
        # Resolution rates
        for error_type in ErrorType:
            type_errors = [e for e in recent_errors if e.error_type == error_type]
            if type_errors:
                resolved = len([e for e in type_errors if e.resolved])
                stats['resolution_rates'][error_type.value] = resolved / len(type_errors)
        
        return stats
    
    def _get_stack_trace(self, error: Exception) -> Optional[str]:
        """Get stack trace from exception"""
        import traceback
        try:
            return traceback.format_exc()
        except:
            return None
    
    async def health_check(self) -> str:
        """Component health check"""
        try:
            # Check if background tasks are running
            if any(task.done() for task in self.background_tasks):
                return 'degraded'
            
            # Check error rates
            stats = self.get_error_statistics()
            if stats['unresolved_errors'] > 50:
                return 'degraded'
            
            return 'healthy'
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return 'unhealthy'

# Testing
async def test_error_recovery():
    """Test error recovery system"""
    print("🧪 Testing Error Recovery System")
    print("=" * 50)
    
    # Mock Redis connection
    import fakeredis
    task_queue = fakeredis.FakeRedis(decode_responses=True)
    
    # Create error recovery system
    from robust_architecture_design import SystemConfiguration
    config = SystemConfiguration()
    
    recovery_system = ErrorRecoverySystem(config, task_queue)
    
    # Initialize
    success = await recovery_system.initialize()
    print(f"✅ Initialization: {'Success' if success else 'Failed'}")
    
    # Test error classification
    test_errors = [
        Exception("HTTP 429: Rate limit exceeded"),
        Exception("Connection timeout"),
        Exception("JSON decode error"),
        Exception("Database connection failed"),
        Exception("Token expired")
    ]
    
    for error in test_errors:
        error_type = recovery_system.classify_error(error)
        print(f"🔍 Error '{str(error)[:30]}...' -> {error_type.value}")
    
    # Test error handling
    test_error = Exception("Test error for recovery")
    action, context = await recovery_system.handle_error(
        test_error, 
        {'test_context': 'value'}, 
        'test_worker'
    )
    print(f"🛠️ Recovery Action: {action.value}")
    
    # Get statistics
    stats = recovery_system.get_error_statistics()
    print(f"📊 Error Statistics: {stats['total_errors']} total errors")
    
    # Health check
    health = await recovery_system.health_check()
    print(f"🏥 Health: {health}")
    
    print("✅ Error Recovery System test complete")

if __name__ == "__main__":
    asyncio.run(test_error_recovery())