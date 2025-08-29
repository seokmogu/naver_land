#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최종 안전한 네이버 수집기 - EC2 배포용 v1.1
완전히 안전한 수집 + 선택적 DB 저장
수정: 더욱 강화된 안전성과 에러 처리
"""

import sys
import os
from datetime import datetime, date
from completely_safe_collector import safe_collect_only
from json_to_db_converter import convert_json_to_properties
from supabase_client import SupabaseHelper

class FinalSafeCollector:
    """최종 안전한 수집기 - 삭제 없는 저장"""
    
    def __init__(self):
        self.db_helper = None
        self._init_db_helper()
    
    def _init_db_helper(self):
        """DB Helper 초기화"""
        try:
            self.db_helper = SupabaseHelper()
            print("✅ Supabase 연결 성공")
            
            # 연결 상태 확인
            test_query = self.db_helper.client.table('properties')\
                .select('article_no', count='exact')\
                .limit(1)\
                .execute()
            
            print(f"✅ DB 상태 확인: 테이블 접근 가능")
            
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {str(e)}")
            self.db_helper = None
    
    def collect_and_save_safely(self, cortar_no: str, max_pages: int = 999, 
                               save_to_db: bool = True, test_mode: bool = False):
        """안전한 수집 + 선택적 DB 저장"""
        
        print(f"🛡️ 최종 안전한 수집기 v1.1")
        print(f"🎯 지역: {cortar_no}, 페이지: {max_pages}")
        print(f"💾 DB 저장: {save_to_db}, 테스트: {test_mode}")
        print("⚠️ 기존 매물 삭제 절대 없음!")
        print("=" * 60)
        
        # 사전 검증
        if save_to_db and not self.db_helper:
            print("❌ DB 연결이 필요하지만 연결에 실패했습니다")
            return {
                'status': 'db_connection_fail',
                'error': 'No database connection'
            }
        
        # 1. 완전히 안전한 수집
        print("🔄 1단계: 안전한 데이터 수집...")
        collect_result = safe_collect_only(cortar_no, max_pages)
        
        if not collect_result or not collect_result.get('success'):
            print("❌ 수집 실패")
            return {
                'status': 'collection_fail',
                'error': 'Data collection failed'
            }
        
        json_file = collect_result['file_path']
        total_collected = collect_result['total_collected']
        
        print(f"✅ 수집 완료: {total_collected}개 매물")
        
        if total_collected == 0:
            print("⚠️ 수집된 매물이 없습니다")
            return {
                'status': 'no_data',
                'collected_count': 0,
                'json_file': json_file
            }
        
        # 2. DB 형식으로 변환
        print("🔄 2단계: DB 형식 변환...")
        try:
            db_properties = convert_json_to_properties(json_file, cortar_no)
        except Exception as e:
            print(f"❌ 변환 중 오류: {str(e)}")
            return {
                'status': 'conversion_fail',
                'error': str(e),
                'json_file': json_file
            }
        
        if not db_properties:
            print("❌ 변환 결과 없음")
            return {
                'status': 'conversion_empty',
                'json_file': json_file
            }
        
        print(f"✅ 변환 완료: {len(db_properties)}개 매물")
        
        # 3. 품질 검증
        quality_result = self._validate_quality(db_properties)
        print(f"📊 데이터 품질: {quality_result['quality_grade']} ({quality_result['quality_score']:.1f}%)")
        
        # 품질 상세 정보 출력
        print(f"   📍 주소 완성도: {quality_result['address_rate']:.1f}%")
        print(f"   🌍 좌표 완성도: {quality_result['coord_rate']:.1f}%")
        print(f"   📝 데이터 무결성: {quality_result['data_integrity']:.1f}%")
        
        if test_mode or not save_to_db:
            print("🧪 테스트 모드 또는 DB 저장 비활성화")
            print(f"📄 수집된 JSON 파일: {json_file}")
            
            # 샘플 데이터 출력
            if db_properties:
                sample = db_properties[0]
                print(f"📋 샘플 매물: {sample.get('article_no')} - {sample.get('article_name', 'N/A')[:30]}")
            
            return {
                'status': 'test_success',
                'collected_count': total_collected,
                'converted_count': len(db_properties),
                'quality': quality_result,
                'json_file': json_file,
                'sample_data': db_properties[0] if db_properties else None
            }
        
        # 4. 품질 기준 확인
        if quality_result['quality_score'] < 50:
            print(f"⚠️ 품질이 너무 낮습니다 ({quality_result['quality_score']:.1f}%). 저장을 중단합니다.")
            return {
                'status': 'quality_fail',
                'quality': quality_result,
                'collected_count': len(db_properties),
                'json_file': json_file
            }
        
        # 5. 최종 안전성 확인
        if not self._final_safety_check():
            print("❌ 최종 안전성 검증 실패. 저장을 중단합니다.")
            return {
                'status': 'safety_fail',
                'quality': quality_result,
                'collected_count': len(db_properties)
            }
        
        # 6. 안전한 DB 저장
        print("🔄 3단계: 안전한 DB 저장...")
        try:
            save_stats = self._safe_save_properties_only(db_properties, cortar_no)
            
            if save_stats['total_processed'] == 0:
                print("⚠️ 저장된 매물이 없습니다")
                return {
                    'status': 'save_empty',
                    'save_stats': save_stats,
                    'quality': quality_result
                }
            
            # 7. 일일 통계 저장
            try:
                daily_stats = {
                    'date': date.today().isoformat(),
                    'cortar_no': cortar_no,
                    'total_collected': len(db_properties),
                    'total_saved': save_stats.get('saved_count', 0),
                    'total_updated': save_stats.get('updated_count', 0),
                    'quality_score': quality_result['quality_score'],
                    'collection_source': 'final_safe_collector',
                    'created_at': datetime.now().isoformat()
                }
                
                self.db_helper.client.table('daily_stats').upsert(daily_stats, on_conflict='date,cortar_no').execute()
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
                'collected_count': len(db_properties),
                'quality': quality_result,
                'json_file': json_file
            }
    
    def _validate_quality(self, properties):
        """데이터 품질 검증"""
        if not properties:
            return {'quality_score': 0, 'quality_grade': 'F (데이터없음)'}
        
        total = len(properties)
        missing_article_no = sum(1 for p in properties if not p.get('article_no'))
        missing_address = sum(1 for p in properties if not p.get('address_road'))
        missing_coords = sum(1 for p in properties 
                           if not p.get('latitude') or not p.get('longitude')
                           or p.get('latitude') == 0 or p.get('longitude') == 0)
        
        address_rate = (total - missing_address) / total * 100
        coord_rate = (total - missing_coords) / total * 100
        data_integrity = (total - missing_article_no) / total * 100
        
        quality_score = (address_rate + coord_rate + data_integrity) / 3
        
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
            'total_count': total,
            'missing_fields': {
                'article_no': missing_article_no,
                'address': missing_address,
                'coordinates': missing_coords
            }
        }
    
    def _final_safety_check(self):
        """최종 안전성 검증"""
        try:
            # DB 연결 상태 확인
            if not self.db_helper:
                return False
            
            # 간단한 쿼리로 DB 상태 확인
            test_result = self.db_helper.client.table('properties')\
                .select('article_no', count='exact')\
                .limit(1)\
                .execute()
            
            print(f"🔒 안전성 검증 통과: DB 접근 가능")
            return True
            
        except Exception as e:
            print(f"🚨 안전성 검증 실패: {str(e)}")
            return False
    
    def _safe_save_properties_only(self, properties, cortar_no):
        """
        완전히 안전한 속성만 저장 
        - 기존 매물 절대 삭제하지 않음
        - upsert 방식으로 중복 처리
        - last_seen_date만 업데이트
        """
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        today = date.today().isoformat()
        
        print(f"🔒 안전 저장 모드: {len(properties)}개 매물 처리")
        
        for prop in properties:
            article_no = prop.get('article_no')
            if not article_no:
                error_count += 1
                continue
            
            try:
                # 필수 필드 추가
                prop['last_seen_date'] = today
                prop['updated_at'] = datetime.now().isoformat()
                prop['is_active'] = True  # 강제로 활성 상태 보장
                
                # 기존 매물 확인
                existing = self.db_helper.client.table('properties')\
                    .select('article_no')\
                    .eq('article_no', article_no)\
                    .execute()
                
                if existing.data:
                    # 기존 매물 업데이트 (안전하게)
                    update_fields = {
                        'price': prop.get('price'),
                        'rent_price': prop.get('rent_price'),
                        'last_seen_date': today,
                        'updated_at': datetime.now().isoformat(),
                        'is_active': True  # 활성 상태 보장
                    }
                    
                    self.db_helper.client.table('properties')\
                        .update(update_fields)\
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
        
        # 🔥 중요: 기존 매물 삭제 로직 완전 제거!
        print(f"💾 저장 결과: 신규 {saved_count}개, 업데이트 {updated_count}개, 오류 {error_count}개")
        print("✅ 기존 매물 삭제 절대 안함 (최고 안전 모드)")
        
        return {
            'saved_count': saved_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'total_processed': len(properties)
        }

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='최종 안전한 네이버 수집기 v1.1')
    parser.add_argument('cortar_no', help='수집할 지역 코드 (예: 1168010100)')
    parser.add_argument('--max-pages', type=int, default=999, help='최대 수집 페이지 (기본: 999)')
    parser.add_argument('--no-save', action='store_true', help='DB에 저장하지 않음')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (DB 저장 안함)')
    
    args = parser.parse_args()
    
    print("🛡️ 최종 안전한 네이버 수집기 v1.1")
    print("=" * 60)
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    collector = FinalSafeCollector()
    
    result = collector.collect_and_save_safely(
        cortar_no=args.cortar_no,
        max_pages=args.max_pages,
        save_to_db=not args.no_save and not args.test,
        test_mode=args.test
    )
    
    if result:
        print(f"\n🎯 최종 결과: {result['status']}")
        print(f"📊 수집 개수: {result.get('collected_count', 0)}개")
        
        if 'quality' in result:
            quality = result['quality']
            print(f"📈 품질 점수: {quality['quality_score']:.1f}% ({quality['quality_grade']})")
            print(f"   📍 주소: {quality['address_rate']:.1f}%")
            print(f"   🌍 좌표: {quality['coord_rate']:.1f}%")
            print(f"   📝 무결성: {quality['data_integrity']:.1f}%")
        
        if result['status'] == 'success':
            save_stats = result.get('save_stats', {})
            print(f"💾 저장 통계:")
            print(f"   신규: {save_stats.get('saved_count', 0)}개")
            print(f"   업데이트: {save_stats.get('updated_count', 0)}개")
            print(f"   오류: {save_stats.get('error_count', 0)}개")
            print(f"🛡️ 안전성: 기존 매물 삭제 절대 없음")
        
        if 'json_file' in result:
            print(f"📄 JSON 파일: {result['json_file']}")
        
        if 'error' in result:
            print(f"❌ 오류: {result['error']}")
        
        # 상태별 종료 코드
        if result['status'] in ['success', 'test_success']:
            print(f"\n🎉 {'테스트' if result['status'] == 'test_success' else '실제'} 수집 완료!")
            sys.exit(0)
        elif result['status'] in ['quality_fail', 'no_data']:
            print(f"\n⚠️ 완료되었지만 주의가 필요합니다.")
            sys.exit(1)
        else:
            print(f"\n❌ 수집 실패")
            sys.exit(2)
        
    else:
        print("\n❌ 수집 실패 (결과 없음)")
        sys.exit(3)

if __name__ == "__main__":
    main()