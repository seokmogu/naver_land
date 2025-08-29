-- =============================================================================
-- 03 - CREATE PROPERTY_REALTORS TABLE
-- Creates the relationship table between properties and realtors
-- =============================================================================

-- Create property_realtors relationship table
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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_property_realtors_property ON property_realtors(property_id);
CREATE INDEX IF NOT EXISTS idx_property_realtors_realtor ON property_realtors(realtor_id);
CREATE INDEX IF NOT EXISTS idx_property_realtors_primary ON property_realtors(is_primary, listing_date);
CREATE INDEX IF NOT EXISTS idx_property_realtors_active ON property_realtors(is_active, listing_type);

-- Add constraint to ensure only one primary realtor per property
CREATE UNIQUE INDEX IF NOT EXISTS idx_property_realtors_unique_primary 
ON property_realtors(property_id) 
WHERE is_primary = true AND is_active = true;

-- Create validation constraints
ALTER TABLE property_realtors 
ADD CONSTRAINT IF NOT EXISTS chk_listing_type 
CHECK (listing_type IN ('exclusive', 'general', 'co_listing'));

ALTER TABLE property_realtors 
ADD CONSTRAINT IF NOT EXISTS chk_commission_rate 
CHECK (commission_rate IS NULL OR (commission_rate >= 0 AND commission_rate <= 1));

-- Verify table creation
SELECT 
    'property_realtors' as table_name,
    COUNT(*) as column_count,
    pg_size_pretty(pg_total_relation_size('property_realtors')) as table_size
FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'property_realtors';

-- Show table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'property_realtors'
ORDER BY ordinal_position;

-- Show foreign key constraints
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_name = 'property_realtors';