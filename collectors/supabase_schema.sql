-- Supabase 테이블 스키마
-- 네이버 부동산 데이터 수집 시스템

-- 1. 지역 마스터 테이블
CREATE TABLE IF NOT EXISTS areas (
  cortar_no TEXT PRIMARY KEY,
  gu_name TEXT NOT NULL,
  dong_name TEXT NOT NULL,
  center_lat DECIMAL(10,6),
  center_lon DECIMAL(10,6),
  boundary_points JSONB,
  zoom_level INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_areas_gu ON areas(gu_name);
CREATE INDEX idx_areas_dong ON areas(dong_name);

-- 2. 매물 정보 테이블
CREATE TABLE IF NOT EXISTS properties (
  id BIGSERIAL PRIMARY KEY,
  article_no TEXT UNIQUE NOT NULL,
  cortar_no TEXT REFERENCES areas(cortar_no),
  
  -- 기본 정보
  article_name TEXT,
  real_estate_type TEXT,
  trade_type TEXT,
  price BIGINT,
  rent_price BIGINT,
  
  -- 면적 정보
  area1 DECIMAL(10,2), -- 전용면적
  area2 DECIMAL(10,2), -- 공급면적
  
  -- 위치 정보
  floor_info TEXT,
  direction TEXT,
  latitude DECIMAL(10,6),
  longitude DECIMAL(10,6),
  
  -- 주소 정보 (카카오 변환)
  address_road TEXT,
  address_jibun TEXT,
  address_detail TEXT,
  building_name TEXT,
  postal_code TEXT,
  
  -- 상세 정보
  tag_list TEXT[],
  description TEXT,
  
  -- 상태 관리
  collected_date DATE NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_properties_cortar ON properties(cortar_no);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_area ON properties(area1);
CREATE INDEX idx_properties_date ON properties(collected_date);
CREATE INDEX idx_properties_active ON properties(is_active);
CREATE INDEX idx_properties_location ON properties(latitude, longitude);

-- 3. 일별 통계 테이블
CREATE TABLE IF NOT EXISTS daily_stats (
  id BIGSERIAL PRIMARY KEY,
  stat_date DATE NOT NULL,
  cortar_no TEXT REFERENCES areas(cortar_no),
  
  -- 수량 통계
  total_count INTEGER DEFAULT 0,
  new_count INTEGER DEFAULT 0,
  removed_count INTEGER DEFAULT 0,
  
  -- 가격 통계
  avg_price DECIMAL(12,2),
  median_price DECIMAL(12,2),
  min_price BIGINT,
  max_price BIGINT,
  
  -- 면적 통계
  avg_area DECIMAL(10,2),
  
  -- 분포 데이터
  price_distribution JSONB,
  area_distribution JSONB,
  type_distribution JSONB,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(stat_date, cortar_no)
);

-- 인덱스 생성
CREATE INDEX idx_daily_stats_date ON daily_stats(stat_date);
CREATE INDEX idx_daily_stats_cortar ON daily_stats(cortar_no);

-- 4. 가격 변동 이력 테이블
CREATE TABLE IF NOT EXISTS price_history (
  id BIGSERIAL PRIMARY KEY,
  article_no TEXT NOT NULL,
  previous_price BIGINT,
  new_price BIGINT,
  change_amount BIGINT,
  change_percent DECIMAL(5,2),
  changed_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_price_history_article ON price_history(article_no);
CREATE INDEX idx_price_history_date ON price_history(changed_date);

-- 5. 수집 로그 테이블
CREATE TABLE IF NOT EXISTS collection_logs (
  id BIGSERIAL PRIMARY KEY,
  gu_name TEXT NOT NULL,
  dong_name TEXT,
  cortar_no TEXT,
  collection_type TEXT, -- 'area_discovery', 'property_collection'
  status TEXT, -- 'started', 'completed', 'failed'
  total_collected INTEGER,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_logs_date ON collection_logs(created_at);
CREATE INDEX idx_logs_status ON collection_logs(status);

-- 트리거: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_areas_updated_at BEFORE UPDATE ON areas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) 설정
ALTER TABLE areas ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_logs ENABLE ROW LEVEL SECURITY;

-- 읽기 권한 정책 (anon 사용자)
CREATE POLICY "Enable read access for all users" ON areas FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON properties FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON daily_stats FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON price_history FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON collection_logs FOR SELECT USING (true);

-- 뷰: 최근 매물 요약
CREATE OR REPLACE VIEW recent_properties AS
SELECT 
  p.*,
  a.gu_name,
  a.dong_name
FROM properties p
JOIN areas a ON p.cortar_no = a.cortar_no
WHERE p.is_active = true
  AND p.collected_date >= CURRENT_DATE - INTERVAL '7 days';

-- 뷰: 지역별 현재 통계
CREATE OR REPLACE VIEW area_current_stats AS
SELECT 
  a.cortar_no,
  a.gu_name,
  a.dong_name,
  COUNT(p.id) as active_count,
  AVG(p.price) as avg_price,
  MIN(p.price) as min_price,
  MAX(p.price) as max_price,
  AVG(p.area1) as avg_area
FROM areas a
LEFT JOIN properties p ON a.cortar_no = p.cortar_no AND p.is_active = true
GROUP BY a.cortar_no, a.gu_name, a.dong_name;