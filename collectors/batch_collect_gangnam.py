#!/usr/bin/env python3
"""
강남구 전체 동 순차 자동 배치 수집 스크립트
우선순위 순서로 모든 동의 매물을 완전 수집 후 Supabase 저장
"""

import sys
import time
import json
from datetime import datetime
from typing import List, Dict
from supabase_client import SupabaseHelper
from fixed_naver_collector import collect_by_cortar_no

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

def collect_and_save_to_supabase(area_info: Dict, include_details: bool = True) -> Dict:
    """단일 동 수집 후 Supabase 저장"""
    dong_name = area_info['dong_name']
    cortar_no = area_info['cortar_no']
    
    print(f"\n{'='*80}")
    print(f"🎯 {dong_name} ({cortar_no}) 수집 시작")
    print(f"📍 중심좌표: {area_info['center_lat']}, {area_info['center_lon']}")
    print(f"🏆 우선순위 점수: {area_info['priority_score']}")
    print(f"{'='*80}")
    
    collection_start = datetime.now()
    
    # 수집 로그 시작
    helper = SupabaseHelper()
    log_data = {
        'gu_name': '강남구',
        'dong_name': dong_name,
        'cortar_no': cortar_no,
        'collection_type': 'property_collection',
        'status': 'started',
        'started_at': collection_start.isoformat()
    }
    helper.log_collection(log_data)
    
    try:
        # 매물 데이터 수집
        collect_result = collect_by_cortar_no(cortar_no, include_details)
        
        if collect_result['success']:
            collection_end = datetime.now()
            duration = (collection_end - collection_start).total_seconds()
            collected_count = collect_result['count']
            json_filepath = collect_result['filepath']
            
            print(f"✅ {dong_name} 수집 완료 (소요시간: {duration:.1f}초, {collected_count}개 매물)")
            
            # JSON 파일을 Supabase에 저장
            print(f"💾 Supabase 저장 시작: {json_filepath}")
            from json_to_supabase import process_json_file
            
            supabase_result = process_json_file(json_filepath, cortar_no)
            
            if supabase_result['success']:
                print(f"✅ Supabase 저장 완료: {supabase_result['count']}개 매물")
                
                # 성공 로그 업데이트
                log_data.update({
                    'status': 'completed',
                    'completed_at': collection_end.isoformat(),
                    'total_collected': collected_count
                })
                helper.log_collection(log_data)
                
                return {
                    'success': True,
                    'dong_name': dong_name,
                    'duration': duration,
                    'collected_count': collected_count,
                    'supabase_count': supabase_result['count'],
                    'supabase_stats': supabase_result['stats'],
                    'json_filepath': json_filepath
                }
            else:
                print(f"❌ Supabase 저장 실패: {supabase_result.get('message', 'Unknown')}")
                
                # 부분 성공 로그 (수집은 성공, DB 저장 실패)
                log_data.update({
                    'status': 'completed',
                    'completed_at': collection_end.isoformat(),
                    'total_collected': collected_count,
                    'error_message': f"Supabase 저장 실패: {supabase_result.get('error', 'Unknown')}"
                })
                helper.log_collection(log_data)
                
                return {
                    'success': False,
                    'dong_name': dong_name,
                    'duration': duration,
                    'collected_count': collected_count,
                    'error': f"Supabase 저장 실패: {supabase_result.get('error', 'Unknown')}",
                    'json_filepath': json_filepath
                }
        else:
            print(f"❌ {dong_name} 수집 실패")
            
            # 실패 로그 업데이트
            log_data.update({
                'status': 'failed',
                'completed_at': datetime.now().isoformat(),
                'error_message': '수집 실패'
            })
            helper.log_collection(log_data)
            
            return {
                'success': False,
                'dong_name': dong_name,
                'error': '수집 실패'
            }
            
    except Exception as e:
        print(f"❌ {dong_name} 수집 중 오류: {e}")
        
        # 오류 로그 업데이트
        log_data.update({
            'status': 'failed',
            'completed_at': datetime.now().isoformat(),
            'error_message': str(e)
        })
        helper.log_collection(log_data)
        
        return {
            'success': False,
            'dong_name': dong_name,
            'error': str(e)
        }

def main():
    """강남구 전체 동 순차 수집 메인 함수"""
    print("🚀 강남구 전체 동 순차 자동 수집 시작")
    print("=" * 80)
    
    # 수집 옵션
    include_details = False  # 상세정보 제외 (속도 최적화)
    batch_size = 5  # 배치 사이즈 (기본값: 5개 동씩 - 속도 최적화)
    
    # 명령행 인자 처리
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'true':
            include_details = True
            print("🔍 상세정보 포함 수집 모드")
        elif sys.argv[1].isdigit():
            batch_size = int(sys.argv[1])
            print(f"📦 배치 사이즈: {batch_size}개 동씩")
    
    if len(sys.argv) > 2:
        if sys.argv[2].lower() == 'true':
            include_details = True
            print("🔍 상세정보 포함 수집 모드")
        elif sys.argv[2].isdigit():
            batch_size = int(sys.argv[2])
            print(f"📦 배치 사이즈: {batch_size}개 동씩")
    
    if not include_details:
        print("⚡ 기본 정보만 수집 모드 (속도 최적화)")
    
    # 강남구 동별 우선순위 목록 가져오기
    areas = get_gangnam_collection_priority()
    total_areas = len(areas)
    
    print(f"\n📋 수집 대상: {total_areas}개 동")
    print(f"📦 배치 사이즈: {batch_size}개 동씩 처리")
    print("🏆 우선순위 순서:")
    for i, area in enumerate(areas, 1):
        print(f"  {i:2d}. {area['dong_name']:8s} (점수: {area['priority_score']:2d}) - {area['cortar_no']}")
    
    # 배치별로 나누어 처리
    batches = [areas[i:i+batch_size] for i in range(0, len(areas), batch_size)]
    total_batches = len(batches)
    
    print(f"\n📦 총 {total_batches}개 배치로 나누어 처리")
    for i, batch in enumerate(batches, 1):
        batch_areas = [area['dong_name'] for area in batch]
        print(f"  배치 {i}: {', '.join(batch_areas)}")
    
    # 자동 실행 (사용자 확인 제거)
    
    # 배치 수집 시작
    batch_start = datetime.now()
    all_results = []
    total_success_count = 0
    
    print(f"\n🚀 배치 수집 시작: {batch_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f"\n📦 배치 {batch_idx}/{total_batches} 시작 ({len(batch)}개 동)")
        print("-" * 60)
        
        batch_results = []
        batch_success = 0
        
        for i, area in enumerate(batch, 1):
            area_idx = (batch_idx - 1) * batch_size + i
            print(f"\n📊 전체 진행률: {area_idx}/{total_areas} ({area_idx/total_areas*100:.1f}%)")
            print(f"📦 배치 내 진행률: {i}/{len(batch)} ({i/len(batch)*100:.1f}%)")
            
            # 동별 수집 실행
            result = collect_and_save_to_supabase(area, include_details)
            batch_results.append(result)
            
            if result['success']:
                batch_success += 1
                total_success_count += 1
                print(f"✅ 성공: {result['dong_name']} ({result.get('duration', 0):.1f}초)")
            else:
                print(f"❌ 실패: {result['dong_name']} - {result.get('error', 'Unknown')}")
            
            # 동 간 대기 (서버 부하 방지) - 속도 최적화
            if i < len(batch):
                print("⏳ 다음 동 수집 전 대기 중... (10초)")
                time.sleep(10)
        
        # 배치 완료 요약
        print(f"\n📦 배치 {batch_idx} 완료: {batch_success}/{len(batch)} 성공")
        all_results.extend(batch_results)
        
        # 배치 간 대기 (메모리 정리 및 안정화) - 속도 최적화
        if batch_idx < total_batches:
            print("⏳ 다음 배치 시작 전 대기 중... (20초)")
            time.sleep(20)
    
    # 배치 수집 완료 요약
    batch_end = datetime.now()
    total_duration = (batch_end - batch_start).total_seconds()
    
    print(f"\n🎯 강남구 전체 수집 완료!")
    print("=" * 80)
    print(f"📊 수집 통계:")
    print(f"  - 전체 동 수: {total_areas}개")
    print(f"  - 성공한 동: {total_success_count}개")
    print(f"  - 실패한 동: {total_areas - total_success_count}개")
    print(f"  - 성공률: {total_success_count/total_areas*100:.1f}%")
    print(f"  - 총 소요시간: {total_duration/60:.1f}분")
    print(f"  - 시작시간: {batch_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 완료시간: {batch_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 배치 수: {total_batches}개 (배치당 {batch_size}개 동)")
    
    # 결과 저장
    timestamp = batch_start.strftime("%Y%m%d_%H%M%S")
    result_file = f"results/batch_collection_gangnam_{timestamp}.json"
    
    batch_summary = {
        'batch_info': {
            'gu_name': '강남구',
            'start_time': batch_start.isoformat(),
            'end_time': batch_end.isoformat(),
            'total_duration_seconds': total_duration,
            'include_details': include_details,
            'batch_size': batch_size,
            'total_batches': total_batches
        },
        'statistics': {
            'total_areas': total_areas,
            'success_count': total_success_count,
            'failed_count': total_areas - total_success_count,
            'success_rate': total_success_count/total_areas*100
        },
        'results': all_results
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(batch_summary, f, ensure_ascii=False, indent=2)
    
    print(f"💾 배치 결과 저장: {result_file}")
    
    if total_success_count == total_areas:
        print("🎉 모든 동 수집 성공!")
        sys.exit(0)
    else:
        print(f"⚠️ {total_areas - total_success_count}개 동 수집 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()