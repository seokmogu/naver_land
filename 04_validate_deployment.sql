-- =============================================================================
-- 04 - VALIDATE DEPLOYMENT
-- Comprehensive validation of all deployed schema elements
-- =============================================================================

-- Create validation function
CREATE OR REPLACE FUNCTION validate_critical_schema_deployment()
RETURNS TABLE (
    component TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Check realtors table
    RETURN QUERY
    SELECT 
        'realtors_table'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'realtors'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'Main realtors table with 16+ columns'::TEXT;

    -- Check property_tax_info table  
    RETURN QUERY
    SELECT 
        'property_tax_info_table'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'property_tax_info'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'Tax information table with acquisition_tax_rate column'::TEXT;

    -- Check property_realtors table
    RETURN QUERY
    SELECT 
        'property_realtors_table'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'property_realtors'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'Property-realtor relationship mapping table'::TEXT;

    -- Check kakao_api_response column
    RETURN QUERY  
    SELECT 
        'kakao_api_response_column'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'property_locations' 
            AND column_name = 'kakao_api_response'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'JSONB column for Kakao API responses'::TEXT;

    -- Check floor_description column
    RETURN QUERY
    SELECT 
        'floor_description_column'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'property_physical' 
            AND column_name = 'floor_description'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'TEXT column for floor descriptions'::TEXT;

    -- Check acquisition_tax_rate column
    RETURN QUERY
    SELECT 
        'acquisition_tax_rate_column'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'property_tax_info' 
            AND column_name = 'acquisition_tax_rate'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'DECIMAL column for tax rate calculations'::TEXT;

    -- Check performance indexes
    RETURN QUERY
    SELECT 
        'performance_indexes'::TEXT,
        CASE WHEN (
            SELECT COUNT(*) FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND (indexname LIKE '%realtors%' 
                OR indexname LIKE '%property_tax_info%' 
                OR indexname LIKE '%kakao_api%'
                OR indexname LIKE '%floor_desc%')
        ) >= 6 THEN 'SUCCESS' ELSE 'PARTIAL' END,
        'Performance indexes for new tables and columns'::TEXT;

    -- Check foreign key constraints
    RETURN QUERY
    SELECT 
        'foreign_key_constraints'::TEXT,
        CASE WHEN (
            SELECT COUNT(*) FROM information_schema.table_constraints 
            WHERE table_schema = 'public' 
            AND constraint_type = 'FOREIGN KEY'
            AND table_name IN ('property_realtors', 'property_tax_info')
        ) >= 2 THEN 'SUCCESS' ELSE 'PARTIAL' END,
        'Foreign key relationships for data integrity'::TEXT;

END;
$$ LANGUAGE plpgsql;

-- Run comprehensive validation
SELECT 
    '🔍 COMPREHENSIVE SCHEMA VALIDATION RESULTS' as title,
    NOW()::timestamp as validation_time;

SELECT 
    CASE 
        WHEN status = 'SUCCESS' THEN '✅'
        WHEN status = 'PARTIAL' THEN '⚠️'
        ELSE '❌'
    END as icon,
    component,
    status,
    details
FROM validate_critical_schema_deployment()
ORDER BY 
    CASE status 
        WHEN 'SUCCESS' THEN 1 
        WHEN 'PARTIAL' THEN 2 
        ELSE 3 
    END,
    component;

-- Summary statistics
SELECT 
    'DEPLOYMENT_SUMMARY' as report_type,
    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_components,
    COUNT(CASE WHEN status = 'MISSING' THEN 1 END) as missing_components,
    COUNT(CASE WHEN status = 'PARTIAL' THEN 1 END) as partial_components,
    COUNT(*) as total_components,
    ROUND(
        COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END)::decimal / COUNT(*) * 100, 
        2
    ) as success_percentage
FROM validate_critical_schema_deployment();

-- Detailed table analysis
SELECT 
    '📊 TABLE ANALYSIS' as section,
    NOW()::date as analysis_date;

-- Count rows in each critical table
SELECT 
    'Table Row Counts' as metric_type,
    'realtors' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('realtors')) as table_size
FROM realtors
UNION ALL
SELECT 
    'Table Row Counts' as metric_type,
    'property_realtors' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('property_realtors')) as table_size
FROM property_realtors
UNION ALL
SELECT 
    'Table Row Counts' as metric_type,
    'property_tax_info' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('property_tax_info')) as table_size
FROM property_tax_info;

-- Check data completeness for new columns
SELECT 
    '📋 COLUMN DATA COMPLETENESS' as section;

-- Check kakao_api_response column usage
SELECT 
    'property_locations' as table_name,
    'kakao_api_response' as column_name,
    COUNT(*) as total_rows,
    COUNT(kakao_api_response) as rows_with_data,
    ROUND(COUNT(kakao_api_response)::decimal / COUNT(*) * 100, 2) as completeness_pct
FROM property_locations
UNION ALL
-- Check floor_description column usage  
SELECT 
    'property_physical' as table_name,
    'floor_description' as column_name,
    COUNT(*) as total_rows,
    COUNT(floor_description) as rows_with_data,
    ROUND(COUNT(floor_description)::decimal / COUNT(*) * 100, 2) as completeness_pct
FROM property_physical;

-- Index analysis
SELECT 
    '📈 INDEX ANALYSIS' as section;

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND (indexname LIKE '%realtors%' 
    OR indexname LIKE '%property_tax_info%' 
    OR indexname LIKE '%kakao_api%' 
    OR indexname LIKE '%floor_desc%')
ORDER BY tablename, indexname;

-- Final validation message
SELECT 
    CASE 
        WHEN (
            SELECT COUNT(*) FROM validate_critical_schema_deployment() 
            WHERE status = 'SUCCESS'
        ) >= 6 THEN '🎉 CRITICAL SCHEMA DEPLOYMENT SUCCESSFUL!'
        WHEN (
            SELECT COUNT(*) FROM validate_critical_schema_deployment() 
            WHERE status = 'SUCCESS'
        ) >= 4 THEN '⚠️ DEPLOYMENT MOSTLY SUCCESSFUL - REVIEW PARTIAL ITEMS'
        ELSE '❌ DEPLOYMENT INCOMPLETE - MANUAL INTERVENTION REQUIRED'
    END as final_status,
    'Validation completed at: ' || NOW()::timestamp as completion_time;