# 완전성 우선 구 단위 수집 가이드

## 🎯 **시스템 개요**

완전성을 보장하면서 효율성을 최적화하는 **3단계 자동화 수집 시스템**

```
🔍 분석 → 📋 계획 → 🚀 수집
```

## 📂 **파일 구조**

```
collectors/
├── gu_config.json                    # 구별 설정 (강남구, 송파구)
├── complete_area_analyzer.py         # 완전 지역 분석기
├── batch_collection_scheduler.py     # 배치 수집 스케줄러  
├── complete_gu_collector.py          # 통합 실행기
└── fixed_naver_collector.py          # 기존 수집기 (개선됨)
```

## 🚀 **사용법**

### **방법 1: 완전 자동 수집**
```bash
# 강남구 전체 자동 분석 → 계획 → 수집
python complete_gu_collector.py 강남구

# 송파구 전체 자동 수집
python complete_gu_collector.py 송파구
```

### **방법 2: 단계별 실행**
```bash
# 1단계: 지역 분석
python complete_area_analyzer.py 강남구

# 2단계: 배치 수집 (생성된 계획 파일 사용)
python batch_collection_scheduler.py collection_plan_강남구_20250804_143000.json
```

### **방법 3: 기존 계획 재사용**
```bash
# 기존 분석 결과 재사용
python complete_gu_collector.py 강남구 --plan-file collection_plan_강남구_20250804_143000.json
```

## 📊 **수집 단계별 설명**

### **Phase 1: 완전 지역 분석** 🔍
- **격자 스캔**: 구 전체를 25x25 격자로 완전 스캔
- **줌 조정**: 다양한 줌 레벨(14-16)로 보완 탐색
- **나선형 스캔**: 빠뜨린 지역 최종 탐색
- **완전성 검증**: 예상 동 수와 비교하여 누락 확인

### **Phase 2: 수집 계획 수립** 📋
- **매물 밀도 분석**: 각 지역별 예상 매물 수 확인
- **우선순위 분류**:
  - 🔥 **고우선순위**: 100개 이상 (즉시 수집)
  - 🔶 **중우선순위**: 30-99개 (30분 후)
  - 🔵 **저우선순위**: 1-29개 (1시간 후)
  - ⚪ **확인용**: 0개 (검증 목적)

### **Phase 3: 배치 수집 실행** 🚀
- **시간 분산**: 30분 간격으로 배치 실행
- **실시간 저장**: 메모리 절약 스트리밍 방식
- **오류 복구**: 실패 지역 자동 재시도
- **진행 모니터링**: 실시간 진행 상황 추적

## 🔧 **설정 커스터마이징**

### **구별 설정 수정** (`gu_config.json`)
```json
{
  "supported_gu": {
    "새로운구": {
      "gu_code": "구코드",
      "center_coordinate": [위도, 경도, 줌],
      "expected_dong_count": 예상동수,
      "scan_config": {
        "grid_size": 25,        // 격자 크기
        "max_zoom": 16,         // 최대 줌 레벨
        "scan_radius_km": 8     // 스캔 반경
      },
      "collection_priority": {
        "high_density_threshold": 100,    // 고밀도 기준
        "medium_density_threshold": 30,   // 중밀도 기준
        "batch_delay_minutes": 30         // 배치 간 딜레이
      }
    }
  }
}
```

## 📈 **결과 파일들**

### **분석 결과**
- `collection_plan_강남구_YYYYMMDD_HHMMSS.json`: 수집 계획
- `batch_execution_result_강남구_YYYYMMDD_HHMMSS.json`: 실행 결과
- `final_summary_강남구_YYYYMMDD_HHMMSS.json`: 최종 요약

### **수집 데이터**
- `area_강남구_지역코드_YYYYMMDD_HHMMSS.json`: 지역별 매물 데이터

## 🔍 **모니터링 & 디버깅**

### **진행 상황 확인**
```bash
# 실행 중 로그 확인
tail -f area_강남구_1168010400_*.json

# 계획 파일 확인
cat collection_plan_강남구_*.json | jq '.collection_batches'
```

### **문제 해결**
```bash
# 특정 배치만 재실행
python batch_collection_scheduler.py collection_plan_강남구_20250804_143000.json

# 분석만 다시 실행
python complete_area_analyzer.py 강남구
```

## ⚡ **성능 최적화**

### **수집 속도 조정**
- `collection_delay_seconds`: 지역 간 딜레이 (기본: 2초)
- `batch_rest_minutes`: 배치 간 휴식 (기본: 30분)

### **메모리 최적화**
- 스트리밍 방식으로 메모리 사용량 최소화
- 대용량 데이터도 안전하게 처리

## 🎯 **예상 결과**

### **강남구 수집 예상**
- **총 지역**: ~26개 동
- **예상 매물**: ~2,500개
- **실행 시간**: 3-4시간
- **성공률**: 95% 이상

### **송파구 수집 예상**  
- **총 지역**: ~28개 동
- **예상 매물**: ~2,000개
- **실행 시간**: 3-4시간
- **성공률**: 95% 이상

## 🔧 **확장성**

### **새로운 구 추가**
1. `gu_config.json`에 구 정보 추가
2. `expected_dongs` 리스트 작성
3. 좌표 및 임계값 설정
4. 바로 실행 가능!

### **다른 매물 타입 지원**
- 아파트: `realEstateType` 변경
- 오피스텔: `purpose` 변경
- 설정 파일에서 쉽게 수정 가능

이제 **완전성을 보장하면서도 효율적인** 대규모 부동산 데이터 수집이 가능합니다!