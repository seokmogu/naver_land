#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
향상된 네이버 수집기 - 직접 DB 저장 버전
json_to_supabase.py 문제를 우회하여 수집 즉시 DB에 안전하게 저장
"""

import sys
import os
from datetime import datetime, date
from fixed_naver_collector_v2_optimized import CachedTokenCollector, collect_by_cortar_no
from json_to_db_converter import convert_json_to_properties
from supabase_client import SupabaseHelper

class EnhancedCollectorWithDirectSave:
    """수집과 DB 저장을 통합한 안전한 수집기"""
    
    def __init__(self):
        self.collector = CachedTokenCollector(use_address_converter=True)
        self.db_helper = None
        self._init_db_helper()
    
    def _init_db_helper(self):
        """DB Helper 초기화"""
        try:
            self.db_helper = SupabaseHelper()
            print("✅ Supabase 연결 성공")
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {str(e)}")
            self.db_helper = None
    
    def collect_and_save_direct(self, cortar_no: str, max_pages: int = 999, test_mode: bool = False):
        """수집 후 즉시 DB에 안전하게 저장"""
        
        print(f"🚀 {cortar_no} 지역 수집 및 직접 저장 시작")
        print(f"📊 최대 페이지: {max_pages}, 테스트 모드: {test_mode}")
        
        if not self.db_helper:
            print("❌ DB 연결이 없어 저장할 수 없습니다")
            return None
        
        # 1. 기존 방식으로 데이터 수집
        print("🔄 데이터 수집 중...")
        collected_result = collect_by_cortar_no(
            cortar_no=cortar_no, 
            include_details=True, 
            max_pages=max_pages
        )
        
        if not collected_result or collected_result.get('total_collected', 0) == 0:
            print("❌ 수집된 데이터가 없습니다")
            return None
        
        json_file = collected_result.get('file_path')
        total_collected = collected_result.get('total_collected', 0)
        
        print(f"✅ 수집 완료: {total_collected}개 매물")
        print(f"📄 JSON 파일: {json_file}")
        
        # 2. JSON 파일을 DB 형식으로 변환
        print("🔄 DB 형식으로 변환 중...")
        db_properties = convert_json_to_properties(json_file, cortar_no)
        
        if not db_properties:
            print("❌ 변환된 데이터가 없습니다")
            return None
        
        print(f"✅ 변환 완료: {len(db_properties)}개 매물")
        
        # 3. 품질 검증
        quality_result = self._validate_quality(db_properties)
        print(f"📊 데이터 품질: {quality_result['quality_grade']}")
        
        if test_mode:
            print("🧪 테스트 모드: DB 저장하지 않고 결과만 반환")
            return {
                'status': 'test_success',
                'collected_count': len(db_properties),
                'quality': quality_result,
                'sample_data': db_properties[0] if db_properties else None
            }
        
        # 4. 품질이 너무 낮으면 저장 중단
        if quality_result['quality_score'] < 50:
            print(f"⚠️ 품질이 너무 낮습니다 ({quality_result['quality_score']:.1f}%). 저장을 중단합니다.")
            return {
                'status': 'quality_fail',
                'quality': quality_result,
                'collected_count': len(db_properties)
            }
        
        # 5. 안전한 DB 저장 (기존 SupabaseHelper.save_properties 사용하지 않음)
        print("🔄 DB에 안전하게 저장 중...")
        try:
            save_stats = self._safe_save_to_db_only(db_properties, cortar_no)
            
            # 6. 일일 통계 저장
            try:
                daily_stats = {
                    'date': date.today().isoformat(),
                    'cortar_no': cortar_no,
                    'total_collected': len(db_properties),
                    'total_saved': save_stats.get('saved_count', 0),
                    'total_updated': save_stats.get('updated_count', 0),
                    'quality_score': quality_result['quality_score']
                }
                
                # daily_stats 테이블에 저장 (있다면)
                self.db_helper.client.table('daily_stats').insert(daily_stats).execute()
                print("✅ 일일 통계 저장 완료")
                
            except Exception as e:
                print(f"⚠️ 일일 통계 저장 실패: {str(e)}")
            
            print(f"✅ DB 저장 완료: {save_stats}")
            
            return {
                'status': 'success',
                'collected_count': len(db_properties),
                'save_stats': save_stats,
                'quality': quality_result,
                'json_file': json_file
            }
            
        except Exception as e:
            print(f"❌ DB 저장 중 오류: {str(e)}")
            return {
                'status': 'save_error',
                'error': str(e),
                'collected_count': len(db_properties)
            }
    
    def _validate_quality(self, properties):
        """데이터 품질 검증"""
        if not properties:
            return {'quality_score': 0, 'quality_grade': 'F (데이터없음)'}
        
        total = len(properties)
        
        # 필수 필드 검증
        missing_article_no = sum(1 for p in properties if not p.get('article_no'))
        missing_address = sum(1 for p in properties if not p.get('address_road'))
        missing_coords = sum(1 for p in properties 
                           if not p.get('latitude') or not p.get('longitude')
                           or p.get('latitude') == 0 or p.get('longitude') == 0)
        
        # 품질 점수 계산
        address_rate = (total - missing_address) / total * 100
        coord_rate = (total - missing_coords) / total * 100
        data_integrity = (total - missing_article_no) / total * 100
        
        quality_score = (address_rate + coord_rate + data_integrity) / 3
        
        # 등급 매기기
        if quality_score >= 90:
            grade = 'A (우수)'
        elif quality_score >= 80:
            grade = 'B (양호)'
        elif quality_score >= 70:
            grade = 'C (보통)'
        elif quality_score >= 50:
            grade = 'D (개선필요)'
        else:
            grade = 'F (심각)'
        
        return {
            'quality_score': quality_score,
            'quality_grade': grade,
            'address_rate': address_rate,
            'coord_rate': coord_rate,
            'data_integrity': data_integrity,
            'total_count': total
        }
    
    def _safe_save_to_db_only(self, properties, cortar_no):
        """안전한 DB 저장 - 기존 매물 삭제하지 않음"""
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        current_article_nos = []
        
        for prop in properties:
            article_no = prop.get('article_no')
            if not article_no:
                error_count += 1
                continue
                
            current_article_nos.append(article_no)
            
            try:
                # 기존 매물 확인
                existing = self.db_helper.client.table('properties')\
                    .select('article_no')\
                    .eq('article_no', article_no)\
                    .execute()
                
                if existing.data:
                    # 기존 매물 업데이트 (last_seen_date 포함)
                    prop['last_seen_date'] = date.today().isoformat()
                    prop['updated_at'] = datetime.now().isoformat()
                    
                    self.db_helper.client.table('properties')\
                        .update(prop)\
                        .eq('article_no', article_no)\
                        .execute()
                    updated_count += 1
                    
                else:
                    # 신규 매물 삽입
                    self.db_helper.client.table('properties')\
                        .insert(prop)\
                        .execute()
                    saved_count += 1
                    
            except Exception as e:
                print(f"❌ 매물 저장 실패 {article_no}: {str(e)}")
                error_count += 1
        
        # 🔥 중요: 기존 매물을 삭제하지 않음!
        # 안전한 방식: last_seen_date만 업데이트하고 삭제는 별도 프로세스에서 처리
        
        # 기존 매물의 last_seen_date 업데이트 (삭제하지 않음)
        try:
            # 현재 수집된 매물들의 last_seen_date 업데이트
            for article_no in current_article_nos:
                self.db_helper.client.table('properties')\
                    .update({'last_seen_date': date.today().isoformat()})\
                    .eq('article_no', article_no)\
                    .execute()
            
            print(f"✅ last_seen_date 업데이트: {len(current_article_nos)}개 매물")
            
        except Exception as e:
            print(f"⚠️ last_seen_date 업데이트 실패: {str(e)}")
        
        # 🚨 주의: 기존 매물 삭제 로직 완전 비활성화
        # 삭제는 별도의 안전한 프로세스에서만 수행
        
        print(f"💾 저장 결과: 신규 {saved_count}개, 업데이트 {updated_count}개, 오류 {error_count}개")
        
        return {
            'saved_count': saved_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'total_processed': len(properties)
        }

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='향상된 네이버 수집기 - 직접 DB 저장')
    parser.add_argument('cortar_no', help='수집할 지역 코드 (예: 11680102)')
    parser.add_argument('--max-pages', type=int, default=999, help='최대 수집 페이지')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (DB 저장하지 않음)')
    
    args = parser.parse_args()
    
    print("🚀 향상된 네이버 수집기 - 직접 DB 저장 버전")
    print("=" * 60)
    
    # 수집기 생성 및 실행
    collector = EnhancedCollectorWithDirectSave()
    
    result = collector.collect_and_save_direct(
        cortar_no=args.cortar_no,
        max_pages=args.max_pages,
        test_mode=args.test
    )
    
    if result:
        print(f"\n🎯 최종 결과: {result['status']}")
        print(f"📊 수집 개수: {result.get('collected_count', 0)}개")
        
        if 'quality' in result:
            quality = result['quality']
            print(f"📈 품질 점수: {quality['quality_score']:.1f}% ({quality['quality_grade']})")
        
        if result['status'] == 'success':
            save_stats = result.get('save_stats', {})
            print(f"💾 저장 통계: 신규 {save_stats.get('saved_count', 0)}개, 업데이트 {save_stats.get('updated_count', 0)}개")
        
    else:
        print("\n❌ 수집 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()