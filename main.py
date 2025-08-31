#!/usr/bin/env python3
"""
네이버 부동산 수집기 v2.0 - 리팩토링된 메인 진입점
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from services.collection_service import CollectionService

def main():
    parser = argparse.ArgumentParser(description='네이버 부동산 데이터 수집기 v2.0')
    parser.add_argument('--area', type=str, help='수집할 지역 코드 (예: 1168010600)')
    parser.add_argument('--article', type=str, help='특정 매물 번호 수집')
    parser.add_argument('--max-pages', type=int, help='최대 페이지 수')
    parser.add_argument('--max-articles', type=int, help='최대 매물 수')
    parser.add_argument('--gangnam', action='store_true', help='강남구 전체 수집')
    parser.add_argument('--priority', action='store_true', help='우선순위 순서로 전체 지역 수집')
    parser.add_argument('--high-priority', action='store_true', help='높은 우선순위 지역만 수집 (20점 이상)')
    
    args = parser.parse_args()
    
    # 수집 서비스 초기화
    print("🚀 네이버 부동산 수집기 v2.0 시작")
    print("="*50)
    
    try:
        service = CollectionService()
        
        if args.article:
            print(f"📋 단일 매물 수집: {args.article}")
            success = service.collect_single_article(args.article)
            if success:
                print("✅ 매물 수집 완료")
            else:
                print("❌ 매물 수집 실패")
                
        elif args.area:
            print(f"🏢 지역 수집: {args.area}")
            result = service.collect_and_save_area(
                args.area, 
                max_pages=args.max_pages,
                max_articles=args.max_articles
            )
            
            print(f"\n📊 지역 {args.area} 수집 결과:")
            print(f"   발견된 매물: {result['total_found']}개")
            print(f"   성공적으로 저장: {result['successful_collections']}개")
            print(f"   성공률: {result['success_rate']}")
            
        elif args.gangnam:
            print("🏙️ 강남구 전체 수집")
            from config.area_codes import get_gangnam_areas
            gangnam_areas = get_gangnam_areas()
            
            total_results = []
            for area in gangnam_areas:
                print(f"\n🔍 {area['name']} 수집 중...")
                result = service.collect_and_save_area(
                    area['code'], 
                    max_pages=args.max_pages,
                    max_articles=args.max_articles
                )
                result['area_name'] = area['name']
                total_results.append(result)
            
            print("\n📊 강남구 전체 수집 결과:")
            total_found = sum(r['total_found'] for r in total_results)
            total_success = sum(r['successful_collections'] for r in total_results)
            
            print(f"   총 발견된 매물: {total_found}개")
            print(f"   총 성공적으로 저장: {total_success}개")
            print(f"   전체 성공률: {(total_success/total_found*100):.2f}%" if total_found > 0 else "0%")
            
            print("\n📍 지역별 상세 결과:")
            for result in total_results:
                print(f"   {result['area_name']}: {result['successful_collections']}/{result['total_found']} ({result['success_rate']})")
        
        elif args.priority:
            print("🏅 강남구 우선순위 순서로 전체 지역 수집")
            from config.area_codes import get_all_priority_areas
            priority_areas = get_all_priority_areas()
            
            total_results = []
            for area in priority_areas:
                print(f"\n🔍 {area['name']} (우선순위: {area['priority']}점) 수집 중...")
                result = service.collect_and_save_area(
                    area['code'], 
                    max_pages=args.max_pages,
                    max_articles=args.max_articles
                )
                result['area_name'] = area['name']
                result['priority'] = area['priority']
                total_results.append(result)
            
            print("\n📍 강남구 지역별 상세 결과 (우선순위순):")
            for result in total_results:
                print(f"   {result['area_name']} ({result['priority']}점): {result['successful_collections']}/{result['total_found']} ({result['success_rate']})")
        
        elif args.high_priority:
            print("⭐ 강남구 높은 우선순위 지역만 수집 (20점 이상)")
            from config.area_codes import get_high_priority_areas
            high_priority_areas = get_high_priority_areas(min_score=20)
            
            total_results = []
            for area in high_priority_areas:
                print(f"\n🔍 {area['name']} (우선순위: {area['priority']}점) 수집 중...")
                result = service.collect_and_save_area(
                    area['code'], 
                    max_pages=args.max_pages,
                    max_articles=args.max_articles
                )
                result['area_name'] = area['name']
                result['priority'] = area['priority']
                total_results.append(result)
            
            print("\n📍 강남구 높은 우선순위 지역 결과:")
            for result in total_results:
                print(f"   {result['area_name']} ({result['priority']}점): {result['successful_collections']}/{result['total_found']} ({result['success_rate']})")
        
        else:
            print("❌ 수집할 대상을 지정해주세요:")
            print("   --area AREA_CODE     : 특정 지역 수집")
            print("   --article ARTICLE_NO : 특정 매물 수집") 
            print("   --gangnam           : 강남구 전체 수집")
            print("   --priority          : 강남구 우선순위 순서로 전체 지역 수집")
            print("   --high-priority     : 강남구 높은 우선순위 지역만 수집 (20점 이상)")
            print("\n예시:")
            print("   python main.py --area 1168010600 --max-articles 10")
            print("   python main.py --article 2390390123")
            print("   python main.py --gangnam --max-pages 2")
            print("   python main.py --priority --max-articles 5")
            print("   python main.py --high-priority --max-pages 1")
            return
        
        # 최종 통계 출력
        service.print_final_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()