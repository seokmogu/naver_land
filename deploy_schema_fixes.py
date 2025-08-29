#!/usr/bin/env python3
"""
스키마 수정사항 배포 및 검증 스크립트
- SQL 파일을 읽어서 Supabase에 배포 가능한 형태로 제공
- 배포 후 검증 테스트 실행
"""

import os
import sys
from pathlib import Path
from supabase import create_client
import subprocess
import json

class SchemaDeploymentManager:
    def __init__(self):
        """배포 관리자 초기화"""
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        print("🚀 스키마 배포 관리자 초기화")
    
    def create_individual_sql_files(self):
        """각 구성 요소별로 개별 SQL 파일 생성"""
        print("\n📄 개별 SQL 파일 생성 중...")
        
        sql_components = {
            'create_missing_tables.sql': self._get_table_creation_sql(),
            'add_missing_columns.sql': self._get_column_addition_sql(),
            'create_indexes.sql': self._get_index_creation_sql(),
            'create_views.sql': self._get_view_creation_sql(),
            'create_triggers.sql': self._get_trigger_creation_sql()
        }
        
        created_files = []
        for filename, sql_content in sql_components.items():
            file_path = Path(__file__).parent / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            
            created_files.append(str(file_path))
            print(f"   ✅ {filename} 생성 완료")
        
        return created_files
    
    def _get_table_creation_sql(self) -> str:
        """테이블 생성 SQL"""
        return """-- =============================================================================
-- 누락된 테이블 생성
-- =============================================================================

-- 1. property_tax_info 테이블
CREATE TABLE IF NOT EXISTS property_tax_info (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    acquisition_tax INTEGER DEFAULT 0,
    acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    registration_tax INTEGER DEFAULT 0,
    registration_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    brokerage_fee INTEGER DEFAULT 0,
    brokerage_fee_rate DECIMAL(5, 4) DEFAULT 0.0000,
    stamp_duty INTEGER DEFAULT 0,
    vat INTEGER DEFAULT 0,
    total_tax INTEGER DEFAULT 0,
    total_cost INTEGER DEFAULT 0,
    
    calculation_date DATE DEFAULT CURRENT_DATE,
    is_estimated BOOLEAN DEFAULT false,
    notes TEXT,
    
    CONSTRAINT chk_tax_amounts CHECK (
        acquisition_tax >= 0 AND registration_tax >= 0 AND 
        brokerage_fee >= 0 AND stamp_duty >= 0 AND 
        vat >= 0 AND total_tax >= 0 AND total_cost >= 0
    ),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. property_price_comparison 테이블
CREATE TABLE IF NOT EXISTS property_price_comparison (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    
    same_addr_count INTEGER DEFAULT 0,
    same_addr_max_price BIGINT,
    same_addr_min_price BIGINT,
    cpid VARCHAR(50),
    complex_name VARCHAR(200),
    article_feature_desc TEXT,
    market_data_date DATE DEFAULT CURRENT_DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_price_comparison_logic 
    CHECK (same_addr_max_price IS NULL OR same_addr_min_price IS NULL OR same_addr_max_price >= same_addr_min_price),
    CONSTRAINT chk_same_addr_count_positive 
    CHECK (same_addr_count >= 0)
);

-- 3. property_facilities 테이블 (확인 및 생성)
CREATE TABLE IF NOT EXISTS property_facilities (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facility_types(id),
    
    available BOOLEAN DEFAULT true,
    condition_grade INTEGER CHECK (condition_grade >= 1 AND condition_grade <= 5),
    notes VARCHAR(200),
    last_checked DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    
    def _get_column_addition_sql(self) -> str:
        """컬럼 추가 SQL"""
        return """-- =============================================================================
-- 기존 테이블에 누락된 컬럼 추가
-- =============================================================================

-- property_locations 테이블 확장
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS nearest_station TEXT;
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS subway_stations JSONB;
ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS detail_address VARCHAR(500);

-- property_physical 테이블 확장  
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS veranda_count INTEGER DEFAULT 0;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS space_type VARCHAR(100);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS structure_type VARCHAR(100);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS floor_description TEXT;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS ground_floor_count INTEGER;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS monthly_management_cost INTEGER;
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS management_office_tel VARCHAR(20);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_type VARCHAR(50);
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_discussion BOOLEAN DEFAULT false;

-- properties_new 테이블 확장
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS building_use VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS law_usage VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS floor_layer_name VARCHAR(100);
"""
    
    def _get_index_creation_sql(self) -> str:
        """인덱스 생성 SQL"""
        return """-- =============================================================================
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
"""
    
    def _get_view_creation_sql(self) -> str:
        """뷰 생성 SQL"""
        return """-- =============================================================================
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
"""
    
    def _get_trigger_creation_sql(self) -> str:
        """트리거 생성 SQL"""
        return """-- =============================================================================
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
"""
    
    def generate_deployment_instructions(self, sql_files: list):
        """배포 지침 생성"""
        instructions = f"""
🚀 네이버 부동산 수집기 - 스키마 수정 배포 가이드
================================================================

📋 배포해야 할 SQL 파일들:
"""
        
        for i, file_path in enumerate(sql_files, 1):
            filename = Path(file_path).name
            instructions += f"{i}. {filename}\n"
        
        instructions += f"""
🎯 배포 방법 1: Supabase Dashboard 사용 (권장)
----------------------------------------------------------------
1. https://supabase.com/dashboard 로그인
2. 프로젝트 선택: eslhavjipwbyvbbknixv
3. SQL Editor 메뉴 선택
4. 위 SQL 파일들을 순서대로 복사-붙여넣기 실행

🎯 배포 방법 2: psql 명령줄 사용
----------------------------------------------------------------
psql 연결 정보가 있다면:
"""
        
        for file_path in sql_files:
            filename = Path(file_path).name
            instructions += f"psql -h <host> -d <database> -U <username> -f {filename}\n"
        
        instructions += f"""
⚠️ 주의사항:
----------------------------------------------------------------
- 파일 순서대로 실행해야 합니다 (의존성 문제)
- 오류가 발생해도 대부분 "이미 존재함" 오류이므로 무시 가능
- 실행 후 test_schema_deployment.py로 검증 필수

✅ 배포 후 검증:
----------------------------------------------------------------
python test_schema_deployment.py

🎉 성공하면 데이터 수집기 시작:
----------------------------------------------------------------
python enhanced_data_collector.py
"""
        
        instructions_file = Path(__file__).parent / "DEPLOYMENT_INSTRUCTIONS.md"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        print(f"\n📋 배포 가이드 생성: {instructions_file}")
        return str(instructions_file)
    
    def run_post_deployment_validation(self):
        """배포 후 검증 테스트"""
        print("\n🧪 배포 후 검증 테스트 실행...")
        
        try:
            test_script = Path(__file__).parent / "test_schema_deployment.py"
            if test_script.exists():
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=120)
                
                print("📊 검증 결과:")
                if result.returncode == 0:
                    print("✅ 검증 성공!")
                    print(result.stdout[-500:])  # 마지막 500자
                else:
                    print("⚠️ 검증에서 일부 문제 발견")
                    print(result.stderr[-300:])  # 오류 메시지
                    
                return result.returncode == 0
            else:
                print("⚠️ 검증 스크립트를 찾을 수 없습니다")
                return False
                
        except Exception as e:
            print(f"❌ 검증 실행 오류: {e}")
            return False
    
    def execute_full_deployment(self):
        """전체 배포 프로세스 실행"""
        print("🚀 스키마 수정사항 전체 배포 프로세스")
        print("=" * 60)
        
        # 1. 개별 SQL 파일 생성
        print("\n📋 1단계: 개별 SQL 파일 생성")
        sql_files = self.create_individual_sql_files()
        
        # 2. 배포 가이드 생성
        print("\n📋 2단계: 배포 가이드 생성")
        instructions_file = self.generate_deployment_instructions(sql_files)
        
        # 3. 현재 상태 확인
        print("\n📋 3단계: 현재 스키마 상태 확인")
        self._check_current_schema_status()
        
        print("\n" + "=" * 60)
        print("📊 배포 준비 완료!")
        print("=" * 60)
        
        print(f"✅ {len(sql_files)}개 SQL 파일 생성 완료")
        print(f"✅ 배포 가이드 생성: {Path(instructions_file).name}")
        
        print(f"\n🎯 다음 단계:")
        print(f"1. {Path(instructions_file).name} 파일을 열어서 배포 가이드 확인")
        print(f"2. Supabase Dashboard에서 SQL 파일들 순서대로 실행")
        print(f"3. python test_schema_deployment.py로 검증")
        print(f"4. 성공하면 enhanced_data_collector.py로 수집 시작")
        
        return True
    
    def _check_current_schema_status(self):
        """현재 스키마 상태 확인"""
        print("   📊 현재 데이터베이스 상태:")
        
        critical_components = {
            'property_tax_info': self._table_exists('property_tax_info'),
            'property_price_comparison': self._table_exists('property_price_comparison'),
            'property_facilities': self._table_exists('property_facilities'),
            'space_type 컬럼': self._column_accessible('property_physical', 'space_type'),
            'law_usage 컬럼': self._column_accessible('properties_new', 'law_usage')
        }
        
        for component, exists in critical_components.items():
            status = "✅ 존재" if exists else "❌ 누락"
            print(f"      {status} {component}")
    
    def _table_exists(self, table_name: str) -> bool:
        """테이블 존재 확인"""
        try:
            self.client.table(table_name).select('count', count='exact').limit(0).execute()
            return True
        except:
            return False
    
    def _column_accessible(self, table_name: str, column_name: str) -> bool:
        """컬럼 접근 가능성 확인"""
        try:
            self.client.table(table_name).select(column_name).limit(1).execute()
            return True
        except:
            return False

def main():
    """메인 실행 함수"""
    print("🔧 네이버 부동산 수집기 - 스키마 배포 관리자")
    
    manager = SchemaDeploymentManager()
    success = manager.execute_full_deployment()
    
    if success:
        print("\n🎉 배포 준비가 완료되었습니다!")
        print("📋 DEPLOYMENT_INSTRUCTIONS.md를 참고하여 배포를 진행하세요.")
    else:
        print("\n❌ 배포 준비 중 문제가 발생했습니다.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)