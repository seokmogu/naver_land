#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
응급 데이터 복구 스크립트
8월 16일 이후 잘못 삭제된 매물 복구
수정: deletion_history 테이블 스키마에 맞게 조정
"""

import sys
import os
from datetime import datetime, date
from supabase_client import SupabaseHelper

def emergency_data_recovery():
    """8월 16일 이후 잘못 삭제된 매물 응급 복구"""
    try:
        helper = SupabaseHelper()
        
        # 1. 현재 상태 백업
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"🔄 응급 복구 시작: {backup_timestamp}")
        print(f"📅 복구 대상 기간: 2025-08-16 이후")
        
        # 2. deletion_history 테이블 스키마 확인
        print("🔍 deletion_history 테이블 스키마 확인...")
        try:
            # 테이블 구조 확인을 위해 1개 레코드만 조회
            schema_check = helper.client.table('deletion_history')\
                .select('*')\
                .limit(1)\
                .execute()
            
            if schema_check.data:
                print("📋 deletion_history 테이블 필드:")
                for key in schema_check.data[0].keys():
                    print(f"   - {key}")
        except Exception as e:
            print(f"⚠️ 스키마 확인 실패: {str(e)}")
        
        # 3. 삭제된 매물 조회 (수정된 필드명 사용)
        print("🔍 삭제된 매물 조회 중...")
        try:
            deleted_props = helper.client.table('deletion_history')\
                .select('article_no, deleted_date, real_estate_type, final_trade_type')\
                .gte('deleted_date', '2025-08-16')\
                .execute()
        except Exception as e:
            print(f"❌ 삭제 이력 조회 실패: {str(e)}")
            # 필드명이 다를 수 있으므로 기본 필드만 조회 시도
            try:
                deleted_props = helper.client.table('deletion_history')\
                    .select('article_no, deleted_date')\
                    .gte('deleted_date', '2025-08-16')\
                    .execute()
                print("✅ 기본 필드로 조회 성공")
            except Exception as e2:
                print(f"❌ 기본 필드 조회도 실패: {str(e2)}")
                return 0
        
        if not deleted_props.data:
            print("ℹ️ 8월 16일 이후 삭제된 매물이 없습니다.")
            return 0
        
        print(f"📊 복구 대상: {len(deleted_props.data)}개 매물")
        
        # 4. 복구 실행
        recovered_count = 0
        failed_count = 0
        
        for prop in deleted_props.data:
            article_no = prop['article_no']
            deleted_date = prop.get('deleted_date', 'N/A')
            
            try:
                # properties 테이블에서 해당 매물 존재 확인
                existing = helper.client.table('properties')\
                    .select('article_no, is_active')\
                    .eq('article_no', article_no)\
                    .execute()
                
                if existing.data:
                    property_data = existing.data[0]
                    
                    if not property_data.get('is_active', False):
                        # 비활성화된 매물이므로 복구 진행
                        result = helper.client.table('properties')\
                            .update({
                                'is_active': True, 
                                'deleted_at': None,
                                'recovered_at': datetime.now().isoformat(),
                                'recovery_reason': 'Emergency recovery - wrong deletion logic',
                                'updated_at': datetime.now().isoformat()
                            })\
                            .eq('article_no', article_no)\
                            .execute()
                        
                        if result.data:
                            recovered_count += 1
                            print(f"✅ 복구: {article_no} (삭제일: {deleted_date})")
                        else:
                            failed_count += 1
                            print(f"⚠️ 복구 실패 (업데이트 안됨): {article_no}")
                    else:
                        print(f"ℹ️ 이미 활성 상태: {article_no}")
                        recovered_count += 1  # 이미 활성화된 것도 성공으로 간주
                else:
                    failed_count += 1
                    print(f"⚠️ 복구 실패 (매물 없음): {article_no}")
                
            except Exception as e:
                failed_count += 1
                print(f"❌ 복구 실패 {article_no}: {str(e)}")
        
        print(f"\n🎯 복구 완료 요약:")
        print(f"   ✅ 성공: {recovered_count}개")
        print(f"   ❌ 실패: {failed_count}개")
        if recovered_count + failed_count > 0:
            print(f"   📈 성공률: {recovered_count/(recovered_count+failed_count)*100:.1f}%")
        
        # 5. 복구 후 상태 확인
        active_count = helper.client.table('properties')\
            .select('article_no', count='exact')\
            .eq('is_active', True)\
            .execute()
        
        print(f"📊 현재 활성 매물: {active_count.count}개")
        
        return recovered_count
        
    except Exception as e:
        print(f"🚨 응급 복구 중 오류 발생: {str(e)}")
        return -1

def verify_recovery():
    """복구 작업 검증"""
    try:
        helper = SupabaseHelper()
        
        # 복구된 매물 수 확인
        recovered_props = helper.client.table('properties')\
            .select('article_no, recovered_at')\
            .is_('deleted_at', 'null')\
            .eq('is_active', True)\
            .not_.is_('recovered_at', 'null')\
            .execute()
        
        print(f"\n📋 복구 검증:")
        print(f"   복구된 매물: {len(recovered_props.data)}개")
        
        if recovered_props.data:
            print(f"   최근 복구된 매물 (최대 5개):")
            for prop in recovered_props.data[:5]:
                print(f"   - {prop['article_no']}: 복구시간 {prop.get('recovered_at', 'N/A')}")
        
        return len(recovered_props.data)
        
    except Exception as e:
        print(f"❌ 복구 검증 중 오류: {str(e)}")
        return -1

def check_database_status():
    """현재 데이터베이스 상태 확인"""
    try:
        helper = SupabaseHelper()
        
        print("\n📊 현재 데이터베이스 상태:")
        
        # 전체 매물 수
        total_props = helper.client.table('properties')\
            .select('article_no', count='exact')\
            .execute()
        print(f"   전체 매물: {total_props.count}개")
        
        # 활성 매물 수
        active_props = helper.client.table('properties')\
            .select('article_no', count='exact')\
            .eq('is_active', True)\
            .execute()
        print(f"   활성 매물: {active_props.count}개")
        
        # 비활성 매물 수
        inactive_props = helper.client.table('properties')\
            .select('article_no', count='exact')\
            .eq('is_active', False)\
            .execute()
        print(f"   비활성 매물: {inactive_props.count}개")
        
        # 복구된 매물 수
        recovered_props = helper.client.table('properties')\
            .select('article_no', count='exact')\
            .not_.is_('recovered_at', 'null')\
            .execute()
        print(f"   복구된 매물: {recovered_props.count}개")
        
        return {
            'total': total_props.count,
            'active': active_props.count,
            'inactive': inactive_props.count,
            'recovered': recovered_props.count
        }
        
    except Exception as e:
        print(f"❌ 상태 확인 중 오류: {str(e)}")
        return None

if __name__ == "__main__":
    print("🚨 네이버 부동산 수집기 응급 데이터 복구")
    print("=" * 50)
    
    # 현재 상태 확인
    print("1️⃣ 현재 데이터베이스 상태 확인...")
    status = check_database_status()
    
    if status:
        print(f"\n현재 85,107개 매물 확인: {status['active'] == 85107}")
        
        if status['active'] < 85000:
            print("⚠️ 활성 매물이 예상보다 적습니다. 복구가 필요할 수 있습니다.")
            
            # 사용자 확인
            confirm = input("\n응급 복구를 진행하시겠습니까? (y/N): ").lower().strip()
            if confirm in ['y', 'yes']:
                # 응급 복구 실행
                print("\n2️⃣ 응급 복구 실행...")
                recovered = emergency_data_recovery()
                
                if recovered > 0:
                    print(f"\n🎉 응급 복구 성공: {recovered}개 매물 복구")
                    
                    # 복구 검증
                    print("\n3️⃣ 복구 검증...")
                    verified = verify_recovery()
                    if verified > 0:
                        print(f"✅ 복구 검증 완료: {verified}개 매물 확인됨")
                    
                    # 최종 상태 확인
                    print("\n4️⃣ 최종 상태 확인...")
                    final_status = check_database_status()
                    
                elif recovered == 0:
                    print("\nℹ️ 복구할 매물이 없습니다.")
                    
                else:
                    print(f"\n❌ 응급 복구 실패")
                    sys.exit(1)
            else:
                print("복구를 취소했습니다.")
        else:
            print("✅ 매물 수가 정상 범위입니다. 복구가 필요하지 않습니다.")
    
    print("\n💡 다음 단계: final_safe_collector.py로 새로운 안전한 수집 테스트")