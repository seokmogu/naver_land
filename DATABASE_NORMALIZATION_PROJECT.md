# 네이버 부동산 수집기 DB 정규화 프로젝트

## 🎯 프로젝트 개요

현재 50개 컬럼의 단일 `properties` 테이블 (86,839개 매물)을 정규화된 다중 테이블 구조로 전환하여 데이터 무결성, 성능, 확장성을 대폭 개선하는 프로젝트

### 현재 상황 분석

#### 현재 시스템 구조
- **단일 테이블**: `properties` (50개 컬럼, 86,839개 매물)
- **API 구조**: 8개 섹션 데이터 수집 가능
- **수집 시스템**: `/collectors/core/` 최적화된 로그 기반 수집기
- **문제점**: 데이터 중복, 성능 저하, 확장성 제약, 정규화 부족

#### API 데이터 구조 (8개 섹션)
```
네이버 부동산 API 응답:
├── articleDetail      # 매물 기본/상세 정보
├── articleAddition    # 추가 정보 (이미지, 태그)
├── articleFacility    # 건물 시설 정보
├── articleFloor       # 층 정보
├── articlePrice       # 상세 가격 정보
├── articleRealtor     # 중개사 정보
├── articleSpace       # 공간/면적 정보
├── articleTax         # 세금 정보
└── articlePhotos      # 현장 사진 배열
```

#### 현재 수집 시스템의 한계
- **누락 데이터**: 중개사 정보, 현장 사진, 상세 가격, 시설 정보
- **단일 테이블**: 모든 정보를 `properties` 테이블에 JSONB로 저장
- **성능 이슈**: 86,839개 레코드의 단일 테이블
- **확장성 부족**: 새로운 데이터 타입 추가 시 스키마 변경 필요

## 🏗️ 새로운 정규화된 DB 구조 설계

### 1. 핵심 테이블 구조

#### 1.1 매물 기본 정보 (`properties`)
```sql
CREATE TABLE properties (
    id BIGSERIAL PRIMARY KEY,
    article_no VARCHAR(50) UNIQUE NOT NULL,
    article_name VARCHAR(500),
    real_estate_type_id INTEGER REFERENCES real_estate_types(id),
    trade_type_id INTEGER REFERENCES trade_types(id),
    region_id INTEGER REFERENCES regions(id),
    collected_date DATE NOT NULL,
    last_seen_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.2 가격 정보 (`property_prices`)
```sql
CREATE TABLE property_prices (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    price_type VARCHAR(20), -- 'sale', 'rent', 'deposit', 'maintenance'
    amount BIGINT,
    currency VARCHAR(10) DEFAULT 'KRW',
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.3 위치 정보 (`property_locations`)
```sql
CREATE TABLE property_locations (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    address_road VARCHAR(500),
    address_jibun VARCHAR(500),
    building_name VARCHAR(200),
    postal_code VARCHAR(10),
    cortar_no VARCHAR(20),
    walking_to_subway INTEGER, -- minutes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.4 물리적 정보 (`property_physical`)
```sql
CREATE TABLE property_physical (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    area_exclusive DECIMAL(10, 2), -- 전용면적
    area_supply DECIMAL(10, 2),    -- 공급면적
    floor_current INTEGER,         -- 해당 층
    floor_total INTEGER,           -- 총 층수
    floor_underground INTEGER,     -- 지하층수
    room_count INTEGER,
    bathroom_count INTEGER,
    direction VARCHAR(20),
    parking_count INTEGER,
    parking_possible BOOLEAN,
    elevator_available BOOLEAN,
    heating_type VARCHAR(50),
    approval_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.5 중개사 정보 (`realtors`)
```sql
CREATE TABLE realtors (
    id BIGSERIAL PRIMARY KEY,
    realtor_name VARCHAR(200) NOT NULL,
    business_number VARCHAR(50),
    phone_number VARCHAR(20),
    address VARCHAR(500),
    profile_image_url TEXT,
    license_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.6 매물-중개사 관계 (`property_realtors`)
```sql
CREATE TABLE property_realtors (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    realtor_id BIGINT REFERENCES realtors(id),
    listing_date DATE,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.7 이미지 정보 (`property_images`)
```sql
CREATE TABLE property_images (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    image_url TEXT NOT NULL,
    image_type VARCHAR(20), -- 'main', 'interior', 'exterior', 'floor_plan'
    image_order INTEGER DEFAULT 0,
    caption VARCHAR(500),
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.8 시설 정보 (`property_facilities`)
```sql
CREATE TABLE property_facilities (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    facility_id INTEGER REFERENCES facility_types(id),
    available BOOLEAN DEFAULT true,
    notes VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.9 세금 정보 (`property_taxes`)
```sql
CREATE TABLE property_taxes (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    tax_type VARCHAR(30), -- 'acquisition', 'registration', 'broker_fee'
    tax_amount DECIMAL(15, 2),
    tax_rate DECIMAL(5, 4),
    calculated_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.10 가격 변동 이력 (`price_history`)
```sql
CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES properties(id),
    price_type VARCHAR(20),
    previous_amount BIGINT,
    new_amount BIGINT,
    change_amount BIGINT,
    change_percent DECIMAL(6, 2),
    changed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 참조 테이블 (Reference Tables)

#### 2.1 부동산 유형 (`real_estate_types`)
```sql
CREATE TABLE real_estate_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(10) UNIQUE,
    type_name VARCHAR(50),
    category VARCHAR(30)
);
```

#### 2.2 거래 유형 (`trade_types`)
```sql
CREATE TABLE trade_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(10) UNIQUE,
    type_name VARCHAR(50)
);
```

#### 2.3 지역 정보 (`regions`)
```sql
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    cortar_no VARCHAR(20) UNIQUE,
    dong_name VARCHAR(100),
    gu_name VARCHAR(50),
    city_name VARCHAR(50),
    center_lat DECIMAL(10, 8),
    center_lon DECIMAL(11, 8),
    area DECIMAL(15, 2),
    population INTEGER
);
```

#### 2.4 시설 유형 (`facility_types`)
```sql
CREATE TABLE facility_types (
    id SERIAL PRIMARY KEY,
    facility_code VARCHAR(20) UNIQUE,
    facility_name VARCHAR(100),
    category VARCHAR(50)
);
```

### 3. 인덱스 전략

#### 3.1 성능 최적화 인덱스
```sql
-- 기본 검색 인덱스
CREATE INDEX idx_properties_article_no ON properties(article_no);
CREATE INDEX idx_properties_active ON properties(is_active, last_seen_date);
CREATE INDEX idx_properties_region ON properties(region_id);
CREATE INDEX idx_properties_type ON properties(real_estate_type_id, trade_type_id);

-- 가격 검색 인덱스
CREATE INDEX idx_property_prices_property ON property_prices(property_id, price_type);
CREATE INDEX idx_property_prices_amount ON property_prices(amount, price_type);

-- 위치 검색 인덱스
CREATE INDEX idx_property_locations_coords ON property_locations USING GIST (point(longitude, latitude));
CREATE INDEX idx_property_locations_region ON property_locations(cortar_no);

-- 물리적 속성 인덱스
CREATE INDEX idx_property_physical_area ON property_physical(area_exclusive);
CREATE INDEX idx_property_physical_floor ON property_physical(floor_current, floor_total);

-- 이미지 조회 인덱스
CREATE INDEX idx_property_images_property ON property_images(property_id, image_type, image_order);

-- 가격 이력 인덱스
CREATE INDEX idx_price_history_property_date ON price_history(property_id, changed_date);
```

#### 3.2 복합 인덱스
```sql
-- 복합 검색용 인덱스
CREATE INDEX idx_properties_search ON properties(region_id, real_estate_type_id, is_active);
CREATE INDEX idx_property_prices_search ON property_prices(price_type, amount, valid_from, valid_to);
CREATE INDEX idx_property_physical_search ON property_physical(area_exclusive, floor_current);
```

## 📊 데이터 마이그레이션 전략

### Phase 1: 준비 단계 (1-2일)
1. **현재 DB 스키마 완전 분석**
2. **새로운 스키마 생성 및 테스트**
3. **데이터 변환 로직 개발**
4. **마이그레이션 스크립트 개발**

### Phase 2: 참조 데이터 마이그레이션 (1일)
1. **지역 정보 (`regions`) 마이그레이션**
2. **부동산/거래 유형 마이그레이션**
3. **시설 유형 데이터 구축**

### Phase 3: 메인 데이터 마이그레이션 (2-3일)
1. **매물 기본 정보 마이그레이션**
2. **가격 정보 정규화**
3. **위치/물리적 정보 분리**
4. **중개사 정보 정규화**

### Phase 4: 관계형 데이터 구축 (1-2일)
1. **매물-중개사 관계 구축**
2. **이미지 정보 구조화**
3. **시설 정보 매핑**
4. **가격 이력 재구성**

### Phase 5: 검증 및 최적화 (1-2일)
1. **데이터 무결성 검증**
2. **성능 테스트**
3. **인덱스 최적화**
4. **쿼리 성능 확인**

## 🔧 수집 로직 개선

### 1. 새로운 데이터 수집 모듈

#### 1.1 섹션별 데이터 처리기
```python
class EnhancedDataProcessor:
    def process_article_detail(self, data): # 기본 매물 정보
    def process_article_addition(self, data): # 추가 정보
    def process_article_facility(self, data): # 시설 정보
    def process_article_floor(self, data): # 층 정보
    def process_article_price(self, data): # 가격 정보
    def process_article_realtor(self, data): # 중개사 정보
    def process_article_space(self, data): # 공간 정보
    def process_article_tax(self, data): # 세금 정보
    def process_article_photos(self, data): # 사진 정보
```

#### 1.2 정규화된 DB 저장 로직
```python
class NormalizedDBSaver:
    def save_property_main(self, property_data): # 기본 매물 정보
    def save_property_prices(self, property_id, price_data): # 가격 정보
    def save_property_location(self, property_id, location_data): # 위치 정보
    def save_property_physical(self, property_id, physical_data): # 물리적 정보
    def save_realtor_info(self, realtor_data): # 중개사 정보
    def save_property_images(self, property_id, images_data): # 이미지 정보
    def save_facility_info(self, property_id, facilities_data): # 시설 정보
    def save_tax_info(self, property_id, tax_data): # 세금 정보
```

### 2. 누락 데이터 보완 전략

#### 2.1 중개사 정보 수집
- **articleRealtor** 섹션 완전 활용
- 중개사 정보 정규화 및 중복 제거
- 연락처, 프로필 이미지, 라이선스 정보 포함

#### 2.2 현장 사진 수집
- **articlePhotos** 배열 완전 처리
- 이미지 분류 (메인, 실내, 외부, 도면)
- 이미지 메타데이터 (크기, 순서) 저장

#### 2.3 상세 가격 정보
- **articlePrice** 섹션 활용
- 보증금, 월세, 관리비 세분화
- 가격 변동 추적 개선

#### 2.4 시설 정보 확장
- **articleFacility** 완전 매핑
- 시설 유형 표준화
- 시설별 상세 정보 저장

## ⚡ 성능 최적화 계획

### 1. 쿼리 최적화
- **인덱스 전략**: 복합 인덱스 활용
- **파티셔닝**: 날짜별/지역별 분할
- **뷰 활용**: 자주 사용하는 조인 쿼리

### 2. 캐싱 전략
- **Redis 캐싱**: 자주 조회되는 매물 정보
- **결과 캐싱**: 복잡한 집계 쿼리 결과
- **이미지 CDN**: 이미지 전용 캐시

### 3. 데이터베이스 최적화
- **연결 풀링**: 효율적인 DB 연결 관리
- **배치 처리**: 대량 데이터 처리 최적화
- **트랜잭션 관리**: 데이터 일관성 보장

## 🧪 테스트 및 검증 계획

### 1. 데이터 무결성 테스트
- **참조 무결성**: FK 제약조건 검증
- **데이터 일치성**: 마이그레이션 후 데이터 비교
- **누락 데이터**: 마이그레이션 중 손실 확인

### 2. 성능 테스트
- **쿼리 성능**: 기존 vs 새로운 구조 비교
- **동시성 테스트**: 다중 사용자 환경 시뮬레이션
- **대용량 테스트**: 100만 레코드 수준 테스트

### 3. 기능 테스트
- **수집 로직**: 새로운 구조로 데이터 수집
- **API 응답**: 기존 API 호환성 확인
- **대시보드**: 모니터링 시스템 호환성

## 📈 예상 성과

### 1. 성능 개선
- **쿼리 성능**: 80% 향상 (적절한 인덱싱)
- **저장 공간**: 30% 절약 (정규화)
- **동시성**: 5배 향상 (테이블 분리)

### 2. 데이터 품질
- **중복 제거**: 100% (정규화)
- **데이터 무결성**: 95% 향상 (FK 제약)
- **확장성**: 무제한 (모듈형 구조)

### 3. 개발 효율성
- **유지보수**: 60% 감소 (명확한 스키마)
- **기능 추가**: 80% 빠른 개발
- **버그 감소**: 70% 감소 (타입 안전성)

## 🗓️ 상세 일정

### Week 1: 분석 및 설계
- **Day 1-2**: 현재 시스템 완전 분석
- **Day 3-4**: 새로운 스키마 설계 및 검토
- **Day 5**: 마이그레이션 전략 수립

### Week 2: 개발 및 테스트
- **Day 1-2**: 마이그레이션 스크립트 개발
- **Day 3-4**: 새로운 수집 로직 개발
- **Day 5**: 테스트 환경 구축 및 초기 테스트

### Week 3: 마이그레이션 및 검증
- **Day 1-2**: 데이터 마이그레이션 실행
- **Day 3-4**: 데이터 무결성 검증
- **Day 5**: 성능 테스트 및 최적화

### Week 4: 배포 및 모니터링
- **Day 1-2**: 프로덕션 배포
- **Day 3-4**: 모니터링 및 버그 수정
- **Day 5**: 문서화 및 팀 교육

## 🚨 리스크 관리

### 1. 기술적 리스크
- **데이터 손실**: 완전한 백업 및 롤백 계획
- **성능 저하**: 단계적 배포 및 모니터링
- **호환성 문제**: 철저한 테스트

### 2. 운영 리스크
- **서비스 중단**: 점진적 마이그레이션
- **사용자 경험**: 기존 API 호환성 유지
- **팀 학습 곡선**: 상세한 문서화

### 3. 완화 전략
- **백업 계획**: 매 단계별 롤백 가능
- **모니터링**: 실시간 성능 추적
- **알림 시스템**: 문제 발생 시 즉시 대응

---

*이 프로젝트는 네이버 부동산 수집기의 데이터 품질, 성능, 확장성을 근본적으로 개선하여 향후 5년간의 성장 기반을 마련하는 핵심 인프라 프로젝트입니다.*