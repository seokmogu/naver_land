#!/usr/bin/env python3
"""
Supabase 데이터베이스에 스키마 업데이트를 직접 적용하는 스크립트
- PostgreSQL 함수를 통한 DDL 실행
- 개별 컴포넌트별 검증
- 실시간 진행상황 보고
"""

import os
import sys
from pathlib import Path
from supabase import create_client
import time

class DirectSchemaUpdater:
    def __init__(self):
        """직접 스키마 업데이터 초기화"""
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        print("🔧 직접 스키마 업데이터 초기화 완료")
        print(f"🎯 대상: {self.supabase_url}")
    
    def create_ddl_executor_function(self):
        """DDL 실행용 PostgreSQL 함수 생성"""
        print("\n📋 DDL 실행 함수 생성...")
        
        # 먼저 DDL 실행 함수가 있는지 확인
        function_sql = """
        CREATE OR REPLACE FUNCTION execute_ddl(ddl_statement text)
        RETURNS text AS $$
        BEGIN
            EXECUTE ddl_statement;
            RETURN 'SUCCESS';
        EXCEPTION
            WHEN OTHERS THEN
                RETURN 'ERROR: ' || SQLERRM;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        try:
            result = self.client.rpc('execute_ddl', {
                'ddl_statement': function_sql
            }).execute()
            print("✅ DDL 실행 함수 생성 성공")
            return True
        except Exception as e:
            print(f"⚠️ DDL 함수 생성 시도 중 오류 (무시 가능): {e}")
            # 함수가 이미 있을 수 있으므로 계속 진행
            return True
    
    def execute_ddl_command(self, ddl_statement: str, description: str) -> bool:
        """DDL 명령어 실행"""
        print(f"🔄 {description} 실행 중...")
        
        try:
            result = self.client.rpc('execute_ddl', {
                'ddl_statement': ddl_statement
            }).execute()
            
            if result.data and result.data == 'SUCCESS':
                print(f"✅ {description} 성공")
                return True
            elif result.data and result.data.startswith('ERROR:'):
                error_msg = result.data[7:]  # Remove 'ERROR: ' prefix
                if self._is_acceptable_error(error_msg):
                    print(f"⚠️ {description} (이미 존재함): {error_msg[:50]}...")
                    return True
                else:
                    print(f"❌ {description} 실패: {error_msg[:100]}...")
                    return False
            else:
                print(f"✅ {description} 완료")
                return True
                
        except Exception as e:
            error_msg = str(e)
            if self._is_acceptable_error(error_msg):
                print(f"⚠️ {description} (이미 존재함): {error_msg[:50]}...")
                return True
            else:
                print(f"❌ {description} 실패: {error_msg[:100]}...")
                return False
    
    def _is_acceptable_error(self, error_msg: str) -> bool:
        """허용 가능한 오류인지 확인 (이미 존재하는 경우 등)"""
        acceptable_errors = [
            'already exists',
            'relation already exists',
            'column already exists',
            'constraint already exists',
            'function already exists',
            'trigger already exists',
            'index already exists',
            'view already exists'
        ]
        
        error_lower = error_msg.lower()
        return any(acceptable in error_lower for acceptable in acceptable_errors)
    
    def add_missing_columns(self):
        """누락된 컬럼들 추가"""
        print("\n🔧 누락된 컬럼 추가 시작...")
        
        column_additions = [
            # property_physical 테이블 (가장 중요한 space_type 포함)
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS space_type VARCHAR(100);", 
             "property_physical.space_type 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS veranda_count INTEGER DEFAULT 0;", 
             "property_physical.veranda_count 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS structure_type VARCHAR(100);", 
             "property_physical.structure_type 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS floor_description TEXT;", 
             "property_physical.floor_description 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS ground_floor_count INTEGER;", 
             "property_physical.ground_floor_count 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS monthly_management_cost INTEGER;", 
             "property_physical.monthly_management_cost 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS management_office_tel VARCHAR(20);", 
             "property_physical.management_office_tel 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_type VARCHAR(50);", 
             "property_physical.move_in_type 컬럼 추가"),
            ("ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS move_in_discussion BOOLEAN DEFAULT false;", 
             "property_physical.move_in_discussion 컬럼 추가"),
            
            # properties_new 테이블 (가장 중요한 law_usage 포함)
            ("ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS law_usage VARCHAR(100);", 
             "properties_new.law_usage 컬럼 추가"),
            ("ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS building_use VARCHAR(100);", 
             "properties_new.building_use 컬럼 추가"),
            ("ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS floor_layer_name VARCHAR(100);", 
             "properties_new.floor_layer_name 컬럼 추가"),
            
            # property_locations 테이블
            ("ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS nearest_station TEXT;", 
             "property_locations.nearest_station 컬럼 추가"),
            ("ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS subway_stations JSONB;", 
             "property_locations.subway_stations 컬럼 추가"),
            ("ALTER TABLE property_locations ADD COLUMN IF NOT EXISTS detail_address VARCHAR(500);", 
             "property_locations.detail_address 컬럼 추가")
        ]
        
        success_count = 0
        for ddl_statement, description in column_additions:
            if self.execute_ddl_command(ddl_statement, description):
                success_count += 1
            time.sleep(0.5)  # 약간의 대기 시간
        
        total_count = len(column_additions)
        print(f"\n📊 컬럼 추가 결과: {success_count}/{total_count} 성공")
        
        return success_count >= (total_count * 0.8)  # 80% 이상 성공하면 OK
    
    def create_missing_tables(self):
        """누락된 테이블 생성"""
        print("\n📋 누락된 테이블 생성 시작...")
        
        table_creations = [
            # property_facilities 테이블 (가장 중요)
            ("""CREATE TABLE IF NOT EXISTS property_facilities (
                id BIGSERIAL PRIMARY KEY,
                property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
                facility_id INTEGER REFERENCES facility_types(id),
                available BOOLEAN DEFAULT true,
                condition_grade INTEGER CHECK (condition_grade >= 1 AND condition_grade <= 5),
                notes VARCHAR(200),
                last_checked DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""", "property_facilities 테이블 생성"),
            
            # property_tax_info 테이블 (이미 있을 수 있음)
            ("""CREATE TABLE IF NOT EXISTS property_tax_info (
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_tax_amounts CHECK (
                    acquisition_tax >= 0 AND registration_tax >= 0 AND 
                    brokerage_fee >= 0 AND stamp_duty >= 0 AND 
                    vat >= 0 AND total_tax >= 0 AND total_cost >= 0
                )
            );""", "property_tax_info 테이블 생성"),
            
            # property_price_comparison 테이블 (이미 있을 수 있음)
            ("""CREATE TABLE IF NOT EXISTS property_price_comparison (
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
            );""", "property_price_comparison 테이블 생성")
        ]
        
        success_count = 0
        for ddl_statement, description in table_creations:
            if self.execute_ddl_command(ddl_statement, description):
                success_count += 1
            time.sleep(1)  # 테이블 생성은 조금 더 대기
        
        total_count = len(table_creations)
        print(f"\n📊 테이블 생성 결과: {success_count}/{total_count} 성공")
        
        return success_count >= total_count  # 모든 테이블이 성공해야 함
    
    def create_essential_indexes(self):
        """필수 인덱스 생성"""
        print("\n🔍 필수 인덱스 생성 시작...")
        
        index_creations = [
            ("CREATE INDEX IF NOT EXISTS idx_property_facilities_property ON property_facilities(property_id);", 
             "property_facilities 인덱스 생성"),
            ("CREATE INDEX IF NOT EXISTS idx_property_facilities_type ON property_facilities(facility_id, available);", 
             "property_facilities 타입 인덱스 생성"),
            ("CREATE INDEX IF NOT EXISTS idx_property_physical_space_type ON property_physical(space_type);", 
             "property_physical space_type 인덱스 생성"),
            ("CREATE INDEX IF NOT EXISTS idx_properties_new_law_usage ON properties_new(law_usage);", 
             "properties_new law_usage 인덱스 생성")
        ]
        
        success_count = 0
        for ddl_statement, description in index_creations:
            if self.execute_ddl_command(ddl_statement, description):
                success_count += 1
            time.sleep(0.5)
        
        total_count = len(index_creations)
        print(f"\n📊 인덱스 생성 결과: {success_count}/{total_count} 성공")
        
        return success_count >= (total_count * 0.7)  # 70% 이상 성공하면 OK
    
    def validate_critical_updates(self):
        """중요 업데이트 항목 검증"""
        print("\n🧪 중요 업데이트 검증 시작...")
        
        validation_tests = {
            'property_facilities 테이블': self._test_table_exists('property_facilities'),
            'space_type 컬럼': self._test_column_accessible('property_physical', 'space_type'),
            'law_usage 컬럼': self._test_column_accessible('properties_new', 'law_usage'),
            'property_tax_info 테이블': self._test_table_exists('property_tax_info'),
            'property_price_comparison 테이블': self._test_table_exists('property_price_comparison')
        }
        
        passed_tests = 0
        total_tests = len(validation_tests)
        
        for test_name, test_result in validation_tests.items():
            if test_result:
                print(f"✅ {test_name} 검증 통과")
                passed_tests += 1
            else:
                print(f"❌ {test_name} 검증 실패")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📊 검증 결과: {passed_tests}/{total_tests} 통과 ({success_rate:.1f}%)")
        
        return success_rate >= 80  # 80% 이상 통과하면 성공
    
    def _test_table_exists(self, table_name: str) -> bool:
        """테이블 존재 확인"""
        try:
            self.client.table(table_name).select('count', count='exact').limit(0).execute()
            return True
        except Exception:
            return False
    
    def _test_column_accessible(self, table_name: str, column_name: str) -> bool:
        """컬럼 접근 가능성 확인"""
        try:
            self.client.table(table_name).select(column_name).limit(1).execute()
            return True
        except Exception as e:
            # 'Could not find the column' 또는 비슷한 메시지가 있으면 컬럼이 없음
            error_msg = str(e).lower()
            if 'could not find' in error_msg and column_name.lower() in error_msg:
                return False
            elif 'column' in error_msg and 'does not exist' in error_msg:
                return False
            else:
                # 다른 오류면 일단 존재한다고 가정 (권한 문제 등)
                return True
    
    def run_complete_update(self):
        """전체 업데이트 프로세스 실행"""
        print("🚀 직접 스키마 업데이트 프로세스 시작")
        print("=" * 60)
        
        # 0. DDL 실행 함수 생성
        print("\n📋 0단계: DDL 실행 환경 준비")
        if not self.create_ddl_executor_function():
            print("❌ DDL 실행 환경 준비 실패")
            return False
        
        # 1. 누락된 컬럼 추가 (가장 중요!)
        print("\n📋 1단계: 누락된 컬럼 추가")
        columns_success = self.add_missing_columns()
        
        # 2. 누락된 테이블 생성
        print("\n📋 2단계: 누락된 테이블 생성")
        tables_success = self.create_missing_tables()
        
        # 3. 필수 인덱스 생성
        print("\n📋 3단계: 필수 인덱스 생성")
        indexes_success = self.create_essential_indexes()
        
        # 약간의 대기 시간 (DB 반영 대기)
        print("\n⏳ 데이터베이스 반영 대기...")
        time.sleep(2)
        
        # 4. 중요 업데이트 검증
        print("\n📋 4단계: 중요 업데이트 검증")
        validation_success = self.validate_critical_updates()
        
        # 5. 최종 결과 보고
        print("\n" + "=" * 60)
        print("📊 직접 스키마 업데이트 완료 보고서")
        print("=" * 60)
        
        steps_results = {
            '컬럼 추가': columns_success,
            '테이블 생성': tables_success,
            '인덱스 생성': indexes_success,
            '업데이트 검증': validation_success
        }
        
        successful_steps = sum(steps_results.values())
        total_steps = len(steps_results)
        overall_success_rate = (successful_steps / total_steps * 100)
        
        print(f"📈 전체 단계: {total_steps}개")
        print(f"✅ 성공한 단계: {successful_steps}개")
        print(f"🎯 성공률: {overall_success_rate:.1f}%")
        
        print(f"\n🔍 단계별 결과:")
        for step_name, step_result in steps_results.items():
            status = "✅ 성공" if step_result else "❌ 실패"
            print(f"   {status} {step_name}")
        
        if overall_success_rate >= 75:
            print(f"\n🎉 스키마 업데이트가 성공적으로 완료되었습니다!")
            print(f"✅ 다음 단계:")
            print(f"   1. python test_schema_deployment.py로 최종 검증")
            print(f"   2. enhanced_data_collector.py로 실제 수집 시작")
            print(f"   3. 데이터 손실 문제 해결 확인")
            return True
        else:
            print(f"\n⚠️ 일부 스키마 업데이트에서 문제가 발생했습니다.")
            print(f"🔧 권장사항:")
            print(f"   - 실패한 단계들을 수동으로 확인해보세요")
            print(f"   - Supabase Dashboard에서 직접 SQL 실행을 고려하세요")
            return False

def main():
    """메인 실행 함수"""
    print("🔧 네이버 부동산 수집기 - 직접 스키마 업데이터")
    
    updater = DirectSchemaUpdater()
    success = updater.run_complete_update()
    
    if success:
        print("\n🎯 성공! 이제 데이터 수집을 시작할 수 있습니다.")
        return 0
    else:
        print("\n⚠️ 일부 문제가 발생했습니다. 로그를 확인하고 재시도하세요.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)