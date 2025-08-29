-- =============================================================================
-- SCHEMA DEPLOYMENT VALIDATION SUITE
-- Comprehensive validation queries for database schema fixes
-- =============================================================================

-- =============================================================================
-- 1. SCHEMA STRUCTURE VALIDATION
-- =============================================================================

-- Verify all required tables exist with correct column types
CREATE OR REPLACE FUNCTION validate_schema_deployment()
RETURNS TABLE (
    validation_type TEXT,
    status TEXT,
    details TEXT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Check core normalized tables
    WITH required_tables AS (
        SELECT unnest(ARRAY[
            'real_estate_types', 'trade_types', 'regions', 'facility_types',
            'properties_new', 'property_prices', 'property_locations', 
            'property_physical', 'property_realtors', 'property_images',
            'property_facilities', 'realtors', 'property_tax_info', 
            'property_price_comparison', 'price_history_new', 
            'deletion_history_new', 'daily_stats_new'
        ]) as table_name
    ),
    existing_tables AS (
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    )
    SELECT 
        'Table Existence'::TEXT,
        CASE 
            WHEN COUNT(rt.table_name) = COUNT(et.table_name) THEN 'PASS'
            ELSE 'FAIL'
        END::TEXT,
        FORMAT('%s/%s required tables exist', 
            COUNT(et.table_name), COUNT(rt.table_name))::TEXT,
        CASE 
            WHEN COUNT(rt.table_name) > COUNT(et.table_name) THEN 
                'Missing tables: Run schema creation script'
            ELSE 'All tables present'
        END::TEXT
    FROM required_tables rt
    LEFT JOIN existing_tables et ON rt.table_name = et.table_name
    
    UNION ALL
    
    -- Check critical columns exist
    SELECT 
        'Critical Columns'::TEXT,
        CASE 
            WHEN missing_cols.count = 0 THEN 'PASS'
            ELSE 'FAIL'
        END::TEXT,
        FORMAT('%s critical columns missing', missing_cols.count)::TEXT,
        CASE 
            WHEN missing_cols.count > 0 THEN 
                'Run comprehensive schema update script'
            ELSE 'All critical columns present'
        END::TEXT
    FROM (
        SELECT COUNT(*) as count FROM (
            SELECT 'property_tax_info'::TEXT, 'total_tax'::TEXT
            UNION SELECT 'property_tax_info', 'brokerage_fee'
            UNION SELECT 'property_price_comparison', 'cpid'
            UNION SELECT 'property_locations', 'subway_stations'
            UNION SELECT 'property_physical', 'veranda_count'
            UNION SELECT 'properties_new', 'building_use'
        ) required_cols(table_name, column_name)
        WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = required_cols.table_name 
            AND column_name = required_cols.column_name
        )
    ) missing_cols;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 2. INDEX VALIDATION
-- =============================================================================

-- Verify all performance indexes are properly created
CREATE OR REPLACE FUNCTION validate_index_deployment()
RETURNS TABLE (
    index_category TEXT,
    created_count INTEGER,
    expected_count INTEGER,
    status TEXT,
    missing_indexes TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    
    WITH expected_indexes AS (
        SELECT unnest(ARRAY[
            -- Primary performance indexes
            'idx_properties_new_article_no',
            'idx_properties_new_active', 
            'idx_properties_new_region',
            'idx_properties_new_type',
            'idx_properties_new_search',
            
            -- Price indexes
            'idx_property_prices_property',
            'idx_property_prices_amount',
            'idx_property_prices_current',
            
            -- Location indexes
            'idx_property_locations_coords',
            'idx_property_locations_region',
            'idx_property_locations_cortar_no',
            
            -- Physical info indexes
            'idx_property_physical_area',
            'idx_property_physical_floor',
            
            -- New table indexes
            'idx_property_tax_info_property',
            'idx_property_price_comparison_property'
        ]) as index_name
    ),
    existing_indexes AS (
        SELECT indexname as index_name
        FROM pg_indexes 
        WHERE schemaname = 'public'
        AND indexname LIKE 'idx_%'
    ),
    missing_indexes AS (
        SELECT ei.index_name
        FROM expected_indexes ei
        LEFT JOIN existing_indexes ex ON ei.index_name = ex.index_name
        WHERE ex.index_name IS NULL
    )
    SELECT 
        'Performance Indexes'::TEXT,
        (SELECT COUNT(*)::INTEGER FROM existing_indexes),
        (SELECT COUNT(*)::INTEGER FROM expected_indexes),
        CASE 
            WHEN (SELECT COUNT(*) FROM missing_indexes) = 0 THEN 'PASS'
            ELSE 'PARTIAL'
        END::TEXT,
        COALESCE(ARRAY_AGG(mi.index_name), ARRAY[]::TEXT[])
    FROM missing_indexes mi;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 3. FOREIGN KEY RELATIONSHIP VALIDATION
-- =============================================================================

-- Test foreign key relationships work correctly
CREATE OR REPLACE FUNCTION validate_foreign_key_relationships()
RETURNS TABLE (
    relationship_type TEXT,
    status TEXT,
    test_result TEXT,
    recommendation TEXT
) AS $$
DECLARE
    test_real_estate_type_id INTEGER;
    test_trade_type_id INTEGER; 
    test_region_id INTEGER;
    test_property_id BIGINT;
BEGIN
    -- Get sample reference IDs
    SELECT id INTO test_real_estate_type_id FROM real_estate_types LIMIT 1;
    SELECT id INTO test_trade_type_id FROM trade_types LIMIT 1;
    SELECT id INTO test_region_id FROM regions LIMIT 1;
    
    IF test_real_estate_type_id IS NULL OR test_trade_type_id IS NULL OR test_region_id IS NULL THEN
        RETURN QUERY
        SELECT 
            'Reference Data'::TEXT,
            'FAIL'::TEXT,
            'Missing reference data in lookup tables'::TEXT,
            'Populate reference tables: real_estate_types, trade_types, regions'::TEXT;
        RETURN;
    END IF;
    
    BEGIN
        -- Test property creation with foreign keys
        INSERT INTO properties_new (
            article_no, article_name, real_estate_type_id, 
            trade_type_id, region_id, collected_date, is_active
        ) VALUES (
            'FK_TEST_' || extract(epoch from now())::TEXT,
            'Foreign Key Test Property',
            test_real_estate_type_id,
            test_trade_type_id, 
            test_region_id,
            CURRENT_DATE,
            true
        ) RETURNING id INTO test_property_id;
        
        -- Test child table relationships
        INSERT INTO property_prices (property_id, price_type, amount, valid_from)
        VALUES (test_property_id, 'sale', 100000, CURRENT_DATE);
        
        INSERT INTO property_locations (property_id, latitude, longitude)
        VALUES (test_property_id, 37.5665, 126.9780);
        
        INSERT INTO property_physical (property_id, area_exclusive, area_supply)
        VALUES (test_property_id, 84.5, 120.0);
        
        -- Clean up test data
        DELETE FROM properties_new WHERE id = test_property_id;
        
        RETURN QUERY
        SELECT 
            'Foreign Key Relationships'::TEXT,
            'PASS'::TEXT,
            'All FK relationships working correctly'::TEXT,
            'No action needed'::TEXT;
            
    EXCEPTION WHEN others THEN
        RETURN QUERY
        SELECT 
            'Foreign Key Relationships'::TEXT,
            'FAIL'::TEXT,
            FORMAT('FK test failed: %s', SQLERRM)::TEXT,
            'Check foreign key constraints and reference data'::TEXT;
    END;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 4. DATA TYPE AND CONSTRAINT VALIDATION
-- =============================================================================

-- Validate constraints and data types
CREATE OR REPLACE FUNCTION validate_data_constraints()
RETURNS TABLE (
    constraint_type TEXT,
    table_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Check NOT NULL constraints on critical fields
    WITH critical_not_nulls AS (
        SELECT 
            table_name, column_name, 
            CASE WHEN is_nullable = 'NO' THEN 'PASS' ELSE 'FAIL' END as status
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND (table_name, column_name) IN (
            ('properties_new', 'article_no'),
            ('properties_new', 'collected_date'),
            ('property_prices', 'amount'),
            ('property_prices', 'price_type'),
            ('property_locations', 'property_id'),
            ('property_physical', 'property_id')
        )
    )
    SELECT 
        'NOT NULL Constraints'::TEXT,
        cnn.table_name::TEXT,
        cnn.status::TEXT,
        FORMAT('Column %s null constraint: %s', 
            cnn.column_name, cnn.status)::TEXT
    FROM critical_not_nulls cnn
    
    UNION ALL
    
    -- Check CHECK constraints
    SELECT 
        'CHECK Constraints'::TEXT,
        cc.table_name::TEXT,
        'PASS'::TEXT,
        FORMAT('Constraint %s exists', cc.constraint_name)::TEXT
    FROM information_schema.check_constraints cc
    JOIN information_schema.table_constraints tc ON cc.constraint_name = tc.constraint_name
    WHERE tc.table_schema = 'public'
    AND cc.constraint_name IN (
        'chk_positive_amount',
        'chk_floor_logic', 
        'chk_positive_area',
        'chk_tax_amounts'
    );
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 5. API SECTION DATA INSERTION VALIDATION
-- =============================================================================

-- Test data insertion for all API sections
CREATE OR REPLACE FUNCTION validate_api_section_insertion()
RETURNS TABLE (
    api_section TEXT,
    insertion_status TEXT,
    test_details TEXT,
    error_message TEXT
) AS $$
DECLARE
    test_property_id BIGINT;
    test_realtor_id BIGINT;
    section_name TEXT;
BEGIN
    -- Create a test property first
    INSERT INTO properties_new (
        article_no, article_name, real_estate_type_id,
        trade_type_id, region_id, collected_date, is_active
    ) VALUES (
        'API_TEST_' || extract(epoch from now())::TEXT,
        'API Section Test Property',
        1, 1, 1,  -- Assuming these IDs exist
        CURRENT_DATE, true
    ) RETURNING id INTO test_property_id;
    
    -- Create test realtor
    INSERT INTO realtors (realtor_name, phone_number)
    VALUES ('Test Realtor', '010-1234-5678')
    RETURNING id INTO test_realtor_id;
    
    -- Test each API section
    FOR section_name IN 
        SELECT unnest(ARRAY[
            'articleDetail', 'articlePrice', 'articleLocation',
            'articlePhysical', 'articleRealtor', 'articleImage',
            'articleFacility', 'articleTax', 'articleAddition'
        ])
    LOOP
        BEGIN
            CASE section_name
                WHEN 'articleDetail' THEN
                    -- Already inserted as properties_new
                    NULL;
                    
                WHEN 'articlePrice' THEN
                    INSERT INTO property_prices (property_id, price_type, amount, valid_from)
                    VALUES (test_property_id, 'sale', 500000000, CURRENT_DATE);
                    
                WHEN 'articleLocation' THEN
                    INSERT INTO property_locations (property_id, latitude, longitude, address_road)
                    VALUES (test_property_id, 37.5665, 126.9780, '서울시 강남구 테스트로 123');
                    
                WHEN 'articlePhysical' THEN
                    INSERT INTO property_physical (property_id, area_exclusive, area_supply, room_count)
                    VALUES (test_property_id, 84.5, 120.0, 3);
                    
                WHEN 'articleRealtor' THEN
                    INSERT INTO property_realtors (property_id, realtor_id, is_primary, contact_phone)
                    VALUES (test_property_id, test_realtor_id, true, '010-1234-5678');
                    
                WHEN 'articleImage' THEN
                    INSERT INTO property_images (property_id, image_url, image_type)
                    VALUES (test_property_id, 'https://example.com/test.jpg', 'main');
                    
                WHEN 'articleFacility' THEN
                    INSERT INTO property_facilities (property_id, facility_id, available)
                    VALUES (test_property_id, 1, true);  -- Assuming facility ID 1 exists
                    
                WHEN 'articleTax' THEN
                    INSERT INTO property_tax_info (property_id, acquisition_tax, registration_tax, brokerage_fee)
                    VALUES (test_property_id, 5000000, 2000000, 3000000);
                    
                WHEN 'articleAddition' THEN
                    INSERT INTO property_price_comparison (property_id, same_addr_count, cpid)
                    VALUES (test_property_id, 5, 'TEST_CPID_123');
                    
            END CASE;
            
            RETURN QUERY
            SELECT 
                section_name::TEXT,
                'SUCCESS'::TEXT,
                'Data insertion successful'::TEXT,
                ''::TEXT;
                
        EXCEPTION WHEN others THEN
            RETURN QUERY
            SELECT 
                section_name::TEXT,
                'ERROR'::TEXT,
                'Data insertion failed'::TEXT,
                SQLERRM::TEXT;
        END;
    END LOOP;
    
    -- Clean up test data
    DELETE FROM properties_new WHERE id = test_property_id;
    DELETE FROM realtors WHERE id = test_realtor_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 6. PERFORMANCE IMPACT ASSESSMENT QUERIES
-- =============================================================================

-- Measure query performance before/after schema changes
CREATE OR REPLACE FUNCTION assess_query_performance()
RETURNS TABLE (
    query_type TEXT,
    execution_time_ms NUMERIC,
    rows_returned BIGINT,
    performance_grade TEXT,
    optimization_notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Test 1: Basic property search with joins
    WITH timing_start AS (SELECT clock_timestamp() as start_time),
    search_query AS (
        SELECT COUNT(*) as row_count
        FROM properties_new p
        JOIN regions r ON r.id = p.region_id
        JOIN real_estate_types ret ON ret.id = p.real_estate_type_id
        WHERE p.is_active = true
        AND r.gu_name = '강남구'
        LIMIT 100
    ),
    timing_end AS (SELECT clock_timestamp() as end_time)
    SELECT 
        'Property Search (with JOINs)'::TEXT,
        EXTRACT(milliseconds FROM (te.end_time - ts.start_time))::NUMERIC,
        sq.row_count::BIGINT,
        CASE 
            WHEN EXTRACT(milliseconds FROM (te.end_time - ts.start_time)) < 100 THEN 'EXCELLENT'
            WHEN EXTRACT(milliseconds FROM (te.end_time - ts.start_time)) < 500 THEN 'GOOD'
            WHEN EXTRACT(milliseconds FROM (te.end_time - ts.start_time)) < 1000 THEN 'ACCEPTABLE'
            ELSE 'NEEDS_OPTIMIZATION'
        END::TEXT,
        'Core search query performance'::TEXT
    FROM timing_start ts, search_query sq, timing_end te
    
    UNION ALL
    
    -- Test 2: Complex aggregation query
    WITH timing_start AS (SELECT clock_timestamp() as start_time),
    agg_query AS (
        SELECT COUNT(*) as row_count
        FROM properties_new p
        LEFT JOIN property_prices pp ON pp.property_id = p.id AND pp.valid_to IS NULL
        LEFT JOIN property_physical phy ON phy.property_id = p.id
        WHERE p.is_active = true
        GROUP BY p.region_id
        HAVING COUNT(*) > 10
    ),
    timing_end AS (SELECT clock_timestamp() as end_time)
    SELECT 
        'Aggregation Query'::TEXT,
        EXTRACT(milliseconds FROM (te.end_time - ts.start_time))::NUMERIC,
        (SELECT COUNT(*) FROM agg_query)::BIGINT,
        CASE 
            WHEN EXTRACT(milliseconds FROM (te.end_time - ts.start_time)) < 200 THEN 'EXCELLENT'
            WHEN EXTRACT(milliseconds FROM (te.end_time - ts.start_time)) < 1000 THEN 'GOOD'
            ELSE 'NEEDS_OPTIMIZATION'
        END::TEXT,
        'Complex aggregation performance'::TEXT
    FROM timing_start ts, timing_end te;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 7. DATA COMPLETENESS MONITORING VIEWS
-- =============================================================================

-- Real-time data completeness dashboard
CREATE OR REPLACE VIEW v_schema_health_dashboard AS
WITH completeness_metrics AS (
    SELECT 
        'properties_new' as table_name,
        COUNT(*) as total_records,
        COUNT(article_name) as has_article_name,
        COUNT(real_estate_type_id) as has_type,
        COUNT(region_id) as has_region,
        ROUND(COUNT(article_name)::decimal / COUNT(*) * 100, 2) as completeness_pct
    FROM properties_new WHERE is_active = true
    
    UNION ALL
    
    SELECT 
        'property_locations',
        COUNT(*),
        COUNT(latitude),
        COUNT(address_road),
        COUNT(subway_stations),
        ROUND(COUNT(latitude)::decimal / COUNT(*) * 100, 2)
    FROM property_locations
    
    UNION ALL
    
    SELECT 
        'property_prices',
        COUNT(*),
        COUNT(amount),
        COUNT(CASE WHEN valid_to IS NULL THEN 1 END),
        COUNT(price_type),
        ROUND(COUNT(amount)::decimal / COUNT(*) * 100, 2)
    FROM property_prices
    
    UNION ALL
    
    SELECT 
        'property_tax_info',
        COUNT(*),
        COUNT(total_tax),
        COUNT(brokerage_fee),
        COUNT(acquisition_tax),
        ROUND(COUNT(total_tax)::decimal / NULLIF(COUNT(*), 0) * 100, 2)
    FROM property_tax_info
)
SELECT 
    table_name,
    total_records,
    completeness_pct,
    CASE 
        WHEN completeness_pct >= 90 THEN 'EXCELLENT'
        WHEN completeness_pct >= 70 THEN 'GOOD'
        WHEN completeness_pct >= 50 THEN 'FAIR'
        ELSE 'POOR'
    END as data_quality_grade,
    CASE 
        WHEN completeness_pct < 70 THEN 'Requires parser improvement'
        ELSE 'Data quality acceptable'
    END as recommendation
FROM completeness_metrics
ORDER BY completeness_pct DESC;

-- =============================================================================
-- 8. ONGOING SCHEMA HEALTH MONITORING
-- =============================================================================

-- Daily schema health check function
CREATE OR REPLACE FUNCTION daily_schema_health_check()
RETURNS TABLE (
    check_category TEXT,
    status TEXT,
    metric_value TEXT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Check table sizes and growth
    SELECT 
        'Table Growth'::TEXT,
        CASE 
            WHEN total_size_mb < 1000 THEN 'NORMAL'
            WHEN total_size_mb < 5000 THEN 'MODERATE'
            ELSE 'LARGE'
        END::TEXT,
        FORMAT('Total DB size: %s MB', total_size_mb)::TEXT,
        CASE 
            WHEN total_size_mb > 5000 THEN 'Monitor disk space and consider archiving'
            ELSE 'Size within normal limits'
        END::TEXT
    FROM (
        SELECT ROUND(SUM(pg_total_relation_size(schemaname||'.'||tablename))/1024/1024) as total_size_mb
        FROM pg_tables WHERE schemaname = 'public'
    ) size_stats
    
    UNION ALL
    
    -- Check data freshness
    SELECT 
        'Data Freshness'::TEXT,
        CASE 
            WHEN hours_since_last_collection < 24 THEN 'FRESH'
            WHEN hours_since_last_collection < 72 THEN 'STALE'
            ELSE 'OUTDATED'
        END::TEXT,
        FORMAT('Last collection: %s hours ago', hours_since_last_collection)::TEXT,
        CASE 
            WHEN hours_since_last_collection > 48 THEN 'Check collection system'
            ELSE 'Data collection up to date'
        END::TEXT
    FROM (
        SELECT EXTRACT(epoch FROM (now() - MAX(collected_date)))/3600 as hours_since_last_collection
        FROM properties_new WHERE is_active = true
    ) freshness_stats
    
    UNION ALL
    
    -- Check constraint violations
    SELECT 
        'Data Integrity'::TEXT,
        CASE 
            WHEN violation_count = 0 THEN 'CLEAN'
            WHEN violation_count < 10 THEN 'MINOR_ISSUES'
            ELSE 'MAJOR_ISSUES'
        END::TEXT,
        FORMAT('%s integrity violations found', violation_count)::TEXT,
        CASE 
            WHEN violation_count > 0 THEN 'Review and fix data integrity issues'
            ELSE 'All constraints satisfied'
        END::TEXT
    FROM (
        SELECT (
            -- Count negative prices
            COALESCE((SELECT COUNT(*) FROM property_prices WHERE amount < 0), 0) +
            -- Count invalid areas
            COALESCE((SELECT COUNT(*) FROM property_physical WHERE area_exclusive <= 0), 0) +
            -- Count floor logic violations
            COALESCE((SELECT COUNT(*) FROM property_physical WHERE floor_current > floor_total), 0)
        ) as violation_count
    ) integrity_stats;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 9. MASTER VALIDATION RUNNER
-- =============================================================================

-- Run all validation tests
CREATE OR REPLACE FUNCTION run_comprehensive_schema_validation()
RETURNS TABLE (
    test_suite TEXT,
    overall_status TEXT,
    passed_tests INTEGER,
    total_tests INTEGER,
    critical_issues TEXT[]
) AS $$
DECLARE
    validation_results RECORD;
    critical_issues_list TEXT[] := ARRAY[]::TEXT[];
    total_passed INTEGER := 0;
    total_tests INTEGER := 0;
BEGIN
    -- Initialize results table
    CREATE TEMP TABLE temp_validation_results (
        suite TEXT,
        status TEXT,
        details TEXT,
        critical BOOLEAN DEFAULT false
    );
    
    -- Run schema deployment validation
    INSERT INTO temp_validation_results (suite, status, details, critical)
    SELECT 'Schema Deployment', status, details, 
           CASE WHEN status = 'FAIL' THEN true ELSE false END
    FROM validate_schema_deployment();
    
    -- Run index validation
    INSERT INTO temp_validation_results (suite, status, details, critical)
    SELECT 'Index Deployment', status, 
           FORMAT('%s/%s indexes created', created_count, expected_count),
           CASE WHEN status = 'FAIL' THEN true ELSE false END
    FROM validate_index_deployment();
    
    -- Run FK validation
    INSERT INTO temp_validation_results (suite, status, details, critical)
    SELECT 'Foreign Keys', status, test_result,
           CASE WHEN status = 'FAIL' THEN true ELSE false END
    FROM validate_foreign_key_relationships();
    
    -- Run constraint validation
    INSERT INTO temp_validation_results (suite, status, details, critical)
    SELECT 'Data Constraints', status, details,
           CASE WHEN status = 'FAIL' THEN true ELSE false END
    FROM validate_data_constraints();
    
    -- Count results
    SELECT COUNT(*) INTO total_tests FROM temp_validation_results;
    SELECT COUNT(*) INTO total_passed FROM temp_validation_results WHERE status = 'PASS';
    
    -- Collect critical issues
    SELECT ARRAY_AGG(suite || ': ' || details) INTO critical_issues_list
    FROM temp_validation_results WHERE critical = true;
    
    RETURN QUERY
    SELECT 
        'Schema Validation Suite'::TEXT,
        CASE 
            WHEN total_passed = total_tests THEN 'ALL_PASS'
            WHEN total_passed >= total_tests * 0.8 THEN 'MOSTLY_PASS'
            ELSE 'NEEDS_ATTENTION'
        END::TEXT,
        total_passed,
        total_tests,
        COALESCE(critical_issues_list, ARRAY[]::TEXT[]);
    
    DROP TABLE temp_validation_results;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 10. QUICK VALIDATION COMMANDS
-- =============================================================================

-- Quick health check for immediate use
CREATE OR REPLACE VIEW v_quick_schema_status AS
SELECT 
    'Schema Tables' as component,
    CASE WHEN table_count >= 15 THEN 'OK' ELSE 'INCOMPLETE' END as status,
    FORMAT('%s tables exist', table_count) as details
FROM (
    SELECT COUNT(*) as table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name LIKE '%property%' OR table_name IN ('real_estate_types', 'trade_types', 'regions')
) t

UNION ALL

SELECT 
    'Performance Indexes',
    CASE WHEN index_count >= 20 THEN 'OK' ELSE 'INCOMPLETE' END,
    FORMAT('%s performance indexes', index_count)
FROM (
    SELECT COUNT(*) as index_count 
    FROM pg_indexes 
    WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
) i

UNION ALL

SELECT 
    'Reference Data',
    CASE WHEN ref_data_count >= 3 THEN 'OK' ELSE 'MISSING' END,
    FORMAT('%s reference tables populated', ref_data_count)
FROM (
    SELECT 
        (CASE WHEN EXISTS(SELECT 1 FROM real_estate_types LIMIT 1) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS(SELECT 1 FROM trade_types LIMIT 1) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS(SELECT 1 FROM regions LIMIT 1) THEN 1 ELSE 0 END) as ref_data_count
) r;

-- =============================================================================
-- VALIDATION SUITE COMPLETION
-- =============================================================================

-- Display installation summary
CREATE OR REPLACE FUNCTION schema_validation_suite_summary()
RETURNS TEXT AS $$
BEGIN
    RETURN FORMAT('
🎯 SCHEMA VALIDATION SUITE INSTALLED SUCCESSFULLY!

📊 Available Validation Functions:
✅ validate_schema_deployment() - Check table and column structure
✅ validate_index_deployment() - Verify performance indexes
✅ validate_foreign_key_relationships() - Test FK constraints
✅ validate_data_constraints() - Check data integrity rules
✅ validate_api_section_insertion() - Test all API section data insertion
✅ assess_query_performance() - Measure query execution times
✅ daily_schema_health_check() - Ongoing monitoring
✅ run_comprehensive_schema_validation() - Master validation runner

📈 Monitoring Views:
✅ v_schema_health_dashboard - Real-time completeness metrics
✅ v_quick_schema_status - Instant status overview

🚀 QUICK START COMMANDS:
-- Run complete validation:
SELECT * FROM run_comprehensive_schema_validation();

-- Check current status:
SELECT * FROM v_quick_schema_status;

-- Daily health monitoring:
SELECT * FROM daily_schema_health_check();

-- Performance assessment:
SELECT * FROM assess_query_performance();

Ready for schema deployment validation! 🎉
');
END;
$$ LANGUAGE plpgsql;

-- Show summary
SELECT schema_validation_suite_summary();