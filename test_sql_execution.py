#!/usr/bin/env python3
"""
SQL 스크립트 실행 테스트 도구
Supabase를 통해 comprehensive_schema_update.sql을 실행하고 에러 확인
"""

import os
import sys
from collectors.db.supabase_client import SupabaseHelper

def test_sql_execution():
    """SQL 스크립트를 실행하고 에러 확인"""
    try:
        # Supabase 클라이언트 초기화
        supabase_helper = SupabaseHelper()
        
        # SQL 파일 읽기
        sql_file = "comprehensive_schema_update.sql"
        if not os.path.exists(sql_file):
            print(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
            return False
            
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"📄 SQL 파일 크기: {len(sql_content)} 문자")
        
        # SQL을 여러 구문으로 분할
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        print(f"📝 총 {len(sql_statements)}개의 SQL 구문 감지")
        
        # 각 SQL 구문을 순차적으로 실행
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(sql_statements, 1):
            if not statement or statement.startswith('--') or statement.startswith('/*'):
                continue
                
            print(f"\n🔄 구문 {i} 실행 중...")
            try:
                # Supabase에서 직접 SQL 실행
                result = supabase_helper.client.rpc('exec_sql', {'sql': statement}).execute()
                print(f"✅ 구문 {i} 성공")
                success_count += 1
            except Exception as e:
                print(f"❌ 구문 {i} 실패: {str(e)}")
                print(f"🔍 문제가 된 구문:\n{statement[:200]}...")
                error_count += 1
        
        print(f"\n📊 실행 결과:")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {error_count}개")
        
        return error_count == 0
        
    except Exception as e:
        print(f"❌ SQL 실행 중 전체적인 오류 발생: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SQL 스크립트 실행 테스트 시작")
    success = test_sql_execution()
    
    if success:
        print("🎉 모든 SQL 구문이 성공적으로 실행되었습니다!")
        sys.exit(0)
    else:
        print("💥 일부 SQL 구문에서 오류가 발생했습니다.")
        sys.exit(1)