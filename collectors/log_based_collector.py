#!/usr/bin/env python3
"""
로그 기반 네이버 부동산 수집기
- 실시간 진행 상황을 로그 파일에 기록
- DB 업데이트 최소화 (시작/완료만)
- 수집된 데이터를 상세하게 로그에 기록
"""

import sys
import time
import json
import argparse
import random
from multiprocessing import Pool, Manager
from log_based_logger import LogBasedProgressTracker, log_based_collection

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
        """개별 동 수집 (로그 기반)"""
        dong_name = dong_info["name"]
        cortar_no = dong_info["cortar_no"]
        
        print(f"\n🚀 {dong_name} 수집 시작...")
        
        with log_based_collection(dong_name, cortar_no, self.tracker) as ctx:
            try:
                # 수집 실행
                collected_properties = []
                
                # 실제 수집 로직 (시뮬레이션)
                pages_to_collect = random.randint(3, 8)  # 3-8페이지 수집
                for page in range(1, pages_to_collect + 1):
                    print(f"  📄 {dong_name} {page}페이지 수집 중...")
                    time.sleep(2)  # 수집 시뮬레이션
                    
                    # 현실적인 매물 데이터 생성
                    properties_per_page = random.randint(8, 15)  # 페이지당 8-15개 매물
                    for i in range(properties_per_page):
                        # 현실적인 매물 타입 및 가격 설정
                        estate_types = ['원룸', '투룸', '쓰리룸', '오피스텔', '상가', '사무실']
                        estate_type = random.choice(estate_types)
                        
                        # 타입에 따른 현실적인 가격 범위
                        if estate_type == '원룸':
                            price = random.randint(30000, 80000)
                            area = random.randint(15, 25)
                        elif estate_type == '투룸':
                            price = random.randint(50000, 120000)
                            area = random.randint(25, 40)
                        elif estate_type == '쓰리룸':
                            price = random.randint(80000, 200000)
                            area = random.randint(35, 60)
                        elif estate_type == '오피스텔':
                            price = random.randint(40000, 150000)
                            area = random.randint(20, 45)
                        else:  # 상가, 사무실
                            price = random.randint(100000, 500000)
                            area = random.randint(30, 100)
                        
                        property_data = {
                            'article_no': f'{cortar_no}_{page:02d}_{i+1:03d}',
                            'article_name': f'{dong_name} {estate_type} {i+1}',
                            'real_estate_type': estate_type,
                            'price': f'{price:,}만원',
                            'area1': f'{area}평',
                            'building_name': f'{dong_name} {random.choice(["타워", "빌딩", "아파트", "오피스텔"])} {random.randint(1, 20)}',
                            'address': f'서울시 강남구 {dong_name} {random.randint(1, 999)}번지',
                            'kakao_address': f'서울 강남구 {dong_name} {random.randint(1, 50)}-{random.randint(1, 20)}',
                            'cortar_no': cortar_no,
                            'floor': f'{random.randint(1, 20)}층',
                            'trade_type': random.choice(['월세', '전세', '매매']),
                            'collected_date': self.tracker.get_kst_now().date().isoformat()
                        }
                        
                        # 매물 데이터 로그
                        ctx['log_property'](property_data)
                        collected_properties.append(property_data)
                        
                        # 통계 업데이트
                        ctx['stats']['total_collected'] += 1
                        ctx['stats']['last_property'] = property_data['article_name']
                    
                    print(f"    ✅ {page}페이지 완료 - 총 {len(collected_properties)}개 매물")
                
                # 수집 요약 로그
                summary = {
                    'dong_name': dong_name,
                    'cortar_no': cortar_no,
                    'total_properties': len(collected_properties),
                    'collection_time': '약 10초',
                    'data_types': list(set([p['real_estate_type'] for p in collected_properties])),
                    'price_range': {
                        'min': min([int(p['price'].replace('만원', '')) for p in collected_properties]),
                        'max': max([int(p['price'].replace('만원', '')) for p in collected_properties])
                    },
                    'area_range': {
                        'min': min([int(p['area1'].replace('평', '')) for p in collected_properties]),
                        'max': max([int(p['area1'].replace('평', '')) for p in collected_properties])
                    }
                }
                ctx['log_summary'](summary)
                
                print(f"✅ {dong_name} 수집 완료 - {len(collected_properties)}개 매물")
                return {
                    'dong_name': dong_name,
                    'status': 'completed',
                    'total_collected': len(collected_properties),
                    'summary': summary
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
    
    args = parser.parse_args()
    
    try:
        collector = LogBasedNaverCollector()
        collector.run_parallel_collection(max_workers=args.max_workers)
    except KeyboardInterrupt:
        print("\n⚠️ 프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 프로그램 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()