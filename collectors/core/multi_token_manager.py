import os, json, random
from datetime import datetime, timedelta

class MultiTokenManager:
    """멀티 토큰 풀 관리"""

    def __init__(self, token_dir=None):
        self.token_dir = token_dir or os.path.join(os.path.dirname(__file__), "..", "tokens")
        os.makedirs(self.token_dir, exist_ok=True)
        self.tokens = []
        self.load_all_tokens()

    def load_all_tokens(self):
        self.tokens = []
        for fname in os.listdir(self.token_dir):
            if fname.endswith(".json"):
                path = os.path.join(self.token_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    expires_at = datetime.fromisoformat(data["expires_at"])
                    if datetime.now() < expires_at:
                        self.tokens.append({
                            "token": data["token"],
                            "cookies": {c["name"]: c["value"] for c in data.get("cookies", [])},
                            "expires_at": expires_at,
                            "path": path
                        })
                except Exception:
                    continue

    def get_random_token(self):
        if not self.tokens:
            return None
        return random.choice(self.tokens)

    def save_token(self, token_data, filename=None, expires_hours=6):
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        cache_data = {
            "token": token_data["token"],
            "cookies": token_data.get("cookies", []),
            "cached_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat()
        }
        filename = filename or f"token_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.token_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        self.load_all_tokens()
        return path

    def ensure_valid_token(self):
        self.load_all_tokens()
        valid_tokens = [t for t in self.tokens if t["expires_at"] > datetime.now()]
        return bool(valid_tokens)
