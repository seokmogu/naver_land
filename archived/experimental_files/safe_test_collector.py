#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완전 안전한 테스트용 수집기
DB에 아무것도 저장하지 않고 수집+변환만 테스트
"""

import sys
import os
from datetime import datetime, date
from fixed_naver_collector_v2_optimized import collect_by_cortar_no
from json_to_db_converter import convert_json_to_properties

def safe_test_collection(cortar_no: str, max_pages: int = 2):
    """완전 안전한 테스트 - DB 저장 없음"""
    
    print(f"🧪 완전 안전한 테스트 수집기")
    print(f"🎯 지역: {cortar_no}, 페이지: {max_pages}")
    print("⚠️ DB에 아무것도 저장하지 않습니다!")
    print("=" * 50)
    
    # 1. 데이터 수집
    print("🔄 데이터 수집 중...")
    collected_result = collect_by_cortar_no(
        cortar_no=cortar_no, 
        include_details=True, 
        max_pages=max_pages
    )
    
    if not collected_result or collected_result.get('total_collected', 0) == 0:
        print("❌ 수집된 데이터가 없습니다")
        return None
    
    total_collected = collected_result.get('total_collected', 0)
    json_file = collected_result.get('file_path')
    
    print(f"✅ 수집 완료: {total_collected}개 매물")
    print(f"📄 JSON 파일: {json_file}")
    
    # 2. 변환 테스트
    print("🔄 DB 형식으로 변환 테스트...")
    db_properties = convert_json_to_properties(json_file, cortar_no)
    
    if not db_properties:
        print("❌ 변환된 데이터가 없습니다")
        return None
    
    print(f"✅ 변환 완료: {len(db_properties)}개 매물")
    
    # 3. 품질 검증
    quality_result = validate_quality(db_properties)
    print(f"📊 데이터 품질: {quality_result['quality_grade']} ({quality_result['quality_score']:.1f}%)")
    
    # 4. 샘플 데이터 출력
    if db_properties:
        print("\n📝 변환된 샘플 데이터 (첫 번째 매물):")
        sample = db_properties[0]
        for key, value in list(sample.items())[:10]:
            if isinstance(value, str) and len(str(value)) > 50:
                value = str(value)[:47] + "..."
            print(f"   {key}: {value}")
        
        # 중요 필드 체크
        print(f"\n🔍 중요 필드 체크:")
        print(f"   매물번호: {sample.get('article_no', 'N/A')}")
        print(f"   주소(도로명): {sample.get('address_road', 'N/A')}")
        print(f"   위도: {sample.get('latitude', 'N/A')}")
        print(f"   경도: {sample.get('longitude', 'N/A')}")
    
    return {
        'status': 'test_success',
        'collected_count': total_collected,
        'converted_count': len(db_properties),
        'quality': quality_result,
        'json_file': json_file,
        'sample_data': db_properties[0] if db_properties else None
    }

def validate_quality(properties):
    """데이터 품질 검증"""
    if not properties:
        return {'quality_score': 0, 'quality_grade': 'F (데이터없음)'}
    
    total = len(properties)
    
    # 필수 필드 검증
    missing_article_no = sum(1 for p in properties if not p.get('article_no'))
    missing_address = sum(1 for p in properties if not p.get('address_road'))
    missing_coords = sum(1 for p in properties 
                       if not p.get('latitude') or not p.get('longitude')
                       or p.get('latitude') == 0 or p.get('longitude') == 0)
    
    # 품질 점수 계산
    address_rate = (total - missing_address) / total * 100
    coord_rate = (total - missing_coords) / total * 100
    data_integrity = (total - missing_article_no) / total * 100
    
    quality_score = (address_rate + coord_rate + data_integrity) / 3
    
    # 등급 매기기
    if quality_score >= 90:
        grade = 'A (우수)'
    elif quality_score >= 80:
        grade = 'B (양호)'
    elif quality_score >= 70:
        grade = 'C (보통)'
    elif quality_score >= 50:
        grade = 'D (개선필요)'
    else:
        grade = 'F (심각)'
    
    return {
        'quality_score': quality_score,
        'quality_grade': grade,
        'address_rate': address_rate,
        'coord_rate': coord_rate,
        'data_integrity': data_integrity,
        'total_count': total,
        'missing_fields': {
            'article_no': missing_article_no,
            'address': missing_address,
            'coordinates': missing_coords
        }
    }

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='완전 안전한 테스트 수집기')
    parser.add_argument('cortar_no', help='수집할 지역 코드 (예: 1168010100)')
    parser.add_argument('--max-pages', type=int, default=2, help='최대 수집 페이지')
    
    args = parser.parse_args()
    
    result = safe_test_collection(args.cortar_no, args.max_pages)
    
    if result:
        print(f"\n🎯 테스트 결과:")
        print(f"   상태: {result['status']}")
        print(f"   수집: {result['collected_count']}개")
        print(f"   변환: {result['converted_count']}개")
        print(f"   품질: {result['quality']['quality_grade']}")
        
        quality = result['quality']
        print(f"\n📊 상세 품질 지표:")
        print(f"   주소 완성도: {quality['address_rate']:.1f}%")
        print(f"   좌표 완성도: {quality['coord_rate']:.1f}%")
        print(f"   데이터 무결성: {quality['data_integrity']:.1f}%")
        
        missing = quality['missing_fields']
        if any(missing.values()):
            print(f"\n⚠️ 누락 필드:")
            if missing['article_no']:
                print(f"   매물번호 누락: {missing['article_no']}개")
            if missing['address']:
                print(f"   주소 누락: {missing['address']}개")  
            if missing['coordinates']:
                print(f"   좌표 누락: {missing['coordinates']}개")
        else:
            print(f"\n✅ 모든 필수 필드 완전!")
        
        print(f"\n💡 다음 단계: DB 저장 기능이 안전하다면 실제 저장 테스트 진행")
        
    else:
        print("\n❌ 테스트 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()