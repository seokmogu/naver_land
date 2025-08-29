-- 카카오 API 통합을 위한 컬럼 추가
-- property_locations 테이블 확장

-- 1. 카카오 API 응답 저장용 컬럼들
ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS kakao_road_address TEXT;

ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS kakao_jibun_address TEXT;

ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS kakao_building_name VARCHAR(200);

ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS kakao_zone_no VARCHAR(10);

ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS kakao_api_response JSONB;

ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS address_enriched BOOLEAN DEFAULT false;

-- 2. 성능 향상을 위한 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_property_locations_enriched 
ON property_locations(address_enriched) WHERE address_enriched = true;

CREATE INDEX IF NOT EXISTS idx_property_locations_kakao_building 
ON property_locations(kakao_building_name) WHERE kakao_building_name IS NOT NULL;

-- 3. 카카오 API 응답 JSONB 인덱스 (검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_property_locations_kakao_response 
ON property_locations USING GIN(kakao_api_response) WHERE kakao_api_response IS NOT NULL;

-- 4. 컬럼 추가 확인 쿼리
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'property_locations' 
  AND column_name LIKE 'kakao%' OR column_name = 'address_enriched'
ORDER BY column_name;

-- 5. 테이블 크기 및 통계 업데이트
ANALYZE property_locations;

COMMENT ON COLUMN property_locations.kakao_road_address IS '카카오 API 도로명 주소';
COMMENT ON COLUMN property_locations.kakao_jibun_address IS '카카오 API 지번 주소';  
COMMENT ON COLUMN property_locations.kakao_building_name IS '카카오 API 건물명';
COMMENT ON COLUMN property_locations.kakao_zone_no IS '카카오 API 우편번호';
COMMENT ON COLUMN property_locations.kakao_api_response IS '카카오 API 전체 응답 (JSONB)';
COMMENT ON COLUMN property_locations.address_enriched IS '주소 정보 보강 여부';