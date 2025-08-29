#!/usr/bin/env python3
"""
긴급 데이터 복구 스크립트
8월 16일 이후 잘못 삭제된 매물을 복구합니다.

사용법:
python emergency_data_recovery.py [옵션]
    --dry-run: 실제 복구 없이 복구 대상만 확인
    --date: 복구 기준 날짜 (기본: 2025-08-16)
    --limit: 한번에 복구할 최대 매물 수 (기본: 제한 없음)
"""

import sys
import argparse
from datetime import datetime, date
from typing import List, Dict, Optional
from supabase_client import SupabaseHelper

class EmergencyDataRecovery:
    def __init__(self):
        self.helper = SupabaseHelper()
        
    def get_wrongly_deleted_properties(self, since_date: str = '2025-08-16') -> List[Dict]:
        """잘못 삭제된 매물 목록 조회"""
        try:
            print(f"🔍 {since_date} 이후 삭제된 매물 조회 중...")
            
            # deletion_history에서 해당 기간 이후 삭제된 매물 조회
            result = self.helper.client.table('deletion_history')\
                .select('article_no, deleted_date, days_active')\
                .gte('deleted_date', since_date)\
                .execute()
                
            if result.data:
                print(f"📊 발견된 삭제 기록: {len(result.data)}개")
                return result.data
            else:
                print("ℹ️ 해당 기간에 삭제된 매물이 없습니다.")
                return []
                
        except Exception as e:
            print(f"❌ 삭제 기록 조회 오류: {e}")
            return []
    
    def check_property_current_status(self, article_no: str) -> Optional[Dict]:
        """매물의 현재 상태 확인"""
        try:
            result = self.helper.client.table('properties')\
                .select('article_no, is_active, article_name')\
                .eq('article_no', article_no)\
                .execute()
                
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            print(f"❌ 매물 상태 조회 오류 ({article_no}): {e}")
            return None
    
    def restore_property(self, article_no: str, dry_run: bool = False) -> bool:
        """단일 매물 복구"""
        try:
            if dry_run:
                print(f"🔍 [DRY-RUN] 복구 대상: {article_no}")
                return True
            
            # properties 테이블에서 다시 활성화
            result = self.helper.client.table('properties')\
                .update({
                    'is_active': True, 
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('article_no', article_no)\
                .execute()
                
            if result.data:
                print(f"✅ 복구 완료: {article_no}")
                return True
            else:
                print(f"⚠️ 복구 실패: {article_no} (데이터 없음)")
                return False
                
        except Exception as e:
            print(f"❌ 복구 오류 ({article_no}): {e}")
            return False
    
    def analyze_deletion_pattern(self, deleted_properties: List[Dict]):
        """삭제 패턴 분석"""
        print("\n📊 삭제 패턴 분석")
        print("=" * 50)
        
        # 날짜별 삭제 수
        date_counts = {}
        active_days_stats = []
        
        for prop in deleted_properties:
            deleted_date = prop['deleted_date'][:10]  # YYYY-MM-DD만 추출
            date_counts[deleted_date] = date_counts.get(deleted_date, 0) + 1
            
            if prop.get('days_active') is not None:
                active_days_stats.append(prop['days_active'])
        
        print("📅 날짜별 삭제 수:")
        for deletion_date in sorted(date_counts.keys()):
            count = date_counts[deletion_date]
            print(f"  {deletion_date}: {count}개")
        
        if active_days_stats:
            avg_active_days = sum(active_days_stats) / len(active_days_stats)
            print(f"\n⏱️ 평균 활성 기간: {avg_active_days:.1f}일")
            print(f"📊 활성 기간 분포:")
            print(f"  - 0일 (즉시 삭제): {len([x for x in active_days_stats if x == 0])}개")
            print(f"  - 1-3일: {len([x for x in active_days_stats if 1 <= x <= 3])}개")
            print(f"  - 4-7일: {len([x for x in active_days_stats if 4 <= x <= 7])}개")
            print(f"  - 8일 이상: {len([x for x in active_days_stats if x > 7])}개")
    
    def perform_recovery(self, since_date: str = '2025-08-16', dry_run: bool = False, limit: Optional[int] = None) -> Dict:
        """전체 복구 작업 수행"""
        print(f"🚨 긴급 데이터 복구 시작")
        print("=" * 50)
        
        if dry_run:
            print("🔍 [DRY-RUN 모드] 실제 복구는 수행되지 않습니다")
        
        # 1. 삭제된 매물 목록 조회
        deleted_properties = self.get_wrongly_deleted_properties(since_date)
        
        if not deleted_properties:
            return {'success': True, 'recovered_count': 0, 'message': '복구할 매물이 없습니다'}
        
        # 2. 삭제 패턴 분석
        self.analyze_deletion_pattern(deleted_properties)
        
        # 3. 복구 대상 필터링
        recovery_candidates = []
        
        for prop in deleted_properties:
            article_no = prop['article_no']
            
            # 현재 상태 확인
            current_status = self.check_property_current_status(article_no)
            
            if current_status:
                if not current_status['is_active']:
                    recovery_candidates.append({
                        'article_no': article_no,
                        'deleted_date': prop['deleted_date'],
                        'days_active': prop.get('days_active'),
                        'article_name': current_status.get('article_name', '')
                    })
                else:
                    print(f"ℹ️ 이미 활성상태: {article_no}")
            else:
                print(f"⚠️ 매물 데이터 없음: {article_no}")
        
        print(f"\n🎯 복구 대상: {len(recovery_candidates)}개 매물")
        
        if limit:
            recovery_candidates = recovery_candidates[:limit]
            print(f"📝 제한 적용: {len(recovery_candidates)}개 매물만 복구")
        
        # 4. 복구 실행
        recovered_count = 0
        failed_count = 0
        
        print(f"\n🔄 복구 시작...")
        
        for i, candidate in enumerate(recovery_candidates, 1):
            article_no = candidate['article_no']
            article_name = candidate.get('article_name', '')
            address = candidate.get('address_road', '')
            
            print(f"\n[{i}/{len(recovery_candidates)}] 복구 중: {article_no}")
            if article_name:
                print(f"  📍 매물명: {article_name}")
            if address:
                print(f"  🏠 주소: {address}")
            
            if self.restore_property(article_no, dry_run):
                recovered_count += 1
            else:
                failed_count += 1
        
        # 5. 결과 요약
        print(f"\n🎉 복구 작업 완료!")
        print("=" * 50)
        print(f"📊 복구 통계:")
        print(f"  - 복구 대상: {len(recovery_candidates)}개")
        print(f"  - 복구 성공: {recovered_count}개")
        print(f"  - 복구 실패: {failed_count}개")
        print(f"  - 성공률: {recovered_count/len(recovery_candidates)*100:.1f}%" if recovery_candidates else "N/A")
        
        if dry_run:
            print(f"\n💡 실제 복구를 위해 --dry-run 옵션 없이 다시 실행하세요")
        
        return {
            'success': True,
            'recovered_count': recovered_count,
            'failed_count': failed_count,
            'total_candidates': len(recovery_candidates)
        }

def main():
    parser = argparse.ArgumentParser(description='긴급 데이터 복구 스크립트')
    parser.add_argument('--dry-run', action='store_true', help='실제 복구 없이 복구 대상만 확인')
    parser.add_argument('--date', default='2025-08-16', help='복구 기준 날짜 (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, help='한번에 복구할 최대 매물 수')
    
    args = parser.parse_args()
    
    # 날짜 형식 검증
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ 날짜 형식 오류. YYYY-MM-DD 형식으로 입력하세요.")
        sys.exit(1)
    
    # 복구 작업 실행
    recovery = EmergencyDataRecovery()
    result = recovery.perform_recovery(
        since_date=args.date,
        dry_run=args.dry_run,
        limit=args.limit
    )
    
    if result['success']:
        print(f"\n✅ 작업 완료: {result['recovered_count']}개 매물 복구됨")
        sys.exit(0)
    else:
        print(f"\n❌ 작업 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()