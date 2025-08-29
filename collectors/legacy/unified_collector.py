#!/usr/bin/env python3
"""
통합 수집기 (UnifiedCollector)
- JSON 수집 + DB 저장 + 모니터링을 한 번에 처리
- 데이터 매칭 문제 해결
- 안전한 삭제 로직 적용
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import sys

# 상대 경로로 모듈 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fixed_naver_collector_v2_optimized import collect_by_cortar_no
from json_to_db_converter import convert_json_data_to_properties
from supabase_client import SupabaseHelper

class UnifiedCollector:
    """통합 수집기 - 수집부터 DB 저장까지 원스톱 처리"""
    
    def __init__(self):
        self.helper = SupabaseHelper()
        self.results_dir = "results"
        os.makedirs(self.results_dir, exist_ok=True)
        
    def collect_and_save(self, cortar_no: str, region_name: str = "") -> Dict:
        """
        매물 수집부터 DB 저장까지 원스톱 처리
        
        Args:
            cortar_no: 행정구역 코드
            region_name: 지역명 (로깅용)
            
        Returns:
            Dict: 수집 및 저장 결과
        """
        
        print(f"\n🚀 통합 수집 시작: {region_name} ({cortar_no})")
        print("=" * 50)
        
        try:
            # 1단계: 기존 데이터 확인
            print("\n📊 1단계: 기존 데이터 현황 조회")
            existing_count = self.helper.get_property_count_by_region(cortar_no)
            print(f"   기존 매물 수: {existing_count}개")
            
            # 2단계: JSON 수집
            print("\n🔍 2단계: 네이버 매물 수집")
            collection_result = collect_by_cortar_no(cortar_no, region_name)
            
            if not collection_result.get('success', False):
                return {
                    'success': False,
                    'error': '매물 수집 실패',
                    'details': collection_result
                }
                
            json_path = collection_result.get('file_path')
            if not json_path or not os.path.exists(json_path):
                return {
                    'success': False,
                    'error': 'JSON 파일 생성 실패',
                    'details': collection_result
                }
                
            # 3단계: JSON 데이터 로드
            print("\n📋 3단계: JSON 데이터 로드 및 변환")
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            # 4단계: DB 형식으로 변환
            db_properties = convert_json_data_to_properties(json_data, cortar_no)
            collected_count = len(db_properties)
            print(f"   변환된 매물: {collected_count}개")
            
            if collected_count == 0:
                return {
                    'success': False,
                    'error': '변환된 매물이 없음',
                    'json_path': json_path
                }
                
            # 5단계: 개선된 DB 저장 (데이터 매칭 문제 해결)
            print("\n💾 5단계: 안전한 DB 저장")
            save_result = self.helper.safe_save_converted_properties(db_properties, cortar_no)
            
            # 6단계: 결과 요약
            print("\n📈 6단계: 수집 결과 요약")
            final_count = self.helper.get_property_count_by_region(cortar_no)
            
            result = {
                'success': True,
                'region_name': region_name,
                'cortar_no': cortar_no,
                'json_path': json_path,
                'existing_properties': existing_count,
                'collected_properties': collected_count,
                'final_properties': final_count,
                'save_stats': save_result,
                'collection_time': datetime.now().isoformat()
            }
            
            print(f"✅ 통합 수집 완료!")
            print(f"   기존: {existing_count}개 → 수집: {collected_count}개 → 최종: {final_count}개")
            
            return result
            
        except Exception as e:
            print(f"❌ 통합 수집 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'region_name': region_name,
                'cortar_no': cortar_no
            }
    
    def safe_save_to_database(self, db_properties: List[Dict], cortar_no: str, region_name: str = "") -> Dict:
        """
        안전한 DB 저장 (데이터 매칭 문제 해결)
        
        기존 문제점:
        - 새로 수집된 매물과 기존 매물의 매칭이 제대로 되지 않음
        - 기존 매물이 "미발견"으로 처리되어 삭제 예약됨
        
        해결 방안:
        - 수집된 매물의 article_no 리스트를 정확히 구성
        - 업서트(upsert) 로직 강화
        - 삭제 로직을 더욱 신중하게 처리
        """
        
        print(f"🔒 안전한 저장 시작: {region_name}")
        
        try:
            # 수집된 매물들의 article_no 추출
            collected_article_nos = set()
            valid_properties = []
            
            for prop in db_properties:
                article_no = prop.get('article_no')
                if article_no:
                    collected_article_nos.add(str(article_no))
                    valid_properties.append(prop)
            
            print(f"   유효한 매물: {len(valid_properties)}개")
            print(f"   Article No 세트 크기: {len(collected_article_nos)}")
            
            if not valid_properties:
                return {'success': False, 'error': '유효한 매물이 없음'}
            
            # 배치 크기로 나누어 처리 (메모리 효율성)
            batch_size = 50
            total_inserted = 0
            total_updated = 0
            
            for i in range(0, len(valid_properties), batch_size):
                batch = valid_properties[i:i+batch_size]
                
                print(f"   배치 {i//batch_size + 1} 처리 중... ({len(batch)}개)")
                
                # 배치별 upsert 실행
                batch_result = self.helper.upsert_properties_batch(batch)
                
                if batch_result.get('success'):
                    total_inserted += batch_result.get('inserted', 0)
                    total_updated += batch_result.get('updated', 0)
                else:
                    print(f"⚠️ 배치 저장 실패: {batch_result.get('error', '알 수 없는 오류')}")
            
            print(f"   저장 완료: 신규 {total_inserted}개, 업데이트 {total_updated}개")
            
            # 개선된 삭제 로직 - 매우 신중하게 처리
            print(f"\n🧹 안전한 삭제 로직 실행")
            deletion_result = self.safe_mark_missing_properties(collected_article_nos, cortar_no)
            
            return {
                'success': True,
                'inserted': total_inserted,
                'updated': total_updated,
                'deletion_stats': deletion_result,
                'total_processed': len(valid_properties)
            }
            
        except Exception as e:
            print(f"❌ 안전한 저장 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def safe_mark_missing_properties(self, collected_article_nos: set, cortar_no: str) -> Dict:
        """
        개선된 누락 매물 처리 로직
        
        기존 문제점:
        - 수집된 데이터와 DB 데이터의 매칭이 부정확
        - 정상 매물이 "미발견"으로 잘못 처리됨
        
        개선 사항:
        - 더 엄격한 매칭 조건
        - 7일 유예 기간 (기존 3일에서 연장)
        - 상세한 로깅으로 문제 추적 가능
        """
        
        print(f"🔍 누락 매물 분석 시작 (수집된 매물: {len(collected_article_nos)}개)")
        
        try:
            # 해당 지역의 활성 매물 조회
            active_properties = self.helper.get_active_properties_by_region(cortar_no)
            active_count = len(active_properties)
            
            print(f"   DB 활성 매물: {active_count}개")
            
            # 매칭되지 않은 매물 찾기
            missing_properties = []
            matched_count = 0
            
            for prop in active_properties:
                article_no = str(prop.get('article_no', ''))
                
                if article_no in collected_article_nos:
                    matched_count += 1
                else:
                    missing_properties.append(prop)
            
            print(f"   매칭된 매물: {matched_count}개")
            print(f"   누락 의심 매물: {len(missing_properties)}개")
            
            # 누락 의심 매물들에 대해 신중한 처리
            marked_missing = 0
            scheduled_deletion = 0
            
            cutoff_date = date.today() - timedelta(days=7)  # 7일 유예 기간
            
            for prop in missing_properties:
                article_no = prop.get('article_no')
                last_seen = prop.get('last_seen_date')
                
                # last_seen_date가 없거나 7일 이상 된 경우만 처리
                if not last_seen:
                    # 처음 누락되는 경우 - 현재 날짜로 last_seen 설정
                    self.helper.update_property_last_seen(article_no, date.today())
                    marked_missing += 1
                    print(f"   🔄 누락 표시: {article_no} (첫 번째 누락)")
                    
                elif isinstance(last_seen, str):
                    try:
                        last_seen_date = datetime.strptime(last_seen, '%Y-%m-%d').date()
                    except:
                        last_seen_date = date.today()
                else:
                    last_seen_date = last_seen
                
                # 7일 이상 누락된 경우만 삭제 예약
                if last_seen_date < cutoff_date:
                    days_missing = (date.today() - last_seen_date).days
                    
                    # 삭제 실행
                    delete_result = self.helper.soft_delete_property(article_no, days_missing)
                    if delete_result:
                        scheduled_deletion += 1
                        print(f"   🗑️ 삭제 처리: {article_no} ({days_missing}일 미발견)")
                else:
                    days_missing = (date.today() - last_seen_date).days
                    print(f"   ⏳ 삭제 유예: {article_no} ({days_missing}일 미발견, 7일 대기 중)")
            
            result = {
                'active_properties': active_count,
                'matched_properties': matched_count,
                'missing_suspected': len(missing_properties),
                'marked_missing': marked_missing,
                'scheduled_deletion': scheduled_deletion
            }
            
            print(f"✅ 누락 처리 완료: 누락표시 {marked_missing}개, 삭제 {scheduled_deletion}개")
            
            return result
            
        except Exception as e:
            print(f"❌ 누락 처리 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def health_check(self, cortar_no: str) -> Dict:
        """수집 전후 헬스 체크"""
        
        try:
            # 기본 통계
            total_count = self.helper.get_property_count_by_region(cortar_no)
            active_count = len(self.helper.get_active_properties_by_region(cortar_no))
            
            # 최근 삭제 현황
            recent_deletions = self.helper.get_recent_deletions(days=7)
            deletion_count = len([d for d in recent_deletions if d.get('cortar_no') == cortar_no])
            
            # 데이터 품질 체크
            quality_score = self.calculate_data_quality(cortar_no)
            
            return {
                'cortar_no': cortar_no,
                'total_properties': total_count,
                'active_properties': active_count,
                'recent_deletions_7d': deletion_count,
                'data_quality_score': quality_score,
                'health_status': 'healthy' if quality_score > 0.8 else 'warning',
                'check_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'cortar_no': cortar_no
            }
    
    def calculate_data_quality(self, cortar_no: str) -> float:
        """데이터 품질 점수 계산 (0.0 ~ 1.0)"""
        
        try:
            properties = self.helper.get_active_properties_by_region(cortar_no)
            if not properties:
                return 0.0
            
            total_score = 0.0
            count = len(properties)
            
            for prop in properties:
                score = 0.0
                
                # 필수 필드 존재 여부 (40%)
                if prop.get('article_name'): score += 0.1
                if prop.get('price'): score += 0.1
                if prop.get('area1'): score += 0.1
                if prop.get('address_road'): score += 0.1
                
                # 위치 정보 정확성 (30%)
                if prop.get('latitude') and prop.get('longitude'): score += 0.3
                
                # 상세 정보 완전성 (30%)
                if prop.get('floor_info'): score += 0.1
                if prop.get('direction'): score += 0.1
                if prop.get('details'): score += 0.1
                
                total_score += score
            
            return round(total_score / count, 3)
            
        except Exception:
            return 0.0

def test_unified_collector():
    """통합 수집기 테스트"""
    
    print("🧪 통합 수집기 테스트")
    print("=" * 40)
    
    collector = UnifiedCollector()
    
    # 테스트 대상: 역삼동
    test_cortar_no = "1168010100"
    test_region_name = "역삼동"
    
    # 수집 전 헬스 체크
    print("\n📊 수집 전 상태 확인")
    pre_health = collector.health_check(test_cortar_no)
    print(f"   기존 매물: {pre_health.get('active_properties', 0)}개")
    print(f"   품질 점수: {pre_health.get('data_quality_score', 0.0)}")
    
    # 통합 수집 실행
    result = collector.collect_and_save(test_cortar_no, test_region_name)
    
    if result.get('success'):
        print(f"\n✅ 테스트 성공!")
        print(f"   JSON 파일: {result.get('json_path')}")
        print(f"   처리 결과: {result.get('save_stats')}")
    else:
        print(f"\n❌ 테스트 실패: {result.get('error')}")
    
    # 수집 후 헬스 체크
    print("\n📈 수집 후 상태 확인")
    post_health = collector.health_check(test_cortar_no)
    print(f"   최종 매물: {post_health.get('active_properties', 0)}개")
    print(f"   품질 점수: {post_health.get('data_quality_score', 0.0)}")

if __name__ == "__main__":
    test_unified_collector()