#!/usr/bin/env python3
"""
CACHING LAYER INTEGRATION
High-performance Redis caching for Naver real estate collection system
- Foreign key lookup caching with intelligent invalidation
- Query result caching with TTL management
- Session data caching for rate limit tracking
- Memory-efficient cache operations
"""

import redis
import redis.asyncio as aioredis
import json
import pickle
import hashlib
import time
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import logging
from functools import wraps
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Cache configuration settings"""
    redis_url: str = "redis://localhost:6379/0"
    max_connections: int = 20
    socket_timeout: int = 30
    socket_connect_timeout: int = 10
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # TTL settings (in seconds)
    default_ttl: int = 3600  # 1 hour
    reference_data_ttl: int = 86400  # 24 hours (foreign keys don't change often)
    query_result_ttl: int = 1800  # 30 minutes
    session_data_ttl: int = 7200  # 2 hours
    rate_limit_ttl: int = 3600  # 1 hour
    
    # Cache key prefixes
    foreign_key_prefix: str = "fk:"
    query_result_prefix: str = "qr:"
    session_prefix: str = "session:"
    rate_limit_prefix: str = "rate:"
    stats_prefix: str = "stats:"

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100
    
    def reset(self):
        """Reset all stats"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_requests = 0

class CacheManager:
    """High-performance Redis cache manager with intelligent caching strategies"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client = None
        self.async_redis_client = None
        self.stats = CacheStats()
        self._lock = threading.Lock()
        
        # Cache key mapping for foreign key lookups
        self.foreign_key_maps = {
            'real_estate_types': {},
            'trade_types': {},
            'regions': {},
            'facility_types': {}
        }
        
        # Query cache invalidation patterns
        self.invalidation_patterns = {
            'properties_new': ['qr:property_*', 'qr:search_*'],
            'property_prices': ['qr:price_*', 'qr:property_*'],
            'regions': ['fk:region_*', 'qr:region_*']
        }
    
    def initialize(self):
        """Initialize Redis connections"""
        try:
            # Synchronous Redis client
            self.redis_client = redis.Redis.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval,
                decode_responses=False  # We'll handle encoding ourselves
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis synchronous client initialized successfully")
            
            # Pre-load foreign key mappings
            self._preload_foreign_key_cache()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis client: {e}")
            raise
    
    async def initialize_async(self):
        """Initialize async Redis client"""
        try:
            self.async_redis_client = aioredis.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval,
                decode_responses=False
            )
            
            # Test async connection
            await self.async_redis_client.ping()
            logger.info("✅ Redis async client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize async Redis client: {e}")
            raise
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache key"""
        key_components = [str(arg) for arg in args]
        key_base = ":".join(key_components)
        
        # For long keys, use hash to prevent Redis key length issues
        if len(key_base) > 200:
            key_hash = hashlib.md5(key_base.encode()).hexdigest()
            return f"{prefix}{key_hash}"
        
        return f"{prefix}{key_base}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Efficiently serialize data for Redis storage"""
        try:
            if isinstance(data, (dict, list)):
                return json.dumps(data, default=str, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, (int, float, str)):
                return str(data).encode('utf-8')
            else:
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"❌ Serialization error: {e}")
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Efficiently deserialize data from Redis"""
        try:
            # Try JSON first (most common case)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                # Fallback to pickle
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"❌ Deserialization error: {e}")
                return data.decode('utf-8', errors='ignore')
    
    # =====================================================================
    # FOREIGN KEY CACHING (Optimizes _resolve_*_id functions)
    # =====================================================================
    
    def cache_foreign_key_lookup(self, table_name: str, lookup_field: str, 
                                lookup_value: str, result_id: int):
        """Cache foreign key lookup result"""
        if not self.redis_client:
            return
        
        cache_key = self._generate_cache_key(
            self.config.foreign_key_prefix,
            table_name, lookup_field, lookup_value
        )
        
        try:
            self.redis_client.setex(
                cache_key,
                self.config.reference_data_ttl,
                self._serialize_data(result_id)
            )
            
            # Also cache reverse lookup (id -> value)
            reverse_key = self._generate_cache_key(
                self.config.foreign_key_prefix,
                table_name, "id", str(result_id)
            )
            self.redis_client.setex(
                reverse_key,
                self.config.reference_data_ttl,
                self._serialize_data({lookup_field: lookup_value})
            )
            
            with self._lock:
                self.stats.sets += 1
            
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to cache foreign key lookup: {e}")
    
    def get_foreign_key_lookup(self, table_name: str, lookup_field: str, 
                              lookup_value: str) -> Optional[int]:
        """Get cached foreign key lookup result"""
        if not self.redis_client:
            return None
        
        cache_key = self._generate_cache_key(
            self.config.foreign_key_prefix,
            table_name, lookup_field, lookup_value
        )
        
        try:
            with self._lock:
                self.stats.total_requests += 1
            
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                with self._lock:
                    self.stats.hits += 1
                
                result = self._deserialize_data(cached_data)
                logger.debug(f"🎯 Cache HIT: {table_name}.{lookup_field}={lookup_value} -> {result}")
                return int(result) if result else None
            else:
                with self._lock:
                    self.stats.misses += 1
                logger.debug(f"❌ Cache MISS: {table_name}.{lookup_field}={lookup_value}")
                return None
                
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to get foreign key lookup: {e}")
            return None
    
    def bulk_cache_foreign_keys(self, table_name: str, lookup_field: str, 
                               mappings: Dict[str, int]):
        """Bulk cache multiple foreign key lookups"""
        if not self.redis_client or not mappings:
            return
        
        try:
            pipe = self.redis_client.pipeline()
            
            for lookup_value, result_id in mappings.items():
                cache_key = self._generate_cache_key(
                    self.config.foreign_key_prefix,
                    table_name, lookup_field, lookup_value
                )
                
                pipe.setex(
                    cache_key,
                    self.config.reference_data_ttl,
                    self._serialize_data(result_id)
                )
            
            pipe.execute()
            
            with self._lock:
                self.stats.sets += len(mappings)
            
            logger.info(f"✅ Bulk cached {len(mappings)} {table_name} foreign key lookups")
            
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to bulk cache foreign keys: {e}")
    
    def _preload_foreign_key_cache(self):
        """Pre-load commonly used foreign key mappings"""
        if not self.redis_client:
            return
        
        try:
            # This would typically load from database
            # For now, we'll implement a lazy loading approach
            logger.info("🔄 Foreign key cache preloading configured (lazy loading)")
            
        except Exception as e:
            logger.error(f"❌ Failed to preload foreign key cache: {e}")
    
    # =====================================================================
    # QUERY RESULT CACHING
    # =====================================================================
    
    def cache_query_result(self, query_signature: str, result: Any, 
                          ttl: Optional[int] = None):
        """Cache query result with automatic TTL"""
        if not self.redis_client:
            return
        
        cache_key = self._generate_cache_key(
            self.config.query_result_prefix,
            query_signature
        )
        
        ttl = ttl or self.config.query_result_ttl
        
        try:
            self.redis_client.setex(
                cache_key,
                ttl,
                self._serialize_data(result)
            )
            
            with self._lock:
                self.stats.sets += 1
            
            logger.debug(f"💾 Cached query result: {query_signature[:50]}... (TTL: {ttl}s)")
            
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to cache query result: {e}")
    
    def get_cached_query_result(self, query_signature: str) -> Optional[Any]:
        """Get cached query result"""
        if not self.redis_client:
            return None
        
        cache_key = self._generate_cache_key(
            self.config.query_result_prefix,
            query_signature
        )
        
        try:
            with self._lock:
                self.stats.total_requests += 1
            
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                with self._lock:
                    self.stats.hits += 1
                
                result = self._deserialize_data(cached_data)
                logger.debug(f"🎯 Query cache HIT: {query_signature[:50]}...")
                return result
            else:
                with self._lock:
                    self.stats.misses += 1
                logger.debug(f"❌ Query cache MISS: {query_signature[:50]}...")
                return None
                
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to get cached query result: {e}")
            return None
    
    def query_cache_decorator(self, ttl: Optional[int] = None):
        """Decorator for automatic query result caching"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate query signature from function name and arguments
                query_signature = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"
                
                # Try to get cached result
                cached_result = self.get_cached_query_result(query_signature)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                if result is not None:
                    self.cache_query_result(query_signature, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    # =====================================================================
    # SESSION AND RATE LIMITING
    # =====================================================================
    
    def cache_session_data(self, session_id: str, session_data: Dict[str, Any]):
        """Cache session data (tokens, cookies, etc.)"""
        if not self.redis_client:
            return
        
        cache_key = self._generate_cache_key(
            self.config.session_prefix,
            session_id
        )
        
        try:
            self.redis_client.setex(
                cache_key,
                self.config.session_data_ttl,
                self._serialize_data(session_data)
            )
            
            with self._lock:
                self.stats.sets += 1
            
            logger.debug(f"💾 Cached session data: {session_id}")
            
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to cache session data: {e}")
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data"""
        if not self.redis_client:
            return None
        
        cache_key = self._generate_cache_key(
            self.config.session_prefix,
            session_id
        )
        
        try:
            with self._lock:
                self.stats.total_requests += 1
            
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                with self._lock:
                    self.stats.hits += 1
                
                return self._deserialize_data(cached_data)
            else:
                with self._lock:
                    self.stats.misses += 1
                return None
                
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to get session data: {e}")
            return None
    
    def track_rate_limit(self, identifier: str, limit: int = 60, 
                        window: int = 3600) -> bool:
        """Track rate limiting with sliding window"""
        if not self.redis_client:
            return True  # Allow if cache is unavailable
        
        cache_key = self._generate_cache_key(
            self.config.rate_limit_prefix,
            identifier
        )
        
        try:
            current_time = int(time.time())
            window_start = current_time - window
            
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(cache_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(cache_key)
            
            # Add current request
            pipe.zadd(cache_key, {str(current_time): current_time})
            
            # Set TTL
            pipe.expire(cache_key, window)
            
            results = pipe.execute()
            current_count = results[1]
            
            # Check if under limit
            return current_count < limit
            
        except Exception as e:
            logger.error(f"❌ Failed to track rate limit: {e}")
            return True  # Allow on error
    
    # =====================================================================
    # CACHE INVALIDATION
    # =====================================================================
    
    def invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        if not self.redis_client:
            return
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                
                with self._lock:
                    self.stats.deletes += len(keys)
                
                logger.info(f"🗑️  Invalidated {len(keys)} cache entries matching: {pattern}")
            
        except Exception as e:
            with self._lock:
                self.stats.errors += 1
            logger.error(f"❌ Failed to invalidate cache pattern {pattern}: {e}")
    
    def invalidate_table_cache(self, table_name: str):
        """Invalidate cache entries related to specific table"""
        if table_name in self.invalidation_patterns:
            for pattern in self.invalidation_patterns[table_name]:
                self.invalidate_cache_pattern(pattern)
    
    def clear_all_cache(self):
        """Clear all cache (use with caution)"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.flushdb()
            logger.warning("⚠️ ALL CACHE CLEARED")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear all cache: {e}")
    
    # =====================================================================
    # STATISTICS AND MONITORING
    # =====================================================================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._lock:
            stats_dict = asdict(self.stats)
        
        # Add Redis-specific stats
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
                stats_dict.update({
                    'redis_connected_clients': redis_info.get('connected_clients', 0),
                    'redis_used_memory': redis_info.get('used_memory_human', 'N/A'),
                    'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'redis_keyspace_misses': redis_info.get('keyspace_misses', 0),
                    'redis_total_commands_processed': redis_info.get('total_commands_processed', 0)
                })
            except Exception as e:
                logger.error(f"❌ Failed to get Redis stats: {e}")
        
        return stats_dict
    
    def print_cache_stats(self):
        """Print formatted cache statistics"""
        stats = self.get_cache_stats()
        
        print("\n" + "="*60)
        print("📊 CACHE PERFORMANCE STATISTICS")
        print("="*60)
        print(f"🎯 Hit Rate: {stats['hit_rate']:.1f}%")
        print(f"✅ Cache Hits: {stats['hits']:,}")
        print(f"❌ Cache Misses: {stats['misses']:,}")
        print(f"💾 Cache Sets: {stats['sets']:,}")
        print(f"🗑️  Cache Deletes: {stats['deletes']:,}")
        print(f"⚠️  Cache Errors: {stats['errors']:,}")
        print(f"📈 Total Requests: {stats['total_requests']:,}")
        
        if 'redis_used_memory' in stats:
            print(f"\n🔧 Redis Memory Usage: {stats['redis_used_memory']}")
            print(f"👥 Redis Connections: {stats['redis_connected_clients']}")
            
            redis_hit_rate = 0
            if stats['redis_keyspace_hits'] + stats['redis_keyspace_misses'] > 0:
                redis_hit_rate = (stats['redis_keyspace_hits'] / 
                                (stats['redis_keyspace_hits'] + stats['redis_keyspace_misses'])) * 100
            print(f"🎯 Redis Hit Rate: {redis_hit_rate:.1f}%")
        
        print("="*60)
    
    def reset_stats(self):
        """Reset cache statistics"""
        with self._lock:
            self.stats.reset()
        logger.info("📊 Cache statistics reset")
    
    # =====================================================================
    # CLEANUP AND MAINTENANCE
    # =====================================================================
    
    def cleanup(self):
        """Clean up cache connections"""
        try:
            if self.redis_client:
                self.redis_client.close()
            logger.info("🔒 Cache connections closed")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup cache: {e}")
    
    async def cleanup_async(self):
        """Clean up async cache connections"""
        try:
            if self.async_redis_client:
                await self.async_redis_client.close()
            logger.info("🔒 Async cache connections closed")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup async cache: {e}")

# Enhanced collector integration
class CachedForeignKeyResolver:
    """Drop-in replacement for foreign key resolution with caching"""
    
    def __init__(self, supabase_client, cache_manager: CacheManager):
        self.client = supabase_client
        self.cache = cache_manager
    
    def resolve_real_estate_type_id(self, type_name: str) -> Optional[int]:
        """Cached real estate type ID resolution"""
        # Check cache first
        cached_id = self.cache.get_foreign_key_lookup('real_estate_types', 'type_name', type_name)
        if cached_id is not None:
            return cached_id
        
        # Database lookup
        try:
            result = self.client.table('real_estate_types').select('id').eq('type_name', type_name).execute()
            if result.data:
                type_id = result.data[0]['id']
                # Cache the result
                self.cache.cache_foreign_key_lookup('real_estate_types', 'type_name', type_name, type_id)
                return type_id
        except Exception as e:
            logger.error(f"❌ Failed to resolve real estate type ID: {e}")
        
        return None
    
    def resolve_trade_type_id(self, type_name: str) -> Optional[int]:
        """Cached trade type ID resolution"""
        cached_id = self.cache.get_foreign_key_lookup('trade_types', 'type_name', type_name)
        if cached_id is not None:
            return cached_id
        
        try:
            result = self.client.table('trade_types').select('id').eq('type_name', type_name).execute()
            if result.data:
                type_id = result.data[0]['id']
                self.cache.cache_foreign_key_lookup('trade_types', 'type_name', type_name, type_id)
                return type_id
        except Exception as e:
            logger.error(f"❌ Failed to resolve trade type ID: {e}")
        
        return None
    
    def resolve_region_id(self, cortar_no: str) -> Optional[int]:
        """Cached region ID resolution"""
        cached_id = self.cache.get_foreign_key_lookup('regions', 'cortar_no', cortar_no)
        if cached_id is not None:
            return cached_id
        
        try:
            result = self.client.table('regions').select('id').eq('cortar_no', cortar_no).execute()
            if result.data:
                region_id = result.data[0]['id']
                self.cache.cache_foreign_key_lookup('regions', 'cortar_no', cortar_no, region_id)
                return region_id
        except Exception as e:
            logger.error(f"❌ Failed to resolve region ID: {e}")
        
        return None

# Example usage
def main():
    """Example usage of the caching system"""
    # Initialize cache
    config = CacheConfig(
        redis_url="redis://localhost:6379/0",
        reference_data_ttl=86400,  # 24 hours for foreign keys
        query_result_ttl=1800      # 30 minutes for query results
    )
    
    cache_manager = CacheManager(config)
    cache_manager.initialize()
    
    try:
        # Test foreign key caching
        cache_manager.cache_foreign_key_lookup('real_estate_types', 'type_name', '아파트', 1)
        cached_id = cache_manager.get_foreign_key_lookup('real_estate_types', 'type_name', '아파트')
        print(f"Cached real estate type ID: {cached_id}")
        
        # Test query result caching
        @cache_manager.query_cache_decorator(ttl=3600)
        def expensive_query(region_id: int):
            time.sleep(1)  # Simulate expensive operation
            return {"properties": [1, 2, 3], "region": region_id}
        
        # First call - miss
        result1 = expensive_query(1)
        print(f"First call result: {result1}")
        
        # Second call - hit
        result2 = expensive_query(1)
        print(f"Second call result: {result2}")
        
        # Print stats
        cache_manager.print_cache_stats()
        
    finally:
        cache_manager.cleanup()

if __name__ == "__main__":
    main()