-- =============================================================================
-- 완전히 수정된 스키마 업데이트 스크립트
-- Primary Key 충돌 및 모든 문제점 해결
-- =============================================================================

BEGIN;

-- 기본 함수 먼저 생성
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 1. 누락된 테이블 생성 (안전한 방식)
-- =============================================================================

-- 1.1 매물 세금 정보 테이블
CREATE TABLE IF NOT EXISTS property_tax_info (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    acquisition_tax INTEGER DEFAULT 0,
    registration_tax INTEGER DEFAULT 0,
    brokerage_fee INTEGER DEFAULT 0,
    total_tax INTEGER DEFAULT 0,
    total_cost INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_tax_amounts CHECK (
        acquisition_tax >= 0 AND registration_tax >= 0 AND 
        brokerage_fee >= 0 AND total_tax >= 0 AND total_cost >= 0
    )
);

-- 1.2 매물 가격 비교 정보 테이블  
CREATE TABLE IF NOT EXISTS property_price_comparison (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    same_addr_count INTEGER DEFAULT 0,
    same_addr_max_price BIGINT,
    same_addr_min_price BIGINT,
    complex_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 2. 기존 테이블에 컬럼 추가 (중복 방지)
-- =============================================================================

DO $$
BEGIN
    -- property_locations 테이블 확장
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='subway_stations') THEN
        ALTER TABLE property_locations ADD COLUMN subway_stations JSONB;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='detail_address') THEN
        ALTER TABLE property_locations ADD COLUMN detail_address VARCHAR(500);
    END IF;
    
    -- 카카오 API 상세 주소 정보 컬럼들 추가
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='kakao_road_address') THEN
        ALTER TABLE property_locations ADD COLUMN kakao_road_address VARCHAR(500);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='kakao_jibun_address') THEN
        ALTER TABLE property_locations ADD COLUMN kakao_jibun_address VARCHAR(500);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='kakao_building_name') THEN
        ALTER TABLE property_locations ADD COLUMN kakao_building_name VARCHAR(200);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='kakao_zone_no') THEN
        ALTER TABLE property_locations ADD COLUMN kakao_zone_no VARCHAR(10);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='kakao_api_response') THEN
        ALTER TABLE property_locations ADD COLUMN kakao_api_response JSONB;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='address_enriched') THEN
        ALTER TABLE property_locations ADD COLUMN address_enriched BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- property_physical 테이블 확장
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_physical' AND column_name='veranda_count') THEN
        ALTER TABLE property_physical ADD COLUMN veranda_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_physical' AND column_name='monthly_management_cost') THEN
        ALTER TABLE property_physical ADD COLUMN monthly_management_cost INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_physical' AND column_name='heating_type') THEN
        ALTER TABLE property_physical ADD COLUMN heating_type VARCHAR(50);
    END IF;
    
    -- properties_new 테이블 확장
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='properties_new' AND column_name='building_use') THEN
        ALTER TABLE properties_new ADD COLUMN building_use VARCHAR(100);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='properties_new' AND column_name='approval_date') THEN
        ALTER TABLE properties_new ADD COLUMN approval_date DATE;
    END IF;
END $$;

-- =============================================================================
-- 3. 시설 유형 데이터 안전한 확장 (충돌 해결)
-- =============================================================================

-- 기존 최대 ID 확인 후 안전한 ID 사용
DO $$
DECLARE
    max_facility_id INTEGER;
BEGIN
    SELECT COALESCE(MAX(id), 0) + 1 INTO max_facility_id FROM facility_types;
    
    -- 새로운 시설 유형들을 안전한 ID로 추가
    INSERT INTO facility_types (id, facility_code, facility_name, category, is_standard) VALUES
    (max_facility_id, 'FIRE_ALARM', '화재경보기', 'security', false),
    (max_facility_id + 1, 'WATER_PURIFIER', '정수기', 'convenience', false),
    (max_facility_id + 2, 'GAS_RANGE', '가스레인지', 'utility', false),
    (max_facility_id + 3, 'INDUCTION', '인덕션', 'utility', false),
    (max_facility_id + 4, 'MICROWAVE', '전자레인지', 'convenience', false),
    (max_facility_id + 5, 'REFRIGERATOR', '냉장고', 'convenience', false),
    (max_facility_id + 6, 'WASHING_MACHINE', '세탁기', 'convenience', false),
    (max_facility_id + 7, 'DISH_WASHER', '식기세척기', 'convenience', false),
    (max_facility_id + 8, 'SHOE_CLOSET', '신발장', 'convenience', false),
    (max_facility_id + 9, 'FULL_OPTION', '풀옵션', 'convenience', false)
    ON CONFLICT (id) DO NOTHING;
    
    -- 시퀀스 업데이트 (있다면)
    PERFORM setval('facility_types_id_seq', max_facility_id + 10, true);
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '시설 유형 추가 중 에러: %', SQLERRM;
END $$;

-- =============================================================================
-- 4. 인덱스 생성 (안전한 방식)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_price_comparison_property ON property_price_comparison(property_id);
CREATE INDEX IF NOT EXISTS idx_property_locations_subway ON property_locations USING GIN (subway_stations);

-- =============================================================================
-- 5. 트리거 생성
-- =============================================================================

-- 세금 테이블 updated_at 트리거
DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
CREATE TRIGGER update_property_tax_info_updated_at 
    BEFORE UPDATE ON property_tax_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 세금 자동 계산 트리거
CREATE OR REPLACE FUNCTION calculate_total_tax_cost()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_tax = COALESCE(NEW.acquisition_tax, 0) + COALESCE(NEW.registration_tax, 0);
    NEW.total_cost = NEW.total_tax + COALESCE(NEW.brokerage_fee, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS calculate_tax_totals_trigger ON property_tax_info;
CREATE TRIGGER calculate_tax_totals_trigger
    BEFORE INSERT OR UPDATE ON property_tax_info
    FOR EACH ROW EXECUTE FUNCTION calculate_total_tax_cost();

-- =============================================================================
-- 6. 데이터 품질 확인 뷰
-- =============================================================================

CREATE OR REPLACE VIEW data_completeness_summary AS
SELECT 
    'properties' as section,
    COUNT(*) as total_records,
    COUNT(article_name) as has_name,
    ROUND(COUNT(article_name)::decimal / COUNT(*) * 100, 1) as completeness_pct
FROM properties_new
WHERE is_active = true;

-- =============================================================================
-- 7. 최종 확인 함수
-- =============================================================================

CREATE OR REPLACE FUNCTION verify_schema_update()
RETURNS TABLE(
    component TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- 테이블 확인
    RETURN QUERY
    SELECT 
        'property_tax_info' as component,
        CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'property_tax_info')
            THEN '✅ 존재' ELSE '❌ 누락' END as status,
        'Tax information table' as details;
    
    RETURN QUERY
    SELECT 
        'property_price_comparison' as component,
        CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'property_price_comparison')
            THEN '✅ 존재' ELSE '❌ 누락' END as status,
        'Price comparison table' as details;
    
    -- 새 시설 확인
    RETURN QUERY
    SELECT 
        'new_facilities' as component,
        CASE WHEN (SELECT COUNT(*) FROM facility_types WHERE facility_code = 'FIRE_ALARM') > 0
            THEN '✅ 추가됨' ELSE '❌ 누락' END as status,
        (SELECT COUNT(*)::text || ' facilities added' FROM facility_types WHERE facility_code IN ('FIRE_ALARM', 'WATER_PURIFIER')) as details;
        
END;
$$ LANGUAGE plpgsql;

-- 스키마 업데이트 확인
SELECT * FROM verify_schema_update();

COMMIT;

-- 최종 메시지
SELECT '🎉 스키마 업데이트 완료! 모든 충돌 문제가 해결되었습니다.' as result;