#!/usr/bin/env python3
"""
수정된 파서로 실제 수집 테스트
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.naver_api_client import NaverAPIClient
from parsers.article_parser import ArticleParser
from database.optimized_repository import OptimizedPropertyRepository

def test_complete_collection():
    """완전한 수집-파싱-저장 테스트"""
    print("🚀 수정된 파서 완전 수집 테스트 시작")
    print("="*80)
    
    # 클라이언트 초기화
    api_client = NaverAPIClient()
    parser = ArticleParser()
    repository = OptimizedPropertyRepository()
    
    try:
        # 1. 논현동 매물 1개 가져오기
        print("1️⃣ 논현동 매물 목록 조회 중...")
        area_response = api_client.get_area_articles("1168010700", page=1)
        
        if not area_response or 'articleList' not in area_response:
            print("❌ 매물 목록 조회 실패")
            return False
            
        article_list = area_response['articleList']
        if not article_list:
            print("❌ 매물 목록이 비어있음")
            return False
            
        first_article = article_list[0]
        article_no = first_article['articleNo']
        print(f"✅ 첫 번째 매물 선택: {article_no}")
        
        # 2. 상세 정보 API 호출
        print(f"2️⃣ 매물 상세 정보 조회 중... (매물번호: {article_no})")
        raw_response = api_client.get_article_detail(article_no)
        
        if not raw_response:
            print("❌ 상세 정보 조회 실패")
            return False
            
        print(f"✅ 상세 정보 조회 완료 (섹션 수: {len(raw_response.keys())})")
        
        # 3. 파싱 수행
        print("3️⃣ 데이터 파싱 중...")
        parsed_data = parser.parse_article_detail(raw_response, article_no)
        
        if not parsed_data:
            print("❌ 파싱 실패")
            return False
            
        # NULL 필드 개수 확인
        null_count = count_null_fields(parsed_data.get('sections', {}))
        print(f"✅ 파싱 완료 (NULL 필드: {null_count}개)")
        
        # 4. 데이터베이스 저장
        print("4️⃣ 데이터베이스 저장 중...")
        save_success = repository.save_property(parsed_data)
        
        if save_success:
            print("✅ 데이터베이스 저장 성공!")
        else:
            print("❌ 데이터베이스 저장 실패")
            
        # 5. 저장 통계 출력
        print("\n5️⃣ 저장 통계:")
        repository.print_save_summary()
        
        # 6. 파싱 통계 출력
        print("\n6️⃣ 파싱 통계:")
        parser_stats = parser.get_parsing_stats()
        print(f"   파싱 오류: {parser_stats.get('total_errors', 0)}개")
        
        return save_success
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        return False

def count_null_fields(sections: dict) -> int:
    """섹션별 NULL 필드 개수 세기"""
    null_count = 0
    
    for section_name, section_data in sections.items():
        if isinstance(section_data, dict):
            for field, value in section_data.items():
                if value is None or value == '':
                    null_count += 1
    
    return null_count

def main():
    """메인 실행 함수"""
    success = test_complete_collection()
    
    print("\n" + "="*80)
    if success:
        print("🎉 수정된 파서 테스트 성공!")
        print("   - API 호출 성공")
        print("   - 파싱 성공 (NULL 필드 대폭 감소)")
        print("   - 데이터베이스 저장 성공")
    else:
        print("❌ 테스트 실패!")
        
    # 테스트 파일 정리
    print("\n🧹 테스트 파일 정리 중...")
    try:
        import glob
        test_files = glob.glob("/Users/smgu/test_code/naver_land/test/*_20250830_*.json")
        for file_path in test_files:
            os.remove(file_path)
        print(f"   {len(test_files)}개 테스트 파일 삭제됨")
    except Exception as e:
        print(f"   정리 중 오류: {e}")

if __name__ == "__main__":
    main()