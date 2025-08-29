#!/usr/bin/env python3
"""
정규화된 스키마 생성 실행기
create_normalized_schema.sql 파일을 읽어서 Supabase에 실행
"""

import os
import sys
from pathlib import Path
from supabase import create_client

# 환경 설정
os.environ['SUPABASE_URL'] = 'https://eslhavjipwbyvbbknixv.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'

def execute_sql_file():
    """SQL 파일을 읽어서 실행"""
    try:
        client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
        print("✅ Supabase 연결 성공")
        
        # SQL 파일 읽기
        sql_file_path = Path(__file__).parent / 'create_normalized_schema.sql'
        if not sql_file_path.exists():
            print("❌ create_normalized_schema.sql 파일을 찾을 수 없습니다")
            return False
        
        print("📄 SQL 파일 읽기 중...")
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # SQL 문을 세미콜론으로 분리
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print(f"🔧 총 {len(sql_statements)}개 SQL 문 실행 예정")
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(sql_statements, 1):
            if not statement or statement.startswith('--'):
                continue
                
            try:
                # PostgreSQL 직접 실행 (Supabase는 PostgreSQL 기반)
                result = client.rpc('exec_sql_direct', {'sql_text': statement}).execute()
                print(f"  ✅ 문장 {i}: 실행 완료")
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                if 'already exists' in error_msg.lower():
                    print(f"  ℹ️  문장 {i}: 이미 존재함 (스킵)")
                else:
                    print(f"  ❌ 문장 {i}: {error_msg[:100]}...")
                    error_count += 1
        
        print(f"\n📊 실행 결과:")
        print(f"  성공: {success_count}개")
        print(f"  오류: {error_count}개")
        
        if error_count == 0:
            print("🎉 모든 테이블 생성 완료!")
            return True
        else:
            print("⚠️ 일부 오류 발생. 수동 확인 필요")
            return False
            
    except Exception as e:
        print(f"❌ 실행 중 오류: {e}")
        return False

if __name__ == "__main__":
    print("🏗️ 정규화된 스키마 생성 시작...")
    success = execute_sql_file()
    
    if success:
        print("\n🚀 다음 단계: core 수집기와 연동 준비")
    else:
        print("\n🔧 문제 해결 후 재시도 필요")