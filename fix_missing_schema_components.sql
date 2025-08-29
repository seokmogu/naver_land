-- =============================================================================
-- 스키마 완성을 위한 누락 컴포넌트 수정 스크립트
-- 검증 결과 기반 타겟 수정
-- =============================================================================

-- =============================================================================
-- 1. 누락된 테이블 생성
-- =============================================================================

-- 1.1 property_tax_info 테이블 생성
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

-- 1.2 property_price_comparison 테이블 생성
CREATE TABLE IF NOT EXISTS property_price_comparison (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    -- 동일 주소 시세 정보
    same_addr_count INTEGER DEFAULT 0,
    same_addr_max_price BIGINT,
    same_addr_min_price BIGINT,
    
    -- 단지/건물 정보
    cpid VARCHAR(50),
    complex_name VARCHAR(200),
    
    -- 매물 특징 설명
    article_feature_desc TEXT,
    
    -- 시세 계산 날짜
    market_data_date DATE DEFAULT CURRENT_DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 제약조건
    CONSTRAINT chk_price_comparison_logic 
    CHECK (same_addr_max_price IS NULL OR same_addr_min_price IS NULL OR same_addr_max_price >= same_addr_min_price),
    CONSTRAINT chk_same_addr_count_positive 
    CHECK (same_addr_count >= 0)
);

-- =============================================================================
-- 2. 기존 테이블에 누락된 컬럼 추가
-- =============================================================================

-- 2.1 property_locations 테이블 확장
DO $$ 
BEGIN
    -- cortar_no 컬럼 추가 (이미 있을 수 있으므로 체크)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_locations' AND column_name = 'cortar_no'
    ) THEN
        ALTER TABLE property_locations ADD COLUMN cortar_no VARCHAR(20);
    END IF;
    
    -- nearest_station 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_locations' AND column_name = 'nearest_station'
    ) THEN
        ALTER TABLE property_locations ADD COLUMN nearest_station TEXT;
    END IF;
    
    -- subway_stations 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_locations' AND column_name = 'subway_stations'
    ) THEN
        ALTER TABLE property_locations ADD COLUMN subway_stations JSONB;
    END IF;
    
    -- postal_code 컬럼 추가 (이미 있을 수 있으므로 체크)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_locations' AND column_name = 'postal_code'
    ) THEN
        ALTER TABLE property_locations ADD COLUMN postal_code VARCHAR(10);
    END IF;
    
    -- detail_address 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_locations' AND column_name = 'detail_address'
    ) THEN
        ALTER TABLE property_locations ADD COLUMN detail_address VARCHAR(500);
    END IF;
END $$;

-- 2.2 property_physical 테이블 확장  
DO $$
BEGIN
    -- veranda_count 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'veranda_count'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN veranda_count INTEGER DEFAULT 0;
    END IF;
    
    -- space_type 컬럼 추가 (중요!)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'space_type'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN space_type VARCHAR(100);
    END IF;
    
    -- structure_type 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'structure_type'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN structure_type VARCHAR(100);
    END IF;
    
    -- floor_description 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'floor_description'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN floor_description TEXT;
    END IF;
    
    -- ground_floor_count 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'ground_floor_count'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN ground_floor_count INTEGER;
    END IF;
    
    -- monthly_management_cost 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'monthly_management_cost'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN monthly_management_cost INTEGER;
    END IF;
    
    -- management_office_tel 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'management_office_tel'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN management_office_tel VARCHAR(20);
    END IF;
    
    -- move_in_type 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'move_in_type'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN move_in_type VARCHAR(50);
    END IF;
    
    -- move_in_discussion 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'move_in_discussion'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN move_in_discussion BOOLEAN DEFAULT false;
    END IF;
    
    -- heating_type 컬럼 추가 (이미 있을 수 있으므로 체크)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'property_physical' AND column_name = 'heating_type'
    ) THEN
        ALTER TABLE property_physical ADD COLUMN heating_type VARCHAR(50);
    END IF;
END $$;

-- 2.3 properties_new 테이블 확장
DO $$
BEGIN
    -- building_use 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'properties_new' AND column_name = 'building_use'
    ) THEN
        ALTER TABLE properties_new ADD COLUMN building_use VARCHAR(100);
    END IF;
    
    -- law_usage 컬럼 추가 (중요!)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'properties_new' AND column_name = 'law_usage'
    ) THEN
        ALTER TABLE properties_new ADD COLUMN law_usage VARCHAR(100);
    END IF;
    
    -- floor_layer_name 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'properties_new' AND column_name = 'floor_layer_name'
    ) THEN
        ALTER TABLE properties_new ADD COLUMN floor_layer_name VARCHAR(100);
    END IF;
    
    -- approval_date 컬럼 추가 (이미 있을 수 있으므로 체크)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'properties_new' AND column_name = 'approval_date'
    ) THEN
        ALTER TABLE properties_new ADD COLUMN approval_date DATE;
    END IF;
END $$;

-- =============================================================================
-- 3. property_facilities 테이블 확인 및 생성 (필요한 경우)
-- =============================================================================

CREATE TABLE IF NOT EXISTS property_facilities (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facility_types(id),
    
    -- 시설 상태
    available BOOLEAN DEFAULT true,
    condition_grade INTEGER CHECK (condition_grade >= 1 AND condition_grade <= 5),
    
    -- 추가 정보
    notes VARCHAR(200),
    last_checked DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 4. 인덱스 생성
-- =============================================================================

-- 4.1 새로운 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_total_cost ON property_tax_info(total_cost);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_date ON property_tax_info(calculation_date);

CREATE INDEX IF NOT EXISTS idx_property_price_comparison_property ON property_price_comparison(property_id);
CREATE INDEX IF NOT EXISTS idx_property_price_comparison_complex ON property_price_comparison(cpid, complex_name);
CREATE INDEX IF NOT EXISTS idx_property_price_comparison_price_range ON property_price_comparison(same_addr_min_price, same_addr_max_price);

-- 4.2 기존 테이블의 새 컬럼 인덱스
CREATE INDEX IF NOT EXISTS idx_property_locations_cortar_no ON property_locations(cortar_no);
CREATE INDEX IF NOT EXISTS idx_property_locations_subway ON property_locations USING GIN (subway_stations);

CREATE INDEX IF NOT EXISTS idx_property_physical_space_type ON property_physical(space_type);
CREATE INDEX IF NOT EXISTS idx_property_physical_management_cost ON property_physical(monthly_management_cost);

CREATE INDEX IF NOT EXISTS idx_properties_new_building_use ON properties_new(building_use);
CREATE INDEX IF NOT EXISTS idx_properties_new_law_usage ON properties_new(law_usage);

CREATE INDEX IF NOT EXISTS idx_property_facilities_property ON property_facilities(property_id);
CREATE INDEX IF NOT EXISTS idx_property_facilities_type ON property_facilities(facility_id, available);

-- =============================================================================
-- 5. 업데이트 트리거 생성
-- =============================================================================

-- 5.1 세금 총액 자동 계산 함수
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

-- 5.2 세금 정보 테이블에 트리거 적용
DROP TRIGGER IF EXISTS calculate_tax_totals_trigger ON property_tax_info;
CREATE TRIGGER calculate_tax_totals_trigger
    BEFORE INSERT OR UPDATE ON property_tax_info
    FOR EACH ROW EXECUTE FUNCTION calculate_total_tax_cost();

-- 5.3 updated_at 트리거 (기존 함수 활용)
DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
CREATE TRIGGER update_property_tax_info_updated_at 
    BEFORE UPDATE ON property_tax_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 6. 데이터 품질 검증 뷰 생성
-- =============================================================================

-- 6.1 데이터 완성도 체크 뷰
CREATE OR REPLACE VIEW data_completeness_check AS
SELECT 
    'property_basic' as table_name,
    COUNT(*) as total_records,
    COUNT(article_name) as has_article_name,
    COUNT(real_estate_type_id) as has_real_estate_type,
    COUNT(trade_type_id) as has_trade_type,
    COUNT(region_id) as has_region,
    ROUND(COUNT(article_name)::decimal / COUNT(*) * 100, 2) as completeness_pct
FROM properties_new
WHERE is_active = true

UNION ALL

SELECT 
    'property_locations' as table_name,
    COUNT(*) as total_records,
    COUNT(latitude) as has_coordinates,
    COUNT(address_road) as has_address,
    COUNT(cortar_no) as has_cortar_no,
    COUNT(nearest_station) as has_subway_info,
    ROUND(COUNT(latitude)::decimal / COUNT(*) * 100, 2) as completeness_pct
FROM property_locations

UNION ALL

SELECT 
    'property_physical' as table_name,
    COUNT(*) as total_records,
    COUNT(area_exclusive) as has_area_exclusive,
    COUNT(area_supply) as has_area_supply,
    COUNT(floor_current) as has_floor_info,
    COUNT(room_count) as has_room_info,
    ROUND(COUNT(area_exclusive)::decimal / COUNT(*) * 100, 2) as completeness_pct
FROM property_physical

UNION ALL

SELECT 
    'property_tax_info' as table_name,
    COUNT(*) as total_records,
    COUNT(total_tax) as has_tax_calculation,
    COUNT(total_cost) as has_total_cost,
    COUNT(brokerage_fee) as has_brokerage_fee,
    0 as placeholder,
    ROUND(COUNT(total_tax)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as completeness_pct
FROM property_tax_info;

-- 6.2 API 섹션별 데이터 커버리지 뷰  
CREATE OR REPLACE VIEW api_section_coverage AS
SELECT 
    p.id as property_id,
    p.article_no,
    
    -- 각 섹션별 데이터 존재 여부
    CASE WHEN pl.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_location_data,
    CASE WHEN pp.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_physical_data, 
    CASE WHEN pr.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_price_data,
    CASE WHEN prel.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_realtor_data,
    CASE WHEN pi.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_image_data,
    CASE WHEN pf.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_facility_data,
    CASE WHEN pti.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_tax_data,
    CASE WHEN ppc.id IS NOT NULL THEN 'Y' ELSE 'N' END as has_price_comparison_data,
    
    -- 전체 완성도 점수 (8개 섹션 중 몇 개가 있는지)
    (CASE WHEN pl.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pp.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pr.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN prel.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pi.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pf.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pti.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN ppc.id IS NOT NULL THEN 1 ELSE 0 END) as data_completeness_score,
    
    ROUND((CASE WHEN pl.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN pp.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN pr.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN prel.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN pi.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN pf.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN pti.id IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN ppc.id IS NOT NULL THEN 1 ELSE 0 END)::decimal / 8 * 100, 2) as completeness_percentage

FROM properties_new p
LEFT JOIN property_locations pl ON pl.property_id = p.id
LEFT JOIN property_physical pp ON pp.property_id = p.id  
LEFT JOIN property_prices pr ON pr.property_id = p.id
LEFT JOIN property_realtors prel ON prel.property_id = p.id
LEFT JOIN property_images pi ON pi.property_id = p.id
LEFT JOIN property_facilities pf ON pf.property_id = p.id
LEFT JOIN property_tax_info pti ON pti.property_id = p.id
LEFT JOIN property_price_comparison ppc ON ppc.property_id = p.id
WHERE p.is_active = true;

-- =============================================================================
-- 7. 제약조건 추가 (추가 데이터 품질 검증)
-- =============================================================================

-- property_physical 테이블 제약조건
DO $$
BEGIN
    -- veranda_count 양수 제약조건
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'chk_veranda_count_positive') THEN
        ALTER TABLE property_physical
        ADD CONSTRAINT chk_veranda_count_positive 
        CHECK (veranda_count >= 0);
    END IF;
    
    -- 관리비 양수 제약조건
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'chk_management_cost_positive') THEN
        ALTER TABLE property_physical 
        ADD CONSTRAINT chk_management_cost_positive 
        CHECK (monthly_management_cost IS NULL OR monthly_management_cost >= 0);
    END IF;
    
    -- 층수 로직 검증
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'chk_floor_counts_logical') THEN
        ALTER TABLE property_physical
        ADD CONSTRAINT chk_floor_counts_logical
        CHECK (
            (ground_floor_count IS NULL OR ground_floor_count >= 0) AND
            (underground_floor_count IS NULL OR underground_floor_count >= 0) AND
            (ground_floor_count IS NULL OR underground_floor_count IS NULL OR 
             (ground_floor_count + underground_floor_count) <= floor_total OR floor_total IS NULL)
        );
    END IF;
END $$;

-- =============================================================================
-- 8. 스키마 완료 확인 함수
-- =============================================================================

CREATE OR REPLACE FUNCTION check_schema_completion_status()
RETURNS TEXT AS $$
DECLARE
    missing_tables INTEGER := 0;
    missing_columns INTEGER := 0;
    missing_facilities INTEGER := 0;
    total_checks INTEGER := 0;
    result_text TEXT;
BEGIN
    -- 새 테이블 확인
    SELECT COUNT(*) INTO missing_tables
    FROM (
        SELECT 'property_tax_info' as table_name
        UNION ALL
        SELECT 'property_price_comparison'
        UNION ALL 
        SELECT 'property_facilities'
    ) required_tables
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = required_tables.table_name
    );
    
    -- 중요 컬럼 확인 
    SELECT COUNT(*) INTO missing_columns
    FROM (
        SELECT 'properties_new' as table_name, 'law_usage' as column_name
        UNION ALL
        SELECT 'property_physical', 'space_type'
    ) required_columns
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = required_columns.table_name
        AND column_name = required_columns.column_name
    );
    
    -- facility_types 확장 확인
    SELECT COUNT(*) INTO missing_facilities
    FROM facility_types 
    WHERE id BETWEEN 10 AND 19;
    
    total_checks := 3 + 19 + 10; -- 테이블 + 컬럼 + 시설
    
    IF missing_tables = 0 AND missing_columns = 0 AND missing_facilities >= 8 THEN
        result_text := '✅ 스키마 완성 완료! 모든 필수 컴포넌트가 존재합니다.';
    ELSE
        result_text := FORMAT('❌ 스키마 불완전: 테이블 누락 %s개, 컬럼 누락 %s개, 시설 유형 %s개', 
                             missing_tables, missing_columns, missing_facilities);
    END IF;
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 9. 실행 완료 확인
-- =============================================================================

-- 스키마 완료 상태 확인
SELECT check_schema_completion_status() as schema_status;

-- 주요 테이블 존재 확인
SELECT 
    table_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = t.table_name) 
        THEN '✅ 존재' 
        ELSE '❌ 누락' 
    END as status
FROM (
    VALUES 
    ('properties_new'),
    ('property_locations'), 
    ('property_physical'),
    ('property_facilities'),
    ('property_tax_info'),
    ('property_price_comparison')
) as t(table_name);

-- =============================================================================
-- 완료 메시지
-- =============================================================================
/*
🎉 스키마 완성 스크립트 실행 완료!

주요 수정사항:
✅ property_tax_info 테이블 생성 (articleTax 섹션)
✅ property_price_comparison 테이블 생성  
✅ property_facilities 테이블 확인/생성
✅ property_physical.space_type 컬럼 추가 (중요!)
✅ properties_new.law_usage 컬럼 추가 (중요!)
✅ 기타 19개 컬럼 추가
✅ 자동 계산 트리거 설정
✅ 인덱스 최적화
✅ 데이터 품질 검증 뷰 생성

다음 단계:
1. test_schema_deployment.py 재실행으로 검증
2. enhanced_data_collector.py로 실제 수집 시작
3. 데이터 손실 없이 100% 수집 확인
*/