-- =============================================================================
-- 성능 최적화 인덱스 생성
-- =============================================================================

-- 새 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_property_tax_info_property ON property_tax_info(property_id);
CREATE INDEX IF NOT EXISTS idx_property_tax_info_total_cost ON property_tax_info(total_cost);

CREATE INDEX IF NOT EXISTS idx_property_price_comparison_property ON property_price_comparison(property_id);
CREATE INDEX IF NOT EXISTS idx_property_price_comparison_complex ON property_price_comparison(cpid, complex_name);

CREATE INDEX IF NOT EXISTS idx_property_facilities_property ON property_facilities(property_id);
CREATE INDEX IF NOT EXISTS idx_property_facilities_type ON property_facilities(facility_id, available);

-- 새 컬럼 인덱스
CREATE INDEX IF NOT EXISTS idx_property_locations_subway ON property_locations USING GIN (subway_stations);
CREATE INDEX IF NOT EXISTS idx_property_physical_space_type ON property_physical(space_type);
CREATE INDEX IF NOT EXISTS idx_property_physical_management_cost ON property_physical(monthly_management_cost);
CREATE INDEX IF NOT EXISTS idx_properties_new_law_usage ON properties_new(law_usage);
