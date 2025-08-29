-- =============================================================================
-- 05 - ADD COMPREHENSIVE MISSING COLUMNS
-- Adds all missing columns referenced in the enhanced data collector
-- =============================================================================

-- 1. Add missing columns to property_locations
DO $$ 
BEGIN
    -- Kakao-related columns (if not already added)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_road_address'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_road_address TEXT;
        RAISE NOTICE 'Added kakao_road_address to property_locations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_jibun_address'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_jibun_address TEXT;
        RAISE NOTICE 'Added kakao_jibun_address to property_locations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_building_name'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_building_name VARCHAR(200);
        RAISE NOTICE 'Added kakao_building_name to property_locations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_zone_no'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_zone_no VARCHAR(10);
        RAISE NOTICE 'Added kakao_zone_no to property_locations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_api_response'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_api_response JSONB;
        RAISE NOTICE 'Added kakao_api_response to property_locations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'address_enriched'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN address_enriched BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added address_enriched to property_locations';
    END IF;

    -- Subway stations JSONB array
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'subway_stations'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN subway_stations JSONB;
        RAISE NOTICE 'Added subway_stations to property_locations';
    END IF;
END $$;

-- 2. Add missing columns to property_physical
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
        RAISE NOTICE 'Added floor_description to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'veranda_count'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN veranda_count INTEGER;
        RAISE NOTICE 'Added veranda_count to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'space_type'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN space_type VARCHAR(100);
        RAISE NOTICE 'Added space_type to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'structure_type'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN structure_type VARCHAR(100);
        RAISE NOTICE 'Added structure_type to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'ground_floor_count'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN ground_floor_count INTEGER;
        RAISE NOTICE 'Added ground_floor_count to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'monthly_management_cost'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN monthly_management_cost INTEGER;
        RAISE NOTICE 'Added monthly_management_cost to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'management_office_tel'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN management_office_tel VARCHAR(20);
        RAISE NOTICE 'Added management_office_tel to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'move_in_type'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN move_in_type VARCHAR(50);
        RAISE NOTICE 'Added move_in_type to property_physical';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'move_in_discussion'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN move_in_discussion BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added move_in_discussion to property_physical';
    END IF;

    -- Direction column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'direction'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN direction VARCHAR(20);
        RAISE NOTICE 'Added direction to property_physical';
    END IF;
END $$;

-- 3. Create property_tax_info table if it doesn't exist
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
    is_estimated BOOLEAN DEFAULT false,
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

-- 4. Add missing facility types to facility_types table
INSERT INTO facility_types (facility_code, facility_name, category, is_standard) VALUES
('FIRE_ALARM', '화재경보기', 'safety', false),
('GAS_RANGE', '가스레인지', 'appliance', false),
('INDUCTION', '인덕션', 'appliance', false),
('MICROWAVE', '전자레인지', 'appliance', false),
('REFRIGERATOR', '냉장고', 'appliance', false),
('WASHING_MACHINE', '세탁기', 'appliance', false),
('DISH_WASHER', '식기세척기', 'appliance', false),
('SHOE_CLOSET', '신발장', 'furniture', false),
('FULL_OPTION', '풀옵션', 'convenience', false)
ON CONFLICT (facility_code) DO NOTHING;

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_property_locations_kakao_road 
ON property_locations(kakao_road_address) WHERE kakao_road_address IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_property_locations_subway_stations 
ON property_locations USING GIN(subway_stations) WHERE subway_stations IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_property_physical_space_type 
ON property_physical(space_type) WHERE space_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_property_physical_structure_type 
ON property_physical(structure_type) WHERE structure_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_property_physical_move_in_type 
ON property_physical(move_in_type) WHERE move_in_type IS NOT NULL;

-- Index for property_tax_info
CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_total_cost ON property_tax_info(total_cost);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_date ON property_tax_info(calculation_date);

-- 6. Add triggers and functions for property_tax_info
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

DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
CREATE TRIGGER update_property_tax_info_updated_at 
    BEFORE UPDATE ON property_tax_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. Verification query
SELECT 
    'property_locations' as table_name,
    COUNT(*) as added_columns
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'property_locations'
  AND column_name IN ('kakao_road_address', 'kakao_jibun_address', 'kakao_building_name', 
                      'kakao_zone_no', 'kakao_api_response', 'address_enriched', 'subway_stations')

UNION ALL

SELECT 
    'property_physical' as table_name,
    COUNT(*) as added_columns  
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'property_physical'
  AND column_name IN ('floor_description', 'veranda_count', 'space_type', 'structure_type',
                      'ground_floor_count', 'monthly_management_cost', 'management_office_tel',
                      'move_in_type', 'move_in_discussion', 'direction')

UNION ALL

SELECT 
    'property_tax_info' as table_name,
    COUNT(*) as total_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'property_tax_info';

ANALYZE property_locations;
ANALYZE property_physical;
ANALYZE property_tax_info;

-- 8. Comments for documentation
COMMENT ON COLUMN property_locations.subway_stations IS 'Array of nearby subway stations (JSONB)';
COMMENT ON COLUMN property_physical.floor_description IS 'Detailed floor description';
COMMENT ON COLUMN property_physical.veranda_count IS 'Number of verandas/balconies';
COMMENT ON COLUMN property_physical.space_type IS 'Type of space (residential, commercial, etc.)';
COMMENT ON COLUMN property_physical.structure_type IS 'Building structure type (RC, steel, etc.)';
COMMENT ON COLUMN property_physical.ground_floor_count IS 'Number of above-ground floors';
COMMENT ON COLUMN property_physical.monthly_management_cost IS 'Monthly management fee';
COMMENT ON COLUMN property_physical.management_office_tel IS 'Management office telephone';
COMMENT ON COLUMN property_physical.move_in_type IS 'Move-in type (immediate, negotiable, etc.)';
COMMENT ON COLUMN property_physical.move_in_discussion IS 'Whether move-in date is negotiable';

COMMENT ON TABLE property_tax_info IS 'Property tax and fee information';
COMMENT ON COLUMN property_tax_info.acquisition_tax_rate IS 'Acquisition tax rate as decimal (e.g., 0.01 for 1%)';