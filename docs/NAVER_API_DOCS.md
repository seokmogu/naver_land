# 네이버 부동산 API 구조 문서

분석 일시: 2025-08-04  
분석 대상: `https://new.land.naver.com/offices` 페이지

## 📡 API 엔드포인트 요약

### 1. 핵심 매물 API
- **지역코드 조회**: `/api/cortars`
- **매물 목록**: `/api/articles` ⭐ 
- **클러스터 매물**: `/api/articles/clusters`
- **관심 매물**: `/api/interests/articles`

### 2. 부가 정보 API
- **개발계획**: `/api/developmentplan/*`
- **지하철역**: `/api/developmentplan/station/list`
- **철도**: `/api/developmentplan/rail/list`

## 🎯 주요 API 상세

### `/api/cortars` - 지역코드 조회

**요청:**
```
GET /api/cortars?zoom=15&centerLat=37.522786&centerLon=127.0466693
```

**응답:**
```json
[
  {
    "cortarNo": "1168010400",
    "cortarName": "역삼동",
    "cortarVertexLists": [...]
  }
]
```

### `/api/articles` - 매물 목록 조회 ⭐

**요청:**
```
GET /api/articles?cortarNo=1168010400&order=rank&realEstateType=SG:SMS:GJCG:APTHGJ:GM:TJ&tradeType=&tag=::::::::&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&priceType=RETAIL&page=1&articleState
```

**필수 파라미터:**
- `cortarNo`: 지역코드 (필수!)
- `order`: 정렬 (rank, priceDesc, priceAsc 등)
- `realEstateType`: 매물 타입
- `priceType`: 가격 타입 (RETAIL=상업용)
- `page`: 페이지 번호

**매물 타입 코드:**
- `SG`: 상가
- `SMS`: 상가주택
- `GJCG`: 근린생활시설
- `APTHGJ`: 아파트형 공장
- `GM`: 기타
- `TJ`: 토지

**응답 구조:**
```json
{
  "articleList": [
    {
      "articleNo": "2541710494",
      "articleName": "일반상가", 
      "realEstateTypeCode": "SG",
      "realEstateTypeName": "상가",
      "tradeTypeCode": "B2",
      "tradeTypeName": "월세",
      "floorInfo": "3/5",
      "rentPrc": "170",
      "dealOrWarrantPrc": "2,000",
      "area1": 315,
      "area2": 130,
      "direction": "동향",
      "articleConfirmYmd": "20250804",
      "articleFeatureDesc": "무권리 대로변 사무실 학원 운동시설등 추천 주차편리",
      "tagList": ["25년이상", "중층", "주차가능", "총5층"],
      "buildingName": "일반상가",
      "latitude": "37.37068",
      "longitude": "127.114833",
      "realtorName": "금손공인중개사무소",
      "cpName": "부동산뱅크"
    }
  ],
  "articleCount": 1234,
  "articleTotalCount": 1234
}
```

## 📋 매물 데이터 필드 설명

### 기본 정보
- `articleNo`: 매물 고유번호
- `articleName`: 매물명
- `buildingName`: 건물명
- `articleStatus`: 매물 상태 (R0=일반)

### 부동산 타입
- `realEstateTypeCode`: 부동산 타입 코드 (SG, SMS 등)
- `realEstateTypeName`: 부동산 타입명 (상가, 상가주택 등)
- `articleRealEstateTypeCode`: 세부 타입 코드 (D02=상가점포)
- `articleRealEstateTypeName`: 세부 타입명

### 거래 정보
- `tradeTypeCode`: 거래 타입 코드 (A1=매매, B1=전세, B2=월세)
- `tradeTypeName`: 거래 타입명
- `dealOrWarrantPrc`: 매매가/보증금 (만원, 쉼표 포함 문자열)
- `rentPrc`: 월세 (만원 단위 문자열)
- `priceChangeState`: 가격 변동 상태 (SAME, UP, DOWN)

### 면적 및 층수
- `area1`: 전용면적 (㎡)
- `area2`: 공급면적 (㎡)  
- `floorInfo`: 층 정보 ("3/5" = 3층/총5층)
- `direction`: 방향 (동향, 서향 등)

### 위치 정보
- `latitude`: 위도 (문자열)
- `longitude`: 경도 (문자열)
- `isLocationShow`: 위치 표시 여부
- `detailAddress`: 상세 주소
- `virtualAddressYn`: 가상 주소 여부

### 부가 정보
- `articleConfirmYmd`: 매물 확인일 (YYYYMMDD)
- `articleFeatureDesc`: 매물 특징 설명
- `tagList`: 태그 목록 (배열)
- `siteImageCount`: 사이트 이미지 수
- `sameAddrCnt`: 같은 주소 매물 수

### 중개사 정보
- `realtorName`: 공인중개사명
- `realtorId`: 중개사 ID
- `cpName`: 중개업체명
- `cpid`: 중개업체 ID
- `cpPcArticleUrl`: PC 매물 URL

### 검증 정보
- `verificationTypeCode`: 검증 타입 (OWNER=소유자 검증)
- `tradeCheckedByOwner`: 소유자 거래 확인 여부
- `isDirectTrade`: 직거래 여부
- `isSafeLessorOfHug`: HUG 안전임대 여부

## 🔐 인증

모든 API 요청에는 JWT 토큰이 필요합니다:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

토큰은 브라우저에서 네이버 부동산 페이지 접속 시 자동 발급됩니다.

## 🔄 페이지네이션

- 한 페이지당 최대 20개 매물
- `page` 파라미터로 페이지 이동
- `articleCount`: 현재 조건의 총 매물 수
- `articleTotalCount`: 전체 매물 수

## ⚠️ 주의사항

1. **지역코드 필수**: `cortarNo` 없이는 매물 조회 불가
2. **토큰 만료**: JWT 토큰은 약 3시간 후 만료
3. **Rate Limit**: 과도한 요청 시 제한 가능
4. **가격 형식**: 쉼표 포함 문자열로 반환 ("2,000")

## 📝 사용 예시

```python
# 1. 지역코드 조회
cortar_response = requests.get(
    "https://new.land.naver.com/api/cortars",
    params={"zoom": 15, "centerLat": 37.522786, "centerLon": 127.0466693},
    headers={"Authorization": f"Bearer {token}"}
)

# 2. 매물 조회
articles_response = requests.get(
    "https://new.land.naver.com/api/articles",
    params={
        "cortarNo": "1168010400",
        "order": "rank",
        "realEstateType": "SG:SMS:GJCG:APTHGJ:GM:TJ",
        "priceType": "RETAIL",
        "page": 1
    },
    headers={"Authorization": f"Bearer {token}"}
)
```