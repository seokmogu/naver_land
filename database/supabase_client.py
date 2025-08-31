#!/usr/bin/env python3
"""
Supabase 클라이언트 관리
"""

from supabase import create_client
from config.settings import settings
import time

class SupabaseClient:
    def __init__(self):
        self.client = create_client(
            settings.supabase_config['url'],
            settings.supabase_config['key']
        )
        self.connection_verified = False
        self._connection_pool_retry = 0
        self._max_pool_retries = 3
    
    def verify_connection(self) -> bool:
        try:
            result = self.client.table('naver_properties').select('id').limit(1).execute()
            self.connection_verified = True
            return True
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            self.connection_verified = False
            return False
    
    def get_client(self):
        if not self.connection_verified:
            self.verify_connection()
        return self.client
    
    def get_client_with_retry(self):
        """연결 풀 에러 시 재시도 로직이 포함된 클라이언트 반환"""
        for attempt in range(self._max_pool_retries):
            try:
                if not self.connection_verified:
                    self.verify_connection()
                return self.client
            except Exception as e:
                if "Resource temporarily unavailable" in str(e) or "Errno 35" in str(e):
                    wait_time = (attempt + 1) * 2  # 2, 4, 6초 대기
                    print(f"⚠️ 연결풀 포화, {wait_time}초 대기 후 재시도 ({attempt + 1}/{self._max_pool_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
        # 모든 재시도 실패시 원래 클라이언트 반환
        return self.client

supabase_client = SupabaseClient()