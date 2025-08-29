#!/usr/bin/env python3
"""
cached_token_collector.py - 호환성 래퍼
fixed_naver_collector_v2_optimized.py의 함수들을 재사용
"""

from fixed_naver_collector_v2_optimized import collect_by_cortar_no, CachedTokenCollector

# 메인 함수들을 외부에서 사용할 수 있도록 re-export
__all__ = ['collect_by_cortar_no', 'CachedTokenCollector']

if __name__ == "__main__":
    # 테스트용 실행
    import sys
    if len(sys.argv) > 1:
        cortar_no = sys.argv[1]
        print(f"🚀 {cortar_no} 수집 시작")
        result = collect_by_cortar_no(cortar_no, include_details=True, max_pages=1)
        print(f"📊 결과: {result}")
    else:
        print("사용법: python3 cached_token_collector.py [지역코드]")
        print("예시: python3 cached_token_collector.py 1168010100")