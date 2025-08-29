#!/usr/bin/env python3
"""
배치 수집 스케줄러
완전성 우선 계획에 따라 시간차를 두고 안전하게 수집
"""

import json
import time
import os
from datetime import datetime
from typing import Dict
from fixed_naver_collector import FixedNaverCollector

class BatchCollectionScheduler:
    def __init__(self, token: str, config_file: str = "gu_config.json", use_address_converter: bool = True):
        self.token = token
        self.collector = FixedNaverCollector(token, use_address_converter=use_address_converter)
        
        # 설정 로드
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def execute_collection_plan(self, plan_file: str) -> Dict:
        """수집 계획 파일을 읽어서 배치별로 실행"""
        print(f"📋 수집 계획 로드: {plan_file}")
        
        with open(plan_file, 'r', encoding='utf-8') as f:
            collection_plan = json.load(f)
        
        gu_name = collection_plan['gu_name']
        batches = collection_plan['collection_batches']
        
        print(f"🚀 {gu_name} 배치 수집 시작!")
        print(f"총 {len(batches)}개 배치 예정")
        
        execution_results = {
            "gu_name": gu_name,
            "execution_start": datetime.now().isoformat(),
            "batch_results": {},
            "total_collected": 0,
            "total_errors": 0
        }
        
        # 배치별 순차 실행
        for batch_name, batch_info in batches.items():
            print(f"\n{'='*60}")
            print(f"📦 {batch_name} 실행 중...")
            print(f"   설명: {batch_info['description']}")
            print(f"   대상 지역: {batch_info['total_areas']}개")
            print(f"   예상 매물: {batch_info['total_properties']}개")
            
            # 빈 배치는 건너뛰기
            if batch_info['total_areas'] == 0:
                print("⏭️ 빈 배치 - 건너뛰기")
                execution_results['batch_results'][batch_name] = {
                    "start_time": datetime.now().isoformat(),
                    "total_areas": 0,
                    "processed_areas": 0,
                    "collected_properties": 0,
                    "error_count": 0,
                    "area_results": [],
                    "end_time": datetime.now().isoformat(),
                    "skipped": True
                }
                continue
            
            # 지연 시간 적용 (빈 배치가 아닐 때만)
            if 'delay_minutes' in batch_info and batch_info['delay_minutes'] > 0:
                delay_minutes = batch_info['delay_minutes']
                print(f"⏰ {delay_minutes}분 대기 중...")
                time.sleep(delay_minutes * 60)
            
            # 배치 실행
            batch_result = self._execute_single_batch(batch_info, gu_name)
            execution_results['batch_results'][batch_name] = batch_result
            
            # 결과 누적
            execution_results['total_collected'] += batch_result['collected_properties']
            execution_results['total_errors'] += batch_result['error_count']
            
            print(f"✅ {batch_name} 완료: {batch_result['collected_properties']}개 매물 수집")
            
            # 배치 간 휴식 (마지막 배치가 아닌 경우)
            batch_list = list(batches.keys())
            if batch_name != batch_list[-1]:
                rest_minutes = self.config['global_settings']['batch_rest_minutes']
                print(f"😴 다음 배치까지 {rest_minutes}분 휴식...")
                time.sleep(rest_minutes * 60)
        
        execution_results['execution_end'] = datetime.now().isoformat()
        
        # 최종 결과 저장
        self._save_execution_results(execution_results)
        
        print(f"\n🎉 {gu_name} 전체 수집 완료!")
        print(f"총 수집 매물: {execution_results['total_collected']}개")
        print(f"총 오류 수: {execution_results['total_errors']}개")
        
        return execution_results
    
    def _execute_single_batch(self, batch_info: Dict, gu_name: str) -> Dict:
        """단일 배치 실행"""
        areas = batch_info['areas']
        batch_result = {
            "start_time": datetime.now().isoformat(),
            "total_areas": len(areas),
            "processed_areas": 0,
            "collected_properties": 0,
            "error_count": 0,
            "area_results": []
        }
        
        for i, area in enumerate(areas):
            cortar_no = area['cortar_no']
            expected_count = area['property_count']
            
            print(f"   🔄 지역 {i+1}/{len(areas)}: {cortar_no} (예상: {expected_count}개)")
            
            try:
                # 개별 지역 수집
                area_result = self._collect_single_area(cortar_no, gu_name)
                
                batch_result['area_results'].append({
                    "cortar_no": cortar_no,
                    "expected_properties": expected_count,
                    "actual_collected": area_result['collected_count'],
                    "success": area_result['success'],
                    "collection_time": area_result['collection_time'],
                    "output_file": area_result.get('output_file')
                })
                
                if area_result['success']:
                    batch_result['collected_properties'] += area_result['collected_count']
                else:
                    batch_result['error_count'] += 1
                
                batch_result['processed_areas'] += 1
                
                # 지역 간 딜레이
                delay = self.config['global_settings']['collection_delay_seconds']
                time.sleep(delay)
                
            except Exception as e:
                print(f"   ❌ 지역 {cortar_no} 수집 실패: {e}")
                batch_result['error_count'] += 1
                
                batch_result['area_results'].append({
                    "cortar_no": cortar_no,
                    "expected_properties": expected_count,
                    "actual_collected": 0,
                    "success": False,
                    "error": str(e),
                    "collection_time": 0
                })
        
        batch_result['end_time'] = datetime.now().isoformat()
        return batch_result
    
    def _collect_single_area(self, cortar_no: str, gu_name: str) -> Dict:
        """개별 지역 수집 (기존 collector 활용)"""
        start_time = time.time()
        
        try:
            # 임시 URL 생성 (cortar 기반)
            temp_url = self._create_temp_url_for_cortar(cortar_no)
            
            # 수집 실행 (결과 폴더에 저장)
            results_dir = os.path.join(os.path.dirname(__file__), 'results')
            os.makedirs(results_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"area_{gu_name}_{cortar_no}_{timestamp}.json"
            output_filepath = os.path.join(results_dir, output_filename)
            
            with open(output_filepath, 'w', encoding='utf-8') as f:
                # 메타데이터 작성
                metadata = {
                    "수집정보": {
                        "수집시간": timestamp,
                        "구이름": gu_name,
                        "지역코드": cortar_no,
                        "수집방식": "배치_완전성_우선"
                    }
                }
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                f.write(',\n')
                
                # 수집 실행
                collected_count = self.collector.collect_articles(
                    cortar_no=cortar_no,
                    parsed_url={"cortar_based": True},
                    max_pages=21,
                    include_details=True,
                    output_file=f
                )
            
            collection_time = time.time() - start_time
            
            return {
                "success": True,
                "collected_count": collected_count,
                "collection_time": collection_time,
                "output_file": output_filepath
            }
            
        except Exception as e:
            collection_time = time.time() - start_time
            return {
                "success": False,
                "collected_count": 0,
                "collection_time": collection_time,
                "error": str(e)
            }
    
    def _create_temp_url_for_cortar(self, cortar_no: str) -> str:
        """cortar 기반 임시 URL 생성"""
        # 실제로는 cortar_no로 직접 수집하므로 URL은 참고용
        return f"https://new.land.naver.com/offices?cortarNo={cortar_no}"
    
    def _save_execution_results(self, results: Dict):
        """실행 결과 저장"""
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gu_name = results['gu_name']
        filename = f"batch_execution_result_{gu_name}_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 실행 결과 저장: {filepath}")
    
    def create_collection_summary(self, execution_results: Dict) -> Dict:
        """수집 결과 요약 생성"""
        gu_name = execution_results['gu_name']
        batch_results = execution_results['batch_results']
        
        summary = {
            "gu_name": gu_name,
            "execution_summary": {
                "total_collected_properties": execution_results['total_collected'],
                "total_processed_areas": sum(batch['processed_areas'] for batch in batch_results.values()),
                "total_errors": execution_results['total_errors'],
                "success_rate": 0,
                "execution_duration": None
            },
            "batch_summary": {},
            "top_productive_areas": [],
            "problematic_areas": []
        }
        
        # 실행 시간 계산
        start_time = datetime.fromisoformat(execution_results['execution_start'])
        end_time = datetime.fromisoformat(execution_results['execution_end'])
        duration = end_time - start_time
        summary['execution_summary']['execution_duration'] = str(duration)
        
        # 성공률 계산
        total_areas = sum(batch['total_areas'] for batch in batch_results.values())
        if total_areas > 0:
            successful_areas = total_areas - execution_results['total_errors']
            summary['execution_summary']['success_rate'] = successful_areas / total_areas
        
        # 배치별 요약
        for batch_name, batch_result in batch_results.items():
            summary['batch_summary'][batch_name] = {
                "processed_areas": batch_result['processed_areas'],
                "collected_properties": batch_result['collected_properties'],
                "error_count": batch_result['error_count'],
                "avg_properties_per_area": (
                    batch_result['collected_properties'] / batch_result['processed_areas']
                    if batch_result['processed_areas'] > 0 else 0
                )
            }
        
        # 생산성 높은 지역 TOP 10
        all_area_results = []
        for batch_result in batch_results.values():
            all_area_results.extend(batch_result['area_results'])
        
        productive_areas = sorted(
            [area for area in all_area_results if area['success']],
            key=lambda x: x['actual_collected'],
            reverse=True
        )[:10]
        
        summary['top_productive_areas'] = productive_areas
        
        # 문제 지역들
        problematic_areas = [area for area in all_area_results if not area['success']]
        summary['problematic_areas'] = problematic_areas
        
        return summary

def main():
    """배치 수집 스케줄러 실행"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python batch_collection_scheduler.py <수집계획파일> [토큰]")
        print("예시: python batch_collection_scheduler.py collection_plan_강남구_20250804_143000.json")
        return
    
    plan_file = sys.argv[1]
    
    # 토큰 수집
    if len(sys.argv) >= 3:
        token = sys.argv[2]
    else:
        from playwright_token_collector import PlaywrightTokenCollector
        print("🔑 토큰 수집 중...")
        token_collector = PlaywrightTokenCollector()
        token = token_collector.get_token_with_playwright()
        
        if not token:
            print("❌ 토큰 획득 실패")
            return
    
    # 배치 수집 실행
    scheduler = BatchCollectionScheduler(token)
    
    try:
        execution_results = scheduler.execute_collection_plan(plan_file)
        
        # 요약 생성
        summary = scheduler.create_collection_summary(execution_results)
        
        print("\n📊 수집 완료 요약:")
        print(f"   성공률: {summary['execution_summary']['success_rate']:.1%}")
        print(f"   실행 시간: {summary['execution_summary']['execution_duration']}")
        print(f"   총 매물: {summary['execution_summary']['total_collected_properties']}개")
        
    except Exception as e:
        print(f"❌ 배치 수집 중 오류: {e}")

if __name__ == "__main__":
    main()