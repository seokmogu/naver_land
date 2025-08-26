#!/usr/bin/env python3
"""
강남구 전체 동 병렬 자동 배치 수집 스크립트
멀티프로세싱을 사용하여 동별로 병렬 수집
"""

import sys
import time
import json
import signal
import multiprocessing as mp
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed
from supabase_client import SupabaseHelper
from cached_token_collector import collect_by_cortar_no
from progress_logger import ProgressLogger

# 전역 변수로 종료 상태 관리
shutdown_requested = False

def signal_handler(signum, frame):
    """Ctrl+C 처리"""
    global shutdown_requested
    print(f"\n⚠️ 종료 신호 수신 (Ctrl+C). 안전하게 종료 중...")
    shutdown_requested = True

def get_gangnam_collection_priority() -> List[Dict]:
    """강남구 동별 수집 우선순위 리스트 반환"""
    helper = SupabaseHelper()
    result = helper.client.table('areas').select('dong_name, cortar_no, center_lat, center_lon').eq('gu_name', '강남구').execute()
    
    # 우선순위 점수 매핑
    priority_scores = {
        '역삼동': 30, '삼성동': 26, '논현동': 23, '대치동': 22, '신사동': 22,
        '압구정동': 20, '청담동': 18, '도곡동': 18, '개포동': 17, '수서동': 12,
        '일원동': 11, '자곡동': 8, '세곡동': 6, '율현동': 5
    }
    
    # 점수 기준으로 정렬
    areas = []
    for area in result.data:
        dong_name = area['dong_name']
        score = priority_scores.get(dong_name, 1)
        areas.append({
            'dong_name': dong_name,
            'cortar_no': area['cortar_no'],
            'center_lat': area['center_lat'],
            'center_lon': area['center_lon'],
            'priority_score': score
        })
    
    # 우선순위 내림차순 정렬
    return sorted(areas, key=lambda x: x['priority_score'], reverse=True)

def collect_single_dong(area_info: Dict, include_details: bool = False) -> Dict:
    """단일 동 수집 (병렬 처리용) - 향상된 로거 사용"""
    dong_name = area_info['dong_name']
    cortar_no = area_info['cortar_no']
    process_name = mp.current_process().name
    
    print(f"🎯 [{process_name}] {dong_name} ({cortar_no}) 수집 시작")
    
    # ProgressLogger 사용으로 자동 로그 관리 및 진행 상태 업데이트
    logger = ProgressLogger()
    
    try:
        with logger.log_collection('강남구', dong_name, cortar_no, f'parallel_collection_{process_name}') as log_context:
            collection_start = time.time()
            
            # 매물 데이터 수집 (각 프로세스에서 독립적으로 토큰 생성)
            collect_result = collect_by_cortar_no(cortar_no, include_details, max_pages=999)
            
            if collect_result['success']:
                duration = time.time() - collection_start
                collected_count = collect_result['count']
                json_filepath = collect_result['filepath']
                
                print(f"✅ [{process_name}] {dong_name} 수집 완료 (소요시간: {duration:.1f}초, {collected_count}개 매물)")
                
                # JSON 파일을 Supabase에 저장
                print(f"💾 [{process_name}] Supabase 저장 시작: {json_filepath}")
                from json_to_supabase import process_json_file
                
                supabase_result = process_json_file(json_filepath, cortar_no)
                
                if supabase_result['success']:
                    print(f"✅ [{process_name}] Supabase 저장 완료: {supabase_result['count']}개 매물")
                    
                    # 최종 통계 저장 (SimpleEnhancedLogger 자동으로 completed 처리)
                    logger.log_final_stats(
                        log_context['log_id'], 
                        collected_count, 
                        supabase_result['stats'], 
                        duration
                    )
                    
                    return {
                        'success': True,
                        'dong_name': dong_name,
                        'duration': duration,
                        'collected_count': collected_count,
                        'supabase_count': supabase_result['count'],
                        'supabase_stats': supabase_result['stats'],
                        'json_filepath': json_filepath,
                        'process_name': process_name
                    }
                else:
                    print(f"❌ [{process_name}] Supabase 저장 실패: {supabase_result.get('message', 'Unknown')}")
                    
                    # 부분 성공 - 수집은 됐지만 DB 저장 실패
                    raise Exception(f"Supabase 저장 실패: {supabase_result.get('error', 'Unknown')}")
            else:
                print(f"❌ [{process_name}] {dong_name} 수집 실패")
                raise Exception('수집 실패')
                
    except Exception as e:
        print(f"❌ [{process_name}] {dong_name} 수집 중 오류: {e}")
        return {
            'success': False,
            'dong_name': dong_name,
            'error': str(e),
            'process_name': process_name
        }
    
    finally:
        print(f"🔚 [{process_name}] {dong_name} 프로세스 종료")

def main():
    """강남구 전체 동 병렬 수집 메인 함수"""
    print("🚀 강남구 전체 동 병렬 자동 수집 시작")
    print("=" * 80)
    
    # 수집 옵션
    include_details = True  # 상세정보 포함 (기본값 변경)
    max_workers = 1  # VM 성능 고려하여 순차 처리 (기본값: 1개)
    
    # 명령행 인자 처리
    if '--max-workers' in sys.argv:
        idx = sys.argv.index('--max-workers')
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            max_workers = int(sys.argv[idx + 1])
            print(f"🔄 병렬 프로세스 수: {max_workers}개")
    
    if include_details:
        print("🔍 상세정보 포함 수집 모드")
    else:
        print("⚡ 기본 정보만 수집 모드 (속도 최적화)")
    
    # CPU 코어 수 확인 및 조정
    cpu_count = mp.cpu_count()
    if max_workers > cpu_count:
        max_workers = cpu_count
        print(f"⚠️ CPU 코어 수({cpu_count})에 맞춰 프로세스 수 조정: {max_workers}개")
    
    # 강남구 동별 우선순위 목록 가져오기
    areas = get_gangnam_collection_priority()
    total_areas = len(areas)
    
    print(f"\n📋 수집 대상: {total_areas}개 동")
    print(f"🔄 병렬 프로세스: {max_workers}개")
    print("🏆 우선순위 순서:")
    for i, area in enumerate(areas, 1):
        print(f"  {i:2d}. {area['dong_name']:8s} (점수: {area['priority_score']:2d}) - {area['cortar_no']}")
    
    # 병렬 수집 시작
    batch_start = datetime.now()
    results = []
    success_count = 0
    
    # Ctrl+C 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"\n🚀 병렬 수집 시작: {batch_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔄 {max_workers}개 프로세스로 동시 실행")
    print("💡 Ctrl+C로 안전하게 종료 가능")
    print("=" * 80)
    
    # ProcessPoolExecutor 사용하여 병렬 처리 (안전한 리소스 관리)
    try:
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context('spawn')) as executor:
            # 모든 동에 대해 작업 제출
            future_to_area = {
                executor.submit(collect_single_dong, area, include_details): area 
                for area in areas
            }
            
            # 완료된 작업들을 순서대로 처리
            completed_count = 0
            for future in as_completed(future_to_area):
                # 종료가 요청되었는지 확인
                if shutdown_requested:
                    print("⚠️ 사용자 요청으로 종료 중... 진행 중인 작업 완료 대기")
                    # 모든 pending futures 취소
                    for f in future_to_area:
                        if not f.done():
                            f.cancel()
                    break
                    
                completed_count += 1
                area = future_to_area[future]
                
                try:
                    # 타임아웃 설정으로 무한 대기 방지
                    result = future.result(timeout=7200)  # 2시간 타임아웃
                    results.append(result)
                    
                    print(f"\n📊 전체 진행률: {completed_count}/{total_areas} ({completed_count/total_areas*100:.1f}%)")
                    
                    if result['success']:
                        success_count += 1
                        print(f"✅ 성공: {result['dong_name']} ({result.get('duration', 0):.1f}초) - {result.get('process_name', 'Unknown')}")
                    else:
                        print(f"❌ 실패: {result['dong_name']} - {result.get('error', 'Unknown')} - {result.get('process_name', 'Unknown')}")
                        
                except TimeoutError:
                    print(f"⏰ 타임아웃: {area['dong_name']} (2시간 초과)")
                    results.append({
                        'success': False,
                        'dong_name': area['dong_name'],
                        'error': 'Timeout (2시간 초과)',
                        'process_name': 'timeout'
                    })
                    
                except Exception as e:
                    print(f"❌ {area['dong_name']} 처리 중 예외 발생: {e}")
                    results.append({
                        'success': False,
                        'dong_name': area['dong_name'],
                        'error': f"처리 중 예외: {e}",
                        'process_name': 'error'
                    })
    
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 병렬 처리 중 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
    
    # 병렬 수집 완료 요약
    batch_end = datetime.now()
    total_duration = (batch_end - batch_start).total_seconds()
    
    print(f"\n🎯 강남구 전체 병렬 수집 완료!")
    print("=" * 80)
    print(f"📊 수집 통계:")
    print(f"  - 전체 동 수: {total_areas}개")
    print(f"  - 성공한 동: {success_count}개")
    print(f"  - 실패한 동: {total_areas - success_count}개")
    print(f"  - 성공률: {success_count/total_areas*100:.1f}%")
    print(f"  - 총 소요시간: {total_duration/60:.1f}분")
    print(f"  - 시작시간: {batch_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 완료시간: {batch_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 병렬 프로세스: {max_workers}개")
    
    # 결과 저장
    timestamp = batch_start.strftime("%Y%m%d_%H%M%S")
    result_file = f"results/parallel_collection_gangnam_{timestamp}.json"
    
    batch_summary = {
        'batch_info': {
            'gu_name': '강남구',
            'start_time': batch_start.isoformat(),
            'end_time': batch_end.isoformat(),
            'total_duration_seconds': total_duration,
            'include_details': include_details,
            'max_workers': max_workers,
            'collection_method': 'parallel'
        },
        'statistics': {
            'total_areas': total_areas,
            'success_count': success_count,
            'failed_count': total_areas - success_count,
            'success_rate': success_count/total_areas*100 if total_areas > 0 else 0
        },
        'results': results
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(batch_summary, f, ensure_ascii=False, indent=2)
    
    print(f"💾 병렬 수집 결과 저장: {result_file}")
    
    if success_count == total_areas:
        print("🎉 모든 동 수집 성공!")
        sys.exit(0)
    else:
        print(f"⚠️ {total_areas - success_count}개 동 수집 실패")
        sys.exit(1)

if __name__ == "__main__":
    # 멀티프로세싱에서 필요한 설정
    mp.set_start_method('spawn', force=True)
    main()
