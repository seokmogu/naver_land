# 네이버 부동산 데이터 수집/DB 매핑 개선 후속 작업 문서

## 1. 문제 요약
- 현재 `properties` 테이블은 50개 이상의 컬럼을 포함하고 있으며, **가격/공간/시설/이미지/중개사/세금** 등 성격이 다른 데이터가 한 곳에 몰려 있음.
- 일부 필드(`deposit`, `exclusiveRate`, `articleRealtor`, `articleTax`)는 **컬럼이 없어 누락**되거나 `details(jsonb)`에만 저장됨.
- 월세 매물의 경우 **보증금과 월세가 분리 저장되지 않고 있음** → `deposit_price` 컬럼 필요.

---

## 2. 단기 개선 (빠른 대응)
1. **누락된 핵심 컬럼 추가**
   - `deposit_price` (보증금)
   - `representative_image_url` (대표 이미지)
   - `realtor_name`, `realtor_phone`
   - `exclusive_rate` (전용률)
   - `acquisition_tax`, `registration_tax`, `broker_fee`

2. **수집 로직(`extract_useful_details`) 확장**
   - `articlePrice` → 보증금/월세/매매/전세/관리비 분리 추출
   - `articleRealtor` → 중개사 정보 추출
   - `articleFacility` → 시설 정보 확장
   - `articleTax` → 세금 정보 추출

3. **DB 변환 로직(`json_to_db_converter.py`) 수정**
   - 새로 추가된 컬럼에 매핑
   - 기존 `details(jsonb)`에만 저장되던 값들을 컬럼으로 분리 저장

---

## 3. 중기 개선 (구조 리팩토링)
1. **테이블 정규화**
   - `properties` → 핵심 식별자만 유지
   - `property_prices` → 가격 관련
   - `property_spaces` → 면적/층수 관련
   - `property_facilities` → 시설 관련
   - `property_images` → 이미지 관련
   - `property_realtors` → 중개사 관련
   - `property_taxes` → 세금 관련

2. **장점**
   - 관리 용이성 증가
   - 확장성 확보
   - 쿼리 성능 최적화
   - 데이터 무결성 강화

---

## 4. 장기 개선 (운영 최적화)
1. **데이터 품질 관리**
   - `data_quality_score` 자동 산출 로직 개선
   - 누락 필드 검증 자동화

2. **검색/분석 최적화**
   - 자주 조회되는 필드(가격, 면적, 위치, 중개사명 등)는 반드시 컬럼화
   - 나머지는 `details(jsonb)`에 보관

3. **마이그레이션 전략**
   - 신규 테이블 생성 후 점진적 데이터 이전
   - 기존 `properties` 테이블은 호환성을 위해 유지하되, 점차 축소

---

## ✅ 결론
- **단기적으로는 누락된 핵심 컬럼 추가 및 매핑 개선**이 필요
- **중기적으로는 테이블 정규화**를 통해 구조적 문제 해결
- **장기적으로는 데이터 품질 관리 및 검색 최적화**를 통해 안정적 운영 기반 마련
