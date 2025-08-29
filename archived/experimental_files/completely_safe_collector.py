#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완전히 안전한 수집기 - DB 저장/삭제 일체 없음
기존 함수들을 사용하지 않고 순수 수집만 실행
"""

import os
import json
from datetime import datetime
from fixed_naver_collector_v2_optimized import CachedTokenCollector

def safe_collect_only(cortar_no: str, max_pages: int = 2):
    """
    완전히 안전한 수집 - DB 작업 일체 없음
    CachedTokenCollector의 collect_articles만 사용
    """
    
    print(f"🛡️ 완전 안전 수집기 v1.0")
    print(f"🎯 지역코드: {cortar_no}")
    print(f"📄 최대 페이지: {max_pages}")
    print("⚠️ DB 저장/삭제 일체 없음!")
    print("=" * 50)
    
    # 지역 정보 하드코딩 (DB 조회하지 않음)
    area_mapping = {
        "1168010100": {"dong_name": "역삼동", "center_lat": 37.500775, "center_lon": 127.0359}
    }
    
    if cortar_no not in area_mapping:
        print(f"❌ 지원하지 않는 지역 코드: {cortar_no}")
        print(f"📋 지원 지역: {list(area_mapping.keys())}")
        return None
    
    area_info = area_mapping[cortar_no]
    dong_name = area_info["dong_name"]
    
    print(f"🎯 수집 대상: {dong_name} ({cortar_no})")
    
    try:
        # 수집기 생성 (주소 변환기 활성화)
        collector = CachedTokenCollector(use_address_converter=True)
        
        # 결과 파일 경로 설정
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"safe_collect_{dong_name}_{cortar_no}_{timestamp}.json"
        results_dir = os.path.join(os.path.dirname(__file__), 'safe_results')
        os.makedirs(results_dir, exist_ok=True)
        filepath = os.path.join(results_dir, filename)
        
        # 수집 실행 (collect_articles 직접 호출)
        print("🔄 순수 수집 실행...")
        
        parsed_url = {
            "direct_cortar": True, 
            "dong_name": dong_name,
            "center_lat": area_info["center_lat"],
            "center_lon": area_info["center_lon"]
        }
        
        # JSON 파일 시작
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write('  "수집정보": {\n')
            f.write('    "수집시간": "' + timestamp + '",\n')
            f.write('    "지역코드": "' + cortar_no + '",\n')
            f.write('    "동이름": "' + dong_name + '",\n')
            f.write('    "수집방식": "완전안전_수집전용",\n')
            f.write('    "DB저장": false,\n')
            f.write('    "DB삭제": false,\n')
            f.write('    "버전": "safe_v1.0"\n')
            f.write('  },\n')
            
            # 🔥 핵심: collect_articles만 호출 (DB 작업 없음)
            total_collected = collector.collect_articles(
                cortar_no=cortar_no,
                parsed_url=parsed_url,
                max_pages=max_pages,
                include_details=True,
                output_file=f
            )
            
            f.write('\n}')
        
        print(f"✅ 안전 수집 완료: {total_collected}개 매물")
        print(f"📄 결과 파일: {filepath}")
        
        return {
            'success': True,
            'total_collected': total_collected,
            'file_path': filepath,
            'dong_name': dong_name,
            'cortar_no': cortar_no,
            'method': 'safe_collect_only'
        }
        
    except Exception as e:
        print(f"❌ 수집 중 오류: {str(e)}")
        return None

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='완전히 안전한 수집기')
    parser.add_argument('cortar_no', help='수집할 지역 코드')
    parser.add_argument('--max-pages', type=int, default=2, help='최대 수집 페이지')
    
    args = parser.parse_args()
    
    result = safe_collect_only(args.cortar_no, args.max_pages)
    
    if result:
        print(f"\n🎯 수집 결과:")
        print(f"   상태: {result['success']}")
        print(f"   수집량: {result['total_collected']}개 매물")
        print(f"   파일: {result['file_path']}")
        print(f"   방식: {result['method']}")
        print(f"\n💡 다음: json_to_db_converter로 변환 테스트")
        
    else:
        print("\n❌ 수집 실패")
        return 1

if __name__ == "__main__":
    main()