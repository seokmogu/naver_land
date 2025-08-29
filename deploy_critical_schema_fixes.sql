-- =============================================================================
-- CRITICAL DATABASE SCHEMA FIXES
-- Deploys missing tables and columns identified in error logs
-- =============================================================================

-- Enable error handling
\set ON_ERROR_STOP on
\timing

-- =============================================================================
-- 1. Deploy missing realtors table
-- =============================================================================

-- Check if realtors table exists
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'realtors'
) AS realtors_exists;

-- Create realtors table if it doesn't exist
CREATE TABLE IF NOT EXISTS realtors (
    id BIGSERIAL PRIMARY KEY,
    
    -- 중개사 기본 정보
    realtor_name VARCHAR(200) NOT NULL,
    business_number VARCHAR(50) UNIQUE, -- 사업자등록번호
    license_number VARCHAR(50), -- 중개업 등록번호
    
    -- 연락처 정보
    phone_number VARCHAR(20),
    mobile_number VARCHAR(20),
    email VARCHAR(100),
    website_url VARCHAR(500),
    
    -- 주소 정보
    office_address VARCHAR(500),
    office_postal_code VARCHAR(10),
    
    -- 프로필 정보
    profile_image_url TEXT,
    company_description TEXT,
    
    -- 평점 정보 (향후 확장)
    rating DECIMAL(3, 2),
    review_count INTEGER DEFAULT 0,
    total_listings INTEGER DEFAULT 0, -- 총 매물 등록 수
    active_listings INTEGER DEFAULT 0, -- 현재 활성 매물 수
    
    -- 메타데이터
    is_verified BOOLEAN DEFAULT false,
    last_verified_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for realtors table
CREATE INDEX IF NOT EXISTS idx_realtors_name ON realtors(realtor_name);
CREATE INDEX IF NOT EXISTS idx_realtors_business ON realtors(business_number);
CREATE INDEX IF NOT EXISTS idx_realtors_verified ON realtors(is_verified, rating);

-- =============================================================================
-- 2. Add missing kakao_api_response column to property_locations
-- =============================================================================

-- Add kakao_api_response JSONB column
DO $$
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_api_response'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_api_response JSONB;
        
        -- Create GIN index for JSONB column
        CREATE INDEX idx_property_locations_kakao_api 
        ON property_locations USING GIN (kakao_api_response);
        
        RAISE NOTICE 'Added kakao_api_response JSONB column to property_locations';
    ELSE
        RAISE NOTICE 'kakao_api_response column already exists in property_locations';
    END IF;
END $$;

-- =============================================================================
-- 3. Add missing floor_description column to property_physical
-- =============================================================================

DO $$
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'floor_description'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN floor_description TEXT;
        
        -- Create index for text searches
        CREATE INDEX idx_property_physical_floor_desc 
        ON property_physical(floor_description);
        
        RAISE NOTICE 'Added floor_description TEXT column to property_physical';
    ELSE
        RAISE NOTICE 'floor_description column already exists in property_physical';
    END IF;
END $$;

-- =============================================================================
-- 4. Add missing acquisition_tax_rate column to property_tax_info
-- =============================================================================

-- First ensure property_tax_info table exists
CREATE TABLE IF NOT EXISTS property_tax_info (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    -- 취득세 정보
    acquisition_tax INTEGER DEFAULT 0,
    acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    
    -- 등록세 정보  
    registration_tax INTEGER DEFAULT 0,
    registration_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    
    -- 중개보수 정보
    brokerage_fee INTEGER DEFAULT 0,
    brokerage_fee_rate DECIMAL(5, 4) DEFAULT 0.0000,
    
    -- 기타 세금/비용
    stamp_duty INTEGER DEFAULT 0,
    vat INTEGER DEFAULT 0,
    
    -- 총 비용 계산
    total_tax INTEGER DEFAULT 0,
    total_cost INTEGER DEFAULT 0,
    
    -- 메타데이터
    calculation_date DATE DEFAULT CURRENT_DATE,
    is_estimated BOOLEAN DEFAULT false, -- 추정값 여부
    notes TEXT,
    
    -- 제약조건
    CONSTRAINT chk_tax_amounts CHECK (
        acquisition_tax >= 0 AND registration_tax >= 0 AND 
        brokerage_fee >= 0 AND stamp_duty >= 0 AND 
        vat >= 0 AND total_tax >= 0 AND total_cost >= 0
    ),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check if acquisition_tax_rate column exists and add if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_tax_info' 
        AND column_name = 'acquisition_tax_rate'
    ) THEN
        ALTER TABLE property_tax_info 
        ADD COLUMN acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000;
        
        RAISE NOTICE 'Added acquisition_tax_rate column to property_tax_info';
    ELSE
        RAISE NOTICE 'acquisition_tax_rate column already exists in property_tax_info';
    END IF;
END $$;

-- =============================================================================
-- 5. Create essential indexes for performance
-- =============================================================================

-- property_tax_info indexes
CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_total_cost ON property_tax_info(total_cost);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_date ON property_tax_info(calculation_date);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_tax_rate ON property_tax_info(acquisition_tax_rate);

-- property_realtors table (if referenced but missing)
CREATE TABLE IF NOT EXISTS property_realtors (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    realtor_id BIGINT REFERENCES realtors(id),
    
    -- 관계 정보
    listing_date DATE,
    listing_type VARCHAR(20) DEFAULT 'exclusive', -- 'exclusive', 'general', 'co_listing'
    is_primary BOOLEAN DEFAULT false, -- 주 중개사 여부
    commission_rate DECIMAL(5, 4), -- 중개 수수료율
    
    -- 연락처 (매물별로 다를 수 있음)
    contact_phone VARCHAR(20),
    contact_person VARCHAR(100),
    
    -- 메타데이터
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- property_realtors indexes
CREATE INDEX IF NOT EXISTS idx_property_realtors_property ON property_realtors(property_id);
CREATE INDEX IF NOT EXISTS idx_property_realtors_realtor ON property_realtors(realtor_id);
CREATE INDEX IF NOT EXISTS idx_property_realtors_primary ON property_realtors(is_primary, listing_date);

-- =============================================================================
-- 6. Create update triggers for new tables
-- =============================================================================

-- Update trigger function (reuse existing if available)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to new tables
DROP TRIGGER IF EXISTS update_realtors_updated_at ON realtors;
CREATE TRIGGER update_realtors_updated_at 
    BEFORE UPDATE ON realtors 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
CREATE TRIGGER update_property_tax_info_updated_at 
    BEFORE UPDATE ON property_tax_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 7. Create validation functions and constraints
-- =============================================================================

-- Tax calculation trigger
CREATE OR REPLACE FUNCTION calculate_total_tax_cost()
RETURNS TRIGGER AS $$
BEGIN
    -- 총 세금 계산
    NEW.total_tax = COALESCE(NEW.acquisition_tax, 0) + 
                   COALESCE(NEW.registration_tax, 0) + 
                   COALESCE(NEW.stamp_duty, 0) + 
                   COALESCE(NEW.vat, 0);
    
    -- 총 비용 계산 (세금 + 중개보수)
    NEW.total_cost = NEW.total_tax + COALESCE(NEW.brokerage_fee, 0);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS calculate_tax_totals_trigger ON property_tax_info;
CREATE TRIGGER calculate_tax_totals_trigger
    BEFORE INSERT OR UPDATE ON property_tax_info
    FOR EACH ROW EXECUTE FUNCTION calculate_total_tax_cost();

-- =============================================================================
-- 8. Deployment validation queries
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
        'Main realtors table with 16 columns'::TEXT;

    -- Check property_tax_info table  
    RETURN QUERY
    SELECT 
        'property_tax_info_table'::TEXT,
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'property_tax_info'
        ) THEN 'SUCCESS' ELSE 'MISSING' END,
        'Tax information table with acquisition_tax_rate column'::TEXT;

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

    -- Check indexes
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
        ) >= 8 THEN 'SUCCESS' ELSE 'PARTIAL' END,
        'Performance indexes for new tables and columns'::TEXT;

    -- Check triggers
    RETURN QUERY
    SELECT 
        'update_triggers'::TEXT,
        CASE WHEN (
            SELECT COUNT(*) FROM information_schema.triggers 
            WHERE event_object_schema = 'public' 
            AND (trigger_name LIKE '%realtors%' 
                OR trigger_name LIKE '%property_tax%')
        ) >= 2 THEN 'SUCCESS' ELSE 'PARTIAL' END,
        'Update triggers for automated timestamp management'::TEXT;

END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 9. Execute validation and display results
-- =============================================================================

-- Run validation check
SELECT * FROM validate_critical_schema_deployment();

-- Display summary statistics
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

-- =============================================================================
-- 10. Rollback procedures (in case of issues)
-- =============================================================================

-- Create rollback function
CREATE OR REPLACE FUNCTION rollback_critical_schema_changes()
RETURNS TEXT AS $$
DECLARE
    rollback_sql TEXT;
BEGIN
    rollback_sql := $ROLLBACK$
    -- Remove added columns (be careful with data loss)
    -- ALTER TABLE property_locations DROP COLUMN IF EXISTS kakao_api_response;
    -- ALTER TABLE property_physical DROP COLUMN IF EXISTS floor_description;
    -- ALTER TABLE property_tax_info DROP COLUMN IF EXISTS acquisition_tax_rate;
    
    -- Drop new tables (be careful with data loss)
    -- DROP TABLE IF EXISTS property_realtors CASCADE;
    -- DROP TABLE IF EXISTS realtors CASCADE;
    -- DROP TABLE IF EXISTS property_tax_info CASCADE;
    
    -- Drop new indexes
    DROP INDEX IF EXISTS idx_realtors_name;
    DROP INDEX IF EXISTS idx_realtors_business;
    DROP INDEX IF EXISTS idx_realtors_verified;
    DROP INDEX IF EXISTS idx_property_locations_kakao_api;
    DROP INDEX IF EXISTS idx_property_physical_floor_desc;
    DROP INDEX IF EXISTS idx_property_tax_info_property;
    DROP INDEX IF EXISTS idx_property_tax_info_total_cost;
    DROP INDEX IF EXISTS idx_property_tax_info_date;
    DROP INDEX IF EXISTS idx_property_tax_info_tax_rate;
    
    -- Drop triggers
    DROP TRIGGER IF EXISTS update_realtors_updated_at ON realtors;
    DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
    DROP TRIGGER IF EXISTS calculate_tax_totals_trigger ON property_tax_info;
    
    -- Drop functions
    DROP FUNCTION IF EXISTS validate_critical_schema_deployment();
    DROP FUNCTION IF EXISTS calculate_total_tax_cost();
    $ROLLBACK$;
    
    RETURN 'Rollback SQL generated. Execute manually if needed: ' || rollback_sql;
END;
$$ LANGUAGE plpgsql;

-- Show rollback instructions
SELECT 'ROLLBACK_READY' as status, 
       'Use SELECT rollback_critical_schema_changes(); if rollback needed' as instructions;

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

SELECT 
    '🎉 CRITICAL SCHEMA FIXES DEPLOYED SUCCESSFULLY!' as message,
    NOW()::timestamp as deployment_time,
    'All missing tables and columns have been added' as summary;

-- EOF