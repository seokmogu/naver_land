# 🏗️ 네이버 부동산 수집기 - 스키마 완성 가이드

이 가이드는 30% 데이터 손실 문제를 해결하기 위한 스키마 수정을 완료하는 방법을 설명합니다.

## 📋 문제 상황

**검증 결과에서 발견된 문제들:**
- ❌ `space_type` 컬럼 누락 (property_physical 테이블)
- ❌ `law_usage` 컬럼 누락 (properties_new 테이블)
- ❌ `property_facilities` 테이블 완전 누락
- ❌ 기타 19개 컬럼 누락
- ❌ 데이터 검증 뷰 누락

## 🎯 해결 방법

### 1단계: SQL 스크립트 실행 (필수!)

**파일:** `COMPLETE_SCHEMA_FIX.sql`

**실행 방법:**
1. [Supabase Dashboard](https://supabase.com/dashboard) 로그인
2. 프로젝트 선택: `eslhavjipwbyvbbknixv`
3. 좌측 메뉴에서 `SQL Editor` 선택
4. `COMPLETE_SCHEMA_FIX.sql` 파일의 내용을 복사-붙여넣기
5. `RUN` 버튼 클릭하여 실행

**예상 실행 시간:** 2-3분

### 2단계: 빠른 검증

SQL 실행 후 즉시 검증:
```bash
python verify_schema_completion.py
```

**성공 기준:** 90% 이상 검증 통과

### 3단계: 전체 검증 (선택적)

더 상세한 검증을 원한다면:
```bash
python test_schema_deployment.py
```

### 4단계: 데이터 수집 시작

검증 성공 후:
```bash
python enhanced_data_collector.py
```

## 🚨 주요 해결 항목

### 중요한 누락 컴포넌트들

1. **space_type 컬럼** (property_physical 테이블)
   - 용도: 공간 유형 저장 (원룸, 투룸 등)
   - 데이터 손실 영향: 높음

2. **law_usage 컬럼** (properties_new 테이블)
   - 용도: 법적 용도 저장 (주거용, 상업용 등)
   - 데이터 손실 영향: 높음

3. **property_facilities 테이블**
   - 용도: 매물 시설 정보 저장
   - 데이터 손실 영향: 중간

4. **기타 확장 컬럼들**
   - veranda_count, monthly_management_cost, subway_stations 등
   - 데이터 손실 영향: 낮음-중간

5. **시설 유형 확장**
   - 기존 7개 → 19개로 확장
   - 새로운 시설: 정수기, 가스레인지, 냉장고, 세탁기 등

## 📊 스키마 수정 내용 상세

### 테이블 생성/수정
- ✅ `property_facilities` 테이블 생성
- ✅ `property_tax_info` 테이블 확인/생성
- ✅ `property_price_comparison` 테이블 확인/생성

### 컬럼 추가
- ✅ `property_physical`: 9개 컬럼 추가
- ✅ `properties_new`: 3개 컬럼 추가
- ✅ `property_locations`: 3개 컬럼 추가

### 성능 최적화
- ✅ 11개 새로운 인덱스 생성
- ✅ GIN 인덱스 (JSONB 컬럼용)
- ✅ 복합 인덱스 (검색 성능 향상)

### 자동화 기능
- ✅ 세금 총액 자동 계산 트리거
- ✅ updated_at 자동 업데이트 트리거
- ✅ 데이터 품질 검증 뷰

## 🔍 검증 체크리스트

### SQL 실행 후 확인사항

1. **오류 없이 실행 완료**
   - 대부분의 "already exists" 오류는 무시 가능
   - 심각한 오류 없이 완료되어야 함

2. **check_schema_fix_completion() 함수 결과**
   - 모든 항목이 '✅ 존재' 또는 '✅ 완료'여야 함
   - SQL 실행 결과 하단에 자동 표시됨

3. **Python 검증 스크립트**
   ```bash
   python verify_schema_completion.py
   ```
   - 90% 이상 검증 통과 필요

## ⚠️ 문제 해결

### 자주 발생하는 문제들

1. **"already exists" 오류**
   - **해결:** 무시하고 계속 진행 (정상)

2. **외래키 제약조건 오류**
   - **해결:** 참조 테이블이 존재하는지 확인

3. **권한 오류**
   - **해결:** service_role 키 사용 확인

4. **컬럼이 여전히 누락**
   - **해결:** ALTER TABLE 부분만 다시 실행

### 수동 복구 방법

가장 중요한 2개 컬럼만 수동 추가:
```sql
ALTER TABLE property_physical ADD COLUMN IF NOT EXISTS space_type VARCHAR(100);
ALTER TABLE properties_new ADD COLUMN IF NOT EXISTS law_usage VARCHAR(100);
```

## 📈 예상 효과

### Before (수정 전)
- ❌ 30% 데이터 손실
- ❌ 핵심 정보 누락
- ❌ 시설 정보 저장 불가
- ❌ 세금 정보 저장 불가

### After (수정 후)
- ✅ 5% 이하 데이터 손실
- ✅ 모든 API 섹션 저장 지원
- ✅ 완전한 매물 정보 저장
- ✅ 자동 데이터 검증

## 🎉 성공 확인

모든 단계 완료 후 다음 메시지가 나오면 성공:

```
🎉 스키마 완료 검증 성공!
✅ 모든 중요 컴포넌트가 정상적으로 생성되었습니다.
```

이후 `enhanced_data_collector.py`로 데이터 수집을 시작하면 30% 데이터 손실 문제가 해결됩니다!

---

## 📞 지원

문제 발생 시:
1. 오류 메시지 전체 복사
2. 실행한 단계 명시
3. `verify_schema_completion.py` 실행 결과 첨부