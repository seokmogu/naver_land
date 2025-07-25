import requests
import json
import time
from datetime import datetime
import pandas as pd
import math
from concurrent.futures import ThreadPoolExecutor, as_completed


class ComprehensiveNaverLandCollector:
    """클러스터 기반 전체 지역 매물 수집기"""
    
    def __init__(self, token_file="token.txt"):
        self.load_token(token_file)
        self.base_cluster_url = "https://new.land.naver.com/api/articles/clusters"
        self.base_article_url = "https://new.land.naver.com/api/articles"
        self.headers = {
            "authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://new.land.naver.com/offices"
        }
        self.collected_articles = {}
        self.cluster_cache = {}
        
    def load_token(self, token_file):
        """토큰 로드"""
        try:
            with open(token_file, 'r') as f:
                self.token = f.read().strip()
            print(f"✓ 토큰 로드 성공")
        except:
            print("✗ 토큰 파일을 찾을 수 없습니다.")
            raise
            
    def get_bounds_from_center(self, lat, lng, zoom):
        """중심 좌표와 줌 레벨로부터 경계 계산"""
        zoom_to_meters = {
            10: 20000, 11: 10000, 12: 5000, 13: 2500, 14: 1250,
            15: 625, 16: 312, 17: 156, 18: 78, 19: 39
        }
        
        meters = zoom_to_meters.get(zoom, 1000)
        lat_diff = meters / 111000
        lng_diff = meters / (111000 * math.cos(math.radians(lat)))
        
        return {
            'leftLon': lng - lng_diff,
            'rightLon': lng + lng_diff,
            'topLat': lat + lat_diff,
            'bottomLat': lat - lat_diff
        }
        
    def get_clusters(self, bounds, zoom=15, real_estate_type="SMS"):
        """특정 범위의 클러스터 조회"""
        params = {
            "zoom": zoom,
            "priceMin": "0",
            "priceMax": "900000000",
            "rentPriceMin": "0",
            "rentPriceMax": "900000000",
            "areaMin": "0",
            "areaMax": "900000000",
            "realEstateType": real_estate_type,
            "tradeType": "",
            "bottomLat": bounds['bottomLat'],
            "leftLon": bounds['leftLon'],
            "topLat": bounds['topLat'],
            "rightLon": bounds['rightLon']
        }
        
        try:
            response = requests.get(self.base_cluster_url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"클러스터 조회 오류: {e}")
            return []
            
    def subdivide_bounds(self, bounds, grid_size=2):
        """영역을 더 작은 격자로 분할"""
        lat_step = (bounds['topLat'] - bounds['bottomLat']) / grid_size
        lng_step = (bounds['rightLon'] - bounds['leftLon']) / grid_size
        
        sub_bounds = []
        for i in range(grid_size):
            for j in range(grid_size):
                sub_bound = {
                    'bottomLat': bounds['bottomLat'] + i * lat_step,
                    'topLat': bounds['bottomLat'] + (i + 1) * lat_step,
                    'leftLon': bounds['leftLon'] + j * lng_step,
                    'rightLon': bounds['leftLon'] + (j + 1) * lng_step
                }
                sub_bounds.append(sub_bound)
        return sub_bounds
        
    def get_articles_from_cortar(self, cortar_no, max_pages=100):
        """법정동 코드로 매물 전체 수집"""
        print(f"\n법정동 {cortar_no} 수집 중...")
        
        params = {
            "cortarNo": cortar_no,
            "order": "rank",
            "realEstateType": "SMS",
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
        
        while page <= max_pages:
            params['page'] = str(page)
            
            try:
                response = requests.get(self.base_article_url, params=params, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                page_articles = data.get('articleList', [])
                
                if not page_articles:
                    break
                    
                articles.extend(page_articles)
                print(f"  페이지 {page}: {len(page_articles)}개 (누적: {len(articles)}개)")
                
                if not data.get('isMoreData', False):
                    break
                    
                page += 1
                time.sleep(0.3)  # API 부하 방지
                
            except Exception as e:
                print(f"  페이지 {page} 오류: {e}")
                break
                
        return articles
        
    def collect_comprehensive_data(self, center_lat, center_lng, zoom=14, grid_size=4):
        """종합적인 데이터 수집"""
        print(f"=== 종합 데이터 수집 시작 ===")
        print(f"중심 좌표: ({center_lat}, {center_lng}), 줌: {zoom}")
        
        # 1. 초기 범위 설정
        main_bounds = self.get_bounds_from_center(center_lat, center_lng, zoom)
        print(f"수집 범위: ({main_bounds['bottomLat']:.6f}, {main_bounds['leftLon']:.6f}) ~ ({main_bounds['topLat']:.6f}, {main_bounds['rightLon']:.6f})")
        
        # 2. 범위를 격자로 분할
        sub_bounds_list = self.subdivide_bounds(main_bounds, grid_size)
        print(f"격자 분할: {len(sub_bounds_list)}개 영역")
        
        all_clusters = []
        cluster_count = 0
        
        # 3. 각 격자별로 클러스터 수집
        print(f"\n격자별 클러스터 수집:")
        for i, bounds in enumerate(sub_bounds_list):
            print(f"  격자 {i+1}/{len(sub_bounds_list)} 처리 중...", end='')
            
            clusters = self.get_clusters(bounds, zoom + 1)  # 더 상세한 줌 레벨
            cluster_count += len(clusters)
            all_clusters.extend(clusters)
            
            total_articles = sum(c.get('count', 0) for c in clusters)
            print(f" {len(clusters)}개 클러스터, {total_articles}개 매물")
            
            time.sleep(0.2)
            
        print(f"\n총 클러스터: {cluster_count}개")
        print(f"예상 매물 수: {sum(c.get('count', 0) for c in all_clusters)}개")
        
        # 4. 클러스터 데이터 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_file = f"clusters_{timestamp}.json"
        with open(cluster_file, 'w', encoding='utf-8') as f:
            json.dump(all_clusters, f, ensure_ascii=False, indent=2)
        print(f"클러스터 데이터 저장: {cluster_file}")
        
        return all_clusters
        
    def extract_cortar_codes(self, clusters):
        """클러스터에서 법정동 코드 추출"""
        cortar_codes = set()
        
        for cluster in clusters:
            # 클러스터에서 법정동 코드 찾기 (있는 경우)
            if 'cortarNo' in cluster:
                cortar_codes.add(cluster['cortarNo'])
                
        # 역삼동 관련 주요 법정동 코드들 (예시)
        default_cortars = [
            "1168010100",  # 역삼동
            "1168010200",  # 강남구 다른 지역
            "1168010300", 
            "1168010400",
            "1168010500"
        ]
        
        cortar_codes.update(default_cortars)
        return list(cortar_codes)
        
    def collect_by_cortar_codes(self, cortar_codes):
        """법정동 코드별 전체 매물 수집"""
        print(f"\n=== 법정동별 전체 매물 수집 ===")
        
        all_articles = []
        
        for cortar in cortar_codes:
            articles = self.get_articles_from_cortar(cortar)
            
            # 중복 제거
            for article in articles:
                article_id = article.get('articleNo')
                if article_id and article_id not in self.collected_articles:
                    self.collected_articles[article_id] = article
                    
            all_articles.extend(articles)
            print(f"  {cortar}: {len(articles)}개 수집 (전체: {len(self.collected_articles)}개)")
            
        return list(self.collected_articles.values())
        
    def save_comprehensive_results(self, articles, prefix="comprehensive"):
        """종합 결과 저장"""
        if not articles:
            print("저장할 데이터가 없습니다.")
            return
            
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
                '중개사': article.get('realtorName'),
                '법정동코드': article.get('cortarNo', '')
            })
            
        df = pd.DataFrame(flat_data)
        csv_file = f"{prefix}_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n=== 최종 저장 완료 ===")
        print(f"JSON: {json_file}")
        print(f"CSV: {csv_file}")
        print(f"총 매물 수: {len(articles)}개")
        
        # 통계 정보
        df_stats = df.groupby('거래타입').size()
        print(f"\n거래타입별 매물 수:")
        for trade_type, count in df_stats.items():
            print(f"  {trade_type}: {count}개")
            
        return json_file, csv_file


def main():
    print("=== 네이버 부동산 종합 수집기 ===")
    print("클러스터 분석을 통한 전체 지역 매물 수집\n")
    
    collector = ComprehensiveNaverLandCollector()
    
    # 역삼동 중심 좌표
    center_lat, center_lng = 37.4990461, 127.0309029
    
    try:
        # 1. 클러스터 기반 영역 분석
        clusters = collector.collect_comprehensive_data(
            center_lat, center_lng, zoom=14, grid_size=3
        )
        
        # 2. 법정동 코드 추출
        cortar_codes = collector.extract_cortar_codes(clusters)
        print(f"\n추출된 법정동 코드: {cortar_codes}")
        
        # 3. 법정동별 전체 매물 수집
        all_articles = collector.collect_by_cortar_codes(cortar_codes)
        
        # 4. 결과 저장
        collector.save_comprehensive_results(all_articles)
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()