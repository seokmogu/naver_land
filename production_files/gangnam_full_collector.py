import requests
import json
import time
import os
from datetime import datetime, timedelta
import pandas as pd
import base64


class GangnamFullCollector:
    """강남구 전체 매물 수집기"""
    
    def __init__(self, token_file="token.txt"):
        self.token_file = token_file
        self.token = None
        self.token_expiry = None
        self.base_url = "https://new.land.naver.com/api/articles"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://new.land.naver.com/offices"
        }
        self.collected_articles = {}  # 중복 제거용
        
    def load_token(self):
        """저장된 토큰 로드"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token = f.read().strip()
                    
                if self.is_token_valid(token):
                    self.token = token
                    print(f"✓ 저장된 토큰 로드 성공 (만료: {self.token_expiry})")
                    return True
                else:
                    print("✗ 저장된 토큰이 만료됨")
            except:
                pass
                
        return False
    
    def is_token_valid(self, token):
        """토큰 유효성 확인"""
        if not token:
            return False
            
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False
                
            payload_part = parts[1]
            missing_padding = len(payload_part) % 4
            if missing_padding:
                payload_part += '=' * (4 - missing_padding)
                
            payload = json.loads(base64.urlsafe_b64decode(payload_part))
            exp_time = datetime.fromtimestamp(payload.get('exp', 0))
            current_time = datetime.now()
            
            if exp_time > current_time + timedelta(minutes=5):
                self.token_expiry = exp_time
                return True
                
        except:
            pass
            
        return False
    
    def get_gangnam_cortar_codes(self):
        """강남구 전체 법정동 코드"""
        return [
            ("1168010100", "역삼1동"),
            ("1168010200", "역삼2동"),  
            ("1168010300", "도곡1동"),
            ("1168010400", "도곡2동"),
            ("1168010500", "개포1동"),
            ("1168010600", "개포2동"),
            ("1168010700", "개포4동"),
            ("1168010800", "세곡동"),
            ("1168010900", "일원본동"),
            ("1168011000", "일원1동"),
            ("1168011100", "일원2동"),
            ("1168011200", "수서동"),
            ("1168011300", "논현1동"),
            ("1168011400", "논현2동"),
            ("1168011500", "압구정동"),
            ("1168011600", "신사동"),
            ("1168011700", "청담동"),
            ("1168011800", "삼성1동"),
            ("1168011900", "삼성2동"),
            ("1168012000", "대치1동"),
            ("1168012100", "대치2동"),
            ("1168012200", "대치4동"),
        ]
    
    def collect_cortar_data(self, cortar_no, dong_name, max_pages=100):
        """특정 법정동의 모든 매물 수집"""
        print(f"\n📍 {dong_name} ({cortar_no}) 수집 중...")
        
        if not self.token:
            print("  토큰이 없습니다.")
            return []
            
        self.headers["authorization"] = f"Bearer {self.token}"
        
        base_params = {
            "cortarNo": cortar_no,
            "order": "rank",
            "realEstateType": "SMS",  # 사무실
            "tradeType": "",
            "tag": "::::::::",
            "rentPriceMin": "0",
            "rentPriceMax": "900000000",
            "priceMin": "0",
            "priceMax": "900000000",
            "areaMin": "0",
            "areaMax": "900000000",
            "showArticle": "false",
            "sameAddressGroup": "false",
            "priceType": "RETAIL",
            "articleState": ""
        }
        
        articles = []
        page = 1
        consecutive_empty = 0
        
        while page <= max_pages and consecutive_empty < 3:
            base_params['page'] = str(page)
            
            try:
                response = requests.get(self.base_url, params=base_params, headers=self.headers)
                
                if response.status_code == 401:
                    print(f"  토큰 만료됨 (페이지 {page})")
                    break
                elif response.status_code != 200:
                    print(f"  HTTP {response.status_code} 오류 (페이지 {page})")
                    consecutive_empty += 1
                    page += 1
                    continue
                    
                data = response.json()
                page_articles = data.get('articleList', [])
                
                if not page_articles:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0
                    articles.extend(page_articles)
                    
                    # 10페이지마다 진행상황 출력
                    if page % 10 == 0 or page <= 5:
                        print(f"    페이지 {page}: {len(page_articles)}개 (누적: {len(articles)}개)")
                
                if not data.get('isMoreData', False) and not page_articles:
                    break
                    
                page += 1
                time.sleep(0.1)  # API 부하 방지
                
            except Exception as e:
                print(f"    페이지 {page} 오류: {e}")
                consecutive_empty += 1
                page += 1
                continue
                
        print(f"  ✓ {dong_name}: {len(articles)}개 매물 수집 완료")
        return articles
    
    def collect_gangnam_full(self):
        """강남구 전체 매물 수집"""
        print("=== 강남구 전체 매물 수집 시작 ===\n")
        
        # 토큰 확인
        if not self.load_token():
            print("유효한 토큰이 없습니다. 먼저 토큰을 획득해주세요.")
            return []
        
        # 강남구 법정동 목록
        cortar_list = self.get_gangnam_cortar_codes()
        print(f"수집 대상: {len(cortar_list)}개 법정동")
        
        start_time = time.time()
        total_collected = 0
        
        # 각 법정동별로 수집
        for i, (cortar_no, dong_name) in enumerate(cortar_list, 1):
            print(f"\n[{i}/{len(cortar_list)}] {dong_name} 처리 중...")
            
            # 해당 동의 모든 매물 수집
            articles = self.collect_cortar_data(cortar_no, dong_name, max_pages=200)
            
            # 중복 제거하며 통합
            new_count = 0
            for article in articles:
                article_id = article.get('articleNo')
                if article_id and article_id not in self.collected_articles:
                    self.collected_articles[article_id] = article
                    new_count += 1
                    
            total_collected = len(self.collected_articles)
            print(f"  📊 {dong_name}: +{new_count}개 신규 (전체: {total_collected}개)")
            
            # 5개동마다 중간 저장
            if i % 5 == 0:
                self.save_intermediate_results(i)
                
        elapsed = time.time() - start_time
        print(f"\n🎉 강남구 전체 수집 완료!")
        print(f"   총 매물: {total_collected}개")
        print(f"   소요시간: {elapsed/60:.1f}분")
        
        return list(self.collected_articles.values())
    
    def save_intermediate_results(self, dong_count):
        """중간 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"gangnam_temp_{dong_count}dong_{timestamp}.json"
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.collected_articles.values()), f, ensure_ascii=False, indent=2)
        
        print(f"    💾 중간저장: {temp_file} ({len(self.collected_articles)}개)")
    
    def save_final_results(self, articles, prefix="gangnam_full"):
        """최종 결과 저장"""
        if not articles:
            print("저장할 데이터가 없습니다.")
            return None, None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"{prefix}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
            
        # CSV 저장
        flat_data = []
        for article in articles:
            flat_data.append({
                '매물번호': article.get('articleNo'),
                '매물명': article.get('articleName'),
                '매물타입': article.get('realEstateTypeName'),
                '거래타입': article.get('tradeTypeName'),
                '보증금/매매가': article.get('dealOrWarrantPrc'),
                '월세': article.get('rentPrc'),
                '전용면적': article.get('area1'),
                '공급면적': article.get('area2'),
                '층': article.get('floorInfo'),
                '방향': article.get('direction'),
                '건물명': article.get('buildingName'),
                '주소': article.get('roadAddress', article.get('address')),
                '설명': article.get('articleFeatureDesc'),
                '태그': ', '.join(article.get('tagList', [])),
                '등록일': article.get('articleConfirmYmd'),
                '위도': article.get('latitude'),
                '경도': article.get('longitude'),
                '중개사': article.get('realtorName')
            })
            
        df = pd.DataFrame(flat_data)
        csv_file = f"{prefix}_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n📁 최종 저장 완료:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")
        print(f"   총 매물: {len(articles)}개")
        
        # 통계 정보
        print(f"\n📊 수집 통계:")
        trade_stats = df['거래타입'].value_counts()
        for trade_type, count in trade_stats.items():
            print(f"   {trade_type}: {count}개 ({count/len(df)*100:.1f}%)")
            
        # 지역별 분포 (주소 기준)
        if not df['주소'].isna().all():
            df['지역'] = df['주소'].str.split().str[:3].str.join(' ')
            area_stats = df['지역'].value_counts().head(10)
            print(f"\n📍 지역별 분포 TOP 10:")
            for area, count in area_stats.items():
                if area and area != 'nan':
                    print(f"   {area}: {count}개")
        
        return json_file, csv_file


def main():
    print("🏢 강남구 전체 사무실 매물 수집기")
    print("=" * 50)
    
    collector = GangnamFullCollector()
    
    try:
        # 강남구 전체 수집 실행
        all_articles = collector.collect_gangnam_full()
        
        # 최종 결과 저장
        if all_articles:
            collector.save_final_results(all_articles)
        else:
            print("수집된 데이터가 없습니다.")
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 사용자에 의해 중단됨")
        # 부분 결과라도 저장
        if collector.collected_articles:
            collector.save_final_results(list(collector.collected_articles.values()), "gangnam_partial")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        # 부분 결과라도 저장
        if collector.collected_articles:
            collector.save_final_results(list(collector.collected_articles.values()), "gangnam_error")


if __name__ == "__main__":
    main()