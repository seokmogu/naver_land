#!/usr/bin/env python3
"""
DATABASE MAINTENANCE SCHEDULER
Automated database optimization and maintenance tasks
- Scheduled VACUUM and ANALYZE operations
- Index maintenance and rebuilding
- Statistics update automation  
- Performance monitoring automation
- Dead row cleanup and table bloat management
"""

import psycopg2
import psycopg2.extras
import asyncio
import asyncpg
import schedule
import time
import threading
import logging
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import json
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MaintenanceConfig:
    """Database maintenance configuration"""
    database_url: str
    
    # Scheduling configuration
    vacuum_schedule: str = "daily"  # daily, weekly, custom
    analyze_schedule: str = "daily"
    reindex_schedule: str = "weekly"
    stats_collection_schedule: str = "hourly"
    
    # Custom schedule times (24-hour format)
    vacuum_time: str = "02:00"  # 2 AM
    analyze_time: str = "03:00"  # 3 AM  
    reindex_time: str = "04:00"  # 4 AM (weekly)
    stats_time: str = "*/2"     # Every 2 hours
    
    # Maintenance thresholds
    dead_tuple_threshold: float = 0.1  # 10% dead tuples triggers vacuum
    table_bloat_threshold: float = 0.2  # 20% bloat triggers action
    index_bloat_threshold: float = 0.3  # 30% index bloat
    
    # Performance settings
    maintenance_work_mem: str = "256MB"
    max_maintenance_connections: int = 2
    vacuum_cost_delay: int = 10  # Lower = faster vacuum
    vacuum_cost_limit: int = 2000
    
    # Logging and monitoring
    log_maintenance_operations: bool = True
    send_notifications: bool = True
    maintenance_log_retention_days: int = 30
    
    # Safety settings
    skip_during_peak_hours: bool = True
    peak_hours_start: str = "08:00"
    peak_hours_end: str = "18:00"
    max_maintenance_duration_hours: int = 4

@dataclass
class MaintenanceResult:
    """Result of maintenance operation"""
    operation: str
    table_name: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    rows_processed: int
    success: bool
    error_message: Optional[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass  
class TableMaintenanceStats:
    """Table maintenance statistics"""
    table_name: str
    table_size_bytes: int
    dead_tuples: int
    live_tuples: int
    dead_tuple_ratio: float
    last_vacuum: Optional[datetime]
    last_analyze: Optional[datetime]
    maintenance_priority: int  # 1-10, higher = more urgent
    recommended_actions: List[str]

class DatabaseMaintenanceScheduler:
    """Automated database maintenance and optimization scheduler"""
    
    def __init__(self, config: MaintenanceConfig):
        self.config = config
        self.maintenance_history: List[MaintenanceResult] = []
        self.is_running = False
        self.scheduler_thread = None
        self._shutdown_event = threading.Event()
        
        # Create maintenance log directory
        self.log_dir = Path("maintenance_logs")
        self.log_dir.mkdir(exist_ok=True)
    
    def start_scheduler(self):
        """Start the maintenance scheduler"""
        if self.is_running:
            logger.warning("Maintenance scheduler is already running")
            return
        
        self.is_running = True
        self._setup_schedules()
        
        # Start scheduler in separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Database maintenance scheduler started")
    
    def stop_scheduler(self):
        """Stop the maintenance scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._shutdown_event.set()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=30)
        
        schedule.clear()
        logger.info("🔒 Database maintenance scheduler stopped")
    
    def _setup_schedules(self):
        """Setup maintenance schedules"""
        
        # Vacuum schedule
        if self.config.vacuum_schedule == "daily":
            schedule.every().day.at(self.config.vacuum_time).do(self._run_vacuum_maintenance)
        elif self.config.vacuum_schedule == "weekly":
            schedule.every().week.at(self.config.vacuum_time).do(self._run_vacuum_maintenance)
        
        # Analyze schedule
        if self.config.analyze_schedule == "daily":
            schedule.every().day.at(self.config.analyze_time).do(self._run_analyze_maintenance)
        elif self.config.analyze_schedule == "weekly":
            schedule.every().week.at(self.config.analyze_time).do(self._run_analyze_maintenance)
        
        # Reindex schedule
        if self.config.reindex_schedule == "weekly":
            schedule.every().sunday.at(self.config.reindex_time).do(self._run_reindex_maintenance)
        elif self.config.reindex_schedule == "monthly":
            schedule.every(4).weeks.do(self._run_reindex_maintenance)
        
        # Statistics collection
        if self.config.stats_collection_schedule == "hourly":
            schedule.every().hour.do(self._collect_maintenance_stats)
        elif self.config.stats_time.startswith("*/"):
            # Every N hours
            hours = int(self.config.stats_time.split("/")[1])
            schedule.every(hours).hours.do(self._collect_maintenance_stats)
        
        logger.info("📅 Maintenance schedules configured")
    
    def _run_scheduler(self):
        """Run the maintenance scheduler loop"""
        while self.is_running and not self._shutdown_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _is_peak_hours(self) -> bool:
        """Check if current time is during peak hours"""
        if not self.config.skip_during_peak_hours:
            return False
        
        now = datetime.now().time()
        start_time = dt_time.fromisoformat(self.config.peak_hours_start)
        end_time = dt_time.fromisoformat(self.config.peak_hours_end)
        
        return start_time <= now <= end_time
    
    @contextmanager
    def get_connection(self):
        """Get database connection with maintenance settings"""
        conn = None
        try:
            conn = psycopg2.connect(
                self.config.database_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            
            # Set maintenance-specific parameters
            with conn.cursor() as cursor:
                cursor.execute(f"SET maintenance_work_mem = '{self.config.maintenance_work_mem}'")
                cursor.execute(f"SET vacuum_cost_delay = {self.config.vacuum_cost_delay}")
                cursor.execute(f"SET vacuum_cost_limit = {self.config.vacuum_cost_limit}")
            
            conn.commit()
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def get_table_maintenance_stats(self) -> List[TableMaintenanceStats]:
        """Get maintenance statistics for all tables"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Query table statistics
                    cursor.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            n_live_tup,
                            n_dead_tup,
                            last_vacuum,
                            last_autovacuum,
                            last_analyze,
                            last_autoanalyze,
                            pg_total_relation_size(schemaname||'.'||tablename) as table_size
                        FROM pg_stat_user_tables 
                        WHERE schemaname = 'public'
                        ORDER BY n_dead_tup DESC
                    """)
                    
                    table_stats = []
                    for row in cursor.fetchall():
                        dead_ratio = 0
                        if row['n_live_tup'] > 0:
                            dead_ratio = row['n_dead_tup'] / row['n_live_tup']
                        
                        # Calculate maintenance priority (1-10)
                        priority = self._calculate_maintenance_priority(
                            dead_ratio, 
                            row['table_size'],
                            row['last_vacuum'] or row['last_autovacuum'],
                            row['last_analyze'] or row['last_autoanalyze']
                        )
                        
                        # Generate recommendations
                        recommendations = self._generate_table_recommendations(
                            dead_ratio, 
                            row['last_vacuum'] or row['last_autovacuum'],
                            row['last_analyze'] or row['last_autoanalyze']
                        )
                        
                        stats = TableMaintenanceStats(
                            table_name=f"{row['schemaname']}.{row['tablename']}",
                            table_size_bytes=row['table_size'],
                            dead_tuples=row['n_dead_tup'],
                            live_tuples=row['n_live_tup'],
                            dead_tuple_ratio=dead_ratio,
                            last_vacuum=row['last_vacuum'] or row['last_autovacuum'],
                            last_analyze=row['last_analyze'] or row['last_autoanalyze'],
                            maintenance_priority=priority,
                            recommended_actions=recommendations
                        )
                        table_stats.append(stats)
                    
                    return table_stats
                    
        except Exception as e:
            logger.error(f"❌ Failed to get table maintenance stats: {e}")
            return []
    
    def _calculate_maintenance_priority(self, dead_ratio: float, table_size: int,
                                      last_vacuum: Optional[datetime], 
                                      last_analyze: Optional[datetime]) -> int:
        """Calculate maintenance priority (1-10, higher = more urgent)"""
        priority = 1
        
        # Dead tuple ratio contribution (0-4 points)
        if dead_ratio > 0.3:
            priority += 4
        elif dead_ratio > 0.2:
            priority += 3  
        elif dead_ratio > 0.1:
            priority += 2
        elif dead_ratio > 0.05:
            priority += 1
        
        # Table size contribution (0-2 points)
        size_gb = table_size / (1024**3)
        if size_gb > 10:
            priority += 2
        elif size_gb > 1:
            priority += 1
        
        # Time since last maintenance (0-3 points)  
        now = datetime.now()
        
        if last_vacuum:
            days_since_vacuum = (now - last_vacuum).days
            if days_since_vacuum > 7:
                priority += 3
            elif days_since_vacuum > 3:
                priority += 2
            elif days_since_vacuum > 1:
                priority += 1
        else:
            priority += 3  # Never vacuumed
        
        return min(10, priority)
    
    def _generate_table_recommendations(self, dead_ratio: float,
                                      last_vacuum: Optional[datetime],
                                      last_analyze: Optional[datetime]) -> List[str]:
        """Generate maintenance recommendations for table"""
        recommendations = []
        
        if dead_ratio > self.config.dead_tuple_threshold:
            recommendations.append(f"VACUUM required (dead ratio: {dead_ratio:.1%})")
        
        if not last_vacuum or (datetime.now() - last_vacuum).days > 7:
            recommendations.append("VACUUM overdue (>7 days since last vacuum)")
        
        if not last_analyze or (datetime.now() - last_analyze).days > 7:
            recommendations.append("ANALYZE overdue (>7 days since last analyze)")
        
        if dead_ratio > 0.2:
            recommendations.append("Consider VACUUM FULL for heavy bloat")
        
        return recommendations
    
    def _run_vacuum_maintenance(self):
        """Run vacuum maintenance on tables that need it"""
        if self._is_peak_hours():
            logger.info("⏰ Skipping vacuum during peak hours")
            return
        
        logger.info("🧹 Starting automated vacuum maintenance")
        start_time = datetime.now()
        results = []
        
        # Get tables that need vacuum
        table_stats = self.get_table_maintenance_stats()
        vacuum_candidates = [
            stats for stats in table_stats 
            if stats.dead_tuple_ratio > self.config.dead_tuple_threshold
            or stats.maintenance_priority >= 7
        ]
        
        vacuum_candidates.sort(key=lambda x: x.maintenance_priority, reverse=True)
        
        for table_stat in vacuum_candidates[:10]:  # Limit to top 10 tables
            result = self._vacuum_table(table_stat.table_name)
            results.append(result)
            
            # Check time limit
            elapsed = (datetime.now() - start_time).total_seconds() / 3600
            if elapsed > self.config.max_maintenance_duration_hours:
                logger.warning("⏰ Vacuum maintenance time limit reached")
                break
        
        self._log_maintenance_results("VACUUM", results)
        logger.info(f"✅ Vacuum maintenance completed: {len(results)} tables processed")
    
    def _run_analyze_maintenance(self):
        """Run analyze maintenance on tables"""
        if self._is_peak_hours():
            logger.info("⏰ Skipping analyze during peak hours")
            return
        
        logger.info("📊 Starting automated analyze maintenance")
        start_time = datetime.now()
        results = []
        
        table_stats = self.get_table_maintenance_stats()
        analyze_candidates = [
            stats for stats in table_stats
            if not stats.last_analyze or 
            (datetime.now() - stats.last_analyze).days > 3
        ]
        
        for table_stat in analyze_candidates:
            result = self._analyze_table(table_stat.table_name)
            results.append(result)
            
            # Check time limit
            elapsed = (datetime.now() - start_time).total_seconds() / 3600
            if elapsed > self.config.max_maintenance_duration_hours:
                break
        
        self._log_maintenance_results("ANALYZE", results)
        logger.info(f"✅ Analyze maintenance completed: {len(results)} tables processed")
    
    def _run_reindex_maintenance(self):
        """Run reindex maintenance on bloated indexes"""
        if self._is_peak_hours():
            logger.info("⏰ Skipping reindex during peak hours")
            return
        
        logger.info("🔧 Starting automated reindex maintenance")
        results = []
        
        # Get indexes that need rebuilding
        bloated_indexes = self._get_bloated_indexes()
        
        for index_info in bloated_indexes:
            result = self._reindex_index(index_info['index_name'], index_info['table_name'])
            results.append(result)
        
        self._log_maintenance_results("REINDEX", results)  
        logger.info(f"✅ Reindex maintenance completed: {len(results)} indexes processed")
    
    def _vacuum_table(self, table_name: str) -> MaintenanceResult:
        """Vacuum specific table"""
        start_time = datetime.now()
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"🧹 Vacuuming {table_name}...")
                    
                    # Use VACUUM (not FULL) for regular maintenance
                    cursor.execute(f"VACUUM ANALYZE {table_name}")
                    
                    # Get row count for reporting
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    result = MaintenanceResult(
                        operation="VACUUM",
                        table_name=table_name,
                        started_at=start_time,
                        completed_at=end_time,
                        duration_seconds=duration,
                        rows_processed=row_count,
                        success=True
                    )
                    
                    logger.info(f"✅ Vacuumed {table_name}: {row_count:,} rows in {duration:.1f}s")
                    return result
                    
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ Failed to vacuum {table_name}: {e}")
            
            return MaintenanceResult(
                operation="VACUUM",
                table_name=table_name,
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
                rows_processed=0,
                success=False,
                error_message=str(e)
            )
    
    def _analyze_table(self, table_name: str) -> MaintenanceResult:
        """Analyze specific table"""
        start_time = datetime.now()
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"📊 Analyzing {table_name}...")
                    
                    cursor.execute(f"ANALYZE {table_name}")
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    result = MaintenanceResult(
                        operation="ANALYZE",
                        table_name=table_name,
                        started_at=start_time,
                        completed_at=end_time,
                        duration_seconds=duration,
                        rows_processed=row_count,
                        success=True
                    )
                    
                    logger.info(f"✅ Analyzed {table_name}: {row_count:,} rows in {duration:.1f}s")
                    return result
                    
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ Failed to analyze {table_name}: {e}")
            
            return MaintenanceResult(
                operation="ANALYZE",
                table_name=table_name,
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
                rows_processed=0,
                success=False,
                error_message=str(e)
            )
    
    def _get_bloated_indexes(self) -> List[Dict[str, Any]]:
        """Get list of bloated indexes that need rebuilding"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Query to find bloated indexes (simplified version)
                    cursor.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            indexname,
                            idx_scan,
                            idx_tup_read,
                            idx_tup_fetch,
                            pg_size_pretty(pg_relation_size(indexrelid)) as size
                        FROM pg_stat_user_indexes
                        WHERE schemaname = 'public'
                        AND idx_scan > 0  -- Only consider used indexes
                        ORDER BY pg_relation_size(indexrelid) DESC
                    """)
                    
                    bloated_indexes = []
                    for row in cursor.fetchall():
                        # Simple heuristic: large indexes with low efficiency
                        efficiency = 0
                        if row['idx_tup_read'] > 0:
                            efficiency = row['idx_tup_fetch'] / row['idx_tup_read']
                        
                        # Consider for reindex if efficiency is very low
                        if efficiency < 0.1 and row['idx_scan'] > 100:
                            bloated_indexes.append({
                                'schema_name': row['schemaname'],
                                'table_name': row['tablename'],
                                'index_name': row['indexname'],
                                'size': row['size'],
                                'efficiency': efficiency
                            })
                    
                    return bloated_indexes[:5]  # Limit to 5 most problematic
                    
        except Exception as e:
            logger.error(f"❌ Failed to get bloated indexes: {e}")
            return []
    
    def _reindex_index(self, index_name: str, table_name: str) -> MaintenanceResult:
        """Reindex specific index"""
        start_time = datetime.now()
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"🔧 Reindexing {index_name} on {table_name}...")
                    
                    cursor.execute(f"REINDEX INDEX CONCURRENTLY {index_name}")
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    result = MaintenanceResult(
                        operation="REINDEX",
                        table_name=table_name,
                        started_at=start_time,
                        completed_at=end_time,
                        duration_seconds=duration,
                        rows_processed=0,  # Not applicable for reindex
                        success=True,
                        details={'index_name': index_name}
                    )
                    
                    logger.info(f"✅ Reindexed {index_name} in {duration:.1f}s")
                    return result
                    
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ Failed to reindex {index_name}: {e}")
            
            return MaintenanceResult(
                operation="REINDEX",
                table_name=table_name,
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
                rows_processed=0,
                success=False,
                error_message=str(e),
                details={'index_name': index_name}
            )
    
    def _collect_maintenance_stats(self):
        """Collect and log maintenance statistics"""
        try:
            stats = self.get_table_maintenance_stats()
            
            # Log high-priority tables
            urgent_tables = [s for s in stats if s.maintenance_priority >= 8]
            if urgent_tables:
                logger.warning(f"⚠️ {len(urgent_tables)} tables need urgent maintenance")
                for table in urgent_tables[:3]:  # Log top 3
                    logger.warning(f"   - {table.table_name}: priority {table.maintenance_priority}")
            
            # Save stats to file for trend analysis
            stats_file = self.log_dir / f"maintenance_stats_{datetime.now().strftime('%Y%m%d')}.json"
            stats_data = {
                'timestamp': datetime.now().isoformat(),
                'table_count': len(stats),
                'urgent_maintenance_count': len(urgent_tables),
                'total_dead_tuples': sum(s.dead_tuples for s in stats),
                'total_table_size': sum(s.table_size_bytes for s in stats)
            }
            
            with open(stats_file, 'a') as f:
                f.write(json.dumps(stats_data) + '\n')
                
        except Exception as e:
            logger.error(f"❌ Failed to collect maintenance stats: {e}")
    
    def _log_maintenance_results(self, operation: str, results: List[MaintenanceResult]):
        """Log maintenance results to file"""
        if not self.config.log_maintenance_operations:
            return
        
        try:
            log_file = self.log_dir / f"maintenance_{operation.lower()}_{datetime.now().strftime('%Y%m%d')}.json"
            
            log_data = {
                'operation': operation,
                'timestamp': datetime.now().isoformat(),
                'results': [asdict(result) for result in results],
                'summary': {
                    'total_operations': len(results),
                    'successful': len([r for r in results if r.success]),
                    'failed': len([r for r in results if not r.success]),
                    'total_duration': sum(r.duration_seconds for r in results),
                    'total_rows_processed': sum(r.rows_processed for r in results)
                }
            }
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_data, default=str) + '\n')
                
            # Keep maintenance history in memory (limited)
            self.maintenance_history.extend(results)
            if len(self.maintenance_history) > 1000:
                self.maintenance_history = self.maintenance_history[-500:]
                
        except Exception as e:
            logger.error(f"❌ Failed to log maintenance results: {e}")
    
    def get_maintenance_summary(self) -> Dict[str, Any]:
        """Get maintenance summary and status"""
        recent_results = [
            r for r in self.maintenance_history
            if r.completed_at > datetime.now() - timedelta(days=7)
        ]
        
        table_stats = self.get_table_maintenance_stats()
        urgent_tables = [s for s in table_stats if s.maintenance_priority >= 8]
        
        return {
            'scheduler_status': 'running' if self.is_running else 'stopped',
            'last_7_days': {
                'total_operations': len(recent_results),
                'successful_operations': len([r for r in recent_results if r.success]),
                'failed_operations': len([r for r in recent_results if not r.success]),
                'total_duration_hours': sum(r.duration_seconds for r in recent_results) / 3600,
                'operations_by_type': {
                    op_type: len([r for r in recent_results if r.operation == op_type])
                    for op_type in ['VACUUM', 'ANALYZE', 'REINDEX']
                }
            },
            'current_status': {
                'total_tables': len(table_stats),
                'urgent_maintenance_needed': len(urgent_tables),
                'total_dead_tuples': sum(s.dead_tuples for s in table_stats),
                'avg_dead_tuple_ratio': sum(s.dead_tuple_ratio for s in table_stats) / max(len(table_stats), 1),
                'largest_table_gb': max((s.table_size_bytes / (1024**3) for s in table_stats), default=0)
            },
            'urgent_tables': [
                {
                    'table_name': s.table_name,
                    'priority': s.maintenance_priority,
                    'dead_tuple_ratio': s.dead_tuple_ratio,
                    'recommendations': s.recommended_actions
                }
                for s in urgent_tables[:5]
            ]
        }
    
    def print_maintenance_status(self):
        """Print formatted maintenance status"""
        summary = self.get_maintenance_summary()
        
        print("\n" + "="*70)
        print("🔧 DATABASE MAINTENANCE STATUS")
        print("="*70)
        
        print(f"Scheduler Status: {summary['scheduler_status'].upper()}")
        
        # Recent activity
        recent = summary['last_7_days']
        print(f"\n📊 Last 7 Days:")
        print(f"   Total Operations: {recent['total_operations']}")
        print(f"   Successful: {recent['successful_operations']}")
        print(f"   Failed: {recent['failed_operations']}")
        print(f"   Total Duration: {recent['total_duration_hours']:.1f} hours")
        
        for op_type, count in recent['operations_by_type'].items():
            if count > 0:
                print(f"   {op_type}: {count} operations")
        
        # Current status
        current = summary['current_status']
        print(f"\n🗃️ Current Database Status:")
        print(f"   Total Tables: {current['total_tables']}")
        print(f"   Urgent Maintenance Needed: {current['urgent_maintenance_needed']}")
        print(f"   Total Dead Tuples: {current['total_dead_tuples']:,}")
        print(f"   Avg Dead Tuple Ratio: {current['avg_dead_tuple_ratio']:.1%}")
        print(f"   Largest Table: {current['largest_table_gb']:.1f} GB")
        
        # Urgent tables
        if summary['urgent_tables']:
            print(f"\n⚠️ Tables Needing Urgent Maintenance:")
            for table in summary['urgent_tables']:
                print(f"   - {table['table_name']} (Priority: {table['priority']})")
                print(f"     Dead Ratio: {table['dead_tuple_ratio']:.1%}")
                for rec in table['recommendations'][:2]:
                    print(f"     • {rec}")
        else:
            print(f"\n✅ No tables need urgent maintenance")
        
        print("="*70)
    
    def run_manual_maintenance(self, operation: str, table_name: str = None):
        """Run maintenance operation manually"""
        logger.info(f"🔧 Running manual {operation} maintenance")
        
        if operation.upper() == 'VACUUM':
            if table_name:
                result = self._vacuum_table(table_name)
                self._log_maintenance_results("MANUAL_VACUUM", [result])
            else:
                self._run_vacuum_maintenance()
        
        elif operation.upper() == 'ANALYZE':
            if table_name:
                result = self._analyze_table(table_name)
                self._log_maintenance_results("MANUAL_ANALYZE", [result])
            else:
                self._run_analyze_maintenance()
        
        elif operation.upper() == 'REINDEX':
            self._run_reindex_maintenance()
        
        else:
            logger.error(f"❌ Unknown maintenance operation: {operation}")
    
    def cleanup_old_logs(self):
        """Clean up old maintenance log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.maintenance_log_retention_days)
            
            for log_file in self.log_dir.glob("maintenance_*.json"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    logger.info(f"🗑️ Removed old log file: {log_file.name}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old logs: {e}")

# Example usage and testing
def main():
    """Example usage of database maintenance scheduler"""
    DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"
    
    config = MaintenanceConfig(
        database_url=DATABASE_URL,
        vacuum_schedule="daily",
        vacuum_time="02:00",
        dead_tuple_threshold=0.05,  # More aggressive maintenance
        skip_during_peak_hours=True,
        peak_hours_start="09:00",
        peak_hours_end="18:00"
    )
    
    scheduler = DatabaseMaintenanceScheduler(config)
    
    try:
        # Print current status
        scheduler.print_maintenance_status()
        
        # Run manual maintenance for testing
        print("\n🧪 Running test maintenance operations...")
        scheduler.run_manual_maintenance('ANALYZE')  # Analyze all tables
        
        # Print updated status
        scheduler.print_maintenance_status()
        
        # Start scheduler (in production, this would run continuously)
        print("\n🔧 Starting maintenance scheduler...")
        scheduler.start_scheduler()
        
        # Keep running for demo (in production, this would run as daemon)
        time.sleep(60)
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down maintenance scheduler...")
    finally:
        scheduler.stop_scheduler()

if __name__ == "__main__":
    main()