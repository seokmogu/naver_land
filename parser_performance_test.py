#!/usr/bin/env python3
"""
파서 성능 테스트 및 벤치마킹 시스템
- 8개 섹션별 파싱 성능 측정
- 메모리 사용량 모니터링
- 처리 속도 벤치마킹
"""

import os
import sys
import json
import time
import psutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from enhanced_data_collector import EnhancedNaverCollector

class ParserPerformanceTest:
    def __init__(self):
        """성능 테스트 시스템 초기화"""
        self.collector = EnhancedNaverCollector()
        
        # 성능 통계
        self.performance_stats = {
            'test_start': datetime.now().isoformat(),
            'total_properties_tested': 0,
            'section_performance': {},
            'memory_usage': {},
            'error_rates': {},
            'processing_times': {
                'total': [],
                'per_section': {}
            }
        }
        
        # 테스트 데이터 (실제 API 응답 샘플)
        self.test_samples = []
    
    def generate_test_data(self, sample_count: int = 10) -> List[str]:
        """테스트용 매물 번호 생성"""
        print(f"🔍 테스트용 매물 {sample_count}개 수집 중...")
        
        try:
            # 역삼동에서 테스트 매물 수집
            test_articles = self.collector.collect_single_page_articles("1168010100", 1)
            
            if len(test_articles) >= sample_count:
                return test_articles[:sample_count]
            else:
                print(f"⚠️ 요청된 {sample_count}개보다 적은 {len(test_articles)}개 매물 발견")
                return test_articles
                
        except Exception as e:
            print(f"❌ 테스트 데이터 생성 실패: {e}")
            return []
    
    def measure_memory_usage(self) -> Dict:
        """현재 메모리 사용량 측정"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': round(memory_info.rss / 1024 / 1024, 2),  # Resident Set Size
            'vms_mb': round(memory_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
            'percent': round(process.memory_percent(), 2)
        }
    
    def test_section_performance(self, article_data: Dict, article_no: str) -> Dict:
        """개별 섹션별 성능 테스트"""
        section_times = {}
        section_errors = {}
        
        # 8개 섹션 개별 테스트
        sections_to_test = [
            ('article_detail', '_process_article_detail', 'articleDetail'),
            ('article_addition', '_process_article_addition', 'articleAddition'),
            ('article_facility', '_process_article_facility', 'articleFacility'),
            ('article_floor', '_process_article_floor', 'articleFloor'),
            ('article_price', '_process_article_price', 'articlePrice'),
            ('article_realtor', '_process_article_realtor', 'articleRealtor'),
            ('article_space', '_process_article_space', 'articleSpace'),
            ('article_tax', '_process_article_tax', 'articleTax'),
            ('article_photos', '_process_article_photos', 'articlePhotos')
        ]
        
        for section_name, method_name, data_key in sections_to_test:
            try:
                # 섹션 데이터 추출
                if data_key == 'articlePhotos':
                    section_data = article_data.get(data_key, [])
                else:
                    section_data = article_data.get(data_key, {})
                
                # 성능 측정
                start_time = time.perf_counter()
                
                # 파서 메서드 호출
                parser_method = getattr(self.collector, method_name)
                
                if data_key == 'articlePhotos':
                    result = parser_method(section_data, article_no)
                else:
                    result = parser_method(section_data, article_no)
                
                end_time = time.perf_counter()
                processing_time = (end_time - start_time) * 1000  # 밀리초
                
                section_times[section_name] = {
                    'processing_time_ms': round(processing_time, 3),
                    'data_size': len(str(section_data)),
                    'output_fields': len(result) if isinstance(result, dict) else 0,
                    'success': True
                }
                
            except Exception as e:
                section_times[section_name] = {
                    'processing_time_ms': 0,
                    'error': str(e),
                    'success': False
                }
                section_errors[section_name] = str(e)
        
        return section_times, section_errors
    
    def test_full_property_performance(self, article_no: str) -> Dict:
        """전체 매물 처리 성능 테스트"""
        print(f"  🏠 매물 {article_no} 성능 테스트...")
        
        memory_before = self.measure_memory_usage()
        start_time = time.perf_counter()
        
        try:
            # 전체 매물 데이터 수집
            enhanced_data = self.collector.collect_article_detail_enhanced(article_no)
            
            if not enhanced_data:
                return {
                    'success': False,
                    'error': 'Data collection failed',
                    'processing_time_ms': 0
                }
            
            end_time = time.perf_counter()
            total_time = (end_time - start_time) * 1000  # 밀리초
            
            memory_after = self.measure_memory_usage()
            memory_delta = memory_after['rss_mb'] - memory_before['rss_mb']
            
            # 섹션별 성능 테스트
            raw_data = enhanced_data.get('raw_sections', {})
            section_times, section_errors = self.test_section_performance(raw_data, article_no)
            
            return {
                'success': True,
                'article_no': article_no,
                'total_processing_time_ms': round(total_time, 3),
                'memory_usage': {
                    'before_mb': memory_before['rss_mb'],
                    'after_mb': memory_after['rss_mb'],
                    'delta_mb': round(memory_delta, 2)
                },
                'section_performance': section_times,
                'section_errors': section_errors,
                'data_quality': {
                    'sections_processed': len([s for s in section_times.values() if s.get('success', False)]),
                    'total_sections': len(section_times),
                    'success_rate': len([s for s in section_times.values() if s.get('success', False)]) / len(section_times) * 100
                }
            }
            
        except Exception as e:
            end_time = time.perf_counter()
            total_time = (end_time - start_time) * 1000
            
            return {
                'success': False,
                'article_no': article_no,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'processing_time_ms': round(total_time, 3)
            }
    
    def run_performance_test(self, test_count: int = 10) -> Dict:
        """전체 성능 테스트 실행"""
        print("🚀 파서 성능 테스트 시작")
        print("=" * 60)
        
        # 테스트 데이터 수집
        test_articles = self.generate_test_data(test_count)
        if not test_articles:
            print("❌ 테스트 데이터를 수집할 수 없습니다.")
            return {}
        
        print(f"📊 {len(test_articles)}개 매물로 성능 테스트 진행")
        
        test_results = []
        successful_tests = 0
        total_processing_times = []
        section_aggregated_times = {}
        
        for i, article_no in enumerate(test_articles, 1):
            print(f"\n[{i}/{len(test_articles)}] 매물 {article_no} 테스트...")
            
            result = self.test_full_property_performance(article_no)
            test_results.append(result)
            
            if result['success']:
                successful_tests += 1
                total_processing_times.append(result['total_processing_time_ms'])
                
                # 섹션별 시간 집계
                for section, timing in result['section_performance'].items():
                    if timing.get('success', False):
                        if section not in section_aggregated_times:
                            section_aggregated_times[section] = []
                        section_aggregated_times[section].append(timing['processing_time_ms'])
                
                print(f"    ✅ 성공 ({result['total_processing_time_ms']:.1f}ms)")
                print(f"    📊 섹션 성공률: {result['data_quality']['success_rate']:.1f}%")
            else:
                print(f"    ❌ 실패: {result.get('error', 'Unknown error')}")
        
        # 통계 계산
        success_rate = (successful_tests / len(test_articles)) * 100 if test_articles else 0
        
        performance_summary = {
            'test_summary': {
                'total_tests': len(test_articles),
                'successful_tests': successful_tests,
                'success_rate': round(success_rate, 2),
                'test_duration': datetime.now().isoformat()
            },
            'processing_time_stats': self._calculate_time_stats(total_processing_times),
            'section_performance': {},
            'memory_efficiency': self._analyze_memory_usage(test_results),
            'error_analysis': self._analyze_errors(test_results),
            'detailed_results': test_results
        }
        
        # 섹션별 성능 통계
        for section, times in section_aggregated_times.items():
            performance_summary['section_performance'][section] = self._calculate_time_stats(times)
        
        self.performance_stats.update(performance_summary)
        
        return performance_summary
    
    def _calculate_time_stats(self, times: List[float]) -> Dict:
        """시간 통계 계산"""
        if not times:
            return {'count': 0, 'avg_ms': 0, 'min_ms': 0, 'max_ms': 0, 'std_ms': 0}
        
        return {
            'count': len(times),
            'avg_ms': round(statistics.mean(times), 3),
            'min_ms': round(min(times), 3),
            'max_ms': round(max(times), 3),
            'std_ms': round(statistics.stdev(times) if len(times) > 1 else 0, 3),
            'median_ms': round(statistics.median(times), 3)
        }
    
    def _analyze_memory_usage(self, test_results: List[Dict]) -> Dict:
        """메모리 사용량 분석"""
        memory_deltas = []
        peak_usage = 0
        
        for result in test_results:
            if result.get('success') and 'memory_usage' in result:
                memory_info = result['memory_usage']
                memory_deltas.append(memory_info['delta_mb'])
                peak_usage = max(peak_usage, memory_info['after_mb'])
        
        return {
            'avg_memory_per_property_mb': round(statistics.mean(memory_deltas), 3) if memory_deltas else 0,
            'peak_memory_usage_mb': peak_usage,
            'memory_efficiency': 'Good' if statistics.mean(memory_deltas) < 10 else 'Needs Optimization' if memory_deltas else 'Unknown'
        }
    
    def _analyze_errors(self, test_results: List[Dict]) -> Dict:
        """에러 분석"""
        section_errors = {}
        total_errors = 0
        
        for result in test_results:
            if 'section_errors' in result:
                for section, error in result['section_errors'].items():
                    if section not in section_errors:
                        section_errors[section] = []
                    section_errors[section].append(error)
                    total_errors += 1
        
        error_summary = {}
        for section, errors in section_errors.items():
            error_summary[section] = {
                'error_count': len(errors),
                'common_errors': list(set(errors))[:3]  # 상위 3개 에러 타입
            }
        
        return {
            'total_section_errors': total_errors,
            'sections_with_errors': len(section_errors),
            'section_error_details': error_summary
        }
    
    def generate_performance_report(self) -> str:
        """성능 보고서 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"parser_performance_report_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.performance_stats, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 성능 보고서 저장: {report_file}")
            return report_file
            
        except Exception as e:
            print(f"❌ 성능 보고서 저장 실패: {e}")
            return ""
    
    def print_performance_summary(self, results: Dict):
        """성능 요약 출력"""
        print("\n" + "=" * 60)
        print("📈 파서 성능 테스트 결과 요약")
        print("=" * 60)
        
        if 'test_summary' in results:
            summary = results['test_summary']
            print(f"🔍 테스트 개요:")
            print(f"  - 테스트 매물: {summary['total_tests']}개")
            print(f"  - 성공률: {summary['success_rate']}%")
            print(f"  - 성공 건수: {summary['successful_tests']}개")
        
        if 'processing_time_stats' in results:
            time_stats = results['processing_time_stats']
            print(f"\n⏱️ 처리 시간 통계:")
            print(f"  - 평균: {time_stats.get('avg_ms', 0):.1f}ms")
            print(f"  - 최소: {time_stats.get('min_ms', 0):.1f}ms")
            print(f"  - 최대: {time_stats.get('max_ms', 0):.1f}ms")
            print(f"  - 중간값: {time_stats.get('median_ms', 0):.1f}ms")
        
        if 'section_performance' in results:
            print(f"\n📋 섹션별 성능 (평균 처리 시간):")
            section_perf = results['section_performance']
            for section, stats in sorted(section_perf.items(), key=lambda x: x[1].get('avg_ms', 0), reverse=True):
                avg_time = stats.get('avg_ms', 0)
                count = stats.get('count', 0)
                print(f"  - {section}: {avg_time:.2f}ms (테스트 {count}회)")
        
        if 'memory_efficiency' in results:
            memory = results['memory_efficiency']
            print(f"\n💾 메모리 효율성:")
            print(f"  - 매물당 평균 메모리: {memory.get('avg_memory_per_property_mb', 0):.2f}MB")
            print(f"  - 최대 메모리 사용량: {memory.get('peak_memory_usage_mb', 0):.2f}MB")
            print(f"  - 효율성 평가: {memory.get('memory_efficiency', 'Unknown')}")
        
        if 'error_analysis' in results:
            errors = results['error_analysis']
            total_errors = errors.get('total_section_errors', 0)
            error_sections = errors.get('sections_with_errors', 0)
            
            print(f"\n⚠️ 에러 분석:")
            print(f"  - 총 섹션 에러: {total_errors}개")
            print(f"  - 에러가 있는 섹션: {error_sections}개")
            
            if 'section_error_details' in errors:
                for section, details in errors['section_error_details'].items():
                    error_count = details.get('error_count', 0)
                    print(f"    - {section}: {error_count}개 에러")

def main():
    """메인 실행 함수"""
    print("🔬 파서 성능 벤치마킹 시작")
    
    # 테스트 설정
    test_count = int(input("테스트할 매물 수를 입력하세요 (기본값: 10): ") or "10")
    
    tester = ParserPerformanceTest()
    
    # 성능 테스트 실행
    results = tester.run_performance_test(test_count)
    
    if results:
        # 결과 출력
        tester.print_performance_summary(results)
        
        # 보고서 저장
        report_file = tester.generate_performance_report()
        
        print(f"\n✅ 성능 테스트 완료!")
        print(f"📄 상세 결과: {report_file}")
    else:
        print("❌ 성능 테스트 실패!")

if __name__ == "__main__":
    main()