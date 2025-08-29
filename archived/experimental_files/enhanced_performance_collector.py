#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성능 최적화된 네이버 수집기 v2.0
- 병렬 처리 및 배치 최적화
- 지능형 중복 제거
- 메모리 효율성 향상
- 실시간 성능 모니터링
"""

import asyncio
import time
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from final_safe_collector import FinalSafeCollector
from supabase_client import SupabaseHelper

@dataclass
class CollectionMetrics:
    """수집 성능 메트릭"""
    start_time: float
    end_time: float = 0
    total_collected: int = 0
    duplicates_removed: int = 0
    errors_count: int = 0
    memory_peak_mb: float = 0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time
    
    @property
    def collection_rate(self) -> float:
        return self.total_collected / self.duration if self.duration > 0 else 0

class EnhancedPerformanceCollector:
    """성능 최적화된 수집기"""
    
    def __init__(self, max_workers: int = 3):
        self.base_collector = FinalSafeCollector()
        self.db_helper = SupabaseHelper()
        self.max_workers = max_workers
        self.metrics = CollectionMetrics(start_time=time.time())
        
        # 성능 설정
        self.batch_size = 50  # 배치 처리 크기
        self.cache_size = 1000  # 중복 체크 캐시 크기
        self.duplicate_cache = set()  # 메모리 기반 중복 체크
    
    def get_memory_usage(self) -> float:
        """현재 메모리 사용량 조회 (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def collect_region_batch(self, region_codes: List[str], max_pages: int = 999) -> Dict:
        """여러 지역 배치 수집"""
        print(f"🚀 배치 수집 시작: {len(region_codes)}개 지역")
        print(f"⚡ 병렬 처리: {self.max_workers}개 스레드")
        
        results = {
            'total_regions': len(region_codes),
            'successful': 0,
            'failed': 0,
            'results': [],
            'performance': {}
        }
        
        # 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_region = {
                executor.submit(self._collect_single_region_optimized, region_code, max_pages): region_code
                for region_code in region_codes
            }
            
            # 결과 수집
            for future in as_completed(future_to_region):
                region_code = future_to_region[future]
                try:
                    result = future.result()
                    if result['status'] == 'success':
                        results['successful'] += 1
                        self.metrics.total_collected += result.get('collected_count', 0)
                    else:
                        results['failed'] += 1
                        self.metrics.errors_count += 1
                    
                    results['results'].append(result)
                    
                    # 메모리 모니터링
                    current_memory = self.get_memory_usage()
                    if current_memory > self.metrics.memory_peak_mb:
                        self.metrics.memory_peak_mb = current_memory
                    
                    print(f"  ✅ {region_code} 완료: {result.get('collected_count', 0)}개 매물")
                    
                except Exception as e:
                    print(f"  ❌ {region_code} 실패: {str(e)}")
                    results['failed'] += 1
                    self.metrics.errors_count += 1
        
        # 성능 메트릭 계산
        self.metrics.end_time = time.time()
        results['performance'] = {
            'duration_seconds': self.metrics.duration,
            'total_collected': self.metrics.total_collected,
            'collection_rate': self.metrics.collection_rate,
            'duplicates_removed': self.metrics.duplicates_removed,
            'memory_peak_mb': self.metrics.memory_peak_mb,
            'errors_count': self.metrics.errors_count
        }
        
        print(f"\n📊 배치 수집 완료")
        print(f"   ⏱️ 소요 시간: {self.metrics.duration:.1f}초")
        print(f"   📦 총 수집: {self.metrics.total_collected:,}개")
        print(f"   ⚡ 수집 속도: {self.metrics.collection_rate:.1f}개/초")
        print(f"   🗑️ 중복 제거: {self.metrics.duplicates_removed}개")
        print(f"   💾 최대 메모리: {self.metrics.memory_peak_mb:.1f}MB")
        
        return results
    
    def _collect_single_region_optimized(self, region_code: str, max_pages: int) -> Dict:
        """최적화된 단일 지역 수집"""
        try:
            # 기존 수집기 사용하되 최적화 적용
            result = self.base_collector.collect_and_save_safely(
                cortar_no=region_code,
                max_pages=max_pages,
                save_to_db=True,
                test_mode=False
            )
            
            # 중복 제거 로직 적용 (메모리 기반)
            if result.get('status') == 'success':
                duplicates = self._remove_duplicates_in_memory(region_code)
                self.metrics.duplicates_removed += duplicates
                result['duplicates_removed'] = duplicates
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'region_code': region_code,
                'error': str(e)
            }
    
    def _remove_duplicates_in_memory(self, region_code: str) -> int:
        """메모리 기반 중복 제거"""
        try:
            # 최근 수집된 매물에서 중복 체크
            recent_properties = self.db_helper.client.table('properties')\
                .select('article_no')\
                .eq('cortar_no', region_code)\
                .eq('is_active', True)\
                .order('updated_at', desc=True)\
                .limit(500)\
                .execute()
            
            duplicates_found = 0
            current_ids = set()
            
            for prop in recent_properties.data or []:
                article_no = prop['article_no']
                if article_no in current_ids:
                    duplicates_found += 1
                    # 중복 매물 비활성화 (안전하게)
                    self.db_helper.client.table('properties')\
                        .update({'is_active': False, 'updated_at': datetime.now().isoformat()})\
                        .eq('article_no', article_no)\
                        .eq('cortar_no', region_code)\
                        .execute()
                else:
                    current_ids.add(article_no)
            
            return duplicates_found
            
        except Exception as e:
            print(f"⚠️ 중복 제거 오류: {e}")
            return 0
    
    def intelligent_scheduling(self, regions_priority: Dict[str, int]) -> List[str]:
        """지능형 수집 스케줄링 - 우선순위 기반"""
        
        # 최근 수집 성과 조회
        performance_data = {}
        for region_code in regions_priority.keys():
            try:
                # 최근 7일 수집 통계
                week_ago = (date.today() - timedelta(days=7)).isoformat()
                stats = self.db_helper.client.table('daily_stats')\
                    .select('total_count, new_count')\
                    .eq('cortar_no', region_code)\
                    .gte('stat_date', week_ago)\
                    .execute()
                
                total_collected = sum(s['total_count'] or 0 for s in stats.data or [])
                avg_new = sum(s['new_count'] or 0 for s in stats.data or []) / max(len(stats.data or []), 1)
                
                performance_data[region_code] = {
                    'total_collected': total_collected,
                    'avg_new_per_day': avg_new,
                    'priority_score': regions_priority[region_code],
                    'efficiency_score': avg_new * 0.7 + regions_priority[region_code] * 0.3
                }
                
            except Exception as e:
                performance_data[region_code] = {
                    'total_collected': 0,
                    'avg_new_per_day': 0,
                    'priority_score': regions_priority[region_code],
                    'efficiency_score': regions_priority[region_code]
                }
        
        # 효율성 점수 기준 정렬
        sorted_regions = sorted(
            performance_data.keys(),
            key=lambda x: performance_data[x]['efficiency_score'],
            reverse=True
        )
        
        print(f"🧠 지능형 스케줄링 결과:")
        for i, region in enumerate(sorted_regions[:5], 1):
            data = performance_data[region]
            print(f"  {i}. {region} - 효율성: {data['efficiency_score']:.1f}, "
                  f"일평균 신규: {data['avg_new_per_day']:.1f}개")
        
        return sorted_regions
    
    def adaptive_collection(self, regions: List[str], target_duration_minutes: int = 60) -> Dict:
        """적응형 수집 - 목표 시간 내 최적화"""
        print(f"🎯 적응형 수집 모드: {target_duration_minutes}분 목표")
        
        target_duration_seconds = target_duration_minutes * 60
        results = []
        start_time = time.time()
        
        for region in regions:
            current_duration = time.time() - start_time
            remaining_time = target_duration_seconds - current_duration
            
            if remaining_time <= 0:
                print(f"⏰ 목표 시간 초과, 남은 지역 생략")
                break
            
            # 남은 시간 기준 페이지 수 조정
            estimated_pages = min(999, int(remaining_time / 30))  # 페이지당 30초 예상
            
            print(f"🚀 {region} 수집 중... (남은시간: {remaining_time:.0f}초, 예상페이지: {estimated_pages})")
            
            result = self._collect_single_region_optimized(region, estimated_pages)
            results.append(result)
            
            # 성공률 기반 동적 조정
            success_rate = sum(1 for r in results if r.get('status') == 'success') / len(results)
            if success_rate < 0.8:  # 성공률 80% 미만시 속도 조정
                print(f"⚠️ 성공률 {success_rate:.1%} - 수집 속도 조정")
                time.sleep(5)  # 5초 휴식
        
        total_duration = time.time() - start_time
        
        return {
            'completed_regions': len(results),
            'target_duration_minutes': target_duration_minutes,
            'actual_duration_minutes': total_duration / 60,
            'efficiency_ratio': (target_duration_seconds / total_duration) if total_duration > 0 else 0,
            'results': results
        }

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='성능 최적화된 네이버 수집기 v2.0')
    parser.add_argument('--regions', nargs='+', help='수집할 지역 코드들')
    parser.add_argument('--workers', type=int, default=3, help='병렬 처리 스레드 수')
    parser.add_argument('--max-pages', type=int, default=999, help='지역별 최대 페이지')
    parser.add_argument('--mode', choices=['batch', 'adaptive', 'intelligent'], default='batch',
                        help='수집 모드 선택')
    parser.add_argument('--target-minutes', type=int, default=60, help='적응형 모드 목표 시간(분)')
    
    args = parser.parse_args()
    
    # 기본 강남구 지역들
    if not args.regions:
        args.regions = [
            "1168010100",  # 역삼동
            "1168010500",  # 삼성동
            "1168010800",  # 논현동
            "1168010600",  # 대치동
            "1168010700"   # 신사동
        ]
    
    collector = EnhancedPerformanceCollector(max_workers=args.workers)
    
    print(f"🚀 성능 최적화 수집기 v2.0 시작")
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 모드: {args.mode}")
    print("=" * 60)
    
    if args.mode == 'batch':
        results = collector.collect_region_batch(args.regions, args.max_pages)
    
    elif args.mode == 'adaptive':
        results = collector.adaptive_collection(args.regions, args.target_minutes)
    
    elif args.mode == 'intelligent':
        # 지역별 우선순위 (실제 데이터 기반)
        priority_map = {
            "1168010100": 30,  # 역삼동
            "1168010500": 26,  # 삼성동  
            "1168010800": 23,  # 논현동
            "1168010600": 22,  # 대치동
            "1168010700": 22   # 신사동
        }
        
        # 우선순위 기반 정렬된 지역으로 배치 수집
        optimized_regions = collector.intelligent_scheduling(priority_map)
        results = collector.collect_region_batch(optimized_regions[:len(args.regions)], args.max_pages)
    
    # 결과 출력
    print(f"\n🎯 최종 결과:")
    print(f"   📊 처리된 지역: {results.get('total_regions', 0)}개")
    print(f"   ✅ 성공: {results.get('successful', 0)}개")
    print(f"   ❌ 실패: {results.get('failed', 0)}개")
    
    if 'performance' in results:
        perf = results['performance']
        print(f"   ⚡ 성능 메트릭:")
        print(f"      - 수집 속도: {perf['collection_rate']:.1f}개/초")
        print(f"      - 총 수집량: {perf['total_collected']:,}개")
        print(f"      - 메모리 사용: {perf['memory_peak_mb']:.1f}MB")
        print(f"      - 중복 제거: {perf['duplicates_removed']}개")

if __name__ == "__main__":
    main()