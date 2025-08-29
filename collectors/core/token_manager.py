import os, json
from datetime import datetime, timedelta

class TokenManager:
    """토큰 캐싱 및 갱신 관리"""

    def __init__(self, token_file=None):
        self.token_file = token_file or os.path.join(os.path.dirname(__file__), '..', 'cached_token.json')
        self.token = None
        self.cookies = {}
        self.token_expires_at = None
        self.load_cached_token()

    def load_cached_token(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                expires_at = datetime.fromisoformat(cache_data['expires_at'])
                if datetime.now() < expires_at:
                    self.token = cache_data['token']
                    cookies_list = cache_data.get('cookies', [])
                    self.cookies = {c['name']: c['value'] for c in cookies_list} if isinstance(cookies_list, list) else cookies_list
                    self.token_expires_at = expires_at
                    return True
            except Exception:
                pass
        return False

    def save_token_cache(self, token_data, expires_hours=6):
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
            self.cookies = {c['name']: c['value'] for c in cache_data['cookies']}
            self.token_expires_at = expires_at
            return True
        except Exception:
            return False

    def get_fresh_token(self):
        try:
            from collectors.playwright_token_collector import PlaywrightTokenCollector
            token_collector = PlaywrightTokenCollector()
            token_data = token_collector.get_token_with_playwright()
            if token_data:
                return self.save_token_cache(token_data, expires_hours=6)
        except Exception:
            return False
        return False

    def ensure_valid_token(self):
        if not self.token or (self.token_expires_at and datetime.now() > self.token_expires_at - timedelta(minutes=30)):
            return self.get_fresh_token()
        return True
