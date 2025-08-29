-- =============================================================================
-- 자동 계산 트리거 생성
-- =============================================================================

-- 세금 총액 자동 계산 함수
CREATE OR REPLACE FUNCTION calculate_total_tax_cost()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_tax = COALESCE(NEW.acquisition_tax, 0) + 
                   COALESCE(NEW.registration_tax, 0) + 
                   COALESCE(NEW.stamp_duty, 0) + 
                   COALESCE(NEW.vat, 0);
    
    NEW.total_cost = NEW.total_tax + COALESCE(NEW.brokerage_fee, 0);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
DROP TRIGGER IF EXISTS calculate_tax_totals_trigger ON property_tax_info;
CREATE TRIGGER calculate_tax_totals_trigger
    BEFORE INSERT OR UPDATE ON property_tax_info
    FOR EACH ROW EXECUTE FUNCTION calculate_total_tax_cost();

DROP TRIGGER IF EXISTS update_property_tax_info_updated_at ON property_tax_info;
CREATE TRIGGER update_property_tax_info_updated_at 
    BEFORE UPDATE ON property_tax_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
