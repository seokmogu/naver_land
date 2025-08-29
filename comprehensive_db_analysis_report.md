# 네이버 부동산 수집기 데이터베이스 구조 분석 보고서

**분석 일시**: 2025년 8월 28일 22시  
**분석자**: Database Administrator  
**데이터베이스**: Supabase (eslhavjipwbyvbbknixv.supabase.co)

---

## 📋 분석 요약

### 현재 DB 상태
- **총 테이블 수**: 6개 (핵심 테이블 모두 존재)
- **총 레코드 수**: 99,307개
- **데이터 보존 기간**: 22일 (2025-08-05 ~ 2025-08-27)
- **시스템 상태**: ✅ 정상 운영 중

### 데이터 규모
- **활성 매물**: 77,591개
- **비활성 매물**: 9,248개 (10.6%)
- **가격 변동 이력**: 2,473건
- **삭제 이력**: 9,245건
- **수집 로그**: 672건
- **일별 통계**: 64건

---

## 🗄️ 테이블 구조 분석

### 1. `areas` (지역 정보) - 14개 레코드
**목적**: 네이버 부동산 수집 대상 지역 관리
```sql
CREATE TABLE areas (
    cortar_no VARCHAR PRIMARY KEY,    -- 행정구역코드 (PK)
    gu_name VARCHAR,                  -- 구 이름
    dong_name VARCHAR,                -- 동 이름  
    center_lat FLOAT,                 -- 중심 위도
    center_lon FLOAT,                 -- 중심 경도
    boundary_points JSONB,            -- 경계 좌표 (비어있음)
    zoom_level INTEGER,               -- 지도 줌 레벨
    created_at TIMESTAMP,             -- 생성일시
    updated_at TIMESTAMP              -- 수정일시
);
```

**현재 상태**:
- ✅ 정상: 강남구 14개 동 데이터 존재
- ⚠️ 문제: `boundary_points` 필드가 모두 비어있음
- 💡 개선: 다른 지역 확장 시 추가 데이터 필요

### 2. `properties` (매물 정보) - 86,839개 레코드
**목적**: 네이버 부동산 매물 데이터 저장 및 관리  
**컬럼 수**: 50개 (매우 상세한 정보 저장)

**핵심 필드**:
```sql
CREATE TABLE properties (
    id BIGINT PRIMARY KEY,            -- 자동 증가 ID
    article_no VARCHAR UNIQUE,        -- 매물 번호 (네이버 ID)
    cortar_no VARCHAR,                -- 지역 코드
    
    -- 매물 기본 정보
    article_name VARCHAR,             -- 매물명
    real_estate_type VARCHAR,         -- 부동산 타입
    trade_type VARCHAR,               -- 거래 타입 (매매/전세/월세)
    price INTEGER,                    -- 가격 (만원)
    rent_price INTEGER,               -- 월세 (만원)
    
    -- 면적 정보
    area1 FLOAT,                      -- 전용면적
    area2 FLOAT,                      -- 공급면적
    floor_info VARCHAR,               -- 층 정보 ("2/6")
    direction VARCHAR,                -- 방향
    
    -- 위치 정보
    latitude FLOAT,                   -- 위도
    longitude FLOAT,                  -- 경도
    address_road VARCHAR,             -- 도로명 주소
    address_jibun VARCHAR,            -- 지번 주소
    address_detail VARCHAR,           -- 상세 주소
    building_name VARCHAR,            -- 건물명
    postal_code VARCHAR,              -- 우편번호
    
    -- 부가 정보
    tag_list JSONB,                   -- 태그 배열
    description TEXT,                 -- 설명
    details JSONB,                    -- 상세 정보 (전체)
    
    -- 수집/관리 정보
    collected_date DATE,              -- 수집 날짜
    last_seen_date DATE,              -- 마지막 확인 날짜  
    is_active BOOLEAN DEFAULT TRUE,   -- 활성 상태
    created_at TIMESTAMP,             -- 생성일시
    updated_at TIMESTAMP,             -- 수정일시
    
    -- 추가 상세 정보 (총 50개 컬럼)
    parking_available BOOLEAN,
    elevator_available BOOLEAN,
    building_age INTEGER,
    maintenance_fee INTEGER,
    heating_type VARCHAR,
    structure_type VARCHAR,
    completion_date DATE,
    move_in_date VARCHAR,
    images JSONB,
    -- ... 등등
);
```

**현재 상태**:
- ✅ 정상: 86,839개 매물 데이터 저장
- ✅ 활성 매물: 77,591개 (89.4%)
- ⚠️ 문제점:
  - `building_age`: 100% NULL
  - `completion_date`: 100% NULL  
  - `last_price_change_date`: 100% NULL
- 💡 개선: 누락된 필드 수집 로직 보완 필요

### 3. `price_history` (가격 변동 이력) - 2,473개 레코드
**목적**: 매물 가격/월세 변동 추적
```sql
CREATE TABLE price_history (
    id BIGINT PRIMARY KEY,
    article_no VARCHAR,               -- 매물 번호 (FK)
    trade_type VARCHAR,               -- 거래 타입
    previous_price INTEGER,           -- 이전 가격
    new_price INTEGER,                -- 신규 가격
    previous_rent_price INTEGER,      -- 이전 월세
    new_rent_price INTEGER,           -- 신규 월세
    change_amount INTEGER,            -- 가격 변동금액
    change_percent DECIMAL,           -- 가격 변동률
    rent_change_amount INTEGER,       -- 월세 변동금액
    rent_change_percent DECIMAL,      -- 월세 변동률
    changed_date DATE                 -- 변동 날짜
);
```

**현재 상태**:
- ✅ 정상: 2,473건의 가격 변동 기록
- ✅ 기간: 2025-08-05 ~ 2025-08-27
- ✅ 월세 변동도 함께 추적

### 4. `deletion_history` (삭제 이력) - 9,245개 레코드  
**목적**: 삭제된 매물 추적 및 감사
```sql
CREATE TABLE deletion_history (
    id BIGINT PRIMARY KEY,
    article_no VARCHAR,               -- 매물 번호
    deleted_date DATE,                -- 삭제 날짜
    deletion_reason VARCHAR,          -- 삭제 사유
    days_active INTEGER,              -- 활성 기간 (일)
    final_price INTEGER,              -- 최종 가격
    final_rent_price INTEGER,         -- 최종 월세
    final_trade_type VARCHAR,         -- 최종 거래타입
    cortar_no VARCHAR,                -- 지역 코드
    real_estate_type VARCHAR          -- 부동산 타입
);
```

**현재 상태**:
- ✅ 정상: 9,245건의 삭제 이력 보관
- ✅ 기간: 2025-08-18 ~ 2025-08-27
- 💡 활용: 매물 생명주기 분석 가능

### 5. `collection_logs` (수집 로그) - 672개 레코드
**목적**: 데이터 수집 과정 모니터링
```sql
CREATE TABLE collection_logs (
    id BIGINT PRIMARY KEY,
    gu_name VARCHAR,                  -- 구 이름
    dong_name VARCHAR,                -- 동 이름  
    cortar_no VARCHAR,                -- 지역 코드
    collection_type VARCHAR,          -- 수집 타입
    -- ... 기타 로그 정보
);
```

### 6. `daily_stats` (일별 통계) - 64개 레코드
**목적**: 일별 수집 현황 통계
```sql  
CREATE TABLE daily_stats (
    id BIGINT PRIMARY KEY,
    stat_date DATE,                   -- 통계 날짜
    cortar_no VARCHAR,                -- 지역 코드
    total_count INTEGER,              -- 총 매물 수
    new_count INTEGER,                -- 신규 매물 수
    -- ... 기타 통계 정보
);
```

---

## ⚡ 성능 분석 결과

### 쿼리 성능 테스트
| 쿼리 유형 | 실행 시간 | 레코드 수 | 상태 |
|----------|----------|----------|------|
| 전체 활성 매물 조회 | 0.615초 | 1,000개 | ✅ 정상 |
| 지역별 매물 조회 | 0.091초 | 100개 | ✅ 양호 |
| 최근 가격 변동 조회 | 0.075초 | 7개 | ✅ 양호 |
| 날짜별 매물 조회 | 0.080초 | 100개 | ✅ 양호 |

### 성능 이슈
- **느린 쿼리**: 전체 활성 매물 조회 (0.615초)
- **원인**: `is_active` 컬럼에 인덱스 부재
- **영향**: 대용량 데이터 조회 시 성능 저하

---

## 📊 데이터 품질 분석

### 데이터 분포
- **지역 분포**: 강남구 14개 동 중심
- **거래 타입**: 매매 100% (샘플 데이터 기준)
- **부동산 타입**: 건물 100% (샘플 데이터 기준)

### 품질 이슈
1. **높은 NULL 비율**: 일부 컬럼에서 100% NULL
   - `building_age`: 건물 연도 정보 없음
   - `completion_date`: 준공일 정보 없음  
   - `last_price_change_date`: 마지막 가격 변경일 없음

2. **데이터 검증**:
   - ✅ 중복 매물: 없음
   - ✅ 가격 이상치: 극단값 없음
   - ✅ 필수 필드: 정상

---

## 📈 데이터 증가 현황

### 수집 현황 (최근 30일)
- **총 매물 추가**: 86,839개
- **일평균**: 2,894.6개/일
- **가격 변동**: 2,473건 (82.4건/일)

### 수집 현황 (최근 7일)  
- **총 매물 추가**: 1,772개
- **일평균**: 253.1개/일
- **가격 변동**: 7건

### 성장 패턴
- 📈 **안정적 성장**: 꾸준한 데이터 수집
- ⚠️ **최근 감소**: 7일 평균이 30일 평균보다 낮음
- 💡 **점검 필요**: 수집기 동작 상태 확인

---

## 🔒 백업 및 보안 상태

### 데이터 보존 정책
- **보존 기간**: 22일 (단기간)
- **백업 전략**: 미구현 상태
- **복구 계획**: 미수립

### 보안 상태
- **접근 제어**: Supabase 기본 보안
- **암호화**: HTTPS 전송 암호화
- **감사 로그**: 수집 로그만 존재

---

## ❌ 발견된 문제점

### 1. 성능 문제
- **인덱스 부족**: 주요 쿼리에 필요한 인덱스 없음
- **복합 쿼리 최적화**: 지역+상태 조건 쿼리 느림

### 2. 데이터 품질 문제  
- **필드 누락**: 중요 정보들이 수집되지 않음
- **검증 부족**: 데이터 품질 검증 로직 미흡

### 3. 운영 관리 문제
- **백업 정책 없음**: 데이터 손실 위험
- **모니터링 부족**: 성능/장애 감지 체계 없음
- **용량 계획 없음**: 데이터 증가에 따른 용량 계획 부재

### 4. 아키텍처 문제
- **확장성**: 단일 지역(강남구)에만 집중
- **중복 제거**: 매물 중복 방지 로직 미흡
- **이력 관리**: 변경 이력 추적 불완전

---

## 💡 개선 권장사항

### 1. 즉시 개선 (우선순위 높음)

#### 성능 최적화
```sql
-- 필수 인덱스 추가
CREATE INDEX idx_properties_cortar_active ON properties(cortar_no, is_active);
CREATE INDEX idx_properties_collected_date ON properties(collected_date DESC);
CREATE INDEX idx_properties_updated_at ON properties(updated_at DESC);
CREATE INDEX idx_price_history_changed_date ON price_history(changed_date DESC);
CREATE INDEX idx_price_history_article_no ON price_history(article_no);

-- 복합 인덱스 (자주 사용되는 조합)
CREATE INDEX idx_properties_trade_type_active ON properties(trade_type, is_active);
CREATE INDEX idx_properties_real_estate_type_active ON properties(real_estate_type, is_active);
```

#### 데이터 품질 개선
1. **수집 로직 보완**: NULL 필드 수집 로직 개선
2. **유효성 검사**: 가격, 면적 등 범위 검증
3. **중복 방지**: UNIQUE 제약조건 강화

### 2. 단기 개선 (1-2주)

#### 백업 및 복구 체계
1. **자동 백업 설정**:
   - 일간: properties, price_history
   - 주간: 전체 DB  
   - 월간: 장기 아카이브

2. **백업 검증**: 정기적인 복구 테스트

#### 모니터링 시스템
1. **성능 모니터링**: 느린 쿼리 감지
2. **데이터 수집 모니터링**: 실패/지연 알림  
3. **용량 모니터링**: 디스크 사용량 추적

### 3. 중기 개선 (1-2개월)

#### 데이터 아키텍처 개선
1. **파티셔닝**: 날짜별 테이블 분할
2. **아카이빙**: 오래된 데이터 별도 보관
3. **읽기 전용 복제본**: 분석 쿼리 분리

#### 확장성 개선
1. **다지역 지원**: 강남구 외 지역 확장
2. **스키마 버전 관리**: 스키마 변경 이력 추적
3. **API 계층**: 데이터 접근 추상화

### 4. 장기 개선 (3-6개월)

#### 고급 기능
1. **실시간 분석**: 가격 동향 실시간 분석
2. **머신러닝**: 가격 예측 모델
3. **데이터 웨어하우스**: OLAP 분석 환경

#### 운영 자동화
1. **CI/CD 파이프라인**: 스키마 변경 자동화
2. **장애 복구**: 자동 failover 구성
3. **캐싱 레이어**: Redis 등 캐시 도입

---

## 📋 액션 아이템

### 🚨 즉시 실행 (24시간 내)
1. [ ] 필수 인덱스 5개 추가
2. [ ] 느린 쿼리 모니터링 설정
3. [ ] 수동 백업 1회 실행

### ⏰ 이번 주 내
1. [ ] 자동 백업 스크립트 작성
2. [ ] 데이터 품질 검증 스크립트 개발
3. [ ] 성능 모니터링 대시보드 구축

### 📅 이번 달 내  
1. [ ] NULL 필드 수집 로직 개선
2. [ ] 용량 계획 및 아카이빙 정책 수립
3. [ ] 다지역 확장 계획 수립

---

## 📊 메트릭 및 KPI

### 성능 지표
- **쿼리 응답 시간**: < 0.5초 목표
- **처리량**: 10,000 req/sec 목표  
- **가용성**: 99.9% 목표

### 데이터 품질 지표
- **완전성**: NULL 비율 < 10%
- **정확성**: 검증 통과율 > 95%
- **일관성**: 중복률 < 0.1%

### 운영 지표
- **백업 성공률**: 100%
- **복구 시간**: RTO 4시간, RPO 1시간
- **모니터링 커버리지**: 100%

---

## 🎯 결론

**현재 상태**: 네이버 부동산 수집기의 데이터베이스는 **기본적인 기능은 정상 동작**하고 있으나, **운영 및 성능 최적화가 필요**한 상태입니다.

**주요 강점**:
- ✅ 안정적인 데이터 수집 (일평균 2,894개)
- ✅ 완전한 스키마 구조 (6개 핵심 테이블)
- ✅ 가격 변동 추적 시스템 동작

**주요 위험**:
- ❌ 백업 체계 부재 (데이터 손실 위험)
- ❌ 성능 최적화 미흡 (확장성 제한)
- ❌ 모니터링 부족 (장애 대응 지연)

**권장 조치**: 즉시 성능 최적화와 백업 체계 구축을 진행하고, 단계적으로 운영 안정성을 강화해야 합니다.

---

*본 분석은 실제 데이터베이스 연결을 통해 수행되었으며, 2025년 8월 28일 시점의 정확한 현황을 반영합니다.*