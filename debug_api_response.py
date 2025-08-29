#!/usr/bin/env python3
"""
네이버 API 응답 구조 상세 분석
면적 정보가 어디에 숨어있는지 찾기
"""

import sys
from pathlib import Path
import json

# 경로 설정
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def analyze_api_response():
    """실제 API 응답에서 면적 정보 찾기"""
    
    print("🔍 네이버 API 응답 구조 분석")
    print("="*50)
    
    try:
        from enhanced_data_collector import EnhancedNaverCollector
        
        collector = EnhancedNaverCollector()
        
        # 실제 매물 하나의 상세 정보 가져오기
        print("📋 실제 매물 데이터 수집 중...")
        
        # 강남구 역삼동 매물 리스트 먼저 가져오기  
        list_url = "https://new.land.naver.com/api/articles/list"
        
        params = {
            'cortarNo': '1168010500',  # 역삼동
            'rletTpCd': 'OPST',        # 오피스텔/상가
            'dealTpCd': 'A1',          # 전월세
            'tag': '::::::',
            'rentPrc': '',
            'prk': '',
            'room': '',
            'btm': '',
            'top': '',
            'area': '',
            'page': 1,
            'size': 5  # 5개만
        }
        
        headers = {
            'authorization': collector.token,
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ko',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        import requests
        response = requests.get(list_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articleList', [])
            
            if articles:
                first_article = articles[0]
                article_no = first_article.get('articleNo')
                
                print(f"📄 매물 {article_no} 상세 정보 분석")
                
                # 상세 정보 API 호출
                detail_url = "https://new.land.naver.com/api/articles/detail"
                detail_params = {
                    'articleNo': article_no,
                    'rletTpCd': first_article.get('rletTpCd'),
                    'tradeType': first_article.get('tradeTypeName')
                }
                
                detail_response = requests.get(detail_url, headers=headers, params=detail_params)
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    
                    print("\n🔍 API 응답 구조 분석:")
                    print(f"최상위 키들: {list(detail_data.keys())}")
                    
                    # 각 섹션별 분석
                    sections_to_check = [
                        'articleDetail', 'articleAddition', 'articleSpace', 
                        'articleFloor', 'articlePrice', 'articlePhotos'
                    ]
                    
                    for section in sections_to_check:
                        if section in detail_data:
                            section_data = detail_data[section]
                            print(f"\n📋 {section} 섹션:")
                            print(f"   키들: {list(section_data.keys()) if isinstance(section_data, dict) else 'Not a dict'}")
                            
                            # 면적 관련 키워드 찾기
                            area_keywords = ['area', 'space', 'size', 'pyeong', '평', '㎡', 'supply', 'exclusive', 'floor', 'total']
                            
                            if isinstance(section_data, dict):
                                for key, value in section_data.items():
                                    if any(keyword in key.lower() for keyword in area_keywords):
                                        print(f"   🎯 면적 관련: {key} = {value}")
                                    elif any(keyword in str(value).lower() for keyword in ['㎡', '평']):
                                        print(f"   🎯 면적 값 발견: {key} = {value}")
                    
                    # JSON 전체 저장해서 수동 분석 가능하도록
                    with open('api_response_debug.json', 'w', encoding='utf-8') as f:
                        json.dump(detail_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"\n💾 전체 API 응답을 api_response_debug.json에 저장했습니다")
                    print("수동으로 파일을 열어서 면적 정보를 찾아보세요!")
                    
                    return True
                else:
                    print(f"❌ 상세 정보 API 오류: {detail_response.status_code}")
                    
            else:
                print("❌ 매물 리스트가 비어있습니다")
        else:
            print(f"❌ 매물 리스트 API 오류: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 분석 중 오류: {e}")
        return False

def search_area_in_text():
    """매물 설명 텍스트에서 면적 정보 추출 테스트"""
    
    print(f"\n📝 매물 설명에서 면적 추출 테스트")
    print("-"*30)
    
    # 실제 매물 설명 예시 (위에서 본 것들)
    test_descriptions = [
        "임대면적 약 53평, 전용면적 : 약 80평(임대인 고지면적)",
        "전용 192.28㎡/49.6㎡",
        "사무실 : 102/49㎡, 12/12층",
        "연면적:192.28㎡/49.6㎡"
    ]
    
    import re
    
    for desc in test_descriptions:
        print(f"\n텍스트: {desc}")
        
        # 면적 패턴들
        patterns = [
            r'(\d+(?:\.\d+)?)\s*평',           # "53평", "80평"  
            r'(\d+(?:\.\d+)?)\s*㎡',           # "192.28㎡"
            r'(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\s*㎡',  # "192.28/49.6㎡"
            r'면적.*?(\d+(?:\.\d+)?)',          # "전용면적 : 약 80"
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, desc)
            if matches:
                print(f"   패턴 {i+1}: {matches}")

if __name__ == "__main__":
    analyze_api_response()
    search_area_in_text()