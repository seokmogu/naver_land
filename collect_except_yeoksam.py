#!/usr/bin/env python3
"""
역삼동을 제외한 나머지 지역 수집 스크립트
강남구 전체 지역 중 역삼동을 제외하고 순차 수집
"""

import subprocess
import sys
import time
from datetime import datetime

# 역삼동을 제외한 강남구 전체 지역 (우선순위 순)
AREAS_EXCEPT_YEOKSAM = [
    {'name': '삼성동', 'code': '1168010500', 'priority': 26},
    {'name': '논현동', 'code': '1168010800', 'priority': 23},
    {'name': '대치동', 'code': '1168010600', 'priority': 22},
    {'name': '신사동', 'code': '1168010700', 'priority': 22},
    {'name': '압구정동', 'code': '1168011000', 'priority': 20},
    {'name': '청담동', 'code': '1168010400', 'priority': 18},
    {'name': '도곡동', 'code': '1168011800', 'priority': 18},
    {'name': '개포동', 'code': '1168010300', 'priority': 17},
    {'name': '수서동', 'code': '1168011500', 'priority': 12},
    {'name': '일원동', 'code': '1168011400', 'priority': 11},
    {'name': '자곡동', 'code': '1168011200', 'priority': 8},
    {'name': '세곡동', 'code': '1168011100', 'priority': 6},
    {'name': '율현동', 'code': '1168011300', 'priority': 5},
]

def collect_area(area_info):
    """특정 지역 수집 실행"""
    
    area_name = area_info['name']
    area_code = area_info['code']
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {area_name} 수집 시작")
    print(f"지역 코드: {area_code}, 우선순위: {area_info['priority']}")
    print("-"*40)
    
    # 수집 명령어
    cmd = [
        sys.executable, "main.py",
        "--area", area_code,
        "--max-pages", "100"  # 모든 페이지 수집
    ]
    
    try:
        # 수집 프로세스 실행
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 실시간 출력
        for line in process.stdout:
            print(f"[{area_name}] {line}", end='')
        
        # 프로세스 종료 대기
        return_code = process.wait()
        
        if return_code == 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {area_name} 수집 완료")
            return True
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {area_name} 수집 실패 (종료 코드: {return_code})")
            return False
            
    except Exception as e:
        print(f"{area_name} 수집 중 오류: {e}")
        return False

def main():
    """메인 실행 함수"""
    
    print("="*60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 역삼동 제외 전체 지역 수집 시작")
    print(f"총 {len(AREAS_EXCEPT_YEOKSAM)}개 지역")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    
    try:
        # 각 지역 순차 수집
        for idx, area in enumerate(AREAS_EXCEPT_YEOKSAM, 1):
            print(f"\n진행률: {idx}/{len(AREAS_EXCEPT_YEOKSAM)}")
            
            if collect_area(area):
                success_count += 1
            else:
                fail_count += 1
            
            # 지역 간 잠시 대기 (API 부하 방지)
            if idx < len(AREAS_EXCEPT_YEOKSAM):
                print("다음 지역 수집 대기 중...")
                time.sleep(5)
        
        # 최종 결과
        print("\n" + "="*60)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 전체 수집 완료")
        print(f"성공: {success_count}개 지역, 실패: {fail_count}개 지역")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n사용자 중단 요청. 수집을 종료합니다...")
        print(f"완료: {success_count}개 지역, 실패: {fail_count}개 지역")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n예기치 않은 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()