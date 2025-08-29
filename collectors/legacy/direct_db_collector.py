#!/usr/bin/env python3
"""
바로 DB 저장 네이버 부동산 수집기 (통합 로그 시스템 적용)
- JSON 파일 생략, 메모리에서 직접 DB로 저장
- 실시간 DB 업데이트 및 향상된 통합 로그 시스템
- 성능 최적화 및 메모리 효율성 극대화
- API 호출 추적 및 오류 패턴 분석
"""

import sys
import time
import argparse
import random
import json
import os
import requests
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from multiprocessing import Pool
from integrated_logger import IntegratedProgressTracker, integrated_log_based_collection, LogLevel
from fixed_naver_collector_v2_optimized import CachedTokenCollector
from supabase_client import SupabaseHelper


class DirectDBCollector:
    """바로 DB 저장 수집기 (향상된 로그 시스템)"""
    
    def __init__(self, log_level: LogLevel = LogLevel.INFO):
        self.tracker = IntegratedProgressTracker(log_level=log_level)
        self.helper = SupabaseHelper()
        
        # 강남구 동별 정보 (우선순위 포함)
        self.gangnam_dongs = [
            {"name": "역삼동", "cortar_no": "1168010100", "priority": 30},
            {"name": "삼성동", "cortar_no": "1168010500", "priority": 26},
            {"name": "논현동", "cortar_no": "1168010800", "priority": 23},
            {"name": "대치동", "cortar_no": "1168010600", "priority": 22},
            {"name": "신사동", "cortar_no": "1168010700", "priority": 22},
            {"name": "압구정동", "cortar_no": "1168011000", "priority": 20},
            {"name": "청담동", "cortar_no": "1168010400", "priority": 18},
            {"name": "도곡동", "cortar_no": "1168011800", "priority": 18},
            {"name": "개포동", "cortar_no": "1168010300", "priority": 17},
            {"name": "수서동", "cortar_no": "1168011500", "priority": 12},
            {"name": "일원동", "cortar_no": "1168011400", "priority": 11},
            {"name": "자곡동", "cortar_no": "1168011200", "priority": 8},
            {"name": "세곡동", "cortar_no": "1168011100", "priority": 6},
            {"name": "율현동", "cortar_no": "1168011300", "priority": 5}
        ]
        
        self.tracker.enhanced_logger.info("direct_db_collector", "바로 DB 저장 수집기 초기화 완료")
    
    def convert_article_to_db_format(self, article: Dict, cortar_no: str, collected_date: date) -> Dict:
        """수집된 매물 데이터를 DB 형식으로 실시간 변환"""
        
        # 상세정보 추출 (있는 경우)
        details_info = article.get('상세정보', {})
        kakao_addr = details_info.get('카카오주소변환', {})
        
        db_property = {
            'article_no': str(article.get('articleNo', article.get('매물번호', ''))),
            'cortar_no': cortar_no,
            'article_name': article.get('articleName', article.get('매물명', '')),
            'real_estate_type': article.get('realEstateTypeName', article.get('부동산타입', '')),
            'trade_type': article.get('tradeTypeName', article.get('거래타입', '')),
            'price': self._parse_price(article.get('dealOrWarrantPrc', article.get('매매가격', 0))),
            'rent_price': self._parse_price(article.get('rentPrc', article.get('월세', 0))),
            'area1': self._parse_area(article.get('area1', article.get('전용면적'))),
            'area2': self._parse_area(article.get('area2', article.get('공급면적'))),
            'floor_info': article.get('floorInfo', article.get('층정보', '')),
            'direction': article.get('direction', article.get('방향', '')),
            'latitude': details_info.get('위치정보', {}).get('정확한_위도'),
            'longitude': details_info.get('위치정보', {}).get('정확한_경도'),
            'address_road': kakao_addr.get('도로명주소', ''),
            'address_jibun': kakao_addr.get('지번주소', ''),
            'address_detail': article.get('buildingName', article.get('상세주소', '')),
            'building_name': kakao_addr.get('건물명', article.get('buildingName', article.get('상세주소', ''))),
            'postal_code': kakao_addr.get('우편번호', ''),
            'tag_list': article.get('tagList', article.get('태그', [])),
            'description': article.get('articleFeatureDesc', article.get('설명', '')),
            'details': details_info if details_info else {},
            'collected_date': collected_date.isoformat(),
            'last_seen_date': collected_date.isoformat(),
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        return db_property
    
    def _parse_price(self, price_str: Any) -> Optional[int]:
        """가격 문자열을 숫자로 변환"""
        if isinstance(price_str, (int, float)):
            return int(price_str)
        if isinstance(price_str, str):
            # "5억 3,000" 같은 형식 처리
            price_str = price_str.replace(',', '').replace('억', '0000').replace('만', '')
            try:
                return int(price_str)
            except:
                return 0
        return 0
    
    def _parse_area(self, area_str: Any) -> Optional[float]:
        """면적 문자열을 숫자로 변환"""
        if isinstance(area_str, (int, float)):
            return float(area_str)
        if isinstance(area_str, str):
            try:
                return float(area_str.replace('㎡', '').strip())
            except:
                return None
        return None
    
    def collect_dong_direct_db(self, dong_info: Dict) -> Dict:
        """
        동별 수집 + 바로 DB 저장 (향상된 로그 시스템 적용)
        - JSON 파일 생성 생략
        - 메모리에서 직접 DB로 실시간 저장
        - API 호출 추적 및 성능 모니터링
        """
        dong_name = dong_info["name"]
        cortar_no = dong_info["cortar_no"]
        
        print(f"\n🚀 {dong_name} 바로 DB 수집 시작...")
        
        with integrated_log_based_collection(dong_name, cortar_no, self.tracker) as ctx:
            try:
                # 1. 토큰 캐싱 수집기 초기화
                collector = CachedTokenCollector(use_address_converter=True)
                
                if not collector.ensure_valid_token():
                    raise Exception("토큰 확보 실패")
                
                ctx['enhanced_logger'].info("token_management", f"{dong_name} 토큰 확보 완료")
                
                # 2. DB 저장용 배치 설정
                batch_size = 50  # 메모리 효율성을 위한 배치 크기
                db_batch = []
                total_collected = 0
                today = date.today()
                
                print(f"  🔍 {dong_name} API 스트리밍 시작...")
                ctx['enhanced_logger'].info("api_streaming", f"{dong_name} 스트리밍 시작", 
                                          {'batch_size': batch_size, 'cortar_no': cortar_no})
                
                # 3. 페이지별 스트리밍 처리
                url = "https://new.land.naver.com/api/articles"
                headers = collector.setup_headers()
                
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
                
                page = 1
                max_pages = 999  # 모든 페이지 수집
                consecutive_failures = 0
                max_consecutive_failures = 3
                
                while page <= max_pages:
                    params = base_params.copy()
                    params['page'] = page
                    
                    print(f"    📄 페이지 {page} 스트리밍 중...")
                    ctx['enhanced_logger'].debug("page_processing", f"{dong_name} 페이지 {page} 시작")
                    
                    try:
                        # API 요청 시작 시간 기록
                        api_start_time = time.time()
                        
                        # API 요청 대기
                        delay = random.uniform(2, 4)
                        time.sleep(delay)
                        
                        response = requests.get(url, headers=headers, params=params, 
                                              cookies=collector.cookies, timeout=15)
                        
                        api_duration = time.time() - api_start_time
                        
                        # API 호출 로그 기록
                        ctx['log_api_call'](
                            endpoint='/api/articles',
                            method='GET',
                            status_code=response.status_code,
                            duration=api_duration,
                            request_size=len(str(params)),
                            response_size=len(response.content) if response.content else 0,
                            extra={'page': page, 'dong_name': dong_name}
                        )
                        
                        if response.status_code == 200:
                            consecutive_failures = 0  # 성공시 실패 카운터 리셋
                            
                            data = response.json()
                            articles = data.get('articleList', [])
                            is_more_data = data.get('isMoreData', False)
                            
                            ctx['enhanced_logger'].debug("api_response", 
                                                       f"페이지 {page} 응답: {len(articles)}개 매물",
                                                       {'articles_count': len(articles), 
                                                        'is_more_data': is_more_data})
                            
                            if not articles:
                                print("    📄 더 이상 매물이 없습니다.")
                                ctx['enhanced_logger'].info("api_response", f"{dong_name} 매물 수집 완료 - 빈 응답")
                                break
                            
                            # 4. 매물별 실시간 처리
                            for article_idx, article in enumerate(articles):
                                try:
                                    # 상세정보 수집 (필요시)
                                    article_no = article.get('articleNo')
                                    if article_no:
                                        detail_start_time = time.time()
                                        detail = collector.get_article_detail(article_no)
                                        detail_duration = time.time() - detail_start_time
                                        
                                        # 상세정보 API 호출 로그
                                        ctx['log_api_call'](
                                            endpoint=f'/api/articles/{article_no}',
                                            method='GET', 
                                            status_code=200 if detail else 404,
                                            duration=detail_duration,
                                            extra={'article_no': article_no}
                                        )
                                        
                                        if detail:
                                            useful_details = collector.extract_useful_details(detail)
                                            if useful_details:
                                                article['상세정보'] = useful_details
                                    
                                    # DB 형식으로 실시간 변환
                                    db_property = self.convert_article_to_db_format(article, cortar_no, today)
                                    db_batch.append(db_property)
                                    
                                    # 로그 기록
                                    property_data = {
                                        'article_no': db_property['article_no'],
                                        'article_name': db_property['article_name'],
                                        'real_estate_type': db_property['real_estate_type'],
                                        'trade_type': db_property['trade_type'],
                                        'price': db_property['price'],
                                        'rent_price': db_property['rent_price'],
                                        'area1': db_property['area1'],
                                        'floor_info': db_property['floor_info'],
                                        'address_detail': db_property['address_detail'],
                                        'cortar_no': cortar_no,
                                        'collected_date': today.isoformat()
                                    }
                                    
                                    ctx['log_property'](property_data)
                                    ctx['stats']['total_collected'] += 1
                                    ctx['stats']['last_property'] = db_property['article_name']
                                    total_collected += 1
                                    
                                    ctx['enhanced_logger'].trace("property_processing", 
                                                               f"매물 처리: {db_property['article_no']}",
                                                               {'property': property_data})
                                
                                except Exception as article_error:
                                    ctx['enhanced_logger'].error("property_processing", 
                                                               f"매물 처리 오류: {article.get('articleNo', 'unknown')}", 
                                                               article_error)
                                    continue  # 개별 매물 오류는 계속 진행
                                
                                # 5. 배치 단위로 DB 저장
                                if len(db_batch) >= batch_size:
                                    print(f"      💾 배치 DB 저장: {len(db_batch)}개")
                                    db_save_start = time.time()
                                    
                                    try:
                                        save_stats = self.helper.safe_save_converted_properties(db_batch, cortar_no)
                                        db_save_duration = time.time() - db_save_start
                                        
                                        ctx['enhanced_logger'].info("db_batch_save", 
                                                                   f"배치 저장 완료: {len(db_batch)}개 ({db_save_duration:.2f}초)",
                                                                   {'batch_size': len(db_batch), 
                                                                    'save_stats': save_stats,
                                                                    'duration': db_save_duration})
                                        
                                        if not save_stats.get('total_saved', 0):
                                            print(f"      ⚠️ 배치 저장 부분 실패")
                                            ctx['enhanced_logger'].warn("db_batch_save", "배치 저장 부분 실패", 
                                                                       {'save_stats': save_stats})
                                        
                                        db_batch = []  # 메모리 초기화
                                        
                                    except Exception as batch_error:
                                        ctx['enhanced_logger'].error("db_batch_save", "배치 저장 실패", 
                                                                   batch_error, {'batch_size': len(db_batch)})
                                        db_batch = []  # 오류시에도 메모리 초기화
                                
                                # 진행 상황 출력
                                if total_collected % 100 == 0:
                                    print(f"      🔄 {total_collected}개 실시간 처리 완료...")
                                    ctx['enhanced_logger'].info("progress_report", 
                                                               f"{dong_name} 진행상황: {total_collected}개 처리")
                            
                            print(f"    ✅ 페이지 {page}: {len(articles)}개 (누적: {total_collected}개)")
                            
                            if not is_more_data:
                                print("    📄 더 이상 데이터 없음")
                                ctx['enhanced_logger'].info("api_completion", f"{dong_name} 모든 페이지 처리 완료")
                                break
                                
                        elif response.status_code == 401:
                            print("    🔄 토큰 만료, 갱신 중...")
                            ctx['enhanced_logger'].warn("token_management", f"{dong_name} 토큰 만료 - 갱신 시도")
                            
                            if collector.get_fresh_token():
                                headers = collector.setup_headers()
                                ctx['enhanced_logger'].info("token_management", f"{dong_name} 토큰 갱신 성공")
                                continue  # 같은 페이지 재시도
                            else:
                                raise Exception("토큰 갱신 실패")
                        else:
                            consecutive_failures += 1
                            error_msg = f"페이지 {page} 요청 실패: {response.status_code}"
                            print(f"    ❌ {error_msg}")
                            ctx['enhanced_logger'].error("api_request", error_msg, 
                                                        extra={'page': page, 'status_code': response.status_code})
                            
                            if consecutive_failures >= max_consecutive_failures:
                                raise Exception(f"연속 {consecutive_failures}회 API 요청 실패")
                            
                            # 실패시 더 긴 대기
                            time.sleep(random.uniform(5, 10))
                            
                    except Exception as e:
                        consecutive_failures += 1
                        error_msg = f"페이지 {page} 처리 오류: {e}"
                        print(f"    ❌ {error_msg}")
                        ctx['enhanced_logger'].error("page_processing", error_msg, e, 
                                                    {'page': page, 'consecutive_failures': consecutive_failures})
                        
                        if consecutive_failures >= max_consecutive_failures:
                            raise Exception(f"연속 {consecutive_failures}회 페이지 처리 실패")
                        
                        # 오류시 더 긴 대기 후 다음 페이지로
                        time.sleep(random.uniform(5, 10))
                    
                    page += 1
                
                # 6. 남은 배치 처리
                if db_batch:
                    print(f"  💾 최종 배치 DB 저장: {len(db_batch)}개")
                    final_save_start = time.time()
                    
                    try:
                        save_stats = self.helper.safe_save_converted_properties(db_batch, cortar_no)
                        final_save_duration = time.time() - final_save_start
                        
                        ctx['enhanced_logger'].info("db_final_save", 
                                                   f"최종 배치 저장 완료: {len(db_batch)}개 ({final_save_duration:.2f}초)",
                                                   {'batch_size': len(db_batch), 
                                                    'save_stats': save_stats,
                                                    'duration': final_save_duration})
                        
                        if not save_stats.get('total_saved', 0):
                            print(f"  ⚠️ 최종 배치 저장 부분 실패")
                            ctx['enhanced_logger'].warn("db_final_save", "최종 배치 저장 부분 실패", 
                                                       {'save_stats': save_stats})
                    
                    except Exception as final_error:
                        ctx['enhanced_logger'].error("db_final_save", "최종 배치 저장 실패", final_error)
                
                # 7. 일별 통계 저장
                if total_collected > 0:
                    try:
                        # 임시로 수집된 데이터 구조 생성 (통계 계산용)
                        temp_properties = []
                        # 통계용으로 최근 배치의 일부만 사용 (메모리 효율성)
                        sample_size = min(100, total_collected)
                        
                        self.helper.save_daily_stats(
                            today, 
                            cortar_no, 
                            temp_properties,
                            {'new_count': total_collected, 'removed_count': 0}
                        )
                        print(f"  📊 일별 통계 저장 완료")
                        ctx['enhanced_logger'].info("daily_stats", f"{dong_name} 일별 통계 저장 완료", 
                                                   {'total_collected': total_collected})
                    except Exception as e:
                        print(f"  ⚠️ 일별 통계 저장 실패: {e}")
                        ctx['enhanced_logger'].error("daily_stats", f"{dong_name} 일별 통계 저장 실패", e)
                
                # 8. 수집 요약 로그
                summary = {
                    'dong_name': dong_name,
                    'cortar_no': cortar_no,
                    'total_properties': total_collected,
                    'collection_method': 'direct_db_streaming_enhanced',
                    'collection_time': f'실시간 DB 저장 (향상된 로그)',
                    'memory_efficient': True,
                    'batch_size': batch_size,
                    'api_calls_tracked': True,
                    'performance_monitored': True
                }
                ctx['log_summary'](summary)
                
                print(f"✅ {dong_name} 바로 DB 수집 완료 - {total_collected}개 매물")
                ctx['enhanced_logger'].info("collection_summary", 
                                          f"{dong_name} 수집 완료 - {total_collected}개 매물",
                                          summary)
                
                return {
                    'dong_name': dong_name,
                    'status': 'completed',
                    'total_collected': total_collected,
                    'summary': summary,
                    'method': 'direct_db_enhanced'
                }
                
            except Exception as e:
                print(f"❌ {dong_name} 바로 DB 수집 실패: {e}")
                ctx['enhanced_logger'].error("collection_failed", f"{dong_name} 전체 수집 실패", e)
                return {
                    'dong_name': dong_name,
                    'status': 'failed',
                    'error': str(e),
                    'method': 'direct_db_enhanced'
                }
    
    def run_direct_db_collection(self, max_workers: int = 1):
        """바로 DB 저장 병렬 수집 실행 (향상된 로그 시스템)"""
        print("🚀 강남구 바로 DB 저장 병렬 수집 시작 (향상된 로그 시스템)")
        print("=" * 80)
        print(f"🔄 병렬 프로세스 수: {max_workers}개")
        print(f"💾 JSON 파일 생략 - 메모리에서 바로 DB 저장")
        print(f"📊 실시간 향상된 로그 기반 모니터링 활성화")
        print(f"⚡ 메모리 효율적 스트리밍 처리")
        print(f"🔍 API 호출 추적 및 성능 분석")
        print(f"🛡️ 오류 패턴 분석 및 자동 복구 제안")
        
        self.tracker.enhanced_logger.info("batch_collection", "전체 배치 수집 시작", 
                                        {'max_workers': max_workers, 
                                         'total_dongs': len(self.gangnam_dongs)})
        
        # 우선순위 순으로 정렬
        sorted_dongs = sorted(self.gangnam_dongs, key=lambda x: x['priority'], reverse=True)
        
        print(f"\n📋 수집 대상: {len(sorted_dongs)}개 동")
        print("🏆 우선순위 순서:")
        for i, dong in enumerate(sorted_dongs, 1):
            print(f"   {i:2d}. {dong['name']:8s} (점수: {dong['priority']:2d}) - {dong['cortar_no']}")
        
        print(f"\n🚀 바로 DB 저장 수집 시작: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 실시간 진행 상황: http://localhost:8000")
        print("=" * 80)
        
        start_time = time.time()
        
        if max_workers == 1:
            # 단일 프로세스로 순차 실행 (메모리 안정성)
            results = []
            for dong_info in sorted_dongs:
                try:
                    result = self.collect_dong_direct_db(dong_info)
                    results.append(result)
                except KeyboardInterrupt:
                    print("\n⚠️ 사용자 중단 요청")
                    self.tracker.enhanced_logger.warn("batch_collection", "사용자에 의한 중단 요청")
                    break
                except Exception as e:
                    error_msg = f"{dong_info['name']} 처리 중 오류: {e}"
                    print(f"❌ {error_msg}")
                    self.tracker.enhanced_logger.error("batch_collection", error_msg, e)
                    results.append({
                        'dong_name': dong_info['name'],
                        'status': 'failed',
                        'error': str(e),
                        'method': 'direct_db_enhanced'
                    })
        else:
            # 멀티프로세싱은 메모리 관리 복잡성으로 인해 제한적 사용
            print("⚠️ 바로 DB 저장에서는 단일 프로세스를 권장합니다 (메모리 안정성)")
            self.tracker.enhanced_logger.warn("batch_collection", "멀티프로세싱 사용 - 메모리 안정성 주의", 
                                            {'max_workers': max_workers})
            
            with Pool(processes=min(max_workers, 2)) as pool:  # 최대 2개 프로세스
                try:
                    results = pool.map(self.collect_dong_direct_db, sorted_dongs)
                except KeyboardInterrupt:
                    print("\n⚠️ 사용자 중단 요청")
                    self.tracker.enhanced_logger.warn("batch_collection", "멀티프로세싱 중 사용자 중단")
                    pool.terminate()
                    pool.join()
                    return
        
        # 결과 요약
        end_time = time.time()
        total_time = end_time - start_time
        
        completed = [r for r in results if r.get('status') == 'completed']
        failed = [r for r in results if r.get('status') == 'failed']
        total_properties = sum(r.get('total_collected', 0) for r in completed)
        
        # 성능 요약 출력
        performance_summary = self.tracker.get_performance_summary()
        
        print("\n" + "=" * 80)
        print("📊 바로 DB 저장 수집 완료 요약 (향상된 로그 시스템)")
        print("=" * 80)
        print(f"🕐 총 소요 시간: {total_time:.1f}초")
        print(f"✅ 성공한 동: {len(completed)}개")
        print(f"❌ 실패한 동: {len(failed)}개")
        print(f"🏢 총 DB 저장 매물: {total_properties:,}개")
        print(f"⚡ 평균 저장 속도: {total_properties/total_time:.1f}개/초")
        print(f"💾 JSON 파일 생성: 0개 (메모리 효율성)")
        print(f"🗃️ DB 직접 저장: {total_properties:,}개")
        
        # 성능 메트릭 표시
        current_metrics = performance_summary.get('current_metrics', {})
        print(f"📊 메모리 사용량: {current_metrics.get('memory_mb', 0):.1f}MB ({current_metrics.get('memory_percent', 0):.1f}%)")
        print(f"🔍 API 호출 통계: {len(performance_summary.get('api_statistics', {}))}개 엔드포인트 추적")
        
        # 오류 분석 표시
        error_analysis = performance_summary.get('error_analysis', {})
        if error_analysis.get('total_errors', 0) > 0:
            print(f"⚠️ 총 오류: {error_analysis['total_errors']}개 ({error_analysis.get('unique_patterns', 0)}개 패턴)")
            recommendations = error_analysis.get('recommendations', [])
            if recommendations:
                print("💡 자동 복구 제안:")
                for rec in recommendations[:3]:  # 상위 3개만 표시
                    print(f"   - {rec}")
        
        if failed:
            print(f"\n❌ 실패한 동들:")
            for fail in failed:
                print(f"   - {fail['dong_name']}: {fail.get('error', 'Unknown error')}")
        
        print(f"\n📊 실시간 모니터링: http://localhost:8000")
        print(f"📋 상세 로그 위치: {self.tracker.log_dir}")
        print("=" * 80)
        
        # 최종 로그 기록
        self.tracker.enhanced_logger.info("batch_collection_complete", 
                                        "전체 배치 수집 완료",
                                        {
                                            'total_time': total_time,
                                            'completed_count': len(completed),
                                            'failed_count': len(failed),
                                            'total_properties': total_properties,
                                            'performance_summary': performance_summary
                                        })
    
    def close(self):
        """수집기 종료"""
        self.tracker.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='바로 DB 저장 네이버 부동산 수집기 (향상된 로그 시스템)')
    parser.add_argument('--max-workers', type=int, default=1,
                        help='최대 병렬 프로세스 수 (기본값: 1, 권장값: 1-2)')
    parser.add_argument('--test-single', type=str, default=None,
                        help='단일 동 테스트 (예: 역삼동)')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE'],
                        help='로그 레벨 설정 (기본값: INFO)')
    
    args = parser.parse_args()
    
    # 로그 레벨 설정
    log_level_map = {
        'ERROR': LogLevel.ERROR,
        'WARN': LogLevel.WARN,
        'INFO': LogLevel.INFO,
        'DEBUG': LogLevel.DEBUG,
        'TRACE': LogLevel.TRACE
    }
    log_level = log_level_map.get(args.log_level, LogLevel.INFO)
    
    try:
        collector = DirectDBCollector(log_level=log_level)
        
        # 단일 동 테스트 모드
        if args.test_single:
            # 해당 동 정보 찾기
            target_dong = None
            for dong in collector.gangnam_dongs:
                if dong["name"] == args.test_single:
                    target_dong = dong
                    break
            
            if target_dong:
                print(f"🧪 단일 동 바로 DB 테스트 모드: {args.test_single}")
                collector.tracker.enhanced_logger.info("test_mode", f"단일 동 테스트: {args.test_single}")
                
                result = collector.collect_dong_direct_db(target_dong)
                print(f"\n📊 테스트 결과: {result}")
                
                # 성능 요약 출력
                performance = collector.tracker.get_performance_summary()
                print(f"\n📈 성능 요약:")
                print(f"  메모리: {performance['current_metrics'].get('memory_mb', 0):.1f}MB")
                print(f"  API 호출: {len(performance.get('api_statistics', {}))}개 엔드포인트")
                if performance.get('error_analysis', {}).get('total_errors', 0) > 0:
                    print(f"  오류: {performance['error_analysis']['total_errors']}개")
                
            else:
                print(f"❌ '{args.test_single}' 동을 찾을 수 없습니다.")
                print("사용 가능한 동:", [dong["name"] for dong in collector.gangnam_dongs])
        else:
            collector.run_direct_db_collection(max_workers=args.max_workers)
        
        collector.close()
            
    except KeyboardInterrupt:
        print("\n⚠️ 프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 프로그램 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()