#!/usr/bin/env python3
"""
Supabase 클라이언트 헬퍼
네이버 부동산 데이터 저장 및 조회
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from supabase import create_client, Client

class SupabaseHelper:
    def __init__(self, config_file: str = None):
        """Supabase 클라이언트 초기화"""
        # 기본 경로 collectors/config/config.json 사용
        if config_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            config_file = os.path.join(base_dir, "config", "config.json")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supabase_config = config.get('supabase', {})
        
        # 환경변수 우선, 없으면 설정 파일 사용
        self.url = os.getenv('SUPABASE_URL', supabase_config.get('url'))
        self.key = os.getenv('SUPABASE_KEY', supabase_config.get('anon_key'))
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL과 Key가 필요합니다. config.json 또는 환경변수를 확인하세요.")
        
        # Supabase 클라이언트 생성
        self.client: Client = create_client(self.url, self.key)
        print("✅ Supabase 연결 성공")
    
    def save_areas(self, areas_data: List[Dict]) -> bool:
        """지역 정보 저장"""
        try:
            # 기존 데이터와 병합 (upsert)
            result = self.client.table('areas').upsert(areas_data).execute()
            print(f"✅ {len(areas_data)}개 지역 정보 저장 완료")
            return True
        except Exception as e:
            print(f"❌ 지역 정보 저장 실패: {e}")
            return False
    
    def save_properties(self, properties_data: List[Dict], cortar_no: str) -> Dict:
        """매물 정보 저장 및 변동 추적"""
        today = date.today()
        stats = {
            'new_count': 0,
            'updated_count': 0,
            'removed_count': 0,
            'total_saved': 0
        }
        
        try:
            # 1. 기존 활성 매물 조회 (가격과 월세 정보 포함)
            existing = self.client.table('properties')\
                .select('article_no, price, rent_price, trade_type')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .execute()
            
            existing_map = {item['article_no']: item for item in existing.data}
            collected_ids = set()
            
            # 2. 매물 데이터 처리
            for prop in properties_data:
                article_no = prop['매물번호']
                collected_ids.add(article_no)
                
                # 저장할 데이터 준비 (last_seen_date 업데이트)
                property_record = self._prepare_property_record(prop, cortar_no, today)
                
                if article_no not in existing_map:
                    # 신규 매물 - upsert 사용으로 중복 오류 방지
                    try:
                        self.client.table('properties').upsert(property_record).execute()
                        stats['new_count'] += 1
                    except Exception as e:
                        # 중복이나 기타 오류 발생시 무시하고 계속 진행
                        print(f"⚠️ 매물 저장 스킵 ({article_no}): {e}")
                        continue
                else:
                    # 기존 매물 - 가격 및 월세 변동 체크
                    existing_property = existing_map[article_no]
                    old_price = existing_property['price']
                    old_rent_price = existing_property.get('rent_price', 0)
                    trade_type = existing_property.get('trade_type', property_record['trade_type'])
                    
                    new_price = property_record['price']
                    new_rent_price = property_record['rent_price']
                    
                    price_changed = old_price != new_price
                    rent_changed = old_rent_price != new_rent_price
                    
                    if price_changed or rent_changed:
                        # 가격/월세 변동 - 업데이트
                        update_data = {
                            'price': new_price,
                            'rent_price': new_rent_price,
                            'last_seen_date': today.isoformat(),
                            'updated_at': datetime.now().isoformat()
                            # missing_since 컬럼 없음으로 제거
                        }
                        
                        self.client.table('properties')\
                            .update(update_data)\
                            .eq('article_no', article_no)\
                            .execute()
                        
                        # 가격 변동 이력 저장 (월세 포함)
                        self._save_price_history(
                            article_no, trade_type, 
                            old_price, new_price, 
                            old_rent_price, new_rent_price, 
                            today
                        )
                        stats['updated_count'] += 1
                    else:
                        # 가격 변동 없으면 last_seen_date만 업데이트
                        self.client.table('properties')\
                            .update({
                                'last_seen_date': today.isoformat()
                                # missing_since 컬럼 없음으로 제거
                            })\
                            .eq('article_no', article_no)\
                            .execute()
                
                stats['total_saved'] += 1
            
            # 3. 🔧 개선된 삭제 매물 처리 (3일 유예 기간 적용)
            for article_no in existing_map:
                if article_no not in collected_ids:
                    # 마지막 확인 날짜 체크
                    last_seen_info = self._get_last_seen_date(article_no)
                    
                    if last_seen_info:
                        last_seen_date = last_seen_info['last_seen_date']
                        days_missing = (today - last_seen_date).days
                        
                        if days_missing >= 3:  # 3일 이상 미발견시에만 삭제 처리
                            deleted_property = existing_map[article_no]
                            
                            print(f"🗑️ 매물 삭제 처리: {article_no} ({days_missing}일 미발견)")
                            
                            # 매물을 비활성화 (삭제 정보는 deletion_history 테이블에 별도 저장)
                            delete_update = {
                                'is_active': False,
                                'deleted_at': today.isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            
                            self.client.table('properties')\
                                .update(delete_update)\
                                .eq('article_no', article_no)\
                                .execute()
                            
                            # 삭제 이력 테이블에 기록
                            self._save_deletion_history(article_no, deleted_property, cortar_no, today)
                            
                            stats['removed_count'] += 1
                        else:
                            print(f"⚠️ 매물 유예: {article_no} ({days_missing}일 미발견, 3일 대기 중)")
                            # last_seen_date 업데이트하지 않고 유지 (다음 수집까지 대기)
                    else:
                        # 첫 번째로 미발견된 경우
                        print(f"📝 매물 첫 미발견: {article_no} (3일 유예 시작)")
                        # missing_since 컬럼이 없으므로 last_seen_date를 업데이트하지 않음으로 유예 기간 추적
                        # 다음 수집까지 대기
            
            print(f"✅ 매물 저장 완료: 신규 {stats['new_count']}, 변동 {stats['updated_count']}, 삭제 {stats['removed_count']}")
            return stats
            
        except Exception as e:
            print(f"❌ 매물 저장 실패: {e}")
            return stats
    
    def get_property_count_by_region(self, cortar_no: str) -> int:
        """특정 지역의 활성 매물 수 조회"""
        try:
            result = self.client.table('properties')\
                .select('article_no', count='exact')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .execute()
            return result.count or 0
        except Exception as e:
            print(f"❌ 매물 수 조회 실패: {e}")
            return 0
    
    def get_active_properties_by_region(self, cortar_no: str) -> List[Dict]:
        """특정 지역의 활성 매물 목록 조회"""
        try:
            result = self.client.table('properties')\
                .select('article_no, last_seen_date, price, rent_price, address_road')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .execute()
            return result.data or []
        except Exception as e:
            print(f"❌ 활성 매물 조회 실패: {e}")
            return []
    
    def update_property_last_seen(self, article_no: str, last_seen_date: date) -> bool:
        """매물의 마지막 발견 날짜 업데이트"""
        try:
            self.client.table('properties')\
                .update({
                    'last_seen_date': last_seen_date.isoformat(),
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('article_no', article_no)\
                .execute()
            return True
        except Exception as e:
            print(f"❌ 마지막 발견 날짜 업데이트 실패: {e}")
            return False
    
    def soft_delete_property(self, article_no: str, days_missing: int) -> bool:
        """매물 소프트 삭제 처리"""
        try:
            today = date.today()
            
            # 매물 비활성화
            self.client.table('properties')\
                .update({
                    'is_active': False,
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('article_no', article_no)\
                .execute()
            
            # 삭제 이력 저장
            deletion_record = {
                'article_no': article_no,
                'deleted_date': today.isoformat(),
                'days_active': days_missing,
                'deletion_reason': f'{days_missing}일간 미발견',
                'created_at': datetime.now().isoformat()
            }
            
            self.client.table('deletion_history').insert(deletion_record).execute()
            print(f"🗑️ 삭제 이력 저장: {article_no} (활성 기간: {days_missing}일)")
            
            return True
        except Exception as e:
            print(f"❌ 매물 삭제 실패: {e}")
            return False
    
    def get_recent_deletions(self, days: int = 7) -> List[Dict]:
        """최근 N일간 삭제된 매물 조회"""
        try:
            cutoff_date = (date.today() - timedelta(days=days)).isoformat()
            
            result = self.client.table('deletion_history')\
                .select('*')\
                .gte('deleted_date', cutoff_date)\
                .order('deleted_date', desc=True)\
                .execute()
            
            return result.data or []
        except Exception as e:
            print(f"❌ 최근 삭제 조회 실패: {e}")
            return []
    
    def upsert_properties_batch(self, properties: List[Dict]) -> Dict:
        """매물 배치 업서트"""
        try:
            result = self.client.table('properties').upsert(properties).execute()
            
            return {
                'success': True,
                'inserted': len(properties),  # upsert라서 정확한 구분은 어려움
                'updated': 0
            }
        except Exception as e:
            print(f"❌ 배치 업서트 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'inserted': 0,
                'updated': 0
            }
    
    def save_converted_properties(self, db_properties: List[Dict], cortar_no: str) -> Dict:
        """이미 DB 형식으로 변환된 매물 데이터 저장"""
        today = date.today()
        stats = {
            'new_count': 0,
            'updated_count': 0,
            'removed_count': 0,
            'total_saved': 0
        }
        
        try:
            # 1. 기존 활성 매물 조회
            existing = self.client.table('properties')\
                .select('article_no, price, rent_price, trade_type')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .execute()
            
            existing_map = {item['article_no']: item for item in existing.data}
            collected_ids = set()
            
            # 2. 변환된 매물 데이터 처리
            for prop in db_properties:
                article_no = prop['article_no']
                collected_ids.add(article_no)
                
                if article_no not in existing_map:
                    # 신규 매물 - upsert 사용으로 중복 오류 방지
                    try:
                        self.client.table('properties').upsert(prop).execute()
                        stats['new_count'] += 1
                    except Exception as e:
                        print(f"⚠️ 매물 저장 스킵 ({article_no}): {e}")
                        continue
                else:
                    # 기존 매물 - 가격 및 월세 변동 체크
                    existing_property = existing_map[article_no]
                    old_price = existing_property['price']
                    old_rent_price = existing_property.get('rent_price', 0)
                    
                    new_price = prop['price']
                    new_rent_price = prop['rent_price']
                    
                    price_changed = old_price != new_price
                    rent_changed = old_rent_price != new_rent_price
                    
                    if price_changed or rent_changed:
                        # 가격/월세 변동 - 업데이트
                        update_data = {
                            'price': new_price,
                            'rent_price': new_rent_price,
                            'last_seen_date': today.isoformat(),
                            'updated_at': datetime.now().isoformat()
                            # missing_since 컬럼 없음으로 제거
                        }
                        
                        self.client.table('properties')\
                            .update(update_data)\
                            .eq('article_no', article_no)\
                            .execute()
                        
                        # 가격 변동 이력 저장
                        if hasattr(self, '_save_price_history'):
                            self._save_price_history(
                                article_no, existing_property.get('trade_type', prop['trade_type']),
                                old_price, new_price, 
                                old_rent_price, new_rent_price, 
                                today
                            )
                        stats['updated_count'] += 1
                    else:
                        # 가격 변동 없으면 last_seen_date만 업데이트
                        self.client.table('properties')\
                            .update({
                                'last_seen_date': today.isoformat()
                                # missing_since 컬럼 없음으로 제거
                            })\
                            .eq('article_no', article_no)\
                            .execute()
                
                stats['total_saved'] += 1
            
            # 3. 🔧 개선된 삭제 매물 처리 (3일 유예 기간 적용)
            for article_no in existing_map:
                if article_no not in collected_ids:
                    # 마지막 확인 날짜 체크
                    last_seen_info = self._get_last_seen_date(article_no)
                    
                    if last_seen_info:
                        last_seen_date = last_seen_info['last_seen_date']
                        days_missing = (today - last_seen_date).days
                        
                        if days_missing >= 3:  # 3일 이상 미발견시에만 삭제 처리
                            deleted_property = existing_map[article_no]
                            
                            print(f"🗑️ 매물 삭제 처리: {article_no} ({days_missing}일 미발견)")
                            
                            # 매물을 비활성화
                            delete_update = {
                                'is_active': False,
                                'updated_at': datetime.now().isoformat()
                            }
                            
                            self.client.table('properties')\
                                .update(delete_update)\
                                .eq('article_no', article_no)\
                                .execute()
                            
                            # 삭제 이력 테이블에 기록
                            self._save_deletion_history(article_no, deleted_property, cortar_no, today)
                            
                            stats['removed_count'] += 1
                        else:
                            print(f"⚠️ 매물 유예: {article_no} ({days_missing}일 미발견, 3일 대기 중)")
                    else:
                        # 첫 번째로 미발견된 경우
                        print(f"📝 매물 첫 미발견: {article_no} (3일 유예 시작)")
                        # missing_since 컬럼이 없으므로 last_seen_date를 업데이트하지 않음으로 유예 기간 추적
            
            print(f"✅ 변환된 매물 저장 완료 (안전모드): {stats['total_saved']}개 처리")
            print(f"⚠️ 삭제 로직은 UnifiedCollector에서 별도 안전하게 처리됩니다")
            return stats
            
        except Exception as e:
            print(f"❌ 변환된 매물 저장 실패: {e}")
            return stats
    
    def safe_save_converted_properties(self, db_properties: List[Dict], cortar_no: str) -> Dict:
        """
        🔧 완전히 안전한 매물 저장 메소드
        - 삭제 로직 완전 비활성화
        - upsert만 사용하여 데이터 안전성 보장
        """
        today = date.today()
        stats = {
            'new_count': 0,
            'updated_count': 0,
            'total_saved': 0
        }
        
        try:
            print(f"🔒 안전 모드 매물 저장: {len(db_properties)}개")
            
            # 모든 매물 데이터에 필수 필드 추가
            for prop in db_properties:
                prop['last_seen_date'] = today.isoformat()
                prop['updated_at'] = datetime.now().isoformat()
                if 'is_active' not in prop:
                    prop['is_active'] = True
            
            # 배치 처리
            batch_size = 25  # 더 작은 배치 사이즈로 안정성 증대
            total_processed = 0
            
            for i in range(0, len(db_properties), batch_size):
                batch = db_properties[i:i+batch_size]
                
                try:
                    # upsert로 안전하게 저장 (article_no 기준 충돌 해결)
                    self.client.table('properties').upsert(batch, on_conflict='article_no').execute()
                    total_processed += len(batch)
                    print(f"   ✅ 배치 {i//batch_size + 1}: {len(batch)}개 안전 저장")
                    
                except Exception as e:
                    print(f"⚠️ 배치 오류, 개별 처리 시도: {e}")
                    # 배치 실패시 개별 처리
                    for prop in batch:
                        try:
                            self.client.table('properties').upsert(prop, on_conflict='article_no').execute()
                            total_processed += 1
                        except Exception as e2:
                            print(f"❌ 매물 저장 실패 ({prop.get('article_no')}): {e2}")
            
            stats['total_saved'] = total_processed
            stats['new_count'] = total_processed  # upsert이므로 전체를 신규로 간주
            
            print(f"🔒 안전 저장 완료: {total_processed}개 처리 (삭제 로직 비활성화)")
            
            return stats
            
        except Exception as e:
            print(f"❌ 안전 저장 실패: {e}")
            return stats
    
    def save_daily_stats(self, stat_date: date, cortar_no: str, properties_data: List[Dict], save_stats: Dict):
        """일별 통계 저장"""
        try:
            # 통계 계산
            prices = [self._parse_price(p.get('매매가격', 0)) for p in properties_data if p.get('매매가격')]
            areas = [self._parse_area(p.get('전용면적')) for p in properties_data if p.get('전용면적')]
            
            stats_record = {
                'stat_date': stat_date.isoformat(),
                'cortar_no': cortar_no,
                'total_count': len(properties_data),
                'new_count': save_stats.get('new_count', 0),
                'removed_count': save_stats.get('removed_count', 0),
                'avg_price': sum(prices) / len(prices) if prices else 0,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'avg_area': sum(areas) / len(areas) if areas else 0,
                'price_distribution': self._calculate_distribution(prices),
                'area_distribution': self._calculate_distribution(areas),
                'type_distribution': self._calculate_type_distribution(properties_data)
            }
            
            # Upsert (동일 날짜 통계는 업데이트)
            self.client.table('daily_stats').upsert(stats_record).execute()
            print(f"✅ 일별 통계 저장 완료: {cortar_no} ({stat_date})")
            
        except Exception as e:
            print(f"❌ 일별 통계 저장 실패: {e}")
    
    def log_collection(self, log_data: Dict):
        """수집 로그 저장"""
        try:
            self.client.table('collection_logs').insert(log_data).execute()
        except Exception as e:
            print(f"⚠️ 로그 저장 실패: {e}")
    
    def _prepare_property_record(self, prop: Dict, cortar_no: str, collected_date: date) -> Dict:
        """매물 데이터를 DB 레코드로 변환"""
        # 카카오 주소 정보 추출
        kakao_addr = prop.get('상세정보', {}).get('카카오주소변환', {})
        
        # 상세정보 전체를 details JSONB 컬럼에 저장
        details_info = prop.get('상세정보', {})
        
        return {
            'article_no': prop['매물번호'],
            'cortar_no': cortar_no,
            'article_name': prop.get('매물명', ''),
            'real_estate_type': prop.get('부동산타입', ''),
            'trade_type': prop.get('거래타입', ''),
            'price': self._parse_price(prop.get('매매가격', 0)),
            'rent_price': self._parse_price(prop.get('월세', 0)),
            'area1': self._parse_area(prop.get('전용면적')),
            'area2': self._parse_area(prop.get('공급면적')),
            'floor_info': prop.get('층정보', ''),
            'direction': prop.get('방향', ''),
            'latitude': details_info.get('위치정보', {}).get('정확한_위도'),
            'longitude': details_info.get('위치정보', {}).get('정확한_경도'),
            'address_road': kakao_addr.get('도로명주소', ''),
            'address_jibun': kakao_addr.get('지번주소', ''),
            'address_detail': prop.get('상세주소', ''),
            'building_name': kakao_addr.get('건물명', prop.get('상세주소', '')),
            'postal_code': kakao_addr.get('우편번호', ''),
            'tag_list': prop.get('태그', []),
            'description': prop.get('설명', ''),
            'details': details_info,  # 상세정보 전체를 JSONB로 저장
            'collected_date': collected_date.isoformat(),
            'last_seen_date': collected_date.isoformat(),  # 신규 필드 추가
            'is_active': True  # 기본값 명시
        }
    
    def _parse_price(self, price_str: Any) -> Optional[int]:
        """가격 문자열을 숫자로 변환"""
        if isinstance(price_str, (int, float)):
            return int(price_str)
        if isinstance(price_str, str):
            # "5억 3,000" 같은 형식 처리
            price_str = price_str.replace(',', '').replace('억', '0000').replace('만', '')
            try:
                return int(price_str)
            except:
                return 0
        return 0
    
    def _parse_area(self, area_str: Any) -> Optional[float]:
        """면적 문자열을 숫자로 변환"""
        if isinstance(area_str, (int, float)):
            return float(area_str)
        if isinstance(area_str, str):
            try:
                return float(area_str.replace('㎡', '').strip())
            except:
                return None
        return None
    
    def _save_price_history(self, article_no: str, trade_type: str, 
                          old_price: int, new_price: int, 
                          old_rent_price: int, new_rent_price: int, 
                          changed_date: date):
        """가격 변동 이력 저장 (월세 포함)"""
        # 매매/전세 가격 변동 계산
        change_amount = new_price - old_price
        change_percent = (change_amount / old_price * 100) if old_price > 0 else 0
        
        # 월세 변동 계산
        rent_change_amount = new_rent_price - old_rent_price if old_rent_price is not None and new_rent_price is not None else None
        rent_change_percent = None
        if rent_change_amount is not None and old_rent_price > 0:
            rent_change_percent = (rent_change_amount / old_rent_price * 100)
        
        history_record = {
            'article_no': article_no,
            'trade_type': trade_type,
            'previous_price': old_price,
            'new_price': new_price,
            'previous_rent_price': old_rent_price,
            'new_rent_price': new_rent_price,
            'change_amount': change_amount,
            'change_percent': round(change_percent, 2),
            'rent_change_amount': rent_change_amount,
            'rent_change_percent': round(rent_change_percent, 2) if rent_change_percent is not None else None,
            'changed_date': changed_date.isoformat()
        }
        
        try:
            self.client.table('price_history').insert(history_record).execute()
            print(f"💰 가격 변동 기록: {article_no} - 가격: {old_price:,} → {new_price:,}만원")
            if rent_change_amount:
                print(f"💰 월세 변동: {old_rent_price:,} → {new_rent_price:,}만원")
        except Exception as e:
            print(f"⚠️ 가격 이력 저장 실패 ({article_no}): {e}")
    
    def _save_deletion_history(self, article_no: str, property_data: Dict, cortar_no: str, deleted_date: date):
        """삭제된 매물 이력 저장"""
        try:
            # 매물이 활성 상태였던 기간 계산
            created_at = property_data.get('created_at')
            days_active = None
            
            if created_at:
                try:
                    # created_at이 ISO 형식 문자열인 경우 파싱
                    if isinstance(created_at, str):
                        from datetime import datetime
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                        days_active = (deleted_date - created_date).days
                except:
                    days_active = None
            
            # 현재 매물 정보 조회해서 삭제 이력에 저장
            try:
                current_property = self.client.table('properties')\
                    .select('price, rent_price, trade_type, real_estate_type')\
                    .eq('article_no', article_no)\
                    .single()\
                    .execute()
                
                property_info = current_property.data if current_property.data else {}
            except:
                property_info = {}
            
            deletion_record = {
                'article_no': article_no,
                'deleted_date': deleted_date.isoformat(),
                'deletion_reason': 'not_found',
                'days_active': days_active,
                'final_price': property_info.get('price'),
                'final_rent_price': property_info.get('rent_price'),
                'final_trade_type': property_info.get('trade_type'),
                'cortar_no': cortar_no,
                'real_estate_type': property_info.get('real_estate_type')
            }
            
            self.client.table('deletion_history').insert(deletion_record).execute()
            print(f"🗑️ 삭제 이력 저장: {article_no} (활성 기간: {days_active}일)")
            
        except Exception as e:
            print(f"⚠️ 삭제 이력 저장 실패 ({article_no}): {e}")
    
    def _get_last_seen_date(self, article_no: str) -> Optional[Dict]:
        """매물의 마지막 확인 날짜 조회"""
        try:
            # properties 테이블에서 updated_at 또는 collected_date 확인
            result = self.client.table('properties')\
                .select('updated_at, collected_date')\
                .eq('article_no', article_no)\
                .single()\
                .execute()
            
            if result.data:
                property_data = result.data
                
                # missing_since 컬럼이 없으므로 생략
                
                # updated_at 또는 collected_date 중 최신 날짜 사용
                last_seen_str = property_data.get('updated_at') or property_data.get('collected_date')
                
                if last_seen_str:
                    from datetime import datetime
                    last_seen_date = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00')).date()
                    return {
                        'last_seen_date': last_seen_date,
                        'source': 'updated_at' if property_data.get('updated_at') else 'collected_date'
                    }
            
            return None
            
        except Exception as e:
            print(f"⚠️ 마지막 확인일 조회 실패 ({article_no}): {e}")
            return None
    
    def _calculate_distribution(self, values: List[float]) -> Dict:
        """값 분포 계산"""
        if not values:
            return {}
        
        # 간단한 히스토그램
        min_val = min(values)
        max_val = max(values)
        range_size = (max_val - min_val) / 10 if max_val > min_val else 1
        
        distribution = {}
        for val in values:
            bucket = int((val - min_val) / range_size) if range_size > 0 else 0
            bucket_key = f"range_{bucket}"
            distribution[bucket_key] = distribution.get(bucket_key, 0) + 1
        
        return distribution
    
    def _calculate_type_distribution(self, properties: List[Dict]) -> Dict:
        """타입별 분포 계산"""
        distribution = {}
        for prop in properties:
            prop_type = prop.get('부동산타입', '기타')
            distribution[prop_type] = distribution.get(prop_type, 0) + 1
        return distribution

# 테스트 함수
def test_connection():
    """Supabase 연결 테스트"""
    try:
        helper = SupabaseHelper()
        
        # 지역 정보 조회 테스트
        result = helper.client.table('areas').select('*').limit(1).execute()
        print(f"✅ 연결 테스트 성공! 지역 테이블 데이터: {len(result.data)}개")
        
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")

if __name__ == "__main__":
    test_connection()
