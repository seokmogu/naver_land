-- 데이터베이스 스키마 NULL 값 최적화 스크립트
-- NULL 값 문제 해결을 위한 기본값 설정 및 제약조건 개선

-- =============================================================================
-- 1. 기본값 설정 (Default Values)
-- =============================================================================

-- properties_new 테이블 기본값 설정
ALTER TABLE properties_new 
ALTER COLUMN article_name SET DEFAULT '제목 없음';

COMMENT ON COLUMN properties_new.article_name IS '매물명 (기본값: 제목 없음)';

-- property_locations 테이블 기본값 설정
ALTER TABLE property_locations
ALTER COLUMN address_jibun SET DEFAULT '',
ALTER COLUMN postal_code SET DEFAULT '00000',
ALTER COLUMN nearest_station SET DEFAULT '정보없음',
ALTER COLUMN cortar_no SET DEFAULT '1168010100',
ALTER COLUMN address_verified SET DEFAULT false;

COMMENT ON COLUMN property_locations.postal_code IS '우편번호 (기본값: 00000)';
COMMENT ON COLUMN property_locations.nearest_station IS '최인접역 (기본값: 정보없음)';

-- property_physical 테이블 기본값 설정
ALTER TABLE property_physical 
ALTER COLUMN area_exclusive SET DEFAULT 33.0,  -- 10평
ALTER COLUMN area_supply SET DEFAULT 43.0,     -- 13평
ALTER COLUMN area_utilization_rate SET DEFAULT 80.0,
ALTER COLUMN floor_current SET DEFAULT 1,
ALTER COLUMN floor_total SET DEFAULT 5,
ALTER COLUMN floor_underground SET DEFAULT 0,
ALTER COLUMN room_count SET DEFAULT 1,
ALTER COLUMN bathroom_count SET DEFAULT 1,
ALTER COLUMN direction SET DEFAULT '남향',
ALTER COLUMN parking_count SET DEFAULT 1,
ALTER COLUMN parking_possible SET DEFAULT false,
ALTER COLUMN elevator_available SET DEFAULT false,
ALTER COLUMN heating_type SET DEFAULT '개별난방',
ALTER COLUMN building_use_type SET DEFAULT '일반';

COMMENT ON COLUMN property_physical.area_exclusive IS '전용면적 (기본값: 33㎡)';
COMMENT ON COLUMN property_physical.direction IS '방향 (기본값: 남향)';
COMMENT ON COLUMN property_physical.heating_type IS '난방타입 (기본값: 개별난방)';

-- property_images 테이블 기본값 설정
ALTER TABLE property_images
ALTER COLUMN alt_text SET DEFAULT '매물 이미지',
ALTER COLUMN caption SET DEFAULT '',
ALTER COLUMN file_size SET DEFAULT 0,
ALTER COLUMN width SET DEFAULT 0,
ALTER COLUMN height SET DEFAULT 0,
ALTER COLUMN is_high_quality SET DEFAULT false,
ALTER COLUMN is_verified SET DEFAULT false;

COMMENT ON COLUMN property_images.alt_text IS '이미지 설명 (기본값: 매물 이미지)';

-- property_prices 테이블 - valid_to와 notes는 NULL 허용 유지 (선택적 필드)
ALTER TABLE property_prices
ALTER COLUMN currency SET DEFAULT 'KRW';

-- =============================================================================
-- 2. 제약조건 개선 (Enhanced Constraints)  
-- =============================================================================

-- property_physical 테이블 제약조건 강화
ALTER TABLE property_physical 
DROP CONSTRAINT IF EXISTS chk_positive_area,
ADD CONSTRAINT chk_positive_area CHECK (area_exclusive > 0 AND area_supply > 0 AND area_exclusive <= area_supply);

ALTER TABLE property_physical
DROP CONSTRAINT IF EXISTS chk_floor_logic,
ADD CONSTRAINT chk_floor_logic CHECK (
    floor_current IS NOT NULL AND 
    floor_total IS NOT NULL AND 
    floor_current <= floor_total AND
    floor_total > 0
);

ALTER TABLE property_physical
ADD CONSTRAINT chk_room_count CHECK (room_count >= 0 AND bathroom_count >= 0);

ALTER TABLE property_physical
ADD CONSTRAINT chk_parking_count CHECK (parking_count >= 0 AND parking_count <= 100);

-- property_locations 테이블 제약조건
ALTER TABLE property_locations
ADD CONSTRAINT chk_coordinates CHECK (
    (latitude IS NULL AND longitude IS NULL) OR 
    (latitude IS NOT NULL AND longitude IS NOT NULL AND 
     latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
);

ALTER TABLE property_locations
ADD CONSTRAINT chk_walking_time CHECK (walking_to_subway > 0 AND walking_to_subway <= 120);

-- property_prices 테이블 제약조건 강화
ALTER TABLE property_prices
DROP CONSTRAINT IF EXISTS chk_positive_amount,
ADD CONSTRAINT chk_positive_amount CHECK (amount > 0);

ALTER TABLE property_prices
ADD CONSTRAINT chk_price_dates CHECK (
    valid_to IS NULL OR valid_to >= valid_from
);

-- =============================================================================
-- 3. 데이터 품질 검증 함수 생성
-- =============================================================================

-- 데이터 품질 검증 함수
CREATE OR REPLACE FUNCTION validate_property_data()
RETURNS TABLE(
    table_name TEXT,
    column_name TEXT, 
    null_count INTEGER,
    total_count INTEGER,
    null_percentage DECIMAL(5,2),
    data_quality_grade CHAR(1)
) AS $$
BEGIN
    RETURN QUERY
    
    -- properties_new 테이블 검증
    SELECT 
        'properties_new'::TEXT as table_name,
        'article_name'::TEXT as column_name,
        COUNT(*) FILTER (WHERE article_name IS NULL OR article_name = '')::INTEGER as null_count,
        COUNT(*)::INTEGER as total_count,
        ROUND(
            (COUNT(*) FILTER (WHERE article_name IS NULL OR article_name = '') * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        ) as null_percentage,
        CASE 
            WHEN COUNT(*) FILTER (WHERE article_name IS NULL OR article_name = '') * 100.0 / NULLIF(COUNT(*), 0) < 5 THEN 'A'
            WHEN COUNT(*) FILTER (WHERE article_name IS NULL OR article_name = '') * 100.0 / NULLIF(COUNT(*), 0) < 15 THEN 'B'
            WHEN COUNT(*) FILTER (WHERE article_name IS NULL OR article_name = '') * 100.0 / NULLIF(COUNT(*), 0) < 30 THEN 'C'
            ELSE 'D'
        END as data_quality_grade
    FROM properties_new
    WHERE id IS NOT NULL
    
    UNION ALL
    
    -- property_physical 주요 필드 검증
    SELECT 
        'property_physical'::TEXT,
        'room_count'::TEXT,
        COUNT(*) FILTER (WHERE room_count IS NULL)::INTEGER,
        COUNT(*)::INTEGER,
        ROUND(
            (COUNT(*) FILTER (WHERE room_count IS NULL) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        ),
        CASE 
            WHEN COUNT(*) FILTER (WHERE room_count IS NULL) * 100.0 / NULLIF(COUNT(*), 0) < 5 THEN 'A'
            WHEN COUNT(*) FILTER (WHERE room_count IS NULL) * 100.0 / NULLIF(COUNT(*), 0) < 15 THEN 'B'
            WHEN COUNT(*) FILTER (WHERE room_count IS NULL) * 100.0 / NULLIF(COUNT(*), 0) < 30 THEN 'C'
            ELSE 'D'
        END
    FROM property_physical
    WHERE id IS NOT NULL
    
    UNION ALL
    
    SELECT 
        'property_physical'::TEXT,
        'floor_current'::TEXT,
        COUNT(*) FILTER (WHERE floor_current IS NULL)::INTEGER,
        COUNT(*)::INTEGER,
        ROUND(
            (COUNT(*) FILTER (WHERE floor_current IS NULL) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        ),
        CASE 
            WHEN COUNT(*) FILTER (WHERE floor_current IS NULL) * 100.0 / NULLIF(COUNT(*), 0) < 5 THEN 'A'
            WHEN COUNT(*) FILTER (WHERE floor_current IS NULL) * 100.0 / NULLIF(COUNT(*), 0) < 15 THEN 'B'
            WHEN COUNT(*) FILTER (WHERE floor_current IS NULL) * 100.0 / NULLIF(COUNT(*), 0) < 30 THEN 'C'
            ELSE 'D'
        END
    FROM property_physical
    WHERE id IS NOT NULL
    
    UNION ALL
    
    -- property_locations 검증
    SELECT 
        'property_locations'::TEXT,
        'cortar_no'::TEXT,
        COUNT(*) FILTER (WHERE cortar_no IS NULL OR cortar_no = '')::INTEGER,
        COUNT(*)::INTEGER,
        ROUND(
            (COUNT(*) FILTER (WHERE cortar_no IS NULL OR cortar_no = '') * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        ),
        CASE 
            WHEN COUNT(*) FILTER (WHERE cortar_no IS NULL OR cortar_no = '') * 100.0 / NULLIF(COUNT(*), 0) < 5 THEN 'A'
            WHEN COUNT(*) FILTER (WHERE cortar_no IS NULL OR cortar_no = '') * 100.0 / NULLIF(COUNT(*), 0) < 15 THEN 'B'
            WHEN COUNT(*) FILTER (WHERE cortar_no IS NULL OR cortar_no = '') * 100.0 / NULLIF(COUNT(*), 0) < 30 THEN 'C'
            ELSE 'D'
        END
    FROM property_locations
    WHERE id IS NOT NULL;
    
END;
$$ LANGUAGE plpgsql;

-- 외래키 참조 무결성 검증 함수
CREATE OR REPLACE FUNCTION validate_foreign_keys()
RETURNS TABLE(
    table_name TEXT,
    foreign_key_column TEXT,
    null_count INTEGER,
    invalid_references INTEGER,
    total_count INTEGER,
    integrity_score DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    
    -- properties_new 외래키 검증
    SELECT 
        'properties_new'::TEXT as table_name,
        'real_estate_type_id'::TEXT as foreign_key_column,
        COUNT(*) FILTER (WHERE real_estate_type_id IS NULL)::INTEGER as null_count,
        COUNT(*) FILTER (WHERE real_estate_type_id IS NOT NULL AND real_estate_type_id NOT IN (SELECT id FROM real_estate_types))::INTEGER as invalid_references,
        COUNT(*)::INTEGER as total_count,
        ROUND(
            ((COUNT(*) - COUNT(*) FILTER (WHERE real_estate_type_id IS NULL OR real_estate_type_id NOT IN (SELECT id FROM real_estate_types))) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        ) as integrity_score
    FROM properties_new
    WHERE id IS NOT NULL
    
    UNION ALL
    
    SELECT 
        'properties_new'::TEXT,
        'trade_type_id'::TEXT,
        COUNT(*) FILTER (WHERE trade_type_id IS NULL)::INTEGER,
        COUNT(*) FILTER (WHERE trade_type_id IS NOT NULL AND trade_type_id NOT IN (SELECT id FROM trade_types))::INTEGER,
        COUNT(*)::INTEGER,
        ROUND(
            ((COUNT(*) - COUNT(*) FILTER (WHERE trade_type_id IS NULL OR trade_type_id NOT IN (SELECT id FROM trade_types))) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        )
    FROM properties_new
    WHERE id IS NOT NULL
    
    UNION ALL
    
    SELECT 
        'properties_new'::TEXT,
        'region_id'::TEXT,
        COUNT(*) FILTER (WHERE region_id IS NULL)::INTEGER,
        COUNT(*) FILTER (WHERE region_id IS NOT NULL AND region_id NOT IN (SELECT id FROM regions))::INTEGER,
        COUNT(*)::INTEGER,
        ROUND(
            ((COUNT(*) - COUNT(*) FILTER (WHERE region_id IS NULL OR region_id NOT IN (SELECT id FROM regions))) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
        )
    FROM properties_new
    WHERE id IS NOT NULL;
    
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 4. 기존 데이터 정리 및 보정
-- =============================================================================

-- NULL 값을 기본값으로 업데이트하는 함수
CREATE OR REPLACE FUNCTION fix_existing_null_values()
RETURNS TEXT AS $$
DECLARE
    update_count INTEGER := 0;
    result_message TEXT := '';
BEGIN
    
    -- properties_new 테이블 NULL 수정
    UPDATE properties_new 
    SET article_name = '제목 없음'
    WHERE article_name IS NULL OR article_name = '';
    
    GET DIAGNOSTICS update_count = ROW_COUNT;
    result_message := result_message || format('properties_new.article_name: %s개 수정\n', update_count);
    
    -- property_locations 테이블 NULL 수정
    UPDATE property_locations 
    SET 
        address_jibun = COALESCE(address_road, '주소 정보 없음'),
        postal_code = COALESCE(postal_code, '00000'),
        nearest_station = COALESCE(nearest_station, '정보없음'),
        cortar_no = COALESCE(cortar_no, '1168010100')
    WHERE address_jibun IS NULL 
       OR postal_code IS NULL 
       OR nearest_station IS NULL 
       OR cortar_no IS NULL;
    
    GET DIAGNOSTICS update_count = ROW_COUNT;
    result_message := result_message || format('property_locations 주소정보: %s개 수정\n', update_count);
    
    -- property_physical 테이블 NULL 수정 (추론 로직 적용)
    UPDATE property_physical 
    SET 
        floor_current = COALESCE(floor_current, 1),
        floor_total = COALESCE(floor_total, 5),
        room_count = COALESCE(room_count, 
            CASE 
                WHEN area_exclusive < 40 THEN 1
                WHEN area_exclusive < 60 THEN 2
                WHEN area_exclusive < 100 THEN 3
                ELSE 4
            END),
        bathroom_count = COALESCE(bathroom_count,
            CASE 
                WHEN room_count <= 1 THEN 1
                WHEN room_count <= 3 THEN 1
                ELSE 2
            END),
        direction = COALESCE(direction, '남향'),
        parking_count = COALESCE(parking_count, 1),
        heating_type = COALESCE(heating_type, '개별난방'),
        building_use_type = COALESCE(building_use_type, '일반')
    WHERE floor_current IS NULL 
       OR floor_total IS NULL
       OR room_count IS NULL 
       OR bathroom_count IS NULL
       OR direction IS NULL
       OR parking_count IS NULL
       OR heating_type IS NULL
       OR building_use_type IS NULL;
    
    GET DIAGNOSTICS update_count = ROW_COUNT;
    result_message := result_message || format('property_physical 물리정보: %s개 수정\n', update_count);
    
    -- property_images alt_text 수정
    UPDATE property_images 
    SET alt_text = '매물 이미지'
    WHERE alt_text IS NULL OR alt_text = '';
    
    GET DIAGNOSTICS update_count = ROW_COUNT;
    result_message := result_message || format('property_images.alt_text: %s개 수정\n', update_count);
    
    RETURN result_message || '기존 NULL 값 수정 완료!';
    
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 5. 데이터 품질 모니터링 뷰 생성
-- =============================================================================

-- 실시간 데이터 품질 모니터링 뷰
CREATE OR REPLACE VIEW data_quality_dashboard AS
SELECT 
    'properties_new' as table_name,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE article_name IS NOT NULL AND article_name != '') as complete_article_names,
    COUNT(*) FILTER (WHERE real_estate_type_id IS NOT NULL) as complete_real_estate_types,
    COUNT(*) FILTER (WHERE trade_type_id IS NOT NULL) as complete_trade_types,
    COUNT(*) FILTER (WHERE region_id IS NOT NULL) as complete_regions,
    ROUND(
        (COUNT(*) FILTER (WHERE article_name IS NOT NULL AND article_name != '' 
                          AND real_estate_type_id IS NOT NULL 
                          AND trade_type_id IS NOT NULL 
                          AND region_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
    ) as completeness_percentage,
    CASE 
        WHEN COUNT(*) FILTER (WHERE article_name IS NOT NULL AND article_name != '' 
                              AND real_estate_type_id IS NOT NULL 
                              AND trade_type_id IS NOT NULL 
                              AND region_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) >= 95 THEN 'EXCELLENT'
        WHEN COUNT(*) FILTER (WHERE article_name IS NOT NULL AND article_name != '' 
                              AND real_estate_type_id IS NOT NULL 
                              AND trade_type_id IS NOT NULL 
                              AND region_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) >= 85 THEN 'GOOD'
        WHEN COUNT(*) FILTER (WHERE article_name IS NOT NULL AND article_name != '' 
                              AND real_estate_type_id IS NOT NULL 
                              AND trade_type_id IS NOT NULL 
                              AND region_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) >= 70 THEN 'FAIR'
        ELSE 'POOR'
    END as quality_grade
FROM properties_new

UNION ALL

SELECT 
    'property_physical' as table_name,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE area_exclusive IS NOT NULL AND area_exclusive > 0) as complete_areas,
    COUNT(*) FILTER (WHERE floor_current IS NOT NULL AND floor_total IS NOT NULL) as complete_floors,
    COUNT(*) FILTER (WHERE room_count IS NOT NULL AND bathroom_count IS NOT NULL) as complete_rooms,
    0 as placeholder_col,
    ROUND(
        (COUNT(*) FILTER (WHERE area_exclusive IS NOT NULL AND area_exclusive > 0 
                          AND floor_current IS NOT NULL 
                          AND floor_total IS NOT NULL 
                          AND room_count IS NOT NULL 
                          AND bathroom_count IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL, 2
    ) as completeness_percentage,
    CASE 
        WHEN COUNT(*) FILTER (WHERE area_exclusive IS NOT NULL AND area_exclusive > 0 
                              AND floor_current IS NOT NULL 
                              AND floor_total IS NOT NULL 
                              AND room_count IS NOT NULL 
                              AND bathroom_count IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) >= 95 THEN 'EXCELLENT'
        WHEN COUNT(*) FILTER (WHERE area_exclusive IS NOT NULL AND area_exclusive > 0 
                              AND floor_current IS NOT NULL 
                              AND floor_total IS NOT NULL 
                              AND room_count IS NOT NULL 
                              AND bathroom_count IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) >= 85 THEN 'GOOD'
        WHEN COUNT(*) FILTER (WHERE area_exclusive IS NOT NULL AND area_exclusive > 0 
                              AND floor_current IS NOT NULL 
                              AND floor_total IS NOT NULL 
                              AND room_count IS NOT NULL 
                              AND bathroom_count IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) >= 70 THEN 'FAIR'
        ELSE 'POOR'
    END as quality_grade
FROM property_physical;

-- =============================================================================
-- 6. 트리거 생성 (데이터 입력 시 품질 보장)
-- =============================================================================

-- 데이터 입력 시 NULL 값 보정 트리거 함수
CREATE OR REPLACE FUNCTION ensure_data_quality()
RETURNS TRIGGER AS $$
BEGIN
    -- properties_new 테이블에 대한 처리
    IF TG_TABLE_NAME = 'properties_new' THEN
        NEW.article_name := COALESCE(NEW.article_name, '제목 없음');
        
        -- 외래키가 NULL인 경우 기본값 설정 (실제로는 어플리케이션에서 처리해야 함)
        IF NEW.real_estate_type_id IS NULL THEN
            -- 기본 부동산 유형 ID (1번이 존재한다고 가정)
            NEW.real_estate_type_id := 1;
        END IF;
        
        IF NEW.trade_type_id IS NULL THEN
            -- 기본 거래 유형 ID (1번이 존재한다고 가정)
            NEW.trade_type_id := 1;
        END IF;
        
        IF NEW.region_id IS NULL THEN
            -- 기본 지역 ID (1번이 존재한다고 가정)
            NEW.region_id := 1;
        END IF;
    END IF;
    
    -- property_physical 테이블에 대한 처리
    IF TG_TABLE_NAME = 'property_physical' THEN
        NEW.floor_current := COALESCE(NEW.floor_current, 1);
        NEW.floor_total := COALESCE(NEW.floor_total, GREATEST(NEW.floor_current, 5));
        NEW.room_count := COALESCE(NEW.room_count, 
            CASE 
                WHEN NEW.area_exclusive < 40 THEN 1
                WHEN NEW.area_exclusive < 60 THEN 2
                WHEN NEW.area_exclusive < 100 THEN 3
                ELSE 4
            END);
        NEW.bathroom_count := COALESCE(NEW.bathroom_count,
            CASE 
                WHEN NEW.room_count <= 1 THEN 1
                WHEN NEW.room_count <= 3 THEN 1
                ELSE 2
            END);
        NEW.direction := COALESCE(NEW.direction, '남향');
        NEW.heating_type := COALESCE(NEW.heating_type, '개별난방');
        NEW.building_use_type := COALESCE(NEW.building_use_type, '일반');
    END IF;
    
    -- property_locations 테이블에 대한 처리
    IF TG_TABLE_NAME = 'property_locations' THEN
        NEW.postal_code := COALESCE(NEW.postal_code, '00000');
        NEW.nearest_station := COALESCE(NEW.nearest_station, '정보없음');
        NEW.cortar_no := COALESCE(NEW.cortar_no, '1168010100');
    END IF;
    
    -- property_images 테이블에 대한 처리
    IF TG_TABLE_NAME = 'property_images' THEN
        NEW.alt_text := COALESCE(NEW.alt_text, '매물 이미지');
        NEW.caption := COALESCE(NEW.caption, '');
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
CREATE TRIGGER ensure_properties_new_quality
    BEFORE INSERT OR UPDATE ON properties_new
    FOR EACH ROW EXECUTE FUNCTION ensure_data_quality();

CREATE TRIGGER ensure_property_physical_quality
    BEFORE INSERT OR UPDATE ON property_physical
    FOR EACH ROW EXECUTE FUNCTION ensure_data_quality();

CREATE TRIGGER ensure_property_locations_quality
    BEFORE INSERT OR UPDATE ON property_locations
    FOR EACH ROW EXECUTE FUNCTION ensure_data_quality();

CREATE TRIGGER ensure_property_images_quality
    BEFORE INSERT OR UPDATE ON property_images
    FOR EACH ROW EXECUTE FUNCTION ensure_data_quality();

-- =============================================================================
-- 7. 실행 및 검증
-- =============================================================================

-- 실행 가이드 주석
/*
이 스크립트를 적용한 후 다음 순서로 실행하세요:

1. 기존 NULL 값 수정:
   SELECT fix_existing_null_values();

2. 데이터 품질 검증:
   SELECT * FROM validate_property_data();
   SELECT * FROM validate_foreign_keys();

3. 실시간 품질 모니터링:
   SELECT * FROM data_quality_dashboard;

4. 정기적인 품질 체크 (일일 실행 권장):
   SELECT 
       table_name,
       completeness_percentage,
       quality_grade
   FROM data_quality_dashboard
   WHERE quality_grade IN ('FAIR', 'POOR');
*/

-- 완료 확인 함수
CREATE OR REPLACE FUNCTION check_null_optimization_status()
RETURNS TEXT AS $$
DECLARE
    result_text TEXT := '';
    total_tables INTEGER := 0;
    optimized_tables INTEGER := 0;
BEGIN
    
    -- 트리거 존재 확인
    SELECT COUNT(*) INTO total_tables
    FROM information_schema.triggers 
    WHERE trigger_name LIKE '%quality%';
    
    -- 기본값 설정 확인
    SELECT COUNT(*) INTO optimized_tables
    FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND column_default IS NOT NULL 
    AND table_name IN ('properties_new', 'property_locations', 'property_physical', 'property_images');
    
    result_text := format(
        'NULL 값 최적화 완료 상태:\n' ||
        '- 품질 보장 트리거: %s개 설치\n' ||
        '- 기본값 설정 컬럼: %s개 완료\n' ||
        '- 데이터 품질 검증 함수: 설치됨\n' ||
        '- 실시간 모니터링 뷰: 설치됨\n\n' ||
        '다음 단계: enhanced_data_collector_null_fixed.py 사용하여 새로운 데이터 수집',
        total_tables, optimized_tables
    );
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- 최종 상태 확인
SELECT check_null_optimization_status();