-- =============================================================================
-- 기존 테이블에 누락된 컬럼 추가
-- =============================================================================

-- property_locations 테이블 확장
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS nearest_station TEXT;
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS subway_stations JSONB;
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS detail_address VARCHAR(500);

-- property_physical 테이블 확장  
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS veranda_count INTEGER DEFAULT 0;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS space_type VARCHAR(100);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS structure_type VARCHAR(100);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS floor_description TEXT;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS ground_floor_count INTEGER;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS monthly_management_cost INTEGER;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS management_office_tel VARCHAR(20);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_type VARCHAR(50);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_discussion BOOLEAN DEFAULT false;

-- properties_new 테이블 확장
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS building_use VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS law_usage VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS floor_layer_name VARCHAR(100);
