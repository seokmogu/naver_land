import requests
import json
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict

class ClusterBasedCollector:
    """클러스터 API를 활용한 효율적인 네이버 부동산 수집기"""
    
    def __init__(self, token_file="token.txt"):
        self.token_file = token_file
        self.token = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://new.land.naver.com/offices"
        }
        self.cluster_url = "https://new.land.naver.com/api/articles/clusters"
        self.article_url = "https://new.land.naver.com/api/articles"
        self.collected_articles = {}  # 중복 제거용
        self.save_lock = threading.Lock()  # 파일 저장 동기화
        self.batch_size = 100  # 배치 저장 크기
        self.output_file = None
        
    def load_token(self):
        """저장된 토큰 로드"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token = f.read().strip()
                    self.token = token
                    self.headers["authorization"] = f"Bearer {token}"
                    print(f"✓ 토큰 로드 성공")
                    return True
            except Exception as e:
                print(f"✗ 토큰 로드 실패: {e}")
        return False
    
    def get_clusters(self, bounds, zoom=15, real_estate_type="SMS"):
        """특정 영역의 클러스터 정보 조회"""
        params = {
            "z": zoom,
            "lat": (bounds['north'] + bounds['south']) / 2,
            "lon": (bounds['east'] + bounds['west']) / 2,
            "bounds": f"{bounds['west']}:{bounds['south']}:{bounds['east']}:{bounds['north']}",
            "showR0": "true",
            "realEstateType": real_estate_type,
            "tradeType": "",
            "tag": ":::::::::",
            "rentPriceMin": "0",
            "rentPriceMax": "900000000",
            "priceMin": "0", 
            "priceMax": "900000000",
            "areaMin": "0",
            "areaMax": "900000000",
            "includeCortarNo": "false",
            "sameAddressGroup": "false"
        }
        
        try:
            response = requests.get(self.cluster_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            clusters = []
            if 'data' in data and 'ARTICLE' in data['data']:
                for cluster in data['data']['ARTICLE']:
                    clusters.append({
                        'lat': cluster.get('lat'),
                        'lng': cluster.get('lgeo'),  
                        'count': cluster.get('count'),
                        'bounds': cluster.get('bounds'),  # 클러스터 범위
                        'cortarNo': cluster.get('cortarNo')
                    })
            
            return clusters
            
        except Exception as e:
            print(f"클러스터 조회 오류: {e}")
            return []
    
    def get_articles_in_bounds(self, bounds, real_estate_type="SMS", max_pages=10):
        """특정 영역 내 매물 목록 조회"""
        articles = []
        page = 1
        
        while page <= max_pages:
            params = {
                "order": "rank",
                "page": page,
                "realEstateType": real_estate_type,
                "tradeType": "",
                "tag": ":::::::::",
                "rentPriceMin": "0",
                "rentPriceMax": "900000000",
                "priceMin": "0",
                "priceMax": "900000000",
                "areaMin": "0",
                "areaMax": "900000000",
                "bounds": f"{bounds['west']}:{bounds['south']}:{bounds['east']}:{bounds['north']}",
                "showArticle": "false",
                "sameAddressGroup": "false",
                "showR0": "true"
            }
            
            try:
                response = requests.get(self.article_url, params=params, headers=self.headers)
                if response.status_code != 200:
                    break
                    
                data = response.json()
                page_articles = data.get('articleList', [])
                
                if not page_articles:
                    break
                    
                articles.extend(page_articles)
                
                if not data.get('isMoreData', False):
                    break
                    
                page += 1
                time.sleep(0.1)  # API 부하 방지
                
            except Exception as e:
                print(f"  매물 조회 오류 (페이지 {page}): {e}")
                break
        
        return articles
    
    def save_batch(self, articles, is_final=False):
        """배치 단위로 파일 저장"""
        if not articles and not is_final:
            return
            
        with self.save_lock:
            # 파일명 설정 (첫 저장시)
            if not self.output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.output_file = f"cluster_collection_{timestamp}.json"
                
            # 기존 데이터 로드
            existing_data = []
            if os.path.exists(self.output_file):
                try:
                    with open(self.output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # 새 데이터 추가
            if articles:
                existing_data.extend(articles)
                
            # 파일 저장
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
                
            if articles:
                print(f"    💾 {len(articles)}개 저장 (전체: {len(existing_data)}개)")
            
            if is_final:
                print(f"\n📁 최종 저장 완료: {self.output_file}")
                print(f"   총 매물: {len(existing_data)}개")
    
    def collect_cluster_area(self, cluster):
        """단일 클러스터 영역 수집"""
        if cluster['count'] == 0:
            return []
            
        # 클러스터 범위 설정
        if cluster.get('bounds'):
            bounds = cluster['bounds']
        else:
            # 범위가 없으면 중심점 기준으로 작은 영역 설정
            offset = 0.002  # 약 200m
            bounds = {
                'west': cluster['lng'] - offset,
                'east': cluster['lng'] + offset,
                'south': cluster['lat'] - offset,
                'north': cluster['lat'] + offset
            }
        
        print(f"  📍 클러스터 수집: {cluster['count']}개 예상")
        articles = self.get_articles_in_bounds(bounds)
        
        # 중복 제거 및 수집
        new_articles = []
        for article in articles:
            article_id = article.get('articleNo')
            if article_id and article_id not in self.collected_articles:
                self.collected_articles[article_id] = True
                new_articles.append(article)
        
        return new_articles
    
    def collect_by_clusters(self, center_lat, center_lng, radius_km=5, initial_zoom=13):
        """클러스터 기반 전체 수집"""
        print(f"\n🔍 클러스터 기반 수집 시작")
        print(f"   중심: {center_lat}, {center_lng}")
        print(f"   반경: {radius_km}km")
        
        # 영역 계산 (1도 = 약 111km)
        lat_offset = radius_km / 111
        lng_offset = radius_km / (111 * 0.8)  # 위도에 따른 보정
        
        bounds = {
            'north': center_lat + lat_offset,
            'south': center_lat - lat_offset,
            'east': center_lng + lng_offset,
            'west': center_lng - lng_offset
        }
        
        # 1단계: 클러스터 탐색
        print(f"\n1️⃣ 클러스터 탐색 (줌 레벨 {initial_zoom})")
        clusters = self.get_clusters(bounds, zoom=initial_zoom)
        print(f"   발견된 클러스터: {len(clusters)}개")
        
        if not clusters:
            print("   클러스터가 없습니다. 줌 레벨을 조정해보세요.")
            return
        
        # 클러스터 통계
        total_expected = sum(c['count'] for c in clusters)
        print(f"   예상 매물 수: {total_expected}개")
        
        # 2단계: 병렬 수집
        print(f"\n2️⃣ 매물 수집 시작 (병렬 처리)")
        batch_articles = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_cluster = {
                executor.submit(self.collect_cluster_area, cluster): cluster 
                for cluster in clusters
            }
            
            completed = 0
            for future in as_completed(future_to_cluster):
                completed += 1
                try:
                    new_articles = future.result()
                    if new_articles:
                        batch_articles.extend(new_articles)
                        
                        # 배치 저장
                        if len(batch_articles) >= self.batch_size:
                            self.save_batch(batch_articles)
                            batch_articles = []
                            
                    print(f"   진행: {completed}/{len(clusters)} 클러스터")
                    
                except Exception as e:
                    print(f"   클러스터 수집 오류: {e}")
        
        # 남은 데이터 저장
        if batch_articles:
            self.save_batch(batch_articles)
            
        # 최종 저장
        self.save_batch([], is_final=True)
        
        print(f"\n✅ 수집 완료!")
        print(f"   수집된 매물: {len(self.collected_articles)}개")
        print(f"   중복 제거: {total_expected - len(self.collected_articles)}개")
    
    def collect_by_grid(self, bounds, grid_size=0.005):
        """격자 분할 방식 수집"""
        print(f"\n🔲 격자 분할 수집 시작")
        print(f"   격자 크기: {grid_size} (약 {grid_size * 111:.1f}km)")
        
        lat_steps = int((bounds['north'] - bounds['south']) / grid_size)
        lng_steps = int((bounds['east'] - bounds['west']) / grid_size)
        total_grids = lat_steps * lng_steps
        
        print(f"   격자 수: {lat_steps} x {lng_steps} = {total_grids}개")
        
        batch_articles = []
        grid_count = 0
        
        for lat_idx in range(lat_steps):
            for lng_idx in range(lng_steps):
                grid_count += 1
                
                # 격자 영역 계산
                grid_bounds = {
                    'south': bounds['south'] + lat_idx * grid_size,
                    'north': bounds['south'] + (lat_idx + 1) * grid_size,
                    'west': bounds['west'] + lng_idx * grid_size,
                    'east': bounds['west'] + (lng_idx + 1) * grid_size
                }
                
                print(f"\n격자 {grid_count}/{total_grids} 수집 중...")
                articles = self.get_articles_in_bounds(grid_bounds, max_pages=5)
                
                # 중복 제거 및 수집
                new_articles = []
                for article in articles:
                    article_id = article.get('articleNo')
                    if article_id and article_id not in self.collected_articles:
                        self.collected_articles[article_id] = True
                        new_articles.append(article)
                        batch_articles.append(article)
                
                print(f"  +{len(new_articles)}개 (전체: {len(self.collected_articles)}개)")
                
                # 배치 저장
                if len(batch_articles) >= self.batch_size:
                    self.save_batch(batch_articles)
                    batch_articles = []
                    
                time.sleep(0.2)  # API 부하 방지
        
        # 남은 데이터 저장
        if batch_articles:
            self.save_batch(batch_articles)
            
        # 최종 저장
        self.save_batch([], is_final=True)
        
        print(f"\n✅ 격자 수집 완료!")
        print(f"   수집된 매물: {len(self.collected_articles)}개")


def main():
    print("🏢 클러스터 기반 네이버 부동산 수집기")
    print("=" * 50)
    
    collector = ClusterBasedCollector()
    
    # 토큰 로드
    if not collector.load_token():
        print("❌ 토큰을 찾을 수 없습니다. 먼저 토큰을 생성해주세요.")
        return
    
    print("\n수집 방식을 선택하세요:")
    print("1. 클러스터 기반 수집 (추천)")
    print("2. 격자 분할 수집")
    print("3. 특정 지역 집중 수집")
    
    choice = input("\n선택 (1-3): ").strip()
    
    if choice == "1":
        # 클러스터 기반 수집 - 강남역 중심 예시
        print("\n중심 좌표를 입력하세요 (기본: 강남역)")
        lat = input("위도 (기본: 37.498): ").strip() or "37.498"
        lng = input("경도 (기본: 127.028): ").strip() or "127.028"
        radius = input("반경(km, 기본: 3): ").strip() or "3"
        
        collector.collect_by_clusters(
            float(lat), float(lng), 
            radius_km=float(radius),
            initial_zoom=14
        )
        
    elif choice == "2":
        # 격자 분할 수집 - 강남구 전체
        bounds = {
            'north': 37.5326,
            'south': 37.4715,
            'east': 127.0796,
            'west': 127.0164
        }
        collector.collect_by_grid(bounds, grid_size=0.005)
        
    elif choice == "3":
        # 특정 지역 집중
        print("\n영역 좌표를 입력하세요:")
        north = float(input("북쪽 위도: "))
        south = float(input("남쪽 위도: "))
        east = float(input("동쪽 경도: "))
        west = float(input("서쪽 경도: "))
        
        bounds = {'north': north, 'south': south, 'east': east, 'west': west}
        articles = collector.get_articles_in_bounds(bounds, max_pages=50)
        
        # 저장
        collector.collected_articles = {a['articleNo']: True for a in articles}
        collector.save_batch(articles, is_final=True)
        
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    main()