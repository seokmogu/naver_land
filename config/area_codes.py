#!/usr/bin/env python3
"""
지역 코드 설정 파일
네이버 부동산 수집용 지역별 코드 관리
사용자 제공 정확한 강남구 동별 코드 (2025-09-04 수정)
"""

# 우선순위 점수 매핑
PRIORITY_SCORES = {
    '역삼동': 30, '삼성동': 26, '논현동': 23, '대치동': 22, '신사동': 22,
    '압구정동': 20, '청담동': 18, '도곡동': 18, '개포동': 17, '수서동': 12,
    '일원동': 11, '자곡동': 8, '세곡동': 6, '율현동': 5
}

# 강남구 지역 코드 설정 (사용자 제공 정확한 코드)
GANGNAM_AREAS = [
    # 정확한 네이버 부동산 코드 (2025-09-04 검증)
    {'name': '역삼동', 'code': '1168010100', 'priority': 30},
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

# 전체 지역 코드 맵 (사용자 제공 정확한 코드)
AREA_CODE_MAP = {
    '역삼동': '1168010100',
    '개포동': '1168010300',
    '청담동': '1168010400',
    '삼성동': '1168010500',
    '대치동': '1168010600',
    '신사동': '1168010700',
    '논현동': '1168010800',
    '압구정동': '1168011000',
    '세곡동': '1168011100',
    '자곡동': '1168011200',
    '율현동': '1168011300',
    '일원동': '1168011400',
    '수서동': '1168011500',
    '도곡동': '1168011800',
}

def get_gangnam_areas():
    """강남구 전체 지역 코드 리스트 반환 (우선순위 순서)"""
    return GANGNAM_AREAS

def get_all_priority_areas():
    """전체 지역을 우선순위 순서로 반환 (모든 지역이 강남구)"""
    return sorted(GANGNAM_AREAS, key=lambda x: x['priority'], reverse=True)

def get_high_priority_areas(min_score: int = 20):
    """높은 우선순위 지역만 반환 (기본 20점 이상)"""
    all_areas = get_all_priority_areas()
    return [area for area in all_areas if area['priority'] >= min_score]

def get_area_code(area_name: str) -> str:
    """지역명으로 코드 검색"""
    return AREA_CODE_MAP.get(area_name)

def get_area_priority(area_name: str) -> int:
    """지역명으로 우선순위 점수 검색"""
    return PRIORITY_SCORES.get(area_name, 0)

def get_all_areas():
    """전체 지역 코드 맵 반환"""
    return AREA_CODE_MAP