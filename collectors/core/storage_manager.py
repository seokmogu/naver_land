import os, json
from datetime import datetime

class StorageManager:
    """수집 데이터 저장 (JSON/DB)"""

    def __init__(self, results_dir=None):
        self.results_dir = results_dir or os.path.join(os.path.dirname(__file__), '..', 'results')
        os.makedirs(self.results_dir, exist_ok=True)

    def save_json(self, cortar_no, dong_name, articles, mode="optimized"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_{mode}_{dong_name}_{cortar_no}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "수집정보": {
                    "수집시간": timestamp,
                    "지역코드": cortar_no,
                    "동이름": dong_name,
                    "수집방식": f"{mode}_캐시토큰",
                    "버전": "v2.0_refactored"
                },
                "매물목록": articles
            }, f, ensure_ascii=False, indent=2)

        return filepath

    def save_to_db(self, cortar_no, filepath):
        try:
            from collectors.json_to_db_converter import convert_json_to_properties
            from collectors.supabase_client import SupabaseHelper
            helper = SupabaseHelper()
            db_properties = convert_json_to_properties(filepath, cortar_no)
            if db_properties:
                save_stats = helper.save_converted_properties(db_properties, cortar_no)
                from datetime import date
                helper.save_daily_stats(date.today(), cortar_no, db_properties, save_stats)
                return save_stats
        except Exception as e:
            return {"error": str(e)}
        return None
