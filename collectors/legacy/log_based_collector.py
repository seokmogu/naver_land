#!/usr/bin/env python3
"""
로그 기반 네이버 부동산 수집기
- 실시간 진행 상황을 로그 파일에 기록
- DB 업데이트 최소화 (시작/완료만)
- 수집된 데이터를 상세하게 로그에 기록
"""

import sys
import time
import argparse
import random
import json
import os
from multiprocessing import Pool
from collectors.experimental.log_based_logger import LogBasedProgressTracker, log_based_collection
from collectors.archived.fixed_naver_collector_v2_optimized import collect_by_cortar_no

class LogBasedNaverCollector:
    def __init__(self):
        self.tracker = LogBasedProgressTracker()
        
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
    
    def collect_dong_with_logging(self, dong_info):
        """개별 동 수집 (로그 기반 + 실제 네이버 API)"""
        dong_name = dong_info["name"]
        cortar_no = dong_info["cortar_no"]
        
        print(f"\n🚀 {dong_name} 수집 시작...")
        
        with log_based_collection(dong_name, cortar_no, self.tracker) as ctx:
            try:
                # 실제 네이버 API를 통한 수집 실행
                print(f"  🔍 {dong_name} API 호출 중...")
                
                # collect_by_cortar_no 호출하여 실제 데이터 수집
                result = collect_by_cortar_no(cortar_no, include_details=True, max_pages=float('inf'))
                
                if not result.get('success', False):
                    error_msg = result.get('error', '수집 실패')
                    print(f"❌ {dong_name} API 수집 실패: {error_msg}")
                    raise Exception(f"API 수집 실패: {error_msg}")
                
                # 수집된 데이터 파일 로드
                filepath = result.get('filepath')
                if not filepath or not os.path.exists(filepath):
                    raise Exception(f"수집 데이터 파일을 찾을 수 없음: {filepath}")
                
                print(f"  📄 {dong_name} 데이터 로드: {filepath}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    collection_data = json.load(f)
                
                properties = collection_data.get('properties', [])
                collected_count = len(properties)
                
                # 수집된 매물들을 개별적으로 로그에 기록
                print(f"  📊 {dong_name} {collected_count}개 매물 로그 기록 중...")
                
                for i, prop in enumerate(properties):
                    # 매물 데이터를 로그 형식으로 변환
                    property_data = {
                        'article_no': prop.get('매물번호', f'{cortar_no}_api_{i+1}'),
                        'article_name': prop.get('매물명', f'{dong_name} 매물 {i+1}'),
                        'real_estate_type': prop.get('부동산타입', ''),
                        'trade_type': prop.get('거래타입', ''),
                        'price': prop.get('매매가격', ''),
                        'rent_price': prop.get('월세', ''),
                        'area1': prop.get('전용면적', ''),
                        'floor': prop.get('층정보', ''),
                        'address': prop.get('상세주소', ''),
                        'cortar_no': cortar_no,
                        'collected_date': self.tracker.get_kst_now().date().isoformat()
                    }
                    
                    # 매물 데이터 로그
                    ctx['log_property'](property_data)
                    
                    # 통계 업데이트
                    ctx['stats']['total_collected'] += 1
                    ctx['stats']['last_property'] = property_data['article_name']
                    
                    # 진행 상황 출력 (100개마다)
                    if (i + 1) % 100 == 0:
                        print(f"    🔄 {i + 1}/{collected_count}개 로그 기록 완료...")
                
                # 수집 요약 로그
                summary = {
                    'dong_name': dong_name,
                    'cortar_no': cortar_no,
                    'total_properties': collected_count,
                    'collection_time': f'약 {int((time.time() - collection_data.get("수집시간", {}).get("시작시간", time.time()))/60)}분',
                    'api_response': {
                        'filepath': filepath,
                        'success': True
                    },
                    'data_summary': collection_data.get('수집통계', {})
                }
                ctx['log_summary'](summary)
                
                print(f"✅ {dong_name} 수집 완료 - {collected_count}개 매물")
                return {
                    'dong_name': dong_name,
                    'status': 'completed',
                    'total_collected': collected_count,
                    'summary': summary,
                    'filepath': filepath
                }
                
            except Exception as e:
                print(f"❌ {dong_name} 수집 실패: {e}")
                return {
                    'dong_name': dong_name,
                    'status': 'failed',
                    'error': str(e)
                }
    
    def run_parallel_collection(self, max_workers=1):
        """병렬 수집 실행"""
        print("🚀 강남구 로그 기반 병렬 수집 시작")
        print("=" * 80)
        print(f"🔄 병렬 프로세스 수: {max_workers}개")
        print(f"📊 로그 기반 모니터링 활성화")
        print(f"🗃️ DB 업데이트 최소화 (시작/완료만)")
        
        # 우선순위 순으로 정렬
        sorted_dongs = sorted(self.gangnam_dongs, key=lambda x: x['priority'], reverse=True)
        
        print(f"\n📋 수집 대상: {len(sorted_dongs)}개 동")
        print("🏆 우선순위 순서:")
        for i, dong in enumerate(sorted_dongs, 1):
            print(f"   {i:2d}. {dong['name']:8s} (점수: {dong['priority']:2d}) - {dong['cortar_no']}")
        
        print(f"\n🚀 병렬 수집 시작: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 실시간 진행 상황: http://localhost:8000")
        print("=" * 80)
        
        start_time = time.time()
        
        if max_workers == 1:
            # 단일 프로세스로 순차 실행
            results = []
            for dong_info in sorted_dongs:
                try:
                    result = self.collect_dong_with_logging(dong_info)
                    results.append(result)
                except KeyboardInterrupt:
                    print("\n⚠️ 사용자 중단 요청")
                    break
                except Exception as e:
                    print(f"❌ {dong_info['name']} 처리 중 오류: {e}")
                    results.append({
                        'dong_name': dong_info['name'],
                        'status': 'failed',
                        'error': str(e)
                    })
        else:
            # 멀티프로세싱 실행
            with Pool(processes=max_workers) as pool:
                try:
                    results = pool.map(self.collect_dong_with_logging, sorted_dongs)
                except KeyboardInterrupt:
                    print("\n⚠️ 사용자 중단 요청")
                    pool.terminate()
                    pool.join()
                    return
        
        # 결과 요약
        end_time = time.time()
        total_time = end_time - start_time
        
        completed = [r for r in results if r.get('status') == 'completed']
        failed = [r for r in results if r.get('status') == 'failed']
        total_properties = sum(r.get('total_collected', 0) for r in completed)
        
        print("\n" + "=" * 80)
        print("📊 수집 완료 요약")
        print("=" * 80)
        print(f"🕐 총 소요 시간: {total_time:.1f}초")
        print(f"✅ 성공한 동: {len(completed)}개")
        print(f"❌ 실패한 동: {len(failed)}개")
        print(f"🏢 총 수집 매물: {total_properties:,}개")
        print(f"⚡ 평균 수집 속도: {total_properties/total_time:.1f}개/초")
        
        if failed:
            print(f"\n❌ 실패한 동들:")
            for fail in failed:
                print(f"   - {fail['dong_name']}: {fail.get('error', 'Unknown error')}")
        
        print(f"\n📊 실시간 모니터링: http://localhost:8000")
        print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description='로그 기반 네이버 부동산 수집기')
    parser.add_argument('--max-workers', type=int, default=1,
                        help='최대 병렬 프로세스 수 (기본값: 1)')
    parser.add_argument('--test-single', type=str, default=None,
                        help='단일 동 테스트 (예: 역삼동)')
    
    args = parser.parse_args()
    
    try:
        collector = LogBasedNaverCollector()
        
        # 단일 동 테스트 모드
        if args.test_single:
            # 해당 동 정보 찾기
            target_dong = None
            for dong in collector.gangnam_dongs:
                if dong["name"] == args.test_single:
                    target_dong = dong
                    break
            
            if target_dong:
                print(f"🧪 단일 동 테스트 모드: {args.test_single}")
                result = collector.collect_dong_with_logging(target_dong)
                print(f"\n📊 테스트 결과: {result}")
            else:
                print(f"❌ '{args.test_single}' 동을 찾을 수 없습니다.")
                print("사용 가능한 동:", [dong["name"] for dong in collector.gangnam_dongs])
        else:
            collector.run_parallel_collection(max_workers=args.max_workers)
            
    except KeyboardInterrupt:
        print("\n⚠️ 프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 프로그램 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
