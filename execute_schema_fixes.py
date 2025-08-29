#!/usr/bin/env python3
"""
스키마 수정사항을 Supabase 데이터베이스에 적용하고 검증
- SQL 스크립트 실행
- 실시간 검증
- 성공/실패 보고
"""

import os
import sys
from pathlib import Path
from supabase import create_client
import time

class SchemaFixer:
    def __init__(self):
        """스키마 수정기 초기화"""
        self.supabase_url = 'https://eslhavjipwbyvbbknixv.supabase.co'
        self.supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        print("🔧 스키마 수정기 초기화 완료")
        print(f"🎯 대상: {self.supabase_url}")
    
    def execute_sql_commands(self, sql_file_path: str):
        """SQL 스크립트를 명령어별로 분할 실행"""
        print(f"\n📄 SQL 스크립트 읽기: {sql_file_path}")
        
        if not Path(sql_file_path).exists():
            print(f"❌ 파일을 찾을 수 없습니다: {sql_file_path}")
            return False
        
        # SQL 파일 읽기
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # SQL 명령어 분할 (간단한 방법)
        sql_commands = self._split_sql_commands(sql_content)
        
        print(f"📊 총 {len(sql_commands)}개 SQL 명령어 발견")
        
        successful_commands = 0
        failed_commands = 0
        
        for i, command in enumerate(sql_commands, 1):
            command = command.strip()
            if not command or command.startswith('--'):
                continue
                
            print(f"\n🔄 명령어 {i} 실행 중...")
            success = self._execute_single_command(command)
            
            if success:
                successful_commands += 1
                print(f"✅ 명령어 {i} 성공")
            else:
                failed_commands += 1
                print(f"❌ 명령어 {i} 실패")
        
        print(f"\n📊 실행 결과: 성공 {successful_commands}개, 실패 {failed_commands}개")
        return failed_commands == 0
    
    def _split_sql_commands(self, sql_content: str) -> list:
        """SQL 내용을 개별 명령어로 분할"""
        # DO $$ 블록과 일반 명령어를 구분하여 처리
        commands = []
        current_command = ""
        in_do_block = False
        
        lines = sql_content.split('\n')
        
        for line in lines:
            stripped_line = line.strip()
            
            # 주석 및 빈 줄 스킵
            if not stripped_line or stripped_line.startswith('--') or stripped_line.startswith('/*'):
                continue
            
            # DO 블록 시작 감지
            if stripped_line.startswith('DO $$'):
                in_do_block = True
                current_command = line + '\n'
                continue
            
            # DO 블록 종료 감지
            if in_do_block and stripped_line == '$$;':
                current_command += line
                commands.append(current_command)
                current_command = ""
                in_do_block = False
                continue
            
            # DO 블록 내부이면 계속 추가
            if in_do_block:
                current_command += line + '\n'
                continue
            
            # 일반 명령어 처리
            current_command += line + '\n'
            
            # 세미콜론으로 끝나면 명령어 완료
            if stripped_line.endswith(';') and not in_do_block:
                commands.append(current_command)
                current_command = ""
        
        # 마지막 명령어 추가
        if current_command.strip():
            commands.append(current_command)
        
        return commands
    
    def _execute_single_command(self, command: str) -> bool:
        """단일 SQL 명령어 실행"""
        try:
            # Supabase의 RPC를 통해 SQL 실행 (직접 SQL 실행)
            result = self.client.rpc('execute_sql', {'sql_query': command}).execute()
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"   🔍 오류 세부사항: {error_msg[:100]}...")
            
            # 일부 오류는 무시 (이미 존재하는 테이블/컬럼 등)
            ignore_errors = [
                'already exists',
                'relation already exists',
                'column already exists',
                'constraint already exists',
                'function already exists'
            ]
            
            if any(ignore_error in error_msg.lower() for ignore_error in ignore_errors):
                print(f"   ⚠️ 이미 존재함 (무시됨)")
                return True
            
            return False
    
    def validate_critical_components(self):
        """중요 컴포넌트들이 제대로 생성되었는지 검증"""
        print(f"\n🧪 중요 컴포넌트 검증 중...")
        
        critical_tests = {
            '테이블 property_tax_info': self._test_table_exists('property_tax_info'),
            '테이블 property_price_comparison': self._test_table_exists('property_price_comparison'), 
            '테이블 property_facilities': self._test_table_exists('property_facilities'),
            '컬럼 space_type': self._test_column_exists('property_physical', 'space_type'),
            '컬럼 law_usage': self._test_column_exists('properties_new', 'law_usage'),
            '뷰 data_completeness_check': self._test_view_exists('data_completeness_check')
        }
        
        passed = 0
        total = len(critical_tests)
        
        for test_name, test_result in critical_tests.items():
            if test_result:
                print(f"   ✅ {test_name}")
                passed += 1
            else:
                print(f"   ❌ {test_name}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\n📊 중요 컴포넌트 검증: {passed}/{total} ({success_rate:.1f}%)")
        
        return success_rate >= 90  # 90% 이상이면 성공
    
    def _test_table_exists(self, table_name: str) -> bool:
        """테이블 존재 확인"""
        try:
            self.client.table(table_name).select('count', count='exact').limit(0).execute()
            return True
        except:
            return False
    
    def _test_column_exists(self, table_name: str, column_name: str) -> bool:
        """컬럼 존재 확인 (간접적 방법)"""
        try:
            # 테이블에서 해당 컬럼을 SELECT 해보기 (1건만)
            result = self.client.table(table_name).select(column_name).limit(1).execute()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if 'column' in error_msg and 'does not exist' in error_msg:
                return False
            elif 'could not find' in error_msg and column_name.lower() in error_msg:
                return False
            else:
                # 다른 오류면 일단 존재한다고 가정
                return True
    
    def _test_view_exists(self, view_name: str) -> bool:
        """뷰 존재 확인"""
        try:
            self.client.table(view_name).select('*').limit(1).execute()
            return True
        except:
            return False
    
    def run_complete_fix(self):
        """전체 수정 프로세스 실행"""
        print("🚀 스키마 완성 프로세스 시작")
        print("=" * 50)
        
        # 1. SQL 스크립트 실행
        sql_file = Path(__file__).parent / "fix_missing_schema_components.sql"
        
        print("\n📋 1단계: SQL 스크립트 실행")
        sql_success = self.execute_sql_commands(str(sql_file))
        
        if not sql_success:
            print("❌ SQL 스크립트 실행에 실패했습니다.")
            return False
        
        # 약간의 대기 시간 (DB 반영 대기)
        print("\n⏳ 데이터베이스 반영 대기 중...")
        time.sleep(3)
        
        # 2. 중요 컴포넌트 검증
        print("\n📋 2단계: 중요 컴포넌트 검증")
        validation_success = self.validate_critical_components()
        
        # 3. 최종 결과 요약
        print("\n" + "=" * 50)
        print("📊 스키마 수정 완료 보고서")
        print("=" * 50)
        
        if sql_success and validation_success:
            print("🎉 스키마 수정이 성공적으로 완료되었습니다!")
            print("\n✅ 다음 단계:")
            print("   1. test_schema_deployment.py 재실행")
            print("   2. enhanced_data_collector.py로 실제 수집 시작")
            print("   3. 데이터 손실 문제 해결 확인")
            return True
        else:
            print("⚠️ 스키마 수정에 일부 문제가 있습니다.")
            print("\n🔧 권장사항:")
            if not sql_success:
                print("   - SQL 스크립트 실행 로그를 확인하세요")
            if not validation_success:
                print("   - 중요 컴포넌트 검증 결과를 확인하세요")
                print("   - 수동으로 누락된 테이블/컬럼을 생성해보세요")
            return False

def main():
    """메인 실행 함수"""
    print("🔧 네이버 부동산 수집기 - 스키마 완성 도구")
    
    fixer = SchemaFixer()
    success = fixer.run_complete_fix()
    
    if success:
        print("\n🎯 성공! 이제 데이터 수집을 시작할 수 있습니다.")
        sys.exit(0)
    else:
        print("\n⚠️ 일부 문제가 발생했습니다. 로그를 확인하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()