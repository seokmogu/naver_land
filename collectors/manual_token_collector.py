#!/usr/bin/env python3
"""
수동 토큰 입력 기반 수집기
VM에서 토큰 자동 획득이 어려울 때 사용
"""

import requests
import json
from datetime import datetime

class ManualTokenCollector:
    def __init__(self, token=None):
        if token:
            self.token = token
        else:
            self.token = self.get_manual_token()
        
        self.headers = {
            'authorization': f'Bearer {self.token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://new.land.naver.com/',
        }
    
    def get_manual_token(self):
        """수동으로 토큰 입력받기"""
        print("🔑 네이버 부동산 토큰을 수동으로 입력해주세요.")
        print("   1. https://new.land.naver.com/offices 접속")
        print("   2. 개발자 도구 > Network 탭 열기")
        print("   3. 페이지 새로고침")
        print("   4. API 호출에서 Authorization: Bearer 토큰 복사")
        print()
        
        while True:
            token = input("토큰을 입력하세요 (Bearer 제외): ").strip()
            if token:
                if token.startswith('Bearer '):
                    token = token[7:]
                
                # 토큰 유효성 테스트
                if self.test_token(token):
                    print("✅ 토큰이 유효합니다!")
                    return token
                else:
                    print("❌ 토큰이 유효하지 않습니다. 다시 입력해주세요.")
            else:
                print("토큰을 입력해주세요.")
    
    def test_token(self, token):
        """토큰 유효성 테스트"""
        test_headers = {
            'authorization': f'Bearer {token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://new.land.naver.com/',
        }
        
        try:
            response = requests.get(
                "https://new.land.naver.com/api/cortars",
                headers=test_headers,
                params={
                    'zoom': 15,
                    'centerLat': 37.4986291,
                    'centerLon': 127.0359669
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def collect_area_data(self, lat, lon, zoom=15):
        """지역 데이터 수집"""
        print(f"🔍 지역 데이터 수집: 위도 {lat}, 경도 {lon}")
        
        try:
            response = requests.get(
                "https://new.land.naver.com/api/cortars",
                headers=self.headers,
                params={
                    'zoom': zoom,
                    'centerLat': lat,
                    'centerLon': lon
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 지역 데이터 획득 성공")
                return data
            else:
                print(f"❌ 지역 데이터 획득 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None
    
    def collect_properties(self, cortar_no, max_pages=5):
        """매물 데이터 수집"""
        print(f"🏢 매물 수집 시작: {cortar_no}")
        
        all_properties = []
        page = 1
        
        while page <= max_pages:
            print(f"📄 페이지 {page} 수집 중...")
            
            try:
                response = requests.get(
                    "https://new.land.naver.com/api/articles",
                    headers=self.headers,
                    params={
                        'cortarNo': cortar_no,
                        'order': 'rank',
                        'realEstateType': 'SG:SMS:GJCG:APTHGJ:GM:TJ',
                        'tradeType': '',
                        'tag': '::::::::',
                        'rentPriceMin': '0',
                        'rentPriceMax': '900000000',
                        'priceMin': '0',
                        'priceMax': '900000000',
                        'areaMin': '0',
                        'areaMax': '900000000',
                        'oldBuildYears': '',
                        'recentlyBuildYears': '',
                        'minHouseHoldCount': '',
                        'maxHouseHoldCount': '',
                        'showArticle': 'false',
                        'sameAddressGroup': 'false',
                        'minMaintenanceCost': '',
                        'maxMaintenanceCost': '',
                        'priceType': 'RETAIL',
                        'directions': '',
                        'articleState': '',
                        'page': page
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articleList', [])
                    
                    if not articles:
                        print(f"   페이지 {page}: 매물 없음")
                        break
                    
                    print(f"   페이지 {page}: {len(articles)}개 매물 수집")
                    all_properties.extend(articles)
                    
                    # 다음 페이지가 있는지 확인
                    if len(articles) < 20:  # 한 페이지당 보통 20개
                        break
                    
                    page += 1
                    
                else:
                    print(f"❌ 페이지 {page} 수집 실패: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"❌ 페이지 {page} 오류: {e}")
                break
        
        print(f"✅ 총 {len(all_properties)}개 매물 수집 완료")
        return all_properties

def main():
    print("🚀 수동 토큰 기반 네이버 부동산 수집기")
    print("=" * 50)
    
    # 토큰 입력 또는 자동 획득 시도
    collector = ManualTokenCollector()
    
    # 테스트 수집
    lat, lon = 37.4986291, 127.0359669
    area_data = collector.collect_area_data(lat, lon)
    
    if area_data:
        print(f"📋 지역 정보: {area_data}")
        
        # 첫 번째 지역의 매물 수집
        if isinstance(area_data, list) and area_data:
            cortar_no = area_data[0].get('cortarNo')
        elif isinstance(area_data, dict):
            cortar_no = area_data.get('cortarNo')
        else:
            cortar_no = None
        
        if cortar_no:
            properties = collector.collect_properties(cortar_no)
            
            # 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"manual_collection_{cortar_no}_{timestamp}.json"
            
            result = {
                "수집정보": {
                    "수집시간": timestamp,
                    "지역코드": cortar_no,
                    "수집방식": "수동_토큰_기반",
                    "지역데이터": area_data
                },
                "매물목록": properties
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"💾 결과 저장: {filename}")

if __name__ == "__main__":
    main()