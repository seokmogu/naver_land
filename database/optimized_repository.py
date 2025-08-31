#!/usr/bin/env python3
"""
최적화된 4개 테이블 구조에 맞는 데이터 저장 Repository
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, date
import json
import psycopg2
import os
from dotenv import load_dotenv
from database.supabase_client import supabase_client

load_dotenv()

class OptimizedPropertyRepository:
    def __init__(self):
        self.supabase_client = supabase_client  # 재시도 기능이 있는 클라이언트 래퍼
        self.client = supabase_client.get_client()
        self.pg_conn = None  # PostgreSQL 직접 연결 (UPSERT용)
        self.save_stats = {
            'total_attempts': 0,
            'successful_saves': 0,
            'failed_saves': 0,
            'updates': 0,
            'inserts': 0,
            'history_records': 0,
            'table_errors': {}
        }
    
    def save_property(self, parsed_data: Dict) -> bool:
        """새로운 4개 테이블 구조에 맞춰 매물 저장"""
        self.save_stats['total_attempts'] += 1
        
        try:
            # 1. 메인 매물 테이블 저장
            property_id = self._save_main_property(parsed_data)
            if not property_id:
                self.save_stats['failed_saves'] += 1
                return False
            
            # 2. 관련 테이블들 저장 (병렬 처리 아님, 순차 처리로 오류 추적)
            success_count = 0
            
            # 중개사 정보 저장
            if self._save_realtor_info(property_id, parsed_data):
                success_count += 1
            
            # 편의시설/세금 정보 저장  
            if self._save_facilities_info(property_id, parsed_data):
                success_count += 1
            
            # 사진 정보 저장
            if self._save_photos_info(property_id, parsed_data):
                success_count += 1
            
            self.save_stats['successful_saves'] += 1
            print(f"✅ 매물 {parsed_data.get('article_no')} 저장 완료")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save property {parsed_data.get('article_no')}: {e}")
            self.save_stats['failed_saves'] += 1
            return False
    
    def _save_main_property(self, parsed_data: Dict) -> Optional[int]:
        """naver_properties 테이블에 메인 매물 정보 저장 (UPSERT 방식)"""
        try:
            sections = parsed_data.get('sections', {})
            article_detail = sections.get('articleDetail', {})
            article_price = sections.get('articlePrice', {})  
            article_space = sections.get('articleSpace', {})
            article_floor = sections.get('articleFloor', {})
            
            article_no = parsed_data.get('article_no')
            
            # 거래 유형에 따른 가격 분리
            trade_type = article_detail.get('trade_type', '매매')
            deal_price, warrant_price, rent_price = self._separate_prices_by_trade_type(
                trade_type, article_detail, article_price
            )
            
            property_data = {
                # 기본 식별자
                'article_no': article_no,
                'is_active': True,
                
                # 거래/매물 유형
                'trade_type_name': trade_type,
                'real_estate_type_name': article_detail.get('real_estate_type'),
                
                # 건물 기본 정보 (카카오 API 건물명 우선 사용)
                'building_name': article_detail.get('address_info', {}).get('building_name') or None,  # 카카오 API 실제 건물명만
                'building_use': article_detail.get('building_name'),  # 네이버 API buildingTypeName (건물 유형: 중소형사무실, 대형사무실 등)
                'law_usage': article_detail.get('law_usage'),
                
                # 위치 정보
                'latitude': self._safe_decimal(article_detail.get('latitude')),
                'longitude': self._safe_decimal(article_detail.get('longitude')),
                'exposure_address': article_detail.get('exposure_address'),
                # 카카오 API로 변환한 상세 주소를 detail_address에 저장 (네이버는 상세주소 제공 안함)
                'detail_address': article_detail.get('address_info', {}).get('primary_address'),
                
                # 가격 정보 (거래유형별 분리)
                'deal_price': deal_price,
                'warrant_price': warrant_price,
                'rent_price': rent_price,
                'monthly_management_cost': self._safe_int(article_detail.get('manage_cost')),
                'price_per_area': self._safe_decimal(article_price.get('price_per_area')),
                
                # 면적 정보
                'supply_area': self._safe_decimal(article_space.get('supply_area')),
                'exclusive_area': self._safe_decimal(article_space.get('exclusive_area')),
                'common_area': self._safe_decimal(article_space.get('common_area')),
                
                # 층수 정보
                'total_floor': self._safe_int(article_floor.get('total_floor')),
                'current_floor': self._safe_int(article_floor.get('current_floor')),
                'floor_description': article_floor.get('floor_description'),
                
                # 교통 및 시설
                'walking_to_subway': self._safe_int(article_detail.get('walking_to_subway')),
                'parking_count': self._safe_int(article_detail.get('parking_count')),
                'parking_possible': self._safe_bool(article_detail.get('parking_possible')),
                'elevator_count': self._safe_int(sections.get('articleFacility', {}).get('elevator_count')),
                
                # 입주 정보
                'move_in_type': article_detail.get('move_in_type'),
                'move_in_discussion': self._safe_bool(article_detail.get('move_in_discussion')),
                
                # 기타
                'detail_description': article_detail.get('detail_description'),
                'management_office_tel': article_detail.get('management_office_tel')
            }
            
            # 기존 데이터 조회
            existing = self.client.table('naver_properties').select('*').eq('article_no', article_no).execute()
            
            if existing.data:
                # UPDATE: 기존 매물 업데이트
                existing_data = existing.data[0]
                property_id = existing_data['id']
                
                # 변경사항 감지 및 history 저장
                self._save_change_history(existing_data, property_data, property_id)
                
                # 업데이트 실행
                property_data['last_updated'] = datetime.now().isoformat()
                result = self.client.table('naver_properties').update(property_data).eq('id', property_id).execute()
                
                if result.data:
                    self.save_stats['updates'] += 1
                    print(f"🔄 매물 {article_no} 업데이트 완료")
                    return property_id
            else:
                # INSERT: 새 매물 저장
                result = self.client.table('naver_properties').insert(property_data).execute()
                if result.data:
                    self.save_stats['inserts'] += 1
                    print(f"✨ 새 매물 {article_no} 저장 완료")
                    return result.data[0]['id']
            
        except Exception as e:
            print(f"❌ Failed to save/update main property: {e}")
            self._log_table_error('naver_properties', str(e))
        return None
    
    def _save_realtor_info(self, property_id: int, parsed_data: Dict) -> bool:
        """naver_realtors 테이블에 중개사 정보 저장"""
        try:
            sections = parsed_data.get('sections', {})
            article_realtor = sections.get('articleRealtor', {})
            
            if not article_realtor:
                return True  # 중개사 정보가 없어도 성공으로 처리
            
            realtor_data = {
                'property_id': property_id,
                'office_name': article_realtor.get('office_name'),
                'agent_name': article_realtor.get('agent_name'),
                'phone_number': article_realtor.get('phone_number'),
                'representative_mobile': article_realtor.get('representative_mobile'),
                'office_certified': self._safe_bool(article_realtor.get('office_certified'))
            }
            
            result = self.client.table('naver_realtors').insert(realtor_data).execute()
            return result.data is not None
            
        except Exception as e:
            print(f"❌ Failed to save realtor info: {e}")
            self._log_table_error('naver_realtors', str(e))
            return False
    
    def _save_facilities_info(self, property_id: int, parsed_data: Dict) -> bool:
        """naver_facilities 테이블에 편의시설/세금 정보 저장"""
        try:
            sections = parsed_data.get('sections', {})
            article_facility = sections.get('articleFacility', {})
            article_addition = sections.get('articleAddition', {})
            article_tax = sections.get('articleTax', {})
            
            facilities_data = {
                'property_id': property_id,
                
                # 편의시설 (JSON으로 저장)
                'near_subway': json.dumps(article_facility.get('near_subway', []), ensure_ascii=False),
                'convenience_facilities': json.dumps(article_facility.get('convenience_facilities', []), ensure_ascii=False),
                'security_facilities': json.dumps(article_facility.get('security_facilities', []), ensure_ascii=False),
                
                # 시세 비교 정보
                'same_addr_direct_deal': self._safe_int(article_addition.get('same_address_direct_deal')),
                'same_addr_hash': article_addition.get('same_address_hash'),
                'nearby_sales': json.dumps(article_addition.get('nearby_sales', {}), ensure_ascii=False),
                
                # 세금 정보
                'acquisition_tax': self._safe_int(article_tax.get('acquisition_tax')),
                'brokerage_fee': self._safe_int(article_tax.get('brokerage_fee')),
                'etc_cost': self._safe_int(article_tax.get('etc_cost'))
            }
            
            result = self.client.table('naver_facilities').insert(facilities_data).execute()
            return result.data is not None
            
        except Exception as e:
            print(f"❌ Failed to save facilities info: {e}")
            self._log_table_error('naver_facilities', str(e))
            return False
    
    def _save_photos_info(self, property_id: int, parsed_data: Dict) -> bool:
        """naver_photos 테이블에 사진 정보 저장"""
        try:
            sections = parsed_data.get('sections', {})
            article_photos = sections.get('articlePhotos', {})
            
            photos = article_photos.get('photos', [])
            if not photos:
                return True  # 사진이 없어도 성공으로 처리
            
            # 사진별로 개별 레코드 저장 (image_url이 null이 아닌 것만)
            for photo in photos:
                image_url = photo.get('url')
                if not image_url:  # null, None, 빈 문자열 건너뛰기
                    continue
                    
                photo_data = {
                    'property_id': property_id,
                    'image_url': image_url,
                    'thumbnail_url': photo.get('thumbnail_url'),
                    'description': photo.get('description'),
                    'display_order': self._safe_int(photo.get('order'))
                }
                
                # 재시도 로직 포함된 클라이언트 사용
                retry_client = self.supabase_client.get_client_with_retry()
                result = retry_client.table('naver_photos').insert(photo_data).execute()
                if not result.data:
                    print(f"⚠️ Failed to save one photo for property {property_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to save photos info: {e}")
            self._log_table_error('naver_photos', str(e))
            return False
    
    def _separate_prices_by_trade_type(self, trade_type: str, article_detail: Dict, article_price: Dict) -> tuple:
        """거래 유형에 따라 가격을 적절한 컬럼에 분리"""
        deal_price = None
        warrant_price = None
        rent_price = None
        
        # articlePrice에서 실제 API 필드명으로 가격 정보 추출
        deal_price_raw = article_price.get('deal_price')  # dealPrice -> deal_price (파서에서 변환됨)
        warrant_price_raw = article_price.get('warrant_price')  # warrantPrice -> warrant_price
        rent_price_raw = article_price.get('rent_price')  # rentPrice -> rent_price
        
        if trade_type == '매매':
            # 매매는 deal_price에만 저장
            deal_price = self._safe_int(deal_price_raw)
        elif trade_type == '전세':
            # 전세는 warrant_price에만 저장 (보증금)
            warrant_price = self._safe_int(deal_price_raw or warrant_price_raw)  # 네이버 API는 전세금을 deal_price로 제공
        elif trade_type == '월세':
            # 월세는 warrant_price(보증금)와 rent_price(월세)에 저장
            warrant_price = self._safe_int(warrant_price_raw or deal_price_raw)  # 보증금
            rent_price = self._safe_int(rent_price_raw)  # 월세액
        
        return deal_price, warrant_price, rent_price
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """안전한 정수 변환"""
        try:
            if value is None or value == '':
                return None
            # 쉼표, '만', '원' 등 제거
            str_val = str(value).replace(',', '').replace('만', '').replace('원', '').strip()
            if str_val == '':
                return None
            return int(float(str_val))
        except (ValueError, TypeError):
            return None
    
    def _safe_decimal(self, value: Any) -> Optional[float]:
        """안전한 소수점 변환 (0.0도 유효한 값으로 처리)"""
        try:
            if value is None or value == '':
                return None
            result = float(str(value).replace(',', ''))
            return result  # 0.0도 유효한 값으로 반환
        except (ValueError, TypeError):
            return None
    
    def _safe_bool(self, value: Any) -> bool:
        """안전한 불린 변환"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', 'y', '1', 'on')
        return bool(value) if value is not None else False
    
    def _save_change_history(self, existing_data: Dict, new_data: Dict, property_id: int):
        """변경사항을 history 테이블에 저장"""
        try:
            changes_detected = []
            history_record = {
                'article_no': existing_data['article_no'],
                'property_id': property_id,
                'change_detected_at': datetime.now().isoformat()
            }
            
            # 가격 변경 감지
            price_changed = False
            if existing_data.get('deal_price') != new_data.get('deal_price'):
                history_record['deal_price_before'] = existing_data.get('deal_price')
                history_record['deal_price_after'] = new_data.get('deal_price')
                changes_detected.append(f"매매가: {existing_data.get('deal_price')} → {new_data.get('deal_price')}")
                price_changed = True
            
            if existing_data.get('warrant_price') != new_data.get('warrant_price'):
                history_record['warrant_price_before'] = existing_data.get('warrant_price')
                history_record['warrant_price_after'] = new_data.get('warrant_price')
                changes_detected.append(f"보증금: {existing_data.get('warrant_price')} → {new_data.get('warrant_price')}")
                price_changed = True
            
            if existing_data.get('rent_price') != new_data.get('rent_price'):
                history_record['rent_price_before'] = existing_data.get('rent_price')
                history_record['rent_price_after'] = new_data.get('rent_price')
                changes_detected.append(f"월세: {existing_data.get('rent_price')} → {new_data.get('rent_price')}")
                price_changed = True
            
            # 상태 변경 감지
            if existing_data.get('is_active') != new_data.get('is_active'):
                history_record['is_active_before'] = existing_data.get('is_active')
                history_record['is_active_after'] = new_data.get('is_active')
                changes_detected.append(f"활성상태: {existing_data.get('is_active')} → {new_data.get('is_active')}")
            
            # 입주 정보 변경 감지
            if existing_data.get('move_in_type') != new_data.get('move_in_type'):
                history_record['move_in_type_before'] = existing_data.get('move_in_type')
                history_record['move_in_type_after'] = new_data.get('move_in_type')
                changes_detected.append(f"입주가능일: {existing_data.get('move_in_type')} → {new_data.get('move_in_type')}")
            
            if existing_data.get('move_in_discussion') != new_data.get('move_in_discussion'):
                history_record['move_in_discussion_before'] = existing_data.get('move_in_discussion')
                history_record['move_in_discussion_after'] = new_data.get('move_in_discussion')
                changes_detected.append(f"입주협의: {existing_data.get('move_in_discussion')} → {new_data.get('move_in_discussion')}")
            
            # 층수 변경 감지
            if existing_data.get('current_floor') != new_data.get('current_floor'):
                history_record['floor_before'] = existing_data.get('current_floor')
                history_record['floor_after'] = new_data.get('current_floor')
                changes_detected.append(f"층수: {existing_data.get('current_floor')} → {new_data.get('current_floor')}")
            
            # 변경사항이 있는 경우만 저장
            if changes_detected:
                history_record['change_type'] = 'price_change' if price_changed else 'info_update'
                history_record['change_summary'] = '; '.join(changes_detected)
                
                # history 테이블에 저장
                result = self.client.table('naver_property_history').insert(history_record).execute()
                if result.data:
                    self.save_stats['history_records'] += 1
                    print(f"📝 변경사항 기록: {history_record['change_summary']}")
            
            # 가격 스냅샷 저장 (매일 1회)
            self._save_price_snapshot(new_data, property_id)
            
        except Exception as e:
            print(f"⚠️ Failed to save history: {e}")
    
    def _save_price_snapshot(self, property_data: Dict, property_id: int):
        """일별 가격 스냅샷 저장"""
        try:
            snapshot_data = {
                'article_no': property_data.get('article_no'),
                'property_id': property_id,
                'snapshot_date': date.today().isoformat(),
                'trade_type_name': property_data.get('trade_type_name'),
                'deal_price': property_data.get('deal_price'),
                'warrant_price': property_data.get('warrant_price'),
                'rent_price': property_data.get('rent_price'),
                'price_per_area': property_data.get('price_per_area'),
                'is_active': property_data.get('is_active', True)
            }
            
            # UPSERT: 오늘 날짜 스냅샷이 있으면 업데이트, 없으면 삽입
            existing_snapshot = self.client.table('naver_price_snapshots').select('id').eq(
                'article_no', property_data.get('article_no')
            ).eq('snapshot_date', date.today().isoformat()).execute()
            
            if existing_snapshot.data:
                # 업데이트
                self.client.table('naver_price_snapshots').update(snapshot_data).eq(
                    'id', existing_snapshot.data[0]['id']
                ).execute()
            else:
                # 삽입
                self.client.table('naver_price_snapshots').insert(snapshot_data).execute()
                
        except Exception as e:
            # 스냅샷 저장 실패는 경고만
            print(f"⚠️ Failed to save price snapshot: {e}")
    
    def _log_table_error(self, table_name: str, error_msg: str):
        """테이블별 에러 로깅"""
        if table_name not in self.save_stats['table_errors']:
            self.save_stats['table_errors'][table_name] = []
        self.save_stats['table_errors'][table_name].append({
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_save_stats(self) -> Dict[str, Any]:
        """저장 통계 반환"""
        return {
            **self.save_stats,
            'success_rate': f"{(self.save_stats['successful_saves'] / max(1, self.save_stats['total_attempts']) * 100):.2f}%"
        }
    
    def print_save_summary(self):
        """저장 요약 출력"""
        stats = self.get_save_stats()
        print(f"\n📊 저장 통계:")
        print(f"   총 시도: {stats['total_attempts']}건")
        print(f"   성공: {stats['successful_saves']}건")
        print(f"   실패: {stats['failed_saves']}건") 
        print(f"   성공률: {stats['success_rate']}")
        print(f"\n📝 상세 내역:")
        print(f"   신규 저장: {stats['inserts']}건")
        print(f"   업데이트: {stats['updates']}건")
        print(f"   변경 이력: {stats['history_records']}건")
        
        if stats['table_errors']:
            print(f"\n❌ 테이블별 에러:")
            for table, errors in stats['table_errors'].items():
                print(f"   {table}: {len(errors)}개 에러")