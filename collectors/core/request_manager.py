import time, random, requests
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

class RequestManager:
    """API 요청 및 재시도/지연 관리"""

    def __init__(self, token_mgr, max_retries=3):
        self.token_mgr = token_mgr
        self.max_retries = max_retries

    def get_random_user_agent(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
        ]
        return random.choice(agents)

    def setup_headers(self):
        return {
            'authorization': f'Bearer {self.token_mgr.token}',
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'application/json',
            'Referer': 'https://new.land.naver.com/',
            'Origin': 'https://new.land.naver.com',
            'Cache-Control': 'no-cache'
        }

    def adaptive_delay(self, base=1.5, jitter=1.5):
        time.sleep(random.uniform(base, base + jitter))

    def parse_url(self, url):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        ms = query.get('ms', [''])[0]
        if ms:
            parts = ms.split(',')
            lat, lon, zoom = float(parts[0]), float(parts[1]), int(parts[2])
        else:
            lat, lon, zoom = 37.5665, 126.9780, 15
        return {
            'lat': lat, 'lon': lon, 'zoom': zoom,
            'article_types': query.get('a', [''])[0],
            'purpose': query.get('e', [''])[0]
        }

    def get_cortar_code(self, lat, lon, zoom):
        url = "https://new.land.naver.com/api/cortars"
        params = {'zoom': zoom, 'centerLat': lat, 'centerLon': lon}
        for attempt in range(self.max_retries):
            try:
                headers = self.setup_headers()
                self.adaptive_delay()
                r = requests.get(url, headers=headers, params=params, cookies=self.token_mgr.cookies, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, dict) and 'cortarNo' in data:
                        return data['cortarNo']
                    if isinstance(data, list) and data:
                        return data[0].get('cortarNo')
                elif r.status_code == 401 and self.token_mgr.get_fresh_token():
                    continue
            except Exception:
                pass
        return None

    def get_article_detail(self, article_no):
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        params = {'complexNo': ''}
        for attempt in range(self.max_retries):
            try:
                headers = self.setup_headers()
                self.adaptive_delay(0.5, 0.5)
                r = requests.get(url, headers=headers, params=params, cookies=self.token_mgr.cookies, timeout=10)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 401 and self.token_mgr.get_fresh_token():
                    continue
            except Exception:
                pass
        return None

    def get_articles_with_details(self, articles, parser, include_details=True, max_workers=5):
        """매물 리스트에서 상세정보 병렬 수집"""
        results = []
        if not include_details:
            return articles
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self.get_article_detail, a['articleNo']): a for a in articles if a.get('articleNo')}
            for future in as_completed(future_map):
                article = future_map[future]
                try:
                    detail = future.result()
                    if detail:
                        parsed_detail = parser.extract_useful_details(detail)
                        if parsed_detail:
                            article['상세정보'] = parsed_detail
                except Exception:
                    pass
                results.append(article)
        return results
