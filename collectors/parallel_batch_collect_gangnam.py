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
from fixed_naver_collector import collect_by_cortar_no

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
    """단일 동 수집 (병렬 처리용)"""
    dong_name = area_info['dong_name']
    cortar_no = area_info['cortar_no']
    
    print(f"🎯 [{mp.current_process().name}] {dong_name} ({cortar_no}) 수집 시작")
    
    collection_start = datetime.now()
    
    # 수집 로그 시작 (로그 저장 실패 시에도 수집 계속)
    log_data = None
    try:
        helper = SupabaseHelper()
        log_data = {
            'gu_name': '강남구',
            'dong_name': dong_name,
            'cortar_no': cortar_no,
            'collection_type': f'parallel_collection_{mp.current_process().name}',
            'status': 'started',
            'started_at': collection_start.isoformat()
        }
        helper.log_collection(log_data)
    except Exception as e:
        print(f"⚠️ [{mp.current_process().name}] 로그 저장 실패, 수집은 계속: {e}")
        log_data = None
    
    try:
        # 매물 데이터 수집 (각 프로세스에서 독립적으로 토큰 생성)
        collect_result = collect_by_cortar_no(cortar_no, include_details, max_pages=999)
        
        if collect_result['success']:
            collection_end = datetime.now()
            duration = (collection_end - collection_start).total_seconds()
            collected_count = collect_result['count']
            json_filepath = collect_result['filepath']
            
            print(f"✅ [{mp.current_process().name}] {dong_name} 수집 완료 (소요시간: {duration:.1f}초, {collected_count}개 매물)")
            
            # JSON 파일을 Supabase에 저장
            print(f"💾 [{mp.current_process().name}] Supabase 저장 시작: {json_filepath}")
            from json_to_supabase import process_json_file
            
            supabase_result = process_json_file(json_filepath, cortar_no)
            
            if supabase_result['success']:
                print(f"✅ [{mp.current_process().name}] Supabase 저장 완료: {supabase_result['count']}개 매물")
                
                # 성공 로그 업데이트
                if log_data:
                    try:
                        log_data.update({
                            'status': 'completed',
                            'completed_at': collection_end.isoformat(),
                            'total_collected': collected_count
                        })
                        helper.log_collection(log_data)
                    except Exception as e:
                        print(f"⚠️ [{mp.current_process().name}] 성공 로그 업데이트 실패: {e}")
                
                return {
                    'success': True,
                    'dong_name': dong_name,
                    'duration': duration,
                    'collected_count': collected_count,
                    'supabase_count': supabase_result['count'],
                    'supabase_stats': supabase_result['stats'],
                    'json_filepath': json_filepath,
                    'process_name': mp.current_process().name
                }
            else:
                print(f"❌ [{mp.current_process().name}] Supabase 저장 실패: {supabase_result.get('message', 'Unknown')}")
                
                # 부분 성공 로그 (수집은 성공, DB 저장 실패)
                if log_data:
                    try:
                        log_data.update({
                            'status': 'completed',
                            'completed_at': collection_end.isoformat(),
                            'total_collected': collected_count,
                            'error_message': f"Supabase 저장 실패: {supabase_result.get('error', 'Unknown')}"
                        })
                        helper.log_collection(log_data)
                    except Exception as e:
                        print(f"⚠️ [{mp.current_process().name}] 부분성공 로그 업데이트 실패: {e}")
                
                return {
                    'success': False,
                    'dong_name': dong_name,
                    'duration': duration,
                    'collected_count': collected_count,
                    'error': f"Supabase 저장 실패: {supabase_result.get('error', 'Unknown')}",
                    'json_filepath': json_filepath,
                    'process_name': mp.current_process().name
                }
        else:
            print(f"❌ [{mp.current_process().name}] {dong_name} 수집 실패")
            
            # 실패 로그 업데이트
            if log_data:
                try:
                    log_data.update({
                        'status': 'failed',
                        'completed_at': datetime.now().isoformat(),
                        'error_message': '수집 실패'
                    })
                    helper.log_collection(log_data)
                except Exception as e:
                    print(f"⚠️ [{mp.current_process().name}] 실패 로그 업데이트 실패: {e}")
            
            return {
                'success': False,
                'dong_name': dong_name,
                'error': '수집 실패',
                'process_name': mp.current_process().name
            }
            
    except Exception as e:
        print(f"❌ [{mp.current_process().name}] {dong_name} 수집 중 오류: {e}")
        
        # 오류 로그 업데이트
        if log_data:
            try:
                log_data.update({
                    'status': 'failed',
                    'completed_at': datetime.now().isoformat(),
                    'error_message': str(e)
                })
                helper.log_collection(log_data)
            except Exception as log_e:
                print(f"⚠️ [{mp.current_process().name}] 오류 로그 업데이트 실패: {log_e}")
        
        return {
            'success': False,
            'dong_name': dong_name,
            'error': str(e),
            'process_name': mp.current_process().name
        }

def main():
    """강남구 전체 동 병렬 수집 메인 함수"""
    print("🚀 강남구 전체 동 병렬 자동 수집 시작")
    print("=" * 80)
    
    # 수집 옵션
    include_details = True  # 상세정보 포함 (기본값 변경)
    max_workers = 1  # VM 성능 고려하여 순차 처리 (기본값: 1개)
    
    # 명령행 인자 처리
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'false':
            include_details = False
            print("⚡ 기본 정보만 수집 모드 (속도 최적화)")
        elif sys.argv[1].isdigit():
            max_workers = int(sys.argv[1])
            print(f"🔄 병렬 프로세스 수: {max_workers}개")
    
    if len(sys.argv) > 2:
        if sys.argv[2].lower() == 'false':
            include_details = False
            print("⚡ 기본 정보만 수집 모드 (속도 최적화)")
        elif sys.argv[2].isdigit():
            max_workers = int(sys.argv[2])
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
    
    # ProcessPoolExecutor 사용하여 병렬 처리
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
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
                executor.shutdown(wait=True)
                break
                
            completed_count += 1
            area = future_to_area[future]
            
            try:
                result = future.result()
                results.append(result)
                
                print(f"\n📊 전체 진행률: {completed_count}/{total_areas} ({completed_count/total_areas*100:.1f}%)")
                
                if result['success']:
                    success_count += 1
                    print(f"✅ 성공: {result['dong_name']} ({result.get('duration', 0):.1f}초) - {result.get('process_name', 'Unknown')}")
                else:
                    print(f"❌ 실패: {result['dong_name']} - {result.get('error', 'Unknown')} - {result.get('process_name', 'Unknown')}")
                    
            except Exception as e:
                print(f"❌ {area['dong_name']} 처리 중 예외 발생: {e}")
                results.append({
                    'success': False,
                    'dong_name': area['dong_name'],
                    'error': f"처리 중 예외: {e}"
                })
    
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
    print(f"  - 평균 처리 시간: {total_duration/max_workers/60:.1f}분/프로세스")
    
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
            'success_rate': success_count/total_areas*100,
            'avg_processing_time_per_worker': total_duration/max_workers
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