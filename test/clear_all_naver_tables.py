#!/usr/bin/env python3
"""
네이버 관련 모든 테이블의 데이터를 완전히 삭제하는 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

def clear_all_naver_tables():
    """네이버 관련 모든 테이블의 데이터 삭제"""
    
    # Supabase 클라이언트 초기화
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
        return False
    
    supabase: Client = create_client(url, key)
    
    print("🗑️  네이버 관련 테이블 데이터 삭제 시작")
    print("=" * 50)
    
    # 삭제할 테이블 목록 (외래키 제약 순서 고려)
    tables_to_clear = [
        'naver_photos',      # 사진 (외래키 있음, 먼저 삭제)
        'naver_facilities',  # 편의시설 (외래키 있음)
        'naver_realtors',    # 중개사 (외래키 있음)
        'naver_properties'   # 메인 매물 (마지막에 삭제)
    ]
    
    total_deleted = 0
    
    for table_name in tables_to_clear:
        try:
            # 먼저 현재 레코드 수 확인
            count_response = supabase.table(table_name).select("*", count='exact').execute()
            current_count = count_response.count if hasattr(count_response, 'count') else 0
            
            if current_count == 0:
                print(f"📋 {table_name}: 이미 비어있음 (0건)")
                continue
            
            print(f"🔄 {table_name} 테이블 삭제 중... (현재 {current_count}건)")
            
            # 모든 데이터 삭제
            # Supabase에서는 조건 없이 삭제하면 모든 행이 삭제됨
            # 안전을 위해 명시적 조건 추가
            delete_response = supabase.table(table_name).delete().neq('article_no', '').execute()
            
            # 삭제 후 확인
            verify_response = supabase.table(table_name).select("*", count='exact').execute()
            remaining_count = verify_response.count if hasattr(verify_response, 'count') else 0
            
            deleted_count = current_count - remaining_count
            total_deleted += deleted_count
            
            if remaining_count == 0:
                print(f"✅ {table_name}: {deleted_count}건 삭제 완료")
            else:
                print(f"⚠️  {table_name}: {deleted_count}건 삭제, {remaining_count}건 남음")
                
        except Exception as e:
            print(f"❌ {table_name} 테이블 삭제 실패: {str(e)}")
    
    print("=" * 50)
    print(f"📊 삭제 완료 요약:")
    print(f"   총 삭제된 레코드: {total_deleted}건")
    
    # 최종 상태 확인
    print("\n📋 최종 테이블 상태:")
    for table_name in tables_to_clear:
        try:
            response = supabase.table(table_name).select("*", count='exact').execute()
            count = response.count if hasattr(response, 'count') else 0
            status = "✅ 비어있음" if count == 0 else f"⚠️  {count}건 남음"
            print(f"   {table_name}: {status}")
        except Exception as e:
            print(f"   {table_name}: ❌ 확인 실패")
    
    print("=" * 50)
    print(f"🕐 작업 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

if __name__ == "__main__":
    # 사용자 확인
    print("⚠️  경고: 이 작업은 되돌릴 수 없습니다!")
    print("네이버 관련 모든 테이블의 데이터가 삭제됩니다:")
    print("- naver_properties (메인 매물)")
    print("- naver_realtors (중개사)")
    print("- naver_facilities (편의시설)")
    print("- naver_photos (사진)")
    print()
    
    confirmation = input("정말로 모든 데이터를 삭제하시겠습니까? (yes/no): ")
    
    if confirmation.lower() == 'yes':
        success = clear_all_naver_tables()
        if success:
            print("\n✨ 모든 네이버 테이블이 비워졌습니다. 새로운 수집을 시작할 수 있습니다.")
        else:
            print("\n❌ 데이터 삭제 중 오류가 발생했습니다.")
    else:
        print("\n❌ 작업이 취소되었습니다.")