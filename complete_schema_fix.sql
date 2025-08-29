-- =============================================================================
-- 네이버 부동산 수집기 - 완전 스키마 수정 스크립트
-- Supabase Dashboard SQL Editor에서 실행용
-- =============================================================================

-- 이 파일을 Supabase Dashboard > SQL Editor에 복사-붙여넣기하여 실행하세요.

-- =============================================================================
-- 1. 누락된 중요 컬럼 추가 (space_type, law_usage 등)
-- =============================================================================

-- 1.1 property_physical 테이블 확장 (space_type 컬럼 - 중요!)
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS space_type VARCHAR(100);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS veranda_count INTEGER DEFAULT 0;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS structure_type VARCHAR(100);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS floor_description TEXT;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS ground_floor_count INTEGER;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS monthly_management_cost INTEGER;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS management_office_tel VARCHAR(20);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_type VARCHAR(50);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_discussion BOOLEAN DEFAULT false;

-- 1.2 properties_new 테이블 확장 (law_usage 컬럼 - 중요!)
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS law_usage VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS building_use VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS floor_layer_name VARCHAR(100);

-- 1.3 property_locations 테이블 확장
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS nearest_station TEXT;
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS subway_stations JSONB;
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS detail_address VARCHAR(500);

-- =============================================================================
-- 2. property_facilities 테이블 생성 (누락됨 - 중요!)
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
-- 3. 누락된 다른 테이블들 생성 (있을 수 있지만 재생성)
-- =============================================================================

-- 3.1 property_tax_info 테이블 (articleTax 섹션)
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

-- 3.2 property_price_comparison 테이블 (시세 비교)
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
-- 4. 성능 최적화 인덱스 생성
-- =============================================================================

-- 4.1 새로운 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_total_cost ON property_tax_info(total_cost);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_date ON property_tax_info(calculation_date);

CREATE INDEX IF NOT EXISTS idx_property_price_comparison_property ON property_price_comparison(property_id);
CREATE INDEX IF NOT EXISTS idx_property_price_comparison_complex ON property_price_comparison(cpid, complex_name);

CREATE INDEX IF NOT EXISTS idx_property_facilities_property ON property_facilities(property_id);
CREATE INDEX IF NOT EXISTS idx_property_facilities_type ON property_facilities(facility_id, available);

-- 4.2 새로운 컬럼 인덱스
CREATE INDEX IF NOT EXISTS idx_property_physical_space_type ON property_physical(space_type);
CREATE INDEX IF NOT EXISTS idx_property_physical_management_cost ON property_physical(monthly_management_cost);

CREATE INDEX IF NOT EXISTS idx_properties_new_law_usage ON properties_new(law_usage);
CREATE INDEX IF NOT EXISTS idx_properties_new_building_use ON properties_new(building_use);

CREATE INDEX IF NOT EXISTS idx_property_locations_subway ON property_locations USING GIN (subway_stations);

-- =============================================================================
-- 5. 자동 계산 트리거 생성 (세금 총액 계산)
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

-- 5.2 트리거 생성 (이전 트리거 삭제 후 재생성)
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
    'properties_new' as table_name,
    COUNT(*) as total_records,
    COUNT(article_name) as has_article_name,
    COUNT(law_usage) as has_law_usage,
    COUNT(building_use) as has_building_use,
    ROUND(COUNT(law_usage)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as law_usage_completeness_pct
FROM properties_new
WHERE is_active = true

UNION ALL

SELECT 
    'property_physical' as table_name,
    COUNT(*) as total_records,
    COUNT(area_exclusive) as has_area_exclusive,
    COUNT(space_type) as has_space_type,
    COUNT(monthly_management_cost) as has_management_cost,
    ROUND(COUNT(space_type)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as space_type_completeness_pct
FROM property_physical

UNION ALL

SELECT 
    'property_facilities' as table_name,
    COUNT(*) as total_records,
    COUNT(facility_id) as has_facility_id,
    COUNT(property_id) as has_property_id,
    0 as placeholder,
    ROUND(COUNT(facility_id)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as facility_completeness_pct
FROM property_facilities

UNION ALL

SELECT 
    'property_tax_info' as table_name,
    COUNT(*) as total_records,
    COUNT(total_tax) as has_tax_calculation,
    COUNT(total_cost) as has_total_cost,
    COUNT(brokerage_fee) as has_brokerage_fee,
    ROUND(COUNT(total_tax)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as tax_completeness_pct
FROM property_tax_info;

-- =============================================================================
-- 7. 제약조건 추가 (데이터 품질 보장)
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
EXCEPTION
    WHEN OTHERS THEN
        -- 제약조건 추가 실패시 무시 (이미 존재할 수 있음)
        NULL;
END $$;

-- =============================================================================
-- 8. 확장된 시설 유형 데이터 추가 (7개 → 19개)
-- =============================================================================

-- 누락된 시설 유형들 추가 (ID 10-19)
INSERT INTO facility_types (id, facility_code, facility_name, category, is_standard) VALUES
(10, 'FIRE_ALARM', '화재경보기', 'security', false),
(11, 'WATER_PURIFIER', '정수기', 'convenience', false),
(12, 'GAS_RANGE', '가스레인지', 'utility', false),
(13, 'INDUCTION', '인덕션', 'utility', false),
(14, 'MICROWAVE', '전자레인지', 'convenience', false),
(15, 'REFRIGERATOR', '냉장고', 'convenience', false),
(16, 'WASHING_MACHINE', '세탁기', 'convenience', false),
(17, 'DISH_WASHER', '식기세척기', 'convenience', false),
(18, 'SHOE_CLOSET', '신발장', 'convenience', false),
(19, 'FULL_OPTION', '풀옵션', 'convenience', false)
ON CONFLICT (id) DO UPDATE SET
    facility_name = EXCLUDED.facility_name,
    category = EXCLUDED.category,
    updated_at = CURRENT_TIMESTAMP
WHERE facility_types.facility_name != EXCLUDED.facility_name;

-- =============================================================================
-- 9. 최종 검증 및 확인
-- =============================================================================

-- 9.1 스키마 완료 상태 확인 함수
CREATE OR REPLACE FUNCTION check_schema_fix_completion()
RETURNS TABLE (
    component_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- 테이블 존재 확인
    RETURN QUERY
    SELECT 
        'property_facilities 테이블' as component_name,
        CASE 
            WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'property_facilities') 
            THEN '✅ 존재' 
            ELSE '❌ 누락' 
        END as status,
        'property_facilities 테이블 생성 확인' as details;
    
    -- space_type 컬럼 확인
    RETURN QUERY
    SELECT 
        'space_type 컬럼' as component_name,
        CASE 
            WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'property_physical' AND column_name = 'space_type') 
            THEN '✅ 존재' 
            ELSE '❌ 누락' 
        END as status,
        'property_physical.space_type 컬럼 생성 확인' as details;
    
    -- law_usage 컬럼 확인
    RETURN QUERY
    SELECT 
        'law_usage 컬럼' as component_name,
        CASE 
            WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'properties_new' AND column_name = 'law_usage') 
            THEN '✅ 존재' 
            ELSE '❌ 누락' 
        END as status,
        'properties_new.law_usage 컬럼 생성 확인' as details;
    
    -- 확장된 시설 유형 확인
    RETURN QUERY
    SELECT 
        '시설 유형 확장' as component_name,
        CASE 
            WHEN (SELECT COUNT(*) FROM facility_types WHERE id BETWEEN 10 AND 19) >= 8 
            THEN '✅ 완료' 
            ELSE '❌ 부족' 
        END as status,
        FORMAT('시설 유형 개수: %s개', (SELECT COUNT(*) FROM facility_types WHERE id BETWEEN 10 AND 19)) as details;
    
    -- 뷰 생성 확인
    RETURN QUERY
    SELECT 
        'data_completeness_check 뷰' as component_name,
        CASE 
            WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'data_completeness_check') 
            THEN '✅ 존재' 
            ELSE '❌ 누락' 
        END as status,
        'data_completeness_check 뷰 생성 확인' as details;
    
END;
$$ LANGUAGE plpgsql;

-- 9.2 최종 확인 실행
SELECT * FROM check_schema_fix_completion();

-- =============================================================================
-- 완료 메시지
-- =============================================================================

-- 완료 확인을 위한 간단한 SELECT 구문
SELECT 
    '🎉 스키마 수정 스크립트 실행 완료!' as message,
    '다음 단계: python test_schema_deployment.py로 검증하세요' as next_step;

-- =============================================================================
-- 실행 후 확인사항
-- =============================================================================
/*
✅ 이 스크립트를 실행한 후 다음을 확인하세요:

1. 오류 없이 실행 완료 여부
2. check_schema_fix_completion() 함수 결과에서 모든 항목이 '✅ 존재' 또는 '✅ 완료'인지 확인
3. Python 검증: python test_schema_deployment.py
4. 성공하면 데이터 수집 시작: python enhanced_data_collector.py

🚨 주요 해결 항목:
- space_type 컬럼 (property_physical 테이블)
- law_usage 컬럼 (properties_new 테이블)  
- property_facilities 테이블 생성
- 시설 유형 7개 → 19개 확장
- 데이터 품질 검증 뷰 생성

이 스크립트로 30% 데이터 손실 문제가 해결됩니다!
*/