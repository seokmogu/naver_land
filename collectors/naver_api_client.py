#!/usr/bin/env python3
"""
네이버 부동산 API 클라이언트
"""

import requests
import random
import time
from typing import Dict, Optional
from config.settings import settings
from collectors.token_collector import NaverTokenCollector

class NaverAPIClient:
    def __init__(self):
        self.session = requests.Session()
        self.token_collector = NaverTokenCollector()
        self.request_count = 0
        self.rate_limit_backoff = settings.collection_settings['base_retry_delay']
        self.consecutive_429_errors = 0
        
    def _get_random_delay(self) -> float:
        return random.uniform(
            settings.collection_settings['request_delay_min'],
            settings.collection_settings['request_delay_max']
        )
    
    def _make_request(self, url: str, params: Dict = None, retries: int = None) -> Optional[Dict]:
        if retries is None:
            retries = settings.collection_settings['max_retries']
            
        for attempt in range(retries):
            try:
                time.sleep(self._get_random_delay())
                
                # 토큰이 포함된 헤더 사용
                headers = self.token_collector.get_headers_with_token()
                cookies = self.token_collector.cookies
                
                response = self.session.get(
                    url, 
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=settings.collection_settings['timeout']
                )
                
                self.request_count += 1
                
                if response.status_code == 200:
                    # 성공시 429 에러 카운터 초기화
                    self.consecutive_429_errors = 0
                    self.rate_limit_backoff = settings.collection_settings['base_retry_delay']
                    return response.json()
                elif response.status_code == 429:
                    # 적응형 지연 적용
                    self.consecutive_429_errors += 1
                    adaptive_delay = min(
                        self.rate_limit_backoff * (2 ** (self.consecutive_429_errors - 1)),
                        settings.collection_settings['max_retry_delay']
                    )
                    print(f"⚠️ Rate limit hit ({self.consecutive_429_errors}회), {adaptive_delay:.1f}초 대기...")
                    time.sleep(adaptive_delay)
                    continue
                elif response.status_code == 401 or response.status_code == 403:
                    print(f"🔑 토큰 만료 또는 인증 실패, 새 토큰 수집 중...")
                    # 새 토큰 수집 시도
                    new_token = self.token_collector.collect_token_from_page()
                    if new_token:
                        print("✅ 새 토큰 수집 성공, 재시도 중...")
                        continue
                    else:
                        print("❌ 새 토큰 수집 실패")
                        break
                else:
                    print(f"❌ HTTP {response.status_code}: {url}")
                    print(f"   응답: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Request failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    
        return None
    
    def get_article_detail(self, article_no: str) -> Optional[Dict]:
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        return self._make_request(url)
    
    def get_area_articles(self, cortar_no: str, page: int = 1) -> Optional[Dict]:
        """
        지역별 사무실 매물 목록 조회 - 사무실만 (상가 제외)
        네이버 랜드 웹사이트의 실제 네트워크 요청 분석을 통해 올바른 파라미터 적용
        """
        url = "https://new.land.naver.com/api/articles"
        
        params = {
            # 필수 파라미터
            'cortarNo': cortar_no,
            'page': page,
            'order': 'rank',
            'realEstateType': 'SMS',    # 사무실 필터 (핵심 파라미터)
            'priceType': 'RETAIL',      # 가격 타입 (필수)
            'tradeType': '',            # 거래유형 전체 (빈값)
            
            # 가격/면적 필터
            'rentPriceMin': 0,
            'rentPriceMax': 900000000,
            'priceMin': 0,
            'priceMax': 900000000,
            'areaMin': 0,
            'areaMax': 900000000,
            
            # 추가 필터 (빈값이지만 API에서 요구)
            'tag': '::::::::',           # 빈 태그들
            'oldBuildYears': '',         # 건축년도
            'recentlyBuildYears': '',    # 최근건축년도
            'minHouseHoldCount': '',     # 최소세대수
            'maxHouseHoldCount': '',     # 최대세대수
            'showArticle': False,        # 매물 표시 여부
            'sameAddressGroup': False,   # 동일주소 그룹핑
            'minMaintenanceCost': '',    # 최소관리비
            'maxMaintenanceCost': '',    # 최대관리비
            'directions': '',            # 방향
            'articleState': ''           # 매물상태
        }
            
        return self._make_request(url, params)
    
    def get_request_stats(self) -> Dict[str, int]:
        return {
            'total_requests': self.request_count,
            'remaining_daily_limit': settings.collection_settings['daily_limit'] - self.request_count
        }