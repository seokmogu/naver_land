#!/usr/bin/env python3
"""
EC2 안전 테스트 검증 체크리스트
각 단계별로 확인해야 할 핵심 사항들
"""

def print_verification_checklist():
    """검증 체크리스트 출력"""
    
    print("🛡️ EC2 안전 테스트 검증 체크리스트")
    print("=" * 60)
    
    print("\n📋 1단계: 배포 완료 확인")
    print("   ✅ 6개 핵심 파일 모두 배포됨")
    print("   ✅ SSH 연결 정상")
    print("   ✅ 파일 권한 설정 완료")
    print("   ✅ Python 환경 및 패키지 확인")
    
    print("\n📊 2단계: DB 상태 확인 (emergency_recovery.py)")
    print("   🔍 확인사항:")
    print("   ├─ 총 매물 수: 85,107개 유지")
    print("   ├─ DB 연결: 정상") 
    print("   ├─ 무결성: 확인됨")
    print("   └─ 마지막 업데이트: 최신")
    
    print("\n🧪 3단계: 테스트 모드 수집")
    print("   🔍 확인사항:")
    print("   ├─ 지역: 1168010100 (강남구 신사동)")
    print("   ├─ 페이지: 최대 2페이지")
    print("   ├─ 수집 매물: ~50-100개 예상")
    print("   ├─ DB 저장: 하지 않음 (테스트 모드)")
    print("   └─ 품질 검증: 통과")
    
    print("\n💾 4단계: 실제 저장 테스트 (선택적)")
    print("   ⚠️ 주의사항:")
    print("   ├─ 사용자 확인 후 진행 (y/N)")
    print("   ├─ 안전 모드로 동작")
    print("   ├─ 기존 85,107개 매물 절대 삭제 안됨")
    print("   ├─ 새 매물만 추가/업데이트")
    print("   └─ 즉시 무결성 재검증")
    
    print("\n🛡️ 5단계: 안전성 재확인")
    print("   ✅ 최종 확인사항:")
    print("   ├─ 기존 85,107개 매물 보호됨")
    print("   ├─ 새 매물 정상 추가됨")
    print("   ├─ DB 무결성 유지")
    print("   └─ 시스템 안정성 확보")
    
    print("\n🚨 긴급시 대응 방안")
    print("   📞 응급 복구:")
    print("   └─ python3 emergency_recovery.py")
    print("   📊 상태 점검:")
    print("   └─ 실시간 DB 상태 모니터링")
    print("   🔄 롤백:")
    print("   └─ 문제시 즉시 이전 상태로 복구")
    
    print("\n" + "=" * 60)
    print("🎯 핵심 성공 기준:")
    print("   1. 85,107개 기존 매물 100% 보호")
    print("   2. 새 매물 정상 수집 및 저장")
    print("   3. DB 무결성 완전 유지")
    print("   4. 시스템 안정성 확보")
    print("   5. 응급 복구 시스템 대기")

def print_expected_timeline():
    """예상 소요 시간"""
    
    print("\n⏰ 예상 소요 시간")
    print("-" * 30)
    print("📤 배포: 2-3분")
    print("🔍 사전 점검: 1분")  
    print("📊 DB 상태 확인: 1-2분")
    print("🧪 테스트 모드: 3-5분")
    print("💾 실제 저장 (선택): 3-5분")
    print("🛡️ 안전성 재확인: 1-2분")
    print("-" * 30)
    print("🕒 총 소요 시간: 약 11-18분")

def print_success_criteria():
    """성공 판정 기준"""
    
    print("\n✅ 성공 판정 기준")
    print("-" * 30)
    print("1. 모든 테스트 단계 통과")
    print("2. 85,107개 매물 완전 보호")
    print("3. 새 매물 정상 수집/저장")
    print("4. DB 무결성 100% 유지")
    print("5. 오류/경고 메시지 없음")
    print("6. 응급 복구 시스템 대기")

if __name__ == "__main__":
    print_verification_checklist()
    print_expected_timeline()
    print_success_criteria()
    
    print("\n🚀 실행 준비 완료!")
    print("   다음 명령어로 배포를 시작하세요:")
    print("   $ python3 manual_deploy.py")
    print("")
    print("   배포 완료 후:")
    print("   $ ssh naver-ec2")
    print("   $ cd /home/ubuntu/naver_land/collectors") 
    print("   $ ./ec2_safe_test.sh")