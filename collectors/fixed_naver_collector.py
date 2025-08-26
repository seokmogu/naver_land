#!/usr/bin/env python3
"""
분석 결과 기반 네이버 부동산 수집기
실제 API 호출 패턴을 정확히 재현합니다.
"""

import requests
import json
import time
import os
import random
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from kakao_address_converter import KakaoAddressConverter

def get_random_user_agent():
    """VM 차단 우회를 위한 랜덤 User-Agent 생성"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0"
    ]
    return random.choice(user_agents)

class FixedNaverCollector:
    def __init__(self, token_data, use_address_converter=True):
        if not token_data:
            raise ValueError("JWT 토큰이 필요합니다.")
        
        # token_data가 문자열이면 기존 방식, dict이면 새로운 방식
        if isinstance(token_data, str):
            self.token = token_data
            self.cookies = {}
        else:
            self.token = token_data['token']
            self.cookies = {cookie['name']: cookie['value'] for cookie in token_data['cookies']}
        self.headers = {
            'authorization': f'Bearer {self.token}',
            'User-Agent': get_random_user_agent(),
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://new.land.naver.com/',
            'Origin': 'https://new.land.naver.com',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # 주소 변환기 초기화 (선택적)
        self.address_converter = None
        if use_address_converter:
            try:
                self.address_converter = KakaoAddressConverter()
                print("🗺️ 카카오 주소 변환기 활성화")
            except ValueError as e:
                print(f"⚠️ 주소 변환기 비활성화: {e}")
                self.address_converter = None
        
    def parse_url(self, url):
        """URL 파싱"""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        # ms 파라미터에서 좌표 추출
        ms = query.get('ms', [''])[0]
        if ms:
            parts = ms.split(',')
            lat, lon, zoom = float(parts[0]), float(parts[1]), int(parts[2])
        else:
            lat, lon, zoom = 37.5665, 126.9780, 15
        
        # 매물 타입 추출
        article_types = query.get('a', [''])[0]
        purpose = query.get('e', [''])[0]
        
        return {
            'lat': lat,
            'lon': lon, 
            'zoom': zoom,
            'article_types': article_types,
            'purpose': purpose,
            'property_type': parsed.path.split('/')[-1]
        }
    
    def get_cortar_code(self, lat, lon, zoom):
        """좌표로 지역코드 조회 (분석된 실제 API)"""
        url = "https://new.land.naver.com/api/cortars"
        params = {
            'zoom': zoom,
            'centerLat': lat,
            'centerLon': lon
        }
        
        print(f"🔍 지역코드 조회: 위도 {lat}, 경도 {lon}")
        print(f"🌐 요청 URL: {url}")
        print(f"📋 파라미터: {params}")
        
        try:
            # 최적화된 요청 간격
            time.sleep(1.5)  # 1.5초 대기로 단축
            response = requests.get(url, headers=self.headers, params=params, cookies=self.cookies)
            print(f"📊 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"📄 응답 데이터: {data}")
                    
                    # 응답이 단일 객체인 경우 처리
                    if data and 'cortarNo' in data:
                        cortar_no = data.get('cortarNo')
                        cortar_name = data.get('cortarName')
                        print(f"✅ 지역: {cortar_name} (코드: {cortar_no})")
                        return cortar_no
                    # 응답이 배열인 경우 처리
                    elif data and isinstance(data, list) and len(data) > 0:
                        cortar = data[0]
                        cortar_no = cortar.get('cortarNo')
                        cortar_name = cortar.get('cortarName')
                        print(f"✅ 지역: {cortar_name} (코드: {cortar_no})")
                        return cortar_no
                    else:
                        print("❌ 지역 데이터가 없습니다.")
                        print(f"📄 실제 응답: {data}")
                except json.JSONDecodeError as je:
                    print(f"❌ JSON 파싱 오류: {je}")
                    print(f"📄 원본 응답: {response.text[:500]}")
            else:
                print(f"❌ 지역코드 조회 실패: {response.status_code}")
                print(f"📄 응답 내용: {response.text[:500]}")
                
        except Exception as e:
            print(f"❌ 지역코드 조회 오류: {e}")
            print(f"🔍 오류 타입: {type(e)}")
        
        return None
    
    def get_article_detail(self, article_no):
        """개별 매물 상세정보 수집"""
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        params = {'complexNo': ''}
        
        try:
            # 최적화된 요청 간격
            time.sleep(1.5)  # 1.5초 대기로 단축
            response = requests.get(url, headers=self.headers, params=params, cookies=self.cookies)
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
        """매물 수집 (무한스크롤 시뮬레이션 - 분석된 실제 패턴)"""
        url = "https://new.land.naver.com/api/articles"
        
        # 실제 분석된 파라미터 사용 (URL 인코딩 없이)
        base_params = {
            'cortarNo': cortar_no,
            'order': 'rank',
            'realEstateType': 'SG:SMS:GJCG:APTHGJ:GM:TJ',  # 오피스/상가
            'tradeType': '',  # 모든 거래 타입
            'tag': '::::::::',  # 빈 태그
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
            'priceType': 'RETAIL',  # 상업용
            'directions': '',
            'articleState': ''
        }
        
        # 스트리밍 파일 쓰기 준비
        if output_file:
            output_file.write('  "매물목록": [\n')
            is_first_article = True
        
        total_collected = 0
        total_expected = 0
        
        print("🔄 무한스크롤 시뮬레이션 (데이터 없을 때까지 자동 수집)")
        if output_file:
            print("💾 실시간 파일 저장 모드 (메모리 절약)")
        
        for page in range(1, max_pages + 1):
            params = base_params.copy()
            params['page'] = page
            
            print(f"📄 페이지 {page} 수집 중...")
            
            try:
                # 요청 간 딜레이 추가 (차단 방지)
                if page > 1:
                    time.sleep(0.3)  # 0.3초 대기 (속도 최적화)
                
                # 최적화된 대기 시간 (차단 방지 + 성능 균형)
                delay = random.uniform(2, 4)  # 2-4초 랜덤 대기로 단축
                time.sleep(delay)
                response = requests.get(url, headers=self.headers, params=params, cookies=self.cookies)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articleList', [])
                    # articleCount 필드가 없을 수 있으므로 실제 매물 수로 추정
                    total_count = data.get('articleCount')
                    is_more_data = data.get('isMoreData', False)
                    
                    if page == 1:
                        if total_count is not None and total_count > 0:
                            total_expected = total_count
                            print(f"📊 전체 매물 수: {total_count}")
                            estimated_pages = (total_expected + 19) // 20
                            print(f"📄 예상 페이지 수: {estimated_pages}")
                        else:
                            # articleCount가 없으면 무한스크롤로 추정
                            print(f"📊 무한스크롤 모드 (정확한 총 개수 미제공)")
                            print(f"📊 첫 페이지 매물: {len(articles)}개")
                            total_expected = 0  # 동적으로 증가시킴
                            print(f"📄 예상 페이지 수: 알 수 없음 (무한스크롤)")
                        print(f"🔄 더 많은 데이터 여부: {is_more_data}")
                    
                    if articles:
                        # 매물별 처리 (실시간 저장)
                        for i, article in enumerate(articles):
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
                                    
                                    # 상세정보 수집 간 딜레이 (최적화)
                                    time.sleep(0.5)  # 0.5초로 적절히 조정
                            
                            # 실시간 파일 쓰기
                            if output_file:
                                if not is_first_article:
                                    output_file.write(',\n')
                                else:
                                    is_first_article = False
                                
                                # 매물 정보 정리
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
                                output_file.flush()  # 즉시 디스크에 쓰기
                            
                            total_collected += 1
                        
                        # 진행률 표시
                        if total_expected > 0:
                            percentage = min((total_collected / total_expected * 100), 100.0)  # 100% 초과 방지
                            progress_msg = f" / {percentage:.1f}%"
                        else:
                            # 무한스크롤 모드에서는 진행률 대신 수집량만 표시
                            progress_msg = ""
                        
                        detail_msg = " (상세정보 포함)" if include_details else ""
                        print(f"✅ {len(articles)}개 수집{detail_msg} (누적: {total_collected}개{progress_msg})")
                        
                        # 실제 무한스크롤처럼 페이지당 20개가 기본
                        if len(articles) < 20 and page > 1:
                            print("📄 마지막 페이지 감지 (20개 미만)")
                        
                        # isMoreData가 False면 더 이상 데이터 없음
                        if not is_more_data:
                            print("📄 API에서 더 이상 데이터 없음을 알림 (isMoreData: false)")
                            break
                    else:
                        print("📄 더 이상 매물이 없습니다.")
                        break
                        
                else:
                    print(f"❌ 페이지 {page} 요청 실패: {response.status_code}")
                    if response.status_code == 401:
                        print("🔑 토큰이 만료되었을 수 있습니다.")
                    break
                    
            except Exception as e:
                print(f"❌ 페이지 {page} 수집 오류: {e}")
                break
        
        # 파일 마무리
        if output_file:
            output_file.write('\n  ]')  # 매물목록만 닫기 (전체 JSON은 상위에서 닫음)
            output_file.flush()
        
        print(f"\n🎯 무한스크롤 시뮬레이션 완료:")
        print(f"   - 요청한 페이지: {page}")
        print(f"   - 수집된 매물: {total_collected}개")
        if total_expected > 0:
            completion = min((total_collected / total_expected * 100), 100.0)
            print(f"   - 완료율: {completion:.1f}%")
            if total_collected > total_expected:
                print(f"   ⚠️ 실제 수집량이 예상보다 많음 (예상: {total_expected}개)")
        else:
            print(f"   - 무한스크롤 모드 (진행률 계산 불가)")
        
        return total_collected
    
    def get_dong_name_by_cortar(self, cortar_no):
        """지역코드로 동 이름 조회"""
        try:
            from supabase_client import SupabaseHelper
            helper = SupabaseHelper()
            result = helper.client.table('areas').select('dong_name, gu_name').eq('cortar_no', cortar_no).execute()
            
            if result.data and len(result.data) > 0:
                area = result.data[0]
                return f"{area['gu_name']}_{area['dong_name']}"
            else:
                return None
        except Exception as e:
            print(f"⚠️ 동 이름 조회 실패: {e}")
            return None

    def save_results(self, articles, parsed_url, cortar_no):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 매물 정보 정리
        processed_articles = []
        for article in articles:
            processed_articles.append({
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
                "등록일": article.get('articleConfirmYmd'),
                "태그": article.get('tagList', []),
                "설명": article.get('articleFeatureDesc', '')
            })
        
        # 통계 생성
        stats = {
            "총매물수": len(articles),
            "부동산타입별": {},
            "거래타입별": {},
            "가격대별": {"1억미만": 0, "1-5억": 0, "5-10억": 0, "10억이상": 0}
        }
        
        for article in articles:
            # 타입별 통계
            re_type = article.get('realEstateTypeName', '기타')
            trade_type = article.get('tradeTypeName', '기타')
            
            stats["부동산타입별"][re_type] = stats["부동산타입별"].get(re_type, 0) + 1
            stats["거래타입별"][trade_type] = stats["거래타입별"].get(trade_type, 0) + 1
            
            # 가격대별 통계
            price = article.get('dealOrWarrantPrc', 0)
            if isinstance(price, str):
                price = 0
            
            if price < 10000:  # 1억 미만
                stats["가격대별"]["1억미만"] += 1
            elif price < 50000:  # 5억 미만
                stats["가격대별"]["1-5억"] += 1
            elif price < 100000:  # 10억 미만
                stats["가격대별"]["5-10억"] += 1
            else:
                stats["가격대별"]["10억이상"] += 1
        
        # 최종 결과
        result = {
            "수집정보": {
                "수집시간": timestamp,
                "지역코드": cortar_no,
                "원본URL": parsed_url,
                "API패턴": "실제_분석된_패턴"
            },
            "통계": stats,
            "매물목록": processed_articles
        }
        
        # 결과 폴더에 저장
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # 동 이름 조회
        dong_info = self.get_dong_name_by_cortar(cortar_no)
        if dong_info:
            filename = f"naver_fixed_{dong_info}_{cortar_no}_{timestamp}.json"
        else:
            filename = f"naver_fixed_{cortar_no}_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 저장 완료: {filepath}")
        return filepath
    
    def collect_from_url(self, url, include_details=True, max_pages=999):
        """URL 기반 전체 수집 프로세스"""
        print("🚀 네이버 부동산 수집 시작 (분석된 실제 패턴)")
        print("=" * 60)
        
        # 1. URL 파싱
        parsed = self.parse_url(url)
        print(f"📍 좌표: {parsed['lat']}, {parsed['lon']} (줌: {parsed['zoom']})")
        
        # 2. 지역코드 조회
        cortar_no = self.get_cortar_code(parsed['lat'], parsed['lon'], parsed['zoom'])
        if not cortar_no:
            print("❌ 지역코드를 찾을 수 없어 수집을 중단합니다.")
            return
        
        # 3. 파일 준비 (스트리밍 방식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 동 이름 조회
        dong_info = self.get_dong_name_by_cortar(cortar_no)
        if dong_info:
            filename = f"naver_streaming_{dong_info}_{cortar_no}_{timestamp}.json"
        else:
            filename = f"naver_streaming_{cortar_no}_{timestamp}.json"
        
        # 4. 매물 수집 (실시간 파일 쓰기)
        # 결과 폴더 생성
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            # 전체 JSON 구조 시작
            f.write('{\n')
            
            # 메타데이터 작성
            f.write('  "수집정보": {\n')
            f.write('    "수집시간": "' + timestamp + '",\n')
            f.write('    "지역코드": "' + cortar_no + '",\n')
            f.write('    "원본URL": ' + json.dumps(parsed, ensure_ascii=False) + ',\n')
            f.write('    "수집방식": "실시간_스트리밍"\n')
            f.write('  },\n')
            
            # 스트리밍 수집 시작
            total_collected = self.collect_articles(cortar_no, parsed, max_pages=max_pages, include_details=include_details, output_file=f)
            
            # 전체 JSON 구조 종료
            f.write('\n}')  # 최종 닫는 중괄호
        
        if total_collected > 0:
            # 5. 요약 출력
            print("\n" + "=" * 60)
            print("📊 수집 완료 요약")
            print("=" * 60)
            print(f"총 {total_collected}개 매물 수집")
            print(f"💾 저장 완료: {filepath}")
            print("🎯 메모리 효율적인 스트리밍 방식으로 수집됨")
            return {'success': True, 'filepath': filepath, 'count': total_collected}
        else:
            print("\n❌ 수집된 매물이 없습니다.")
            return {'success': False, 'filepath': None, 'count': 0}

def collect_by_cortar_no(cortar_no: str, include_details: bool = True, max_pages: int = 999) -> bool:
    """cortar_no로 매물 수집"""
    from playwright_token_collector import PlaywrightTokenCollector
    from supabase_client import SupabaseHelper
    
    try:
        # Supabase에서 지역 정보 조회
        helper = SupabaseHelper()
        result = helper.client.table('areas').select('*').eq('cortar_no', cortar_no).execute()
        
        if not result.data:
            print(f"❌ 지역 정보를 찾을 수 없습니다: {cortar_no}")
            return False
        
        area_info = result.data[0]
        dong_name = area_info['dong_name']
        center_lat = area_info['center_lat']
        center_lon = area_info['center_lon']
        
        print(f"🎯 수집 대상: {dong_name} ({cortar_no})")
        print(f"📍 중심좌표: {center_lat}, {center_lon}")
        
        # 토큰 획득
        print("🔑 토큰 수집 중...")
        token_collector = PlaywrightTokenCollector()
        token_data = token_collector.get_token_with_playwright()
        
        if not token_data:
            print("❌ 토큰 획득 실패")
            return False
        
        # 수집기 생성
        collector = FixedNaverCollector(token_data)
        
        # 직접 cortar_no로 수집 (불필요한 지역코드 조회 건너뛰기)
        print(f"🚀 직접 cortar_no로 수집 시작: {cortar_no}")
        
        # 파일 준비 (스트리밍 방식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_streaming_{dong_name}_{cortar_no}_{timestamp}.json"
        
        # 결과 폴더 생성
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            # 전체 JSON 구조 시작
            f.write('{\n')
            
            # 메타데이터 작성
            f.write('  "수집정보": {\n')
            f.write('    "수집시간": "' + timestamp + '",\n')
            f.write('    "지역코드": "' + cortar_no + '",\n')
            f.write('    "동이름": "' + dong_name + '",\n')
            f.write('    "수집방식": "cortar_no_직접수집"\n')
            f.write('  },\n')
            
            # 스트리밍 수집 시작 (지역코드 조회 없이 바로 수집)
            total_collected = collector.collect_articles(
                cortar_no=cortar_no,
                parsed_url={"direct_cortar": True},
                max_pages=max_pages,
                include_details=include_details,
                output_file=f
            )
            
            # 전체 JSON 구조 종료
            f.write('\n}')
        
        result = {
            'success': total_collected > 0,
            'filepath': filepath,
            'count': total_collected
        }
        
        if result['success']:
            print(f"✅ {dong_name} 수집 완료 ({result['count']}개 매물)")
            return result
        else:
            print(f"❌ {dong_name} 수집 실패")
            return result
        
    except Exception as e:
        print(f"❌ 수집 중 오류: {e}")
        return {'success': False, 'filepath': None, 'count': 0, 'error': str(e)}

def main():
    import sys
    from playwright_token_collector import PlaywrightTokenCollector
    
    # 커맨드라인 인자 확인
    if len(sys.argv) > 1:
        cortar_no = sys.argv[1]
        include_details = len(sys.argv) <= 2 or sys.argv[2].lower() != 'false'
        max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 999
        
        print(f"🚀 배치 모드: {cortar_no} 수집 시작")
        result = collect_by_cortar_no(cortar_no, include_details, max_pages)
        sys.exit(0 if result['success'] else 1)
    
    # Interactive 모드 (기존 방식)
    # 토큰 수집
    print("🔑 토큰 수집 중...")
    token_collector = PlaywrightTokenCollector()
    token = token_collector.get_token_with_playwright()
    
    if not token:
        print("❌ 토큰 획득 실패")
        return
    
    # 수집기 생성
    collector = FixedNaverCollector(token)
    
    # URL 입력
    url = input("네이버 부동산 URL을 입력하세요: ").strip()
    if not url:
        print("❌ URL이 입력되지 않았습니다.")
        return
    
    # 상세정보 수집 옵션
    print("\n📋 수집 옵션:")
    print("1. 기본 정보만 수집 (빠름)")
    print("2. 상세정보 포함 수집 (느림, 더 많은 데이터)")
    choice = input("선택하세요 (1 또는 2, 기본값: 2): ").strip()
    
    include_details = choice != "1"
    if include_details:
        print("🔍 상세정보 포함 모드로 수집합니다.")
    else:
        print("⚡ 기본 정보만 빠르게 수집합니다.")
    
    # 수집 실행
    collector.collect_from_url(url, include_details)

if __name__ == "__main__":
    main()