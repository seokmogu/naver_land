-- =====================================================================
-- DATABASE OPTIMIZATION SUITE
-- Naver Real Estate Collection System Performance Enhancement
-- =====================================================================

-- =====================================================================
-- 1. COMPREHENSIVE INDEXING STRATEGY
-- =====================================================================

-- === Primary Performance Indexes ===

-- Properties table optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_region_type_active 
ON properties_new(region_id, real_estate_type_id, is_active) 
WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_created_at_btree 
ON properties_new USING btree(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_article_no_hash 
ON properties_new USING hash(article_no);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_last_seen 
ON properties_new(last_seen_date DESC) 
WHERE is_active = true;

-- Property prices optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prices_property_type_valid 
ON property_prices(property_id, price_type, valid_from DESC) 
WHERE valid_to IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prices_amount_range 
ON property_prices(price_type, amount) 
WHERE amount > 0 AND (valid_to IS NULL OR valid_to > CURRENT_DATE);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prices_current_active 
ON property_prices(property_id, price_type, amount) 
WHERE valid_to IS NULL;

-- Property locations optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_locations_coordinates_gist 
ON property_locations USING gist(point(longitude, latitude)) 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_locations_region_active 
ON property_locations(region_id, property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_locations_address_search 
ON property_locations USING gin(to_tsvector('korean', address_road));

-- Property physical optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_physical_area_rooms 
ON property_physical(area_exclusive, room_count, bathroom_count) 
WHERE area_exclusive > 0;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_physical_floor_range 
ON property_physical(floor_total, floor_current) 
WHERE floor_total > 0;

-- === Reference Table Indexes for Fast Lookups ===

-- Real estate types
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_real_estate_types_name_active 
ON real_estate_types(type_name, is_active) 
WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_real_estate_types_code_hash 
ON real_estate_types USING hash(type_code);

-- Trade types
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trade_types_name_active 
ON trade_types(type_name, is_active) 
WHERE is_active = true;

-- Regions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_regions_cortar_active 
ON regions(cortar_no, is_active) 
WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_regions_dong_gu 
ON regions(dong_name, gu_name);

-- === Complex Query Optimization Indexes ===

-- Property search optimization (most common queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_property_search_comprehensive 
ON properties_new(region_id, real_estate_type_id, trade_type_id, is_active, last_seen_date)
WHERE is_active = true;

-- Price range search optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_range_search 
ON property_prices(price_type, amount, property_id, valid_from) 
WHERE valid_to IS NULL AND amount > 0;

-- Realtor performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtors_performance 
ON realtors(is_verified, rating DESC, total_listings DESC) 
WHERE is_verified = true AND rating > 0;

-- Property-realtor relationship optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_property_realtors_active 
ON property_realtors(property_id, is_primary, is_active) 
WHERE is_active = true;

-- Image optimization for gallery loading
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_images_property_order 
ON property_images(property_id, image_type, image_order) 
WHERE image_url IS NOT NULL AND image_url != '';

-- Facility search optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_facilities_available 
ON property_facilities(facility_id, available, condition_grade) 
WHERE available = true;

-- =====================================================================
-- 2. PARTIAL INDEXES FOR FILTERED QUERIES
-- =====================================================================

-- Active properties only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_properties_recent 
ON properties_new(last_seen_date DESC, region_id) 
WHERE is_active = true AND last_seen_date >= CURRENT_DATE - INTERVAL '30 days';

-- High-value properties
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_high_value_properties 
ON property_prices(amount DESC, property_id) 
WHERE price_type = 'sale' AND amount >= 100000 AND valid_to IS NULL;

-- Recent price changes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recent_price_changes 
ON price_history_new(changed_date DESC, property_id) 
WHERE changed_date >= CURRENT_DATE - INTERVAL '30 days';

-- =====================================================================
-- 3. EXPRESSION INDEXES FOR COMPUTED QUERIES
-- =====================================================================

-- Price per square meter calculation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_per_sqm 
ON property_prices((amount::decimal / NULLIF((
    SELECT area_exclusive FROM property_physical pp 
    WHERE pp.property_id = property_prices.property_id
), 0))) 
WHERE price_type = 'sale' AND valid_to IS NULL;

-- Property age calculation (for listings with approval dates)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_property_age 
ON property_physical((EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM approval_date))) 
WHERE approval_date IS NOT NULL;

-- =====================================================================
-- 4. SPECIALIZED INDEXES FOR REPORTING QUERIES
-- =====================================================================

-- Monthly statistics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_monthly_stats 
ON properties_new(EXTRACT(YEAR FROM created_at), EXTRACT(MONTH FROM created_at), region_id);

-- Daily collection tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_daily_collection 
ON properties_new(collected_date, region_id, real_estate_type_id);

-- Price trend analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_trend_analysis 
ON price_history_new(changed_date, region_id, price_type, market_trend);

-- =====================================================================
-- 5. FOREIGN KEY CONSTRAINT OPTIMIZATION
-- =====================================================================

-- Ensure all foreign key columns have proper indexes
-- (These should already exist, but ensuring they're optimized)

-- Properties references
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_properties_real_estate_type 
ON properties_new(real_estate_type_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_properties_trade_type 
ON properties_new(trade_type_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_properties_region 
ON properties_new(region_id);

-- Child table foreign keys
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_prices_property 
ON property_prices(property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_locations_property 
ON property_locations(property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_physical_property 
ON property_physical(property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_images_property 
ON property_images(property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_facilities_property 
ON property_facilities(property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_realtors_property 
ON property_realtors(property_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fk_property_realtors_realtor 
ON property_realtors(realtor_id);

-- =====================================================================
-- 6. VACUUM AND ANALYZE OPTIMIZATION
-- =====================================================================

-- Update table statistics for query planner optimization
ANALYZE properties_new;
ANALYZE property_prices;
ANALYZE property_locations;
ANALYZE property_physical;
ANALYZE real_estate_types;
ANALYZE trade_types;
ANALYZE regions;
ANALYZE realtors;
ANALYZE property_realtors;
ANALYZE property_images;
ANALYZE property_facilities;

-- =====================================================================
-- 7. MATERIALIZED VIEWS FOR EXPENSIVE QUERIES
-- =====================================================================

-- Popular search combinations (refresh periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_popular_searches AS
SELECT 
    r.dong_name,
    r.gu_name,
    ret.type_name as real_estate_type,
    tt.type_name as trade_type,
    COUNT(*) as property_count,
    AVG(pp.amount) as avg_price,
    MIN(pp.amount) as min_price,
    MAX(pp.amount) as max_price,
    AVG(phy.area_exclusive) as avg_area
FROM properties_new p
JOIN regions r ON r.id = p.region_id
JOIN real_estate_types ret ON ret.id = p.real_estate_type_id
JOIN trade_types tt ON tt.id = p.trade_type_id
LEFT JOIN property_prices pp ON pp.property_id = p.id 
    AND pp.price_type IN ('sale', 'rent') 
    AND pp.valid_to IS NULL
LEFT JOIN property_physical phy ON phy.property_id = p.id
WHERE p.is_active = true
GROUP BY r.dong_name, r.gu_name, ret.type_name, tt.type_name
HAVING COUNT(*) >= 5;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_popular_searches_location 
ON mv_popular_searches(dong_name, gu_name, real_estate_type);

-- Refresh schedule (to be run periodically)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_popular_searches;

-- =====================================================================
-- 8. DATABASE CONFIGURATION OPTIMIZATION RECOMMENDATIONS
-- =====================================================================

-- Note: These are recommendations to be applied via postgresql.conf or ALTER SYSTEM
/*
RECOMMENDED POSTGRESQL CONFIGURATION CHANGES:

-- Memory settings (adjust based on available RAM)
shared_buffers = 256MB                    # 25% of available RAM
effective_cache_size = 1GB               # 75% of available RAM  
work_mem = 16MB                          # For complex queries
maintenance_work_mem = 64MB              # For VACUUM, CREATE INDEX

-- Query planning
random_page_cost = 1.1                   # For SSD storage
effective_io_concurrency = 200           # For SSD storage
seq_page_cost = 1                        # Default for balanced workload

-- WAL settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 1GB
min_wal_size = 80MB

-- Connection settings
max_connections = 200                    # Adjust based on expected load

-- Logging (for performance monitoring)
log_statement = 'ddl'                    # Log DDL statements
log_min_duration_statement = 1000        # Log slow queries (>1 second)
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

-- Auto vacuum settings
autovacuum = on
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_threshold = 50
autovacuum_analyze_scale_factor = 0.05

-- Apply these with:
-- ALTER SYSTEM SET parameter_name = 'value';
-- SELECT pg_reload_conf();
*/

-- =====================================================================
-- 9. INDEX USAGE MONITORING
-- =====================================================================

-- Function to monitor index usage
CREATE OR REPLACE FUNCTION get_index_usage_stats()
RETURNS TABLE (
    schemaname text,
    tablename text,
    indexname text,
    idx_scans bigint,
    idx_rows_read bigint,
    idx_rows_fetched bigint,
    usage_ratio numeric
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.schemaname::text,
        s.tablename::text,
        s.indexrelname::text,
        s.idx_scan,
        s.idx_tup_read,
        s.idx_tup_fetch,
        CASE 
            WHEN s.idx_scan = 0 THEN 0
            ELSE ROUND((s.idx_tup_fetch::numeric / NULLIF(s.idx_tup_read, 0)) * 100, 2)
        END as usage_ratio
    FROM pg_stat_user_indexes s
    WHERE s.schemaname = 'public'
    ORDER BY s.idx_scan DESC, s.idx_tup_read DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to find unused indexes
CREATE OR REPLACE FUNCTION find_unused_indexes()
RETURNS TABLE (
    schemaname text,
    tablename text,
    indexname text,
    index_size text
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.schemaname::text,
        s.tablename::text,
        s.indexrelname::text,
        pg_size_pretty(pg_relation_size(s.indexrelid))::text
    FROM pg_stat_user_indexes s
    WHERE s.idx_scan = 0 
    AND s.schemaname = 'public'
    AND s.indexrelname NOT LIKE '%_pkey'  -- Exclude primary keys
    ORDER BY pg_relation_size(s.indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 10. COMPLETION STATUS CHECK
-- =====================================================================

-- Function to verify optimization completion
CREATE OR REPLACE FUNCTION check_optimization_status()
RETURNS TEXT AS $$
DECLARE
    index_count INTEGER;
    mv_count INTEGER;
    function_count INTEGER;
    total_indexes INTEGER;
BEGIN
    -- Count optimization indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND (indexname LIKE 'idx_%' OR indexname LIKE 'mv_%');
    
    -- Count materialized views
    SELECT COUNT(*) INTO mv_count
    FROM pg_matviews 
    WHERE schemaname = 'public';
    
    -- Count optimization functions
    SELECT COUNT(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' 
    AND p.proname IN ('get_index_usage_stats', 'find_unused_indexes', 'check_optimization_status');
    
    -- Total index count including system indexes
    SELECT COUNT(*) INTO total_indexes
    FROM pg_indexes 
    WHERE schemaname = 'public';
    
    RETURN FORMAT('DATABASE OPTIMIZATION COMPLETE! 
Performance indexes: %s, 
Materialized views: %s, 
Monitoring functions: %s,
Total indexes: %s',
        index_count, mv_count, function_count, total_indexes);
END;
$$ LANGUAGE plpgsql;

-- Run optimization status check
SELECT check_optimization_status();

-- =====================================================================
-- OPTIMIZATION SUITE INSTALLATION COMPLETE
-- =====================================================================