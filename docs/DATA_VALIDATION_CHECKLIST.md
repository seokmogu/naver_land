# 네이버 부동산 데이터 수집/DB 매핑 검증 문서

## 1. 원본 API 응답 구조
- 주요 섹션:
  - `articleDetail`: 매물 기본/상세 정보 (건물명, 용도, 주차, 층수, 상세 설명 등)
  - `articleAddition`: 대표 이미지(`representativeImgUrl`), 요약 정보, 태그, 가격 요약
  - `articleFacility`: 건물 시설 (에어컨, 엘리베이터 등)
  - `articleFloor`: 총 층수, 지하/지상 층수
  - `articlePrice`: 보증금, 월세, 매매가 등 정규화된 가격 정보
  - `articleRealtor`: 중개사무소 정보 (이름, 연락처, 주소, 프로필 이미지 등)
  - `articleSpace`: 공급/전용 면적, 전용률
  - `articleTax`: 취득세, 등록세, 중개보수 등
  - `articlePhotos`: 다수의 현장 사진 배열

## 2. 현재 수집 로직 (`extract_useful_details`)
- 반영되는 필드:
  - 건물정보: 법적용도, 주차대수, 주차가능 여부, 엘리베이터 여부, 층구조
  - 위치정보: 위도, 경도, 노출주소, 지하철 도보시간
  - 비용정보: 월관리비, 관리비 포함항목(하드코딩)
  - 입주정보: 입주가능일, 협의가능여부
  - 이미지: 현장사진수(`siteImageCount`), 대표이미지(`representativeImgUrl`)
  - 주변시세: 동일주소 매물수, 최고가, 최저가
  - 상세설명: `detailDescription` (200자 제한)
  - 카카오주소변환 (옵션)

- 누락된 필드:
  - `articlePhotos` (대표 이미지 외 다수 사진)
  - `articleFacility` (시설 정보)
  - `articlePrice` (보증금, 세부 가격)
  - `articleRealtor` (중개사 정보)
  - `articleFloor`, `articleSpace`, `articleTax` 등

## 3. DB 변환 로직 (`json_to_db_converter.py`)
- DB에 반영되는 필드:
  - 기본 정보: `article_no`, `article_name`, `real_estate_type`, `trade_type`, `cortar_no`, `collected_date`, `is_active`, `created_at`, `updated_at`
  - 가격: `price`(매매가), `rent_price`(월세)
  - 면적: `area1`(전용), `area2`(공급)
  - 층: `floor_info`, `floor`
  - 기타: `direction`, `tag_list`, `description`
  - 상세정보(`details` dict 전체 저장)
    - 카카오 주소 변환: `address_road`, `address_jibun`, `building_name`, `postal_code`
    - 위치정보: `latitude`, `longitude`
    - 추가 상세: `room_count`, `bathroom_count`, `parking_info`, `heating_type`, `approval_date`

- DB에 반영되지 않는 필드:
  - 이미지 배열(`articlePhotos`)
  - 중개사 정보(`articleRealtor`)
  - 세부 가격(`articlePrice`)
  - 시설 정보(`articleFacility`)
  - 층/건물 구조(`articleFloor`)
  - 공간 정보(`articleSpace`)
  - 세금 정보(`articleTax`)

## 4. Supabase DB 스키마 확인 필요
- 실제 DB 테이블(`properties` 등)에 어떤 컬럼이 정의되어 있는지 확인 필요
- Supabase MCP 서버를 토큰과 함께 실행해야 `list_tables`, `list_columns`로 확인 가능

---

## ✅ 결론
- 현재 수집기는 원본 API의 모든 데이터를 반영하지 않고 있음
- 특히 **이미지 배열(articlePhotos), 중개사 정보(articleRealtor), 가격 세부(articlePrice), 시설 정보(articleFacility)** 등이 누락
- DB 변환 단계에서도 이들 필드가 매핑되지 않음
- Supabase DB 스키마를 확인하여, 누락된 필드 중 어떤 것을 DB에 반영할지 결정해야 함
