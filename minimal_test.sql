
-- 최소 테스트 SQL: 가장 기본적인 것만 테스트
-- 기존 테이블 확인
SELECT 'properties_new' as table_name, count(*) as record_count 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'properties_new';

-- 새 테이블 하나만 테스트 생성
CREATE TABLE IF NOT EXISTS test_property_tax_info (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT,
    total_tax INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 생성 확인
SELECT 'test_property_tax_info' as table_name, count(*) as record_count 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'test_property_tax_info';

-- 정리
DROP TABLE IF EXISTS test_property_tax_info;
