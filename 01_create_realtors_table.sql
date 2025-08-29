-- =============================================================================
-- 01 - CREATE REALTORS TABLE
-- Creates the missing realtors table with all required columns and indexes
-- =============================================================================

-- Create realtors table
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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_realtors_name ON realtors(realtor_name);
CREATE INDEX IF NOT EXISTS idx_realtors_business ON realtors(business_number);
CREATE INDEX IF NOT EXISTS idx_realtors_verified ON realtors(is_verified, rating);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_realtors_updated_at ON realtors;
CREATE TRIGGER update_realtors_updated_at 
    BEFORE UPDATE ON realtors 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Verify table creation
SELECT 
    'realtors' as table_name,
    COUNT(*) as column_count,
    pg_size_pretty(pg_total_relation_size('realtors')) as table_size
FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'realtors';

-- Show table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'realtors'
ORDER BY ordinal_position;