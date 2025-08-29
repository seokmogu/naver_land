#!/usr/bin/env python3
"""
SQL 스크립트 구문 검증 도구
comprehensive_schema_update.sql의 구문 오류를 찾아내는 도구
"""

import re
import sys

def validate_sql_syntax():
    """SQL 스크립트의 구문을 검증하고 잠재적 오류를 찾음"""
    sql_file = "comprehensive_schema_update.sql"
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False
    
    print(f"📄 SQL 파일 검증 시작: {sql_file}")
    print(f"📏 파일 크기: {len(content)} 문자")
    
    errors = []
    warnings = []
    line_number = 0
    
    # 라인별로 검증
    lines = content.split('\n')
    in_comment_block = False
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # 빈 라인이나 주석 라인 스킵
        if not line_stripped or line_stripped.startswith('--'):
            continue
            
        # 블록 주석 처리
        if line_stripped.startswith('/*'):
            in_comment_block = True
            continue
        if '*/' in line_stripped and in_comment_block:
            in_comment_block = False
            continue
        if in_comment_block:
            continue
            
        # 1. 테이블명/컬럼명 문법 오류 검사
        if 'CREATE TABLE' in line_stripped.upper():
            # 테이블명에 특수문자나 예약어 체크
            table_match = re.search(r'CREATE TABLE\s+(\w+)', line_stripped, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(1)
                if table_name.upper() in ['ORDER', 'GROUP', 'WHERE', 'SELECT']:
                    errors.append(f"라인 {i}: 테이블명이 SQL 예약어입니다: {table_name}")
        
        # 2. 제약조건 문법 오류 검사
        if 'CONSTRAINT' in line_stripped.upper():
            if not re.search(r'CONSTRAINT\s+\w+', line_stripped, re.IGNORECASE):
                errors.append(f"라인 {i}: CONSTRAINT 구문에 이름이 누락되었습니다")
        
        # 3. 데이터 타입 오류 검사
        data_type_issues = [
            (r'DECIMAL\(\d+,\s*\d+\)', '올바른 DECIMAL 형식'),
            (r'VARCHAR\(\d+\)', '올바른 VARCHAR 형식'),
            (r'BIGINT|INTEGER|TEXT|BOOLEAN|DATE|TIMESTAMP', '올바른 데이터 타입')
        ]
        
        if any(dt in line_stripped.upper() for dt in ['DECIMAL', 'VARCHAR']) and 'ADD COLUMN' in line_stripped.upper():
            if not re.search(r'(DECIMAL|VARCHAR)\s*\(\d+', line_stripped, re.IGNORECASE):
                warnings.append(f"라인 {i}: 데이터 타입에 크기 명시가 필요할 수 있습니다")
        
        # 4. 함수명 오류 검사
        if 'update_updated_at_column()' in line_stripped:
            warnings.append(f"라인 {i}: update_updated_at_column 함수가 존재하는지 확인 필요")
        
        # 5. 인덱스 중복 검사
        if 'CREATE INDEX' in line_stripped.upper():
            index_match = re.search(r'CREATE INDEX\s+IF NOT EXISTS\s+(\w+)', line_stripped, re.IGNORECASE)
            if not index_match:
                warnings.append(f"라인 {i}: 인덱스 생성 시 IF NOT EXISTS 사용 권장")
        
        # 6. DO 블록 문법 검사
        if line_stripped.startswith('DO $$'):
            # DO 블록의 기본 구조 확인
            if not ('BEGIN' in content[content.find(line):content.find(line)+500]):
                errors.append(f"라인 {i}: DO 블록에 BEGIN이 누락되었습니다")
        
        # 7. ALTER TABLE 구문 검사
        if 'ALTER TABLE' in line_stripped.upper():
            if 'ADD COLUMN' in line_stripped.upper():
                if not 'IF NOT EXISTS' in line_stripped.upper():
                    warnings.append(f"라인 {i}: ALTER TABLE ADD COLUMN에 IF NOT EXISTS 사용 권장")
        
        # 8. 참조 무결성 검사
        if 'REFERENCES' in line_stripped.upper():
            ref_match = re.search(r'REFERENCES\s+(\w+)\s*\((\w+)\)', line_stripped, re.IGNORECASE)
            if ref_match:
                ref_table = ref_match.group(1)
                ref_column = ref_match.group(2)
                if ref_table not in ['properties_new', 'regions', 'facility_types']:
                    warnings.append(f"라인 {i}: 참조 테이블 존재 여부 확인 필요: {ref_table}")
    
    # 결과 리포트
    print(f"\n📊 검증 결과:")
    print(f"❌ 오류: {len(errors)}개")
    print(f"⚠️ 경고: {len(warnings)}개")
    
    if errors:
        print(f"\n❌ 발견된 오류들:")
        for error in errors:
            print(f"  • {error}")
    
    if warnings:
        print(f"\n⚠️ 주의사항들:")
        for warning in warnings:
            print(f"  • {warning}")
    
    # 특별히 확인해야 할 사항들
    print(f"\n🔍 추가 확인 사항:")
    
    # 테이블 의존성 확인
    required_tables = ['properties_new', 'property_locations', 'property_physical', 'facility_types']
    print(f"  📋 필수 테이블 존재 여부 확인 필요: {', '.join(required_tables)}")
    
    # 함수 존재 여부 확인
    if 'update_updated_at_column()' in content:
        print(f"  ⚙️ 함수 존재 여부 확인 필요: update_updated_at_column()")
    
    # 데이터 타입 호환성
    print(f"  🔗 PostgreSQL 데이터 타입 호환성 확인")
    print(f"  🗂️ JSONB 컬럼 지원 여부 확인")
    
    return len(errors) == 0

if __name__ == "__main__":
    print("🔍 SQL 구문 검증 시작")
    is_valid = validate_sql_syntax()
    
    if is_valid:
        print("\n✅ 기본적인 구문 오류는 발견되지 않았습니다.")
        print("💡 실제 실행 시에는 테이블/함수 존재 여부와 권한을 확인하세요.")
    else:
        print("\n💥 구문 오류가 발견되었습니다. 수정이 필요합니다.")
        sys.exit(1)