#!/usr/bin/env python3
"""
기존 properties 테이블을 정규화된 스키마로 마이그레이션하는 스크립트
안전한 단계별 마이그레이션 프로세스
"""

import os
import sys
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from supabase import create_client

# 환경변수 설정
os.environ['SUPABASE_URL'] = 'https://eslhavjipwbyvbbknixv.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'

class DatabaseMigrator:
    def __init__(self):
        """마이그레이션 도구 초기화"""
        try:
            self.client = create_client(
                os.environ['SUPABASE_URL'], 
                os.environ['SUPABASE_KEY']
            )
            print("✅ Supabase 연결 성공")
            
            self.migration_log = []
            self.stats = {
                'processed': 0,
                'errors': 0,
                'warnings': 0,
                'start_time': datetime.now()
            }
            
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            sys.exit(1)
    
    def log_action(self, action: str, status: str = "INFO", details: str = ""):
        """마이그레이션 액션 로그"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'action': action,
            'status': status,
            'details': details
        }
        self.migration_log.append(log_entry)
        
        status_symbol = {
            'INFO': '📝',
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌'
        }.get(status, '📝')
        
        print(f"{status_symbol} {action}: {details}")
    
    def backup_existing_data(self):
        """기존 데이터 백업"""
        self.log_action("데이터 백업", "INFO", "기존 테이블 백업 시작")
        
        try:
            # properties 테이블 백업
            properties_data = self.client.table('properties').select('*').execute()
            backup_file = current_dir / f"properties_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(properties_data.data, f, ensure_ascii=False, indent=2, default=str)
            
            self.log_action("데이터 백업", "SUCCESS", 
                          f"{len(properties_data.data):,}개 레코드 백업 완료: {backup_file}")
            
            return backup_file
            
        except Exception as e:
            self.log_action("데이터 백업", "ERROR", f"백업 실패: {e}")
            raise
    
    def check_schema_exists(self):
        """새로운 스키마가 생성되었는지 확인"""
        self.log_action("스키마 확인", "INFO", "정규화된 스키마 존재 여부 확인")
        
        try:
            # properties_new 테이블 존재 확인
            result = self.client.table('properties_new').select('*').limit(1).execute()
            self.log_action("스키마 확인", "SUCCESS", "정규화된 스키마 발견")
            return True
            
        except Exception as e:
            self.log_action("스키마 확인", "WARNING", 
                          f"정규화된 스키마가 없음: {e}")
            return False
    
    def analyze_existing_data(self):
        """기존 데이터 구조 분석"""
        self.log_action("데이터 분석", "INFO", "기존 properties 테이블 분석")
        
        try:
            # 전체 레코드 수 조회
            count_result = self.client.table('properties').select('*', count='exact').limit(1).execute()
            total_count = count_result.count or 0
            
            # 샘플 데이터 분석
            sample_result = self.client.table('properties').select('*').limit(100).execute()
            sample_data = sample_result.data
            
            analysis = {
                'total_records': total_count,
                'sample_size': len(sample_data),
                'columns': list(sample_data[0].keys()) if sample_data else [],
                'unique_article_types': set(),
                'unique_trade_types': set(),
                'unique_regions': set(),
                'details_structure': set()
            }
            
            # 샘플 데이터에서 고유값 추출
            for record in sample_data:
                if record.get('real_estate_type'):
                    analysis['unique_article_types'].add(record['real_estate_type'])
                if record.get('trade_type'):
                    analysis['unique_trade_types'].add(record['trade_type'])
                if record.get('cortar_no'):
                    analysis['unique_regions'].add(record['cortar_no'])
                
                # details 구조 분석
                if record.get('details') and isinstance(record['details'], dict):
                    analysis['details_structure'].update(record['details'].keys())
            
            # set을 list로 변환 (JSON 직렬화를 위해)
            for key in ['unique_article_types', 'unique_trade_types', 'unique_regions', 'details_structure']:
                analysis[key] = list(analysis[key])
            
            self.log_action("데이터 분석", "SUCCESS", 
                          f"분석 완료: {total_count:,}개 레코드, {len(analysis['columns'])}개 컬럼")
            
            return analysis
            
        except Exception as e:
            self.log_action("데이터 분석", "ERROR", f"분석 실패: {e}")
            raise
    
    def migrate_reference_data(self, analysis: Dict):
        """참조 데이터 마이그레이션"""
        self.log_action("참조 데이터 마이그레이션", "INFO", "참조 테이블 데이터 구축 시작")
        
        try:
            # 1. 부동산 유형 매핑
            type_mapping = self._migrate_real_estate_types(analysis['unique_article_types'])
            
            # 2. 거래 유형 매핑
            trade_mapping = self._migrate_trade_types(analysis['unique_trade_types'])
            
            # 3. 지역 정보 매핑
            region_mapping = self._migrate_regions(analysis['unique_regions'])
            
            self.log_action("참조 데이터 마이그레이션", "SUCCESS", 
                          f"매핑 완료: 유형 {len(type_mapping)}, 거래 {len(trade_mapping)}, 지역 {len(region_mapping)}")
            
            return {
                'real_estate_types': type_mapping,
                'trade_types': trade_mapping,
                'regions': region_mapping
            }
            
        except Exception as e:
            self.log_action("참조 데이터 마이그레이션", "ERROR", f"참조 데이터 마이그레이션 실패: {e}")
            raise
    
    def _migrate_real_estate_types(self, types: List[str]) -> Dict[str, int]:
        """부동산 유형 매핑"""
        mapping = {}
        
        for type_name in types:
            if not type_name:
                continue
                
            try:
                # 기존 매핑 확인
                existing = self.client.table('real_estate_types').select('id').eq('type_name', type_name).execute()
                
                if existing.data:
                    mapping[type_name] = existing.data[0]['id']
                else:
                    # 새로운 유형 추가
                    type_code = type_name[:10].upper().replace(' ', '_')
                    new_type = {
                        'type_code': type_code,
                        'type_name': type_name,
                        'category': self._classify_real_estate_type(type_name)
                    }
                    
                    result = self.client.table('real_estate_types').insert(new_type).execute()
                    mapping[type_name] = result.data[0]['id']
                    
            except Exception as e:
                self.log_action("부동산 유형 매핑", "WARNING", f"{type_name} 매핑 실패: {e}")
        
        return mapping
    
    def _migrate_trade_types(self, types: List[str]) -> Dict[str, int]:
        """거래 유형 매핑"""
        mapping = {}
        
        for type_name in types:
            if not type_name:
                continue
                
            try:
                # 기존 매핑 확인
                existing = self.client.table('trade_types').select('id').eq('type_name', type_name).execute()
                
                if existing.data:
                    mapping[type_name] = existing.data[0]['id']
                else:
                    # 새로운 거래 유형 추가
                    type_code = type_name[:10].upper().replace(' ', '_')
                    new_type = {
                        'type_code': type_code,
                        'type_name': type_name,
                        'requires_deposit': type_name in ['전세', '월세', '단기임대']
                    }
                    
                    result = self.client.table('trade_types').insert(new_type).execute()
                    mapping[type_name] = result.data[0]['id']
                    
            except Exception as e:
                self.log_action("거래 유형 매핑", "WARNING", f"{type_name} 매핑 실패: {e}")
        
        return mapping
    
    def _migrate_regions(self, cortar_nos: List[str]) -> Dict[str, int]:
        """지역 정보 매핑"""
        mapping = {}
        
        for cortar_no in cortar_nos:
            if not cortar_no:
                continue
                
            try:
                # regions 테이블에서 확인
                existing = self.client.table('regions').select('id').eq('cortar_no', cortar_no).execute()
                
                if existing.data:
                    mapping[cortar_no] = existing.data[0]['id']
                else:
                    # 기존 areas 테이블에서 정보 가져오기
                    areas_info = self.client.table('areas').select('*').eq('cortar_no', cortar_no).execute()
                    
                    if areas_info.data:
                        area_data = areas_info.data[0]
                        new_region = {
                            'cortar_no': cortar_no,
                            'dong_name': area_data.get('dong_name', '알 수 없음'),
                            'gu_name': self._guess_gu_name(area_data.get('dong_name', '')),
                            'center_lat': area_data.get('center_lat'),
                            'center_lon': area_data.get('center_lon')
                        }
                    else:
                        # 최소 정보로 생성
                        new_region = {
                            'cortar_no': cortar_no,
                            'dong_name': f'지역_{cortar_no}',
                            'gu_name': '알 수 없음'
                        }
                    
                    result = self.client.table('regions').insert(new_region).execute()
                    mapping[cortar_no] = result.data[0]['id']
                    
            except Exception as e:
                self.log_action("지역 매핑", "WARNING", f"{cortar_no} 매핑 실패: {e}")
        
        return mapping
    
    def migrate_main_properties(self, mappings: Dict, batch_size: int = 100):
        """메인 매물 데이터 마이그레이션"""
        self.log_action("메인 데이터 마이그레이션", "INFO", f"배치 크기 {batch_size}로 시작")
        
        try:
            # 전체 레코드 수 확인
            count_result = self.client.table('properties').select('*', count='exact').limit(1).execute()
            total_count = count_result.count or 0
            
            processed = 0
            errors = 0
            
            # 배치 단위로 처리
            for offset in range(0, total_count, batch_size):
                try:
                    # 배치 데이터 조회
                    batch_result = self.client.table('properties').select('*').range(offset, offset + batch_size - 1).execute()
                    batch_data = batch_result.data
                    
                    if not batch_data:
                        break
                    
                    # 배치 처리
                    migrated_properties = []
                    migrated_locations = []
                    migrated_physical = []
                    migrated_prices = []
                    
                    for record in batch_data:
                        try:
                            # 1. 기본 매물 정보
                            property_data = self._convert_property_data(record, mappings)
                            migrated_properties.append(property_data)
                            
                            # property_id는 나중에 설정 (insert 후 받아야 함)
                            property_id = None
                            
                            # 2. 위치 정보
                            location_data = self._convert_location_data(record, property_id, mappings)
                            if location_data:
                                migrated_locations.append(location_data)
                            
                            # 3. 물리적 정보
                            physical_data = self._convert_physical_data(record, property_id)
                            if physical_data:
                                migrated_physical.append(physical_data)
                            
                            # 4. 가격 정보
                            price_data = self._convert_price_data(record, property_id)
                            if price_data:
                                migrated_prices.extend(price_data)
                            
                        except Exception as e:
                            self.log_action("레코드 변환", "ERROR", 
                                          f"매물 {record.get('article_no')} 변환 실패: {e}")
                            errors += 1
                            continue
                    
                    # 배치 저장 (일단 기본 매물 정보만)
                    if migrated_properties:
                        try:
                            result = self.client.table('properties_new').insert(migrated_properties).execute()
                            batch_saved = len(result.data)
                            processed += batch_saved
                            
                            self.log_action("배치 저장", "SUCCESS", 
                                          f"배치 {offset//batch_size + 1}: {batch_saved}개 저장")
                            
                        except Exception as e:
                            self.log_action("배치 저장", "ERROR", f"배치 저장 실패: {e}")
                            errors += len(migrated_properties)
                    
                    # 진행률 표시
                    progress = (offset + batch_size) / total_count * 100
                    print(f"진행률: {progress:.1f}% ({processed:,}/{total_count:,})")
                    
                    # 배치 간 잠깐 휴식
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.log_action("배치 처리", "ERROR", f"배치 {offset} 처리 실패: {e}")
                    errors += batch_size
                    continue
            
            self.stats['processed'] = processed
            self.stats['errors'] = errors
            
            self.log_action("메인 데이터 마이그레이션", "SUCCESS", 
                          f"완료: {processed:,}개 처리, {errors}개 오류")
            
            return True
            
        except Exception as e:
            self.log_action("메인 데이터 마이그레이션", "ERROR", f"마이그레이션 실패: {e}")
            raise
    
    def _convert_property_data(self, record: Dict, mappings: Dict) -> Dict:
        """매물 기본 정보 변환"""
        real_estate_type_id = mappings['real_estate_types'].get(record.get('real_estate_type'))
        trade_type_id = mappings['trade_types'].get(record.get('trade_type'))  
        region_id = mappings['regions'].get(record.get('cortar_no'))
        
        return {
            'article_no': record.get('article_no'),
            'article_name': record.get('article_name'),
            'real_estate_type_id': real_estate_type_id,
            'trade_type_id': trade_type_id,
            'region_id': region_id,
            'collected_date': record.get('collected_date'),
            'last_seen_date': record.get('last_seen_date'),
            'is_active': record.get('is_active', True),
            'tag_list': record.get('tag_list'),
            'description': record.get('description'),
            'created_at': record.get('created_at'),
            'updated_at': record.get('updated_at')
        }
    
    def _convert_location_data(self, record: Dict, property_id: Optional[int], mappings: Dict) -> Optional[Dict]:
        """위치 정보 변환"""
        if not any([record.get('latitude'), record.get('longitude'), record.get('address_road')]):
            return None
        
        return {
            'property_id': property_id,  # 나중에 업데이트
            'latitude': record.get('latitude'),
            'longitude': record.get('longitude'),
            'address_road': record.get('address_road'),
            'address_jibun': record.get('address_jibun'),
            'building_name': record.get('building_name'),
            'postal_code': record.get('postal_code'),
            'cortar_no': record.get('cortar_no'),
            'region_id': mappings['regions'].get(record.get('cortar_no')),
            'address_verified': False
        }
    
    def _convert_physical_data(self, record: Dict, property_id: Optional[int]) -> Optional[Dict]:
        """물리적 정보 변환"""
        if not any([record.get('area1'), record.get('area2'), record.get('floor_info')]):
            return None
        
        # floor_info에서 층 정보 파싱
        floor_current, floor_total = self._parse_floor_info(record.get('floor_info', ''))
        
        return {
            'property_id': property_id,  # 나중에 업데이트
            'area_exclusive': self._parse_area(record.get('area1')),
            'area_supply': self._parse_area(record.get('area2')),
            'floor_current': floor_current,
            'floor_total': floor_total,
            'direction': record.get('direction'),
            'parking_possible': False,  # 기본값
            'elevator_available': False  # 기본값
        }
    
    def _convert_price_data(self, record: Dict, property_id: Optional[int]) -> List[Dict]:
        """가격 정보 변환"""
        prices = []
        collected_date = record.get('collected_date', date.today().isoformat())
        
        # 매매가
        if record.get('price') and self._parse_price(record['price']) > 0:
            prices.append({
                'property_id': property_id,
                'price_type': 'sale',
                'amount': self._parse_price(record['price']),
                'valid_from': collected_date,
                'valid_to': None
            })
        
        # 월세
        if record.get('rent_price') and self._parse_price(record['rent_price']) > 0:
            prices.append({
                'property_id': property_id,
                'price_type': 'rent',
                'amount': self._parse_price(record['rent_price']),
                'valid_from': collected_date,
                'valid_to': None
            })
        
        return prices
    
    def _classify_real_estate_type(self, type_name: str) -> str:
        """부동산 유형 분류"""
        if '아파트' in type_name or '빌라' in type_name or '주택' in type_name:
            return 'residential'
        elif '상가' in type_name or '사무실' in type_name or '건물' in type_name:
            return 'commercial'
        elif '오피스텔' in type_name:
            return 'mixed'
        elif '공장' in type_name:
            return 'industrial'
        elif '토지' in type_name:
            return 'land'
        else:
            return 'other'
    
    def _guess_gu_name(self, dong_name: str) -> str:
        """동 이름으로부터 구 이름 추정"""
        gu_mapping = {
            '강남': '강남구', '서초': '서초구', '송파': '송파구', '강동': '강동구',
            '마포': '마포구', '용산': '용산구', '중구': '중구', '종로': '종로구',
            '성동': '성동구', '광진': '광진구', '동대문': '동대문구', '중랑': '중랑구',
            '성북': '성북구', '강북': '강북구', '도봉': '도봉구', '노원': '노원구',
            '은평': '은평구', '서대문': '서대문구', '양천': '양천구', '강서': '강서구',
            '구로': '구로구', '금천': '금천구', '영등포': '영등포구', '동작': '동작구',
            '관악': '관악구'
        }
        
        for key, value in gu_mapping.items():
            if key in dong_name:
                return value
        
        return '알 수 없음'
    
    def _parse_floor_info(self, floor_info: str) -> tuple:
        """층 정보 파싱"""
        if not floor_info:
            return None, None
        
        try:
            # "3/15층" 형식 파싱
            if '/' in floor_info and '층' in floor_info:
                parts = floor_info.replace('층', '').split('/')
                current = int(parts[0].strip())
                total = int(parts[1].strip()) if len(parts) > 1 else None
                return current, total
            # "3층" 형식
            elif '층' in floor_info:
                floor_num = int(floor_info.replace('층', '').strip())
                return floor_num, None
        except:
            pass
        
        return None, None
    
    def _parse_area(self, area_str: Any) -> Optional[float]:
        """면적 문자열 파싱"""
        if not area_str:
            return None
        
        try:
            if isinstance(area_str, (int, float)):
                return float(area_str)
            elif isinstance(area_str, str):
                # "84.3㎡" -> 84.3
                area_clean = area_str.replace('㎡', '').replace('m²', '').strip()
                return float(area_clean)
        except:
            pass
        
        return None
    
    def _parse_price(self, price_str: Any) -> int:
        """가격 문자열 파싱"""
        if not price_str:
            return 0
        
        try:
            if isinstance(price_str, (int, float)):
                return int(price_str)
            elif isinstance(price_str, str):
                # "5억 3,000만원" -> 53000
                price_clean = price_str.replace('억', '0000').replace('만', '').replace('원', '').replace(',', '').strip()
                return int(price_clean) if price_clean.isdigit() else 0
        except:
            pass
        
        return 0
    
    def generate_migration_report(self):
        """마이그레이션 보고서 생성"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        report = {
            'migration_summary': {
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'processed_records': self.stats['processed'],
                'error_count': self.stats['errors'],
                'warning_count': self.stats['warnings']
            },
            'detailed_log': self.migration_log
        }
        
        # 보고서 파일 저장
        report_file = current_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        self.log_action("마이그레이션 보고서", "SUCCESS", f"보고서 저장: {report_file}")
        
        # 요약 출력
        print("\n" + "="*80)
        print("📊 마이그레이션 완료 보고서")
        print("="*80)
        print(f"⏱️ 소요시간: {duration.total_seconds():.1f}초")
        print(f"✅ 처리된 레코드: {self.stats['processed']:,}개")
        print(f"❌ 오류 레코드: {self.stats['errors']}개")
        print(f"⚠️ 경고 레코드: {self.stats['warnings']}개")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['processed'] - self.stats['errors']) / self.stats['processed'] * 100
            print(f"📈 성공률: {success_rate:.1f}%")
        
        print(f"📁 상세 보고서: {report_file}")
        print("="*80)
        
        return report

def main():
    """메인 마이그레이션 프로세스"""
    print("🚀 네이버 부동산 DB 정규화 마이그레이션 시작")
    print("="*60)
    
    migrator = DatabaseMigrator()
    
    try:
        # 1. 데이터 백업
        backup_file = migrator.backup_existing_data()
        
        # 2. 스키마 확인
        if not migrator.check_schema_exists():
            print("❌ 정규화된 스키마가 생성되지 않았습니다.")
            print("먼저 create_normalized_schema.sql을 실행하세요.")
            sys.exit(1)
        
        # 3. 기존 데이터 분석
        analysis = migrator.analyze_existing_data()
        
        # 4. 참조 데이터 마이그레이션
        mappings = migrator.migrate_reference_data(analysis)
        
        # 5. 메인 데이터 마이그레이션
        migrator.migrate_main_properties(mappings, batch_size=50)
        
        # 6. 마이그레이션 보고서 생성
        report = migrator.generate_migration_report()
        
        print("\n✅ 마이그레이션 완료!")
        print("📋 다음 단계: 데이터 무결성 검증 및 성능 테스트")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        migrator.generate_migration_report()
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        migrator.generate_migration_report()
        sys.exit(1)

if __name__ == "__main__":
    main()