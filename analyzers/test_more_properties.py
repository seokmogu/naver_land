#!/usr/bin/env python3
"""
더 많은 매물이 있는 지역에서 스크롤링 테스트
"""

from scroll_loading_analyzer import ScrollLoadingAnalyzer

def test_multiple_areas():
    """여러 지역에서 스크롤링 테스트"""
    
    test_urls = [
        # 강남역 일대 (더 넓은 범위)
        "https://new.land.naver.com/offices?ms=37.498095,127.027610,14&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL",
        
        # 서울 전체 (매우 넓은 범위) 
        "https://new.land.naver.com/offices?ms=37.566826,126.9786567,11&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL",
        
        # 홍대 일대
        "https://new.land.naver.com/offices?ms=37.556785,126.922070,14&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    ]
    
    area_names = ["강남역 넓은 범위", "서울 전체", "홍대 일대"]
    
    for i, (url, name) in enumerate(zip(test_urls, area_names)):
        print(f"\n{'='*60}")
        print(f"🏢 {name} 테스트 ({i+1}/{len(test_urls)})")
        print(f"{'='*60}")
        
        analyzer = ScrollLoadingAnalyzer()
        
        try:
            # 스크롤 분석 실행
            analyzer.analyze_scroll_loading(url)
            
            # 결과 출력
            analyzer.print_scroll_summary()
            
            # 결과 저장
            filename = analyzer.save_scroll_analysis()
            print(f"💾 {name} 결과: {filename}")
            
        except Exception as e:
            print(f"❌ {name} 테스트 실패: {e}")
        
        if i < len(test_urls) - 1:
            print(f"\n⏳ 다음 테스트까지 5초 대기...")
            import time
            time.sleep(5)

if __name__ == "__main__":
    test_multiple_areas()