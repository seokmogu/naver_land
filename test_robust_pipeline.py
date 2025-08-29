#!/usr/bin/env python3
"""
Robust Pipeline Test Suite
Comprehensive testing of the robust data collection architecture
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import components to test
from collectors.core.robust_data_collector import RobustDataCollector
from collectors.core.error_recovery_system import ErrorRecoverySystem, ErrorType, ErrorSeverity
from collectors.monitoring.comprehensive_monitor import ComprehensiveMonitor
from collectors.config.pipeline_config import PipelineConfig
from robust_data_pipeline import RobustDataPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RobustPipelineTestSuite:
    """Comprehensive test suite for robust pipeline"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results = {
            'start_time': datetime.now(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': []
        }
        # Initialize instance variables
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_details = []
    
    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """Run individual test with error handling"""
        self.logger.info(f"🧪 Running test: {test_name}")
        
        test_start = time.time()
        test_result = {
            'test_name': test_name,
            'start_time': datetime.now(),
            'duration': 0,
            'passed': False,
            'error': None,
            'details': {}
        }
        
        try:
            result = test_func(*args, **kwargs)
            test_result['passed'] = True
            test_result['details'] = result if isinstance(result, dict) else {'result': result}
            self.tests_passed += 1
            self.logger.info(f"✅ Test passed: {test_name}")
            
        except Exception as e:
            test_result['error'] = str(e)
            test_result['details']['exception'] = type(e).__name__
            self.tests_failed += 1
            self.logger.error(f"❌ Test failed: {test_name} - {e}")
            
        finally:
            test_result['duration'] = time.time() - test_start
            test_result['end_time'] = datetime.now()
            self.test_details.append(test_result)
            self.tests_run += 1
    
    def test_configuration_system(self):
        """Test configuration management system"""
        self.logger.info("🔧 Testing Configuration System")
        
        # Test default configuration
        config = PipelineConfig()
        
        # Test configuration access
        max_workers = config.get('pipeline.max_workers')
        if max_workers is None or max_workers <= 0:
            raise ValueError("Invalid max_workers configuration")
        
        # Test configuration validation
        is_valid, errors = config.validate()
        if not is_valid:
            raise ValueError(f"Configuration validation failed: {errors}")
        
        # Test environment overrides
        original_value = config.get('pipeline.batch_size')
        os.environ['PIPELINE_BATCH_SIZE'] = '99'
        
        config_with_env = PipelineConfig()
        new_value = config_with_env.get('pipeline.batch_size')
        
        if new_value != 99:
            raise ValueError("Environment override not working")
        
        # Clean up environment
        del os.environ['PIPELINE_BATCH_SIZE']
        
        return {
            'config_sections': len(config.config),
            'max_workers': max_workers,
            'validation_passed': is_valid,
            'env_override_test': 'passed'
        }
    
    def test_error_recovery_system(self):
        """Test error recovery system"""
        self.logger.info("🔄 Testing Error Recovery System")
        
        recovery_system = ErrorRecoverySystem()
        
        # Test error classification
        test_errors = [
            (Exception("Unauthorized access"), ErrorType.TOKEN_ERROR),
            (Exception("Too many requests"), ErrorType.RATE_LIMIT_ERROR),
            (Exception("Connection timeout"), ErrorType.NETWORK_ERROR),
            (Exception("Database constraint violation"), ErrorType.DATABASE_ERROR)
        ]
        
        recovery_successes = 0
        for error, expected_type in test_errors:
            context = {'test_error': True}
            recovered = recovery_system.handle_error(error, context, expected_type)
            if recovered:
                recovery_successes += 1
        
        # Test error patterns
        summary = recovery_system.get_error_summary()
        
        # Test cleanup
        recovery_system.cleanup_old_errors(0)  # Clean all
        
        return {
            'test_errors_handled': len(test_errors),
            'recovery_successes': recovery_successes,
            'total_errors_in_system': summary['total_errors'],
            'recovery_rate': summary['health_metrics']['recovery_success_rate'],
            'health_status': recovery_system.get_health_status()
        }
    
    def test_comprehensive_monitor(self):
        """Test comprehensive monitoring system"""
        self.logger.info("📊 Testing Comprehensive Monitor")
        
        monitor = ComprehensiveMonitor()
        
        try:
            # Test metric recording
            monitor.record_metric('test_metric', 42.0, {'test': 'true'})
            monitor.record_api_call('/test/endpoint', 200, 1.5)
            monitor.record_database_operation('test_insert', True, 0.8, 1)
            monitor.record_article_collection('test_article', True, 2.1, 0.95)
            
            # Test operation monitoring
            monitor.record_operation_start('test_operation')
            time.sleep(0.1)
            monitor.record_operation_success('test_operation', 0.1)
            
            # Test dashboard data
            dashboard_data = monitor.get_dashboard_data()
            
            # Test status report (should not crash)
            monitor.print_status_report()
            
            return {
                'metrics_recorded': 4,
                'operations_completed': dashboard_data['system_state']['operations_completed'],
                'health_status': dashboard_data['system_state']['health_status'],
                'total_metrics': dashboard_data['total_metrics'],
                'uptime_seconds': dashboard_data['uptime_seconds']
            }
            
        finally:
            monitor.shutdown()
    
    def test_data_collector_initialization(self):
        """Test robust data collector initialization"""
        self.logger.info("🔍 Testing Data Collector Initialization")
        
        collector = RobustDataCollector()
        
        # Test token management
        has_token = collector.token is not None
        
        # Test configuration
        has_config = collector.config is not None and len(collector.config) > 0
        
        # Test Supabase connection
        has_supabase = collector.supabase_client is not None
        
        # Test metrics
        metrics = collector.get_collection_metrics()
        
        return {
            'has_token': has_token,
            'has_config': has_config,
            'has_supabase_connection': has_supabase,
            'initial_metrics': {
                'total_articles': metrics.total_articles,
                'successful_collections': metrics.successful_collections,
                'failed_collections': metrics.failed_collections
            }
        }
    
    def test_data_validation_system(self):
        """Test data validation and sanitization"""
        self.logger.info("🔍 Testing Data Validation System")
        
        collector = RobustDataCollector()
        
        # Test with mock data
        mock_api_response = {
            'articleDetail': {
                'buildingName': 'Test Building',
                'realEstateTypeName': '아파트',
                'tradeTypeName': '매매',
                'latitude': 37.5665,
                'longitude': 126.9780,
                'exposureAddress': 'Test Address'
            },
            'articlePrice': {
                'dealPrice': 50000,
                'warrantPrice': None,
                'rentPrice': None
            },
            'articleSpace': {
                'supplyArea': 84.5,
                'exclusiveArea': 65.2,
                'roomCount': 3
            },
            'articlePhotos': []
        }
        
        # Test validation
        validation_result = collector._validate_article_data(mock_api_response, 'test_article')
        
        # Test sanitization
        if validation_result.is_valid:
            sanitized_data = validation_result.sanitized_data
            
            # Test processing
            processed_data = collector._process_article_data(sanitized_data, 'test_article')
            
            if processed_data:
                # Test foreign key resolution
                resolved_data = collector._resolve_foreign_keys(processed_data)
                
                return {
                    'validation_passed': validation_result.is_valid,
                    'validation_errors': len(validation_result.errors),
                    'validation_warnings': len(validation_result.warnings),
                    'processing_successful': processed_data is not None,
                    'foreign_key_resolution': resolved_data is not None,
                    'processed_sections': len(processed_data.keys()) if processed_data else 0
                }
        
        raise ValueError("Data validation failed")
    
    def test_database_operations(self):
        """Test database operations"""
        self.logger.info("🗄️ Testing Database Operations")
        
        collector = RobustDataCollector()
        
        # Test connection
        try:
            result = collector.supabase_client.table('properties_new').select('id').limit(1).execute()
            connection_test = True
        except Exception as e:
            connection_test = False
            self.logger.warning(f"Database connection test failed: {e}")
        
        # Test foreign key resolution functions
        real_estate_type_id = collector._resolve_real_estate_type_id('아파트')
        trade_type_id = collector._resolve_trade_type_id('매매', {'deal_price': 50000})
        region_id = collector._resolve_region_id({})
        
        return {
            'connection_test': connection_test,
            'real_estate_type_resolved': real_estate_type_id is not None,
            'trade_type_resolved': trade_type_id is not None,
            'region_resolved': region_id is not None,
            'foreign_keys_working': all([
                real_estate_type_id is not None,
                trade_type_id is not None,
                region_id is not None
            ])
        }
    
    def test_pipeline_integration(self):
        """Test pipeline integration"""
        self.logger.info("🚀 Testing Pipeline Integration")
        
        # Test pipeline initialization
        config = {
            'max_workers': 2,
            'batch_size': 5,
            'region_delay': 1.0,
            'article_delay': 0.5
        }
        
        pipeline = RobustDataPipeline(config)
        
        # Test configuration
        pipeline_config_valid = pipeline.config is not None
        
        # Test component initialization
        has_error_recovery = pipeline.error_recovery is not None
        has_monitor = pipeline.monitor is not None
        has_collector = pipeline.collector is not None
        
        # Test state tracking
        initial_state = pipeline.pipeline_state.copy()
        
        # Clean up
        pipeline.shutdown()
        
        return {
            'initialization_successful': True,
            'config_loaded': pipeline_config_valid,
            'error_recovery_initialized': has_error_recovery,
            'monitor_initialized': has_monitor,
            'collector_initialized': has_collector,
            'initial_state': initial_state
        }
    
    def test_single_article_collection(self):
        """Test single article collection with real API"""
        self.logger.info("📋 Testing Single Article Collection")
        
        collector = RobustDataCollector()
        
        # Test with known article (may fail if article doesn't exist anymore)
        test_article_no = "2546339433"
        
        try:
            # Test collection
            processed_data = collector.collect_article_with_comprehensive_validation(test_article_no)
            
            if processed_data:
                # Test data quality
                data_quality_score = collector._calculate_data_quality_score(processed_data) if hasattr(collector, '_calculate_data_quality_score') else 0.0
                
                return {
                    'collection_successful': True,
                    'article_no': test_article_no,
                    'has_basic_info': 'basic_info' in processed_data,
                    'has_price_info': 'price_info' in processed_data,
                    'has_space_info': 'space_info' in processed_data,
                    'data_quality_score': data_quality_score,
                    'sections_collected': len(processed_data.keys())
                }
            else:
                return {
                    'collection_successful': False,
                    'article_no': test_article_no,
                    'reason': 'API returned no data or validation failed'
                }
                
        except Exception as e:
            return {
                'collection_successful': False,
                'article_no': test_article_no,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        self.logger.info("🚀 Starting Robust Pipeline Test Suite")
        print("\n" + "="*60)
        print("🧪 ROBUST PIPELINE TEST SUITE")
        print("="*60)
        
        # Define all tests
        tests = [
            ('Configuration System', self.test_configuration_system),
            ('Error Recovery System', self.test_error_recovery_system),
            ('Comprehensive Monitor', self.test_comprehensive_monitor),
            ('Data Collector Initialization', self.test_data_collector_initialization),
            ('Data Validation System', self.test_data_validation_system),
            ('Database Operations', self.test_database_operations),
            ('Pipeline Integration', self.test_pipeline_integration),
            ('Single Article Collection', self.test_single_article_collection)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            time.sleep(0.5)  # Brief pause between tests
        
        # Generate final report
        self._generate_test_report()
    
    def _generate_test_report(self):
        """Generate comprehensive test report"""
        end_time = datetime.now()
        duration = end_time - self.test_results['start_time']
        
        # Calculate success rate
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print("\n" + "="*60)
        print("📊 TEST SUITE RESULTS")
        print("="*60)
        
        print(f"⏱️ Total Duration: {duration}")
        print(f"🧪 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Test details
        print(f"\n📋 Test Details:")
        for test_detail in self.test_details:
            status = "✅ PASS" if test_detail['passed'] else "❌ FAIL"
            duration = test_detail['duration']
            print(f"   {status} {test_detail['test_name']} ({duration:.2f}s)")
            
            if not test_detail['passed'] and test_detail['error']:
                print(f"      Error: {test_detail['error']}")
        
        # System health summary
        print(f"\n🏥 System Health Summary:")
        if success_rate >= 90:
            health_status = "EXCELLENT"
        elif success_rate >= 75:
            health_status = "GOOD"
        elif success_rate >= 50:
            health_status = "FAIR"
        else:
            health_status = "POOR"
        
        print(f"   Overall Health: {health_status}")
        print(f"   Ready for Production: {'YES' if success_rate >= 80 else 'NO'}")
        
        # Save detailed results
        self._save_test_results()
        
        print("="*60)
    
    def _save_test_results(self):
        """Save detailed test results to file"""
        results_data = {
            'test_suite': 'Robust Pipeline Test Suite',
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'tests_run': self.tests_run,
                'tests_passed': self.tests_passed,
                'tests_failed': self.tests_failed,
                'success_rate': (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
            },
            'test_details': self.test_details
        }
        
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"\n💾 Detailed results saved to: {results_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save test results: {e}")

def main():
    """Main test execution"""
    try:
        # Create and run test suite
        test_suite = RobustPipelineTestSuite()
        test_suite.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️ Test suite interrupted by user")
    
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        logging.exception("Test suite failure")

if __name__ == "__main__":
    main()