-- 사용하지 않는 테이블들 삭제 쿼리
-- 모두 레코드가 0개인 테이블들이므로 데이터 손실 없음

-- 1. 먼저 의존하는 VIEW들 삭제
DROP VIEW IF EXISTS property_full_info;
DROP VIEW IF EXISTS recent_properties;
DROP VIEW IF EXISTS area_current_stats;
DROP VIEW IF EXISTS property_lifecycle;

-- 2. CASCADE로 레거시 테이블들 삭제
DROP TABLE IF EXISTS properties CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS deletion_history CASCADE;
DROP TABLE IF EXISTS collection_logs CASCADE;
DROP TABLE IF EXISTS daily_stats CASCADE;

-- 3. 사용되지 않는 새 테이블들  
DROP TABLE IF EXISTS daily_stats_new CASCADE;

-- 4. 버그로 인해 사용되지 않는 관계 테이블들
DROP TABLE IF EXISTS property_facilities CASCADE;
DROP TABLE IF EXISTS property_realtors CASCADE;
DROP TABLE IF EXISTS realtors CASCADE;