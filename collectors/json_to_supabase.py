#!/usr/bin/env python3
"""
JSON 파일을 Supabase properties 테이블에 저장하는 모듈
"""

import json
import os
from typing import List, Dict, Optional
from supabase_client import SupabaseHelper

def parse_property_json(json_filepath: str) -> List[Dict]:
    """JSON 파일을 파싱하여 매물 리스트 반환"""
    if not os.path.exists(json_filepath):
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_filepath}")
        return []
    
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 메타데이터와 매물 리스트 분리
        if isinstance(data, dict):
            properties = data.get('매물목록', [])
            metadata = {k: v for k, v in data.items() if k != '매물목록'}
        elif isinstance(data, list):
            properties = data
            metadata = {}
        else:
            print(f"❌ 알 수 없는 JSON 형식: {type(data)}")
            return []
        
        print(f"📊 JSON 파싱 완료: {len(properties)}개 매물, 메타데이터: {len(metadata)}개 항목")
        return properties
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return []

def save_properties_to_supabase(properties: List[Dict], cortar_no: str) -> Dict:
    """매물 리스트를 Supabase에 저장"""
    if not properties:
        print("⚠️ 저장할 매물이 없습니다.")
        return {'success': False, 'count': 0}
    
    try:
        helper = SupabaseHelper()
        
        # SupabaseHelper의 save_properties 메소드 사용
        # (이미 가격 변동 추적, 통계 생성 등이 구현되어 있음)
        stats = helper.save_properties(properties, cortar_no)
        
        print(f"✅ Supabase 저장 완료:")
        print(f"  - 신규 매물: {stats['new_count']}개")
        print(f"  - 가격 변동: {stats['updated_count']}개")
        print(f"  - 삭제 매물: {stats['removed_count']}개")
        print(f"  - 총 저장량: {stats['total_saved']}개")
        
        return {
            'success': True,
            'count': stats['total_saved'],
            'stats': stats
        }
        
    except Exception as e:
        print(f"❌ Supabase 저장 실패: {e}")
        return {'success': False, 'count': 0, 'error': str(e)}

def save_daily_stats_to_supabase(properties: List[Dict], cortar_no: str, save_stats: Dict):
    """일별 통계를 Supabase에 저장"""
    try:
        from datetime import date
        helper = SupabaseHelper()
        
        helper.save_daily_stats(date.today(), cortar_no, properties, save_stats)
        print("✅ 일별 통계 저장 완료")
        
    except Exception as e:
        print(f"⚠️ 일별 통계 저장 실패: {e}")

def process_json_file(json_filepath: str, cortar_no: str) -> Dict:
    """JSON 파일 전체 처리 (파싱 + Supabase 저장)"""
    print(f"📁 JSON 파일 처리 시작: {json_filepath}")
    
    # 1. JSON 파싱
    properties = parse_property_json(json_filepath)
    if not properties:
        return {'success': False, 'count': 0, 'message': 'JSON 파싱 실패 또는 빈 데이터'}
    
    # 2. Supabase 저장
    save_result = save_properties_to_supabase(properties, cortar_no)
    
    if save_result['success']:
        # 3. 일별 통계 저장
        save_daily_stats_to_supabase(properties, cortar_no, save_result['stats'])
        
        return {
            'success': True,
            'count': save_result['count'],
            'stats': save_result['stats'],
            'json_filepath': json_filepath
        }
    else:
        return save_result

def main():
    """테스트용 메인 함수"""
    import sys
    
    if len(sys.argv) < 3:
        print("사용법: python3 json_to_supabase.py <JSON파일경로> <cortar_no>")
        print("예시: python3 json_to_supabase.py results/naver_streaming_20250804_203053.json 1168010100")
        sys.exit(1)
    
    json_filepath = sys.argv[1]
    cortar_no = sys.argv[2]
    
    print(f"🚀 JSON → Supabase 저장 시작")
    print(f"📁 파일: {json_filepath}")
    print(f"🏷️ 지역코드: {cortar_no}")
    print("=" * 60)
    
    result = process_json_file(json_filepath, cortar_no)
    
    if result['success']:
        print(f"✅ 전체 처리 완료: {result['count']}개 매물 저장")
        sys.exit(0)
    else:
        print(f"❌ 처리 실패: {result.get('message', result.get('error', 'Unknown'))}")
        sys.exit(1)

if __name__ == "__main__":
    main()