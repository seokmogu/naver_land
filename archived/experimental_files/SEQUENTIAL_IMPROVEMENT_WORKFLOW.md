# 🚀 네이버 부동산 수집기 순차 개선 워크플로우

**작성일**: 2025-08-27  
**전략**: Systematic Implementation with Safety-First Approach  
**목표**: json_to_supabase.py 문제 해결 및 시스템 안정화

---

## 📋 워크플로우 개요

### 🎯 핵심 목표
1. **즉시**: 추가 데이터 손실 방지
2. **단기**: 안전한 직접 DB 저장 시스템 구축
3. **중기**: 완전 통합 자동화 시스템
4. **장기**: 실시간 모니터링 및 확장 가능한 아키텍처

### 🛡️ 안전성 원칙
- **단계별 검증**: 각 단계 완료 후 필수 검증
- **롤백 준비**: 모든 변경사항에 대한 복구 계획
- **점진적 적용**: 10% → 50% → 100% 단계적 배포
- **실시간 모니터링**: 이상 징후 발견시 즉시 중단

---

## 🚨 Phase 1: Emergency Response (TODAY - 즉시 실행)

### Step 1.1: 즉시 손실 방지 조치 (30분)
**목표**: json_to_supabase.py 관련 모든 자동 실행 중단

**실행 단계**:
```bash
# 1. 크론탭 확인 및 비활성화
crontab -l > /tmp/backup_crontab.txt
crontab -r  # 모든 크론탭 제거

# 2. 실행 중인 프로세스 확인
ps aux | grep json_to_supabase
ps aux | grep python | grep collector

# 3. 스케줄링 스크립트 확인
find /home/hackit/naver_land -name "*schedule*" -type f
find /home/hackit/naver_land -name "*cron*" -type f
```

**검증 기준**:
- [ ] 크론탭이 완전히 비활성화됨
- [ ] json_to_supabase.py 관련 프로세스 없음
- [ ] 백업 크론탭 파일 생성됨 (`/tmp/backup_crontab.txt`)

**롤백 방법**:
```bash
crontab /tmp/backup_crontab.txt  # 원본 크론탭 복구
```

---

### Step 1.2: 응급 데이터 복구 (60분)
**목표**: 8월 16일 이후 잘못 삭제된 매물 복구

**실행 단계**:
```bash
# 1. 응급 복구 스크립트 생성
cat > emergency_recovery.py << 'EOF'
from supabase_client import SupabaseHelper
from datetime import datetime, date

def emergency_data_recovery():
    """8월 16일 이후 잘못 삭제된 매물 응급 복구"""
    helper = SupabaseHelper()
    
    # 1. 현재 상태 백업
    backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"🔄 백업 시작: {backup_timestamp}")
    
    # 2. 삭제된 매물 조회
    deleted_props = helper.client.table('deletion_history')\
        .select('article_no, deleted_date')\
        .gte('deleted_date', '2025-08-16')\
        .execute()
    
    print(f"📊 복구 대상: {len(deleted_props.data)}개 매물")
    
    # 3. 복구 실행
    recovered_count = 0
    for prop in deleted_props.data:
        article_no = prop['article_no']
        
        try:
            # properties 테이블에서 다시 활성화
            result = helper.client.table('properties')\
                .update({
                    'is_active': True, 
                    'deleted_at': None,
                    'recovered_at': datetime.now().isoformat(),
                    'recovery_reason': 'Emergency recovery - wrong deletion'
                })\
                .eq('article_no', article_no)\
                .execute()
            
            if result.data:
                recovered_count += 1
                print(f"✅ 복구: {article_no}")
            
        except Exception as e:
            print(f"❌ 복구 실패 {article_no}: {str(e)}")
    
    print(f"🎯 복구 완료: {recovered_count}/{len(deleted_props.data)} 매물")
    return recovered_count

if __name__ == "__main__":
    recovered = emergency_data_recovery()
    print(f"📈 최종 결과: {recovered}개 매물 복구 완료")
EOF

# 2. 복구 실행
python emergency_recovery.py > recovery_log_$(date +%Y%m%d_%H%M%S).txt 2>&1
```

**검증 기준**:
- [ ] 복구 로그 파일 생성됨
- [ ] 최소 50개 이상 매물 복구됨
- [ ] properties 테이블에서 is_active=true 카운트 증가 확인

**롤백 방법**:
```sql
-- 복구 작업 롤백 (필요시)
UPDATE properties 
SET is_active = false, deleted_at = NOW(), recovered_at = NULL
WHERE recovery_reason = 'Emergency recovery - wrong deletion';
```

---

### Step 1.3: 안전 검증 및 백업 (15분)
**목표**: 현재 상태 완전 백업 및 복구 검증

**실행 단계**:
```bash
# 1. 데이터베이스 백업
pg_dump 데이터베이스명 > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# 2. 중요 파일 백업
cp -r /home/hackit/naver_land/collectors /home/hackit/backup_collectors_$(date +%Y%m%d)

# 3. 복구 상태 검증
python -c "
from supabase_client import SupabaseHelper
helper = SupabaseHelper()
active_count = helper.client.table('properties').select('article_no', count='exact').eq('is_active', True).execute()
print(f'현재 활성 매물: {active_count.count}개')
"
```

**검증 기준**:
- [ ] 데이터베이스 백업 파일 생성됨
- [ ] 코드 백업 완료됨
- [ ] 활성 매물 수 확인 및 기록됨

---

## 🔄 Phase 2: Direct DB Integration (TODAY - 2시간)

### Step 2.1: 직접 DB 저장 모듈 구현 (90분)
**목표**: JSON 파일을 거치지 않는 직접 DB 저장 시스템

**실행 단계**:
```bash
# 1. JSON-DB 변환기 생성
cat > json_to_db_converter.py << 'EOF'
from typing import List, Dict, Any
from datetime import date
import json

class JsonToDbConverter:
    """JSON 형식을 DB 스키마에 맞게 변환"""
    
    @staticmethod
    def convert_property(json_property: Dict[str, Any], cortar_no: str) -> Dict[str, Any]:
        """단일 매물 JSON을 DB 형식으로 변환"""
        
        # 기본 매물 정보
        db_property = {
            'article_no': json_property.get('매물번호'),
            'article_name': json_property.get('매물명', ''),
            'real_estate_type': json_property.get('부동산타입', ''),
            'trade_type': json_property.get('거래타입', ''),
            'price': JsonToDbConverter._parse_price(json_property.get('매매가격', '')),
            'rent_price': JsonToDbConverter._parse_price(json_property.get('월세', '')),
            'deposit': JsonToDbConverter._parse_price(json_property.get('보증금', '')),
            'area1': JsonToDbConverter._parse_float(json_property.get('전용면적', '')),
            'area2': JsonToDbConverter._parse_float(json_property.get('공급면적', '')),
            'floor_info': json_property.get('층정보', ''),
            'direction': json_property.get('방향', ''),
            'tag_list': json_property.get('태그', []),
            'description': json_property.get('설명', ''),
            'cortar_no': cortar_no,
            'collected_date': date.today().isoformat(),
            'is_active': True,
            'created_at': 'NOW()',
            'updated_at': 'NOW()'
        }
        
        # 상세정보에서 추가 데이터 추출
        details = json_property.get('상세정보', {})
        
        # 카카오 주소 정보
        kakao_info = details.get('카카오주소변환', {})
        if kakao_info:
            db_property.update({
                'address_road': kakao_info.get('도로명주소', ''),
                'address_jibun': kakao_info.get('지번주소', ''),
                'building_name': kakao_info.get('건물명', ''),
                'postal_code': kakao_info.get('우편번호', '')
            })
        
        # 위치 정보
        location_info = details.get('위치정보', {})
        if location_info:
            db_property.update({
                'latitude': JsonToDbConverter._parse_float(location_info.get('정확한_위도', '0')),
                'longitude': JsonToDbConverter._parse_float(location_info.get('정확한_경도', '0'))
            })
        
        return db_property
    
    @staticmethod
    def _parse_price(price_str: str) -> int:
        """가격 문자열을 정수로 변환"""
        if not price_str:
            return 0
        # 숫자가 아닌 문자 제거
        import re
        numbers = re.findall(r'\d+', str(price_str))
        if numbers:
            return int(''.join(numbers))
        return 0
    
    @staticmethod
    def _parse_float(value: str) -> float:
        """문자열을 float로 안전하게 변환"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

def convert_json_file_to_properties(json_file_path: str, cortar_no: str) -> List[Dict[str, Any]]:
    """JSON 파일을 읽어 DB 형식으로 변환"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    properties = []
    for item in data:
        converted = JsonToDbConverter.convert_property(item, cortar_no)
        properties.append(converted)
    
    return properties
EOF

# 2. 메인 수집기 수정
cp fixed_naver_collector_v2_optimized.py fixed_naver_collector_v2_optimized.py.backup
cat >> fixed_naver_collector_v2_optimized.py << 'EOF'

# 🔥 신규 추가: 직접 DB 저장 기능
def collect_and_save_to_db(cortar_no: str, max_pages: int = 999):
    """수집 후 바로 DB에 저장"""
    from supabase_client import SupabaseHelper
    from json_to_db_converter import convert_json_file_to_properties
    import os
    
    print(f"🔄 {cortar_no} 지역 수집 및 DB 저장 시작")
    
    # 1. 기존 수집 로직 실행
    result = collect_by_cortar_no(cortar_no, include_details=True, max_pages=max_pages)
    
    if not result or result.get('total_collected', 0) == 0:
        print(f"❌ 수집된 데이터 없음")
        return None
    
    # 2. 수집된 JSON 파일 확인
    json_file = result.get('file_path')
    if not json_file or not os.path.exists(json_file):
        print(f"❌ JSON 파일 없음: {json_file}")
        return None
    
    # 3. JSON을 DB 형식으로 변환
    try:
        db_properties = convert_json_file_to_properties(json_file, cortar_no)
        print(f"✅ {len(db_properties)}개 매물 변환 완료")
    except Exception as e:
        print(f"❌ 변환 실패: {str(e)}")
        return None
    
    # 4. DB에 저장
    try:
        helper = SupabaseHelper()
        save_stats = helper.save_properties(db_properties, cortar_no)
        
        # 5. 일일 통계 저장
        helper.save_daily_stats(date.today(), cortar_no, db_properties, save_stats)
        
        print(f"✅ DB 저장 완료: {save_stats}")
        return {
            'collected_count': len(db_properties),
            'save_stats': save_stats,
            'json_file': json_file
        }
        
    except Exception as e:
        print(f"❌ DB 저장 실패: {str(e)}")
        return None

if __name__ == "__main__":
    # 테스트 실행
    test_cortar_no = "11680102"  # 강남구 역삼1동
    result = collect_and_save_to_db(test_cortar_no, max_pages=3)
    print(f"🎯 테스트 결과: {result}")
EOF
```

**검증 기준**:
- [ ] `json_to_db_converter.py` 생성됨
- [ ] 메인 수집기에 직접 저장 기능 추가됨
- [ ] 백업 파일이 생성됨

---

### Step 2.2: 직접 DB 저장 테스트 (30분)
**목표**: 새로운 직접 저장 방식이 정상 작동하는지 확인

**실행 단계**:
```bash
# 1. 소규모 테스트 실행
python -c "
from fixed_naver_collector_v2_optimized import collect_and_save_to_db
result = collect_and_save_to_db('11680102', max_pages=2)  # 역삼1동, 2페이지만
print(f'테스트 결과: {result}')
"

# 2. DB 저장 확인
python -c "
from supabase_client import SupabaseHelper
helper = SupabaseHelper()
recent = helper.client.table('properties').select('*').eq('cortar_no', '11680102').order('created_at', desc=True).limit(5).execute()
print(f'최근 저장된 매물: {len(recent.data)}개')
for prop in recent.data:
    print(f'- {prop[\"article_no\"]}: {prop[\"article_name\"][:20]}... (주소: {prop.get(\"address_road\", \"N/A\")})')
"
```

**검증 기준**:
- [ ] 테스트 수집이 성공적으로 완료됨
- [ ] DB에 매물 데이터가 올바르게 저장됨
- [ ] 주소 정보(address_road)가 NULL이 아님
- [ ] 위도/경도 정보가 0이 아님

**롤백 방법**:
```bash
# 테스트 데이터 정리
python -c "
from supabase_client import SupabaseHelper
helper = SupabaseHelper()
helper.client.table('properties').delete().eq('cortar_no', '11680102').gte('created_at', '2025-08-27').execute()
"
```

---

## 🛡️ Phase 3: Enhanced Safety Logic (Week 1)

### Step 3.1: 스마트 삭제 로직 구현 (1일)
**목표**: 연속 3일 미발견시에만 삭제하는 안전한 로직

**실행 단계**:
```python
# enhanced_property_manager.py
class EnhancedPropertyManager:
    def __init__(self):
        self.helper = SupabaseHelper()
        self.safety_days = 3  # 3일 연속 미발견시에만 삭제
    
    def safe_property_cleanup(self, cortar_no: str, current_article_nos: List[str]):
        """안전한 매물 정리 - 3일 규칙 적용"""
        
        # 1. 기존 활성 매물 조회
        existing = self.helper.client.table('properties')\
            .select('article_no, last_seen_date')\
            .eq('cortar_no', cortar_no)\
            .eq('is_active', True)\
            .execute()
        
        today = date.today()
        deletion_candidates = []
        
        # 2. 삭제 후보 검사
        for prop in existing.data:
            article_no = prop['article_no']
            
            if article_no not in current_article_nos:
                last_seen = prop.get('last_seen_date')
                if last_seen:
                    last_seen_date = datetime.strptime(last_seen, '%Y-%m-%d').date()
                    days_missing = (today - last_seen_date).days
                    
                    if days_missing >= self.safety_days:
                        deletion_candidates.append({
                            'article_no': article_no,
                            'days_missing': days_missing
                        })
                        print(f"🗑️ 삭제 예정: {article_no} ({days_missing}일 미발견)")
                    else:
                        print(f"⚠️ 유지: {article_no} ({days_missing}일 미발견 - 안전 기간 내)")
                else:
                    # 처음 발견된 경우 last_seen_date 설정
                    self.helper.client.table('properties')\
                        .update({'last_seen_date': today.isoformat()})\
                        .eq('article_no', article_no)\
                        .execute()
        
        # 3. 안전한 삭제 실행
        deleted_count = 0
        for candidate in deletion_candidates:
            try:
                self.helper.soft_delete_property(candidate['article_no'])
                deleted_count += 1
            except Exception as e:
                print(f"❌ 삭제 실패 {candidate['article_no']}: {str(e)}")
        
        print(f"📊 안전 정리 완료: {deleted_count}/{len(deletion_candidates)} 삭제")
        return deleted_count
```

**검증 기준**:
- [ ] 3일 규칙이 올바르게 적용됨
- [ ] 1-2일 미발견 매물은 삭제되지 않음
- [ ] 삭제 로그가 상세하게 기록됨

---

### Step 3.2: 실시간 품질 모니터링 (2일)
**목표**: 대량 삭제나 데이터 이상 징후 자동 감지

**실행 단계**:
```python
# quality_monitor.py
class RealTimeQualityMonitor:
    def __init__(self):
        self.helper = SupabaseHelper()
        self.thresholds = {
            'max_deletion_rate': 0.1,  # 10% 이상 삭제시 경고
            'min_address_rate': 0.9,   # 주소 정보 90% 이상 필수
            'max_null_coordinates': 0.05  # 좌표 없는 매물 5% 이하
        }
    
    def validate_collection_quality(self, cortar_no: str, new_properties: List[Dict]):
        """수집 품질 실시간 검증"""
        warnings = []
        
        # 1. 주소 정보 비율 체크
        address_missing = sum(1 for p in new_properties if not p.get('address_road'))
        address_rate = 1 - (address_missing / len(new_properties))
        
        if address_rate < self.thresholds['min_address_rate']:
            warnings.append(f"❌ 주소 정보 부족: {address_rate:.1%} (기준: {self.thresholds['min_address_rate']:.1%})")
        
        # 2. 좌표 정보 체크
        coord_missing = sum(1 for p in new_properties 
                           if not p.get('latitude') or not p.get('longitude') 
                           or p.get('latitude') == 0 or p.get('longitude') == 0)
        coord_rate = coord_missing / len(new_properties)
        
        if coord_rate > self.thresholds['max_null_coordinates']:
            warnings.append(f"❌ 좌표 정보 부족: {coord_rate:.1%} (기준: {self.thresholds['max_null_coordinates']:.1%})")
        
        # 3. 삭제율 체크 (기존 매물 대비)
        existing_count = self.helper.client.table('properties')\
            .select('article_no', count='exact')\
            .eq('cortar_no', cortar_no)\
            .eq('is_active', True)\
            .execute().count
        
        if existing_count > 0:
            deletion_rate = max(0, 1 - (len(new_properties) / existing_count))
            if deletion_rate > self.thresholds['max_deletion_rate']:
                warnings.append(f"⚠️ 높은 삭제율: {deletion_rate:.1%} (기준: {self.thresholds['max_deletion_rate']:.1%})")
        
        return warnings
    
    def emergency_stop_if_needed(self, warnings: List[str]) -> bool:
        """심각한 문제 발생시 자동 중단"""
        critical_warnings = [w for w in warnings if w.startswith("❌")]
        
        if len(critical_warnings) >= 2:
            print("🚨 EMERGENCY STOP: 심각한 품질 문제 감지")
            print("\n".join(critical_warnings))
            return True
        
        return False
```

**검증 기준**:
- [ ] 품질 모니터링이 실시간으로 작동함
- [ ] 임계값 초과시 경고 발생함
- [ ] 심각한 문제 발생시 자동 중단됨

---

## 🚀 Phase 4: Unified System (Month 1)

### Step 4.1: 완전 통합 수집기 클래스 (1주)
**목표**: 수집+저장+품질검증+모니터링을 하나로 통합

```python
# unified_collector.py
class UnifiedCollector:
    def __init__(self):
        self.collector = NaverCollector()
        self.db_helper = SupabaseHelper()
        self.quality_monitor = RealTimeQualityMonitor()
        self.property_manager = EnhancedPropertyManager()
    
    def collect_and_process(self, cortar_no: str, max_pages: int = 999):
        """완전 통합 수집 및 처리"""
        
        # 1. 수집 실행
        collected_data = self.collector.collect_by_cortar_no(cortar_no, max_pages)
        
        if not collected_data:
            return None
        
        # 2. 데이터 변환
        properties = JsonToDbConverter.convert_properties(collected_data, cortar_no)
        
        # 3. 품질 검증
        warnings = self.quality_monitor.validate_collection_quality(cortar_no, properties)
        
        if self.quality_monitor.emergency_stop_if_needed(warnings):
            return {'status': 'emergency_stopped', 'warnings': warnings}
        
        # 4. DB 저장
        save_stats = self.db_helper.save_properties(properties, cortar_no)
        
        # 5. 안전한 정리
        current_article_nos = [p['article_no'] for p in properties]
        cleanup_stats = self.property_manager.safe_property_cleanup(cortar_no, current_article_nos)
        
        # 6. 통계 저장
        self.db_helper.save_daily_stats(date.today(), cortar_no, properties, save_stats)
        
        return {
            'status': 'success',
            'collected': len(properties),
            'save_stats': save_stats,
            'cleanup_stats': cleanup_stats,
            'warnings': warnings
        }
```

**검증 기준**:
- [ ] 통합 클래스가 모든 기능을 성공적으로 실행함
- [ ] 품질 검증이 각 단계에서 작동함
- [ ] 로그가 상세하게 기록됨

---

### Step 4.2: 배치 처리 시스템 (3일)
**목표**: 강남구 전체를 자동으로 순차 처리

```python
# batch_processor.py
class BatchProcessor:
    def __init__(self):
        self.unified_collector = UnifiedCollector()
        self.gangnam_cortars = [
            "11680101", "11680102", "11680103", "11680104",  # 역삼동
            "11680105", "11680106", "11680107",              # 개포동
            # ... 강남구 전체 코드
        ]
    
    def process_gangnam_district(self):
        """강남구 전체 배치 처리"""
        results = {}
        
        for cortar_no in self.gangnam_cortars:
            print(f"🔄 처리 중: {cortar_no}")
            
            result = self.unified_collector.collect_and_process(cortar_no)
            results[cortar_no] = result
            
            # 성공률 체크
            if result and result.get('status') == 'success':
                print(f"✅ {cortar_no}: {result['collected']}개 수집")
            else:
                print(f"❌ {cortar_no}: {result}")
            
            # 적절한 대기 시간 (API 제한 고려)
            time.sleep(5)
        
        return results
```

---

## 📊 Phase 5: Production Deployment (Week 3-4)

### Step 5.1: 자동 백업 시스템 (2일)
```python
# backup_system.py
class AutomatedBackupSystem:
    def daily_backup(self):
        """일일 자동 백업"""
        # 1. DB 백업
        # 2. 코드 백업  
        # 3. 로그 백업
        # 4. 백업 검증
        pass
    
    def emergency_rollback(self, backup_date: str):
        """응급 롤백"""
        pass
```

### Step 5.2: 실시간 모니터링 대시보드 (3일)
```python
# monitoring_dashboard.py
class MonitoringDashboard:
    def real_time_status(self):
        """실시간 상태 모니터링"""
        return {
            'active_properties': self.get_active_count(),
            'daily_collection': self.get_today_stats(),
            'quality_metrics': self.get_quality_metrics(),
            'error_alerts': self.get_recent_errors()
        }
```

---

## 📋 실행 체크리스트

### ✅ Phase 1: Emergency (TODAY)
- [ ] Step 1.1: json_to_supabase.py 중단 (30분)
- [ ] Step 1.2: 데이터 복구 (60분) 
- [ ] Step 1.3: 백업 및 검증 (15분)

### ✅ Phase 2: Direct Integration (TODAY)
- [ ] Step 2.1: 직접 DB 저장 구현 (90분)
- [ ] Step 2.2: 테스트 및 검증 (30분)

### ⏳ Phase 3: Safety Enhancement (Week 1)
- [ ] Step 3.1: 스마트 삭제 로직
- [ ] Step 3.2: 품질 모니터링

### 🚀 Phase 4: Unified System (Month 1)
- [ ] Step 4.1: 통합 수집기
- [ ] Step 4.2: 배치 처리

### 🏁 Phase 5: Production (Month 1)
- [ ] Step 5.1: 백업 시스템
- [ ] Step 5.2: 모니터링 대시보드

---

## 🎯 성공 지표

### Phase 1 성공 지표:
- **손실 방지**: 추가 데이터 삭제 0건
- **복구율**: 50% 이상 매물 복구
- **백업 완료**: 전체 시스템 백업 완료

### Phase 2 성공 지표:
- **직접 저장**: JSON 거치지 않는 저장 성공
- **주소 완성도**: 95% 이상 주소 정보 보유
- **좌표 정확도**: 90% 이상 정확한 좌표

### Final 성공 지표:
- **시스템 안정성**: 99% 이상 정상 작동률
- **데이터 품질**: 95% 이상 완전한 매물 정보
- **자동화율**: 100% 수동 개입 없는 수집

---

## 🚨 긴급 연락처 및 롤백

### 긴급시 즉시 실행:
```bash
# 1. 모든 자동 프로세스 중단
pkill -f python
crontab -r

# 2. 백업에서 복구
pg_dump 복구명령어...

# 3. 이전 버전으로 코드 복구  
git checkout HEAD~1
```

### 문제 발생시 단계별 롤백:
1. **Phase 1 실패**: 크론탭 복구, 데이터 복구 취소
2. **Phase 2 실패**: 백업 코드로 복구
3. **Phase 3+ 실패**: 이전 Phase로 롤백

---

**💡 핵심 성공 요소**: 각 단계를 완료한 후 반드시 검증하고, 문제 발생시 즉시 이전 단계로 롤백할 준비를 해야 합니다!