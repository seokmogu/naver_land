-- 매물 변경 이력 테이블 생성
CREATE TABLE IF NOT EXISTS naver_property_history (
    id BIGSERIAL PRIMARY KEY,
    article_no VARCHAR NOT NULL,
    property_id BIGINT,
    change_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 변경 유형
    change_type VARCHAR(50), -- 'price_change', 'status_change', 'info_update' 등
    
    -- 가격 변경 추적 (이전값 -> 새값)
    deal_price_before BIGINT,
    deal_price_after BIGINT,
    warrant_price_before BIGINT,
    warrant_price_after BIGINT,
    rent_price_before INTEGER,
    rent_price_after INTEGER,
    
    -- 상태 변경 추적
    is_active_before BOOLEAN,
    is_active_after BOOLEAN,
    
    -- 주요 정보 변경 추적
    floor_before INTEGER,
    floor_after INTEGER,
    move_in_type_before VARCHAR,
    move_in_type_after VARCHAR,
    move_in_discussion_before BOOLEAN,
    move_in_discussion_after BOOLEAN,
    
    -- 변경 요약
    change_summary TEXT,
    
    -- 인덱스용 필드
    CONSTRAINT fk_property FOREIGN KEY (property_id) REFERENCES naver_properties(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX idx_property_history_article_no ON naver_property_history(article_no);
CREATE INDEX idx_property_history_property_id ON naver_property_history(property_id);
CREATE INDEX idx_property_history_change_detected_at ON naver_property_history(change_detected_at DESC);
CREATE INDEX idx_property_history_change_type ON naver_property_history(change_type);

-- 가격 스냅샷 테이블 (일별 가격 추적)
CREATE TABLE IF NOT EXISTS naver_price_snapshots (
    id BIGSERIAL PRIMARY KEY,
    article_no VARCHAR NOT NULL,
    property_id BIGINT,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    
    -- 거래 유형
    trade_type_name VARCHAR,
    
    -- 가격 정보
    deal_price BIGINT,
    warrant_price BIGINT,
    rent_price INTEGER,
    price_per_area NUMERIC,
    
    -- 메타 정보
    is_active BOOLEAN DEFAULT TRUE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 복합 유니크 키 (하루에 한 번만 스냅샷)
    CONSTRAINT unique_daily_snapshot UNIQUE (article_no, snapshot_date),
    CONSTRAINT fk_property_snapshot FOREIGN KEY (property_id) REFERENCES naver_properties(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX idx_price_snapshots_article_no ON naver_price_snapshots(article_no);
CREATE INDEX idx_price_snapshots_property_id ON naver_price_snapshots(property_id);
CREATE INDEX idx_price_snapshots_date ON naver_price_snapshots(snapshot_date DESC);