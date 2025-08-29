#!/usr/bin/env python3
"""
성능 벤치마크 도구
기존 방식 vs 최적화된 직접 저장 방식 성능 비교
"""

import time
import json
import os
import sys
import psutil
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

# 상대 경로로 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    method_name: str
    region_name: str
    cortar_no: str
    success: bool
    
    # 시간 측정
    start_time: str
    end_time: str
    processing_time: float
    
    # 데이터 통계
    total_properties: int
    new_properties: int
    updated_properties: int
    failed_properties: int
    
    # 성능 지표
    properties_per_second: float
    
    # 리소스 사용량
    peak_memory_mb: float
    avg_memory_mb: float
    cpu_percent: float
    
    # 추가 메트릭
    batch_count: int = 0
    api_calls: int = 0
    error_message: str = ""

class PerformanceBenchmark:
    """성능 벤치마크 도구"""
    
    def __init__(self):
        """벤치마크 도구 초기화"""
        self.results = []
        self.process = psutil.Process()
        
    def benchmark_method(self, method_name: str, method_func, *args, **kwargs) -> BenchmarkResult:
        """
        특정 메소드의 성능 벤치마크
        
        Args:
            method_name: 메소드 이름
            method_func: 실행할 함수
            *args, **kwargs: 함수 매개변수
            
        Returns:
            BenchmarkResult: 벤치마크 결과
        """
        
        print(f"\n🔍 벤치마크 시작: {method_name}")
        print("=" * 50)
        
        # 시작 상태 기록
        start_time = datetime.now()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = start_memory
        total_memory = 0
        memory_samples = 0
        
        # CPU 모니터링 시작
        cpu_percent = self.process.cpu_percent()
        
        try:
            # 메모리 모니터링을 위한 별도 스레드는 생략하고 간단하게 처리
            result = method_func(*args, **kwargs)
            
            # 종료 상태 기록
            end_time = datetime.now()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            cpu_percent = self.process.cpu_percent()
            
            peak_memory = max(peak_memory, end_memory)
            processing_time = (end_time - start_time).total_seconds()
            
            # 결과 추출
            if isinstance(result, dict) and result.get('success'):
                # 성공적인 수집 결과 처리
                collection_stats = result.get('collection_stats', {})
                session_info = result.get('session_info', {})
                performance = result.get('performance', {})
                
                total_properties = collection_stats.get('collected_properties', 0)
                new_properties = collection_stats.get('new_properties', 0)
                updated_properties = collection_stats.get('updated_properties', 0)
                failed_properties = collection_stats.get('failed_properties', 0)
                batch_count = result.get('batch_count', 0)
                
                properties_per_second = performance.get('records_per_second', 
                    total_properties / processing_time if processing_time > 0 else 0
                )
                
                benchmark_result = BenchmarkResult(
                    method_name=method_name,
                    region_name=result.get('region_name', ''),
                    cortar_no=result.get('cortar_no', ''),
                    success=True,
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    processing_time=processing_time,
                    total_properties=total_properties,
                    new_properties=new_properties,
                    updated_properties=updated_properties,
                    failed_properties=failed_properties,
                    properties_per_second=properties_per_second,
                    peak_memory_mb=peak_memory,
                    avg_memory_mb=(start_memory + end_memory) / 2,
                    cpu_percent=cpu_percent,
                    batch_count=batch_count,
                    api_calls=session_info.get('total_pages', 0)
                )
                
            else:
                # 실패한 경우
                error_message = result.get('error', '알 수 없는 오류') if isinstance(result, dict) else str(result)
                
                benchmark_result = BenchmarkResult(
                    method_name=method_name,
                    region_name=kwargs.get('region_name', ''),
                    cortar_no=args[0] if args else '',
                    success=False,
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    processing_time=processing_time,
                    total_properties=0,
                    new_properties=0,
                    updated_properties=0,
                    failed_properties=0,
                    properties_per_second=0.0,
                    peak_memory_mb=peak_memory,
                    avg_memory_mb=(start_memory + end_memory) / 2,
                    cpu_percent=cpu_percent,
                    error_message=error_message
                )
            
        except Exception as e:
            # 예외 발생
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            benchmark_result = BenchmarkResult(
                method_name=method_name,
                region_name=kwargs.get('region_name', ''),
                cortar_no=args[0] if args else '',
                success=False,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                processing_time=processing_time,
                total_properties=0,
                new_properties=0,
                updated_properties=0,
                failed_properties=0,
                properties_per_second=0.0,
                peak_memory_mb=peak_memory,
                avg_memory_mb=(start_memory + peak_memory) / 2,
                cpu_percent=cpu_percent,
                error_message=str(e)
            )
        
        # 결과 출력
        self._print_benchmark_result(benchmark_result)
        
        # 결과 저장
        self.results.append(benchmark_result)
        
        return benchmark_result
    
    def _print_benchmark_result(self, result: BenchmarkResult):
        """벤치마크 결과 출력"""
        
        if result.success:
            print(f"✅ {result.method_name} 완료")
            print(f"   지역: {result.region_name} ({result.cortar_no})")
            print(f"   처리 시간: {result.processing_time:.2f}초")
            print(f"   총 매물: {result.total_properties:,}개")
            print(f"   신규 매물: {result.new_properties:,}개")
            print(f"   업데이트: {result.updated_properties:,}개")
            print(f"   처리 속도: {result.properties_per_second:.1f} 매물/초")
            print(f"   최대 메모리: {result.peak_memory_mb:.1f}MB")
            print(f"   평균 메모리: {result.avg_memory_mb:.1f}MB")
            print(f"   CPU 사용률: {result.cpu_percent:.1f}%")
            print(f"   배치 수: {result.batch_count}개")
            print(f"   API 호출: {result.api_calls}회")
        else:
            print(f"❌ {result.method_name} 실패")
            print(f"   처리 시간: {result.processing_time:.2f}초")
            print(f"   오류: {result.error_message}")
            print(f"   최대 메모리: {result.peak_memory_mb:.1f}MB")
    
    def compare_methods(self, test_cases: List[Tuple[str, str]]) -> Dict:
        """
        여러 메소드 성능 비교
        
        Args:
            test_cases: [(cortar_no, region_name), ...] 리스트
            
        Returns:
            Dict: 비교 결과
        """
        
        print(f"\n🏁 성능 비교 시작: {len(test_cases)}개 지역")
        print("=" * 60)
        
        comparison_results = {
            'test_cases': test_cases,
            'methods': {},
            'summary': {}
        }
        
        for cortar_no, region_name in test_cases:
            print(f"\n📍 테스트 지역: {region_name} ({cortar_no})")
            
            # 1. 기존 방식 (UnifiedCollector)
            try:
                from unified_collector import UnifiedCollector
                
                def test_unified():
                    collector = UnifiedCollector()
                    return collector.collect_and_save(cortar_no, region_name)
                
                unified_result = self.benchmark_method(
                    "기존 방식 (JSON→DB)", 
                    test_unified
                )
                
            except Exception as e:
                print(f"⚠️ 기존 방식 테스트 불가: {e}")
                unified_result = None
            
            # 2. 최적화된 직접 저장 방식
            try:
                from optimized_direct_collector import OptimizedDirectCollector
                
                def test_direct():
                    collector = OptimizedDirectCollector(batch_size=50)
                    return collector.collect_region_direct(cortar_no, region_name)
                
                direct_result = self.benchmark_method(
                    "최적화 방식 (Direct DB)", 
                    test_direct
                )
                
            except Exception as e:
                print(f"⚠️ 최적화 방식 테스트 불가: {e}")
                direct_result = None
            
            # 결과 저장
            comparison_results['methods'][f"{region_name}_{cortar_no}"] = {
                'unified': unified_result,
                'direct': direct_result
            }
        
        # 전체 비교 분석
        comparison_results['summary'] = self._analyze_comparison(comparison_results['methods'])
        
        return comparison_results
    
    def _analyze_comparison(self, methods_results: Dict) -> Dict:
        """비교 분석 수행"""
        
        unified_results = []
        direct_results = []
        
        for region_results in methods_results.values():
            if region_results['unified'] and region_results['unified'].success:
                unified_results.append(region_results['unified'])
            
            if region_results['direct'] and region_results['direct'].success:
                direct_results.append(region_results['direct'])
        
        if not unified_results or not direct_results:
            return {'error': '비교할 수 있는 성공적인 결과가 부족합니다'}
        
        # 평균 계산
        unified_avg = {
            'processing_time': sum(r.processing_time for r in unified_results) / len(unified_results),
            'properties_per_second': sum(r.properties_per_second for r in unified_results) / len(unified_results),
            'peak_memory_mb': sum(r.peak_memory_mb for r in unified_results) / len(unified_results),
            'total_properties': sum(r.total_properties for r in unified_results) / len(unified_results)
        }
        
        direct_avg = {
            'processing_time': sum(r.processing_time for r in direct_results) / len(direct_results),
            'properties_per_second': sum(r.properties_per_second for r in direct_results) / len(direct_results),
            'peak_memory_mb': sum(r.peak_memory_mb for r in direct_results) / len(direct_results),
            'total_properties': sum(r.total_properties for r in direct_results) / len(direct_results)
        }
        
        # 개선률 계산
        time_improvement = ((unified_avg['processing_time'] - direct_avg['processing_time']) / 
                           unified_avg['processing_time'] * 100) if unified_avg['processing_time'] > 0 else 0
        
        speed_improvement = ((direct_avg['properties_per_second'] - unified_avg['properties_per_second']) / 
                            unified_avg['properties_per_second'] * 100) if unified_avg['properties_per_second'] > 0 else 0
        
        memory_improvement = ((unified_avg['peak_memory_mb'] - direct_avg['peak_memory_mb']) / 
                             unified_avg['peak_memory_mb'] * 100) if unified_avg['peak_memory_mb'] > 0 else 0
        
        summary = {
            'unified_avg': unified_avg,
            'direct_avg': direct_avg,
            'improvements': {
                'processing_time': time_improvement,
                'processing_speed': speed_improvement,
                'memory_usage': memory_improvement
            },
            'test_count': {
                'unified': len(unified_results),
                'direct': len(direct_results)
            }
        }
        
        return summary
    
    def print_comparison_summary(self, comparison_results: Dict):
        """비교 결과 요약 출력"""
        
        summary = comparison_results.get('summary')
        if not summary or 'error' in summary:
            print(f"❌ 비교 분석 실패: {summary.get('error', '알 수 없는 오류')}")
            return
        
        print(f"\n📊 성능 비교 결과 요약")
        print("=" * 60)
        
        unified_avg = summary['unified_avg']
        direct_avg = summary['direct_avg']
        improvements = summary['improvements']
        
        print(f"\n📈 평균 성능 지표")
        print(f"{'지표':<20} {'기존 방식':<15} {'최적화 방식':<15} {'개선률':<10}")
        print("-" * 60)
        print(f"{'처리 시간 (초)':<20} {unified_avg['processing_time']:<15.1f} {direct_avg['processing_time']:<15.1f} {improvements['processing_time']:>6.1f}%")
        print(f"{'처리 속도 (매물/초)':<20} {unified_avg['properties_per_second']:<15.1f} {direct_avg['properties_per_second']:<15.1f} {improvements['processing_speed']:>6.1f}%")
        print(f"{'최대 메모리 (MB)':<20} {unified_avg['peak_memory_mb']:<15.1f} {direct_avg['peak_memory_mb']:<15.1f} {improvements['memory_usage']:>6.1f}%")
        print(f"{'평균 매물 수':<20} {unified_avg['total_properties']:<15.0f} {direct_avg['total_properties']:<15.0f} {'N/A':>6}")
        
        print(f"\n🎯 개선 효과")
        if improvements['processing_time'] > 0:
            print(f"   ⚡ 처리 시간: {improvements['processing_time']:.1f}% 단축")
        if improvements['processing_speed'] > 0:
            print(f"   🚀 처리 속도: {improvements['processing_speed']:.1f}% 향상")
        if improvements['memory_usage'] > 0:
            print(f"   💾 메모리 사용: {improvements['memory_usage']:.1f}% 감소")
        
        print(f"\n📋 테스트 정보")
        print(f"   기존 방식 성공: {summary['test_count']['unified']}회")
        print(f"   최적화 방식 성공: {summary['test_count']['direct']}회")
    
    def save_benchmark_report(self, filename: str = None):
        """벤치마크 결과를 JSON 파일로 저장"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_report_{timestamp}.json"
        
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'system_info': {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                    'platform': sys.platform
                },
                'results': [asdict(result) for result in self.results]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"📄 벤치마크 리포트 저장: {filename}")
            
        except Exception as e:
            print(f"❌ 리포트 저장 실패: {e}")

def run_comprehensive_benchmark():
    """종합 벤치마크 실행"""
    
    print("🧪 네이버 부동산 수집기 종합 성능 벤치마크")
    print("=" * 60)
    
    # 벤치마크 도구 초기화
    benchmark = PerformanceBenchmark()
    
    # 테스트 케이스 정의 (소규모 지역으로 시작)
    test_cases = [
        ("1168010100", "역삼동"),
        ("1168010200", "삼성동"),
        ("1168010300", "논현동")
    ]
    
    # 비교 실행
    comparison_results = benchmark.compare_methods(test_cases)
    
    # 결과 요약 출력
    benchmark.print_comparison_summary(comparison_results)
    
    # 리포트 저장
    benchmark.save_benchmark_report()
    
    return comparison_results

if __name__ == "__main__":
    # 종합 벤치마크 실행
    results = run_comprehensive_benchmark()