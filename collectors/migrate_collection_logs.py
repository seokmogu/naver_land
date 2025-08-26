#!/usr/bin/env python3
"""
collection_logs 테이블 마이그레이션 스크립트
새로운 컬럼 추가 및 데이터 정리
"""

from supabase_client import SupabaseHelper
from datetime import datetime, timedelta


def migrate_collection_logs():
    """collection_logs 테이블 스키마 확장"""
    helper = SupabaseHelper()
    
    print("🔄 collection_logs 테이블 마이그레이션 시작...")
    
    # 마이그레이션 SQL 명령어들
    migrations = [
        # 새 컬럼 추가
        """
        ALTER TABLE collection_logs 
        ADD COLUMN IF NOT EXISTS process_id INTEGER,
        ADD COLUMN IF NOT EXISTS process_name TEXT,
        ADD COLUMN IF NOT EXISTS duration_seconds DECIMAL(10,2),
        ADD COLUMN IF NOT EXISTS error_details JSONB,
        ADD COLUMN IF NOT EXISTS collection_stats JSONB
        """,
        
        # 인덱스 추가 (성능 향상)
        """
        CREATE INDEX IF NOT EXISTS idx_collection_logs_status_created 
        ON collection_logs(status, created_at DESC)
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_collection_logs_cortar_status 
        ON collection_logs(cortar_no, status, created_at DESC)
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_collection_logs_process 
        ON collection_logs(process_name, created_at DESC)
        """
    ]
    
    try:
        for i, migration in enumerate(migrations, 1):
            print(f"📝 마이그레이션 {i}/{len(migrations)} 실행 중...")
            helper.client.rpc('exec_sql', {'sql': migration}).execute()
            print(f"✅ 마이그레이션 {i} 완료")
        
        print("🎉 모든 마이그레이션 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False


def cleanup_old_logs():
    """오래된 로그 정리"""
    helper = SupabaseHelper()
    
    print("🧹 오래된 로그 정리 시작...")
    
    try:
        # 30일 이전 로그 삭제
        cutoff_date = datetime.now() - timedelta(days=30)
        
        result = helper.client.table('collection_logs')\
            .delete()\
            .lt('created_at', cutoff_date.isoformat())\
            .execute()
        
        deleted_count = len(result.data) if result.data else 0
        print(f"🗑️ {deleted_count}개 오래된 로그 삭제 완료")
        
        # 고아 프로세스 로그 정리 (2시간 이상 started 상태)
        orphan_cutoff = datetime.now() - timedelta(hours=2)
        
        orphaned_logs = helper.client.table('collection_logs')\
            .select('id, dong_name, started_at')\
            .eq('status', 'started')\
            .lt('started_at', orphan_cutoff.isoformat())\
            .execute()
        
        if orphaned_logs.data:
            for log in orphaned_logs.data:
                helper.client.table('collection_logs')\
                    .update({
                        'status': 'timeout',
                        'completed_at': datetime.now().isoformat(),
                        'error_message': '프로세스 타임아웃 (2시간 초과)',
                        'error_details': {
                            'cleanup_reason': 'orphaned_process_migration',
                            'original_started_at': log['started_at']
                        }
                    })\
                    .eq('id', log['id'])\
                    .execute()
            
            print(f"⏰ {len(orphaned_logs.data)}개 고아 프로세스 로그 정리 완료")
        
        print("✅ 로그 정리 완료")
        return True
        
    except Exception as e:
        print(f"❌ 로그 정리 실패: {e}")
        return False


def validate_migration():
    """마이그레이션 검증"""
    helper = SupabaseHelper()
    
    print("🔍 마이그레이션 검증 중...")
    
    try:
        # 테이블 구조 확인
        result = helper.client.table('collection_logs').select('*').limit(1).execute()
        
        if result.data:
            columns = list(result.data[0].keys())
            print("📋 현재 테이블 컬럼:")
            for col in sorted(columns):
                print(f"  - {col}")
            
            # 필수 컬럼 확인
            required_columns = [
                'process_id', 'process_name', 'duration_seconds', 
                'error_details', 'collection_stats'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ 누락된 컬럼: {missing_columns}")
                return False
            else:
                print("✅ 모든 필수 컬럼 존재")
        
        # 로그 상태 분포 확인
        print("\n📊 현재 로그 상태 분포:")
        all_logs = helper.client.table('collection_logs').select('status').execute()
        
        status_count = {}
        for log in all_logs.data:
            status = log['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        for status, count in sorted(status_count.items()):
            print(f"  {status}: {count}개")
        
        print("✅ 마이그레이션 검증 완료")
        return True
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return False


def main():
    """마이그레이션 메인 함수"""
    print("🚀 collection_logs 테이블 마이그레이션 시작")
    print("=" * 60)
    
    # 1. 스키마 마이그레이션
    if not migrate_collection_logs():
        print("❌ 스키마 마이그레이션 실패")
        return False
    
    # 2. 기존 데이터 정리
    if not cleanup_old_logs():
        print("❌ 데이터 정리 실패")
        return False
    
    # 3. 마이그레이션 검증
    if not validate_migration():
        print("❌ 마이그레이션 검증 실패")
        return False
    
    print("\n🎉 collection_logs 마이그레이션 성공!")
    print("이제 enhanced_logger.py를 사용할 수 있습니다.")
    
    return True


if __name__ == "__main__":
    main()