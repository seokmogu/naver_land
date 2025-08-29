-- =============================================================================
-- 데이터 품질 검증 뷰 생성
-- =============================================================================

-- 1. 데이터 완성도 체크 뷰
CREATE OR REPLACE VIEW data_completeness_check AS
SELECT 
    'property_basic' as table_name,
    COUNT(*) as total_records,
    COUNT(article_name) as has_article_name,
    COUNT(real_estate_type_id) as has_real_estate_type,
    ROUND(COUNT(article_name)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as completeness_pct
FROM properties_new
WHERE is_active = true
UNION ALL
SELECT 
    'property_physical' as table_name,
    COUNT(*) as total_records,
    COUNT(area_exclusive) as has_area_exclusive,
    COUNT(space_type) as has_space_type,
    ROUND(COUNT(area_exclusive)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as completeness_pct
FROM property_physical
UNION ALL
SELECT 
    'property_tax_info' as table_name,
    COUNT(*) as total_records,
    COUNT(total_tax) as has_tax_calculation,
    COUNT(total_cost) as has_total_cost,
    ROUND(COUNT(total_tax)::decimal / NULLIF(COUNT(*), 0) * 100, 2) as completeness_pct
FROM property_tax_info;
