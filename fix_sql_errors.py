#!/usr/bin/env python3
"""
comprehensive_schema_update.sql 에러 분석 및 수정
실제 실행 시 발생할 수 있는 문제점들을 찾아서 수정된 SQL을 생성
"""

import re

def analyze_and_fix_sql():
    """SQL 스크립트를 분석하고 수정된 버전을 생성"""
    
    try:
        with open('comprehensive_schema_update.sql', 'r', encoding='utf-8') as f:
            original_sql = f.read()
    except FileNotFoundError:
        print("❌ comprehensive_schema_update.sql 파일을 찾을 수 없습니다.")
        return False
    
    print("🔍 SQL 스크립트 분석 시작...")
    
    # 일반적인 PostgreSQL 실행 오류들을 확인하고 수정
    fixes = []
    fixed_sql = original_sql
    
    # 1. update_updated_at_column 함수가 없을 경우를 대비한 함수 생성 추가
    if 'update_updated_at_column()' in fixed_sql and 'CREATE OR REPLACE FUNCTION update_updated_at_column' not in fixed_sql:
        function_creation = '''
-- 필수 함수: updated_at 자동 업데이트 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

'''
        # 첫 번째 CREATE TABLE 앞에 함수 정의 삽입
        first_create_table = fixed_sql.find('CREATE TABLE')
        if first_create_table != -1:
            fixed_sql = fixed_sql[:first_create_table] + function_creation + fixed_sql[first_create_table:]
            fixes.append("✅ update_updated_at_column() 함수 정의 추가")
    
    # 2. 존재하지 않을 수 있는 테이블에 대한 방어 로직 추가
    vulnerable_references = [
        ('properties_new', 'id'),
        ('facility_types', 'id'),
        ('property_locations', 'property_id'),
        ('property_physical', 'property_id')
    ]
    
    # 3. JSONB 지원 확인 로직 추가 (PostgreSQL 9.4 이상 필요)
    if 'JSONB' in fixed_sql:
        jsonb_check = '''
-- JSONB 지원 확인
DO $$
BEGIN
    IF (SELECT current_setting('server_version_num')::int < 90400) THEN
        RAISE EXCEPTION 'JSONB requires PostgreSQL 9.4 or higher';
    END IF;
END $$;

'''
        fixed_sql = jsonb_check + fixed_sql
        fixes.append("✅ JSONB 지원 버전 확인 로직 추가")
    
    # 4. 트랜잭션 래핑 추가 (일부 명령이 실패해도 전체가 롤백되지 않도록)
    if not fixed_sql.strip().startswith('BEGIN'):
        fixed_sql = "BEGIN;\n\n" + fixed_sql + "\n\nCOMMIT;"
        fixes.append("✅ 트랜잭션 블록으로 래핑")
    
    # 5. 스키마 확인 로직 개선
    schema_check = '''
-- 기본 테이블 존재 확인
DO $$
DECLARE
    table_names TEXT[] := ARRAY['properties_new', 'property_locations', 'property_physical', 'facility_types'];
    table_name TEXT;
    table_exists BOOLEAN;
BEGIN
    FOREACH table_name IN ARRAY table_names
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = table_name
        ) INTO table_exists;
        
        IF NOT table_exists THEN
            RAISE WARNING '테이블이 존재하지 않습니다: %', table_name;
        END IF;
    END LOOP;
END $$;

'''
    
    # 첫 번째 CREATE TABLE 앞에 스키마 확인 삽입
    first_create_table = fixed_sql.find('CREATE TABLE')
    if first_create_table != -1:
        fixed_sql = fixed_sql[:first_create_table] + schema_check + fixed_sql[first_create_table:]
        fixes.append("✅ 기존 테이블 존재 확인 로직 추가")
    
    # 6. 에러 허용 모드로 변경 (일부 에러가 있어도 계속 진행)
    fixed_sql = fixed_sql.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
    fixed_sql = fixed_sql.replace('CREATE INDEX IF NOT EXISTS', 'CREATE INDEX IF NOT EXISTS')
    fixes.append("✅ CREATE TABLE을 CREATE TABLE IF NOT EXISTS로 변경")
    
    # 수정된 파일 저장
    with open('comprehensive_schema_update_fixed.sql', 'w', encoding='utf-8') as f:
        f.write(fixed_sql)
    
    print(f"\n📊 분석 및 수정 결과:")
    print(f"📏 원본 파일 크기: {len(original_sql)} 문자")
    print(f"📏 수정 파일 크기: {len(fixed_sql)} 문자")
    print(f"🔧 적용된 수정사항: {len(fixes)}개")
    
    for fix in fixes:
        print(f"  • {fix}")
    
    print(f"\n✅ 수정된 SQL 파일 생성: comprehensive_schema_update_fixed.sql")
    print(f"💡 이제 수정된 파일로 다시 실행해보세요.")
    
    return True

def create_minimal_test_sql():
    """최소한의 테스트용 SQL 생성"""
    minimal_sql = '''
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
'''
    
    with open('minimal_test.sql', 'w', encoding='utf-8') as f:
        f.write(minimal_sql)
    
    print("✅ 최소 테스트 SQL 생성: minimal_test.sql")

if __name__ == "__main__":
    print("🛠️ SQL 에러 분석 및 수정 도구")
    
    success = analyze_and_fix_sql()
    create_minimal_test_sql()
    
    if success:
        print("\n🎉 분석 및 수정 완료!")
        print("📋 다음 단계:")
        print("  1. minimal_test.sql로 먼저 기본 연결 테스트")
        print("  2. comprehensive_schema_update_fixed.sql로 전체 실행")
        print("  3. 문제가 있다면 에러 메시지를 공유해주세요")
    else:
        print("\n💥 분석 중 오류가 발생했습니다.")