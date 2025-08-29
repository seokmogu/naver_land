#!/usr/bin/env python3
"""
BATCH PROCESSING OPTIMIZER
High-performance bulk operations for Naver real estate collection system
- Bulk INSERT operations with conflict handling
- Transaction batching for optimal performance  
- Connection pooling optimization
- Memory-efficient batch processing
"""

import asyncio
import asyncpg
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import logging
import time
import json
from dataclasses import dataclass
from datetime import datetime, date
import threading
from queue import Queue, Empty

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BatchConfig:
    """Batch processing configuration"""
    batch_size: int = 500
    max_connections: int = 10
    transaction_timeout: int = 30
    retry_attempts: int = 3
    connection_timeout: int = 10
    enable_prepared_statements: bool = True
    use_copy_from: bool = True  # Use COPY for bulk inserts
    parallel_workers: int = 4

@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    total_processed: int = 0
    successful_inserts: int = 0
    failed_inserts: int = 0
    duplicate_skips: int = 0
    total_time: float = 0.0
    avg_batch_time: float = 0.0
    records_per_second: float = 0.0
    
    def calculate_rates(self):
        if self.total_time > 0:
            self.records_per_second = self.total_processed / self.total_time
        if self.total_processed > 0:
            self.avg_batch_time = self.total_time / (self.total_processed / 500)  # Assuming 500 batch size

class DatabaseConnectionPool:
    """High-performance connection pool manager"""
    
    def __init__(self, database_url: str, config: BatchConfig):
        self.database_url = database_url
        self.config = config
        self.pool = None
        self._lock = threading.Lock()
        
    async def initialize_async_pool(self):
        """Initialize asyncpg connection pool for maximum performance"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=self.config.max_connections,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                timeout=self.config.connection_timeout,
                command_timeout=self.config.transaction_timeout
            )
            logger.info(f"✅ Async connection pool initialized with {self.config.max_connections} connections")
        except Exception as e:
            logger.error(f"❌ Failed to initialize async pool: {e}")
            raise
    
    @contextmanager
    def get_sync_connection(self):
        """Get synchronous connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(
                self.database_url,
                connect_timeout=self.config.connection_timeout
            )
            conn.autocommit = False
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    async def close_pool(self):
        """Clean up connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("🔒 Connection pool closed")

class BatchProcessor:
    """High-performance batch processing engine"""
    
    def __init__(self, database_url: str, config: BatchConfig = None):
        self.database_url = database_url
        self.config = config or BatchConfig()
        self.pool_manager = DatabaseConnectionPool(database_url, self.config)
        self.metrics = PerformanceMetrics()
        self._prepared_statements = {}
        
    async def initialize(self):
        """Initialize the batch processor"""
        await self.pool_manager.initialize_async_pool()
        if self.config.enable_prepared_statements:
            await self._prepare_statements()
    
    async def _prepare_statements(self):
        """Prepare frequently used SQL statements for better performance"""
        statements = {
            'upsert_property': '''
                INSERT INTO properties_new (
                    article_no, article_name, real_estate_type_id, trade_type_id, 
                    region_id, collected_date, last_seen_date, is_active, 
                    tag_list, description, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (article_no) DO UPDATE SET
                    article_name = EXCLUDED.article_name,
                    last_seen_date = EXCLUDED.last_seen_date,
                    is_active = EXCLUDED.is_active,
                    tag_list = EXCLUDED.tag_list,
                    description = EXCLUDED.description,
                    updated_at = EXCLUDED.updated_at
                RETURNING id;
            ''',
            
            'bulk_insert_prices': '''
                INSERT INTO property_prices (
                    property_id, price_type, amount, currency, valid_from, notes
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (property_id, price_type, valid_from) DO UPDATE SET
                    amount = EXCLUDED.amount,
                    currency = EXCLUDED.currency,
                    notes = EXCLUDED.notes;
            ''',
            
            'bulk_insert_locations': '''
                INSERT INTO property_locations (
                    property_id, latitude, longitude, address_road, building_name,
                    walking_to_subway, region_id, address_verified
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (property_id) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    address_road = EXCLUDED.address_road,
                    building_name = EXCLUDED.building_name,
                    walking_to_subway = EXCLUDED.walking_to_subway,
                    region_id = EXCLUDED.region_id,
                    address_verified = EXCLUDED.address_verified;
            ''',
            
            'bulk_insert_physical': '''
                INSERT INTO property_physical (
                    property_id, area_exclusive, area_supply, area_utilization_rate,
                    floor_current, floor_total, floor_underground, room_count, 
                    bathroom_count, parking_possible, elevator_available
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (property_id) DO UPDATE SET
                    area_exclusive = EXCLUDED.area_exclusive,
                    area_supply = EXCLUDED.area_supply,
                    area_utilization_rate = EXCLUDED.area_utilization_rate,
                    floor_current = EXCLUDED.floor_current,
                    floor_total = EXCLUDED.floor_total,
                    floor_underground = EXCLUDED.floor_underground,
                    room_count = EXCLUDED.room_count,
                    bathroom_count = EXCLUDED.bathroom_count,
                    parking_possible = EXCLUDED.parking_possible,
                    elevator_available = EXCLUDED.elevator_available;
            ''',
            
            'bulk_insert_images': '''
                INSERT INTO property_images (
                    property_id, image_url, image_type, image_order, caption,
                    width, height, file_size, is_high_quality, captured_date
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (property_id, image_url) DO NOTHING;
            '''
        }
        
        async with self.pool_manager.pool.acquire() as conn:
            for name, sql in statements.items():
                await conn.execute(f"PREPARE {name} AS {sql}")
                self._prepared_statements[name] = sql
        
        logger.info(f"✅ Prepared {len(statements)} SQL statements")
    
    async def bulk_insert_properties(self, properties_data: List[Dict]) -> List[int]:
        """
        High-performance bulk property insertion with optimized batching
        Returns list of property IDs for successful insertions
        """
        start_time = time.time()
        property_ids = []
        
        # Process in optimized batches
        for i in range(0, len(properties_data), self.config.batch_size):
            batch = properties_data[i:i + self.config.batch_size]
            batch_start_time = time.time()
            
            try:
                if self.config.use_copy_from:
                    # Use COPY for maximum performance
                    batch_ids = await self._bulk_copy_properties(batch)
                else:
                    # Use prepared statements
                    batch_ids = await self._bulk_insert_properties_prepared(batch)
                
                property_ids.extend(batch_ids)
                self.metrics.successful_inserts += len(batch_ids)
                
                batch_time = time.time() - batch_start_time
                logger.info(f"🚀 Batch {i//self.config.batch_size + 1}: {len(batch_ids)}/{len(batch)} properties processed in {batch_time:.2f}s")
                
            except Exception as e:
                self.metrics.failed_inserts += len(batch)
                logger.error(f"❌ Batch {i//self.config.batch_size + 1} failed: {e}")
                
                # Fallback to individual processing
                individual_ids = await self._process_batch_individually(batch)
                property_ids.extend(individual_ids)
        
        # Update metrics
        self.metrics.total_processed = len(properties_data)
        self.metrics.total_time = time.time() - start_time
        self.metrics.calculate_rates()
        
        logger.info(f"✅ Bulk insert complete: {len(property_ids)} properties in {self.metrics.total_time:.2f}s ({self.metrics.records_per_second:.1f} records/sec)")
        return property_ids
    
    async def _bulk_copy_properties(self, batch: List[Dict]) -> List[int]:
        """Use PostgreSQL COPY for maximum insertion performance"""
        import io
        
        # Prepare data for COPY
        copy_data = io.StringIO()
        property_data_map = {}
        
        for i, prop in enumerate(batch):
            # Generate row for COPY
            row = [
                prop.get('article_no', ''),
                prop.get('article_name', ''),
                str(prop.get('real_estate_type_id', '')),
                str(prop.get('trade_type_id', '')),
                str(prop.get('region_id', '')),
                prop.get('collected_date', date.today().isoformat()),
                prop.get('last_seen_date', date.today().isoformat()),
                'true',  # is_active
                json.dumps(prop.get('tag_list', [])),
                prop.get('description', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ]
            
            # Escape and join
            escaped_row = [str(field).replace('\t', ' ').replace('\n', ' ').replace('\r', ' ') for field in row]
            copy_data.write('\t'.join(escaped_row) + '\n')
            property_data_map[prop.get('article_no')] = i
        
        copy_data.seek(0)
        
        async with self.pool_manager.pool.acquire() as conn:
            async with conn.transaction():
                # Create temporary table
                await conn.execute('''
                    CREATE TEMPORARY TABLE temp_properties_bulk (
                        article_no VARCHAR(50),
                        article_name VARCHAR(500),
                        real_estate_type_id INTEGER,
                        trade_type_id INTEGER,
                        region_id INTEGER,
                        collected_date DATE,
                        last_seen_date DATE,
                        is_active BOOLEAN,
                        tag_list JSONB,
                        description TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                ''')
                
                # COPY data to temp table
                await conn.copy_to_table(
                    'temp_properties_bulk',
                    source=copy_data,
                    delimiter='\t'
                )
                
                # Insert from temp table with UPSERT
                result = await conn.fetch('''
                    INSERT INTO properties_new 
                    SELECT * FROM temp_properties_bulk
                    ON CONFLICT (article_no) DO UPDATE SET
                        article_name = EXCLUDED.article_name,
                        last_seen_date = EXCLUDED.last_seen_date,
                        is_active = EXCLUDED.is_active,
                        tag_list = EXCLUDED.tag_list,
                        description = EXCLUDED.description,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id, article_no;
                ''')
                
                return [row['id'] for row in result]
    
    async def _bulk_insert_properties_prepared(self, batch: List[Dict]) -> List[int]:
        """Use prepared statements for bulk insertion"""
        property_ids = []
        
        async with self.pool_manager.pool.acquire() as conn:
            async with conn.transaction():
                for prop in batch:
                    try:
                        row = await conn.fetchrow(
                            self._prepared_statements['upsert_property'],
                            prop.get('article_no', ''),
                            prop.get('article_name', ''),
                            prop.get('real_estate_type_id'),
                            prop.get('trade_type_id'),
                            prop.get('region_id'),
                            prop.get('collected_date', date.today()),
                            prop.get('last_seen_date', date.today()),
                            True,  # is_active
                            json.dumps(prop.get('tag_list', [])),
                            prop.get('description', ''),
                            datetime.now(),
                            datetime.now()
                        )
                        
                        if row:
                            property_ids.append(row['id'])
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to insert property {prop.get('article_no')}: {e}")
                        continue
        
        return property_ids
    
    async def _process_batch_individually(self, batch: List[Dict]) -> List[int]:
        """Fallback: process failed batch items individually"""
        property_ids = []
        
        for prop in batch:
            try:
                async with self.pool_manager.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        self._prepared_statements['upsert_property'],
                        prop.get('article_no', ''),
                        prop.get('article_name', ''),
                        prop.get('real_estate_type_id'),
                        prop.get('trade_type_id'),
                        prop.get('region_id'),
                        prop.get('collected_date', date.today()),
                        prop.get('last_seen_date', date.today()),
                        True,
                        json.dumps(prop.get('tag_list', [])),
                        prop.get('description', ''),
                        datetime.now(),
                        datetime.now()
                    )
                    
                    if row:
                        property_ids.append(row['id'])
                        self.metrics.successful_inserts += 1
                    
            except Exception as e:
                logger.error(f"❌ Individual insert failed for {prop.get('article_no')}: {e}")
                self.metrics.failed_inserts += 1
                continue
        
        return property_ids
    
    async def bulk_insert_related_data(self, property_mapping: Dict[str, int], 
                                     related_data: Dict[str, List[Dict]]):
        """
        Bulk insert related data (prices, locations, physical, images)
        property_mapping: {article_no: property_id}
        related_data: {'prices': [...], 'locations': [...], 'physical': [...], 'images': [...]}
        """
        
        tasks = []
        
        # Process prices
        if 'prices' in related_data:
            prices_with_ids = []
            for price_data in related_data['prices']:
                article_no = price_data.get('article_no')
                if article_no in property_mapping:
                    price_data['property_id'] = property_mapping[article_no]
                    prices_with_ids.append(price_data)
            
            if prices_with_ids:
                tasks.append(self._bulk_insert_prices(prices_with_ids))
        
        # Process locations
        if 'locations' in related_data:
            locations_with_ids = []
            for location_data in related_data['locations']:
                article_no = location_data.get('article_no')
                if article_no in property_mapping:
                    location_data['property_id'] = property_mapping[article_no]
                    locations_with_ids.append(location_data)
            
            if locations_with_ids:
                tasks.append(self._bulk_insert_locations(locations_with_ids))
        
        # Process physical data
        if 'physical' in related_data:
            physical_with_ids = []
            for physical_data in related_data['physical']:
                article_no = physical_data.get('article_no')
                if article_no in property_mapping:
                    physical_data['property_id'] = property_mapping[article_no]
                    physical_with_ids.append(physical_data)
            
            if physical_with_ids:
                tasks.append(self._bulk_insert_physical(physical_with_ids))
        
        # Process images
        if 'images' in related_data:
            images_with_ids = []
            for image_data in related_data['images']:
                article_no = image_data.get('article_no')
                if article_no in property_mapping:
                    image_data['property_id'] = property_mapping[article_no]
                    images_with_ids.append(image_data)
            
            if images_with_ids:
                tasks.append(self._bulk_insert_images(images_with_ids))
        
        # Execute all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks)
            logger.info(f"✅ Bulk inserted related data for {len(property_mapping)} properties")
    
    async def _bulk_insert_prices(self, prices_data: List[Dict]):
        """Bulk insert price data"""
        async with self.pool_manager.pool.acquire() as conn:
            await conn.executemany(
                self._prepared_statements['bulk_insert_prices'],
                [
                    (
                        price['property_id'],
                        price.get('price_type', 'sale'),
                        price.get('amount', 0),
                        price.get('currency', 'KRW'),
                        price.get('valid_from', date.today()),
                        price.get('notes', '')
                    )
                    for price in prices_data
                ]
            )
    
    async def _bulk_insert_locations(self, locations_data: List[Dict]):
        """Bulk insert location data"""
        async with self.pool_manager.pool.acquire() as conn:
            await conn.executemany(
                self._prepared_statements['bulk_insert_locations'],
                [
                    (
                        location['property_id'],
                        location.get('latitude'),
                        location.get('longitude'),
                        location.get('address_road', ''),
                        location.get('building_name', ''),
                        location.get('walking_to_subway'),
                        location.get('region_id'),
                        location.get('address_verified', False)
                    )
                    for location in locations_data
                ]
            )
    
    async def _bulk_insert_physical(self, physical_data: List[Dict]):
        """Bulk insert physical property data"""
        async with self.pool_manager.pool.acquire() as conn:
            await conn.executemany(
                self._prepared_statements['bulk_insert_physical'],
                [
                    (
                        physical['property_id'],
                        physical.get('area_exclusive'),
                        physical.get('area_supply'),
                        physical.get('area_utilization_rate'),
                        physical.get('floor_current'),
                        physical.get('floor_total'),
                        physical.get('floor_underground'),
                        physical.get('room_count'),
                        physical.get('bathroom_count'),
                        physical.get('parking_possible', False),
                        physical.get('elevator_available', False)
                    )
                    for physical in physical_data
                ]
            )
    
    async def _bulk_insert_images(self, images_data: List[Dict]):
        """Bulk insert image data"""
        async with self.pool_manager.pool.acquire() as conn:
            await conn.executemany(
                self._prepared_statements['bulk_insert_images'],
                [
                    (
                        image['property_id'],
                        image.get('image_url', ''),
                        image.get('image_type', 'general'),
                        image.get('image_order', 0),
                        image.get('caption', ''),
                        image.get('width'),
                        image.get('height'),
                        image.get('file_size'),
                        image.get('is_high_quality', False),
                        image.get('captured_date', date.today())
                    )
                    for image in images_data
                    if image.get('image_url')  # Only insert images with valid URLs
                ]
            )
    
    def print_performance_metrics(self):
        """Print detailed performance metrics"""
        print("\n" + "="*60)
        print("📊 BATCH PROCESSING PERFORMANCE METRICS")
        print("="*60)
        print(f"✅ Total Processed: {self.metrics.total_processed:,} records")
        print(f"✅ Successful Inserts: {self.metrics.successful_inserts:,} records")
        print(f"❌ Failed Inserts: {self.metrics.failed_inserts:,} records")
        print(f"⏱️  Total Time: {self.metrics.total_time:.2f} seconds")
        print(f"🚀 Records/Second: {self.metrics.records_per_second:.1f}")
        print(f"⚡ Avg Batch Time: {self.metrics.avg_batch_time:.2f} seconds")
        
        success_rate = (self.metrics.successful_inserts / max(self.metrics.total_processed, 1)) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print("="*60)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.pool_manager.close_pool()

# Synchronous wrapper for compatibility
class SyncBatchProcessor:
    """Synchronous wrapper for batch processing operations"""
    
    def __init__(self, database_url: str, config: BatchConfig = None):
        self.database_url = database_url
        self.config = config or BatchConfig()
        self.metrics = PerformanceMetrics()
    
    def bulk_insert_properties_sync(self, properties_data: List[Dict]) -> List[int]:
        """Synchronous bulk property insertion using psycopg2"""
        start_time = time.time()
        property_ids = []
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Process in batches
                for i in range(0, len(properties_data), self.config.batch_size):
                    batch = properties_data[i:i + self.config.batch_size]
                    batch_start = time.time()
                    
                    try:
                        # Use execute_values for high performance
                        insert_sql = '''
                            INSERT INTO properties_new (
                                article_no, article_name, real_estate_type_id, trade_type_id,
                                region_id, collected_date, last_seen_date, is_active,
                                tag_list, description, created_at, updated_at
                            ) VALUES %s
                            ON CONFLICT (article_no) DO UPDATE SET
                                article_name = EXCLUDED.article_name,
                                last_seen_date = EXCLUDED.last_seen_date,
                                is_active = EXCLUDED.is_active,
                                tag_list = EXCLUDED.tag_list,
                                description = EXCLUDED.description,
                                updated_at = EXCLUDED.updated_at
                            RETURNING id;
                        '''
                        
                        values = [
                            (
                                prop.get('article_no', ''),
                                prop.get('article_name', ''),
                                prop.get('real_estate_type_id'),
                                prop.get('trade_type_id'),
                                prop.get('region_id'),
                                prop.get('collected_date', date.today()),
                                prop.get('last_seen_date', date.today()),
                                True,  # is_active
                                json.dumps(prop.get('tag_list', [])),
                                prop.get('description', ''),
                                datetime.now(),
                                datetime.now()
                            )
                            for prop in batch
                        ]
                        
                        psycopg2.extras.execute_values(
                            cursor, insert_sql, values,
                            template=None, page_size=self.config.batch_size
                        )
                        
                        # Get inserted IDs
                        batch_ids = [row['id'] for row in cursor.fetchall()]
                        property_ids.extend(batch_ids)
                        
                        self.metrics.successful_inserts += len(batch_ids)
                        conn.commit()
                        
                        batch_time = time.time() - batch_start
                        logger.info(f"🚀 Sync Batch {i//self.config.batch_size + 1}: {len(batch_ids)} properties in {batch_time:.2f}s")
                        
                    except Exception as e:
                        conn.rollback()
                        self.metrics.failed_inserts += len(batch)
                        logger.error(f"❌ Sync Batch {i//self.config.batch_size + 1} failed: {e}")
        
        # Update metrics
        self.metrics.total_processed = len(properties_data)
        self.metrics.total_time = time.time() - start_time
        self.metrics.calculate_rates()
        
        return property_ids
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(
                self.database_url,
                connect_timeout=self.config.connection_timeout
            )
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def print_performance_metrics(self):
        """Print detailed performance metrics"""
        print("\n" + "="*60)
        print("📊 SYNC BATCH PROCESSING PERFORMANCE METRICS")
        print("="*60)
        print(f"✅ Total Processed: {self.metrics.total_processed:,} records")
        print(f"✅ Successful Inserts: {self.metrics.successful_inserts:,} records")
        print(f"❌ Failed Inserts: {self.metrics.failed_inserts:,} records")
        print(f"⏱️  Total Time: {self.metrics.total_time:.2f} seconds")
        print(f"🚀 Records/Second: {self.metrics.records_per_second:.1f}")
        
        success_rate = (self.metrics.successful_inserts / max(self.metrics.total_processed, 1)) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print("="*60)

# Example usage and testing
async def test_batch_processor():
    """Test the batch processor with sample data"""
    DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"
    
    # Sample property data
    sample_properties = [
        {
            'article_no': f'test_{i}',
            'article_name': f'Test Property {i}',
            'real_estate_type_id': 1,
            'trade_type_id': 1,
            'region_id': 1,
            'tag_list': ['test', 'sample'],
            'description': f'Test property description {i}'
        }
        for i in range(1000)  # 1000 test properties
    ]
    
    # Initialize batch processor
    config = BatchConfig(
        batch_size=200,
        max_connections=8,
        use_copy_from=True
    )
    
    processor = BatchProcessor(DATABASE_URL, config)
    
    try:
        await processor.initialize()
        
        # Bulk insert properties
        property_ids = await processor.bulk_insert_properties(sample_properties)
        
        # Print metrics
        processor.print_performance_metrics()
        
        logger.info(f"✅ Test completed: {len(property_ids)} properties processed")
        
    finally:
        await processor.cleanup()

if __name__ == "__main__":
    # Run async test
    asyncio.run(test_batch_processor())