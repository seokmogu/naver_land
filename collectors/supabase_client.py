#!/usr/bin/env python3
"""
Supabase 클라이언트 헬퍼
네이버 부동산 데이터 저장 및 조회
"""

import os
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from supabase import create_client, Client

class SupabaseHelper:
    def __init__(self, config_file: str = "config.json"):
        """Supabase 클라이언트 초기화"""
        # 설정 파일에서 연결 정보 로드
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
            # 1. 기존 활성 매물 조회
            existing = self.client.table('properties')\
                .select('article_no, price')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .execute()
            
            existing_map = {item['article_no']: item for item in existing.data}
            collected_ids = set()
            
            # 2. 매물 데이터 처리
            for prop in properties_data:
                article_no = prop['매물번호']
                collected_ids.add(article_no)
                
                # 저장할 데이터 준비
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
                    # 기존 매물 - 가격 변동 체크
                    old_price = existing_map[article_no]['price']
                    new_price = property_record['price']
                    
                    if old_price != new_price:
                        # 가격 변동 - 업데이트
                        self.client.table('properties')\
                            .update({
                                'price': new_price,
                                'updated_at': datetime.now().isoformat()
                            })\
                            .eq('article_no', article_no)\
                            .execute()
                        
                        # 가격 변동 이력 저장
                        self._save_price_history(article_no, old_price, new_price, today)
                        stats['updated_count'] += 1
                
                stats['total_saved'] += 1
            
            # 3. 삭제된 매물 처리
            for article_no in existing_map:
                if article_no not in collected_ids:
                    self.client.table('properties')\
                        .update({'is_active': False})\
                        .eq('article_no', article_no)\
                        .execute()
                    stats['removed_count'] += 1
            
            print(f"✅ 매물 저장 완료: 신규 {stats['new_count']}, 변동 {stats['updated_count']}, 삭제 {stats['removed_count']}")
            return stats
            
        except Exception as e:
            print(f"❌ 매물 저장 실패: {e}")
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
            'collected_date': collected_date.isoformat()
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
    
    def _save_price_history(self, article_no: str, old_price: int, new_price: int, changed_date: date):
        """가격 변동 이력 저장"""
        change_amount = new_price - old_price
        change_percent = (change_amount / old_price * 100) if old_price > 0 else 0
        
        history_record = {
            'article_no': article_no,
            'previous_price': old_price,
            'new_price': new_price,
            'change_amount': change_amount,
            'change_percent': round(change_percent, 2),
            'changed_date': changed_date.isoformat()
        }
        
        self.client.table('price_history').insert(history_record).execute()
    
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