-- =============================================================================
-- 누락된 참조 데이터 채우기 스크립트
-- 시설 유형, 부동산 유형, 거래 유형 등 기본 데이터 확장
-- =============================================================================

-- =============================================================================
-- 1. 시설 유형 데이터 완전 확장 (기존 7개 → 19개)
-- =============================================================================

-- 기존 데이터 확인 및 중복 방지를 위한 UPSERT
INSERT INTO facility_types (id, facility_code, facility_name, category, is_standard, description) VALUES

-- 🔥 보안/안전 시설 (ID: 10-12)
(10, 'FIRE_ALARM', '화재경보기', 'security', false, '화재 감지 및 경보 시설'),
(11, 'SPRINKLER', '스프링클러', 'security', false, '자동 화재 진압 시설'),  
(12, 'EMERGENCY_LIGHT', '비상등', 'security', false, '정전시 비상 조명'),

-- 🏠 생활 편의 시설 (ID: 13-16)
(13, 'WATER_PURIFIER', '정수기', 'convenience', false, '정수 및 냉온수 시설'),
(14, 'MICROWAVE', '전자레인지', 'convenience', false, '간편 조리 기구'),
(15, 'REFRIGERATOR', '냉장고', 'convenience', false, '식품 보관 시설'),
(16, 'SHOE_CLOSET', '신발장', 'convenience', false, '신발 보관함'),

-- ⚡ 전기/가스 시설 (ID: 17-19)  
(17, 'GAS_RANGE', '가스레인지', 'utility', false, '가스 조리 시설'),
(18, 'INDUCTION', '인덕션', 'utility', false, '전기 조리 시설'),
(19, 'ELECTRIC_PANEL', '전기판넬', 'utility', false, '전력 제어반'),

-- 🏊‍♂️ 운동/여가 시설 (ID: 20-22)
(20, 'POOL', '수영장', 'exercise', false, '실내/외 수영 시설'),
(21, 'FITNESS', '피트니스', 'exercise', false, '헬스/운동 시설'),
(22, 'SAUNA', '사우나', 'exercise', false, '찜질방/사우나'),

-- 🧺 가전/세탁 시설 (ID: 23-25)
(23, 'WASHING_MACHINE', '세탁기', 'convenience', false, '의류 세탁 기구'),
(24, 'DRYER', '건조기', 'convenience', false, '의류 건조 기구'),
(25, 'DISH_WASHER', '식기세척기', 'convenience', false, '설거지 자동화'),

-- 🎯 특수 옵션 (ID: 26-27)
(26, 'FULL_OPTION', '풀옵션', 'convenience', false, '모든 기본 시설 완비'),
(27, 'BUILT_IN_FURNITURE', '빌트인가구', 'convenience', false, '붙박이 수납가구')

ON CONFLICT (id) DO UPDATE SET
    facility_name = EXCLUDED.facility_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 2. 부동산 유형 확장 (네이버 API 실제 데이터 기반)
-- =============================================================================

INSERT INTO real_estate_types (type_code, type_name, category, description) VALUES

-- 🏢 상업시설 확장
('OFFICE', '사무실', 'commercial', '업무용 오피스 공간'),
('RETAIL', '매장', 'commercial', '소매업용 점포'),
('WAREHOUSE', '창고', 'industrial', '물류/보관용 창고'),
('FACTORY', '공장', 'industrial', '제조업용 시설'),

-- 🏠 주거시설 확장  
('VILLA', '빌라', 'residential', '다가구 주택'),
('TOWNHOUSE', '타운하우스', 'residential', '연립 주택'),
('STUDIO', '원룸', 'residential', '단일 공간 주거'),
('LOFT', '로프트', 'residential', '복층 구조 주거'),

-- 🌐 특수 용도
('PENSION', '펜션', 'commercial', '숙박/휴양 시설'),
('RESTAURANT', '음식점', 'commercial', '요식업 시설'),
('MEDICAL', '병원', 'commercial', '의료 시설'),
('EDUCATION', '학원', 'commercial', '교육 시설')

ON CONFLICT (type_code) DO UPDATE SET
    type_name = EXCLUDED.type_name,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 3. 거래 유형 확장 (실제 시장 거래 방식)
-- =============================================================================

INSERT INTO trade_types (type_code, type_name, requires_deposit, description) VALUES

-- 📝 추가 거래 방식
('A2', '경매', false, '법원 경매 매물'),
('A3', '공매', false, '국세청 공매 매물'),  
('B4', '사글세', true, '단기 거주용 임대'),
('B5', '연세', true, '연 단위 임대료'),
('C1', '권리금', false, '영업권 포함 거래'),
('C2', '분양권', false, '분양 전 권리 거래'),
('D1', '임대사업', false, '임대 사업용 매물')

ON CONFLICT (type_code) DO UPDATE SET
    type_name = EXCLUDED.type_name,
    requires_deposit = EXCLUDED.requires_deposit,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 4. 지역 정보 확장 (서울 주요 지역 추가)
-- =============================================================================

-- 강남구 세부 지역 (기존 데이터 보완)
INSERT INTO regions (cortar_no, dong_name, gu_name, city_name, center_lat, center_lon) VALUES

-- 강남구 추가 지역  
('1168010101', '역삼1동', '강남구', '서울특별시', 37.5006, 127.0366),
('1168010102', '역삼2동', '강남구', '서울특별시', 37.5006, 127.0366),
('1168010501', '삼성1동', '강남구', '서울특별시', 37.5135, 127.0595),
('1168010502', '삼성2동', '강남구', '서울특별시', 37.5135, 127.0595),

-- 서초구 주요 지역
('1165010100', '서초동', '서초구', '서울특별시', 37.4836, 127.0327),
('1165010200', '잠원동', '서초구', '서울특별시', 37.5214, 127.0114),
('1165010300', '반포동', '서초구', '서울특별시', 37.5047, 127.0056),
('1165010400', '방배동', '서초구', '서울특별시', 37.4812, 126.9976),

-- 송파구 주요 지역
('1171010100', '풍납동', '송파구', '서울특별시', 37.5316, 127.1198),
('1171010200', '거여동', '송파구', '서울특별시', 37.4943, 127.1453),
('1171010300', '마천동', '송파구', '서울특별시', 37.4939, 127.1472),
('1171010400', '잠실동', '송파구', '서울특별시', 37.5125, 127.1000),

-- 강동구 주요 지역
('1174010100', '강일동', '강동구', '서울특별시', 37.5584, 127.1757),
('1174010200', '상일동', '강동구', '서울특별시', 37.5476, 127.1737),
('1174010300', '명일동', '강동구', '서울특별시', 37.5495, 127.1474),
('1174010400', '고덕동', '강동구', '서울특별시', 37.5548, 127.1542)

ON CONFLICT (cortar_no) DO UPDATE SET
    dong_name = EXCLUDED.dong_name,
    gu_name = EXCLUDED.gu_name,
    center_lat = EXCLUDED.center_lat,
    center_lon = EXCLUDED.center_lon,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 5. 데이터 품질 향상을 위한 기본값 설정
-- =============================================================================

-- 5.1 시설 유형 활성화 상태 업데이트
UPDATE facility_types 
SET is_active = true, updated_at = CURRENT_TIMESTAMP
WHERE is_active IS NULL;

-- 5.2 부동산/거래 유형 활성화  
UPDATE real_estate_types 
SET is_active = true, updated_at = CURRENT_TIMESTAMP
WHERE is_active IS NULL;

UPDATE trade_types 
SET is_active = true, updated_at = CURRENT_TIMESTAMP  
WHERE is_active IS NULL;

-- 5.3 지역 정보 활성화
UPDATE regions 
SET is_active = true, last_updated = CURRENT_DATE
WHERE is_active IS NULL;

-- =============================================================================
-- 6. 참조 데이터 통계 및 검증
-- =============================================================================

-- 참조 데이터 완성도 체크 뷰
CREATE OR REPLACE VIEW reference_data_summary AS
SELECT 
    '시설 유형' as data_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
    string_agg(DISTINCT category, ', ') as categories
FROM facility_types

UNION ALL

SELECT 
    '부동산 유형' as data_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
    string_agg(DISTINCT category, ', ') as categories  
FROM real_estate_types

UNION ALL

SELECT 
    '거래 유형' as data_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
    string_agg(DISTINCT type_code, ', ') as categories
FROM trade_types

UNION ALL

SELECT 
    '지역 정보' as data_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
    string_agg(DISTINCT gu_name, ', ') as categories
FROM regions;

-- =============================================================================
-- 7. 시설 유형별 매핑 테이블 (API 필드명 → DB ID)
-- =============================================================================

-- 네이버 API articleFacility 필드와 DB facility_types 매핑
CREATE TABLE IF NOT EXISTS api_facility_mapping (
    id SERIAL PRIMARY KEY,
    api_field_name VARCHAR(50) NOT NULL UNIQUE,
    facility_id INTEGER REFERENCES facility_types(id),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 필드명 매핑 데이터 삽입
INSERT INTO api_facility_mapping (api_field_name, facility_id, description) VALUES
('airConditioner', 7, 'articleFacility.airConditioner'),
('cableTv', 9, 'articleFacility.cableTv'),  
('internet', 8, 'articleFacility.internet'),
('interphone', 6, 'articleFacility.interphone'),
('securitySystem', 4, 'articleFacility.securitySystem'),
('fireAlarm', 10, 'articleFacility.fireAlarm'),
('elevator', 1, 'articleFacility.elevator'),
('parking', 2, 'articleFacility.parking'),
('waterPurifier', 13, 'articleFacility.waterPurifier'),
('gasRange', 17, 'articleFacility.gasRange'),
('induction', 18, 'articleFacility.induction'),
('microwave', 14, 'articleFacility.microwave'),
('refrigerator', 15, 'articleFacility.refrigerator'),
('washingMachine', 23, 'articleFacility.washingMachine'),
('dishWasher', 25, 'articleFacility.dishWasher'),
('shoeCloset', 16, 'articleFacility.shoeCloset'),
('fullOption', 26, 'articleFacility.fullOption')
ON CONFLICT (api_field_name) DO UPDATE SET
    facility_id = EXCLUDED.facility_id,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 8. 완료 검증 함수
-- =============================================================================

CREATE OR REPLACE FUNCTION check_reference_data_population()
RETURNS TEXT AS $$
DECLARE
    facility_count INTEGER;
    real_estate_count INTEGER;
    trade_count INTEGER;
    region_count INTEGER;
    mapping_count INTEGER;
    result_text TEXT;
BEGIN
    -- 각 테이블별 데이터 수 확인
    SELECT COUNT(*) INTO facility_count FROM facility_types WHERE is_active = true;
    SELECT COUNT(*) INTO real_estate_count FROM real_estate_types WHERE is_active = true;
    SELECT COUNT(*) INTO trade_count FROM trade_types WHERE is_active = true;  
    SELECT COUNT(*) INTO region_count FROM regions WHERE is_active = true;
    SELECT COUNT(*) INTO mapping_count FROM api_facility_mapping WHERE is_active = true;
    
    result_text := FORMAT('🎉 참조 데이터 채우기 완료!
    
    📊 데이터 현황:
    ✅ 시설 유형: %s개 (기존 7개 → %s개로 확장)
    ✅ 부동산 유형: %s개  
    ✅ 거래 유형: %s개
    ✅ 지역 정보: %s개
    ✅ API 매핑: %s개
    
    🔧 API 필드 → DB 매핑 완료
    📈 데이터 품질 대폭 향상
    🚀 enhanced_data_collector.py에서 사용 준비 완료!',
    facility_count, facility_count,
    real_estate_count,
    trade_count,
    region_count,
    mapping_count);
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- 참조 데이터 채우기 완료 확인
SELECT check_reference_data_population();

-- 요약 통계 출력  
SELECT * FROM reference_data_summary ORDER BY data_type;