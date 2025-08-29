#!/usr/bin/env python3
"""
API 필드 매핑 진단 도구
- enhanced_data_collector.py의 실제 필드 매핑 효과 검증
- 최신 매물 데이터로 파싱 테스트
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# 환경변수 로드
load_dotenv()

class FieldMappingDiagnostic:
    def __init__(self):
        """진단기 초기화"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        # enhanced_data_collector.py에서 사용하는 토큰 (하드코딩된 값)
        self.token = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuaWQiOiJkYXNuZTUyOSIsImlhdCI6MTcyNTE0NTY1NCwibmxvZ2luX29yaWdpbl90eXBlIjoiMDIiLCJleHAiOjE3MjUxNTI4NTR9.wlJPyXOIdH3bR-C6-XH5XRJRH6rJRDh2t95P7Y5N3gE"
        
    def get_recent_article_no(self) -> str:
        """최신 매물번호 가져오기"""
        result = self.client.table('properties_new').select('article_no').order('created_at', desc=True).limit(1).execute()
        
        if result.data:
            return result.data[0]['article_no']
        else:
            # 강남구 테스트 매물번호
            return "2546565120"
    
    def fetch_api_response(self, article_no: str) -> dict:
        """네이버 API에서 실제 응답 가져오기"""
        print(f"🔍 매물 {article_no} API 응답 조회 중...")
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Authorization': self.token,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': 'https://new.land.naver.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            url = f"https://new.land.naver.com/api/articles/{article_no}?format=json"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API 요청 실패: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ API 요청 오류: {e}")
            return {}
    
    def analyze_api_structure(self, api_response: dict) -> dict:
        """API 응답 구조 분석"""
        if not api_response:
            return {}
        
        analysis = {
            'top_level_keys': list(api_response.keys()),
            'sections': {}
        }
        
        # 각 섹션별 구조 분석
        sections_to_check = [
            'articleDetail', 'articleAddition', 'articleSpace', 'articleFloor',
            'articleFacility', 'articlePrice', 'articleRealtor', 'articleTax',
            'articlePhotos'
        ]
        
        for section in sections_to_check:
            if section in api_response:
                section_data = api_response[section]
                if isinstance(section_data, dict):
                    analysis['sections'][section] = {
                        'exists': True,
                        'keys': list(section_data.keys()),
                        'key_count': len(section_data.keys())
                    }
                elif isinstance(section_data, list):
                    analysis['sections'][section] = {
                        'exists': True,
                        'type': 'list',
                        'length': len(section_data),
                        'sample_keys': list(section_data[0].keys()) if section_data and isinstance(section_data[0], dict) else []
                    }
                else:
                    analysis['sections'][section] = {
                        'exists': True,
                        'type': type(section_data).__name__,
                        'value': section_data
                    }
            else:
                analysis['sections'][section] = {'exists': False}
        
        return analysis
    
    def test_field_mapping_effectiveness(self, api_response: dict) -> dict:
        """필드 매핑 효과성 테스트"""
        results = {
            'area_mapping': {},
            'space_mapping': {},
            'floor_mapping': {},
            'facility_mapping': {},
            'realtor_mapping': {}
        }
        
        # 1. articleSpace 섹션 테스트
        if 'articleSpace' in api_response:
            space_data = api_response['articleSpace']
            
            results['area_mapping'] = {
                'supplyArea_exists': 'supplyArea' in space_data,
                'supplySpace_exists': 'supplySpace' in space_data,
                'exclusiveArea_exists': 'exclusiveArea' in space_data,
                'exclusiveSpace_exists': 'exclusiveSpace' in space_data,
                'supplyArea_value': space_data.get('supplyArea'),
                'supplySpace_value': space_data.get('supplySpace'),
                'exclusiveArea_value': space_data.get('exclusiveArea'),
                'exclusiveSpace_value': space_data.get('exclusiveSpace'),
                'all_space_keys': list(space_data.keys()) if isinstance(space_data, dict) else []
            }
            
            results['space_mapping'] = {
                'roomCount': space_data.get('roomCount'),
                'bathRoomCount': space_data.get('bathRoomCount'),
                'verandaCount': space_data.get('verandaCount'),
                'spaceType': space_data.get('spaceType'),
                'structureType': space_data.get('structureType')
            }
        
        # 2. articleFloor 섹션 테스트
        if 'articleFloor' in api_response:
            floor_data = api_response['articleFloor']
            
            results['floor_mapping'] = {
                'totalFloorCount': floor_data.get('totalFloorCount'),
                'undergroundFloorCount': floor_data.get('undergroundFloorCount'),
                'uppergroundFloorCount': floor_data.get('uppergroundFloorCount'),
                'floorTypeCode': floor_data.get('floorTypeCode'),
                'all_floor_keys': list(floor_data.keys()) if isinstance(floor_data, dict) else []
            }
        
        # 3. articleRealtor 섹션 테스트
        if 'articleRealtor' in api_response:
            realtor_data = api_response['articleRealtor']
            
            results['realtor_mapping'] = {
                'realtorName': realtor_data.get('realtorName'),
                'representativeName': realtor_data.get('representativeName'),
                'cellPhoneNo': realtor_data.get('cellPhoneNo'),
                'representativeTelNo': realtor_data.get('representativeTelNo'),
                'all_realtor_keys': list(realtor_data.keys()) if isinstance(realtor_data, dict) else []
            }
        
        # 4. articleFacility 섹션 테스트
        if 'articleFacility' in api_response:
            facility_data = api_response['articleFacility']
            
            results['facility_mapping'] = {
                'hasData': bool(facility_data),
                'facilityInfo': facility_data.get('facilityInfo'),
                'all_facility_keys': list(facility_data.keys()) if isinstance(facility_data, dict) else []
            }
        
        return results
    
    def diagnose_null_causes(self, mapping_results: dict) -> list:
        """NULL 값 발생 원인 진단"""
        issues = []
        
        # 면적 필드 이슈
        area_info = mapping_results.get('area_mapping', {})
        if not area_info.get('supplyArea_exists') and not area_info.get('supplySpace_exists'):
            issues.append("공급면적 필드가 API 응답에 없음 (supplyArea, supplySpace 모두 없음)")
        
        if not area_info.get('exclusiveArea_exists') and not area_info.get('exclusiveSpace_exists'):
            issues.append("전용면적 필드가 API 응답에 없음 (exclusiveArea, exclusiveSpace 모두 없음)")
        
        # 층수 정보 이슈
        floor_info = mapping_results.get('floor_mapping', {})
        if not floor_info.get('totalFloorCount'):
            issues.append("총 층수 정보가 API 응답에 없음 (totalFloorCount)")
        
        # 중개사 정보 이슈
        realtor_info = mapping_results.get('realtor_mapping', {})
        if not realtor_info.get('realtorName'):
            issues.append("중개사 이름이 API 응답에 없음 (realtorName)")
        
        return issues
    
    def generate_diagnostic_report(self, article_no: str, api_response: dict, analysis: dict, mapping_results: dict) -> dict:
        """진단 보고서 생성"""
        issues = self.diagnose_null_causes(mapping_results)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'article_no': article_no,
            'api_response_available': bool(api_response),
            'api_structure_analysis': analysis,
            'field_mapping_test_results': mapping_results,
            'identified_issues': issues,
            'recommendations': self.generate_recommendations(issues, mapping_results)
        }
        
        return report
    
    def generate_recommendations(self, issues: list, mapping_results: dict) -> list:
        """개선 권장사항 생성"""
        recommendations = []
        
        if "공급면적 필드가 API 응답에 없음" in str(issues):
            recommendations.append("articleDetail 섹션에서 면적 정보를 백업으로 수집하도록 로직 수정")
        
        if "전용면적 필드가 API 응답에 없음" in str(issues):
            recommendations.append("articleDetail의 spaceDetail에서 면적 정보 추출 로직 추가")
        
        if "총 층수 정보가 API 응답에 없음" in str(issues):
            recommendations.append("articleDetail에서 층수 정보 백업 수집")
        
        if not mapping_results.get('realtor_mapping', {}).get('realtorName'):
            recommendations.append("중개사 정보 수집 로직 재검토 필요")
        
        if len(issues) > 3:
            recommendations.append("API 응답 구조가 변경되었을 가능성 - 전체적인 필드 매핑 재검토 필요")
        
        return recommendations
    
    def print_diagnostic_summary(self, report: dict):
        """진단 결과 요약 출력"""
        print("\n" + "="*80)
        print("🔍 API 필드 매핑 진단 결과 요약")
        print("="*80)
        
        print(f"📋 분석 매물: {report['article_no']}")
        print(f"🌐 API 응답 수신: {'✅' if report['api_response_available'] else '❌'}")
        
        if report['api_response_available']:
            structure = report['api_structure_analysis']
            print(f"📊 최상위 키: {len(structure.get('top_level_keys', []))}개")
            
            # 섹션별 상태
            sections = structure.get('sections', {})
            existing_sections = [name for name, info in sections.items() if info.get('exists')]
            missing_sections = [name for name, info in sections.items() if not info.get('exists')]
            
            print(f"✅ 존재하는 섹션: {', '.join(existing_sections)}")
            if missing_sections:
                print(f"❌ 누락된 섹션: {', '.join(missing_sections)}")
            
            # 필드 매핑 결과
            mapping = report['field_mapping_test_results']
            area_mapping = mapping.get('area_mapping', {})
            
            print(f"\n📐 면적 필드 매핑:")
            print(f"   - supplyArea: {'✅' if area_mapping.get('supplyArea_exists') else '❌'} (값: {area_mapping.get('supplyArea_value')})")
            print(f"   - exclusiveArea: {'✅' if area_mapping.get('exclusiveArea_exists') else '❌'} (값: {area_mapping.get('exclusiveArea_value')})")
            
            floor_mapping = mapping.get('floor_mapping', {})
            print(f"\n🏢 층수 필드 매핑:")
            print(f"   - totalFloorCount: {floor_mapping.get('totalFloorCount')}")
            print(f"   - undergroundFloorCount: {floor_mapping.get('undergroundFloorCount')}")
            
            realtor_mapping = mapping.get('realtor_mapping', {})
            print(f"\n🏢 중개사 필드 매핑:")
            print(f"   - realtorName: {realtor_mapping.get('realtorName')}")
            print(f"   - representativeName: {realtor_mapping.get('representativeName')}")
        
        # 발견된 문제점
        issues = report['identified_issues']
        print(f"\n🚨 발견된 문제: {len(issues)}개")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        
        # 권장사항
        recommendations = report['recommendations']
        print(f"\n💡 권장사항: {len(recommendations)}개")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "="*80)

def main():
    """메인 실행 함수"""
    print("🔍 API 필드 매핑 진단 시작")
    print("="*50)
    
    try:
        diagnostic = FieldMappingDiagnostic()
        
        # 최신 매물번호 가져오기
        article_no = diagnostic.get_recent_article_no()
        print(f"📋 진단 대상: 매물번호 {article_no}")
        
        # API 응답 가져오기
        api_response = diagnostic.fetch_api_response(article_no)
        
        if not api_response:
            print("❌ API 응답을 받을 수 없습니다. 토큰 만료 또는 네트워크 문제일 수 있습니다.")
            return False
        
        # API 구조 분석
        structure_analysis = diagnostic.analyze_api_structure(api_response)
        
        # 필드 매핑 테스트
        mapping_results = diagnostic.test_field_mapping_effectiveness(api_response)
        
        # 진단 보고서 생성
        report = diagnostic.generate_diagnostic_report(
            article_no, api_response, structure_analysis, mapping_results
        )
        
        # 보고서 저장
        report_file = f"field_mapping_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 상세 보고서 저장: {report_file}")
        
        # 요약 출력
        diagnostic.print_diagnostic_summary(report)
        
        return True
        
    except Exception as e:
        print(f"❌ 진단 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)