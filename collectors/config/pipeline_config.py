#!/usr/bin/env python3
"""
Pipeline Configuration Management
Centralized configuration for the robust data pipeline
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PipelineConfig:
    """Centralized configuration management"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self.config = self._load_default_config()
        
        if self.config_file and Path(self.config_file).exists():
            self._load_from_file()
        
        # Environment variable overrides
        self._apply_env_overrides()
        
        logger.info(f"✅ Configuration loaded from {self.config_file or 'defaults'}")
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in common locations"""
        possible_locations = [
            'config.json',
            'collectors/config/config.json',
            os.path.expanduser('~/.naver_land/config.json'),
            '/etc/naver_land/config.json'
        ]
        
        for location in possible_locations:
            if Path(location).exists():
                return location
        
        return None
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            # Pipeline Settings
            'pipeline': {
                'max_workers': 5,
                'batch_size': 20,
                'max_retries': 3,
                'checkpoint_interval': 100,
                'progress_report_interval': 50
            },
            
            # Rate Limiting
            'rate_limiting': {
                'region_delay': 5.0,
                'article_delay': 2.0,
                'api_delay_min': 1.0,
                'api_delay_max': 3.0,
                'backoff_multiplier': 2.0
            },
            
            # Error Handling
            'error_handling': {
                'max_consecutive_failures': 10,
                'circuit_breaker_timeout': 300,  # 5 minutes
                'retry_delays': [2, 5, 10],
                'critical_error_threshold': 5
            },
            
            # Monitoring
            'monitoring': {
                'metrics_retention_hours': 24,
                'alert_cooldown_minutes': 5,
                'health_check_interval': 30,
                'performance_window_minutes': 10
            },
            
            # Database
            'database': {
                'batch_size': 50,
                'connection_timeout': 30,
                'query_timeout': 60,
                'max_retries': 3,
                'constraint_validation': True
            },
            
            # Collection
            'collection': {
                'request_timeout': 15,
                'max_redirects': 5,
                'user_agent_rotation': True,
                'validate_responses': True,
                'save_raw_data': False
            },
            
            # Data Quality
            'quality': {
                'min_data_completeness': 0.7,
                'required_fields': [
                    'article_no', 'building_name', 'real_estate_type',
                    'trade_type', 'address'
                ],
                'validation_strict': True
            },
            
            # Logging
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_rotation': True,
                'max_file_size_mb': 100,
                'backup_count': 5
            },
            
            # Regional Settings
            'regions': {
                'default_pages': None,  # Collect all pages
                'parallel_regions': False,
                'region_timeout_minutes': 60,
                'skip_empty_regions': True
            },
            
            # Performance
            'performance': {
                'memory_limit_mb': 1000,
                'cpu_limit_percent': 80,
                'cache_size_mb': 100,
                'gc_interval': 1000
            }
        }
    
    def _load_from_file(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Deep merge configurations
            self.config = self._deep_merge(self.config, file_config)
            
            logger.info(f"✅ Configuration loaded from {self.config_file}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load config file {self.config_file}: {e}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        env_mappings = {
            'PIPELINE_MAX_WORKERS': ['pipeline', 'max_workers'],
            'PIPELINE_BATCH_SIZE': ['pipeline', 'batch_size'],
            'API_DELAY': ['rate_limiting', 'article_delay'],
            'DB_TIMEOUT': ['database', 'connection_timeout'],
            'LOG_LEVEL': ['logging', 'level'],
            'MEMORY_LIMIT_MB': ['performance', 'memory_limit_mb']
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                try:
                    # Convert to appropriate type
                    if config_path[-1] in ['max_workers', 'batch_size', 'connection_timeout', 'memory_limit_mb']:
                        env_value = int(env_value)
                    elif config_path[-1] in ['article_delay']:
                        env_value = float(env_value)
                    
                    # Set nested configuration value
                    self._set_nested_config(config_path, env_value)
                    logger.info(f"✅ Environment override: {env_var} = {env_value}")
                    
                except ValueError as e:
                    logger.warning(f"⚠️ Invalid environment value for {env_var}: {env_value}")
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _set_nested_config(self, path: list, value: Any):
        """Set nested configuration value"""
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path"""
        keys = path.split('.')
        current = self.config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set(self, path: str, value: Any):
        """Set configuration value by dot-separated path"""
        keys = path.split('.')
        self._set_nested_config(keys, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.config.get(section, {})
    
    def validate(self) -> tuple[bool, list]:
        """Validate configuration values"""
        errors = []
        
        # Validate pipeline settings
        if self.get('pipeline.max_workers', 0) <= 0:
            errors.append("pipeline.max_workers must be > 0")
        
        if self.get('pipeline.batch_size', 0) <= 0:
            errors.append("pipeline.batch_size must be > 0")
        
        # Validate rate limiting
        if self.get('rate_limiting.article_delay', 0) < 0:
            errors.append("rate_limiting.article_delay must be >= 0")
        
        # Validate database settings
        if self.get('database.connection_timeout', 0) <= 0:
            errors.append("database.connection_timeout must be > 0")
        
        # Validate performance limits
        memory_limit = self.get('performance.memory_limit_mb', 0)
        if memory_limit <= 0:
            errors.append("performance.memory_limit_mb must be > 0")
        
        return len(errors) == 0, errors
    
    def save_to_file(self, file_path: str):
        """Save current configuration to file"""
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata
            config_with_meta = {
                '_metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'version': '1.0'
                },
                **self.config
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_with_meta, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Configuration saved to {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
            raise
    
    def create_sample_config(self, file_path: str):
        """Create sample configuration file"""
        sample_config = {
            '_metadata': {
                'description': 'Naver Land Data Pipeline Configuration',
                'version': '1.0',
                'created_at': datetime.now().isoformat()
            },
            'pipeline': {
                'max_workers': 3,
                'batch_size': 15,
                'max_retries': 3,
                'checkpoint_interval': 50,
                'progress_report_interval': 25
            },
            'rate_limiting': {
                'region_delay': 3.0,
                'article_delay': 1.5,
                'api_delay_min': 1.0,
                'api_delay_max': 2.0
            },
            'database': {
                'batch_size': 25,
                'connection_timeout': 30,
                'constraint_validation': True
            },
            'monitoring': {
                'metrics_retention_hours': 12,
                'alert_cooldown_minutes': 10,
                'health_check_interval': 60
            },
            'quality': {
                'min_data_completeness': 0.8,
                'validation_strict': False
            },
            'logging': {
                'level': 'INFO',
                'file_rotation': True
            }
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Sample configuration created at {file_path}")
            print(f"   Edit this file to customize your pipeline settings")
            
        except Exception as e:
            logger.error(f"❌ Failed to create sample config: {e}")
    
    def print_summary(self):
        """Print configuration summary"""
        print("\n" + "="*50)
        print("⚙️ PIPELINE CONFIGURATION SUMMARY")
        print("="*50)
        
        # Pipeline settings
        pipeline = self.get_section('pipeline')
        print(f"🔧 Pipeline: {pipeline['max_workers']} workers, batch size {pipeline['batch_size']}")
        
        # Rate limiting
        rate_limiting = self.get_section('rate_limiting')
        print(f"⏱️ Rate Limiting: {rate_limiting['article_delay']}s per article")
        
        # Database
        database = self.get_section('database')
        print(f"🗄️ Database: {database['batch_size']} batch size, {database['connection_timeout']}s timeout")
        
        # Monitoring
        monitoring = self.get_section('monitoring')
        print(f"📊 Monitoring: {monitoring['metrics_retention_hours']}h retention")
        
        # Performance
        performance = self.get_section('performance')
        print(f"⚡ Performance: {performance['memory_limit_mb']}MB memory limit")
        
        print("="*50)

# Global configuration instance
_global_config = None

def get_config() -> PipelineConfig:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = PipelineConfig()
    return _global_config

def init_config(config_file: Optional[str] = None) -> PipelineConfig:
    """Initialize global configuration"""
    global _global_config
    _global_config = PipelineConfig(config_file)
    return _global_config

def create_sample_config():
    """Create sample configuration file in current directory"""
    config = PipelineConfig()
    config.create_sample_config('config.json')

# Command line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'create-sample':
        create_sample_config()
    else:
        # Test configuration
        config = PipelineConfig()
        
        # Validate
        is_valid, errors = config.validate()
        if not is_valid:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✅ Configuration is valid")
        
        # Print summary
        config.print_summary()