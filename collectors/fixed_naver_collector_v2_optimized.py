#!/usr/bin/env python3
"""
토큰 캐싱 네이버 부동산 수집기
Playwright 사용을 최소화하여 토큰만 캐싱하고 재사용
"""

import requests
import json
import time
import os
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from kakao_address_converter import KakaoAddressConverter

class CachedTokenCollector:
    def __init__(self, use_address_converter=True):
        """토큰 캐싱 수집기 초기화"""
        self.token_file = os.path.join(os.path.dirname(__file__), 'cached_token.json')
        self.token = None
        self.cookies = {}
        self.token_expires_at = None
        
        # 캐시된 토큰 로드 시도
        self.load_cached_token()
        
        # 주소 변환기 초기화
        self.address_converter = None
        if use_address_converter:
            try:
                self.address_converter = KakaoAddressConverter()
                print("🗺️ 카카오 주소 변환기 활성화")
            except ValueError as e:
                print(f"⚠️ 주소 변환기 비활성화: {e}")
                self.address_converter = None
    
    def load_cached_token(self):
        """캐시된 토큰 로드"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 토큰 만료 확인
                expires_at = datetime.fromisoformat(cache_data['expires_at'])
                if datetime.now() < expires_at:
                    self.token = cache_data['token']
                    # 쿠키 리스트를 딕셔너리로 변환
                    cookies_list = cache_data.get('cookies', [])
                    if isinstance(cookies_list, list):
                        self.cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
                    else:
                        self.cookies = cookies_list
                    self.token_expires_at = expires_at
                    print(f"✅ 캐시된 토큰 로드 성공 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    return True
                else:
                    print(f"⏰ 캐시된 토큰 만료됨 (만료시간: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    
            except Exception as e:
                print(f"⚠️ 캐시된 토큰 로드 실패: {e}")
        
        print("🔄 새로운 토큰 수집 필요")
        return False
    
    def save_token_cache(self, token_data, expires_hours=6):
        """토큰 캐시 저장"""
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
            self.cookies = {cookie['name']: cookie['value'] for cookie in cache_data['cookies']}
            self.token_expires_at = expires_at
            
            print(f"💾 토큰 캐시 저장 완료 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
            return True
            
        except Exception as e:
            print(f"❌ 토큰 캐시 저장 실패: {e}")
            return False
    
    def get_fresh_token(self):
        """새로운 토큰 수집 (Playwright 사용)"""
        print("🎭 Playwright로 새로운 토큰 수집 중...")
        
        try:
            from playwright_token_collector import PlaywrightTokenCollector
            
            token_collector = PlaywrightTokenCollector()
            token_data = token_collector.get_token_with_playwright()
            
            if token_data:
                # 토큰 캐시 저장 (6시간 유효)
                if self.save_token_cache(token_data, expires_hours=6):
                    print("✅ 새로운 토큰 수집 및 캐싱 완료")
                    return True
            else:
                print("❌ 새로운 토큰 수집 실패")
                
        except Exception as e:
            print(f"❌ 토큰 수집 오류: {e}")
        
        return False
    
    def ensure_valid_token(self):
        """유효한 토큰 확보"""
        # 토큰이 없거나 만료 임박 시 새로 수집
        if not self.token or (self.token_expires_at and datetime.now() > self.token_expires_at - timedelta(minutes=30)):
            print("🔄 토큰 갱신 필요")
            return self.get_fresh_token()
        
        print("✅ 유효한 토큰 존재")
        return True
    
    def setup_headers(self):
        """API 요청 헤더 설정"""
        headers = {
            'authorization': f'Bearer {self.token}',
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://new.land.naver.com/',
            'Origin': 'https://new.land.naver.com',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache'
        }
        return headers
    
    def get_random_user_agent(self):
        """랜덤 User-Agent"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
        ]
        return random.choice(agents)
    
    def parse_url(self, url):
        """URL 파싱"""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        ms = query.get('ms', [''])[0]
        if ms:
            parts = ms.split(',')
            lat, lon, zoom = float(parts[0]), float(parts[1]), int(parts[2])
        else:
            lat, lon, zoom = 37.5665, 126.9780, 15
        
        return {
            'lat': lat,
            'lon': lon,
            'zoom': zoom,
            'article_types': query.get('a', [''])[0],
            'purpose': query.get('e', [''])[0]
        }
    
    def get_cortar_code(self, lat, lon, zoom):
        """지역코드 조회"""
        url = "https://new.land.naver.com/api/cortars"
        params = {
            'zoom': zoom,
            'centerLat': lat,
            'centerLon': lon
        }
        
        print(f"🔍 지역코드 조회: 위도 {lat}, 경도 {lon}")
        
        try:
            headers = self.setup_headers()
            time.sleep(random.uniform(1, 2))
            
            response = requests.get(url, headers=headers, params=params, cookies=self.cookies, timeout=10)
            print(f"📊 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data and 'cortarNo' in data:
                    cortar_no = data.get('cortarNo')
                    cortar_name = data.get('cortarName')
                    print(f"✅ 지역: {cortar_name} (코드: {cortar_no})")
                    return cortar_no
                elif data and isinstance(data, list) and len(data) > 0:
                    cortar = data[0]
                    cortar_no = cortar.get('cortarNo')
                    cortar_name = cortar.get('cortarName')
                    print(f"✅ 지역: {cortar_name} (코드: {cortar_no})")
                    return cortar_no
            elif response.status_code == 401:
                print("🔄 토큰 만료 감지, 새로운 토큰 수집 중...")
                if self.get_fresh_token():
                    return self.get_cortar_code(lat, lon, zoom)  # 재시도
            else:
                print(f"❌ 지역코드 조회 실패: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 지역코드 조회 오류: {e}")
        
        return None
    
    def get_article_detail(self, article_no):
        """개별 매물 상세정보 수집"""
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        params = {'complexNo': ''}
        
        try:
            headers = self.setup_headers()
            time.sleep(random.uniform(0.5, 1.0))  # 상세정보 수집 간격
            
            response = requests.get(url, headers=headers, params=params, cookies=self.cookies, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print(f"🔄 매물 {article_no} 상세정보 - 토큰 만료")
                if self.get_fresh_token():
                    headers = self.setup_headers()
                    response = requests.get(url, headers=headers, params=params, cookies=self.cookies, timeout=10)
                    if response.status_code == 200:
                        return response.json()
            else:
                print(f"⚠️ 매물 {article_no} 상세정보 조회 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 매물 {article_no} 상세정보 오류: {e}")
            return None
    
    def extract_useful_details(self, detail_data):
        """상세정보에서 핵심 정보만 추출"""
        if not detail_data:
            return None
            
        article_detail = detail_data.get('articleDetail', {})
        article_addition = detail_data.get('articleAddition', {})
        
        # 좌표에서 주소 변환 (카카오 API 사용)
        converted_address = None
        latitude = article_detail.get('latitude')
        longitude = article_detail.get('longitude')
        
        if self.address_converter and latitude and longitude:
            try:
                converted_address = self.address_converter.convert_coord_to_address(
                    str(latitude), str(longitude)
                )
            except Exception as e:
                print(f"⚠️ 주소 변환 오류: {e}")
        
        # 핵심 정보만 선별
        useful_info = {
            # 🏢 건물 상세 정보
            "건물정보": {
                "법적용도": article_detail.get('lawUsage'),
                "주차대수": article_detail.get('parkingCount'),
                "주차가능": "예" if article_detail.get('parkingPossibleYN') == 'Y' else "아니오",
                "엘리베이터": "있음" if "엘리베이터" in article_detail.get('tagList', []) else "없음",
                "층구조": article_detail.get('floorLayerName')
            },
            
            # 📍 위치 정보  
            "위치정보": {
                "정확한_위도": article_detail.get('latitude'),
                "정확한_경도": article_detail.get('longitude'),
                "상세주소": article_detail.get('exposureAddress'),
                "지하철도보시간": f"{article_detail.get('walkingTimeToNearSubway', 0)}분"
            },
            
            # 💰 관리비 정보
            "비용정보": {
                "월관리비": article_detail.get('monthlyManagementCost'),
                "관리비_포함항목": "전기, 수도, 인터넷 등"  # 필요시 상세 파싱
            },
            
            # 🏠 입주 정보
            "입주정보": {
                "입주가능일": article_detail.get('moveInTypeName'),
                "협의가능여부": article_detail.get('moveInDiscussionPossibleYN')
            },
            
            # 📷 이미지 정보
            "이미지": {
                "현장사진수": article_addition.get('siteImageCount', 0),
                "대표이미지": article_addition.get('representativeImgUrl')
            },
            
            # 🏘️ 주변 시세
            "주변시세": {
                "동일주소_매물수": article_addition.get('sameAddrCnt', 0),
                "최고가": article_addition.get('sameAddrMaxPrc'),
                "최저가": article_addition.get('sameAddrMinPrc')
            },
            
            # 📝 상세 설명 (정리됨)
            "상세설명": article_detail.get('detailDescription', '').strip()[:200]  # 200자로 제한
        }
        
        # 변환된 주소 정보 추가 (있는 경우)
        if converted_address:
            useful_info["카카오주소변환"] = converted_address
        
        return useful_info
    
    def collect_articles(self, cortar_no, parsed_url, max_pages=999, include_details=True, output_file=None):
        """매물 수집 (캐시된 토큰 사용)"""
        if not self.ensure_valid_token():
            print("❌ 유효한 토큰을 확보할 수 없습니다.")
            return 0
        
        url = "https://new.land.naver.com/api/articles"
        headers = self.setup_headers()
        
        base_params = {
            'cortarNo': cortar_no,
            'order': 'rank',
            'realEstateType': 'SG:SMS:GJCG:APTHGJ:GM:TJ',
            'tradeType': '',
            'tag': '::::::::',
            'rentPriceMin': '0',
            'rentPriceMax': '900000000',
            'priceMin': '0',
            'priceMax': '900000000',
            'areaMin': '0',
            'areaMax': '900000000',
            'oldBuildYears': '',
            'recentlyBuildYears': '',
            'minHouseHoldCount': '',
            'maxHouseHoldCount': '',
            'showArticle': 'false',
            'sameAddressGroup': 'false',
            'minMaintenanceCost': '',
            'maxMaintenanceCost': '',
            'priceType': 'RETAIL',
            'directions': '',
            'articleState': ''
        }
        
        if output_file:
            output_file.write('  "매물목록": [\n')
            is_first_article = True
        
        total_collected = 0
        
        print("🔄 캐시된 토큰으로 매물 수집 시작")
        
        for page in range(1, min(max_pages + 1, 10)):  # 테스트용으로 10페이지 제한
            params = base_params.copy()
            params['page'] = page
            
            print(f"📄 페이지 {page} 수집 중...")
            
            try:
                # 최적화된 대기시간
                delay = random.uniform(2, 4)
                time.sleep(delay)
                
                response = requests.get(url, headers=headers, params=params, cookies=self.cookies, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articleList', [])
                    is_more_data = data.get('isMoreData', False)
                    
                    if page == 1:
                        total_count = data.get('articleCount', 0)
                        print(f"📊 전체 매물 수: {total_count}")
                    
                    if articles:
                        for article in articles:
                            # 상세정보 수집 옵션이 활성화된 경우
                            if include_details:
                                article_no = article.get('articleNo')
                                if article_no:
                                    detail = self.get_article_detail(article_no)
                                    if detail:
                                        # 핵심 정보만 추출하여 저장
                                        useful_details = self.extract_useful_details(detail)
                                        if useful_details:
                                            article['상세정보'] = useful_details
                            
                            # 실시간 파일 쓰기
                            if output_file:
                                if not is_first_article:
                                    output_file.write(',\n')
                                else:
                                    is_first_article = False
                                
                                processed_article = {
                                    "매물번호": article.get('articleNo'),
                                    "매물명": article.get('articleName'),
                                    "부동산타입": article.get('realEstateTypeName'),
                                    "거래타입": article.get('tradeTypeName'),
                                    "매매가격": article.get('dealOrWarrantPrc', ''),
                                    "월세": article.get('rentPrc', ''),
                                    "전용면적": article.get('area1'),
                                    "공급면적": article.get('area2'),
                                    "층정보": article.get('floorInfo'),
                                    "방향": article.get('direction'),
                                    "주소": article.get('address', ''),
                                    "상세주소": article.get('buildingName', ''),
                                    "등록일": article.get('articleConfirmYMD'),
                                    "태그": article.get('tagList', []),
                                    "설명": article.get('articleFeatureDesc', '')
                                }
                                
                                # 정리된 상세정보가 있으면 추가
                                if '상세정보' in article:
                                    processed_article['상세정보'] = article['상세정보']
                                
                                json.dump(processed_article, output_file, ensure_ascii=False, indent=2)
                                output_file.flush()
                            
                            total_collected += 1
                        
                        print(f"✅ {len(articles)}개 수집 (누적: {total_collected}개)")
                        
                        if not is_more_data:
                            print("📄 더 이상 데이터 없음")
                            break
                    else:
                        print("📄 더 이상 매물이 없습니다.")
                        break
                        
                elif response.status_code == 401:
                    print("🔄 토큰 만료, 새로운 토큰 수집 중...")
                    if self.get_fresh_token():
                        headers = self.setup_headers()  # 헤더 갱신
                        continue  # 같은 페이지 재시도
                    else:
                        print("❌ 토큰 갱신 실패")
                        break
                else:
                    print(f"❌ 페이지 {page} 요청 실패: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"❌ 페이지 {page} 수집 오류: {e}")
                break
        
        if output_file:
            output_file.write('\n  ]')
            output_file.flush()
        
        print(f"\n🎯 캐시된 토큰 수집 완료: {total_collected}개 매물")
        return total_collected
    
    def collect_from_url(self, url, include_details=False, max_pages=10):
        """URL 기반 수집 (테스트용)"""
        print("🚀 캐시된 토큰 네이버 부동산 수집 시작")
        print("=" * 60)
        
        # 토큰 확보
        if not self.ensure_valid_token():
            print("❌ 토큰 확보 실패")
            return {'success': False, 'count': 0}
        
        # URL 파싱
        parsed = self.parse_url(url)
        print(f"📍 좌표: {parsed['lat']}, {parsed['lon']}")
        
        # 지역코드 조회
        cortar_no = self.get_cortar_code(parsed['lat'], parsed['lon'], parsed['zoom'])
        if not cortar_no:
            print("❌ 지역코드를 찾을 수 없습니다.")
            return {'success': False, 'count': 0}
        
        # 파일 준비
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_cached_token_{cortar_no}_{timestamp}.json"
        
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write('  "수집정보": {\n')
            f.write('    "수집시간": "' + timestamp + '",\n')
            f.write('    "지역코드": "' + cortar_no + '",\n')
            f.write('    "원본URL": ' + json.dumps(parsed, ensure_ascii=False) + ',\n')
            f.write('    "수집방식": "캐시된_토큰_기반"\n')
            f.write('  },\n')
            
            total_collected = self.collect_articles(
                cortar_no=cortar_no,
                parsed_url=parsed,
                max_pages=max_pages,
                include_details=include_details,
                output_file=f
            )
            
            f.write('\n}')
        
        if total_collected > 0:
            print(f"\n✅ 수집 성공: {total_collected}개 매물")
            print(f"💾 저장 완료: {filepath}")
            return {'success': True, 'filepath': filepath, 'count': total_collected}
        else:
            return {'success': False, 'count': 0}

def main():
    """테스트용 메인 함수"""
    import sys
    
    collector = CachedTokenCollector()
    
    # 테스트 URL
    url = "https://new.land.naver.com/offices?ms=37.4986291,127.0359669,13&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL"
    
    # 수집 실행 (상세정보 포함 테스트, 1페이지만)
    result = collector.collect_from_url(url, include_details=True, max_pages=1)
    
    if result['success']:
        print(f"🎉 테스트 성공: {result['count']}개 매물 수집")
    else:
        print("❌ 테스트 실패")

# ==============================
# 병렬 처리용 독립 함수 
# ==============================

def collect_by_cortar_no(cortar_no: str, include_details: bool = True, max_pages: int = 999):
    """cortar_no로 매물 수집 (최적화된 캐시 토큰 버전)"""
    from supabase_client import SupabaseHelper
    
    try:
        # Supabase에서 지역 정보 조회
        helper = SupabaseHelper()
        result = helper.client.table('areas').select('*').eq('cortar_no', cortar_no).execute()
        
        if not result.data:
            print(f"❌ 지역 정보를 찾을 수 없습니다: {cortar_no}")
            return {'success': False, 'filepath': None, 'count': 0, 'error': '지역 정보 없음'}
        
        area_info = result.data[0]
        dong_name = area_info['dong_name']
        center_lat = area_info['center_lat']
        center_lon = area_info['center_lon']
        
        print(f"🎯 수집 대상: {dong_name} ({cortar_no})")
        print(f"📍 중심좌표: {center_lat}, {center_lon}")
        
        # 최적화된 수집기 생성 (토큰 캐싱 사용)
        collector = CachedTokenCollector()
        
        # 토큰 확보
        if not collector.ensure_valid_token():
            print("❌ 토큰 확보 실패")
            return {'success': False, 'filepath': None, 'count': 0, 'error': '토큰 확보 실패'}
        
        print(f"🚀 최적화된 수집 시작: {dong_name}")
        
        # 파일 준비 (스트리밍 방식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_optimized_{dong_name}_{cortar_no}_{timestamp}.json"
        
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write('  "수집정보": {\n')
            f.write('    "수집시간": "' + timestamp + '",\n')
            f.write('    "지역코드": "' + cortar_no + '",\n')
            f.write('    "동이름": "' + dong_name + '",\n')
            f.write('    "수집방식": "최적화된_캐시토큰_기반",\n')
            f.write('    "버전": "v2.0_optimized"\n')
            f.write('  },\n')
            
            # 직접 수집 (지역코드 조회 생략)
            total_collected = collector.collect_articles(
                cortar_no=cortar_no,
                parsed_url={"direct_cortar": True, "dong_name": dong_name},
                max_pages=max_pages,
                include_details=include_details,
                output_file=f
            )
            
            f.write('\n}')
        
        result = {
            'success': total_collected > 0,
            'filepath': filepath,
            'count': total_collected,
            'dong_name': dong_name
        }
        
        if result['success']:
            print(f"✅ {dong_name} 최적화 수집 완료 ({result['count']}개 매물)")
            return result
        else:
            print(f"❌ {dong_name} 수집 실패")
            return result
        
    except Exception as e:
        print(f"❌ 수집 중 오류: {e}")
        return {'success': False, 'filepath': None, 'count': 0, 'error': str(e)}

if __name__ == "__main__":
    main()