# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

네이버 부동산 데이터 수집기 v2.0 - 네이버 부동산 매물 정보를 수집, 파싱, 저장하는 리팩토링된 Python 애플리케이션

## 실행 명령어

### 기본 수집 명령어
```bash
# 특정 지역 수집 (논현동 예시)
python main.py --area 1168010700 --max-articles 10

# 특정 매물 수집
python main.py --article 2390390123

# 강남구 전체 수집
python main.py --gangnam --max-pages 2
```

### 데이터베이스 관리
```bash
# PostgreSQL 직접 연결로 테이블 정리 (DDL 실행)
python direct_postgres_cleanup.py
```

### 환경 설정
`.env` 파일에 필수 환경변수 설정 필요:
- `SUPABASE_URL`: Supabase 프로젝트 URL
- `SUPABASE_KEY`: Supabase Service Role Key  
- `SUPABASE_PASSWORD`: PostgreSQL 비밀번호
- `DATABASE_URL`: PostgreSQL 직접 연결 URL
- `KAKAO_REST_API_KEY`: 카카오 주소 변환 API 키 (선택사항)

## 아키텍처 구조

### 모듈화된 레이어 아키텍처
프로젝트는 단일 책임 원칙에 따라 5개 레이어로 분리:

1. **config/** - 중앙화된 설정 관리
   - `settings.py`: 모든 환경변수와 설정값 통합 관리

2. **collectors/** - 외부 API 호출 레이어
   - `naver_api_client.py`: 네이버 부동산 API 호출
   - `base_collector.py`: 수집기 추상 클래스
   - `core/kakao_address_converter.py`: 기존 카카오 주소 변환기 (레거시)

3. **parsers/** - 데이터 변환 레이어  
   - `article_parser.py`: 네이버 API 응답을 구조화된 데이터로 파싱

4. **database/** - 데이터 영속성 레이어
   - `supabase_client.py`: Supabase 연결 관리
   - `repository.py`: 데이터베이스 저장 로직

5. **services/** - 비즈니스 로직 레이어
   - `collection_service.py`: 전체 수집 프로세스 조율 (메인 오케스트레이터)
   - `address_service.py`: 카카오 주소 변환 서비스

### 데이터 플로우
1. `main.py` → `CollectionService` (진입점)
2. `CollectionService` → `NaverAPIClient` (API 호출)
3. `ArticleParser` → 구조화된 데이터 변환
4. `AddressService` → 좌표→주소 변환 (선택적)
5. `PropertyRepository` → Supabase 저장

### 중요한 설계 결정사항

**데이터베이스 연결**:
- Supabase Python 클라이언트: SELECT/INSERT/UPDATE 작업용
- PostgreSQL 직접 연결 (`psycopg2`): DDL(DROP TABLE) 작업용
- 이유: Supabase 클라이언트는 DDL 실행에 제약이 있음

**오류 처리 및 재시도**:
- API 호출 실패시 지수 백오프 재시도
- 429 Rate Limit 감지시 자동 대기
- 각 레이어별 독립적인 오류 처리

**설정 관리**:
- 환경변수 우선, 코드 내 기본값 제공
- `settings.py`에서 모든 설정 중앙화
- `.env` 파일로 로컬 개발 환경 지원

## 데이터 구조

### 네이버 API 섹션
매물 데이터는 8개 섹션으로 구성:
- `articleDetail`: 기본 정보 (가격, 면적, 층수)
- `articleAddition`: 추가 정보 (주변 시세 비교) 
- `articleFacility`: 편의시설 (지하철, 편의점)
- `articleFloor`: 층수 정보
- `articlePrice`: 가격 상세
- `articleRealtor`: 중개사 정보
- `articleSpace`: 면적 상세  
- `articleTax`: 세금 정보
- `articlePhotos`: 매물 사진

### 지역 코드
강남구 동별 코드 예시:
- 신사동: 1168010600
- 논현동: 1168010700  
- 압구정동: 1168010800
- 청담동: 1168011000

## 레거시 코드 처리

`enhanced_data_collector.py` (90K+ 라인)는 DEPRECATED 상태:
- 모든 로직이 단일 파일에 집중되어 있던 구버전
- 새로운 모듈화된 구조로 완전 대체됨
- 파일 헤더에 사용 중단 경고 포함

## 테스트 및 임시 파일 관리 규칙

### 테스트 파일 생성 원칙
- **모든 테스트/실험용 코드는 `test/` 폴더 내에서만 생성**
- 루트 디렉토리나 다른 모듈 폴더에 테스트 파일 생성 금지
- 테스트 파일 명명 규칙: `test_*.py`, `sample_*.py`, `temp_*.py`

### 테스트 파일 생명주기
1. **생성**: `test/` 폴더 내에서만 생성
2. **실행**: 테스트 목적으로 임시 사용
3. **정리**: 테스트 완료 후 즉시 제거
4. **보존**: 테스트를 통해 확인된 중요한 정보는 CLAUDE.md에 업데이트

### 테스트를 통해 확인된 중요 사실들
- **PostgreSQL 직접 연결 필요성**: Supabase Python 클라이언트는 DDL(DROP TABLE) 실행 불가
- **API Rate Limiting**: 네이버 부동산 API는 429 에러로 속도 제한 적용
- **환경변수 우선순위**: `.env` 파일 → 환경변수 → 코드 기본값 순으로 적용
- **데이터베이스 PASSWORD**: `SFHjy2PqCcMaMjVe` (DATABASE_URL에 포함)

### 예시 구조
```
naver_land/
├── config/
├── collectors/
├── parsers/
├── database/
├── services/
├── test/          # 모든 테스트 파일은 여기에만
│   ├── test_api.py
│   ├── sample_data.py
│   └── temp_cleanup.py
└── main.py
```