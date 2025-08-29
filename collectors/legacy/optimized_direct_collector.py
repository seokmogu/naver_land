#!/usr/bin/env python3
"""
최적화된 직접 DB 저장 수집기
- JSON 파일 생략하고 직접 DB 저장
- 스트리밍 처리로 메모리 효율성 극대화
- 기존 토큰 관리 로직 재사용
- 실시간 성능 모니터링
"""

import requests
import json
import time
import os
import sys
import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Generator, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

# 상대 경로로 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_supabase_client import EnhancedSupabaseClient
from kakao_address_converter import KakaoAddressConverter

@dataclass
class CollectionSession:
    """수집 세션 정보"""
    cortar_no: str
    region_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_pages: int = 0
    total_properties: int = 0
    success_count: int = 0
    error_count: int = 0
    processing_time: float = 0.0

class OptimizedDirectCollector:
    """최적화된 직접 DB 저장 수집기"""
    
    def __init__(self, batch_size: int = 50, use_address_converter: bool = True):
        """
        최적화된 직접 수집기 초기화
        
        Args:
            batch_size: 배치 처리 크기
            use_address_converter: 주소 변환기 사용 여부
        """
        self.batch_size = batch_size
        
        # Enhanced Supabase 클라이언트 초기화
        self.db_client = EnhancedSupabaseClient(batch_size=batch_size)
        
        # 주소 변환기 초기화
        self.address_converter = None
        if use_address_converter:
            try:
                self.address_converter = KakaoAddressConverter()
                print("🗺️ 카카오 주소 변환기 활성화")
            except ValueError as e:
                print(f"⚠️ 주소 변환기 비활성화: {e}")
        
        # 토큰 관리
        self.token_file = os.path.join(os.path.dirname(__file__), 'cached_token.json')
        self.token = None
        self.cookies = {}
        self.token_expires_at = None
        
        # 캐시된 토큰 로드
        self.load_cached_token()
        
        print(f"✅ 최적화된 직접 수집기 초기화 완료 (배치 크기: {batch_size})")
    
    def collect_region_direct(self, cortar_no: str, region_name: str = "") -> Dict:
        """
        지역 매물을 직접 DB에 저장하면서 수집
        
        Args:
            cortar_no: 행정구역 코드
            region_name: 지역명
            
        Returns:
            Dict: 수집 및 저장 결과
        """
        
        session = CollectionSession(
            cortar_no=cortar_no,
            region_name=region_name,
            start_time=datetime.now()
        )
        
        print(f"\n🚀 최적화된 직접 수집 시작: {region_name} ({cortar_no})")
        print("=" * 60)
        
        try:
            # 1. 토큰 유효성 확인
            if not self._ensure_valid_token():
                return self._create_error_result(session, "토큰 획득 실패")
            
            # 2. 기존 데이터 현황
            print("\n📊 수집 전 현황 확인")
            existing_stats = self.db_client.get_region_statistics(cortar_no)
            existing_count = existing_stats.get('active_properties', 0)
            print(f"   기존 활성 매물: {existing_count:,}개")
            
            # 3. 스트리밍 수집 및 직접 저장
            print(f"\n🔄 스트리밍 수집 시작 (배치 크기: {self.batch_size})")
            
            # 매물 데이터 제너레이터 생성
            property_generator = self._create_property_generator(cortar_no, session)
            
            # 스트리밍 저장 실행
            save_result = self.db_client.stream_save_properties(
                property_generator, 
                cortar_no, 
                region_name
            )
            
            # 4. 최종 결과 정리
            session.end_time = datetime.now()
            session.processing_time = (session.end_time - session.start_time).total_seconds()
            
            if save_result['success']:
                final_stats = self.db_client.get_region_statistics(cortar_no)
                final_count = final_stats.get('active_properties', 0)
                
                result = {
                    'success': True,
                    'region_name': region_name,
                    'cortar_no': cortar_no,
                    'session_info': {
                        'start_time': session.start_time.isoformat(),
                        'end_time': session.end_time.isoformat(),
                        'processing_time': session.processing_time,
                        'total_pages': session.total_pages,
                        'total_properties': session.total_properties
                    },
                    'collection_stats': {
                        'existing_properties': existing_count,
                        'collected_properties': save_result['stats']['total_processed'],
                        'final_properties': final_count,
                        'new_properties': save_result['stats']['total_inserted'],
                        'updated_properties': save_result['stats']['total_updated'],
                        'failed_properties': save_result['stats']['total_errors']
                    },
                    'performance': save_result['performance'],
                    'batch_count': save_result['batch_count']
                }
                
                print(f"\n✅ 최적화된 직접 수집 완료!")
                print(f"   총 처리 시간: {session.processing_time:.1f}초")
                print(f"   페이지 수집: {session.total_pages}개")
                print(f"   매물 처리: {session.total_properties:,}개")
                print(f"   기존: {existing_count:,} → 최종: {final_count:,}개")
                print(f"   신규: {result['collection_stats']['new_properties']:,}개")
                print(f"   업데이트: {result['collection_stats']['updated_properties']:,}개")
                
                return result
            else:
                return self._create_error_result(session, save_result.get('error', '저장 실패'))
                
        except Exception as e:
            print(f"❌ 수집 과정 오류: {e}")
            return self._create_error_result(session, str(e))
    
    def _create_property_generator(self, cortar_no: str, session: CollectionSession) -> Generator[Dict, None, None]:
        """
        매물 데이터 제너레이터 생성
        
        Args:
            cortar_no: 행정구역 코드
            session: 수집 세션 정보
            
        Yields:
            Dict: 변환된 매물 데이터
        """
        
        page = 1
        consecutive_failures = 0
        max_failures = 3
        
        while consecutive_failures < max_failures:
            try:
                print(f"   📄 페이지 {page} 수집 중...")
                
                # API 호출
                page_data = self._fetch_page_data(cortar_no, page)
                
                if not page_data or not page_data.get('body'):
                    print(f"   ⚠️ 페이지 {page}: 데이터 없음, 수집 완료")
                    break
                
                # 매물 리스트 추출
                articles = page_data['body'].get('articleList', [])
                
                if not articles:
                    print(f"   ⚠️ 페이지 {page}: 매물 없음, 수집 완료")
                    break
                
                session.total_pages = page
                page_property_count = 0
                
                # 각 매물을 DB 형식으로 변환하여 yield
                for article in articles:
                    try:
                        converted_property = self._convert_article_to_db_format(article, cortar_no)
                        
                        if converted_property:
                            yield converted_property
                            page_property_count += 1
                            session.total_properties += 1
                        
                    except Exception as e:
                        print(f"      ⚠️ 매물 변환 실패: {e}")
                        session.error_count += 1
                        continue
                
                print(f"      ✅ 페이지 {page}: {page_property_count}개 변환 완료")
                
                # 다음 페이지로
                page += 1
                consecutive_failures = 0
                
                # API 호출 제한 준수
                time.sleep(random.uniform(0.3, 0.8))
                
            except Exception as e:
                print(f"      ❌ 페이지 {page} 처리 실패: {e}")
                consecutive_failures += 1
                session.error_count += 1
                
                if consecutive_failures < max_failures:
                    print(f"      🔄 {consecutive_failures}/{max_failures} 실패, 재시도...")
                    time.sleep(2)
                else:
                    print(f"      🚫 연속 실패 한계 도달, 수집 중단")
                    break
    
    def _fetch_page_data(self, cortar_no: str, page: int, size: int = 20) -> Optional[Dict]:
        """
        네이버 API에서 페이지 데이터 가져오기
        
        Args:
            cortar_no: 행정구역 코드
            page: 페이지 번호
            size: 페이지 크기
            
        Returns:
            Optional[Dict]: API 응답 데이터
        """
        
        try:
            # 네이버 API 엔드포인트
            url = "https://new.land.naver.com/api/articles/complex/overview/area"
            
            # 요청 매개변수
            params = {
                'cortarNo': cortar_no,
                'page': page,
                'size': size,
                'realEstateType': '',  # 전체
                'tradeType': '',       # 전체
                'tag': ':::::',
                'sortBy': 'date',
                'sortOrder': 'desc'
            }
            
            # 요청 헤더
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Authorization': self.token,
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Host': 'new.land.naver.com',
                'Pragma': 'no-cache',
                'Referer': f'https://new.land.naver.com/complexes?cortarNo={cortar_no}',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # API 호출
            response = requests.get(
                url, 
                params=params, 
                headers=headers, 
                cookies=self.cookies,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ API 오류 (페이지 {page}): {response.status_code}")
                
                # 401 오류인 경우 토큰 갱신 시도
                if response.status_code == 401:
                    print("🔑 토큰 만료, 갱신 시도...")
                    if self._refresh_token():
                        # 토큰 갱신 후 재시도
                        headers['Authorization'] = self.token
                        response = requests.get(url, params=params, headers=headers, cookies=self.cookies, timeout=30)
                        if response.status_code == 200:
                            return response.json()
                
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 네트워크 오류 (페이지 {page}): {e}")
            return None
        except Exception as e:
            print(f"❌ API 호출 오류 (페이지 {page}): {e}")
            return None
    
    def _convert_article_to_db_format(self, article: Dict, cortar_no: str) -> Optional[Dict]:
        """
        네이버 매물 데이터를 DB 형식으로 변환
        
        Args:
            article: 네이버 매물 데이터
            cortar_no: 행정구역 코드
            
        Returns:
            Optional[Dict]: DB 저장용 데이터
        """
        
        try:
            # 주소 정보 변환
            address_info = {}
            if self.address_converter and article.get('realEstateAddress'):
                try:
                    address_info = self.address_converter.convert_address(
                        article['realEstateAddress']
                    )
                except Exception as e:
                    print(f"   ⚠️ 주소 변환 실패: {e}")
            
            # 현재 날짜
            today = date.today()
            now = datetime.now()
            
            # DB 레코드 구성
            property_record = {
                'article_no': str(article.get('articleNo', '')),
                'cortar_no': cortar_no,
                'article_name': article.get('articleName', ''),
                'real_estate_type': article.get('realEstateTypeName', ''),
                'trade_type': article.get('tradeTypeName', ''),
                'price': self._parse_price(article.get('dealOrWarrantPrc', 0)),
                'rent_price': self._parse_price(article.get('rentPrc', 0)),
                'area1': self._parse_area(article.get('area1', 0)),  # 전용면적
                'area2': self._parse_area(article.get('area2', 0)),  # 공급면적
                'floor_info': article.get('floorInfo', ''),
                'direction': article.get('direction', ''),
                'latitude': article.get('lat'),
                'longitude': article.get('lng'),
                'address_road': address_info.get('road_address', article.get('realEstateAddress', '')),
                'address_jibun': address_info.get('jibun_address', ''),
                'address_detail': article.get('buildingName', ''),
                'building_name': address_info.get('building_name', article.get('buildingName', '')),
                'postal_code': address_info.get('postal_code', ''),
                'tag_list': article.get('tagList', []),
                'description': article.get('articleFeatureDesc', ''),
                'details': article,  # 원시 데이터 보존
                'collected_date': today.isoformat(),
                'last_seen_date': today.isoformat(),
                'is_active': True,
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }
            
            return property_record
            
        except Exception as e:
            print(f"❌ 매물 변환 오류: {e}")
            return None
    
    def _parse_price(self, price_value: any) -> int:
        """가격 데이터 파싱"""
        if isinstance(price_value, (int, float)):
            return int(price_value)
        
        if isinstance(price_value, str):
            # 쉼표 제거 후 숫자만 추출
            price_str = ''.join(filter(str.isdigit, price_value))
            try:
                return int(price_str) if price_str else 0
            except:
                return 0
        
        return 0
    
    def _parse_area(self, area_value: any) -> Optional[float]:
        """면적 데이터 파싱"""
        if isinstance(area_value, (int, float)):
            return float(area_value)
        
        if isinstance(area_value, str):
            try:
                # 숫자와 소수점만 추출
                area_str = ''.join(c for c in area_value if c.isdigit() or c == '.')
                return float(area_str) if area_str else None
            except:
                return None
        
        return None
    
    def _ensure_valid_token(self) -> bool:
        """토큰 유효성 확인 및 갱신"""
        
        # 토큰이 있고 만료되지 않았으면 사용
        if self.token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return True
        
        # 토큰 갱신 시도
        return self._refresh_token()
    
    def _refresh_token(self) -> bool:
        """토큰 갱신"""
        
        print("🔑 토큰 갱신 중...")
        
        try:
            from playwright_token_collector import PlaywrightTokenCollector
            
            token_collector = PlaywrightTokenCollector()
            token_data = token_collector.get_token_with_playwright()
            
            if token_data and token_data.get('success'):
                # 토큰 캐시 저장
                self.save_token_cache(token_data, expires_hours=6)
                print("✅ 토큰 갱신 완료")
                return True
            else:
                print("❌ 토큰 갱신 실패")
                return False
                
        except Exception as e:
            print(f"❌ 토큰 갱신 오류: {e}")
            return False
    
    def load_cached_token(self):
        """캐시된 토큰 로드"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 토큰 만료 확인
                expires_at = datetime.fromisoformat(cache_data['expires_at'])
                if datetime.now() < expires_at:
                    self.token = cache_data['token']
                    
                    # 쿠키 처리
                    cookies_data = cache_data.get('cookies', [])
                    if isinstance(cookies_data, list):
                        self.cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
                    else:
                        self.cookies = cookies_data
                    
                    self.token_expires_at = expires_at
                    print(f"✅ 캐시된 토큰 로드 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    return True
                else:
                    print(f"⏰ 캐시된 토큰 만료 (만료시간: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    
            except Exception as e:
                print(f"⚠️ 캐시된 토큰 로드 실패: {e}")
        
        return False
    
    def save_token_cache(self, token_data, expires_hours=6):
        """토큰 캐시 저장"""
        try:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            cache_data = {
                'token': token_data['token'],
                'cookies': token_data.get('cookies', []),
                'cached_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }
            
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.token = cache_data['token']
            
            # 쿠키 설정
            cookies_data = cache_data['cookies']
            if isinstance(cookies_data, list):
                self.cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
            else:
                self.cookies = cookies_data
                
            self.token_expires_at = expires_at
            
            print(f"💾 토큰 캐시 저장 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
            return True
            
        except Exception as e:
            print(f"❌ 토큰 캐시 저장 실패: {e}")
            return False
    
    def _create_error_result(self, session: CollectionSession, error_message: str) -> Dict:
        """에러 결과 생성"""
        session.end_time = datetime.now()
        session.processing_time = (session.end_time - session.start_time).total_seconds()
        
        return {
            'success': False,
            'error': error_message,
            'region_name': session.region_name,
            'cortar_no': session.cortar_no,
            'session_info': {
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'processing_time': session.processing_time,
                'total_pages': session.total_pages,
                'total_properties': session.total_properties,
                'error_count': session.error_count
            }
        }

# 성능 테스트 함수
def test_optimized_direct_collector():
    """최적화된 직접 수집기 테스트"""
    
    print("🧪 최적화된 직접 수집기 테스트")
    print("=" * 50)
    
    try:
        collector = OptimizedDirectCollector(batch_size=25)
        
        # 테스트 지역: 역삼동
        test_cortar_no = "1168010100"
        test_region_name = "역삼동"
        
        # 직접 수집 실행
        result = collector.collect_region_direct(test_cortar_no, test_region_name)
        
        if result['success']:
            print(f"\n✅ 테스트 성공!")
            print(f"   처리 시간: {result['session_info']['processing_time']:.1f}초")
            print(f"   수집 매물: {result['collection_stats']['collected_properties']:,}개")
            print(f"   신규 매물: {result['collection_stats']['new_properties']:,}개")
            print(f"   성능: {result['performance']['records_per_second']:.1f} 레코드/초")
        else:
            print(f"❌ 테스트 실패: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ 테스트 예외: {e}")

if __name__ == "__main__":
    test_optimized_direct_collector()