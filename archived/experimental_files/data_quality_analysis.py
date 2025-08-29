#!/usr/bin/env python3
"""
Properties 테이블 데이터 품질 분석
- 최신 데이터의 NULL 값 분석
- 매물 상세정보 누락 여부 확인
- 수집기별 데이터 품질 비교
- 근본적 문제점 파악
"""

import json
from datetime import datetime, date, timedelta
from supabase_client import SupabaseHelper

class DataQualityAnalyzer:
    def __init__(self):
        self.helper = SupabaseHelper()
        
    def analyze_recent_properties_quality(self, days_back=7):
        """최근 매물 데이터 품질 분석"""
        print("=" * 80)
        print(f"🔍 최근 {days_back}일 properties 테이블 데이터 품질 분석")
        print("=" * 80)
        
        # 최근 데이터 조회
        cutoff_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        try:
            recent_properties = self.helper.client.table('properties')\
                .select('*')\
                .gte('collected_date', cutoff_date)\
                .order('collected_date', desc=True)\
                .limit(100)\
                .execute()
            
            if not recent_properties.data:
                print("❌ 최근 데이터가 없습니다!")
                return
            
            properties = recent_properties.data
            total_count = len(properties)
            
            print(f"📊 분석 대상: 최근 {total_count}개 매물 (최근 {days_back}일)")
            print()
            
            # 필수 필드별 NULL 분석
            critical_fields = {
                'article_no': '매물번호',
                'article_name': '매물명', 
                'real_estate_type': '부동산타입',
                'trade_type': '거래타입',
                'price': '가격',
                'area1': '전용면적',
                'address_road': '도로명주소',
                'address_jibun': '지번주소',
                'building_name': '건물명',
                'latitude': '위도',
                'longitude': '경도',
                'details': '상세정보'
            }
            
            print("🔴 필수 필드 NULL 비율 분석:")
            print("-" * 50)
            
            null_analysis = {}
            for field, description in critical_fields.items():
                null_count = sum(1 for p in properties if not p.get(field))
                null_ratio = (null_count / total_count) * 100
                null_analysis[field] = {
                    'null_count': null_count,
                    'null_ratio': null_ratio,
                    'description': description
                }
                
                status = "🚨" if null_ratio > 50 else "⚠️" if null_ratio > 10 else "✅"
                print(f"{status} {description:12} | NULL: {null_count:3}개 ({null_ratio:5.1f}%)")
            
            return null_analysis, properties
            
        except Exception as e:
            print(f"❌ 데이터 품질 분석 실패: {e}")
            return None, None
    
    def analyze_details_field_quality(self, properties):
        """details 필드 상세 분석"""
        print("\n" + "=" * 80)
        print("🔍 매물 상세정보(details) 필드 품질 분석")
        print("=" * 80)
        
        if not properties:
            print("❌ 분석할 데이터가 없습니다.")
            return
        
        total_count = len(properties)
        
        # details 필드 상태 분석
        null_details = 0
        empty_details = 0
        minimal_details = 0  # 기본 정보만 있는 경우
        rich_details = 0     # 풍부한 정보가 있는 경우
        
        details_examples = {
            'null': [],
            'empty': [], 
            'minimal': [],
            'rich': []
        }
        
        for prop in properties:
            article_no = prop.get('article_no', 'unknown')
            details = prop.get('details')
            
            if details is None:
                null_details += 1
                if len(details_examples['null']) < 3:
                    details_examples['null'].append(article_no)
            elif not details or details == {}:
                empty_details += 1
                if len(details_examples['empty']) < 3:
                    details_examples['empty'].append(article_no)
            else:
                # details 내용 분석
                detail_keys = list(details.keys()) if isinstance(details, dict) else []
                key_count = len(detail_keys)
                
                if key_count <= 3:  # 기본 정보만
                    minimal_details += 1
                    if len(details_examples['minimal']) < 3:
                        details_examples['minimal'].append({
                            'article_no': article_no,
                            'keys': detail_keys,
                            'count': key_count
                        })
                else:  # 풍부한 정보
                    rich_details += 1 
                    if len(details_examples['rich']) < 3:
                        details_examples['rich'].append({
                            'article_no': article_no,
                            'keys': detail_keys[:5],  # 처음 5개만 표시
                            'count': key_count
                        })
        
        print(f"📊 Details 필드 상태 분석 (총 {total_count}개)")
        print("-" * 50)
        print(f"🚨 NULL:           {null_details:3}개 ({null_details/total_count*100:5.1f}%)")
        print(f"⚠️  Empty:         {empty_details:3}개 ({empty_details/total_count*100:5.1f}%)")  
        print(f"🔶 Minimal (≤3키): {minimal_details:3}개 ({minimal_details/total_count*100:5.1f}%)")
        print(f"✅ Rich (>3키):    {rich_details:3}개 ({rich_details/total_count*100:5.1f}%)")
        
        # 예시 출력
        print("\n🔍 Details 예시:")
        print("-" * 50)
        
        if details_examples['null']:
            print(f"🚨 NULL 예시: {details_examples['null'][:3]}")
        
        if details_examples['empty']:
            print(f"⚠️ Empty 예시: {details_examples['empty'][:3]}")
        
        if details_examples['minimal']:
            print("🔶 Minimal 예시:")
            for ex in details_examples['minimal'][:2]:
                print(f"   {ex['article_no']}: {ex['keys']} ({ex['count']}키)")
        
        if details_examples['rich']:
            print("✅ Rich 예시:")
            for ex in details_examples['rich'][:2]:
                print(f"   {ex['article_no']}: {ex['keys']}... ({ex['count']}키)")
        
        return {
            'null_ratio': null_details/total_count*100,
            'empty_ratio': empty_details/total_count*100,
            'minimal_ratio': minimal_details/total_count*100,
            'rich_ratio': rich_details/total_count*100
        }
    
    def analyze_by_collection_date(self):
        """수집 날짜별 데이터 품질 변화 분석"""
        print("\n" + "=" * 80)
        print("📈 수집 날짜별 데이터 품질 변화 분석")
        print("=" * 80)
        
        try:
            # 최근 7일간 날짜별 분석
            daily_quality = {}
            
            for days_ago in range(7):
                target_date = (date.today() - timedelta(days=days_ago)).isoformat()
                
                day_properties = self.helper.client.table('properties')\
                    .select('article_no, details, address_road, latitude, longitude')\
                    .eq('collected_date', target_date)\
                    .limit(50)\
                    .execute()
                
                if day_properties.data:
                    props = day_properties.data
                    count = len(props)
                    
                    # 주요 필드 NULL 비율 계산
                    null_details = sum(1 for p in props if not p.get('details'))
                    null_address = sum(1 for p in props if not p.get('address_road'))
                    null_coords = sum(1 for p in props if not p.get('latitude') or not p.get('longitude'))
                    
                    daily_quality[target_date] = {
                        'count': count,
                        'null_details_ratio': null_details/count*100 if count > 0 else 0,
                        'null_address_ratio': null_address/count*100 if count > 0 else 0,
                        'null_coords_ratio': null_coords/count*100 if count > 0 else 0
                    }
            
            print("날짜별 데이터 품질 (최근 7일, 최대 50개 매물 기준):")
            print("-" * 70)
            print("날짜       | 매물수 | Details  | 주소     | 좌표")
            print("-" * 70)
            
            for target_date in sorted(daily_quality.keys(), reverse=True):
                quality = daily_quality[target_date]
                if quality['count'] > 0:
                    print(f"{target_date} | {quality['count']:4}개 | "
                          f"{quality['null_details_ratio']:5.1f}% | "
                          f"{quality['null_address_ratio']:5.1f}% | "
                          f"{quality['null_coords_ratio']:5.1f}%")
            
            return daily_quality
            
        except Exception as e:
            print(f"❌ 날짜별 분석 실패: {e}")
            return None
    
    def analyze_collection_method_impact(self):
        """수집 방법별 데이터 품질 분석"""
        print("\n" + "=" * 80)
        print("🔧 수집 방법 변화에 따른 데이터 품질 영향 분석")
        print("=" * 80)
        
        try:
            # 8월 16일 이전 vs 이후 데이터 품질 비교
            cutoff_date = "2025-08-16"
            
            # 이전 데이터 (정상 기간)
            before_data = self.helper.client.table('properties')\
                .select('*')\
                .lt('collected_date', cutoff_date)\
                .order('collected_date', desc=True)\
                .limit(100)\
                .execute()
            
            # 이후 데이터 (문제 기간)  
            after_data = self.helper.client.table('properties')\
                .select('*')\
                .gte('collected_date', cutoff_date)\
                .order('collected_date', desc=True)\
                .limit(100)\
                .execute()
            
            def analyze_dataset(data, label):
                if not data or not data.data:
                    print(f"❌ {label} 데이터 없음")
                    return None
                
                props = data.data
                count = len(props)
                
                # 주요 필드 NULL 분석
                results = {}
                critical_fields = ['details', 'address_road', 'latitude', 'longitude', 'building_name']
                
                for field in critical_fields:
                    null_count = sum(1 for p in props if not p.get(field))
                    results[field] = null_count / count * 100
                
                print(f"\n📊 {label} 데이터 품질 (최대 {count}개):")
                print("-" * 40)
                for field, ratio in results.items():
                    status = "🚨" if ratio > 70 else "⚠️" if ratio > 30 else "✅"
                    print(f"{status} {field:15}: {ratio:5.1f}% NULL")
                
                return results
            
            before_quality = analyze_dataset(before_data, "8/16 이전 (정상기간)")
            after_quality = analyze_dataset(after_data, "8/16 이후 (문제기간)")
            
            # 품질 변화 분석
            if before_quality and after_quality:
                print("\n📈 품질 변화 분석:")
                print("-" * 50)
                for field in before_quality:
                    before_ratio = before_quality[field]
                    after_ratio = after_quality[field]
                    change = after_ratio - before_ratio
                    
                    if abs(change) > 10:
                        status = "🆘" if change > 30 else "⚠️" if change > 0 else "✅"
                        direction = "악화" if change > 0 else "개선"
                        print(f"{status} {field:15}: {change:+5.1f}% {direction}")
            
            return before_quality, after_quality
            
        except Exception as e:
            print(f"❌ 수집 방법별 분석 실패: {e}")
            return None, None
    
    def identify_root_causes(self, null_analysis, details_quality, daily_quality):
        """근본 원인 분석"""
        print("\n" + "=" * 80)
        print("🎯 근본 원인 분석 및 해결 방향")
        print("=" * 80)
        
        critical_issues = []
        
        # 1. 심각한 NULL 비율 체크
        if null_analysis:
            for field, analysis in null_analysis.items():
                if analysis['null_ratio'] > 50:
                    critical_issues.append(f"🚨 {analysis['description']} NULL 비율 {analysis['null_ratio']:.1f}% (심각)")
                elif analysis['null_ratio'] > 20:
                    critical_issues.append(f"⚠️ {analysis['description']} NULL 비율 {analysis['null_ratio']:.1f}% (주의)")
        
        # 2. Details 필드 품질 체크  
        if details_quality:
            total_problematic = details_quality['null_ratio'] + details_quality['empty_ratio'] + details_quality['minimal_ratio']
            if total_problematic > 70:
                critical_issues.append(f"🚨 매물 상세정보 심각한 결손: {total_problematic:.1f}%가 부실")
        
        # 3. 품질 악화 추세 체크
        if daily_quality:
            recent_dates = sorted(daily_quality.keys(), reverse=True)[:3]
            avg_recent_null = sum(daily_quality[d]['null_details_ratio'] for d in recent_dates) / len(recent_dates)
            if avg_recent_null > 60:
                critical_issues.append(f"🚨 최근 3일 평균 Details NULL 비율 {avg_recent_null:.1f}%")
        
        print("🔍 발견된 핵심 문제점들:")
        print("-" * 50)
        for issue in critical_issues:
            print(f"   {issue}")
        
        if not critical_issues:
            print("✅ 심각한 데이터 품질 문제는 발견되지 않았습니다.")
        
        # 근본 원인 추론
        print("\n💡 추론된 근본 원인:")
        print("-" * 50)
        
        if null_analysis and null_analysis.get('details', {}).get('null_ratio', 0) > 50:
            print("1. 🔧 수집기에서 상세정보 API 호출 실패")
            print("   - include_details=False로 설정되어 있거나")  
            print("   - 상세정보 API 엔드포인트 변경")
            print("   - API 토큰/권한 문제")
        
        if null_analysis and null_analysis.get('latitude', {}).get('null_ratio', 0) > 30:
            print("2. 🗺️ 주소 변환 프로세스 실패") 
            print("   - 카카오 API 키 문제")
            print("   - 주소 변환 로직 오류")
        
        if null_analysis and null_analysis.get('address_road', {}).get('null_ratio', 0) > 40:
            print("3. 📍 기본 매물 정보 수집 실패")
            print("   - 네이버 API 구조 변경")
            print("   - 파싱 로직 오류")
            
        return critical_issues

def main():
    """메인 분석 실행"""
    analyzer = DataQualityAnalyzer()
    
    print("🔍 Properties 테이블 종합 데이터 품질 분석 시작...\n")
    
    # 1. 최근 데이터 품질 분석 (점진적으로 범위 확장)
    null_analysis, recent_properties = None, None
    for days_back in [7, 14, 30, 60]:
        print(f"🔍 최근 {days_back}일 데이터 확인 중...")
        result = analyzer.analyze_recent_properties_quality(days_back=days_back)
        if result and result[0] is not None:
            null_analysis, recent_properties = result
            break
    
    if null_analysis is None:
        print("❌ 분석할 데이터를 찾을 수 없습니다!")
        return
    
    # 2. Details 필드 상세 분석
    details_quality = analyzer.analyze_details_field_quality(recent_properties)
    
    # 3. 날짜별 품질 변화
    daily_quality = analyzer.analyze_by_collection_date()
    
    # 4. 수집 방법별 영향 분석
    before_quality, after_quality = analyzer.analyze_collection_method_impact()
    
    # 5. 근본 원인 분석
    critical_issues = analyzer.identify_root_causes(null_analysis, details_quality, daily_quality)
    
    # 6. 결과 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"data_quality_analysis_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'null_analysis': null_analysis,
            'details_quality': details_quality,
            'daily_quality': daily_quality,
            'before_after_quality': {
                'before': before_quality,
                'after': after_quality
            },
            'critical_issues': critical_issues
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 상세 분석 결과가 {result_file}에 저장되었습니다.")

if __name__ == "__main__":
    main()