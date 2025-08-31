#!/usr/bin/env python3
"""
네이버 부동산 수집기 NULL 값 디버깅 스크립트

1. 실제 API 응답 캡처 및 분석
2. 파싱 과정 단계별 디버깅  
3. 데이터베이스 저장 과정 디버깅
4. NULL이 되는 정확한 시점과 이유 파악
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.naver_api_client import NaverAPIClient
from parsers.article_parser import ArticleParser
from database.optimized_repository import OptimizedPropertyRepository

class NullFieldDebugger:
    def __init__(self):
        self.api_client = NaverAPIClient()
        self.parser = ArticleParser()
        self.repository = OptimizedPropertyRepository()
        self.debug_results = {
            'api_response': None,
            'parsing_results': {},
            'field_analysis': {},
            'null_fields': []
        }
        
    def debug_single_article(self, area_code: str = "1168010700") -> Dict[str, Any]:
        """단일 매물에 대해 전체 파이프라인 디버깅"""
        print(f"\n🔍 NULL 필드 디버깅 시작 - 지역코드: {area_code}")
        print("="*80)
        
        # 1단계: API에서 매물 목록 가져오기
        print("\n1️⃣ API 매물 목록 조회 중...")
        area_response = self.api_client.get_area_articles(area_code, page=1)
        
        if not area_response or 'articleList' not in area_response:
            print("❌ 매물 목록 조회 실패")
            return self.debug_results
            
        article_list = area_response['articleList']
        if not article_list:
            print("❌ 매물 목록이 비어있음")
            return self.debug_results
            
        # 첫 번째 매물 선택
        first_article = article_list[0]
        article_no = first_article['articleNo']
        print(f"✅ 첫 번째 매물 선택: {article_no}")
        
        # 2단계: 상세 정보 API 호출
        print(f"\n2️⃣ 매물 상세 정보 API 호출 중... (매물번호: {article_no})")
        raw_response = self.api_client.get_article_detail(article_no)
        
        if not raw_response:
            print("❌ 상세 정보 API 호출 실패")
            return self.debug_results
            
        # API 응답 저장
        self.debug_results['api_response'] = raw_response
        self._save_api_response(article_no, raw_response)
        
        print(f"✅ API 응답 수신 완료")
        print(f"   섹션 수: {len(raw_response.keys())}")
        print(f"   섹션 목록: {list(raw_response.keys())}")
        
        # 3단계: 섹션별 원본 데이터 분석
        print(f"\n3️⃣ API 응답 섹션별 분석...")
        self._analyze_api_sections(raw_response)
        
        # 4단계: 파싱 과정 디버깅
        print(f"\n4️⃣ 파싱 과정 단계별 디버깅...")
        parsed_data = self._debug_parsing_process(raw_response, article_no)
        
        if not parsed_data:
            print("❌ 파싱 실패")
            return self.debug_results
            
        # 5단계: 파싱 결과 분석
        print(f"\n5️⃣ 파싱 결과 분석...")
        self._analyze_parsed_data(parsed_data)
        
        # 6단계: 데이터베이스 저장 과정 디버깅 (실제로는 저장하지 않음)
        print(f"\n6️⃣ 데이터베이스 저장 데이터 구조 분석...")
        self._analyze_database_mapping(parsed_data)
        
        # 7단계: NULL 필드 종합 분석
        print(f"\n7️⃣ NULL 필드 종합 분석...")
        self._comprehensive_null_analysis()
        
        # 결과 저장
        self._save_debug_results(article_no)
        
        return self.debug_results
    
    def _analyze_api_sections(self, raw_response: Dict):
        """API 응답 섹션별 분석"""
        for section_name, section_data in raw_response.items():
            print(f"\n   📋 {section_name} 섹션:")
            
            if section_data is None:
                print(f"      ❌ NULL 섹션")
                continue
                
            if isinstance(section_data, dict):
                non_null_fields = {k: v for k, v in section_data.items() if v is not None and v != ''}
                null_fields = {k: v for k, v in section_data.items() if v is None or v == ''}
                
                print(f"      ✅ 유효한 필드: {len(non_null_fields)}개")
                print(f"      ❌ NULL/빈 필드: {len(null_fields)}개")
                
                # 중요한 필드들 체크
                important_fields = self._get_important_fields_by_section(section_name)
                for field in important_fields:
                    if field in section_data:
                        value = section_data[field]
                        status = "✅" if value is not None and value != '' else "❌"
                        print(f"         {status} {field}: {value}")
                    else:
                        print(f"         ❌ {field}: [필드 없음]")
                        
            elif isinstance(section_data, list):
                print(f"      📝 리스트 형태: {len(section_data)}개 항목")
                if section_data:
                    print(f"         첫 항목 예시: {section_data[0]}")
            else:
                print(f"      📝 값: {section_data}")
    
    def _debug_parsing_process(self, raw_response: Dict, article_no: str) -> Dict:
        """파싱 과정 단계별 디버깅"""
        
        # 전체 파싱 실행
        parsed_data = self.parser.parse_article_detail(raw_response, article_no)
        
        if not parsed_data:
            print("❌ 전체 파싱 실패")
            return None
            
        # 섹션별 파싱 결과 분석
        sections = parsed_data.get('sections', {})
        
        for section_name, section_result in sections.items():
            print(f"\n   🔄 {section_name} 파싱 결과:")
            
            if isinstance(section_result, dict):
                non_null_count = sum(1 for v in section_result.values() if v is not None and v != '')
                null_count = sum(1 for v in section_result.values() if v is None or v == '')
                
                print(f"      ✅ 파싱된 유효 필드: {non_null_count}개")
                print(f"      ❌ 파싱된 NULL 필드: {null_count}개")
                
                # NULL 필드 상세 출력
                for field, value in section_result.items():
                    if value is None or value == '':
                        print(f"         ❌ {field}: {value}")
                    
        self.debug_results['parsing_results'] = parsed_data
        return parsed_data
    
    def _analyze_parsed_data(self, parsed_data: Dict):
        """파싱된 데이터 분석"""
        sections = parsed_data.get('sections', {})
        
        all_null_fields = []
        
        for section_name, section_data in sections.items():
            if isinstance(section_data, dict):
                for field, value in section_data.items():
                    if value is None or value == '':
                        all_null_fields.append({
                            'section': section_name,
                            'field': field,
                            'value': value
                        })
        
        self.debug_results['null_fields'] = all_null_fields
        
        print(f"   총 NULL 필드: {len(all_null_fields)}개")
        
        # 섹션별 NULL 필드 수
        section_null_counts = {}
        for null_field in all_null_fields:
            section = null_field['section']
            section_null_counts[section] = section_null_counts.get(section, 0) + 1
        
        for section, count in section_null_counts.items():
            print(f"      {section}: {count}개")
    
    def _analyze_database_mapping(self, parsed_data: Dict):
        """데이터베이스 매핑 분석 (실제 저장 없이 구조만 분석)"""
        
        sections = parsed_data.get('sections', {})
        
        # 메인 테이블 매핑 분석
        print(f"\n   📊 naver_properties 테이블 매핑 분석:")
        
        article_detail = sections.get('articleDetail', {})
        article_price = sections.get('articlePrice', {})
        article_space = sections.get('articleSpace', {})
        article_floor = sections.get('articleFloor', {})
        article_facility = sections.get('articleFacility', {})
        
        # 중요 필드들 매핑 상태 확인
        important_mappings = {
            'article_no': parsed_data.get('article_no'),
            'trade_type_name': article_detail.get('trade_type'),
            'real_estate_type_name': article_detail.get('real_estate_type'),
            'building_name': article_detail.get('building_name'),
            'latitude': article_detail.get('latitude'),
            'longitude': article_detail.get('longitude'),
            'exposure_address': article_detail.get('exposure_address'),
            'detail_address': article_detail.get('detail_address'),
            'deal_price': article_price.get('deal_price'),
            'warrant_price': article_price.get('warrant_price'),
            'rent_price': article_price.get('rent_price'),
            'supply_area': article_space.get('supply_area'),
            'exclusive_area': article_space.get('exclusive_area'),
            'total_floor': article_floor.get('total_floor'),
            'current_floor': article_floor.get('current_floor'),
            'elevator_count': article_facility.get('elevator_count')
        }
        
        for field, value in important_mappings.items():
            status = "✅" if value is not None and value != '' else "❌"
            print(f"      {status} {field}: {value}")
    
    def _comprehensive_null_analysis(self):
        """종합적인 NULL 분석"""
        
        print(f"\n📋 종합 NULL 분석 결과:")
        
        null_fields = self.debug_results.get('null_fields', [])
        
        if not null_fields:
            print("   🎉 NULL 필드가 발견되지 않았습니다!")
            return
        
        # 가장 많이 NULL인 섹션 찾기
        section_counts = {}
        for field in null_fields:
            section = field['section']
            section_counts[section] = section_counts.get(section, 0) + 1
        
        print(f"   가장 문제가 많은 섹션:")
        sorted_sections = sorted(section_counts.items(), key=lambda x: x[1], reverse=True)
        for section, count in sorted_sections[:3]:
            print(f"      {section}: {count}개 NULL 필드")
        
        # 필드별 NULL 분석
        critical_null_fields = [
            'trade_type', 'real_estate_type', 'building_name', 
            'latitude', 'longitude', 'deal_price', 'supply_area'
        ]
        
        print(f"\n   중요 필드 NULL 상태:")
        for field in critical_null_fields:
            is_null = any(nf['field'] == field for nf in null_fields)
            status = "❌" if is_null else "✅"
            print(f"      {status} {field}")
    
    def _get_important_fields_by_section(self, section_name: str) -> list:
        """섹션별 중요 필드 목록"""
        important_fields = {
            'articleDetail': ['articleNo', 'realestateTypeName', 'tradeTypeName', 'buildingTypeName', 
                            'latitude', 'longitude', 'exposureAddress', 'detailAddress'],
            'articlePrice': ['dealPrice', 'warrantPrice', 'rentPrice', 'priceBySpace'],
            'articleSpace': ['supplySpace', 'exclusiveSpace', 'totalSpace'],
            'articleFloor': ['totalFloorCount', 'correspondingFloorCount'],
            'articleRealtor': ['address', 'realtorName', 'representativeTelNo'],
            'articleFacility': ['subwayList', 'directionTypeName', 'etcFacilities'],
            'articleTax': ['acquisitionTax', 'brokerFee']
        }
        return important_fields.get(section_name, [])
    
    def _save_api_response(self, article_no: str, raw_response: Dict):
        """API 응답을 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/Users/smgu/test_code/naver_land/test/api_response_{article_no}_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(raw_response, f, ensure_ascii=False, indent=2)
            print(f"   💾 API 응답 저장: {filename}")
        except Exception as e:
            print(f"   ❌ API 응답 저장 실패: {e}")
    
    def _save_debug_results(self, article_no: str):
        """디버깅 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/Users/smgu/test_code/naver_land/test/debug_results_{article_no}_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.debug_results, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 디버깅 결과 저장: {filename}")
        except Exception as e:
            print(f"\n❌ 디버깅 결과 저장 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 네이버 부동산 NULL 필드 디버거 시작")
    
    debugger = NullFieldDebugger()
    
    # 논현동(1168010700) 매물 디버깅
    results = debugger.debug_single_article("1168010700")
    
    print("\n" + "="*80)
    print("🏁 디버깅 완료!")
    
    # 요약 출력
    null_count = len(results.get('null_fields', []))
    if null_count > 0:
        print(f"❌ 발견된 NULL 필드: {null_count}개")
        print("   상세 결과는 저장된 JSON 파일을 확인하세요.")
    else:
        print("✅ NULL 필드가 발견되지 않았습니다!")

if __name__ == "__main__":
    main()