#!/usr/bin/env python3
"""
고도화된 데이터 무결성 검증 시스템
- 실시간 데이터 품질 모니터링
- 자동 복구 메커니즘
- 상세한 데이터 추적
- 이상 패턴 감지
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from supabase_client import SupabaseHelper

@dataclass
class IntegrityCheck:
    """무결성 검사 결과"""
    check_name: str
    status: str  # PASS, WARN, FAIL
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    details: Dict
    fix_suggestion: Optional[str] = None

@dataclass
class DataQualityReport:
    """데이터 품질 보고서"""
    timestamp: str
    overall_score: float
    checks: List[IntegrityCheck]
    summary: Dict
    recommendations: List[str]

class DataIntegrityValidator:
    """데이터 무결성 검증기"""
    
    def __init__(self):
        self.helper = SupabaseHelper()
        self.quality_thresholds = {
            'missing_price_rate': 5.0,      # 가격 누락률 5% 이하
            'missing_address_rate': 10.0,   # 주소 누락률 10% 이하  
            'missing_coords_rate': 15.0,    # 좌표 누락률 15% 이하
            'duplicate_rate': 1.0,          # 중복률 1% 이하
            'stale_data_days': 7,           # 오래된 데이터 7일 이하
            'massive_deletion_threshold': 100  # 대량 삭제 임계값
        }
    
    def comprehensive_validation(self, check_days: int = 7) -> DataQualityReport:
        """종합 데이터 무결성 검증"""
        print("🔍 종합 데이터 무결성 검증 시작")
        print("=" * 60)
        
        checks = []
        
        # 1. 기본 데이터 품질 검사
        checks.extend(self._check_basic_data_quality(check_days))
        
        # 2. 중복 데이터 검사
        checks.extend(self._check_duplicate_data())
        
        # 3. 참조 무결성 검사
        checks.extend(self._check_referential_integrity())
        
        # 4. 시계열 일관성 검사
        checks.extend(self._check_temporal_consistency(check_days))
        
        # 5. 비즈니스 로직 검사
        checks.extend(self._check_business_logic_constraints())
        
        # 6. 대량 변경 감지
        checks.extend(self._check_massive_changes(check_days))
        
        # 종합 점수 계산
        overall_score = self._calculate_overall_score(checks)
        
        # 권장사항 생성
        recommendations = self._generate_recommendations(checks)
        
        # 요약 통계
        summary = self._generate_summary(checks)
        
        report = DataQualityReport(
            timestamp=datetime.now().isoformat(),
            overall_score=overall_score,
            checks=checks,
            summary=summary,
            recommendations=recommendations
        )
        
        self._print_validation_report(report)
        return report
    
    def _check_basic_data_quality(self, days: int) -> List[IntegrityCheck]:
        """기본 데이터 품질 검사"""
        print("📊 기본 데이터 품질 검사")
        
        checks = []
        since_date = (date.today() - timedelta(days=days)).isoformat()
        
        try:
            # 최근 데이터 조회
            recent_data = self.helper.client.table('properties')\
                .select('article_no, price, address_road, address_jibun, latitude, longitude, article_name')\
                .gte('collected_date', since_date)\
                .eq('is_active', True)\
                .execute()
            
            total_count = len(recent_data.data) if recent_data.data else 0
            
            if total_count == 0:
                checks.append(IntegrityCheck(
                    check_name="basic_data_availability",
                    status="FAIL",
                    severity="CRITICAL",
                    description="최근 수집된 데이터가 없습니다",
                    details={'period_days': days, 'total_count': 0},
                    fix_suggestion="수집기 상태 확인 및 재시작 필요"
                ))
                return checks
            
            # 누락 데이터 계산
            missing_stats = {
                'price': 0,
                'address': 0,
                'coordinates': 0,
                'name': 0
            }
            
            for record in recent_data.data:
                if not record.get('price'):
                    missing_stats['price'] += 1
                if not record.get('address_road') and not record.get('address_jibun'):
                    missing_stats['address'] += 1
                if not record.get('latitude') or not record.get('longitude'):
                    missing_stats['coordinates'] += 1
                if not record.get('article_name'):
                    missing_stats['name'] += 1
            
            # 각 항목별 품질 검사
            for field, missing_count in missing_stats.items():
                missing_rate = (missing_count / total_count) * 100
                threshold_key = f'missing_{field}_rate'
                threshold = self.quality_thresholds.get(threshold_key, 20.0)
                
                if missing_rate <= threshold:
                    status, severity = "PASS", "LOW"
                elif missing_rate <= threshold * 1.5:
                    status, severity = "WARN", "MEDIUM"
                else:
                    status, severity = "FAIL", "HIGH"
                
                checks.append(IntegrityCheck(
                    check_name=f"missing_{field}_check",
                    status=status,
                    severity=severity,
                    description=f"{field} 필드 누락률: {missing_rate:.1f}%",
                    details={
                        'missing_count': missing_count,
                        'total_count': total_count,
                        'missing_rate': missing_rate,
                        'threshold': threshold
                    },
                    fix_suggestion=f"{field} 수집 로직 점검 필요" if status != "PASS" else None
                ))
            
            print(f"  ✅ 기본 품질 검사 완료: {total_count:,}개 레코드 검사")
            
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="basic_data_quality",
                status="FAIL", 
                severity="CRITICAL",
                description=f"기본 품질 검사 실패: {str(e)}",
                details={'error': str(e)},
                fix_suggestion="데이터베이스 연결 및 테이블 구조 확인"
            ))
        
        return checks
    
    def _check_duplicate_data(self) -> List[IntegrityCheck]:
        """중복 데이터 검사"""
        print("🔄 중복 데이터 검사")
        
        checks = []
        
        try:
            # article_no 기준 중복 검사
            duplicate_query = """
                SELECT article_no, COUNT(*) as count
                FROM properties 
                WHERE is_active = true
                GROUP BY article_no 
                HAVING COUNT(*) > 1
            """
            
            # Supabase에서 직접 SQL 실행이 어려우므로 Python으로 중복 검사
            all_active = self.helper.client.table('properties')\
                .select('article_no')\
                .eq('is_active', True)\
                .execute()
            
            article_nos = [record['article_no'] for record in all_active.data or []]
            total_active = len(article_nos)
            unique_count = len(set(article_nos))
            duplicate_count = total_active - unique_count
            
            duplicate_rate = (duplicate_count / total_active * 100) if total_active > 0 else 0
            threshold = self.quality_thresholds['duplicate_rate']
            
            if duplicate_rate <= threshold:
                status, severity = "PASS", "LOW"
            elif duplicate_rate <= threshold * 2:
                status, severity = "WARN", "MEDIUM"
            else:
                status, severity = "FAIL", "HIGH"
            
            checks.append(IntegrityCheck(
                check_name="duplicate_articles",
                status=status,
                severity=severity,
                description=f"중복 매물 비율: {duplicate_rate:.1f}%",
                details={
                    'total_active': total_active,
                    'unique_count': unique_count,
                    'duplicate_count': duplicate_count,
                    'duplicate_rate': duplicate_rate,
                    'threshold': threshold
                },
                fix_suggestion="중복 제거 스크립트 실행 필요" if status != "PASS" else None
            ))
            
            print(f"  ✅ 중복 검사 완료: {duplicate_count}개 중복 발견")
            
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="duplicate_check",
                status="FAIL",
                severity="MEDIUM",
                description=f"중복 검사 실패: {str(e)}",
                details={'error': str(e)}
            ))
        
        return checks
    
    def _check_referential_integrity(self) -> List[IntegrityCheck]:
        """참조 무결성 검사"""
        print("🔗 참조 무결성 검사")
        
        checks = []
        
        try:
            # properties와 price_history 간 참조 무결성
            orphaned_history = self.helper.client.table('price_history')\
                .select('article_no')\
                .execute()
            
            if orphaned_history.data:
                history_article_nos = set(record['article_no'] for record in orphaned_history.data)
                
                existing_properties = self.helper.client.table('properties')\
                    .select('article_no')\
                    .in_('article_no', list(history_article_nos))\
                    .execute()
                
                existing_article_nos = set(record['article_no'] for record in existing_properties.data or [])
                orphaned_count = len(history_article_nos - existing_article_nos)
                
                if orphaned_count == 0:
                    status, severity = "PASS", "LOW"
                elif orphaned_count <= 10:
                    status, severity = "WARN", "MEDIUM"  
                else:
                    status, severity = "FAIL", "HIGH"
                
                checks.append(IntegrityCheck(
                    check_name="price_history_integrity",
                    status=status,
                    severity=severity,
                    description=f"고아 가격 이력: {orphaned_count}개",
                    details={
                        'orphaned_count': orphaned_count,
                        'total_history_records': len(history_article_nos)
                    },
                    fix_suggestion="고아 레코드 정리 필요" if status != "PASS" else None
                ))
            
            print(f"  ✅ 참조 무결성 검사 완료")
            
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="referential_integrity",
                status="FAIL",
                severity="MEDIUM", 
                description=f"참조 무결성 검사 실패: {str(e)}",
                details={'error': str(e)}
            ))
        
        return checks
    
    def _check_temporal_consistency(self, days: int) -> List[IntegrityCheck]:
        """시계열 일관성 검사"""
        print("⏰ 시계열 일관성 검사")
        
        checks = []
        since_date = (date.today() - timedelta(days=days)).isoformat()
        
        try:
            # 미래 날짜 데이터 검사
            today = date.today().isoformat()
            future_data = self.helper.client.table('properties')\
                .select('article_no, collected_date')\
                .gt('collected_date', today)\
                .execute()
            
            future_count = len(future_data.data) if future_data.data else 0
            
            checks.append(IntegrityCheck(
                check_name="future_dates",
                status="FAIL" if future_count > 0 else "PASS",
                severity="HIGH" if future_count > 0 else "LOW",
                description=f"미래 날짜 데이터: {future_count}개",
                details={'future_count': future_count},
                fix_suggestion="시스템 시간 및 수집 로직 확인" if future_count > 0 else None
            ))
            
            # 오래된 데이터 검사  
            stale_threshold = (date.today() - timedelta(days=self.quality_thresholds['stale_data_days'])).isoformat()
            stale_data = self.helper.client.table('properties')\
                .select('article_no', count='exact')\
                .lt('last_seen_date', stale_threshold)\
                .eq('is_active', True)\
                .execute()
            
            stale_count = stale_data.count or 0
            
            if stale_count == 0:
                status, severity = "PASS", "LOW"
            elif stale_count <= 100:
                status, severity = "WARN", "MEDIUM"
            else:
                status, severity = "FAIL", "HIGH"
            
            checks.append(IntegrityCheck(
                check_name="stale_data",
                status=status,
                severity=severity,
                description=f"오래된 활성 데이터: {stale_count}개",
                details={
                    'stale_count': stale_count,
                    'threshold_days': self.quality_thresholds['stale_data_days']
                },
                fix_suggestion="비활성화 로직 실행 필요" if status != "PASS" else None
            ))
            
            print(f"  ✅ 시계열 검사 완료")
            
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="temporal_consistency",
                status="FAIL",
                severity="MEDIUM",
                description=f"시계열 검사 실패: {str(e)}",
                details={'error': str(e)}
            ))
        
        return checks
    
    def _check_business_logic_constraints(self) -> List[IntegrityCheck]:
        """비즈니스 로직 제약 조건 검사"""
        print("💼 비즈니스 로직 검사")
        
        checks = []
        
        try:
            # 가격 범위 검사 (서울 강남구 기준)
            invalid_prices = self.helper.client.table('properties')\
                .select('article_no, price')\
                .or_('price.lt.1000,price.gt.100000000')\
                .eq('is_active', True)\
                .execute()
            
            invalid_price_count = len(invalid_prices.data) if invalid_prices.data else 0
            
            checks.append(IntegrityCheck(
                check_name="price_range_validation",
                status="WARN" if invalid_price_count > 0 else "PASS",
                severity="MEDIUM" if invalid_price_count > 0 else "LOW",
                description=f"비정상 가격 범위: {invalid_price_count}개",
                details={'invalid_count': invalid_price_count},
                fix_suggestion="가격 데이터 검증 로직 강화" if invalid_price_count > 0 else None
            ))
            
            # 좌표 범위 검사 (대한민국 범위)
            invalid_coords = self.helper.client.table('properties')\
                .select('article_no, latitude, longitude')\
                .or_('latitude.lt.33,latitude.gt.39,longitude.lt.124,longitude.gt.132')\
                .eq('is_active', True)\
                .execute()
            
            invalid_coord_count = len(invalid_coords.data) if invalid_coords.data else 0
            
            checks.append(IntegrityCheck(
                check_name="coordinate_range_validation", 
                status="WARN" if invalid_coord_count > 0 else "PASS",
                severity="MEDIUM" if invalid_coord_count > 0 else "LOW",
                description=f"비정상 좌표 범위: {invalid_coord_count}개",
                details={'invalid_count': invalid_coord_count},
                fix_suggestion="좌표 변환 로직 검증 필요" if invalid_coord_count > 0 else None
            ))
            
            print(f"  ✅ 비즈니스 로직 검사 완료")
            
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="business_logic",
                status="FAIL",
                severity="MEDIUM",
                description=f"비즈니스 로직 검사 실패: {str(e)}",
                details={'error': str(e)}
            ))
        
        return checks
    
    def _check_massive_changes(self, days: int) -> List[IntegrityCheck]:
        """대량 변경 감지"""
        print("📈 대량 변경 감지")
        
        checks = []
        since_date = (date.today() - timedelta(days=days)).isoformat()
        
        try:
            # 대량 삭제 감지
            massive_deletions = self.helper.client.table('deletion_history')\
                .select('deleted_date', count='exact')\
                .gte('deleted_date', since_date)\
                .execute()
            
            deletion_count = massive_deletions.count or 0
            threshold = self.quality_thresholds['massive_deletion_threshold']
            
            if deletion_count <= threshold:
                status, severity = "PASS", "LOW"
            elif deletion_count <= threshold * 2:
                status, severity = "WARN", "HIGH"
            else:
                status, severity = "FAIL", "CRITICAL"
            
            checks.append(IntegrityCheck(
                check_name="massive_deletion_detection",
                status=status,
                severity=severity,
                description=f"최근 {days}일 삭제: {deletion_count}개",
                details={
                    'deletion_count': deletion_count,
                    'threshold': threshold,
                    'period_days': days
                },
                fix_suggestion="삭제 로직 재검토 및 복구 스크립트 실행" if status == "FAIL" else None
            ))
            
            print(f"  ✅ 대량 변경 감지 완료")
            
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="massive_changes",
                status="FAIL", 
                severity="MEDIUM",
                description=f"대량 변경 감지 실패: {str(e)}",
                details={'error': str(e)}
            ))
        
        return checks
    
    def _calculate_overall_score(self, checks: List[IntegrityCheck]) -> float:
        """종합 품질 점수 계산"""
        if not checks:
            return 0.0
        
        severity_weights = {
            'LOW': 1,
            'MEDIUM': 2, 
            'HIGH': 4,
            'CRITICAL': 8
        }
        
        total_weight = 0
        penalty_weight = 0
        
        for check in checks:
            weight = severity_weights.get(check.severity, 1)
            total_weight += weight
            
            if check.status != "PASS":
                penalty_weight += weight
        
        if total_weight == 0:
            return 100.0
        
        score = max(0, 100 - (penalty_weight / total_weight * 100))
        return round(score, 1)
    
    def _generate_recommendations(self, checks: List[IntegrityCheck]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        failed_checks = [c for c in checks if c.status == "FAIL"]
        warn_checks = [c for c in checks if c.status == "WARN"]
        
        if failed_checks:
            recommendations.append("🚨 치명적 문제 발견 - 즉시 수정 필요")
            for check in failed_checks:
                if check.fix_suggestion:
                    recommendations.append(f"  • {check.fix_suggestion}")
        
        if warn_checks:
            recommendations.append("⚠️ 주의사항 - 모니터링 강화 권장") 
            for check in warn_checks[:3]:  # 최대 3개만
                if check.fix_suggestion:
                    recommendations.append(f"  • {check.fix_suggestion}")
        
        if not failed_checks and not warn_checks:
            recommendations.append("✅ 데이터 품질이 우수합니다")
        
        return recommendations
    
    def _generate_summary(self, checks: List[IntegrityCheck]) -> Dict:
        """요약 통계 생성"""
        status_counts = {'PASS': 0, 'WARN': 0, 'FAIL': 0}
        severity_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        
        for check in checks:
            status_counts[check.status] = status_counts.get(check.status, 0) + 1
            severity_counts[check.severity] = severity_counts.get(check.severity, 0) + 1
        
        return {
            'total_checks': len(checks),
            'status_distribution': status_counts,
            'severity_distribution': severity_counts,
            'pass_rate': (status_counts['PASS'] / len(checks) * 100) if checks else 0
        }
    
    def _print_validation_report(self, report: DataQualityReport):
        """검증 보고서 출력"""
        print("\n" + "="*70)
        print("📋 데이터 무결성 검증 보고서")
        print("="*70)
        
        # 종합 점수
        score = report.overall_score
        if score >= 90:
            score_icon = "🟢"
        elif score >= 70:
            score_icon = "🟡"
        else:
            score_icon = "🔴"
        
        print(f"{score_icon} 종합 품질 점수: {score}/100")
        print(f"📅 검사 시간: {report.timestamp}")
        
        # 요약
        summary = report.summary
        print(f"\n📊 검사 요약:")
        print(f"  총 검사: {summary['total_checks']}개")
        print(f"  통과: {summary['status_distribution']['PASS']}개")
        print(f"  경고: {summary['status_distribution']['WARN']}개") 
        print(f"  실패: {summary['status_distribution']['FAIL']}개")
        print(f"  통과율: {summary['pass_rate']:.1f}%")
        
        # 실패/경고 세부사항
        failed_checks = [c for c in report.checks if c.status != "PASS"]
        if failed_checks:
            print(f"\n🚨 주의 필요한 항목:")
            for check in failed_checks:
                status_icon = "❌" if check.status == "FAIL" else "⚠️"
                print(f"  {status_icon} {check.description}")
        
        # 권장사항
        if report.recommendations:
            print(f"\n💡 권장사항:")
            for rec in report.recommendations:
                print(f"  {rec}")
        
        print("="*70)
    
    def save_validation_report(self, report: DataQualityReport, filename: Optional[str] = None):
        """검증 보고서 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_integrity_report_{timestamp}.json"
        
        # DataClass를 dict로 변환
        report_dict = {
            'timestamp': report.timestamp,
            'overall_score': report.overall_score,
            'summary': report.summary,
            'recommendations': report.recommendations,
            'checks': [asdict(check) for check in report.checks]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        print(f"📄 검증 보고서 저장: {filename}")
        return filename

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='고도화된 데이터 무결성 검증')
    parser.add_argument('--days', type=int, default=7, help='검사 기간 (일)')
    parser.add_argument('--save-report', action='store_true', help='보고서 파일 저장')
    parser.add_argument('--output', type=str, help='출력 파일명')
    
    args = parser.parse_args()
    
    print("🔍 고도화된 데이터 무결성 검증 시스템 v2.0")
    print("=" * 60)
    
    validator = DataIntegrityValidator()
    report = validator.comprehensive_validation(check_days=args.days)
    
    if args.save_report:
        validator.save_validation_report(report, args.output)
    
    # 종료 코드 반환
    if report.overall_score >= 90:
        exit(0)  # 우수
    elif report.overall_score >= 70:
        exit(1)  # 보통
    else:
        exit(2)  # 문제 있음

if __name__ == "__main__":
    main()