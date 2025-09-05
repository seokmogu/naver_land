#!/usr/bin/env python3
"""
네이버 부동산 수집기 전체 설정 관리
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class Settings:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        load_dotenv()
        
    @property
    def supabase_config(self) -> Dict[str, str]:
        return {
            'url': os.getenv('SUPABASE_URL', 'https://eslhavjipwbyvbbknixv.supabase.co'),
            'key': os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE')
        }
    
    @property
    def kakao_api_key(self) -> Optional[str]:
        return os.getenv('KAKAO_REST_API_KEY')
    
    @property
    def naver_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Referer': 'https://land.naver.com/',
            'Origin': 'https://land.naver.com'
        }
    
    @property
    def collection_settings(self) -> Dict[str, Any]:
        return {
            'request_delay_min': 1.5,    # 1.5초로 단축 (60% 개선)
            'request_delay_max': 3.0,    # 3초로 단축 (70% 개선)
            'max_retries': 3,            # 재시도 늘림 (안정성 확보)
            'timeout': 30,
            'daily_limit': 100000,
            'parallel_workers': 2,       # 병렬 처리용 워커 수 (연결풀 고려하여 축소)
            'adaptive_delay': True,      # 적응형 지연 활성화
            'base_retry_delay': 2.0,     # 429 에러시 기본 대기시간
            'max_retry_delay': 60.0      # 429 에러시 최대 대기시간
        }
    
    @property
    def gangnam_districts(self) -> Dict[str, str]:
        """사용자 제공 강남구 동별 코드"""
        return {
            "역삼동": "1168010100",
            "개포동": "1168010300",
            "청담동": "1168010400",
            "삼성동": "1168010500",
            "대치동": "1168010600",
            "신사동": "1168010700",
            "논현동": "1168010800",
            "압구정동": "1168011000",
            "세곡동": "1168011100",
            "자곡동": "1168011200",
            "율현동": "1168011300",
            "일원동": "1168011400",
            "수서동": "1168011500",
            "도곡동": "1168011800"
        }
    
    @property
    def validation_rules(self) -> Dict[str, Any]:
        """매물 검증 규칙 - 조건에 맞지 않으면 is_active = False"""
        return {
            'deposit_limits': {
                'min': 10_000_000,      # 보증금 1천만원 미만 제외
                'max': 500_000_000      # 보증금 5억 초과 제외
            },
            'monthly_rent_limits': {
                'min': 2_000_000,       # 월세 200만원 미만 제외  
                'max': 50_000_000       # 월세 5천만원 초과 제외
            },
            'elevator_required': True,   # 엘리베이터 0개 또는 null 제외
            'excluded_trade_types': [    # 제외할 거래유형
                'A2',  # 전세
                'A1',  # 매매  
                'B2'   # 단기임대
            ],
            'validation_enabled': True   # 검증 활성화/비활성화 스위치
        }

settings = Settings()