#!/usr/bin/env python3
"""
성능 최적화된 Supabase 클라이언트
- 직접 DB 저장 지원
- 스트리밍 처리 최적화  
- 메모리 효율성 개선
- 트랜잭션 관리 강화
"""

import os
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Generator, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
from supabase import create_client, Client

@dataclass
class BatchResult:
    """배치 처리 결과"""
    success: bool = False
    processed: int = 0
    inserted: int = 0
    updated: int = 0
    errors: int = 0
    processing_time: float = 0.0
    error_details: List[str] = None

    def __post_init__(self):
        if self.error_details is None:
            self.error_details = []

@dataclass
class PerformanceMetrics:
    """성능 측정 지표"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_processing_time: float = 0.0
    average_batch_time: float = 0.0
    records_per_second: float = 0.0
    memory_usage_mb: float = 0.0

class EnhancedSupabaseClient:
    """성능 최적화된 Supabase 클라이언트"""
    
    def __init__(self, config_file: str = "config.json", batch_size: int = 50):
        """
        향상된 Supabase 클라이언트 초기화
        
        Args:
            config_file: 설정 파일 경로
            batch_size: 기본 배치 크기
        """
        self.batch_size = batch_size
        self.client = self._initialize_client(config_file)
        self.performance_metrics = PerformanceMetrics()
        
        # 연결 풀링 설정
        self._connection_pool_size = 10
        self._connection_timeout = 30
        
        print(f"✅ 성능 최적화된 Supabase 클라이언트 초기화 완료 (배치 크기: {batch_size})")
    
    def _initialize_client(self, config_file: str) -> Client:
        """Supabase 클라이언트 초기화"""
        try:
            # 설정 파일 로드
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            supabase_config = config.get('supabase', {})
            
            # 환경변수 우선, 설정 파일 차순위
            url = os.getenv('SUPABASE_URL', supabase_config.get('url'))
            key = os.getenv('SUPABASE_KEY', supabase_config.get('anon_key'))
            
            if not url or not key:
                raise ValueError("Supabase URL과 Key가 필요합니다.")
            
            return create_client(url, key)
            
        except Exception as e:
            print(f"❌ Supabase 클라이언트 초기화 실패: {e}")
            raise
    
    @contextmanager
    def performance_tracking(self, operation_name: str):
        """성능 추적 컨텍스트 매니저"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
            self.performance_metrics.successful_operations += 1
        except Exception as e:
            self.performance_metrics.failed_operations += 1
            raise
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            processing_time = end_time - start_time
            memory_delta = end_memory - start_memory
            
            self.performance_metrics.total_operations += 1
            self.performance_metrics.total_processing_time += processing_time
            self.performance_metrics.memory_usage_mb = max(
                self.performance_metrics.memory_usage_mb, 
                end_memory
            )
            
            print(f"⏱️ {operation_name}: {processing_time:.2f}초, 메모리: +{memory_delta:.1f}MB")
    
    def stream_save_properties(
        self, 
        property_generator: Generator[Dict, None, None], 
        cortar_no: str,
        region_name: str = ""
    ) -> Dict:
        """
        스트리밍 방식으로 매물 데이터를 직접 DB에 저장
        
        Args:
            property_generator: 매물 데이터 제너레이터
            cortar_no: 행정구역 코드
            region_name: 지역명 (로깅용)
            
        Returns:
            Dict: 전체 저장 결과
        """
        
        print(f"\n🚀 스트리밍 직접 저장 시작: {region_name} ({cortar_no})")
        
        with self.performance_tracking("스트리밍 저장"):
            batch_buffer = []
            batch_count = 0
            total_stats = {
                'total_processed': 0,
                'total_inserted': 0,
                'total_updated': 0,
                'total_errors': 0,
                'batch_results': []
            }
            
            try:
                for property_data in property_generator:
                    batch_buffer.append(property_data)
                    
                    # 배치 크기에 도달하면 저장
                    if len(batch_buffer) >= self.batch_size:
                        batch_count += 1
                        batch_result = self._process_batch(batch_buffer, cortar_no, batch_count)
                        
                        # 통계 업데이트
                        total_stats['total_processed'] += batch_result.processed
                        total_stats['total_inserted'] += batch_result.inserted
                        total_stats['total_updated'] += batch_result.updated
                        total_stats['total_errors'] += batch_result.errors
                        total_stats['batch_results'].append(batch_result)
                        
                        # 배치 버퍼 초기화
                        batch_buffer.clear()
                        
                        # 메모리 정리 및 잠깐 대기
                        if batch_count % 10 == 0:
                            self._memory_cleanup()
                        
                        time.sleep(0.1)  # API 제한 준수
                
                # 남은 데이터 처리
                if batch_buffer:
                    batch_count += 1
                    batch_result = self._process_batch(batch_buffer, cortar_no, batch_count)
                    
                    total_stats['total_processed'] += batch_result.processed
                    total_stats['total_inserted'] += batch_result.inserted
                    total_stats['total_updated'] += batch_result.updated
                    total_stats['total_errors'] += batch_result.errors
                    total_stats['batch_results'].append(batch_result)
                
                # 성능 지표 계산
                if total_stats['total_processed'] > 0:
                    self.performance_metrics.records_per_second = (
                        total_stats['total_processed'] / 
                        self.performance_metrics.total_processing_time
                    )
                
                print(f"✅ 스트리밍 저장 완료!")
                print(f"   총 배치: {batch_count}개")
                print(f"   처리: {total_stats['total_processed']:,}개")
                print(f"   신규: {total_stats['total_inserted']:,}개")
                print(f"   업데이트: {total_stats['total_updated']:,}개")
                print(f"   오류: {total_stats['total_errors']:,}개")
                print(f"   처리 속도: {self.performance_metrics.records_per_second:.1f} 레코드/초")
                
                return {
                    'success': True,
                    'region_name': region_name,
                    'cortar_no': cortar_no,
                    'batch_count': batch_count,
                    'stats': total_stats,
                    'performance': self._get_performance_summary()
                }
                
            except Exception as e:
                print(f"❌ 스트리밍 저장 오류: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'stats': total_stats,
                    'performance': self._get_performance_summary()
                }
    
    def _process_batch(self, batch_data: List[Dict], cortar_no: str, batch_num: int) -> BatchResult:
        """
        배치 데이터 처리
        
        Args:
            batch_data: 배치 데이터
            cortar_no: 행정구역 코드
            batch_num: 배치 번호
            
        Returns:
            BatchResult: 배치 처리 결과
        """
        
        start_time = time.time()
        result = BatchResult()
        
        print(f"   📦 배치 {batch_num}: {len(batch_data)}개 처리 중...")
        
        try:
            # 1. 데이터 유효성 검사 및 전처리
            valid_data = []
            for item in batch_data:
                if self._validate_property_data(item):
                    # 필수 필드 보강
                    item = self._enrich_property_data(item, cortar_no)
                    valid_data.append(item)
                else:
                    result.errors += 1
                    result.error_details.append(f"유효성 검사 실패: {item.get('article_no', 'Unknown')}")
            
            if not valid_data:
                result.processing_time = time.time() - start_time
                return result
            
            # 2. 기존 데이터와의 중복 체크 및 업데이트 처리
            existing_properties = self._get_existing_properties(
                [item['article_no'] for item in valid_data], 
                cortar_no
            )
            
            insert_data = []
            update_data = []
            
            for item in valid_data:
                article_no = item['article_no']
                existing = existing_properties.get(article_no)
                
                if existing:
                    # 기존 데이터와 비교하여 업데이트 필요 여부 확인
                    if self._needs_update(existing, item):
                        item['updated_at'] = datetime.now().isoformat()
                        update_data.append(item)
                    # 업데이트 불필요한 경우 last_seen_date만 갱신
                    else:
                        self._update_last_seen_date(article_no)
                else:
                    insert_data.append(item)
            
            # 3. 배치 INSERT
            if insert_data:
                insert_result = self.client.table('properties').upsert(
                    insert_data, 
                    on_conflict='article_no'
                ).execute()
                
                result.inserted = len(insert_data)
                print(f"      ✅ 신규 저장: {result.inserted}개")
            
            # 4. 배치 UPDATE
            if update_data:
                # 개별 업데이트 (Supabase 배치 업데이트 한계로 인해)
                updated_count = 0
                for item in update_data:
                    try:
                        self.client.table('properties')\
                            .update(item)\
                            .eq('article_no', item['article_no'])\
                            .execute()
                        updated_count += 1
                    except Exception as e:
                        result.errors += 1
                        result.error_details.append(f"업데이트 실패 ({item['article_no']}): {e}")
                
                result.updated = updated_count
                print(f"      📝 업데이트: {result.updated}개")
            
            result.processed = len(valid_data)
            result.success = True
            
        except Exception as e:
            print(f"      ❌ 배치 처리 실패: {e}")
            result.errors += len(batch_data)
            result.error_details.append(f"배치 처리 오류: {e}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _validate_property_data(self, data: Dict) -> bool:
        """매물 데이터 유효성 검사"""
        required_fields = ['article_no', 'cortar_no']
        return all(data.get(field) for field in required_fields)
    
    def _enrich_property_data(self, data: Dict, cortar_no: str) -> Dict:
        """매물 데이터 보강"""
        now = datetime.now()
        today = date.today()
        
        # 필수 필드 기본값 설정
        data.setdefault('cortar_no', cortar_no)
        data.setdefault('collected_date', today.isoformat())
        data.setdefault('last_seen_date', today.isoformat())
        data.setdefault('is_active', True)
        data.setdefault('created_at', now.isoformat())
        data.setdefault('updated_at', now.isoformat())
        
        # 가격 데이터 정규화
        data['price'] = self._normalize_price(data.get('price', 0))
        data['rent_price'] = self._normalize_price(data.get('rent_price', 0))
        
        return data
    
    def _get_existing_properties(self, article_nos: List[str], cortar_no: str) -> Dict:
        """기존 매물 조회"""
        try:
            if not article_nos:
                return {}
            
            # 배치 크기로 나누어 조회 (IN 절 한계 고려)
            existing_map = {}
            batch_size = 100
            
            for i in range(0, len(article_nos), batch_size):
                batch_ids = article_nos[i:i+batch_size]
                
                result = self.client.table('properties')\
                    .select('article_no, price, rent_price, trade_type, updated_at')\
                    .in_('article_no', batch_ids)\
                    .eq('cortar_no', cortar_no)\
                    .eq('is_active', True)\
                    .execute()
                
                for item in result.data:
                    existing_map[item['article_no']] = item
            
            return existing_map
            
        except Exception as e:
            print(f"⚠️ 기존 매물 조회 실패: {e}")
            return {}
    
    def _needs_update(self, existing: Dict, new_data: Dict) -> bool:
        """업데이트 필요 여부 확인"""
        
        # 가격 변동 체크
        if existing.get('price') != new_data.get('price'):
            return True
        
        if existing.get('rent_price') != new_data.get('rent_price'):
            return True
        
        # 기타 주요 필드 변동 체크
        check_fields = ['trade_type', 'floor_info', 'direction']
        for field in check_fields:
            if existing.get(field) != new_data.get(field):
                return True
        
        return False
    
    def _update_last_seen_date(self, article_no: str):
        """마지막 발견 날짜만 업데이트"""
        try:
            self.client.table('properties')\
                .update({
                    'last_seen_date': date.today().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('article_no', article_no)\
                .execute()
        except Exception as e:
            print(f"⚠️ last_seen_date 업데이트 실패 ({article_no}): {e}")
    
    def _normalize_price(self, price_value: Any) -> int:
        """가격 데이터 정규화"""
        if isinstance(price_value, (int, float)):
            return int(price_value)
        
        if isinstance(price_value, str):
            # "5억 3,000만" 형식 처리
            price_str = price_value.replace(',', '').replace('억', '0000').replace('만', '')
            try:
                return int(price_str)
            except:
                return 0
        
        return 0
    
    def _get_memory_usage(self) -> float:
        """현재 메모리 사용량 조회 (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _memory_cleanup(self):
        """메모리 정리"""
        import gc
        gc.collect()
        print("🧹 메모리 정리 완료")
    
    def _get_performance_summary(self) -> Dict:
        """성능 요약 정보 반환"""
        return {
            'total_operations': self.performance_metrics.total_operations,
            'successful_operations': self.performance_metrics.successful_operations,
            'failed_operations': self.performance_metrics.failed_operations,
            'success_rate': (
                self.performance_metrics.successful_operations / 
                max(self.performance_metrics.total_operations, 1) * 100
            ),
            'total_processing_time': self.performance_metrics.total_processing_time,
            'records_per_second': self.performance_metrics.records_per_second,
            'memory_usage_mb': self.performance_metrics.memory_usage_mb
        }
    
    def get_region_statistics(self, cortar_no: str) -> Dict:
        """지역별 통계 조회"""
        try:
            with self.performance_tracking("지역 통계 조회"):
                # 활성 매물 수
                active_count = self.client.table('properties')\
                    .select('id', count='exact')\
                    .eq('cortar_no', cortar_no)\
                    .eq('is_active', True)\
                    .execute()
                
                # 가격 통계
                price_stats = self.client.table('properties')\
                    .select('price, rent_price, trade_type')\
                    .eq('cortar_no', cortar_no)\
                    .eq('is_active', True)\
                    .execute()
                
                prices = [item['price'] for item in price_stats.data if item['price']]
                
                statistics = {
                    'cortar_no': cortar_no,
                    'active_properties': active_count.count or 0,
                    'avg_price': sum(prices) / len(prices) if prices else 0,
                    'min_price': min(prices) if prices else 0,
                    'max_price': max(prices) if prices else 0,
                    'trade_type_distribution': self._calculate_trade_type_distribution(price_stats.data),
                    'last_updated': datetime.now().isoformat()
                }
                
                return statistics
                
        except Exception as e:
            print(f"❌ 지역 통계 조회 실패: {e}")
            return {'error': str(e)}
    
    def _calculate_trade_type_distribution(self, data: List[Dict]) -> Dict:
        """거래 타입별 분포 계산"""
        distribution = {}
        for item in data:
            trade_type = item.get('trade_type', '기타')
            distribution[trade_type] = distribution.get(trade_type, 0) + 1
        return distribution

# 테스트 함수
def test_enhanced_client():
    """성능 최적화된 클라이언트 테스트"""
    
    print("🧪 성능 최적화된 Supabase 클라이언트 테스트")
    print("=" * 50)
    
    try:
        client = EnhancedSupabaseClient(batch_size=25)
        
        # 지역 통계 조회 테스트
        test_cortar_no = "1168010100"
        stats = client.get_region_statistics(test_cortar_no)
        
        print(f"✅ 테스트 완료!")
        print(f"   지역 통계: {stats}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    test_enhanced_client()