#!/usr/bin/env python3
"""
데이터 파이프라인 수정사항 테스트
- 외래키 해결 메서드 테스트
- 참조 데이터 검증
- 데이터 플로우 시뮬레이션
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from enhanced_data_collector import EnhancedNaverCollector
    print("✅ Enhanced Data Collector 로드 성공")
except ImportError as e:
    print(f"❌ Enhanced Data Collector 로드 실패: {e}")
    sys.exit(1)

class PipelineFixTester:
    def __init__(self):
        self.collector = EnhancedNaverCollector()
        
    def test_foreign_key_resolution(self):
        """외래키 해결 메서드 테스트"""
        print("="*60)
        print("🔍 외래키 해결 메서드 테스트")
        print("="*60)
        
        # 테스트 데이터 생성
        test_data_sets = [
            {
                'article_no': 'TEST_001',
                'raw_sections': {
                    'articleDetail': {
                        'realEstateTypeName': '아파트',
                        'buildingUse': '주거용',
                        'cortarNo': '1168010100'
                    },
                    'articlePrice': {
                        'tradeTypeName': '매매'
                    }
                },
                'basic_info': {'building_use': '아파트'},
                'price_info': {'deal_price': 50000}
            },
            {
                'article_no': 'TEST_002',
                'raw_sections': {},  # 빈 데이터로 기본값 테스트
                'basic_info': {},
                'price_info': {}
            },
            {
                'article_no': 'TEST_003',
                'raw_sections': {
                    'articleDetail': {
                        'realEstateTypeName': '새로운유형',
                        'cortarNo': 'NEW_REGION_123'
                    },
                    'articlePrice': {
                        'tradeTypeName': '새로운거래'
                    }
                },
                'basic_info': {},
                'price_info': {}
            }
        ]
        
        results = []
        
        for i, test_data in enumerate(test_data_sets, 1):
            print(f"\n🧪 테스트 {i}: {test_data['article_no']}")
            print("-" * 40)
            
            # 부동산 유형 ID 테스트
            real_estate_id = self.collector._resolve_real_estate_type_id(test_data)
            trade_id = self.collector._resolve_trade_type_id(test_data)
            region_id = self.collector._resolve_region_id(test_data)
            
            result = {
                'test_case': i,
                'article_no': test_data['article_no'],
                'real_estate_type_id': real_estate_id,
                'trade_type_id': trade_id,
                'region_id': region_id,
                'all_resolved': all([real_estate_id, trade_id, region_id])
            }
            
            results.append(result)
            
            print(f"  부동산 유형 ID: {real_estate_id}")
            print(f"  거래 유형 ID: {trade_id}")
            print(f"  지역 ID: {region_id}")
            
            status = "✅ 성공" if result['all_resolved'] else "❌ 실패"
            print(f"  전체 해결: {status}")
        
        # 결과 요약
        print(f"\n📊 외래키 해결 테스트 결과")
        print("-" * 40)
        
        successful_cases = sum(1 for r in results if r['all_resolved'])
        total_cases = len(results)
        success_rate = (successful_cases / total_cases) * 100
        
        print(f"총 테스트 케이스: {total_cases}개")
        print(f"성공한 케이스: {successful_cases}개")
        print(f"성공률: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 모든 외래키 해결 테스트 성공!")
            print("💡 NULL 반환 문제 해결됨")
        else:
            print("⚠️ 일부 테스트 실패 - 추가 수정 필요")
            
        return results
    
    def test_data_pipeline_flow(self):
        """데이터 파이프라인 플로우 시뮬레이션"""
        print(f"\n🔄 데이터 파이프라인 플로우 시뮬레이션")
        print("-" * 60)
        
        # 실제 네이버 API 응답 구조 시뮬레이션
        mock_api_response = {
            'articleDetail': {
                'realEstateTypeName': '아파트',
                'buildingName': '테스트아파트',
                'buildingUse': '주거용',
                'cortarNo': '1168010100',
                'latitude': 37.5,
                'longitude': 127.0
            },
            'articlePrice': {
                'tradeTypeName': '매매',
                'dealPrice': 80000
            },
            'articleSpace': {
                'area1': 85.5,
                'area2': 60.2
            },
            'articleAddition': {
                'totalFloor': 15,
                'currentFloor': 5
            },
            'articleRealtor': {
                'realtorName': '테스트공인중개사'
            }
        }
        
        try:
            # API 응답을 직접 테스트 데이터로 변환
            test_data = {
                'article_no': 'TEST_FLOW',
                'raw_sections': mock_api_response,
                'basic_info': {
                    'building_use': mock_api_response['articleDetail'].get('buildingUse', ''),
                    'real_estate_type': mock_api_response['articleDetail'].get('realEstateTypeName', '')
                },
                'price_info': {
                    'deal_price': mock_api_response['articlePrice'].get('dealPrice', 0),
                    'trade_type': mock_api_response['articlePrice'].get('tradeTypeName', '')
                },
                'space_info': mock_api_response.get('articleSpace', {}),
                'location_info': {
                    'latitude': mock_api_response['articleDetail'].get('latitude'),
                    'longitude': mock_api_response['articleDetail'].get('longitude'),
                    'cortar_no': mock_api_response['articleDetail'].get('cortarNo')
                }
            }
            
            print("✅ API 응답 데이터 변환 성공")
            
            # 외래키 해결 테스트
            real_estate_id = self.collector._resolve_real_estate_type_id(test_data)
            trade_id = self.collector._resolve_trade_type_id(test_data)
            region_id = self.collector._resolve_region_id(test_data)
            
            if all([real_estate_id, trade_id, region_id]):
                print("✅ 외래키 해결 성공")
                print(f"  부동산유형: {real_estate_id}, 거래유형: {trade_id}, 지역: {region_id}")
                
                # area 정보 추출 테스트
                area_info = test_data.get('space_info', {})
                supply_area = area_info.get('supplySpace') or area_info.get('area1')
                exclusive_area = area_info.get('exclusiveSpace') or area_info.get('area2')
                
                print(f"  공급면적: {supply_area}㎡")
                print(f"  전용면적: {exclusive_area}㎡")
                
                # 카카오 주소 변환 테스트 (실제 변환 안함)
                if test_data['location_info'].get('latitude') and test_data['location_info'].get('longitude'):
                    print("✅ 좌표 정보 확인됨 - 카카오 주소 변환 준비 완료")
                
                print("✅ 데이터베이스 저장 준비 완료")
                print("💡 실제 저장은 테스트에서 건너뜀")
                
                return True
            else:
                print("❌ 외래키 해결 실패")
                return False
                
        except Exception as e:
            print(f"❌ 파이프라인 플로우 테스트 실패: {e}")
            return False
    
    def check_reference_data_health(self):
        """참조 데이터 상태 점검"""
        print(f"\n📋 참조 데이터 상태 점검")
        print("-" * 60)
        
        ref_tables = [
            ('real_estate_types', '부동산 유형'),
            ('trade_types', '거래 유형'),
            ('regions', '지역 정보')
        ]
        
        health_status = True
        
        for table_name, description in ref_tables:
            try:
                result = self.collector.client.table(table_name).select('id', count='exact').execute()
                count = result.count
                print(f"  {description} ({table_name}): {count}개")
                
                if count == 0:
                    print(f"    ⚠️ {description} 데이터 없음!")
                    health_status = False
                elif count < 5:
                    print(f"    ⚠️ {description} 데이터 부족 (최소 5개 권장)")
                else:
                    print(f"    ✅ {description} 데이터 충분")
                    
            except Exception as e:
                print(f"  ❌ {description} 조회 실패: {e}")
                health_status = False
        
        # 특별히 '알 수 없음' 타입들 확인
        print(f"\n🔍 '알 수 없음' 기본값 데이터 확인:")
        
        try:
            unknown_ret = self.collector.client.table('real_estate_types').select('id').eq('type_name', '알 수 없음').execute()
            unknown_trade = self.collector.client.table('trade_types').select('id').eq('type_name', '알 수 없음').execute()
            unknown_region = self.collector.client.table('regions').select('id').eq('cortar_no', 'UNKNOWN').execute()
            
            checks = [
                ('부동산유형 "알 수 없음"', unknown_ret.data),
                ('거래유형 "알 수 없음"', unknown_trade.data),
                ('지역 "UNKNOWN"', unknown_region.data)
            ]
            
            for desc, data in checks:
                if data:
                    print(f"  ✅ {desc}: ID={data[0]['id']}")
                else:
                    print(f"  ❌ {desc}: 없음 - 생성 필요!")
                    health_status = False
                    
        except Exception as e:
            print(f"  ❌ 기본값 확인 실패: {e}")
            health_status = False
        
        return health_status
    
    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        print("🧪 데이터 파이프라인 수정사항 종합 테스트")
        print("=" * 80)
        print(f"📅 테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 1. 참조 데이터 상태 점검
        ref_health = self.check_reference_data_health()
        
        # 2. 외래키 해결 테스트
        fk_results = self.test_foreign_key_resolution()
        fk_success = all(r['all_resolved'] for r in fk_results)
        
        # 3. 데이터 파이프라인 플로우 테스트
        flow_success = self.test_data_pipeline_flow()
        
        # 종합 결과
        print("\n" + "=" * 80)
        print("📊 종합 테스트 결과")
        print("=" * 80)
        
        tests = [
            ('참조 데이터 상태', ref_health),
            ('외래키 해결', fk_success),
            ('파이프라인 플로우', flow_success)
        ]
        
        passed_tests = sum(1 for _, success in tests if success)
        total_tests = len(tests)
        
        for test_name, success in tests:
            status = "✅ 통과" if success else "❌ 실패"
            print(f"  {status}: {test_name}")
        
        overall_success_rate = (passed_tests / total_tests) * 100
        print(f"\n전체 성공률: {overall_success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if overall_success_rate >= 100:
            print("🎉 모든 테스트 통과! 파이프라인 수정 성공!")
            print("💡 실제 데이터 수집 시작 가능")
        elif overall_success_rate >= 66:
            print("⚠️ 대부분 테스트 통과 - 일부 수정 필요")
            print("💡 기본 데이터 수집은 가능하나 추가 최적화 권장")
        else:
            print("❌ 다수 테스트 실패 - 추가 수정 필요")
            print("💡 파이프라인 추가 수정 후 재테스트 권장")
        
        return overall_success_rate

def main():
    tester = PipelineFixTester()
    success_rate = tester.run_comprehensive_test()
    
    print(f"\n🎯 권장 다음 단계:")
    if success_rate >= 100:
        print("1. 실제 네이버 부동산 데이터 수집 테스트")
        print("2. 카카오 API 컬럼 추가 (add_kakao_columns.sql 실행)")
        print("3. 대용량 데이터 수집 시작")
    else:
        print("1. 실패한 테스트 항목 수정")
        print("2. pipeline_monitor.py로 실시간 상태 확인")
        print("3. 추가 디버깅 및 최적화")

if __name__ == "__main__":
    main()