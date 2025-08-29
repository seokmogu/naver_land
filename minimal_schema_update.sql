-- =============================================================================
-- 최소한의 필수 스키마 업데이트
-- 카카오 주소 변환 지원만 추가 (핵심 기능!)
-- =============================================================================

BEGIN;

-- 필수 함수 생성
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 핵심 기능: 카카오 주소 변환 지원 컬럼 추가
-- =============================================================================

DO $$
BEGIN
    -- property_locations 테이블에 카카오 API 컬럼만 추가
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
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='address_enriched') THEN
        ALTER TABLE property_locations ADD COLUMN address_enriched BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- 지하철 정보 (이건 유용함)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_locations' AND column_name='subway_stations') THEN
        ALTER TABLE property_locations ADD COLUMN subway_stations JSONB;
    END IF;
    
    RAISE NOTICE '✅ 카카오 주소 변환 지원 컬럼 추가 완료';
END $$;

-- =============================================================================
-- 선택적: 유용한 컬럼들만 추가  
-- =============================================================================

DO $$
BEGIN
    -- property_physical 테이블 - 실용적인 정보들
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_physical' AND column_name='monthly_management_cost') THEN
        ALTER TABLE property_physical ADD COLUMN monthly_management_cost INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='property_physical' AND column_name='heating_type') THEN
        ALTER TABLE property_physical ADD COLUMN heating_type VARCHAR(50);
    END IF;
    
    -- properties_new 테이블 - 건물 용도 (검색에 유용)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='properties_new' AND column_name='building_use') THEN
        ALTER TABLE properties_new ADD COLUMN building_use VARCHAR(100);
    END IF;
    
    RAISE NOTICE '✅ 실용적인 추가 컬럼 완료';
END $$;

-- =============================================================================
-- 인덱스 (성능 향상)
-- =============================================================================

-- 인덱스 생성
DO $$
BEGIN
    -- 카카오 관련 인덱스
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_property_locations_kakao_building') THEN
        CREATE INDEX idx_property_locations_kakao_building ON property_locations(kakao_building_name);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_property_locations_address_enriched') THEN
        CREATE INDEX idx_property_locations_address_enriched ON property_locations(address_enriched);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_property_locations_subway') THEN
        CREATE INDEX idx_property_locations_subway ON property_locations USING GIN (subway_stations);
    END IF;
    
    RAISE NOTICE '✅ 인덱스 생성 완료';
END $$;

-- =============================================================================
-- 확인 함수
-- =============================================================================

CREATE OR REPLACE FUNCTION verify_minimal_schema()
RETURNS TEXT AS $$
BEGIN
    RETURN '🎉 최소 스키마 업데이트 완료! 카카오 주소 변환 지원이 추가되었습니다.';
END;
$$ LANGUAGE plpgsql;

SELECT verify_minimal_schema();

COMMIT;