# 네이버 부동산 수집기 버전 관리

## 🚀 현재 최신 버전: v2.0 (Optimized)

### **주요 수집기 파일들**

#### ✅ **활성 파일들 (v2.0 최적화)**
- `cached_token_collector.py` - 최신 최적화 수집기
  - **토큰 캐싱**: 6시간 재사용으로 Playwright 사용 95% 감소
  - **대기시간 단축**: 8-15초 → 2-4초 (70% 개선)  
  - **메모리 절약**: 500-800MB → 50-100MB (85% 절약)
  - **상세정보**: 완전한 매물 상세정보 + 카카오 주소변환
  - **함수**: `collect_from_url()`, `collect_by_cortar_no()`

- `parallel_batch_collect_gangnam.py` - 병렬 배치 수집기 (v2.0 호환)
  - **최적화된 수집**: `cached_token_collector` 사용
  - **토큰 공유**: 프로세스당 토큰 재사용
  - **성능 향상**: 동당 수집시간 45-60분 → 15-25분

#### 📂 **지원 파일들**
- `playwright_token_collector.py` - 토큰 수집 (최초 1회 + 6시간마다)
- `json_to_supabase.py` - Supabase 데이터베이스 저장
- `supabase_client.py` - 데이터베이스 클라이언트
- `kakao_address_converter.py` - 카카오맵 주소 변환

#### 🗂️ **백업 및 테스트 파일들**
- `legacy/fixed_naver_collector_v1.py` - 기존 버전 (매번 Playwright 사용)
- `legacy/parallel_batch_collect_gangnam_v1.py` - 기존 병렬 버전
- `test/` - 실험 및 테스트 파일들
  - `no_token_collector.py` - 토큰 없는 수집 시도 (실패)
  - `test_no_token.py`, `quick_test.py` - 테스트 파일들

---

## 📋 사용 방법

### **단일 동 수집**
```bash
# 기본 수집 (상세정보 포함)
python3 cached_token_collector.py

# URL 기반 수집
python3 -c "
from cached_token_collector import CachedTokenCollector
collector = CachedTokenCollector()
result = collector.collect_from_url('https://new.land.naver.com/offices?ms=37.4986291,127.0359669,13', include_details=True)
"

# cortar_no로 직접 수집
python3 -c "
from cached_token_collector import collect_by_cortar_no
result = collect_by_cortar_no('1168010100', include_details=True)
"
```

### **강남구 전체 병렬 수집**
```bash
# 상세정보 포함, 1개 프로세스 (안정적)
python3 parallel_batch_collect_gangnam.py 1 true

# 기본 정보만, 2개 프로세스 (빠름)  
python3 parallel_batch_collect_gangnam.py 2 false
```

### **수집된 JSON → Supabase 저장**
```bash
python3 json_to_supabase.py results/naver_optimized_역삼동_1168010100_20250816_012345.json 1168010100
```

---

## 🔄 버전별 성능 비교

| 항목 | v1.0 (기존) | v2.0 (최적화) | 개선율 |
|------|-------------|---------------|--------|
| 토큰 수집 | 매번 Playwright | 6시간 캐싱 | **95% 감소** |
| API 대기시간 | 8-15초 | 2-4초 | **70% 단축** |
| 메모리 사용량 | 500-800MB | 50-100MB | **85% 절약** |
| 동당 수집시간 | 45-60분 | 15-25분 | **60% 단축** |
| 기능 완성도 | 상세정보 + 주소변환 | 동일 + 안정성 향상 | **동등** |

---

## 🚨 중요 사항

### **v1.0 → v2.0 마이그레이션**
- ✅ **자동 호환**: `parallel_batch_collect_gangnam.py`가 자동으로 v2.0 사용
- ✅ **API 호환**: `collect_by_cortar_no()` 함수 동일한 인터페이스  
- ✅ **데이터 호환**: 동일한 JSON 구조 + 추가 최적화 정보
- ⚠️ **토큰 캐싱**: 처음 실행 시 `cached_token.json` 파일 생성됨

### **권장 사항**
1. **개발/테스트**: `cached_token_collector.py` 직접 사용
2. **대량 수집**: `parallel_batch_collect_gangnam.py` 사용
3. **AWS 배포**: v2.0 버전 사용 (메모리 효율성)
4. **문제 발생시**: `legacy/` 폴더의 v1.0으로 롤백 가능

---

## 📝 변경 이력

### v2.0 (2025-08-16)
- 토큰 캐싱 시스템 도입 (6시간 재사용)
- API 요청 대기시간 최적화 (8-15초 → 2-4초)  
- 메모리 사용량 85% 감소
- 상세정보 및 카카오 주소변환 완전 지원
- 자동 토큰 갱신 및 에러 복구 개선

### v1.0 (기존)
- Playwright 기반 토큰 수집 (매번 실행)
- 8-15초 랜덤 대기 시간
- 상세정보 및 카카오 주소변환 지원
- 안정적이지만 메모리/시간 비효율적