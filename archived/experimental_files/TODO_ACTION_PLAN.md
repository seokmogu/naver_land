# 🚨 네이버 부동산 수집기 개선 계획 (최종 수정)

**작성일**: 2025-08-27  
**상태**: 문제 원인 정확히 파악됨  
**우선순위**: 잘못된 삭제 로직 수정 > 통합 수집기 > 모니터링

---

## 🔍 **문제 원인 정확히 파악됨**

### ✅ **수집기는 정상 작동**
```
✅ 네이버 API 호출 성공 (토큰 정상)
✅ 매물 상세정보 수집 완료 (위도/경도 포함)
✅ 카카오 주소 변환 정상 작동
✅ JSON 파일에 완벽한 데이터 저장

예시: 
"위치정보": {
  "정확한_위도": "37.4996424",
  "정확한_경도": "127.0358454"
},
"카카오주소변환": {
  "도로명주소": "서울특별시 강남구 테헤란로26길 10",
  "지번주소": "서울 강남구 역삼동 736-55"
}
```

### 🚨 **진짜 문제: JSON→DB 저장 과정의 잘못된 삭제 로직**
```
❌ json_to_supabase.py가 기존 매물을 "삭제된 것"으로 잘못 판단
❌ 새로 수집한 20개만 남기고 수백개 매물을 삭제 처리
❌ 이 과정에서 기존 매물의 주소 정보 손실
❌ daily_stats 업데이트도 이 과정에서 누락

로그 예시:
🗑️ 삭제 이력 저장: 2542368337 (활성 기간: None일)
🗑️ 삭제 이력 저장: 2542371076 (활성 기간: None일)
... (수백개 매물 삭제)
```

---

## 📋 **즉시 해야할 일 (오늘)**

### ⚡ **Priority 1: 잘못된 삭제 로직 긴급 중단**

- [ ] **json_to_supabase.py 사용 즉시 중단**
  - 파일: 모든 크론탭, 스케줄링 스크립트
  - 작업: json_to_supabase.py 호출하는 모든 스크립트 비활성화
  - 목표: 추가 데이터 손실 방지

- [ ] **잘못 삭제된 매물 복구**
  - 파일: `emergency_data_recovery.py` (신규 작성)
  - 작업: deletion_history에서 최근 삭제된 매물을 다시 활성화
  - 목표: 8월 16일 이후 잘못 삭제된 매물 복원

### ⚡ **Priority 2: 수집기 DB 직접 저장 방식으로 변경**

- [ ] **fixed_naver_collector_v2_optimized.py 수정**
  - 파일: `fixed_naver_collector_v2_optimized.py`
  - 작업: collect_by_cortar_no 함수에 SupabaseHelper 직접 호출 추가
  - 목표: JSON 파일 거치지 않고 바로 DB 저장

```python
# 수정할 부분 예시
def collect_by_cortar_no(cortar_no: str, include_details: bool = True, max_pages: int = 999):
    # 기존 수집 로직...
    
    # 🔥 신규 추가: 수집 후 바로 DB 저장
    if total_collected > 0:
        from supabase_client import SupabaseHelper
        helper = SupabaseHelper()
        
        # JSON → dict 변환 후 DB 저장
        properties_data = convert_json_to_properties(collected_data)
        save_stats = helper.save_properties(properties_data, cortar_no)
        
        # daily_stats도 함께 저장
        helper.save_daily_stats(date.today(), cortar_no, properties_data, save_stats)
        
        print(f"✅ DB 직접 저장 완료: {save_stats}")
```

- [ ] **데이터 변환 함수 구현**
  - 파일: `json_to_db_converter.py` (신규)
  - 작업: JSON 형식을 properties 테이블 형식으로 변환하는 함수
  - 목표: 기존 JSON 구조를 DB 스키마에 맞게 변환

---

## 📅 **1주일 내 해야할 일**

### 🔧 **Priority 3: json_to_supabase.py 삭제 로직 완전 수정**

- [ ] **매물 삭제 판단 로직 개선**
  - 파일: `json_to_supabase.py`
  - 문제: 1회 수집으로 기존 매물을 "삭제"로 판단하는 오류
  - 개선: 연속 3일 이상 미발견시에만 삭제 처리
  
```python
# ❌ 현재 잘못된 로직
for article_no in existing_map:
    if article_no not in collected_ids:
        # 바로 삭제 처리 (위험!)
        delete_property(article_no)

# ✅ 개선된 로직  
for article_no in existing_map:
    if article_no not in collected_ids:
        # 최종 확인일 체크
        last_seen = existing_map[article_no]['last_seen_date']
        days_missing = (today - last_seen).days
        
        if days_missing >= 3:  # 3일 이상 미발견시에만
            delete_property(article_no)
        else:
            print(f"⚠️ {article_no}: {days_missing}일 미발견 (유지)")
```

### 🔧 **Priority 4: 자동 복구 시스템**

- [ ] **일일 건강성 체크 시스템**
  - 파일: `daily_health_monitor.py` (신규)
  - 작업: 매일 데이터 품질, 수집 상태, 삭제 이상 징후 체크
  - 목표: 유사한 문제 재발 방지

- [ ] **실시간 경고 시스템**
  - 파일: `alert_system.py` (신규)  
  - 작업: 대량 삭제 감지시 즉시 중단 및 알림
  - 목표: 문제 발생시 자동 대응

---

## 📅 **1달 내 해야할 일**

### 🚀 **Priority 5: 완전 통합 수집기**

- [ ] **UnifiedCollector 클래스 구현**
  - 파일: `unified_collector.py` (신규)
  - 작업: 수집+저장+통계+로그를 원스톱 처리
  - 목표: 분산된 프로세스 통합

- [ ] **배치 처리 시스템**
  - 파일: `batch_collector.py` (신규)
  - 작업: 여러 지역을 효율적으로 순차 수집
  - 목표: 강남구 전체 자동 수집

### 🚀 **Priority 6: 고도화**

- [ ] **실시간 모니터링 대시보드**
  - 파일: `real_time_dashboard.py` (신규)
  - 작업: 수집 상태, 데이터 품질, 에러 현황 실시간 표시
  - 목표: 문제 조기 발견

- [ ] **서울 전체 확장**
  - 작업: 25개 구 전체로 수집 범위 확장
  - 목표: 서울 전체 부동산 시장 커버

---

## 🔧 **구체적 수정 코드**

### **1. 긴급 데이터 복구 스크립트**

```python
# emergency_data_recovery.py
def restore_wrongly_deleted_properties():
    """잘못 삭제된 매물 복구"""
    helper = SupabaseHelper()
    
    # 8월 16일 이후 삭제된 매물 조회
    deleted_properties = helper.client.table('deletion_history')\
        .select('article_no')\
        .gte('deleted_date', '2025-08-16')\
        .execute()
    
    for prop in deleted_properties.data:
        article_no = prop['article_no']
        
        # properties 테이블에서 다시 활성화
        helper.client.table('properties')\
            .update({'is_active': True, 'deleted_at': None})\
            .eq('article_no', article_no)\
            .execute()
        
        print(f"✅ 복구: {article_no}")
```

### **2. 수집기 DB 직접 저장 수정**

```python
# fixed_naver_collector_v2_optimized.py 수정
def collect_and_save_directly(cortar_no: str):
    """수집 + DB 직접 저장"""
    
    # 1. 기존 수집 로직
    collected_properties = collect_articles(cortar_no, max_pages=999)
    
    # 2. 🔥 신규: DB 직접 저장  
    if collected_properties:
        helper = SupabaseHelper()
        
        # JSON 형식을 DB 형식으로 변환
        db_properties = []
        for prop in collected_properties:
            db_prop = {
                'article_no': prop['매물번호'],
                'article_name': prop['매물명'],
                'real_estate_type': prop['부동산타입'],
                'trade_type': prop['거래타입'],
                'price': parse_price(prop['매매가격']),
                'rent_price': parse_price(prop['월세']),
                'area1': prop['전용면적'],
                'area2': prop['공급면적'],
                'floor_info': prop['층정보'],
                'direction': prop['방향'],
                'tag_list': prop['태그'],
                'description': prop['설명'],
                'details': prop['상세정보'],
                'cortar_no': cortar_no,
                'collected_date': date.today().isoformat(),
                'is_active': True
            }
            
            # 카카오 주소 정보 추가
            kakao_info = prop['상세정보'].get('카카오주소변환', {})
            if kakao_info:
                db_prop.update({
                    'address_road': kakao_info.get('도로명주소'),
                    'address_jibun': kakao_info.get('지번주소'), 
                    'building_name': kakao_info.get('건물명'),
                    'postal_code': kakao_info.get('우편번호')
                })
            
            # 위치 정보 추가
            location_info = prop['상세정보'].get('위치정보', {})
            if location_info:
                db_prop.update({
                    'latitude': float(location_info.get('정확한_위도', 0)),
                    'longitude': float(location_info.get('정확한_경도', 0))
                })
            
            db_properties.append(db_prop)
        
        # DB 저장
        save_stats = helper.save_properties(db_properties, cortar_no)
        helper.save_daily_stats(date.today(), cortar_no, db_properties, save_stats)
        
        return save_stats
    
    return None
```

---

## 📊 **성공 지표**

### **즉시 목표 (오늘)**
- [ ] json_to_supabase.py 중단으로 추가 데이터 손실 방지
- [ ] 잘못 삭제된 매물 50% 이상 복구
- [ ] 수집기 DB 직접 저장 방식 구현 완료

### **단기 목표 (1주일)**  
- [ ] 주소 정보 NULL 비율 5% 이하 달성
- [ ] daily_stats 업데이트 지연 0일 달성
- [ ] 매물 삭제 오판율 1% 이하 달성

### **중기 목표 (1달)**
- [ ] 완전 자동화된 수집 시스템 완성
- [ ] 실시간 모니터링 대시보드 운영
- [ ] 데이터 품질 자동 복구율 95% 이상

---

## ⚠️ **중요 주의사항**

### **절대 금지사항**
1. **json_to_supabase.py 함부로 실행 금지** - 추가 데이터 손실 위험
2. **대량 삭제 작업시 반드시 백업** - 복구 불가능한 손실 방지  
3. **운영 중인 시스템 함부로 변경 금지** - 점진적 개선만

### **반드시 확인할 것**
1. **매일 데이터 품질 체크** - 삭제 이상 징후 조기 발견
2. **수집 완료 후 즉시 검증** - 저장된 데이터 품질 확인
3. **변경사항 단계별 테스트** - 운영 적용 전 충분한 검증

---

## 🎯 **실행 우선순위**

### **🔥 극한 긴급 (지금 당장)**
1. json_to_supabase.py 사용 중단
2. 잘못 삭제된 매물 복구

### **⚡ 긴급 (오늘 내)**  
1. 수집기 DB 직접 저장 방식 구현
2. 응급 모니터링 시스템 구축

### **🔧 중요 (1주일 내)**
1. 삭제 로직 완전 수정
2. 자동 복구 시스템 구축

### **🚀 장기 (1달 내)**
1. 통합 수집기 시스템
2. 실시간 모니터링 대시보드

---

**💡 핵심: json_to_supabase.py의 잘못된 삭제 로직이 모든 문제의 근원입니다. 수집기 자체는 완벽하게 작동하므로, DB 직접 저장 방식으로 변경하면 모든 문제가 해결됩니다!**