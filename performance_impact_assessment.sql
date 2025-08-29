-- =============================================================================
-- PERFORMANCE IMPACT ASSESSMENT QUERIES
-- Measure and track database performance before/after schema changes
-- =============================================================================

-- =============================================================================
-- 1. BASELINE PERFORMANCE MEASUREMENT
-- =============================================================================

-- Create performance baseline measurement function
CREATE OR REPLACE FUNCTION measure_performance_baseline()
RETURNS TABLE (
    metric_name TEXT,
    baseline_value NUMERIC,
    measurement_unit TEXT,
    measurement_timestamp TIMESTAMP,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Query execution time baseline
    WITH timing_test AS (
        SELECT 
            'basic_property_count' as test_name,
            clock_timestamp() as start_time
    ),
    query_execution AS (
        SELECT COUNT(*) as result_count
        FROM properties_new 
        WHERE is_active = true
    ),
    timing_end AS (
        SELECT clock_timestamp() as end_time
    )
    SELECT 
        'Basic Property Count Query'::TEXT,
        EXTRACT(milliseconds FROM (te.end_time - tt.start_time))::NUMERIC,
        'milliseconds'::TEXT,
        now()::TIMESTAMP,
        FORMAT('Counted %s active properties', qe.result_count)::TEXT
    FROM timing_test tt, query_execution qe, timing_end te
    
    UNION ALL
    
    -- Index scan ratio
    SELECT 
        'Index Usage Ratio'::TEXT,
        ROUND(
            (SUM(idx_scan)::NUMERIC / GREATEST(SUM(seq_scan + idx_scan), 1)) * 100, 2
        ),
        'percentage'::TEXT,
        now()::TIMESTAMP,
        FORMAT('Based on %s table scans', SUM(seq_scan + idx_scan))::TEXT
    FROM pg_stat_user_tables 
    WHERE schemaname = 'public'
    
    UNION ALL
    
    -- Buffer cache hit ratio
    SELECT 
        'Buffer Cache Hit Ratio'::TEXT,
        ROUND(
            (SUM(heap_blks_hit)::NUMERIC / GREATEST(SUM(heap_blks_hit + heap_blks_read), 1)) * 100, 2
        ),
        'percentage'::TEXT,
        now()::TIMESTAMP,
        'Database buffer cache efficiency'::TEXT
    FROM pg_statio_user_tables 
    WHERE schemaname = 'public'
    
    UNION ALL
    
    -- Database size
    SELECT 
        'Total Database Size'::TEXT,
        ROUND(pg_database_size(current_database())::NUMERIC / 1024 / 1024, 2),
        'MB'::TEXT,
        now()::TIMESTAMP,
        'Current database size including indexes'::TEXT
    
    UNION ALL
    
    -- Largest table size
    SELECT 
        'Largest Table Size'::TEXT,
        ROUND(MAX(pg_total_relation_size(schemaname||'.'||tablename))::NUMERIC / 1024 / 1024, 2),
        'MB'::TEXT,
        now()::TIMESTAMP,
        'Size of the largest table with indexes'::TEXT
    FROM pg_tables 
    WHERE schemaname = 'public';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 2. SCHEMA CHANGE IMPACT MEASUREMENT
-- =============================================================================

-- Measure impact of new schema structures
CREATE OR REPLACE FUNCTION assess_schema_change_impact()
RETURNS TABLE (
    impact_category TEXT,
    before_value NUMERIC,
    after_value NUMERIC,
    change_percentage NUMERIC,
    impact_severity TEXT,
    recommendation TEXT
) AS $$
DECLARE
    old_table_count INTEGER;
    new_table_count INTEGER;
    old_index_count INTEGER;
    new_index_count INTEGER;
BEGIN
    -- Count legacy vs new tables
    SELECT COUNT(*) INTO old_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' 
    AND table_name IN ('properties', 'areas', 'price_history', 'deletion_history', 'daily_stats');
    
    SELECT COUNT(*) INTO new_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' 
    AND (table_name LIKE '%_new' OR table_name LIKE 'property_%' OR table_name IN ('real_estate_types', 'trade_types', 'regions'));
    
    -- Count indexes
    SELECT COUNT(*) INTO old_index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname NOT LIKE 'idx_%'
    AND indexname NOT LIKE '%_pkey'
    AND indexname NOT LIKE '%_key';
    
    SELECT COUNT(*) INTO new_index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname LIKE 'idx_%';
    
    RETURN QUERY
    
    -- Table structure impact
    SELECT 
        'Table Structure'::TEXT,
        old_table_count::NUMERIC,
        new_table_count::NUMERIC,
        CASE 
            WHEN old_table_count > 0 THEN 
                ROUND(((new_table_count - old_table_count)::NUMERIC / old_table_count) * 100, 2)
            ELSE 0
        END,
        CASE 
            WHEN new_table_count > old_table_count * 2 THEN 'HIGH'
            WHEN new_table_count > old_table_count * 1.5 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT,
        FORMAT('Schema normalized: %s legacy → %s normalized tables', old_table_count, new_table_count)::TEXT
    
    UNION ALL
    
    -- Index impact
    SELECT 
        'Index Structure'::TEXT,
        old_index_count::NUMERIC,
        new_index_count::NUMERIC,
        CASE 
            WHEN old_index_count > 0 THEN 
                ROUND(((new_index_count - old_index_count)::NUMERIC / old_index_count) * 100, 2)
            ELSE 0
        END,
        CASE 
            WHEN new_index_count > old_index_count * 3 THEN 'HIGH'
            WHEN new_index_count > old_index_count * 2 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT,
        FORMAT('Performance indexes added: %s → %s total indexes', old_index_count, new_index_count)::TEXT
    
    UNION ALL
    
    -- Storage impact
    WITH storage_comparison AS (
        SELECT 
            SUM(CASE WHEN table_name IN ('properties', 'areas', 'price_history', 'deletion_history', 'daily_stats')
                THEN pg_total_relation_size(schemaname||'.'||table_name) ELSE 0 END) as legacy_size,
            SUM(CASE WHEN table_name LIKE '%property_%' OR table_name LIKE '%_new' OR table_name IN ('real_estate_types', 'trade_types', 'regions')
                THEN pg_total_relation_size(schemaname||'.'||table_name) ELSE 0 END) as new_size
        FROM pg_tables 
        WHERE schemaname = 'public'
    )
    SELECT 
        'Storage Usage'::TEXT,
        ROUND(sc.legacy_size::NUMERIC / 1024 / 1024, 2),  -- Legacy size in MB
        ROUND(sc.new_size::NUMERIC / 1024 / 1024, 2),     -- New size in MB
        CASE 
            WHEN sc.legacy_size > 0 THEN 
                ROUND(((sc.new_size - sc.legacy_size)::NUMERIC / sc.legacy_size) * 100, 2)
            ELSE 0
        END,
        CASE 
            WHEN sc.new_size > sc.legacy_size * 1.5 THEN 'HIGH'
            WHEN sc.new_size > sc.legacy_size * 1.2 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT,
        'Monitor disk space usage during migration'::TEXT
    FROM storage_comparison sc;
    
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 3. QUERY PERFORMANCE COMPARISON
-- =============================================================================

-- Compare query performance before/after schema changes
CREATE OR REPLACE FUNCTION compare_query_performance()
RETURNS TABLE (
    query_type TEXT,
    legacy_time_ms NUMERIC,
    normalized_time_ms NUMERIC,
    performance_improvement NUMERIC,
    improvement_grade TEXT,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Test 1: Basic property search comparison
    WITH legacy_timing AS (
        SELECT 
            clock_timestamp() as start_time,
            (SELECT COUNT(*) FROM properties WHERE is_active = true LIMIT 100) as result_count,
            clock_timestamp() as end_time
    ),
    legacy_duration AS (
        SELECT EXTRACT(milliseconds FROM (end_time - start_time)) as duration_ms
        FROM legacy_timing
    ),
    normalized_timing AS (
        SELECT 
            clock_timestamp() as start_time,
            (SELECT COUNT(*) FROM properties_new WHERE is_active = true LIMIT 100) as result_count,
            clock_timestamp() as end_time
    ),
    normalized_duration AS (
        SELECT EXTRACT(milliseconds FROM (end_time - start_time)) as duration_ms
        FROM normalized_timing
    )
    SELECT 
        'Basic Property Search'::TEXT,
        ld.duration_ms::NUMERIC,
        nd.duration_ms::NUMERIC,
        CASE 
            WHEN ld.duration_ms > 0 THEN 
                ROUND(((ld.duration_ms - nd.duration_ms) / ld.duration_ms) * 100, 2)
            ELSE 0
        END::NUMERIC,
        CASE 
            WHEN nd.duration_ms < ld.duration_ms * 0.5 THEN 'EXCELLENT'
            WHEN nd.duration_ms < ld.duration_ms * 0.8 THEN 'GOOD'
            WHEN nd.duration_ms < ld.duration_ms THEN 'IMPROVED'
            ELSE 'NO_IMPROVEMENT'
        END::TEXT,
        FORMAT('Legacy: %sms → Normalized: %sms', ld.duration_ms, nd.duration_ms)::TEXT
    FROM legacy_duration ld, normalized_duration nd
    
    UNION ALL
    
    -- Test 2: Complex join query comparison
    WITH legacy_join_timing AS (
        SELECT 
            clock_timestamp() as start_time,
            (SELECT COUNT(*) 
             FROM properties p 
             LEFT JOIN areas a ON p.cortar_no = a.cortar_no 
             WHERE p.is_active = true 
             LIMIT 50) as result_count,
            clock_timestamp() as end_time
    ),
    legacy_join_duration AS (
        SELECT COALESCE(EXTRACT(milliseconds FROM (end_time - start_time)), 9999) as duration_ms
        FROM legacy_join_timing
    ),
    normalized_join_timing AS (
        SELECT 
            clock_timestamp() as start_time,
            (SELECT COUNT(*) 
             FROM properties_new p 
             JOIN regions r ON p.region_id = r.id 
             JOIN real_estate_types ret ON p.real_estate_type_id = ret.id
             WHERE p.is_active = true 
             LIMIT 50) as result_count,
            clock_timestamp() as end_time
    ),
    normalized_join_duration AS (
        SELECT EXTRACT(milliseconds FROM (end_time - start_time)) as duration_ms
        FROM normalized_join_timing
    )
    SELECT 
        'Complex Join Query'::TEXT,
        ljd.duration_ms::NUMERIC,
        njd.duration_ms::NUMERIC,
        CASE 
            WHEN ljd.duration_ms > 0 AND ljd.duration_ms < 9999 THEN 
                ROUND(((ljd.duration_ms - njd.duration_ms) / ljd.duration_ms) * 100, 2)
            ELSE 0
        END::NUMERIC,
        CASE 
            WHEN njd.duration_ms < ljd.duration_ms * 0.3 THEN 'EXCELLENT'
            WHEN njd.duration_ms < ljd.duration_ms * 0.6 THEN 'GOOD'
            WHEN njd.duration_ms < ljd.duration_ms THEN 'IMPROVED'
            WHEN ljd.duration_ms >= 9999 THEN 'LEGACY_FAILED'
            ELSE 'NO_IMPROVEMENT'
        END::TEXT,
        FORMAT('Normalized schema shows improved join performance')::TEXT
    FROM legacy_join_duration ljd, normalized_join_duration njd;
    
EXCEPTION
    WHEN others THEN
        -- Return error information if comparison fails
        RETURN QUERY
        SELECT 
            'Comparison Error'::TEXT,
            0::NUMERIC,
            0::NUMERIC,
            0::NUMERIC,
            'ERROR'::TEXT,
            FORMAT('Performance comparison failed: %s', SQLERRM)::TEXT;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 4. INDEX EFFECTIVENESS ANALYSIS
-- =============================================================================

-- Analyze the effectiveness of new indexes
CREATE OR REPLACE FUNCTION analyze_index_effectiveness()
RETURNS TABLE (
    index_name TEXT,
    table_name TEXT,
    index_scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    selectivity_ratio NUMERIC,
    effectiveness_grade TEXT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    WITH index_stats AS (
        SELECT 
            indexrelname,
            schemaname,
            tablename,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            CASE 
                WHEN idx_tup_read > 0 THEN 
                    ROUND((idx_tup_fetch::NUMERIC / idx_tup_read) * 100, 2)
                ELSE 0
            END as selectivity_pct
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        AND indexrelname LIKE 'idx_%'
    )
    SELECT 
        ist.indexrelname::TEXT,
        ist.tablename::TEXT,
        ist.idx_scan,
        ist.idx_tup_read,
        ist.idx_tup_fetch,
        ist.selectivity_pct,
        CASE 
            WHEN ist.idx_scan = 0 THEN 'UNUSED'
            WHEN ist.idx_scan < 10 THEN 'LOW_USAGE'
            WHEN ist.selectivity_pct < 10 THEN 'INEFFICIENT'
            WHEN ist.selectivity_pct >= 80 THEN 'EXCELLENT'
            WHEN ist.selectivity_pct >= 50 THEN 'GOOD'
            ELSE 'MODERATE'
        END::TEXT,
        CASE 
            WHEN ist.idx_scan = 0 THEN 'Consider removing unused index'
            WHEN ist.idx_scan < 10 THEN 'Monitor usage, may need different columns'
            WHEN ist.selectivity_pct < 10 THEN 'Low selectivity - review index design'
            WHEN ist.selectivity_pct >= 80 THEN 'Highly effective index'
            ELSE 'Index performing adequately'
        END::TEXT
    FROM index_stats ist
    ORDER BY ist.idx_scan DESC, ist.selectivity_pct DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 5. REAL-TIME PERFORMANCE MONITORING
-- =============================================================================

-- Real-time performance monitoring view
CREATE OR REPLACE VIEW v_performance_monitoring AS
WITH current_metrics AS (
    -- Current query performance
    SELECT 
        COUNT(*) as active_queries,
        AVG(EXTRACT(epoch FROM (now() - query_start))) as avg_query_duration,
        MAX(EXTRACT(epoch FROM (now() - query_start))) as max_query_duration
    FROM pg_stat_activity 
    WHERE state = 'active' 
    AND query_start IS NOT NULL
    AND pid != pg_backend_pid()
),
cache_metrics AS (
    -- Cache hit ratios
    SELECT 
        ROUND(
            (SUM(heap_blks_hit)::NUMERIC / GREATEST(SUM(heap_blks_hit + heap_blks_read), 1)) * 100, 2
        ) as buffer_cache_hit_ratio,
        ROUND(
            (SUM(idx_blks_hit)::NUMERIC / GREATEST(SUM(idx_blks_hit + idx_blks_read), 1)) * 100, 2
        ) as index_cache_hit_ratio
    FROM pg_statio_user_tables
    WHERE schemaname = 'public'
),
table_metrics AS (
    -- Table scan ratios
    SELECT 
        COUNT(*) as total_tables,
        SUM(seq_scan) as total_seq_scans,
        SUM(idx_scan) as total_idx_scans,
        ROUND(
            (SUM(idx_scan)::NUMERIC / GREATEST(SUM(seq_scan + idx_scan), 1)) * 100, 2
        ) as index_usage_ratio
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
),
size_metrics AS (
    -- Database size metrics
    SELECT 
        ROUND(pg_database_size(current_database())::NUMERIC / 1024 / 1024, 2) as db_size_mb,
        COUNT(*) as table_count
    FROM pg_tables
    WHERE schemaname = 'public'
)
SELECT 
    'Active Queries' as metric_type,
    cm.active_queries::TEXT as current_value,
    CASE 
        WHEN cm.active_queries < 10 THEN 'NORMAL'
        WHEN cm.active_queries < 50 THEN 'MODERATE'
        ELSE 'HIGH'
    END as status,
    FORMAT('Avg duration: %ss, Max: %ss', 
        ROUND(cm.avg_query_duration, 2), 
        ROUND(cm.max_query_duration, 2)) as details
FROM current_metrics cm

UNION ALL

SELECT 
    'Buffer Cache Hit Ratio',
    cache.buffer_cache_hit_ratio::TEXT || '%',
    CASE 
        WHEN cache.buffer_cache_hit_ratio >= 95 THEN 'EXCELLENT'
        WHEN cache.buffer_cache_hit_ratio >= 90 THEN 'GOOD'
        WHEN cache.buffer_cache_hit_ratio >= 80 THEN 'FAIR'
        ELSE 'POOR'
    END,
    FORMAT('Index cache: %s%%', cache.index_cache_hit_ratio)
FROM cache_metrics cache

UNION ALL

SELECT 
    'Index Usage Ratio',
    tm.index_usage_ratio::TEXT || '%',
    CASE 
        WHEN tm.index_usage_ratio >= 80 THEN 'EXCELLENT'
        WHEN tm.index_usage_ratio >= 60 THEN 'GOOD'
        WHEN tm.index_usage_ratio >= 40 THEN 'FAIR'
        ELSE 'POOR'
    END,
    FORMAT('Total scans: %s seq, %s idx', tm.total_seq_scans, tm.total_idx_scans)
FROM table_metrics tm

UNION ALL

SELECT 
    'Database Size',
    sm.db_size_mb::TEXT || ' MB',
    CASE 
        WHEN sm.db_size_mb < 1000 THEN 'NORMAL'
        WHEN sm.db_size_mb < 5000 THEN 'MODERATE'
        ELSE 'LARGE'
    END,
    FORMAT('%s tables total', sm.table_count)
FROM size_metrics sm;

-- =============================================================================
-- 6. PERFORMANCE TREND TRACKING
-- =============================================================================

-- Track performance trends over time
CREATE TABLE IF NOT EXISTS performance_trend_log (
    id BIGSERIAL PRIMARY KEY,
    measurement_timestamp TIMESTAMP DEFAULT now(),
    metric_name TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit TEXT,
    notes TEXT
);

-- Function to log current performance metrics
CREATE OR REPLACE FUNCTION log_performance_metrics()
RETURNS INTEGER AS $$
DECLARE
    inserted_count INTEGER := 0;
BEGIN
    -- Insert current performance metrics
    INSERT INTO performance_trend_log (metric_name, metric_value, metric_unit, notes)
    SELECT 
        metric_name,
        baseline_value,
        measurement_unit,
        notes
    FROM measure_performance_baseline();
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 7. PERFORMANCE ALERT SYSTEM
-- =============================================================================

-- Check for performance issues and generate alerts
CREATE OR REPLACE FUNCTION check_performance_alerts()
RETURNS TABLE (
    alert_level TEXT,
    alert_type TEXT,
    current_value TEXT,
    threshold_value TEXT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Check for slow queries
    SELECT 
        'CRITICAL'::TEXT,
        'Long Running Queries'::TEXT,
        FORMAT('%s queries running >5min', COUNT(*))::TEXT,
        '0 queries'::TEXT,
        'Review and optimize long-running queries'::TEXT
    FROM pg_stat_activity 
    WHERE state = 'active'
    AND (now() - query_start) > interval '5 minutes'
    AND query NOT ILIKE '%vacuum%'
    HAVING COUNT(*) > 0
    
    UNION ALL
    
    -- Check cache hit ratio
    WITH cache_check AS (
        SELECT ROUND(
            (SUM(heap_blks_hit)::NUMERIC / GREATEST(SUM(heap_blks_hit + heap_blks_read), 1)) * 100, 2
        ) as hit_ratio
        FROM pg_statio_user_tables 
        WHERE schemaname = 'public'
    )
    SELECT 
        CASE 
            WHEN cc.hit_ratio < 80 THEN 'CRITICAL'
            WHEN cc.hit_ratio < 90 THEN 'WARNING'
            ELSE 'INFO'
        END::TEXT,
        'Buffer Cache Performance'::TEXT,
        FORMAT('%s%% hit ratio', cc.hit_ratio)::TEXT,
        '>95% recommended'::TEXT,
        CASE 
            WHEN cc.hit_ratio < 80 THEN 'Increase shared_buffers immediately'
            WHEN cc.hit_ratio < 90 THEN 'Consider increasing shared_buffers'
            ELSE 'Cache performance acceptable'
        END::TEXT
    FROM cache_check cc
    WHERE cc.hit_ratio < 95  -- Only show if below recommended threshold
    
    UNION ALL
    
    -- Check for tables needing maintenance
    SELECT 
        'WARNING'::TEXT,
        'Table Maintenance Needed'::TEXT,
        FORMAT('%s tables need vacuum', COUNT(*))::TEXT,
        '0 tables'::TEXT,
        'Run VACUUM ANALYZE on tables with high dead row ratio'::TEXT
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    AND n_live_tup > 1000
    AND (n_dead_tup::NUMERIC / GREATEST(n_live_tup, 1)) > 0.1
    HAVING COUNT(*) > 0
    
    UNION ALL
    
    -- Check database size growth
    WITH size_check AS (
        SELECT ROUND(pg_database_size(current_database())::NUMERIC / 1024 / 1024 / 1024, 2) as db_size_gb
    )
    SELECT 
        CASE 
            WHEN sc.db_size_gb > 10 THEN 'WARNING'
            ELSE 'INFO'
        END::TEXT,
        'Database Size'::TEXT,
        FORMAT('%s GB', sc.db_size_gb)::TEXT,
        '<10 GB optimal'::TEXT,
        CASE 
            WHEN sc.db_size_gb > 10 THEN 'Monitor disk space and consider archiving old data'
            ELSE 'Database size within normal limits'
        END::TEXT
    FROM size_check sc
    WHERE sc.db_size_gb > 5;  -- Only alert if > 5GB
    
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 8. COMPREHENSIVE PERFORMANCE DASHBOARD
-- =============================================================================

-- Master performance assessment function
CREATE OR REPLACE FUNCTION comprehensive_performance_assessment()
RETURNS TABLE (
    assessment_category TEXT,
    status TEXT,
    current_metrics JSONB,
    recommendations TEXT[]
) AS $$
DECLARE
    baseline_metrics JSONB;
    impact_analysis JSONB;
    performance_comparison JSONB;
    index_analysis JSONB;
    alerts JSONB;
BEGIN
    -- Collect all performance data
    SELECT json_agg(row_to_json(t))::JSONB INTO baseline_metrics
    FROM measure_performance_baseline() t;
    
    SELECT json_agg(row_to_json(t))::JSONB INTO impact_analysis
    FROM assess_schema_change_impact() t;
    
    SELECT json_agg(row_to_json(t))::JSONB INTO performance_comparison
    FROM compare_query_performance() t;
    
    SELECT json_agg(row_to_json(t))::JSONB INTO index_analysis
    FROM analyze_index_effectiveness() t;
    
    SELECT json_agg(row_to_json(t))::JSONB INTO alerts
    FROM check_performance_alerts() t;
    
    RETURN QUERY
    
    SELECT 
        'Baseline Metrics'::TEXT,
        'MEASURED'::TEXT,
        baseline_metrics,
        ARRAY['Performance baseline established', 'Use for ongoing monitoring']::TEXT[]
    
    UNION ALL
    
    SELECT 
        'Schema Change Impact'::TEXT,
        CASE 
            WHEN impact_analysis->0->>'impact_severity' = 'HIGH' THEN 'HIGH_IMPACT'
            WHEN impact_analysis->0->>'impact_severity' = 'MEDIUM' THEN 'MEDIUM_IMPACT'
            ELSE 'LOW_IMPACT'
        END::TEXT,
        impact_analysis,
        ARRAY['Monitor resource usage during migration', 'Track storage growth']::TEXT[]
    
    UNION ALL
    
    SELECT 
        'Query Performance'::TEXT,
        CASE 
            WHEN performance_comparison->0->>'improvement_grade' = 'EXCELLENT' THEN 'EXCELLENT'
            WHEN performance_comparison->0->>'improvement_grade' = 'GOOD' THEN 'GOOD'
            ELSE 'NEEDS_MONITORING'
        END::TEXT,
        performance_comparison,
        ARRAY['Continue monitoring query performance', 'Optimize slow queries']::TEXT[]
    
    UNION ALL
    
    SELECT 
        'Index Effectiveness'::TEXT,
        CASE 
            WHEN (index_analysis->0->>'effectiveness_grade') = 'EXCELLENT' THEN 'EXCELLENT'
            ELSE 'OPTIMIZING'
        END::TEXT,
        index_analysis,
        ARRAY['Monitor index usage patterns', 'Remove unused indexes']::TEXT[]
    
    UNION ALL
    
    SELECT 
        'Performance Alerts'::TEXT,
        CASE 
            WHEN alerts IS NULL OR jsonb_array_length(alerts) = 0 THEN 'ALL_CLEAR'
            WHEN alerts->0->>'alert_level' = 'CRITICAL' THEN 'CRITICAL_ISSUES'
            ELSE 'MINOR_ISSUES'
        END::TEXT,
        COALESCE(alerts, '[]'::JSONB),
        ARRAY['Address critical performance issues', 'Set up automated monitoring']::TEXT[];
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 9. AUTOMATED PERFORMANCE TESTING
-- =============================================================================

-- Automated daily performance check
CREATE OR REPLACE FUNCTION daily_performance_check()
RETURNS TABLE (
    check_date DATE,
    overall_status TEXT,
    critical_issues INTEGER,
    performance_grade TEXT,
    summary_report TEXT
) AS $$
DECLARE
    critical_count INTEGER := 0;
    warning_count INTEGER := 0;
    total_checks INTEGER := 0;
    grade TEXT;
    report TEXT;
BEGIN
    -- Count alerts by severity
    SELECT 
        COUNT(CASE WHEN alert_level = 'CRITICAL' THEN 1 END),
        COUNT(CASE WHEN alert_level = 'WARNING' THEN 1 END),
        COUNT(*)
    INTO critical_count, warning_count, total_checks
    FROM check_performance_alerts();
    
    -- Determine grade
    IF critical_count > 0 THEN
        grade := 'CRITICAL';
    ELSIF warning_count > 2 THEN
        grade := 'POOR';
    ELSIF warning_count > 0 THEN
        grade := 'FAIR';
    ELSE
        grade := 'EXCELLENT';
    END IF;
    
    -- Generate summary report
    report := FORMAT('Performance check completed: %s critical, %s warnings from %s total checks. 
Cache hit ratio and index usage monitored. %s',
        critical_count, warning_count, total_checks,
        CASE WHEN critical_count = 0 THEN 'System performing well.' 
             ELSE 'Immediate attention required.' END
    );
    
    -- Log performance metrics
    PERFORM log_performance_metrics();
    
    RETURN QUERY
    SELECT 
        CURRENT_DATE,
        CASE 
            WHEN critical_count = 0 AND warning_count = 0 THEN 'HEALTHY'
            WHEN critical_count = 0 THEN 'STABLE'
            ELSE 'NEEDS_ATTENTION'
        END::TEXT,
        critical_count,
        grade,
        report;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 10. INSTALLATION VERIFICATION
-- =============================================================================

-- Verify performance monitoring installation
CREATE OR REPLACE FUNCTION verify_performance_monitoring_installation()
RETURNS TEXT AS $$
DECLARE
    function_count INTEGER;
    view_count INTEGER;
    table_count INTEGER;
BEGIN
    -- Count monitoring functions
    SELECT COUNT(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' 
    AND p.proname IN (
        'measure_performance_baseline',
        'assess_schema_change_impact', 
        'compare_query_performance',
        'analyze_index_effectiveness',
        'check_performance_alerts',
        'comprehensive_performance_assessment',
        'daily_performance_check'
    );
    
    -- Count monitoring views
    SELECT COUNT(*) INTO view_count
    FROM pg_views 
    WHERE schemaname = 'public'
    AND viewname = 'v_performance_monitoring';
    
    -- Count monitoring tables
    SELECT COUNT(*) INTO table_count
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename = 'performance_trend_log';
    
    RETURN FORMAT('
🎯 PERFORMANCE IMPACT ASSESSMENT SUITE INSTALLED!

📊 Components Installed:
✅ Monitoring Functions: %s/7
✅ Monitoring Views: %s/1  
✅ Trend Tracking Tables: %s/1

🚀 QUICK START COMMANDS:
-- Run comprehensive assessment:
SELECT * FROM comprehensive_performance_assessment();

-- Check daily performance:
SELECT * FROM daily_performance_check();

-- Monitor real-time metrics:
SELECT * FROM v_performance_monitoring;

-- Check for alerts:
SELECT * FROM check_performance_alerts();

-- Measure baseline performance:
SELECT * FROM measure_performance_baseline();

-- Compare query performance:
SELECT * FROM compare_query_performance();

-- Analyze index effectiveness:
SELECT * FROM analyze_index_effectiveness();

📈 Performance monitoring is now active and ready for schema deployment tracking!
', function_count, view_count, table_count);
END;
$$ LANGUAGE plpgsql;

-- Show installation summary
SELECT verify_performance_monitoring_installation();