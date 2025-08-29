#!/usr/bin/env python3
"""
Error Recovery System - Comprehensive error handling and recovery mechanisms
Handles various failure scenarios and provides automatic recovery
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Error type classification"""
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    TOKEN_ERROR = "token_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorRecord:
    """Individual error record"""
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    context: Dict
    timestamp: datetime
    retry_count: int = 0
    resolved: bool = False
    resolution_strategy: Optional[str] = None

@dataclass
class RecoveryAction:
    """Recovery action configuration"""
    name: str
    condition: Callable[[ErrorRecord], bool]
    action: Callable[[ErrorRecord], bool]
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    timeout: int = 30

class ErrorRecoverySystem:
    """Comprehensive error recovery system"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.error_history: List[ErrorRecord] = []
        self.recovery_actions: List[RecoveryAction] = []
        self.error_patterns: Dict[str, int] = {}
        
        # System health metrics
        self.health_metrics = {
            'total_errors': 0,
            'resolved_errors': 0,
            'unresolved_errors': 0,
            'recovery_success_rate': 0.0,
            'last_error_time': None,
            'system_uptime': datetime.now()
        }
        
        # Initialize recovery actions
        self._initialize_recovery_actions()
        
        self.logger.info("✅ Error Recovery System initialized")
    
    def _initialize_recovery_actions(self):
        """Initialize predefined recovery actions"""
        
        # Token refresh recovery
        self.recovery_actions.append(RecoveryAction(
            name="token_refresh",
            condition=lambda error: error.error_type == ErrorType.TOKEN_ERROR,
            action=self._recover_token_error,
            max_retries=3,
            backoff_multiplier=1.5
        ))
        
        # Rate limit recovery
        self.recovery_actions.append(RecoveryAction(
            name="rate_limit_backoff",
            condition=lambda error: error.error_type == ErrorType.RATE_LIMIT_ERROR,
            action=self._recover_rate_limit_error,
            max_retries=5,
            backoff_multiplier=2.0
        ))
        
        # Network error recovery
        self.recovery_actions.append(RecoveryAction(
            name="network_retry",
            condition=lambda error: error.error_type == ErrorType.NETWORK_ERROR,
            action=self._recover_network_error,
            max_retries=3,
            backoff_multiplier=1.5
        ))
        
        # Database error recovery
        self.recovery_actions.append(RecoveryAction(
            name="database_reconnect",
            condition=lambda error: error.error_type == ErrorType.DATABASE_ERROR,
            action=self._recover_database_error,
            max_retries=2,
            backoff_multiplier=2.0
        ))
        
        # API error recovery
        self.recovery_actions.append(RecoveryAction(
            name="api_retry",
            condition=lambda error: error.error_type == ErrorType.API_ERROR,
            action=self._recover_api_error,
            max_retries=3,
            backoff_multiplier=1.8
        ))
    
    def handle_error(self, error: Exception, context: Dict = None, 
                    error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
        """
        Handle error with automatic classification and recovery
        
        Returns:
            bool: True if error was resolved, False otherwise
        """
        
        # Create error record
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.error_history)}"
        error_record = ErrorRecord(
            error_id=error_id,
            error_type=error_type,
            severity=severity,
            message=str(error),
            context=context or {},
            timestamp=datetime.now()
        )
        
        # Auto-classify error if not specified
        if error_type == ErrorType.UNKNOWN_ERROR:
            error_record.error_type = self._classify_error(error, context)
        
        # Add to error history
        self.error_history.append(error_record)
        self.health_metrics['total_errors'] += 1
        self.health_metrics['last_error_time'] = datetime.now()
        
        # Update error patterns
        error_key = f"{error_record.error_type.value}:{str(error)[:100]}"
        self.error_patterns[error_key] = self.error_patterns.get(error_key, 0) + 1
        
        self.logger.error(f"❌ Error {error_id} - {error_record.error_type.value}: {error}")
        
        # Attempt recovery
        recovery_success = self._attempt_recovery(error_record)
        
        if recovery_success:
            error_record.resolved = True
            self.health_metrics['resolved_errors'] += 1
            self.logger.info(f"✅ Error {error_id} resolved successfully")
        else:
            self.health_metrics['unresolved_errors'] += 1
            self.logger.warning(f"⚠️ Error {error_id} could not be resolved")
        
        # Update success rate
        if self.health_metrics['total_errors'] > 0:
            self.health_metrics['recovery_success_rate'] = (
                self.health_metrics['resolved_errors'] / self.health_metrics['total_errors'] * 100
            )
        
        return recovery_success
    
    def _classify_error(self, error: Exception, context: Dict = None) -> ErrorType:
        """Automatically classify error type"""
        error_str = str(error).lower()
        context = context or {}
        
        # Token-related errors
        if any(keyword in error_str for keyword in ['unauthorized', '401', 'token', 'auth']):
            return ErrorType.TOKEN_ERROR
        
        # Rate limiting errors
        if any(keyword in error_str for keyword in ['429', 'too many requests', 'rate limit']):
            return ErrorType.RATE_LIMIT_ERROR
        
        # Network errors
        if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'dns']):
            return ErrorType.NETWORK_ERROR
        
        # Database errors
        if any(keyword in error_str for keyword in ['database', 'sql', 'constraint', 'foreign key']):
            return ErrorType.DATABASE_ERROR
        
        # API errors
        if any(keyword in error_str for keyword in ['api', 'request', 'response', 'http']):
            return ErrorType.API_ERROR
        
        # Validation errors
        if any(keyword in error_str for keyword in ['validation', 'invalid', 'missing field']):
            return ErrorType.VALIDATION_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    def _attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """Attempt error recovery using registered actions"""
        
        for recovery_action in self.recovery_actions:
            if recovery_action.condition(error_record):
                self.logger.info(f"🔄 Attempting recovery: {recovery_action.name}")
                
                for attempt in range(recovery_action.max_retries):
                    try:
                        error_record.retry_count = attempt + 1
                        
                        # Apply backoff delay
                        if attempt > 0:
                            delay = recovery_action.backoff_multiplier ** attempt
                            self.logger.info(f"⏳ Backoff delay: {delay:.1f}s")
                            time.sleep(delay)
                        
                        # Execute recovery action
                        success = recovery_action.action(error_record)
                        
                        if success:
                            error_record.resolution_strategy = recovery_action.name
                            self.logger.info(f"✅ Recovery successful with {recovery_action.name}")
                            return True
                        
                    except Exception as recovery_error:
                        self.logger.warning(f"⚠️ Recovery attempt {attempt + 1} failed: {recovery_error}")
                
                self.logger.warning(f"❌ Recovery action {recovery_action.name} exhausted all retries")
        
        return False
    
    def _recover_token_error(self, error_record: ErrorRecord) -> bool:
        """Recover from token-related errors"""
        try:
            self.logger.info("🔑 Attempting token refresh...")
            
            # Import token collector
            from collectors.core.playwright_token_collector import PlaywrightTokenCollector
            
            token_collector = PlaywrightTokenCollector()
            new_token_data = token_collector.get_token_with_playwright()
            
            if new_token_data and new_token_data.get('token'):
                self.logger.info("✅ New token acquired successfully")
                
                # Update context with new token
                error_record.context['recovery_token'] = new_token_data['token']
                error_record.context['recovery_cookies'] = new_token_data.get('cookies', {})
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Token recovery failed: {e}")
            return False
    
    def _recover_rate_limit_error(self, error_record: ErrorRecord) -> bool:
        """Recover from rate limiting"""
        try:
            # Calculate backoff time based on retry count
            base_delay = 5
            backoff_delay = base_delay * (2 ** error_record.retry_count)
            max_delay = 300  # 5 minutes max
            
            delay = min(backoff_delay, max_delay)
            
            self.logger.info(f"⏳ Rate limit recovery: waiting {delay}s")
            time.sleep(delay)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Rate limit recovery failed: {e}")
            return False
    
    def _recover_network_error(self, error_record: ErrorRecord) -> bool:
        """Recover from network-related errors"""
        try:
            self.logger.info("🌐 Testing network connectivity...")
            
            import requests
            
            # Test connectivity with simple request
            test_url = "https://www.google.com"
            response = requests.get(test_url, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("✅ Network connectivity restored")
                return True
            else:
                self.logger.warning(f"⚠️ Network test failed: {response.status_code}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Network recovery failed: {e}")
            return False
    
    def _recover_database_error(self, error_record: ErrorRecord) -> bool:
        """Recover from database-related errors"""
        try:
            self.logger.info("🗄️ Attempting database reconnection...")
            
            # Test database connection
            from supabase import create_client
            
            url = 'https://eslhavjipwbyvbbknixv.supabase.co'
            key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
            
            client = create_client(url, key)
            
            # Test with simple query
            result = client.table('properties_new').select('id').limit(1).execute()
            
            if result:
                self.logger.info("✅ Database connection restored")
                error_record.context['recovery_client'] = client
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Database recovery failed: {e}")
            return False
    
    def _recover_api_error(self, error_record: ErrorRecord) -> bool:
        """Recover from API-related errors"""
        try:
            context = error_record.context
            
            # If it's a specific article error, skip it and continue
            if 'article_no' in context:
                self.logger.info(f"⏭️ Skipping problematic article {context['article_no']}")
                return True
            
            # For general API errors, wait and retry
            delay = 3 * error_record.retry_count
            self.logger.info(f"⏳ API recovery: waiting {delay}s before retry")
            time.sleep(delay)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ API recovery failed: {e}")
            return False
    
    @contextmanager
    def error_context(self, operation_name: str, **context_data):
        """Context manager for error handling"""
        start_time = time.time()
        operation_context = {
            'operation': operation_name,
            'start_time': start_time,
            **context_data
        }
        
        try:
            yield operation_context
            
        except Exception as e:
            operation_context['duration'] = time.time() - start_time
            operation_context['exception_type'] = type(e).__name__
            
            # Classify error based on operation and context
            error_type = self._classify_error(e, operation_context)
            severity = self._determine_severity(e, operation_context)
            
            # Handle the error
            recovered = self.handle_error(e, operation_context, error_type, severity)
            
            if not recovered:
                raise
    
    def _determine_severity(self, error: Exception, context: Dict) -> ErrorSeverity:
        """Determine error severity based on error and context"""
        error_str = str(error).lower()
        
        # Critical errors
        if any(keyword in error_str for keyword in ['critical', 'fatal', 'system']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if any(keyword in error_str for keyword in ['database', 'connection', 'auth']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors (API, validation)
        if any(keyword in error_str for keyword in ['api', 'validation', 'timeout']):
            return ErrorSeverity.MEDIUM
        
        # Low severity by default
        return ErrorSeverity.LOW
    
    def get_error_summary(self) -> Dict:
        """Get comprehensive error summary"""
        
        # Recent errors (last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [e for e in self.error_history if e.timestamp >= one_hour_ago]
        
        # Error type distribution
        error_type_dist = {}
        for error in self.error_history:
            error_type_dist[error.error_type.value] = error_type_dist.get(error.error_type.value, 0) + 1
        
        # Top error patterns
        top_patterns = sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'health_metrics': self.health_metrics,
            'total_errors': len(self.error_history),
            'recent_errors_count': len(recent_errors),
            'error_type_distribution': error_type_dist,
            'top_error_patterns': top_patterns,
            'unresolved_errors': [e for e in self.error_history if not e.resolved],
            'recovery_actions_count': len(self.recovery_actions)
        }
    
    def cleanup_old_errors(self, days_to_keep: int = 7):
        """Clean up old error records"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        before_count = len(self.error_history)
        self.error_history = [e for e in self.error_history if e.timestamp >= cutoff_date]
        after_count = len(self.error_history)
        
        cleaned_count = before_count - after_count
        self.logger.info(f"🧹 Cleaned up {cleaned_count} old error records")
        
        return cleaned_count
    
    def add_custom_recovery_action(self, action: RecoveryAction):
        """Add custom recovery action"""
        self.recovery_actions.append(action)
        self.logger.info(f"✅ Added custom recovery action: {action.name}")
    
    def get_health_status(self) -> str:
        """Get system health status"""
        if self.health_metrics['recovery_success_rate'] >= 90:
            return "HEALTHY"
        elif self.health_metrics['recovery_success_rate'] >= 75:
            return "DEGRADED"
        elif self.health_metrics['recovery_success_rate'] >= 50:
            return "UNHEALTHY"
        else:
            return "CRITICAL"

# Utility functions for common error handling patterns
def with_retry(max_retries: int = 3, backoff_multiplier: float = 1.5):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        delay = backoff_multiplier ** attempt
                        logger.info(f"⏳ Retry {attempt + 1}/{max_retries} in {delay:.1f}s")
                        time.sleep(delay)
                    else:
                        logger.error(f"❌ All {max_retries} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator

def safe_execute(func: Callable, error_recovery_system: ErrorRecoverySystem, 
                context: Dict = None, default_return: Any = None):
    """Safely execute function with error recovery"""
    try:
        return func()
    except Exception as e:
        recovered = error_recovery_system.handle_error(e, context)
        
        if recovered:
            # Try again after recovery
            try:
                return func()
            except Exception as retry_error:
                logger.error(f"❌ Function failed even after recovery: {retry_error}")
                return default_return
        else:
            logger.error(f"❌ Function failed and could not recover: {e}")
            return default_return

# Example usage and testing
def test_error_recovery_system():
    """Test the error recovery system"""
    print("🧪 Testing Error Recovery System")
    print("=" * 50)
    
    recovery_system = ErrorRecoverySystem()
    
    # Test different error types
    test_errors = [
        (Exception("Unauthorized access"), ErrorType.TOKEN_ERROR),
        (Exception("Too many requests"), ErrorType.RATE_LIMIT_ERROR),
        (Exception("Connection timeout"), ErrorType.NETWORK_ERROR),
        (Exception("Database constraint violation"), ErrorType.DATABASE_ERROR),
        (Exception("Invalid API response"), ErrorType.API_ERROR)
    ]
    
    for error, error_type in test_errors:
        print(f"\n🧪 Testing {error_type.value}...")
        context = {'test_error': True, 'error_type': error_type.value}
        recovered = recovery_system.handle_error(error, context, error_type)
        print(f"   Recovery: {'✅ Success' if recovered else '❌ Failed'}")
    
    # Print summary
    summary = recovery_system.get_error_summary()
    print(f"\n📊 Error Summary:")
    print(f"   Total Errors: {summary['total_errors']}")
    print(f"   Recovery Rate: {summary['health_metrics']['recovery_success_rate']:.1f}%")
    print(f"   Health Status: {recovery_system.get_health_status()}")
    
    return recovery_system

if __name__ == "__main__":
    test_error_recovery_system()