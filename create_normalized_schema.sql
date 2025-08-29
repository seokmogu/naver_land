-- 정규화된 데이터베이스 스키마 생성 스크립트
-- 네이버 부동산 수집기 v2.0

-- =============================================================================
-- 참조 테이블 생성 (Reference Tables)
-- =============================================================================

-- 1. 부동산 유형 테이블
CREATE TABLE real_estate_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(10) UNIQUE NOT NULL,
    type_name VARCHAR(50) NOT NULL,
    category VARCHAR(30), -- 'residential', 'commercial', 'mixed', 'industrial'
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 데이터 삽입
INSERT INTO real_estate_types (type_code, type_name, category) VALUES
('APT', '아파트', 'residential'),
('OT', '오피스텔', 'mixed'),
('SG', '상가', 'commercial'),
('SMS', '사무실', 'commercial'),
('GJCG', '단독주택', 'residential'),
('APTHGJ', '아파트형 공장', 'industrial'),
('GM', '건물', 'commercial'),
('TJ', '토지', 'land');

-- 2. 거래 유형 테이블
CREATE TABLE trade_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(10) UNIQUE NOT NULL,
    type_name VARCHAR(50) NOT NULL,
    description TEXT,
    requires_deposit BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 데이터 삽입
INSERT INTO trade_types (type_code, type_name, requires_deposit) VALUES
('A1', '매매', false),
('B1', '전세', true),
('B2', '월세', true),
('B3', '단기임대', true);

-- 3. 지역 정보 테이블 (기존 areas 테이블 확장)
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    cortar_no VARCHAR(20) UNIQUE NOT NULL,
    dong_name VARCHAR(100) NOT NULL,
    gu_name VARCHAR(50) NOT NULL,
    city_name VARCHAR(50) NOT NULL DEFAULT '서울특별시',
    
    -- 지리 정보
    center_lat DECIMAL(10, 8),
    center_lon DECIMAL(11, 8),
    area DECIMAL(15, 2), -- 면적 (㎢)
    
    -- 인구 및 경제 정보 (향후 확장)
    population INTEGER,
    household_count INTEGER,
    average_income BIGINT,
    
    -- 부동산 통계 (실시간 업데이트)
    total_property_count INTEGER DEFAULT 0,
    active_property_count INTEGER DEFAULT 0,
    average_sale_price BIGINT,
    average_rent_price BIGINT,
    
    -- 메타데이터
    is_active BOOLEAN DEFAULT true,
    last_updated DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기존 areas 테이블에서 데이터 마이그레이션
INSERT INTO regions (cortar_no, dong_name, gu_name, center_lat, center_lon, created_at)
SELECT 
    cortar_no,
    dong_name,
    COALESCE(
        CASE 
            WHEN dong_name LIKE '%강남%' THEN '강남구'
            WHEN dong_name LIKE '%서초%' THEN '서초구'
            WHEN dong_name LIKE '%송파%' THEN '송파구'
            WHEN dong_name LIKE '%강동%' THEN '강동구'
            ELSE '강남구' -- 기본값
        END, '강남구'
    ) as gu_name,
    center_lat,
    center_lon,
    CURRENT_TIMESTAMP
FROM areas
ON CONFLICT (cortar_no) DO NOTHING;

-- 4. 시설 유형 테이블
CREATE TABLE facility_types (
    id SERIAL PRIMARY KEY,
    facility_code VARCHAR(20) UNIQUE NOT NULL,
    facility_name VARCHAR(100) NOT NULL,
    category VARCHAR(50), -- 'security', 'convenience', 'exercise', 'parking', 'utility'
    description TEXT,
    is_standard BOOLEAN DEFAULT false, -- 기본 시설 여부
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 시설 유형 데이터
INSERT INTO facility_types (facility_code, facility_name, category, is_standard) VALUES
-- 기본 시설
('ELEVATOR', '엘리베이터', 'convenience', true),
('PARKING', '주차장', 'parking', true),
('HEATING', '난방시설', 'utility', true),

-- 보안 시설
('SECURITY', '경비실', 'security', false),
('CCTV', 'CCTV', 'security', false),
('INTERCOM', '인터폰', 'security', false),
('CARD_KEY', '카드키', 'security', false),

-- 편의 시설
('AIR_CON', '에어컨', 'convenience', false),
('INTERNET', '인터넷', 'convenience', false),
('CABLE_TV', 'TV/케이블', 'convenience', false),
('WATER_PURIFIER', '정수기', 'convenience', false),

-- 운동 시설
('GYM', '헬스장', 'exercise', false),
('POOL', '수영장', 'exercise', false),
('SAUNA', '사우나', 'exercise', false),

-- 편의점/상업시설
('CONVENIENCE_STORE', '편의점', 'commercial', false),
('RESTAURANT', '식당', 'commercial', false),
('CAFE', '카페', 'commercial', false);

-- =============================================================================
-- 핵심 데이터 테이블 생성
-- =============================================================================

-- 1. 매물 기본 정보 테이블 (정규화된)
CREATE TABLE properties_new (
    id BIGSERIAL PRIMARY KEY,
    article_no VARCHAR(50) UNIQUE NOT NULL,
    article_name VARCHAR(500),
    
    -- 외래키 참조
    real_estate_type_id INTEGER REFERENCES real_estate_types(id),
    trade_type_id INTEGER REFERENCES trade_types(id),
    region_id INTEGER REFERENCES regions(id),
    
    -- 기본 메타데이터
    collected_date DATE NOT NULL,
    last_seen_date DATE,
    is_active BOOLEAN DEFAULT true,
    
    -- 태그 및 설명 (간소화)
    tag_list JSONB,
    description TEXT,
    
    -- 시간 추적
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 가격 정보 테이블
CREATE TABLE property_prices (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    -- 가격 유형
    price_type VARCHAR(20) NOT NULL, -- 'sale', 'rent', 'deposit', 'maintenance'
    
    -- 가격 정보
    amount BIGINT NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    
    -- 유효 기간 (가격 변동 추적)
    valid_from DATE NOT NULL,
    valid_to DATE, -- NULL이면 현재 유효
    
    -- 메타데이터
    notes VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 위치 정보 테이블
CREATE TABLE property_locations (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    -- 좌표 정보
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- 주소 정보
    address_road VARCHAR(500),
    address_jibun VARCHAR(500),
    building_name VARCHAR(200),
    postal_code VARCHAR(10),
    cortar_no VARCHAR(20),
    
    -- 교통 정보
    walking_to_subway INTEGER, -- 지하철까지 도보 시간 (분)
    nearest_station VARCHAR(100),
    
    -- 지역 정보
    region_id INTEGER REFERENCES regions(id),
    
    -- 메타데이터
    address_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 물리적 정보 테이블
CREATE TABLE property_physical (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    -- 면적 정보
    area_exclusive DECIMAL(10, 2), -- 전용면적 (㎡)
    area_supply DECIMAL(10, 2),    -- 공급면적 (㎡)
    area_utilization_rate DECIMAL(5, 2), -- 전용률 (%)
    
    -- 층 정보
    floor_current INTEGER,    -- 해당 층
    floor_total INTEGER,      -- 총 층수
    floor_underground INTEGER, -- 지하층수
    
    -- 구조 정보
    room_count INTEGER,
    bathroom_count INTEGER,
    direction VARCHAR(20), -- 향 (남향, 남서향 등)
    
    -- 주차 정보
    parking_count INTEGER,
    parking_possible BOOLEAN DEFAULT false,
    
    -- 편의 시설
    elevator_available BOOLEAN DEFAULT false,
    
    -- 건물 정보
    heating_type VARCHAR(50),
    building_use_type VARCHAR(100), -- 법적 용도
    approval_date DATE, -- 사용승인일
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 중개사 정보 테이블
CREATE TABLE realtors (
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

-- 6. 매물-중개사 관계 테이블
CREATE TABLE property_realtors (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    realtor_id BIGINT REFERENCES realtors(id),
    
    -- 관계 정보
    listing_date DATE,
    listing_type VARCHAR(20) DEFAULT 'exclusive', -- 'exclusive', 'general', 'co_listing'
    is_primary BOOLEAN DEFAULT false, -- 주 중개사 여부
    commission_rate DECIMAL(5, 4), -- 중개 수수료율
    
    -- 연락처 (매물별로 다를 수 있음)
    contact_phone VARCHAR(20),
    contact_person VARCHAR(100),
    
    -- 메타데이터
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 이미지 정보 테이블
CREATE TABLE property_images (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    -- 이미지 기본 정보
    image_url TEXT NOT NULL,
    image_type VARCHAR(20) DEFAULT 'general', -- 'main', 'interior', 'exterior', 'floor_plan', 'view'
    image_order INTEGER DEFAULT 0,
    
    -- 이미지 메타데이터
    caption VARCHAR(500),
    alt_text VARCHAR(300),
    file_size INTEGER, -- bytes
    width INTEGER,
    height INTEGER,
    
    -- 이미지 품질 정보
    is_high_quality BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    
    -- 시간 정보
    captured_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 시설 정보 테이블
CREATE TABLE property_facilities (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facility_types(id),
    
    -- 시설 상태
    available BOOLEAN DEFAULT true,
    condition_grade INTEGER CHECK (condition_grade >= 1 AND condition_grade <= 5), -- 1-5 등급
    
    -- 추가 정보
    notes VARCHAR(200),
    last_checked DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 이력 및 통계 테이블
-- =============================================================================

-- 1. 가격 변동 이력 테이블 (기존 price_history 확장)
CREATE TABLE price_history_new (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id),
    
    -- 가격 변동 정보
    price_type VARCHAR(20) NOT NULL,
    previous_amount BIGINT,
    new_amount BIGINT,
    change_amount BIGINT,
    change_percent DECIMAL(8, 2),
    
    -- 월세 관련 (월세 매물의 경우)
    previous_rent_amount BIGINT,
    new_rent_amount BIGINT,
    rent_change_amount BIGINT,
    rent_change_percent DECIMAL(8, 2),
    
    -- 변동 원인 (향후 분석용)
    change_reason VARCHAR(100), -- 'market_change', 'property_improvement', 'seasonal'
    market_trend VARCHAR(20), -- 'up', 'down', 'stable'
    
    -- 메타데이터
    changed_date DATE NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 매물 삭제 이력 테이블 (기존 deletion_history 확장)
CREATE TABLE deletion_history_new (
    id BIGSERIAL PRIMARY KEY,
    
    -- 삭제된 매물 정보
    article_no VARCHAR(50) NOT NULL,
    property_snapshot JSONB, -- 삭제 시점의 매물 정보
    
    -- 삭제 정보
    deleted_date DATE NOT NULL,
    deletion_reason VARCHAR(50) DEFAULT 'not_found',
    days_active INTEGER, -- 매물이 활성 상태였던 기간
    
    -- 가격 정보 (삭제 시점)
    final_sale_price BIGINT,
    final_rent_price BIGINT,
    final_deposit BIGINT,
    
    -- 분류 정보
    real_estate_type VARCHAR(50),
    trade_type VARCHAR(50),
    region_cortar_no VARCHAR(20),
    region_id INTEGER REFERENCES regions(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 일별 통계 테이블 (기존 daily_stats 확장)
CREATE TABLE daily_stats_new (
    id BIGSERIAL PRIMARY KEY,
    
    -- 날짜 및 지역
    stat_date DATE NOT NULL,
    region_id INTEGER REFERENCES regions(id),
    cortar_no VARCHAR(20),
    
    -- 매물 수 통계
    total_count INTEGER DEFAULT 0,
    active_count INTEGER DEFAULT 0,
    new_count INTEGER DEFAULT 0,
    removed_count INTEGER DEFAULT 0,
    price_changed_count INTEGER DEFAULT 0,
    
    -- 가격 통계
    avg_sale_price BIGINT,
    median_sale_price BIGINT,
    min_sale_price BIGINT,
    max_sale_price BIGINT,
    
    avg_rent_price BIGINT,
    median_rent_price BIGINT,
    min_rent_price BIGINT,
    max_rent_price BIGINT,
    
    -- 면적 통계
    avg_area DECIMAL(8, 2),
    median_area DECIMAL(8, 2),
    min_area DECIMAL(8, 2),
    max_area DECIMAL(8, 2),
    
    -- 분포 정보 (JSONB)
    price_distribution JSONB,
    area_distribution JSONB,
    type_distribution JSONB,
    floor_distribution JSONB,
    
    -- 시장 분석 정보
    market_trend VARCHAR(20), -- 'bullish', 'bearish', 'stable'
    price_volatility DECIMAL(8, 4), -- 가격 변동성
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 인덱스 생성 (성능 최적화)
-- =============================================================================

-- 1. 매물 기본 테이블 인덱스
CREATE INDEX idx_properties_new_article_no ON properties_new(article_no);
CREATE INDEX idx_properties_new_active ON properties_new(is_active, last_seen_date);
CREATE INDEX idx_properties_new_region ON properties_new(region_id);
CREATE INDEX idx_properties_new_type ON properties_new(real_estate_type_id, trade_type_id);
CREATE INDEX idx_properties_new_date ON properties_new(collected_date, last_seen_date);

-- 복합 검색용 인덱스
CREATE INDEX idx_properties_new_search ON properties_new(region_id, real_estate_type_id, is_active);

-- 2. 가격 정보 인덱스
CREATE INDEX idx_property_prices_property ON property_prices(property_id, price_type);
CREATE INDEX idx_property_prices_amount ON property_prices(amount, price_type);
CREATE INDEX idx_property_prices_date ON property_prices(valid_from, valid_to);
CREATE INDEX idx_property_prices_current ON property_prices(property_id, price_type, valid_from) 
WHERE valid_to IS NULL;

-- 3. 위치 정보 인덱스 (공간 검색 최적화)
CREATE INDEX idx_property_locations_coords ON property_locations 
USING GIST (point(longitude, latitude));
CREATE INDEX idx_property_locations_region ON property_locations(region_id);
CREATE INDEX idx_property_locations_cortar ON property_locations(cortar_no);

-- 4. 물리적 정보 인덱스
CREATE INDEX idx_property_physical_area ON property_physical(area_exclusive);
CREATE INDEX idx_property_physical_floor ON property_physical(floor_current, floor_total);
CREATE INDEX idx_property_physical_rooms ON property_physical(room_count, bathroom_count);

-- 5. 중개사 관련 인덱스
CREATE INDEX idx_realtors_name ON realtors(realtor_name);
CREATE INDEX idx_realtors_business ON realtors(business_number);
CREATE INDEX idx_realtors_verified ON realtors(is_verified, rating);

CREATE INDEX idx_property_realtors_property ON property_realtors(property_id);
CREATE INDEX idx_property_realtors_realtor ON property_realtors(realtor_id);
CREATE INDEX idx_property_realtors_primary ON property_realtors(is_primary, listing_date);

-- 6. 이미지 관련 인덱스
CREATE INDEX idx_property_images_property ON property_images(property_id, image_type, image_order);
CREATE INDEX idx_property_images_type ON property_images(image_type, is_high_quality);

-- 7. 시설 정보 인덱스
CREATE INDEX idx_property_facilities_property ON property_facilities(property_id);
CREATE INDEX idx_property_facilities_type ON property_facilities(facility_id, available);

-- 8. 이력 테이블 인덱스
CREATE INDEX idx_price_history_new_property ON price_history_new(property_id, changed_date);
CREATE INDEX idx_price_history_new_trend ON price_history_new(changed_date, market_trend);

CREATE INDEX idx_deletion_history_new_date ON deletion_history_new(deleted_date);
CREATE INDEX idx_deletion_history_new_region ON deletion_history_new(region_id, deleted_date);

CREATE INDEX idx_daily_stats_new_date ON daily_stats_new(stat_date, region_id);
CREATE INDEX idx_daily_stats_new_region ON daily_stats_new(region_id, stat_date);

-- =============================================================================
-- 뷰 생성 (복잡한 조인 쿼리 최적화)
-- =============================================================================

-- 1. 매물 전체 정보 뷰 (가장 자주 사용되는 조인)
CREATE VIEW property_full_info AS
SELECT 
    p.*,
    ret.type_name as real_estate_type_name,
    ret.category as real_estate_category,
    tt.type_name as trade_type_name,
    r.dong_name, r.gu_name, r.city_name,
    
    -- 위치 정보
    pl.latitude, pl.longitude, pl.address_road, pl.address_jibun,
    pl.building_name, pl.postal_code, pl.walking_to_subway,
    
    -- 물리적 정보
    pp.area_exclusive, pp.area_supply, pp.floor_current, pp.floor_total,
    pp.room_count, pp.bathroom_count, pp.direction, pp.parking_count,
    pp.parking_possible, pp.elevator_available,
    
    -- 현재 가격 (최신 가격 정보)
    (SELECT amount FROM property_prices 
     WHERE property_id = p.id AND price_type = 'sale' 
     AND (valid_to IS NULL OR valid_to > CURRENT_DATE)
     ORDER BY valid_from DESC LIMIT 1) as current_sale_price,
     
    (SELECT amount FROM property_prices 
     WHERE property_id = p.id AND price_type = 'rent' 
     AND (valid_to IS NULL OR valid_to > CURRENT_DATE)
     ORDER BY valid_from DESC LIMIT 1) as current_rent_price,
     
    (SELECT amount FROM property_prices 
     WHERE property_id = p.id AND price_type = 'deposit' 
     AND (valid_to IS NULL OR valid_to > CURRENT_DATE)
     ORDER BY valid_from DESC LIMIT 1) as current_deposit,
     
    -- 중개사 정보 (주 중개사)
    (SELECT r.realtor_name FROM property_realtors pr 
     JOIN realtors r ON r.id = pr.realtor_id 
     WHERE pr.property_id = p.id AND pr.is_primary = true 
     LIMIT 1) as primary_realtor_name,
     
    (SELECT pr.contact_phone FROM property_realtors pr 
     WHERE pr.property_id = p.id AND pr.is_primary = true 
     LIMIT 1) as primary_contact_phone,
     
    -- 이미지 정보
    (SELECT image_url FROM property_images 
     WHERE property_id = p.id AND image_type = 'main' 
     ORDER BY image_order LIMIT 1) as main_image_url,
     
    (SELECT COUNT(*) FROM property_images 
     WHERE property_id = p.id) as total_images

FROM properties_new p
LEFT JOIN real_estate_types ret ON ret.id = p.real_estate_type_id
LEFT JOIN trade_types tt ON tt.id = p.trade_type_id
LEFT JOIN regions r ON r.id = p.region_id
LEFT JOIN property_locations pl ON pl.property_id = p.id
LEFT JOIN property_physical pp ON pp.property_id = p.id
WHERE p.is_active = true;

-- 2. 지역별 통계 뷰
CREATE VIEW region_stats AS
SELECT 
    r.*,
    COUNT(p.id) as total_properties,
    COUNT(CASE WHEN p.is_active = true THEN 1 END) as active_properties,
    
    -- 평균 가격 (현재 유효한 가격만)
    AVG(pp_sale.amount) as avg_sale_price,
    AVG(pp_rent.amount) as avg_rent_price,
    AVG(pp_deposit.amount) as avg_deposit,
    
    -- 면적 통계
    AVG(phy.area_exclusive) as avg_area,
    
    -- 최신 업데이트 시간
    MAX(p.updated_at) as last_property_update

FROM regions r
LEFT JOIN properties_new p ON p.region_id = r.id
LEFT JOIN property_prices pp_sale ON pp_sale.property_id = p.id 
    AND pp_sale.price_type = 'sale' 
    AND (pp_sale.valid_to IS NULL OR pp_sale.valid_to > CURRENT_DATE)
LEFT JOIN property_prices pp_rent ON pp_rent.property_id = p.id 
    AND pp_rent.price_type = 'rent'
    AND (pp_rent.valid_to IS NULL OR pp_rent.valid_to > CURRENT_DATE)
LEFT JOIN property_prices pp_deposit ON pp_deposit.property_id = p.id 
    AND pp_deposit.price_type = 'deposit'
    AND (pp_deposit.valid_to IS NULL OR pp_deposit.valid_to > CURRENT_DATE)
LEFT JOIN property_physical phy ON phy.property_id = p.id
GROUP BY r.id, r.cortar_no, r.dong_name, r.gu_name, r.city_name, 
         r.center_lat, r.center_lon, r.area, r.is_active;

-- =============================================================================
-- 제약조건 및 트리거 생성
-- =============================================================================

-- 1. 체크 제약조건
ALTER TABLE property_prices ADD CONSTRAINT chk_price_type 
CHECK (price_type IN ('sale', 'rent', 'deposit', 'maintenance', 'management'));

ALTER TABLE property_prices ADD CONSTRAINT chk_positive_amount 
CHECK (amount >= 0);

ALTER TABLE property_physical ADD CONSTRAINT chk_floor_logic 
CHECK (floor_current <= floor_total);

ALTER TABLE property_physical ADD CONSTRAINT chk_positive_area 
CHECK (area_exclusive > 0 AND area_supply > 0);

-- 2. 업데이트 트리거 (updated_at 자동 갱신)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_properties_updated_at 
    BEFORE UPDATE ON properties_new 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_realtors_updated_at 
    BEFORE UPDATE ON realtors 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regions_updated_at 
    BEFORE UPDATE ON regions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 권한 설정 (필요한 경우)
-- =============================================================================

-- 읽기 전용 사용자를 위한 뷰 권한 (선택적)
-- GRANT SELECT ON property_full_info TO readonly_user;
-- GRANT SELECT ON region_stats TO readonly_user;

-- =============================================================================
-- 완료 메시지
-- =============================================================================

-- 스키마 생성 완료 확인을 위한 함수
CREATE OR REPLACE FUNCTION check_schema_creation()
RETURNS TEXT AS $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name LIKE '%properties_new%' OR table_name LIKE '%property_%' OR table_name LIKE '%real_estate_%';
    
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND indexname LIKE 'idx_%';
    
    SELECT COUNT(*) INTO view_count 
    FROM information_schema.views 
    WHERE table_schema = 'public' 
    AND table_name IN ('property_full_info', 'region_stats');
    
    RETURN FORMAT('정규화된 스키마 생성 완료! 테이블: %s개, 인덱스: %s개, 뷰: %s개', 
                  table_count, index_count, view_count);
END;
$$ LANGUAGE plpgsql;

-- 스키마 생성 상태 확인
SELECT check_schema_creation();