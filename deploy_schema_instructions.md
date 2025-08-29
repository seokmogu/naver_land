# 스키마 배포 안내

## ✅ 현재 상황 확인
- 기본 데이터 수집기는 작동 중 (매물 정보, 이미지, 가격 저장 성공)
- 새로운 컬럼/테이블 누락으로 일부 고급 기능 제한

## 🚀 스키마 배포 절차

### 1. Supabase SQL Editor에서 실행
다음 파일을 순서대로 실행:

```sql
-- 1단계: 메인 스키마 업데이트
-- 파일: comprehensive_schema_update.sql
-- 내용: 새 테이블 2개 + 기존 테이블에 컬럼 15개+ 추가

-- 2단계: 참조 데이터 추가  
-- 파일: populate_missing_reference_data.sql
-- 내용: 시설 유형 7개→19개 확장 데이터

-- 3단계: 검증
-- 파일에서 마지막 SELECT check_comprehensive_schema_update(); 실행
```

### 2. 스키마 배포 완료 후 활성화할 기능들

#### enhanced_data_collector.py에서 주석 제거:
```python
# 현재 주석처리된 컬럼들 활성화:
'building_use': basic_info.get('building_use'),
'law_usage': basic_info.get('law_usage'),  
'floor_layer_name': basic_info.get('floor_layer_name'),
'approval_date': basic_info.get('approval_date'),

# location 테이블 새 컬럼들:
'subway_stations': ...,
'cortar_no': ...,
'floor_description': ...,
```

## 📊 예상 결과
- **30% 데이터 손실** → **5% 이하** 감소
- **세금 정보** 완전 저장 (현재 0% → 95%+)
- **시설 정보** 7개 → 19개 유형 지원
- **API 8개 섹션** 완전 활용

## 🔧 배포 후 즉시 테스트
```bash
python enhanced_data_collector.py --test-single --limit 1
```

모든 기능이 정상 작동하면 30% 데이터 손실 문제가 해결됩니다!