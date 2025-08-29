#!/usr/bin/env python3
"""
Robust Data Pipeline - Enterprise-Grade Data Collection System
Integrates all backend components for reliable data collection and storage
"""

import os
import sys
import json
import time
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Generator
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import all components
from collectors.core.robust_data_collector import RobustDataCollector
from collectors.core.error_recovery_system import ErrorRecoverySystem, ErrorType, ErrorSeverity
from collectors.monitoring.comprehensive_monitor import ComprehensiveMonitor, OperationMonitor

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('robust_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RobustDataPipeline:
    """Enterprise-grade data collection pipeline"""
    
    def __init__(self, config: Dict = None):
        """Initialize robust data pipeline with all components"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load configuration
        self.config = self._load_configuration(config)
        
        # Initialize core components
        self.logger.info("🚀 Initializing Robust Data Pipeline...")
        
        # 1. Error Recovery System
        self.error_recovery = ErrorRecoverySystem()
        
        # 2. Comprehensive Monitor
        self.monitor = ComprehensiveMonitor()
        
        # 3. Data Collector
        self.collector = RobustDataCollector()
        
        # Pipeline state
        self.pipeline_state = {
            'start_time': datetime.now(),
            'is_running': False,
            'total_processed': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'current_region': None,
            'regions_completed': 0,
            'estimated_completion': None
        }
        
        # Thread management
        self.executor = ThreadPoolExecutor(max_workers=self.config['max_workers'])
        self.shutdown_event = threading.Event()
        
        self.logger.info("✅ Robust Data Pipeline initialized successfully")
    
    def _load_configuration(self, config: Dict = None) -> Dict:
        """Load pipeline configuration with defaults"""
        default_config = {
            'max_workers': 5,
            'batch_size': 20,
            'region_delay': 5.0,
            'article_delay': 2.0,
            'max_retries': 3,
            'enable_recovery': True,
            'enable_monitoring': True,
            'checkpoint_interval': 100,
            'progress_report_interval': 50
        }
        
        if config:
            default_config.update(config)
        
        return default_config
    
    def collect_region_comprehensive(self, cortar_no: str, region_name: str, 
                                   max_pages: int = None) -> Dict:
        """
        Comprehensive region collection with full error handling and monitoring
        
        Args:
            cortar_no: Region code
            region_name: Human-readable region name
            max_pages: Maximum pages to collect (None for all)
        
        Returns:
            Dict: Collection results and statistics
        """
        
        collection_start = time.time()
        self.pipeline_state['current_region'] = region_name
        self.pipeline_state['is_running'] = True
        
        with OperationMonitor(self.monitor, "region_collection", 
                            {"region": region_name, "cortar_no": cortar_no}):
            
            self.logger.info(f"🏠 Starting comprehensive collection: {region_name} ({cortar_no})")
            
            try:
                # Initialize region statistics
                region_stats = {
                    'region_name': region_name,
                    'cortar_no': cortar_no,
                    'start_time': datetime.now(),
                    'articles_found': 0,
                    'articles_processed': 0,
                    'articles_successful': 0,
                    'articles_failed': 0,
                    'pages_processed': 0,
                    'api_calls': 0,
                    'database_saves': 0,
                    'errors_by_type': {},
                    'processing_times': []
                }
                
                # Phase 1: Collect article list with pagination
                all_articles = self._collect_region_articles_paginated(
                    cortar_no, region_name, max_pages, region_stats
                )
                
                region_stats['articles_found'] = len(all_articles)
                
                if not all_articles:
                    self.logger.warning(f"⚠️ No articles found for {region_name}")
                    return self._finalize_region_results(region_stats, collection_start)
                
                # Phase 2: Process articles in batches with comprehensive error handling
                self._process_articles_in_batches(all_articles, region_stats)
                
                # Phase 3: Finalize and return results
                return self._finalize_region_results(region_stats, collection_start)
                
            except Exception as e:
                # Handle catastrophic errors
                self.error_recovery.handle_error(
                    e, 
                    {"operation": "region_collection", "region": region_name},
                    ErrorType.UNKNOWN_ERROR,
                    ErrorSeverity.CRITICAL
                )
                
                region_stats['catastrophic_error'] = str(e)
                return self._finalize_region_results(region_stats, collection_start)
            
            finally:
                self.pipeline_state['is_running'] = False
                self.pipeline_state['regions_completed'] += 1
    
    def _collect_region_articles_paginated(self, cortar_no: str, region_name: str, 
                                         max_pages: int, region_stats: Dict) -> List[str]:
        """Collect all article numbers from region with pagination"""
        
        all_articles = []
        page = 1
        
        while max_pages is None or page <= max_pages:
            
            if self.shutdown_event.is_set():
                self.logger.info("🛑 Shutdown requested during article collection")
                break
            
            with OperationMonitor(self.monitor, "collect_page", 
                                {"region": region_name, "page": page}):
                
                try:
                    self.logger.info(f"📄 Collecting {region_name} page {page}...")
                    
                    # Get single page articles
                    page_articles = self._collect_single_page_with_retry(cortar_no, page)
                    
                    if not page_articles:
                        self.logger.info(f"📄 No more articles on page {page}")
                        break
                    
                    all_articles.extend(page_articles)
                    region_stats['pages_processed'] += 1
                    region_stats['api_calls'] += 1
                    
                    self.logger.info(f"📄 Page {page}: {len(page_articles)} articles collected")
                    
                    # Rate limiting
                    time.sleep(self.config['region_delay'])
                    page += 1
                    
                except Exception as e:
                    error_context = {
                        "operation": "page_collection",
                        "region": region_name,
                        "page": page
                    }
                    
                    recovered = self.error_recovery.handle_error(
                        e, error_context, self._classify_collection_error(e), ErrorSeverity.MEDIUM
                    )
                    
                    if not recovered:
                        self.logger.error(f"❌ Failed to collect page {page}, stopping pagination")
                        break
                    
                    page += 1  # Continue to next page even after error
        
        self.logger.info(f"📊 {region_name}: Found {len(all_articles)} total articles across {region_stats['pages_processed']} pages")
        return all_articles
    
    def _collect_single_page_with_retry(self, cortar_no: str, page: int) -> List[str]:
        """Collect single page with comprehensive retry logic"""
        
        for attempt in range(self.config['max_retries']):
            try:
                # Use the collector's single page method
                articles = self.collector.collect_single_page_articles(cortar_no, page)
                
                if articles is not None:
                    return articles
                
            except Exception as e:
                self.logger.warning(f"⚠️ Page collection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config['max_retries'] - 1:
                    delay = (2 ** attempt) * self.config['region_delay']
                    time.sleep(delay)
                else:
                    raise e
        
        return []
    
    def _process_articles_in_batches(self, articles: List[str], region_stats: Dict):
        """Process articles in batches with parallel processing and error handling"""
        
        batch_size = self.config['batch_size']
        total_batches = (len(articles) + batch_size - 1) // batch_size
        
        self.logger.info(f"🔄 Processing {len(articles)} articles in {total_batches} batches")
        
        for batch_num in range(total_batches):
            
            if self.shutdown_event.is_set():
                self.logger.info("🛑 Shutdown requested during batch processing")
                break
            
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(articles))
            batch_articles = articles[start_idx:end_idx]
            
            with OperationMonitor(self.monitor, "process_batch", 
                                {"batch": batch_num + 1, "size": len(batch_articles)}):
                
                self.logger.info(f"📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_articles)} articles)")
                
                batch_start = time.time()
                
                # Process batch with thread pool
                batch_results = self._process_batch_parallel(batch_articles, region_stats)
                
                batch_duration = time.time() - batch_start
                region_stats['processing_times'].append(batch_duration)
                
                # Update statistics
                region_stats['articles_processed'] += len(batch_articles)
                region_stats['articles_successful'] += batch_results['successful']
                region_stats['articles_failed'] += batch_results['failed']
                
                self.logger.info(f"✅ Batch {batch_num + 1} completed: {batch_results['successful']}/{len(batch_articles)} successful ({batch_duration:.2f}s)")
                
                # Progress reporting
                if (batch_num + 1) % self.config['progress_report_interval'] == 0:
                    self._print_progress_report(region_stats, len(articles))
                
                # Checkpoint
                if (batch_num + 1) % self.config['checkpoint_interval'] == 0:
                    self._create_checkpoint(region_stats)
    
    def _process_batch_parallel(self, articles: List[str], region_stats: Dict) -> Dict:
        """Process batch of articles in parallel"""
        
        batch_results = {'successful': 0, 'failed': 0, 'errors': []}
        
        # Submit all articles to thread pool
        futures = []
        for article_no in articles:
            future = self.executor.submit(self._process_single_article_safe, article_no, region_stats)
            futures.append((future, article_no))
        
        # Collect results
        for future, article_no in futures:
            try:
                success = future.result(timeout=60)  # 60 second timeout per article
                
                if success:
                    batch_results['successful'] += 1
                else:
                    batch_results['failed'] += 1
                    
            except Exception as e:
                batch_results['failed'] += 1
                batch_results['errors'].append(f"Article {article_no}: {str(e)}")
                self.logger.error(f"❌ Article {article_no} processing failed: {e}")
        
        return batch_results
    
    def _process_single_article_safe(self, article_no: str, region_stats: Dict) -> bool:
        """Safely process single article with comprehensive error handling"""
        
        article_start = time.time()
        
        try:
            with self.error_recovery.error_context("article_processing", article_no=article_no):
                
                # 1. Collect article data
                processed_data = self.collector.collect_article_with_comprehensive_validation(article_no)
                
                if not processed_data:
                    self.monitor.record_article_collection(article_no, False, time.time() - article_start)
                    return False
                
                # 2. Save to database
                success = self.collector.save_to_database_with_transaction(processed_data)
                
                # 3. Record metrics
                duration = time.time() - article_start
                data_quality_score = self._calculate_data_quality_score(processed_data)
                
                self.monitor.record_article_collection(article_no, success, duration, data_quality_score)
                
                # 4. Update pipeline state
                if success:
                    self.pipeline_state['successful_collections'] += 1
                else:
                    self.pipeline_state['failed_collections'] += 1
                
                self.pipeline_state['total_processed'] += 1
                
                # Rate limiting
                time.sleep(self.config['article_delay'])
                
                return success
        
        except Exception as e:
            # Error already handled by error_context, just record the failure
            duration = time.time() - article_start
            self.monitor.record_article_collection(article_no, False, duration)
            
            self.pipeline_state['failed_collections'] += 1
            self.pipeline_state['total_processed'] += 1
            
            return False
    
    def _calculate_data_quality_score(self, processed_data: Dict) -> float:
        """Calculate data quality score based on completeness and validity"""
        
        score = 0.0
        max_score = 100.0
        
        # Basic info completeness (30 points)
        basic_info = processed_data.get('basic_info', {})
        basic_fields = ['building_name', 'real_estate_type', 'trade_type', 'address']
        basic_score = sum(30/len(basic_fields) for field in basic_fields if basic_info.get(field))
        score += basic_score
        
        # Price info completeness (25 points)
        price_info = processed_data.get('price_info', {})
        if price_info.get('deal_price') or price_info.get('rent_price') or price_info.get('warrant_price'):
            score += 25
        
        # Space info completeness (20 points)
        space_info = processed_data.get('space_info', {})
        if space_info.get('exclusive_area') and space_info.get('room_count'):
            score += 20
        
        # Photo info completeness (15 points)
        photo_info = processed_data.get('photo_info', {})
        if photo_info.get('photo_count', 0) > 0:
            score += 15
        
        # Realtor info completeness (10 points)
        realtor_info = processed_data.get('realtor_info', {})
        if realtor_info.get('office_name'):
            score += 10
        
        return min(score, max_score)
    
    def _classify_collection_error(self, error: Exception) -> ErrorType:
        """Classify collection errors"""
        error_str = str(error).lower()
        
        if 'token' in error_str or 'unauthorized' in error_str:
            return ErrorType.TOKEN_ERROR
        elif 'rate limit' in error_str or '429' in error_str:
            return ErrorType.RATE_LIMIT_ERROR
        elif 'network' in error_str or 'timeout' in error_str:
            return ErrorType.NETWORK_ERROR
        elif 'database' in error_str or 'constraint' in error_str:
            return ErrorType.DATABASE_ERROR
        elif 'api' in error_str or 'request' in error_str:
            return ErrorType.API_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _finalize_region_results(self, region_stats: Dict, collection_start: float) -> Dict:
        """Finalize region collection results"""
        
        region_stats['end_time'] = datetime.now()
        region_stats['total_duration'] = time.time() - collection_start
        
        # Calculate success rate
        if region_stats['articles_processed'] > 0:
            region_stats['success_rate'] = (
                region_stats['articles_successful'] / region_stats['articles_processed'] * 100
            )
        else:
            region_stats['success_rate'] = 0.0
        
        # Calculate average processing time
        if region_stats['processing_times']:
            region_stats['avg_batch_time'] = sum(region_stats['processing_times']) / len(region_stats['processing_times'])
        else:
            region_stats['avg_batch_time'] = 0.0
        
        # Log final results
        self.logger.info(f"✅ {region_stats['region_name']} collection completed")
        self.logger.info(f"   📊 Processed: {region_stats['articles_processed']}/{region_stats['articles_found']}")
        self.logger.info(f"   ✅ Success Rate: {region_stats['success_rate']:.1f}%")
        self.logger.info(f"   ⏱️ Duration: {region_stats['total_duration']:.2f}s")
        
        return region_stats
    
    def _print_progress_report(self, region_stats: Dict, total_articles: int):
        """Print progress report"""
        processed = region_stats['articles_processed']
        successful = region_stats['articles_successful']
        progress = (processed / total_articles * 100) if total_articles > 0 else 0
        success_rate = (successful / processed * 100) if processed > 0 else 0
        
        self.logger.info(f"📊 Progress Report:")
        self.logger.info(f"   🔄 Articles: {processed}/{total_articles} ({progress:.1f}%)")
        self.logger.info(f"   ✅ Success Rate: {success_rate:.1f}%")
        self.logger.info(f"   📈 Pipeline Success Rate: {self.collector.get_collection_metrics().success_rate:.1f}%")
    
    def _create_checkpoint(self, region_stats: Dict):
        """Create checkpoint for recovery"""
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'region_stats': region_stats,
            'pipeline_state': self.pipeline_state,
            'collector_metrics': self.collector.get_collection_metrics().__dict__,
            'monitor_data': self.monitor.get_dashboard_data()
        }
        
        checkpoint_path = f"checkpoint_{region_stats['cortar_no']}_{int(time.time())}.json"
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            
            self.logger.info(f"💾 Checkpoint saved: {checkpoint_path}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save checkpoint: {e}")
    
    def collect_gangnam_full_robust(self) -> Dict:
        """Collect all Gangnam districts with robust error handling"""
        
        gangnam_regions = [
            {"name": "역삼동", "cortar_no": "1168010100"},
            {"name": "삼성동", "cortar_no": "1168010500"}, 
            {"name": "논현동", "cortar_no": "1168010800"},
            {"name": "대치동", "cortar_no": "1168010600"},
            {"name": "신사동", "cortar_no": "1168010700"},
            {"name": "압구정동", "cortar_no": "1168011000"},
            {"name": "청담동", "cortar_no": "1168010400"},
            {"name": "도곡동", "cortar_no": "1168011800"},
            {"name": "개포동", "cortar_no": "1168010300"},
            {"name": "수서동", "cortar_no": "1168011500"},
        ]
        
        pipeline_start = time.time()
        total_results = {
            'start_time': datetime.now(),
            'regions': [],
            'summary': {
                'total_regions': len(gangnam_regions),
                'completed_regions': 0,
                'total_articles': 0,
                'successful_articles': 0,
                'failed_articles': 0,
                'overall_success_rate': 0.0
            }
        }
        
        self.logger.info(f"🚀 Starting Gangnam Full Collection ({len(gangnam_regions)} regions)")
        
        for region_info in gangnam_regions:
            
            if self.shutdown_event.is_set():
                self.logger.info("🛑 Pipeline shutdown requested")
                break
            
            region_name = region_info["name"]
            cortar_no = region_info["cortar_no"]
            
            self.logger.info(f"\n🏠 Starting region: {region_name}")
            
            # Collect region with comprehensive error handling
            region_result = self.collect_region_comprehensive(cortar_no, region_name)
            
            # Add to results
            total_results['regions'].append(region_result)
            total_results['summary']['completed_regions'] += 1
            total_results['summary']['total_articles'] += region_result.get('articles_found', 0)
            total_results['summary']['successful_articles'] += region_result.get('articles_successful', 0)
            total_results['summary']['failed_articles'] += region_result.get('articles_failed', 0)
            
            self.logger.info(f"✅ {region_name} completed")
            
            # Brief pause between regions
            time.sleep(10)
        
        # Finalize results
        total_results['end_time'] = datetime.now()
        total_results['total_duration'] = time.time() - pipeline_start
        
        if total_results['summary']['total_articles'] > 0:
            total_results['summary']['overall_success_rate'] = (
                total_results['summary']['successful_articles'] / 
                total_results['summary']['total_articles'] * 100
            )
        
        # Generate final report
        self._generate_final_report(total_results)
        
        return total_results
    
    def _generate_final_report(self, results: Dict):
        """Generate comprehensive final report"""
        
        print("\n" + "="*80)
        print("🎉 ROBUST DATA PIPELINE - FINAL REPORT")
        print("="*80)
        
        summary = results['summary']
        duration = results['total_duration']
        
        print(f"⏱️ Total Duration: {timedelta(seconds=int(duration))}")
        print(f"🏠 Regions Processed: {summary['completed_regions']}/{summary['total_regions']}")
        print(f"📊 Articles Found: {summary['total_articles']:,}")
        print(f"✅ Successfully Processed: {summary['successful_articles']:,}")
        print(f"❌ Failed: {summary['failed_articles']:,}")
        print(f"📈 Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        
        # Region breakdown
        print(f"\n📍 Region Breakdown:")
        for region_result in results['regions']:
            name = region_result['region_name']
            success_rate = region_result.get('success_rate', 0)
            processed = region_result.get('articles_processed', 0)
            found = region_result.get('articles_found', 0)
            
            print(f"   {name}: {processed}/{found} articles, {success_rate:.1f}% success rate")
        
        # System health
        monitor_data = self.monitor.get_dashboard_data()
        print(f"\n🏥 System Health:")
        print(f"   Status: {monitor_data['system_state']['health_status']}")
        print(f"   Total Errors: {monitor_data['system_state']['total_errors']}")
        print(f"   Operations Completed: {monitor_data['system_state']['operations_completed']}")
        
        # Error recovery
        recovery_summary = self.error_recovery.get_error_summary()
        print(f"\n🔄 Error Recovery:")
        print(f"   Total Errors Handled: {recovery_summary['total_errors']}")
        print(f"   Recovery Success Rate: {recovery_summary['health_metrics']['recovery_success_rate']:.1f}%")
        
        print("="*80)
        
        # Export detailed results
        results_path = f"robust_pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"📊 Detailed results saved to: {results_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save results: {e}")
    
    def shutdown(self):
        """Graceful shutdown of pipeline"""
        self.logger.info("🛑 Initiating pipeline shutdown...")
        
        self.shutdown_event.set()
        
        # Shutdown components
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        
        if hasattr(self, 'monitor'):
            self.monitor.shutdown()
        
        self.logger.info("✅ Pipeline shutdown completed")

# Main execution function
def main():
    """Main execution function"""
    print("🚀 ROBUST DATA PIPELINE - STARTING")
    print("="*60)
    
    pipeline = None
    
    try:
        # Initialize pipeline
        config = {
            'max_workers': 3,
            'batch_size': 15,
            'region_delay': 3.0,
            'article_delay': 1.5,
            'max_retries': 3
        }
        
        pipeline = RobustDataPipeline(config)
        
        # Start comprehensive collection
        results = pipeline.collect_gangnam_full_robust()
        
        print("✅ Pipeline completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrupted by user")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        logging.exception("Pipeline failure")
        
    finally:
        if pipeline:
            pipeline.shutdown()

if __name__ == "__main__":
    main()