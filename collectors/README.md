# 네이버 부동산 수집기

네이버 부동산 데이터를 수집하고 분석하는 통합 시스템입니다. 스마트 경계 기반 탐지, 카카오 주소 변환, Supabase 연동 등의 기능을 제공합니다.

## 📁 파일 구조

### 🚀 메인 실행 파일
- `fixed_naver_collector.py` - 메인 수집기 (주소 변환 포함)
- `batch_collection_scheduler.py` - 배치 수집 스케줄러
- `smart_boundary_collector.py` - 스마트 경계 기반 지역 분석기

### 🔧 지원 모듈
- `playwright_token_collector.py` - JWT 토큰 수집기
- `kakao_address_converter.py` - 카카오 주소 변환기

### ⚙️ 설정 파일
- `config.json` - API 키 등 실제 설정 (git 제외)
- `config.template.json` - 배포용 설정 템플릿
- `gu_config.json` - 구별 수집 설정

### 🧪 테스트 및 설정
- `test_integrated_collector.py` - 통합 기능 테스트
- `setup_deployment.py` - 배포 환경 설정

### 📊 결과 폴더
- `results/` - 모든 수집 결과 저장 (git 제외)

## 🏗️ 시스템 아키텍처

### 데이터 수집 파이프라인
```
1. 지역 탐지 (smart_boundary_collector.py)
   ↓ 네이버 경계 데이터 활용
2. 매물 수집 (fixed_naver_collector.py)
   ↓ 무한스크롤 시뮬레이션
3. 주소 변환 (kakao_address_converter.py)
   ↓ 좌표 → 실제 주소
4. 데이터 저장
   ├─ 원본: GCS 압축 저장 (백업)
   └─ 핵심: Supabase 저장 (쿼리)
```

### 인프라 구성
- **수집 서버**: Google Cloud Compute Engine (e2-micro 무료)
- **원본 저장**: Google Cloud Storage (~$0.21/월)
- **쿼리 DB**: Supabase PostgreSQL ($0-25/월)
- **API 서버**: Cloud Run 또는 Supabase Edge Functions

## 💾 데이터 저장 전략

### Supabase 테이블 구조
```sql
-- 지역 마스터 정보
areas (cortar_no, gu_name, dong_name, boundary_points)

-- 매물 핵심 정보 (일별 업데이트)
properties (article_no, price, area, address, lat/lon)

-- 일별 통계 (대시보드용)
daily_stats (date, total_count, avg_price, changes)

-- 가격 변동 이력
price_history (article_no, price, change_date)
```

### 저장 용량 예상
- **일일**: 300,000개 매물 × 500 bytes = 150MB
- **월간**: 4.5GB (Supabase) + 4.5GB (GCS 압축)
- **비용**: 월 $5-30 (규모에 따라)

## 🚀 사용법

### 1. 초기 설정
```bash
python setup_deployment.py
```

### 2. 통합 테스트
```bash
python test_integrated_collector.py
```

### 3. 지역 분석 (스마트 경계 기반)
```bash
python smart_boundary_collector.py 강남구
```

### 4. 배치 수집
```bash
python batch_collection_scheduler.py results/smart_areas_강남구_YYYYMMDD_HHMMSS.json
```

## 📋 주요 기능

### 핵심 기능
- ✅ JWT 토큰 자동 수집 (Playwright)
- ✅ 무한스크롤 시뮬레이션 (21페이지, 420개 매물)
- ✅ 상세정보 수집 (건물정보, 위치, 비용 등)
- ✅ 카카오 주소 변환 (좌표 → 실제 주소)
- ✅ 메모리 효율적 스트리밍 저장

### 지역 탐지 (신규)
- ✅ 스마트 경계 기반 완전한 지역 탐지
- ✅ 네이버 실제 경계 데이터 (cortarVertexLists) 활용
- ✅ 구 경계 내부만 효율적 스캔
- ✅ 3일 캐싱으로 반복 스캔 방지

### 데이터 관리
- ✅ 배치 스케줄링 시스템
- ✅ GCS + Supabase 하이브리드 저장
- ✅ 일별 통계 자동 생성
- ✅ 가격 변동 추적

## ⚙️ 환경 설정

### 카카오 API 키 설정
1. https://developers.kakao.com 에서 REST API 키 발급
2. `python setup_deployment.py` 실행하여 설정
3. 또는 `config.json`에서 직접 수정

### Supabase 설정
1. https://supabase.com 에서 프로젝트 생성
2. 환경변수 설정:
```bash
export SUPABASE_URL="your-project-url"
export SUPABASE_KEY="your-anon-key"
```

### Google Cloud 설정
1. GCS 버킷 생성 (백업용)
2. 서비스 계정 키 다운로드
3. 환경변수 설정:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
```

## 🚀 순차 실행 가이드

### 일일 수집 프로세스
```bash
# 1. 지역 정보 수집 (첫 실행시만)
python smart_boundary_collector.py 강남구

# 2. 매물 수집 실행
python batch_collection_scheduler.py results/smart_areas_강남구_*.json

# 3. 또는 자동화 스크립트
python daily_collection.py 강남구
```

### 수집 데이터 흐름
```
네이버 API → 수집기 → 카카오 주소 변환
                ↓
        ┌─────────────────┐
        │  데이터 분할    │
        └─────────────────┘
                ↓
    ┌───────────┴───────────┐
    │                       │
원본 압축 → GCS          핵심 데이터 → Supabase
(백업용)                 (쿼리/API용)
```

## 📊 개발 방법론

### 완전성 우선 접근
- 매물 밀도보다 모든 정보 수집 우선
- 네이버 실제 경계 데이터 활용
- 누락 없는 전수 조사 방식

### 효율성 전략
- 경계 기반 스마트 스캔 (불필요한 영역 제외)
- 3일 캐싱으로 반복 작업 방지
- 스트리밍 저장으로 메모리 최적화

### 비용 최적화
- GCP 무료 티어 최대 활용
- 데이터 압축 (90% 압축률)
- 하이브리드 저장 (원본+쿼리용 분리)