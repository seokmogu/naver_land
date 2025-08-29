-- =====================================================================
-- PERFORMANCE MONITORING AND ANALYSIS QUERIES
-- Real-time database performance tracking and optimization guidance
-- =====================================================================

-- =====================================================================
-- 1. SLOW QUERY IDENTIFICATION
-- =====================================================================

-- Monitor currently running slow queries
CREATE OR REPLACE VIEW v_slow_queries_current AS
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state,
    client_addr,
    application_name,
    wait_event_type,
    wait_event
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state = 'active'
ORDER BY duration DESC;

-- Get slow query statistics (requires pg_stat_statements extension)
CREATE OR REPLACE FUNCTION get_slow_query_stats(min_duration_ms INTEGER DEFAULT 1000)
RETURNS TABLE (
    query_summary TEXT,
    calls BIGINT,
    total_time_ms NUMERIC,
    mean_time_ms NUMERIC,
    max_time_ms NUMERIC,
    rows_examined BIGINT,
    query_efficiency NUMERIC
) AS $$
BEGIN
    -- Check if pg_stat_statements is available
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') THEN
        RAISE NOTICE 'pg_stat_statements extension not installed. Cannot provide detailed query statistics.';
        RETURN;
    END IF;

    RETURN QUERY
    SELECT 
        LEFT(regexp_replace(pss.query, '\s+', ' ', 'g'), 100) AS query_summary,
        pss.calls,
        ROUND(pss.total_exec_time::numeric, 2) AS total_time_ms,
        ROUND(pss.mean_exec_time::numeric, 2) AS mean_time_ms,
        ROUND(pss.max_exec_time::numeric, 2) AS max_time_ms,
        pss.rows AS rows_examined,
        CASE 
            WHEN pss.calls > 0 THEN ROUND((pss.rows::numeric / pss.calls), 2)
            ELSE 0
        END AS query_efficiency
    FROM pg_stat_statements pss
    WHERE pss.mean_exec_time > min_duration_ms
    ORDER BY pss.mean_exec_time DESC
    LIMIT 20;
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Error accessing pg_stat_statements: %', SQLERRM;
        RETURN;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 2. INDEX PERFORMANCE ANALYSIS
-- =====================================================================

-- Index usage effectiveness
CREATE OR REPLACE VIEW v_index_usage_analysis AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 10 THEN 'LOW_USAGE'
        WHEN idx_tup_fetch::float / GREATEST(idx_tup_read, 1) < 0.1 THEN 'INEFFICIENT'
        ELSE 'GOOD'
    END as index_status,
    ROUND((idx_tup_fetch::numeric / GREATEST(idx_tup_read, 1)) * 100, 2) as selectivity_ratio
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY 
    CASE 
        WHEN idx_scan = 0 THEN 1
        WHEN idx_scan < 10 THEN 2
        ELSE 3
    END,
    pg_relation_size(indexrelid) DESC;

-- Missing index suggestions based on query patterns
CREATE OR REPLACE FUNCTION suggest_missing_indexes()
RETURNS TABLE (
    table_name TEXT,
    suggested_columns TEXT,
    reason TEXT,
    query_pattern TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH seq_scan_tables AS (
        SELECT 
            schemaname,
            tablename,
            seq_scan,
            seq_tup_read,
            n_tup_ins + n_tup_upd + n_tup_del as modifications
        FROM pg_stat_user_tables 
        WHERE schemaname = 'public'
        AND seq_scan > 100  -- High sequential scan count
        AND seq_tup_read > seq_scan * 1000  -- High rows per scan
    )
    SELECT 
        sst.tablename::TEXT,
        CASE 
            WHEN sst.tablename = 'properties_new' THEN 'region_id, is_active, last_seen_date'
            WHEN sst.tablename = 'property_prices' THEN 'property_id, valid_to, price_type'
            WHEN sst.tablename = 'property_locations' THEN 'latitude, longitude (GIST)'
            ELSE 'id, created_at'
        END::TEXT,
        FORMAT('High seq_scan ratio: %s scans, %s rows read', sst.seq_scan, sst.seq_tup_read)::TEXT,
        'Frequent full table scans detected'::TEXT
    FROM seq_scan_tables sst
    ORDER BY sst.seq_tup_read DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 3. TABLE PERFORMANCE METRICS
-- =====================================================================

-- Table size and performance overview
CREATE OR REPLACE VIEW v_table_performance AS
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    CASE 
        WHEN n_live_tup > 0 THEN ROUND((n_dead_tup::numeric / n_live_tup) * 100, 2)
        ELSE 0
    END as dead_row_ratio,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    CASE 
        WHEN seq_scan + idx_scan > 0 THEN 
            ROUND((idx_scan::numeric / (seq_scan + idx_scan)) * 100, 2)
        ELSE 0
    END as index_usage_ratio,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables psu
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- =====================================================================
-- 4. CONNECTION AND LOCK MONITORING
-- =====================================================================

-- Active connections and their activities
CREATE OR REPLACE VIEW v_connection_monitor AS
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    now() - query_start as query_duration,
    wait_event_type,
    wait_event,
    LEFT(query, 100) as current_query
FROM pg_stat_activity 
WHERE state != 'idle'
AND pid != pg_backend_pid()  -- Exclude current connection
ORDER BY query_start;

-- Lock analysis
CREATE OR REPLACE VIEW v_lock_analysis AS
SELECT 
    l.locktype,
    l.database,
    l.relation::regclass as table_name,
    l.mode,
    l.granted,
    a.pid,
    a.usename,
    a.application_name,
    a.client_addr,
    now() - a.query_start as lock_duration,
    LEFT(a.query, 100) as query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted 
OR l.mode IN ('AccessExclusiveLock', 'ExclusiveLock')
ORDER BY a.query_start;

-- =====================================================================
-- 5. CACHE HIT RATIOS
-- =====================================================================

-- Buffer cache hit ratios
CREATE OR REPLACE VIEW v_cache_hit_ratios AS
SELECT 
    'Database Cache' as cache_type,
    ROUND(
        (sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2
    ) as hit_ratio,
    CASE 
        WHEN ROUND((sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2) >= 95 THEN 'EXCELLENT'
        WHEN ROUND((sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2) >= 90 THEN 'GOOD'
        WHEN ROUND((sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2) >= 80 THEN 'FAIR'
        ELSE 'POOR'
    END as performance_status
FROM pg_statio_user_tables 
WHERE schemaname = 'public'

UNION ALL

SELECT 
    'Index Cache' as cache_type,
    ROUND(
        (sum(idx_blks_hit) / GREATEST(sum(idx_blks_hit + idx_blks_read), 1)) * 100, 2
    ) as hit_ratio,
    CASE 
        WHEN ROUND((sum(idx_blks_hit) / GREATEST(sum(idx_blks_hit + idx_blks_read), 1)) * 100, 2) >= 95 THEN 'EXCELLENT'
        WHEN ROUND((sum(idx_blks_hit) / GREATEST(sum(idx_blks_hit + idx_blks_read), 1)) * 100, 2) >= 90 THEN 'GOOD'
        WHEN ROUND((sum(idx_blks_hit) / GREATEST(sum(idx_blks_hit + idx_blks_read), 1)) * 100, 2) >= 80 THEN 'FAIR'
        ELSE 'POOR'
    END as performance_status
FROM pg_statio_user_indexes
WHERE schemaname = 'public';

-- =====================================================================
-- 6. QUERY EXECUTION PLAN ANALYSIS
-- =====================================================================

-- Function to analyze execution plans for common queries
CREATE OR REPLACE FUNCTION analyze_query_performance(query_text TEXT)
RETURNS TABLE (
    execution_plan TEXT,
    estimated_cost NUMERIC,
    estimated_rows BIGINT,
    recommendations TEXT
) AS $$
DECLARE
    plan_result TEXT;
BEGIN
    -- Execute EXPLAIN (without running the query)
    EXECUTE format('EXPLAIN (FORMAT JSON, ANALYZE FALSE, COSTS TRUE) %s', query_text)
    INTO plan_result;
    
    RETURN QUERY
    SELECT 
        plan_result::TEXT,
        0::NUMERIC,  -- Placeholder for cost extraction
        0::BIGINT,   -- Placeholder for row estimation
        'Use EXPLAIN ANALYZE for detailed performance analysis'::TEXT;
        
EXCEPTION
    WHEN others THEN
        RETURN QUERY
        SELECT 
            ('Error analyzing query: ' || SQLERRM)::TEXT,
            0::NUMERIC,
            0::BIGINT,
            'Check query syntax and permissions'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 7. VACUUM AND MAINTENANCE MONITORING
-- =====================================================================

-- Tables that need maintenance
CREATE OR REPLACE VIEW v_maintenance_needed AS
SELECT 
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    CASE 
        WHEN n_live_tup > 0 THEN ROUND((n_dead_tup::numeric / n_live_tup) * 100, 2)
        ELSE 0
    END as dead_row_percentage,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    CASE 
        WHEN last_autovacuum IS NULL AND last_vacuum IS NULL THEN 'NEVER_VACUUMED'
        WHEN COALESCE(last_autovacuum, last_vacuum) < now() - interval '7 days' THEN 'VACUUM_NEEDED'
        WHEN n_live_tup > 0 AND (n_dead_tup::numeric / n_live_tup) > 0.2 THEN 'HIGH_DEAD_ROWS'
        WHEN last_autoanalyze IS NULL AND last_analyze IS NULL THEN 'NEVER_ANALYZED'
        WHEN COALESCE(last_autoanalyze, last_analyze) < now() - interval '7 days' THEN 'ANALYZE_NEEDED'
        ELSE 'OK'
    END as maintenance_status,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY 
    CASE 
        WHEN last_autovacuum IS NULL AND last_vacuum IS NULL THEN 1
        WHEN n_live_tup > 0 AND (n_dead_tup::numeric / n_live_tup) > 0.2 THEN 2
        ELSE 3
    END,
    n_dead_tup DESC;

-- =====================================================================
-- 8. REAL-TIME PERFORMANCE DASHBOARD
-- =====================================================================

-- Comprehensive performance dashboard view
CREATE OR REPLACE VIEW v_performance_dashboard AS
WITH performance_metrics AS (
    SELECT 
        'Active Connections' as metric_name,
        count(*)::TEXT as metric_value,
        CASE 
            WHEN count(*) < 50 THEN 'GOOD'
            WHEN count(*) < 100 THEN 'MODERATE'
            ELSE 'HIGH'
        END as status
    FROM pg_stat_activity 
    WHERE state = 'active' AND pid != pg_backend_pid()
    
    UNION ALL
    
    SELECT 
        'Cache Hit Ratio',
        ROUND(
            (sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2
        )::TEXT || '%',
        CASE 
            WHEN ROUND((sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2) >= 95 THEN 'EXCELLENT'
            WHEN ROUND((sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2) >= 90 THEN 'GOOD'
            ELSE 'NEEDS_ATTENTION'
        END
    FROM pg_statio_user_tables 
    WHERE schemaname = 'public'
    
    UNION ALL
    
    SELECT 
        'Tables Needing Vacuum',
        count(*)::TEXT,
        CASE 
            WHEN count(*) = 0 THEN 'GOOD'
            WHEN count(*) <= 3 THEN 'MODERATE'
            ELSE 'NEEDS_ATTENTION'
        END
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    AND n_live_tup > 0 
    AND (n_dead_tup::numeric / n_live_tup) > 0.1
    
    UNION ALL
    
    SELECT 
        'Database Size',
        pg_size_pretty(pg_database_size(current_database())),
        'INFO'
)
SELECT 
    metric_name,
    metric_value,
    status,
    now() as last_updated
FROM performance_metrics;

-- =====================================================================
-- 9. AUTOMATED PERFORMANCE MONITORING FUNCTIONS
-- =====================================================================

-- Daily performance check function
CREATE OR REPLACE FUNCTION daily_performance_check()
RETURNS TABLE (
    check_type TEXT,
    status TEXT,
    details TEXT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Check for slow queries
    SELECT 
        'Slow Queries'::TEXT,
        CASE WHEN count(*) = 0 THEN 'OK' ELSE 'WARNING' END::TEXT,
        FORMAT('%s queries running longer than 5 minutes', count(*))::TEXT,
        CASE 
            WHEN count(*) > 0 THEN 'Review long-running queries and consider optimization'
            ELSE 'No action needed'
        END::TEXT
    FROM pg_stat_activity 
    WHERE (now() - query_start) > interval '5 minutes'
    AND state = 'active'
    
    UNION ALL
    
    -- Check cache hit ratio
    SELECT 
        'Cache Performance'::TEXT,
        CASE 
            WHEN hit_ratio >= 95 THEN 'GOOD'
            WHEN hit_ratio >= 90 THEN 'OK' 
            ELSE 'WARNING'
        END::TEXT,
        FORMAT('Database cache hit ratio: %s%%', hit_ratio)::TEXT,
        CASE 
            WHEN hit_ratio < 90 THEN 'Consider increasing shared_buffers'
            ELSE 'Cache performance is acceptable'
        END::TEXT
    FROM (
        SELECT ROUND(
            (sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2
        ) as hit_ratio
        FROM pg_statio_user_tables 
        WHERE schemaname = 'public'
    ) cache_stats
    
    UNION ALL
    
    -- Check for tables needing maintenance
    SELECT 
        'Table Maintenance'::TEXT,
        CASE 
            WHEN tables_need_vacuum = 0 THEN 'GOOD'
            WHEN tables_need_vacuum <= 2 THEN 'OK'
            ELSE 'WARNING'
        END::TEXT,
        FORMAT('%s tables need vacuum/analyze', tables_need_vacuum)::TEXT,
        CASE 
            WHEN tables_need_vacuum > 0 THEN 'Run VACUUM ANALYZE on affected tables'
            ELSE 'All tables are well maintained'
        END::TEXT
    FROM (
        SELECT count(*) as tables_need_vacuum
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        AND (
            (n_live_tup > 0 AND (n_dead_tup::numeric / n_live_tup) > 0.1)
            OR COALESCE(last_autovacuum, last_vacuum) < now() - interval '7 days'
            OR COALESCE(last_autoanalyze, last_analyze) < now() - interval '7 days'
        )
    ) maintenance_stats;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 10. PERFORMANCE ALERTS AND NOTIFICATIONS
-- =====================================================================

-- Critical performance alert function
CREATE OR REPLACE FUNCTION check_critical_performance_issues()
RETURNS TABLE (
    alert_level TEXT,
    issue_type TEXT,
    description TEXT,
    immediate_action TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Critical: Long-running transactions blocking others
    SELECT 
        'CRITICAL'::TEXT,
        'Blocking Transactions'::TEXT,
        FORMAT('Transaction blocking for %s minutes', 
            EXTRACT(epoch FROM (now() - query_start))/60)::TEXT,
        'Consider terminating blocking queries'::TEXT
    FROM pg_stat_activity 
    WHERE state = 'active'
    AND (now() - query_start) > interval '30 minutes'
    AND query NOT ILIKE '%VACUUM%'
    AND query NOT ILIKE '%pg_stat_%'
    
    UNION ALL
    
    -- Critical: Very low cache hit ratio
    SELECT 
        'CRITICAL'::TEXT,
        'Low Cache Hit Ratio'::TEXT,
        FORMAT('Cache hit ratio is %s%% (should be >90%%)', hit_ratio)::TEXT,
        'Increase shared_buffers or check for inefficient queries'::TEXT
    FROM (
        SELECT ROUND(
            (sum(heap_blks_hit) / GREATEST(sum(heap_blks_hit + heap_blks_read), 1)) * 100, 2
        ) as hit_ratio
        FROM pg_statio_user_tables 
        WHERE schemaname = 'public'
    ) cache_stats
    WHERE hit_ratio < 80
    
    UNION ALL
    
    -- Warning: High dead row percentage
    SELECT 
        'WARNING'::TEXT,
        'High Dead Row Percentage'::TEXT,
        FORMAT('Table %s has %s%% dead rows', 
            tablename, 
            ROUND((n_dead_tup::numeric / GREATEST(n_live_tup, 1)) * 100, 2))::TEXT,
        FORMAT('Run VACUUM ANALYZE on %s', tablename)::TEXT
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    AND n_live_tup > 1000  -- Only for tables with significant data
    AND (n_dead_tup::numeric / GREATEST(n_live_tup, 1)) > 0.25;  -- >25% dead rows
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- MONITORING SUITE COMPLETION CHECK
-- =====================================================================

-- Verify monitoring setup
CREATE OR REPLACE FUNCTION verify_monitoring_setup()
RETURNS TEXT AS $$
DECLARE
    view_count INTEGER;
    function_count INTEGER;
    extension_count INTEGER;
BEGIN
    -- Count monitoring views
    SELECT COUNT(*) INTO view_count
    FROM pg_views 
    WHERE schemaname = 'public' 
    AND viewname LIKE 'v_%';
    
    -- Count monitoring functions
    SELECT COUNT(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' 
    AND p.proname LIKE '%performance%' OR p.proname LIKE '%monitor%';
    
    -- Check for useful extensions
    SELECT COUNT(*) INTO extension_count
    FROM pg_extension 
    WHERE extname IN ('pg_stat_statements', 'pg_buffercache');
    
    RETURN FORMAT('PERFORMANCE MONITORING SETUP COMPLETE!
Monitoring Views: %s
Monitoring Functions: %s  
Performance Extensions: %s/2

RECOMMENDED USAGE:
- SELECT * FROM v_performance_dashboard;
- SELECT * FROM daily_performance_check();  
- SELECT * FROM check_critical_performance_issues();
- SELECT * FROM get_slow_query_stats();
- SELECT * FROM v_index_usage_analysis;',
        view_count, function_count, extension_count);
END;
$$ LANGUAGE plpgsql;

-- Execute verification
SELECT verify_monitoring_setup();