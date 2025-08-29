-- =============================================================================
-- 02 - ADD MISSING COLUMNS
-- Adds the critical missing columns identified in the error logs
-- =============================================================================

-- Add kakao_api_response JSONB column to property_locations
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_api_response'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_api_response JSONB;
        
        -- Create GIN index for JSONB column performance
        CREATE INDEX idx_property_locations_kakao_api 
        ON property_locations USING GIN (kakao_api_response);
        
        RAISE NOTICE 'Added kakao_api_response JSONB column to property_locations';
    ELSE
        RAISE NOTICE 'kakao_api_response column already exists in property_locations';
    END IF;
END $$;

-- Add floor_description TEXT column to property_physical  
DO $$ 
BEGIN
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

-- Ensure property_tax_info table exists and has acquisition_tax_rate column
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

-- Ensure acquisition_tax_rate column exists in property_tax_info
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

-- Create indexes for property_tax_info
CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_total_cost ON property_tax_info(total_cost);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_date ON property_tax_info(calculation_date);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_tax_rate ON property_tax_info(acquisition_tax_rate);

-- Create update trigger for property_tax_info
DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
CREATE TRIGGER update_property_tax_info_updated_at 
    BEFORE UPDATE ON property_tax_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Tax calculation trigger for automatic totals
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

-- Verify columns were added
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('property_locations', 'property_physical', 'property_tax_info')
AND column_name IN ('kakao_api_response', 'floor_description', 'acquisition_tax_rate')
ORDER BY table_name, column_name;