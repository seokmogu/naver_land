-- =============================================================================
-- 누락된 테이블 생성
-- =============================================================================

-- 1. property_tax_info 테이블
CREATE TABLE IF NOT EXISTS property_tax_info (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    acquisition_tax INTEGER DEFAULT 0,
    acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    registration_tax INTEGER DEFAULT 0,
    registration_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    brokerage_fee INTEGER DEFAULT 0,
    brokerage_fee_rate DECIMAL(5, 4) DEFAULT 0.0000,
    stamp_duty INTEGER DEFAULT 0,
    vat INTEGER DEFAULT 0,
    total_tax INTEGER DEFAULT 0,
    total_cost INTEGER DEFAULT 0,
    
    calculation_date DATE DEFAULT CURRENT_DATE,
    is_estimated BOOLEAN DEFAULT false,
    notes TEXT,
    
    CONSTRAINT chk_tax_amounts CHECK (
        acquisition_tax >= 0 AND registration_tax >= 0 AND 
        brokerage_fee >= 0 AND stamp_duty >= 0 AND 
        vat >= 0 AND total_tax >= 0 AND total_cost >= 0
    ),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. property_price_comparison 테이블
CREATE TABLE IF NOT EXISTS property_price_comparison (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    same_addr_count INTEGER DEFAULT 0,
    same_addr_max_price BIGINT,
    same_addr_min_price BIGINT,
    cpid VARCHAR(50),
    complex_name VARCHAR(200),
    article_feature_desc TEXT,
    market_data_date DATE DEFAULT CURRENT_DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_price_comparison_logic 
    CHECK (same_addr_max_price IS NULL OR same_addr_min_price IS NULL OR same_addr_max_price >= same_addr_min_price),
    CONSTRAINT chk_same_addr_count_positive 
    CHECK (same_addr_count >= 0)
);

-- 3. property_facilities 테이블 (확인 및 생성)
CREATE TABLE IF NOT EXISTS property_facilities (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facility_types(id),
    
    available BOOLEAN DEFAULT true,
    condition_grade INTEGER CHECK (condition_grade >= 1 AND condition_grade <= 5),
    notes VARCHAR(200),
    last_checked DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
