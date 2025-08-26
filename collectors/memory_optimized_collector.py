#!/usr/bin/env python3
"""
메모리 최적화된 네이버 부동산 수집기
- 실시간 DB 저장 (JSON 파일 불필요)
- 배치 단위 처리 (50개씩)
- 메모리 사용량 최소화
- 중단점 복구 기능
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta
from optimized_supabase_client import OptimizedSupabaseHelper
from kakao_address_converter import KakaoAddressConverter

class MemoryOptimizedCollector:
    def __init__(self, batch_size=50):
        """메모리 최적화 수집기 초기화"""
        self.batch_size = batch_size  # 배치 크기
        self.token_file = os.path.join(os.path.dirname(__file__), 'cached_token.json')
        self.token = None
        self.cookies = {}
        self.token_expires_at = None
        
        # 최적화된 Supabase 클라이언트
        self.db = OptimizedSupabaseHelper()
        
        # 주소 변환기
        try:
            self.address_converter = KakaoAddressConverter()
            print("🗺️ 카카오 주소 변환기 활성화")
        except ValueError as e:
            print(f"⚠️ 주소 변환기 비활성화: {e}")
            self.address_converter = None
        
        # 캐시된 토큰 로드
        self.load_cached_token()
    
    def load_cached_token(self):
        """캐시된 토큰 로드"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                expires_at = datetime.fromisoformat(cache_data['expires_at'])
                if datetime.now() < expires_at:
                    self.token = cache_data['token']
                    cookies_list = cache_data.get('cookies', [])
                    if isinstance(cookies_list, list):
                        self.cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
                    else:
                        self.cookies = cookies_list
                    self.token_expires_at = expires_at
                    print(f"✅ 캐시된 토큰 로드 완료 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    return True
                else:
                    print("⏰ 캐시된 토큰이 만료되었습니다")
            except Exception as e:
                print(f"❌ 토큰 캐시 로드 실패: {e}")
        return False
    
    def setup_headers(self):
        """API 요청 헤더 설정"""
        return {
            'authority': 'new.land.naver.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'authorization': f'Bearer {self.token}',
            'referer': 'https://new.land.naver.com/offices?ms=37.4986291,127.0359669,16&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
    
    def save_batch_to_db(self, properties_batch, cortar_no):
        """배치 단위로 DB 저장"""
        if not properties_batch:
            return 0
        
        try:
            # 주소 변환 (필요시) - 간소화
            processed_properties = []
            for prop in properties_batch:
                # 정규화된 데이터 생성
                property_data = self.normalize_property_data(prop, cortar_no)
                processed_properties.append(property_data)
            
            # 쿼리 최적화된 배치 저장 사용
            result = self.db.save_properties_optimized(processed_properties, cortar_no)
            
            saved_count = result.get('saved_count', 0)
            print(f"💾 배치 저장 완료: {saved_count}/{len(properties_batch)}개")
            return saved_count
            
        except Exception as e:
            print(f"❌ 배치 저장 오류: {e}")
            return 0
    
    def normalize_property_data(self, raw_data, cortar_no):
        """매물 데이터를 기존 형식에 맞춰 정규화"""
        return {
            '매물번호': raw_data.get('articleNo', ''),
            '매물명': raw_data.get('articleName', ''),
            '부동산타입': raw_data.get('realEstateTypeName', ''),
            '거래타입': raw_data.get('tradeTypeName', ''),
            '매매가격': raw_data.get('dealOrWarrantPrc', ''),
            '월세': raw_data.get('rentPrc', ''),
            '전용면적': raw_data.get('area1', 0),
            '공급면적': raw_data.get('area2', 0),
            '층정보': raw_data.get('floorInfo', ''),
            '방향': raw_data.get('direction', ''),
            '상세주소': raw_data.get('representativeImgUrl', ''),
            '태그': raw_data.get('tagList', []),
            '설명': raw_data.get('articleFeatureDesc', ''),
            '상세정보': {
                '위치정보': {
                    '정확한_위도': raw_data.get('lat'),
                    '정확한_경도': raw_data.get('lng')
                }
            }
        }
    
    def collect_with_realtime_save(self, cortar_no, dong_name, max_pages=999):
        """실시간 DB 저장 수집 (메모리 최적화)"""
        if not self.token:
            print("❌ 유효한 토큰이 없습니다.")
            return 0
        
        url = "https://new.land.naver.com/api/articles"
        headers = self.setup_headers()
        
        base_params = {
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
            'articleState': ''
        }
        
        total_collected = 0
        batch_buffer = []  # 메모리 최소화: 배치만 유지
        
        print(f"🚀 {dong_name} 실시간 수집 시작 (배치 크기: {self.batch_size})")
        
        try:
            for page in range(1, max_pages + 1):
                params = base_params.copy()
                params['page'] = page
                
                print(f"📄 페이지 {page} 처리 중... (현재 배치: {len(batch_buffer)}개)")
                
                response = requests.get(url, headers=headers, params=params, cookies=self.cookies, timeout=30)
                
                if response.status_code != 200:
                    print(f"❌ API 오류: {response.status_code}")
                    print(f"❌ 응답 내용: {response.text[:500]}")
                    break
                
                data = response.json()
                # 응답 구조에 맞춰 수정
                if 'body' in data:
                    articles = data['body']
                elif 'articleList' in data:
                    articles = data['articleList']
                else:
                    articles = []
                
                print(f"📊 API 응답: status={response.status_code}, articles={len(articles)}")
                if page == 1:  # 첫 페이지만 디버그 출력
                    print(f"🔍 첫 페이지 응답 구조: {list(data.keys())}")
                
                if not articles:
                    print("📭 더 이상 매물이 없습니다.")
                    break
                
                # 배치 버퍼에 추가
                batch_buffer.extend(articles)
                total_collected += len(articles)
                
                # 배치 크기에 도달하면 즉시 DB 저장
                if len(batch_buffer) >= self.batch_size:
                    saved = self.save_batch_to_db(batch_buffer, cortar_no)
                    print(f"✅ 실시간 저장: {saved}개 (총 {total_collected}개 수집)")
                    batch_buffer.clear()  # 메모리 해제
                
                # API 제한 방지
                time.sleep(0.1)
            
            # 마지막 남은 배치 저장
            if batch_buffer:
                saved = self.save_batch_to_db(batch_buffer, cortar_no)
                print(f"✅ 최종 저장: {saved}개")
                batch_buffer.clear()
        
        except Exception as e:
            print(f"❌ 수집 중 오류: {e}")
            # 오류 발생 시에도 마지막 배치 저장 시도
            if batch_buffer:
                print("🔄 오류 발생, 마지막 배치 저장 시도...")
                self.save_batch_to_db(batch_buffer, cortar_no)
        
        print(f"🎯 {dong_name} 수집 완료: 총 {total_collected}개 매물")
        return total_collected

def collect_optimized_by_dong(dong_name, cortar_no, batch_size=50):
    """동별 메모리 최적화 수집"""
    print(f"🚀 메모리 최적화 수집 시작: {dong_name} ({cortar_no})")
    
    try:
        collector = MemoryOptimizedCollector(batch_size=batch_size)
        total = collector.collect_with_realtime_save(cortar_no, dong_name)
        
        return {
            'success': total > 0,
            'dong_name': dong_name,
            'count': total,
            'method': '실시간_DB_저장'
        }
    
    except Exception as e:
        print(f"❌ 수집 오류: {e}")
        return {
            'success': False,
            'dong_name': dong_name,
            'count': 0,
            'error': str(e)
        }

if __name__ == "__main__":
    # 테스트: 역삼동 메모리 최적화 수집
    result = collect_optimized_by_dong("역삼동", "1168010100", batch_size=50)
    print(f"🎯 결과: {result}")