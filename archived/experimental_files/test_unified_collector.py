#!/usr/bin/env python3
"""
통합 수집기 간단 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_collector import UnifiedCollector

def simple_test():
    """간단한 연결 테스트"""
    print("🔧 통합 수집기 초기화 테스트")
    print("=" * 40)
    
    try:
        collector = UnifiedCollector()
        print("✅ UnifiedCollector 초기화 성공")
        
        # 헬스 체크만 테스트
        test_cortar_no = "1168010100"
        health = collector.health_check(test_cortar_no)
        
        print(f"\n📊 헬스 체크 결과:")
        print(f"   지역 코드: {health.get('cortar_no')}")
        print(f"   총 매물: {health.get('total_properties', 0)}개")
        print(f"   활성 매물: {health.get('active_properties', 0)}개")
        print(f"   품질 점수: {health.get('data_quality_score', 0.0)}")
        print(f"   상태: {health.get('health_status', 'unknown')}")
        
        print(f"\n✅ 통합 수집기 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    simple_test()