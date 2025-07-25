import os
import sys
from cluster_based_collector import ClusterBasedCollector

def test_cluster_analysis():
    """클러스터 API 테스트 및 분석"""
    print("=== 클러스터 API 테스트 ===\n")
    
    collector = ClusterBasedCollector()
    
    # 토큰 로드
    if not collector.load_token():
        print("❌ 토큰을 찾을 수 없습니다.")
        return
    
    # 테스트 영역: 강남역 주변
    test_bounds = {
        'north': 37.5050,
        'south': 37.4910,
        'east': 127.0350,
        'west': 127.0210
    }
    
    print("1️⃣ 클러스터 분석 (줌 레벨별)")
    print("-" * 40)
    
    for zoom in [13, 14, 15]:
        clusters = collector.get_clusters(test_bounds, zoom=zoom)
        if clusters:
            total_count = sum(c['count'] for c in clusters)
            print(f"\n줌 레벨 {zoom}:")
            print(f"  클러스터 수: {len(clusters)}개")
            print(f"  총 매물 수: {total_count}개")
            print(f"  평균 매물/클러스터: {total_count/len(clusters):.1f}개")
            
            # 상위 5개 클러스터
            sorted_clusters = sorted(clusters, key=lambda x: x['count'], reverse=True)[:5]
            print("  상위 클러스터:")
            for i, c in enumerate(sorted_clusters, 1):
                print(f"    {i}. {c['count']}개 (위치: {c['lat']:.4f}, {c['lng']:.4f})")
    
    print("\n" + "=" * 50)

def test_small_area_collection():
    """작은 지역 수집 테스트"""
    print("\n=== 작은 지역 수집 테스트 ===\n")
    
    collector = ClusterBasedCollector()
    
    if not collector.load_token():
        print("❌ 토큰을 찾을 수 없습니다.")
        return
    
    # 매우 작은 영역 테스트 (강남역 인근 약 500m x 500m)
    small_bounds = {
        'north': 37.5000,
        'south': 37.4955,
        'east': 127.0300,
        'west': 127.0255
    }
    
    print("테스트 영역: 강남역 인근 500m x 500m")
    articles = collector.get_articles_in_bounds(small_bounds, max_pages=3)
    
    if articles:
        print(f"\n수집된 매물: {len(articles)}개")
        
        # 거래 타입별 분석
        trade_types = {}
        for article in articles:
            trade_type = article.get('tradeTypeName', '기타')
            trade_types[trade_type] = trade_types.get(trade_type, 0) + 1
        
        print("\n거래 타입별 분포:")
        for trade_type, count in trade_types.items():
            print(f"  {trade_type}: {count}개")
        
        # 샘플 출력
        print("\n샘플 매물 (최대 3개):")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n  [{i}] {article.get('articleName', '이름없음')}")
            print(f"      타입: {article.get('tradeTypeName')}")
            print(f"      가격: {article.get('dealOrWarrantPrc', 0):,}만원")
            if article.get('rentPrc'):
                print(f"      월세: {article.get('rentPrc', 0):,}만원")
            print(f"      면적: {article.get('area1', 0)}㎡")
            print(f"      주소: {article.get('roadAddress', article.get('address', '주소없음'))}")

def test_performance():
    """성능 테스트: 클러스터 vs 일반 수집"""
    print("\n\n=== 성능 비교 테스트 ===\n")
    
    collector = ClusterBasedCollector()
    
    if not collector.load_token():
        print("❌ 토큰을 찾을 수 없습니다.")
        return
    
    # 중간 크기 영역 (약 2km x 2km)
    medium_bounds = {
        'north': 37.5100,
        'south': 37.4900,
        'east': 127.0400,
        'west': 127.0200
    }
    
    # 1. 클러스터 정보
    clusters = collector.get_clusters(medium_bounds, zoom=14)
    if clusters:
        total_expected = sum(c['count'] for c in clusters)
        print(f"클러스터 분석:")
        print(f"  클러스터 수: {len(clusters)}개")
        print(f"  예상 매물: {total_expected}개")
        print(f"  예상 API 호출: {len(clusters)}회 (클러스터별 1회)")
    
    # 2. 일반 수집 예상
    print(f"\n일반 수집 예상:")
    print(f"  페이지당 20개 매물")
    print(f"  예상 페이지: {total_expected // 20 + 1}개")
    print(f"  예상 API 호출: {total_expected // 20 + 1}회")
    
    # 3. 효율성 비교
    if clusters and total_expected > 0:
        cluster_efficiency = total_expected / len(clusters)
        page_efficiency = 20
        print(f"\n효율성 비교:")
        print(f"  클러스터 방식: 호출당 {cluster_efficiency:.1f}개 매물")
        print(f"  페이지 방식: 호출당 {page_efficiency}개 매물")
        print(f"  효율성 향상: {cluster_efficiency/page_efficiency:.1f}배")

def main():
    """테스트 메인 함수"""
    print("🧪 클러스터 수집기 테스트\n")
    
    print("테스트 항목:")
    print("1. 클러스터 API 분석")
    print("2. 작은 지역 수집 테스트")
    print("3. 성능 비교 테스트")
    print("4. 전체 테스트 실행")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        test_cluster_analysis()
    elif choice == "2":
        test_small_area_collection()
    elif choice == "3":
        test_performance()
    elif choice == "4":
        test_cluster_analysis()
        test_small_area_collection()
        test_performance()
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()