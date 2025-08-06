-- 네이버 부동산 API 데이터베이스 스키마 개선
-- 작성일: 2025-01-20

-- 1. price_history 테이블 수정
-- 월세 추적 기능 추가 및 거래 타입 구분

ALTER TABLE price_history 
ADD COLUMN trade_type VARCHAR(10), -- 거래타입 (매매, 전세, 월세)
ADD COLUMN previous_rent_price INTEGER, -- 이전 월세
ADD COLUMN new_rent_price INTEGER, -- 새 월세  
ADD COLUMN rent_change_amount INTEGER, -- 월세 변동액
ADD COLUMN rent_change_percent DECIMAL(5,2); -- 월세 변동률

-- 기존 데이터 trade_type 업데이트 (매매/전세로 가정)
UPDATE price_history 
SET trade_type = '매매' 
WHERE trade_type IS NULL;

-- trade_type을 NOT NULL로 변경
ALTER TABLE price_history 
ALTER COLUMN trade_type SET NOT NULL;

-- price_history 테이블 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_price_history_trade_type ON price_history(trade_type);
CREATE INDEX IF NOT EXISTS idx_price_history_changed_date ON price_history(changed_date);

-- 2. properties 테이블 삭제 매물 추적 개선
-- 삭제 시점과 이유 추적을 위한 필드 추가

ALTER TABLE properties 
ADD COLUMN deleted_at TIMESTAMP, -- 삭제 시점
ADD COLUMN deletion_reason VARCHAR(50), -- 삭제 사유
ADD COLUMN last_seen_date DATE DEFAULT CURRENT_DATE; -- 마지막 확인일

-- 기존 비활성 매물에 대해 last_seen_date 설정
UPDATE properties 
SET last_seen_date = collected_date 
WHERE is_active = false AND last_seen_date IS NULL;

-- 활성 매물에 대해 last_seen_date를 오늘로 설정
UPDATE properties 
SET last_seen_date = CURRENT_DATE 
WHERE is_active = true;

-- last_seen_date를 NOT NULL로 변경
ALTER TABLE properties 
ALTER COLUMN last_seen_date SET NOT NULL;

-- 3. 삭제 이력 추적을 위한 새 테이블 생성
CREATE TABLE IF NOT EXISTS deletion_history (
    id SERIAL PRIMARY KEY,
    article_no VARCHAR NOT NULL,
    deleted_date DATE NOT NULL DEFAULT CURRENT_DATE,
    deletion_reason VARCHAR(50) DEFAULT 'not_found',
    days_active INTEGER, -- 매물이 활성 상태였던 일수
    final_price INTEGER, -- 삭제 시점의 마지막 가격
    final_rent_price INTEGER, -- 삭제 시점의 마지막 월세
    final_trade_type VARCHAR(10), -- 삭제 시점의 거래 타입
    cortar_no VARCHAR(10), -- 지역 코드
    real_estate_type VARCHAR(20), -- 부동산 타입
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 외래 키 제약조건 (선택사항 - 삭제된 매물이므로)
    CONSTRAINT fk_deletion_history_article 
        FOREIGN KEY (article_no) 
        REFERENCES properties(article_no) 
        ON DELETE CASCADE
);

-- deletion_history 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_deletion_history_article_no ON deletion_history(article_no);
CREATE INDEX IF NOT EXISTS idx_deletion_history_deleted_date ON deletion_history(deleted_date);
CREATE INDEX IF NOT EXISTS idx_deletion_history_cortar_no ON deletion_history(cortar_no);

-- 4. 매물 생명주기 추적을 위한 뷰 생성
CREATE OR REPLACE VIEW property_lifecycle AS
SELECT 
    p.article_no,
    p.article_name,
    p.cortar_no,
    p.real_estate_type,
    p.trade_type,
    p.price,
    p.rent_price,
    p.is_active,
    p.collected_date as first_seen,
    p.last_seen_date,
    p.deleted_at,
    p.deletion_reason,
    CASE 
        WHEN p.is_active THEN CURRENT_DATE - p.collected_date
        ELSE p.last_seen_date - p.collected_date
    END as days_on_market,
    (SELECT COUNT(*) FROM price_history ph WHERE ph.article_no = p.article_no) as price_change_count
FROM properties p;

-- 5. 가격 변동 통계를 위한 뷰 생성
CREATE OR REPLACE VIEW price_change_summary AS
SELECT 
    ph.article_no,
    ph.trade_type,
    COUNT(*) as total_changes,
    SUM(CASE WHEN ph.change_amount > 0 THEN 1 ELSE 0 END) as price_increases,
    SUM(CASE WHEN ph.change_amount < 0 THEN 1 ELSE 0 END) as price_decreases,
    SUM(CASE WHEN ph.rent_change_amount > 0 THEN 1 ELSE 0 END) as rent_increases,
    SUM(CASE WHEN ph.rent_change_amount < 0 THEN 1 ELSE 0 END) as rent_decreases,
    MAX(ph.change_percent) as max_price_increase_pct,
    MIN(ph.change_percent) as max_price_decrease_pct,
    AVG(ph.change_percent) as avg_price_change_pct
FROM price_history ph
GROUP BY ph.article_no, ph.trade_type;

-- 6. 기존 인덱스 최적화
-- properties 테이블 성능 개선을 위한 추가 인덱스

CREATE INDEX IF NOT EXISTS idx_properties_is_active_cortar ON properties(is_active, cortar_no);
CREATE INDEX IF NOT EXISTS idx_properties_trade_type_price ON properties(trade_type, price);
CREATE INDEX IF NOT EXISTS idx_properties_last_seen_date ON properties(last_seen_date);
CREATE INDEX IF NOT EXISTS idx_properties_deleted_at ON properties(deleted_at);

-- 복합 인덱스 - 자주 함께 조회되는 컬럼들
CREATE INDEX IF NOT EXISTS idx_properties_search ON properties(cortar_no, real_estate_type, trade_type, is_active);
CREATE INDEX IF NOT EXISTS idx_properties_price_range ON properties(price, area1) WHERE is_active = true;

-- 7. 데이터 정합성 검증을 위한 함수
CREATE OR REPLACE FUNCTION verify_data_integrity() 
RETURNS TABLE(
    check_name TEXT,
    result BOOLEAN,
    message TEXT
) 
LANGUAGE plpgsql AS $$
BEGIN
    -- 1. price_history의 매물이 properties에 존재하는지 확인
    RETURN QUERY
    SELECT 
        'price_history_references'::TEXT,
        NOT EXISTS(
            SELECT 1 FROM price_history ph 
            LEFT JOIN properties p ON ph.article_no = p.article_no 
            WHERE p.article_no IS NULL
        ),
        'All price_history records reference valid properties'::TEXT;
    
    -- 2. 삭제된 매물의 is_active 상태 확인
    RETURN QUERY
    SELECT 
        'deleted_properties_inactive'::TEXT,
        NOT EXISTS(
            SELECT 1 FROM properties 
            WHERE deleted_at IS NOT NULL AND is_active = true
        ),
        'All deleted properties are marked as inactive'::TEXT;
    
    -- 3. last_seen_date가 collected_date보다 이른 경우 확인
    RETURN QUERY
    SELECT 
        'last_seen_after_collected'::TEXT,
        NOT EXISTS(
            SELECT 1 FROM properties 
            WHERE last_seen_date < collected_date
        ),
        'All last_seen_date are after or equal to collected_date'::TEXT;
END;
$$;

-- 8. 주석 추가
COMMENT ON TABLE deletion_history IS '매물 삭제 이력 추적 테이블';
COMMENT ON COLUMN properties.deleted_at IS '매물 삭제 시점';
COMMENT ON COLUMN properties.deletion_reason IS '삭제 사유 (not_found, sold, expired 등)';
COMMENT ON COLUMN properties.last_seen_date IS '매물이 마지막으로 확인된 날짜';
COMMENT ON COLUMN price_history.trade_type IS '거래 타입 (매매, 전세, 월세)';
COMMENT ON COLUMN price_history.rent_change_amount IS '월세 변동액 (원)';
COMMENT ON COLUMN price_history.rent_change_percent IS '월세 변동률 (%)';

-- 9. 마이그레이션 완료 확인
SELECT 'Database migration completed successfully' as status;