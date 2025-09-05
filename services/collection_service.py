#!/usr/bin/env python3
"""
매물 수집 서비스 - 전체 수집 프로세스 조율
"""

from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
from collectors.naver_api_client import NaverAPIClient
from parsers.article_parser import ArticleParser
from database.optimized_repository import OptimizedPropertyRepository
from services.address_service import AddressService
from config.settings import settings

class CollectionService:
    def __init__(self):
        self.api_client = NaverAPIClient()
        self.parser = ArticleParser()
        self.repository = OptimizedPropertyRepository()
        
        try:
            self.address_service = AddressService()
            self.address_enabled = True
        except ValueError as e:
            print(f"⚠️ 주소 서비스 비활성화: {e}")
            self.address_enabled = False
        
        self.collection_stats = {
            'total_processed': 0,
            'successful_collections': 0,
            'parsing_failures': 0,
            'save_failures': 0,
            'start_time': None,
            'estimated_completion': None
        }
    
    def collect_single_article(self, article_no: str, quiet: bool = False) -> bool:
        self.collection_stats['total_processed'] += 1
        if not quiet:
            print(f"🔍 매물 {article_no} 상세정보 수집 중...")
        
        try:
            raw_data = self.api_client.get_article_detail(article_no)
            if not raw_data:
                print(f"❌ API 호출 실패: {article_no}")
                return False
            
            if not quiet:
                print(f"📝 매물 {article_no} 데이터 파싱 중...")
            parsed_data = self.parser.parse_article_detail(raw_data, article_no)
            if not parsed_data:
                if not quiet:
                    print(f"❌ 파싱 실패: {article_no}")
                self.collection_stats['parsing_failures'] += 1
                return False
            
            if self.address_enabled and 'articleDetail' in parsed_data.get('sections', {}):
                self._enrich_with_address_data(parsed_data)
            
            # 매물 검증 및 is_active 설정
            self._validate_and_set_active_status(parsed_data, quiet)
            
            if not quiet:
                print(f"💾 매물 {article_no} 데이터베이스 저장 중...")
            success = self.repository.save_property(parsed_data)
            if success:
                self.collection_stats['successful_collections'] += 1
                if not quiet:
                    print(f"✅ 매물 {article_no} 저장 완료!")
                return True
            else:
                self.collection_stats['save_failures'] += 1
                if not quiet:
                    print(f"❌ 데이터베이스 저장 실패: {article_no}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing article {article_no}: {e}")
            return False
    
    def collect_area_articles(self, cortar_no: str, max_pages: int = None) -> List[str]:
        collected_articles = []
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
                
            print(f"🔍 수집 중: 지역 {cortar_no}, 페이지 {page}")
            
            response = self.api_client.get_area_articles(cortar_no, page)  # 사무실만 수집 (상가 제외)
            if not response or 'articleList' not in response:
                print(f"❌ No more articles found for area {cortar_no}")
                break
            
            articles = response['articleList']
            if not articles:
                print(f"✅ No more articles on page {page}")
                break
            
            page_articles = []
            for article in articles:
                article_no = article.get('articleNo')
                if article_no:
                    page_articles.append(str(article_no))
            
            if not page_articles:
                break
            
            collected_articles.extend(page_articles)
            print(f"📄 페이지 {page}: {len(page_articles)}개 매물 발견")
            
            page += 1
        
        print(f"📊 지역 {cortar_no} 총 {len(collected_articles)}개 매물 발견")
        return collected_articles
    
    def collect_and_save_area(self, cortar_no: str, max_pages: int = None, max_articles: int = None) -> Dict[str, Any]:
        print(f"🚀 지역 {cortar_no} 수집 시작")
        
        successful_collections = 0
        total_processed = 0
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
                
            print(f"🔍 수집 중: 지역 {cortar_no}, 페이지 {page}")
            
            response = self.api_client.get_area_articles(cortar_no, page)  # 사무실만 수집 (상가 제외)
            if not response or 'articleList' not in response:
                print(f"❌ No more articles found for area {cortar_no}")
                break
            
            articles = response['articleList']
            if not articles:
                print(f"✅ No more articles on page {page}")
                break
            
            page_articles = []
            for article in articles:
                article_no = article.get('articleNo')
                if article_no:
                    page_articles.append(str(article_no))
            
            if not page_articles:
                break
            
            print(f"📄 페이지 {page}: {len(page_articles)}개 매물 발견")
            
            # 병렬 처리로 상세정보 수집 및 저장
            articles_to_process = page_articles[:max_articles - total_processed] if max_articles else page_articles
            
            if not self.collection_stats['start_time']:
                self.collection_stats['start_time'] = time.time()
            
            page_successful = self._collect_articles_parallel(articles_to_process, total_processed + 1, max_articles)
            
            successful_collections += page_successful
            total_processed += len(articles_to_process)
            
            # 진행률 및 ETA 출력
            self._print_progress_with_eta(total_processed, successful_collections, max_articles)
            
            if max_articles and total_processed >= max_articles:
                break
                
            page += 1
        
        return {
            'area_code': cortar_no,
            'total_found': total_processed,
            'successful_collections': successful_collections,
            'success_rate': f"{(successful_collections / total_processed * 100):.2f}%" if total_processed else "0%",
            'api_stats': self.api_client.get_request_stats(),
            'parsing_stats': self.parser.get_parsing_stats(),
            'save_stats': self.repository.get_save_stats()
        }
    
    def _enrich_with_address_data(self, parsed_data: Dict):
        article_detail = parsed_data.get('sections', {}).get('articleDetail', {})
        latitude = article_detail.get('latitude')
        longitude = article_detail.get('longitude')
        
        if latitude and longitude:
            try:
                address_info = self.address_service.convert_coordinates_to_address(latitude, longitude)
                if address_info:
                    if 'address_info' not in article_detail:
                        article_detail['address_info'] = {}
                    article_detail['address_info'].update(address_info)
                    print(f"✅ 주소 정보 추가됨: {address_info.get('primary_address', 'N/A')}")
            except Exception as e:
                print(f"⚠️ 주소 변환 실패: {e}")
    
    def _validate_and_set_active_status(self, parsed_data: Dict, quiet: bool = False):
        """매물 데이터 검증 후 is_active 상태 설정"""
        if not settings.validation_rules['validation_enabled']:
            if not quiet:
                print("🔧 매물 검증 비활성화됨")
            return
        
        is_active = True
        rejection_reasons = []
        
        # articleDetail, articlePrice 섹션 가져오기
        sections = parsed_data.get('sections', {})
        article_detail = sections.get('articleDetail', {})
        article_price = sections.get('articlePrice', {})
        
        # 1. 거래유형 검증 (전세/매매/단기임대 제외)
        trade_type = article_detail.get('tradeTypeCd')
        if trade_type in settings.validation_rules['excluded_trade_types']:
            is_active = False
            rejection_reasons.append(f"제외된 거래유형: {trade_type}")
        
        # 2. 보증금 검증
        deposit = article_price.get('dealOrWarrantPrc', 0)
        if isinstance(deposit, str):
            deposit = int(deposit) if deposit.isdigit() else 0
        
        deposit_limits = settings.validation_rules['deposit_limits']
        if deposit < deposit_limits['min'] or deposit > deposit_limits['max']:
            is_active = False
            rejection_reasons.append(f"보증금 범위 벗어남: {deposit:,}원")
        
        # 3. 월세 검증
        rent = article_price.get('rentPrc', 0)
        if isinstance(rent, str):
            rent = int(rent) if rent.isdigit() else 0
        
        rent_limits = settings.validation_rules['monthly_rent_limits']
        if rent < rent_limits['min'] or rent > rent_limits['max']:
            is_active = False
            rejection_reasons.append(f"월세 범위 벗어남: {rent:,}원")
        
        # 4. 엘리베이터 검증
        if settings.validation_rules['elevator_required']:
            elevator_count = article_detail.get('elevatorNum')
            if elevator_count is None or elevator_count == 0:
                is_active = False
                rejection_reasons.append("엘리베이터 없음")
        
        # is_active 설정
        if 'metadata' not in parsed_data:
            parsed_data['metadata'] = {}
        parsed_data['metadata']['is_active'] = is_active
        
        # 로그 출력
        if not quiet:
            if not is_active:
                print(f"⚠️ 매물 비활성화: {', '.join(rejection_reasons)}")
            else:
                print(f"✅ 매물 검증 통과")
    
    def _collect_articles_parallel(self, article_nos: List[str], start_idx: int, max_articles: Optional[int]) -> int:
        """병렬로 매물들을 수집하여 성공한 개수 반환"""
        max_workers = settings.collection_settings['parallel_workers']
        successful_count = 0
        
        # 연결 풀 과부하 방지를 위한 배치 처리
        batch_size = max_workers * 2  # 워커 수의 2배씩 배치 처리
        
        for i in range(0, len(article_nos), batch_size):
            batch_articles = article_nos[i:i + batch_size]
            batch_successful = self._process_batch(batch_articles, max_workers)
            successful_count += batch_successful
            
            # 배치 간 짧은 휴식 (연결 풀 안정화)
            if i + batch_size < len(article_nos):
                time.sleep(1)
        
        return successful_count
    
    def _process_batch(self, article_nos: List[str], max_workers: int) -> int:
        """단일 배치를 병렬 처리"""
        successful_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 병렬 작업 제출
            future_to_article = {
                executor.submit(self.collect_single_article, article_no, quiet=True): article_no 
                for article_no in article_nos
            }
            
            # 완료된 작업들 처리
            for future in as_completed(future_to_article):
                article_no = future_to_article[future]
                try:
                    success = future.result()
                    if success:
                        successful_count += 1
                        print(f"✅ {article_no} 완료")
                    else:
                        print(f"❌ {article_no} 실패")
                except Exception as e:
                    # 연결 풀 에러 특별 처리
                    if "Resource temporarily unavailable" in str(e) or "Errno 35" in str(e):
                        print(f"⚠️ {article_no} 연결풀 에러: 재시도 권장")
                    else:
                        print(f"❌ {article_no} 예외: {e}")
        
        return successful_count
    
    def _print_progress_with_eta(self, processed: int, successful: int, total: Optional[int]):
        """진행률과 예상 완료 시간 출력"""
        if not self.collection_stats['start_time']:
            return
        
        elapsed_time = time.time() - self.collection_stats['start_time']
        
        print(f"\n📈 진행 현황:")
        print(f"   처리완료: {processed}개")
        print(f"   성공: {successful}개")
        print(f"   성공률: {(successful/processed*100):.1f}%" if processed > 0 else "0%")
        print(f"   경과시간: {elapsed_time/60:.1f}분")
        
        # ETA 계산
        if total and processed > 0:
            remaining = total - processed
            avg_time_per_item = elapsed_time / processed
            eta_seconds = remaining * avg_time_per_item
            eta_minutes = eta_seconds / 60
            
            print(f"   남은 매물: {remaining}개")
            print(f"   예상 완료: {eta_minutes:.1f}분 후")
            
            # 완료 예정 시각
            completion_time = datetime.fromtimestamp(time.time() + eta_seconds)
            print(f"   완료 예정: {completion_time.strftime('%H:%M')}")
            
        print("=" * 50)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        stats = {
            'collection_stats': self.collection_stats,
            'api_stats': self.api_client.get_request_stats(),
            'parsing_stats': self.parser.get_parsing_stats(),
            'save_stats': self.repository.get_save_stats()
        }
        
        if self.address_enabled:
            stats['address_stats'] = self.address_service.get_usage_stats()
        
        return stats
    
    def print_final_summary(self):
        stats = self.get_comprehensive_stats()
        
        print("\n" + "="*50)
        print("📊 최종 수집 결과")
        print("="*50)
        
        collection = stats['collection_stats']
        print(f"총 처리: {collection['total_processed']}개")
        print(f"성공: {collection['successful_collections']}개")
        print(f"파싱 실패: {collection['parsing_failures']}개")
        print(f"저장 실패: {collection['save_failures']}개")
        
        if collection['total_processed'] > 0:
            success_rate = (collection['successful_collections'] / collection['total_processed']) * 100
            print(f"성공률: {success_rate:.2f}%")
        
        api = stats['api_stats']
        print(f"\nAPI 호출: {api['total_requests']}회")
        
        if self.address_enabled and 'address_stats' in stats:
            addr = stats['address_stats']
            print(f"\n주소 변환: {addr['total_requests']}회")
            print(f"캐시 히트: {addr['cache_hits']}개")
        
        print("="*50)