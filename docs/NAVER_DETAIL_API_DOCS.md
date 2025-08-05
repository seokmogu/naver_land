# 네이버 부동산 매물 상세 API 문서

분석 일시: 2025-08-04  
발견된 API: `/api/articles/{articleNo}?complexNo=`

## 🎯 매물 상세 정보 API

### API 엔드포인트
```
GET /api/articles/{articleNo}?complexNo=
```

**예시:**
- `GET /api/articles/2541178466?complexNo=`
- `GET /api/articles/2541203479?complexNo=`

### 호출 방법
매물 목록에서 개별 매물을 클릭하면 자동으로 호출됩니다.

## 📋 응답 구조

매물 상세 API는 **2개의 주요 객체**로 구성됩니다:

### 1. `articleDetail` - 상세 정보
### 2. `articleAddition` - 추가 정보

## 🏢 articleDetail 필드 설명

### 기본 정보
- `articleNo`: 매물 고유번호
- `articleName`: 매물명 ("복합상가")
- `articleSubName`: 매물 부제목
- `buildingTypeName`: 건물 타입명
- `cortarNo`: 지역코드

### 노출 및 상태 정보
- `exposeStartYMD`: 노출 시작일 ("20250802")
- `exposeEndYMD`: 노출 종료일 ("20250901")
- `articleConfirmYMD`: 매물 확인일
- `tradeCompleteYN`: 거래 완료 여부 ("N")
- `articleStatusCode`: 매물 상태 코드 ("R0")

### 건물 정보
- `totalDongCount`: 총 동 수
- `tradeBuildingTypeCode`: 거래 건물 타입 ("SPOFC")
- `buildingTypeCode`: 건물 타입 코드 ("D0204")
- `lawUsage`: 법적 용도 ("제2종 근린생활시설")

### 위치 정보 (상세)
- `latitude`: 위도 (문자열, 더 정밀)
- `longitude`: 경도 (문자열, 더 정밀)
- `pnu`: 부동산 고유번호 ("1168010400101210028")
- `cityNo`: 시/도 코드
- `cityName`: 시/도명 ("서울시")
- `divisionName`: 구/군명 ("강남구")
- `sectionName`: 동/읍/면명 ("청담동")
- `exposureAddress`: 노출 주소
- `detailAddress`: 상세 주소
- `virtualAddressYn`: 가상 주소 여부
- `walkingTimeToNearSubway`: 지하철역까지 도보 시간(분)

### 거래 정보 (상세)
- `realestateTypeCode`: 부동산 타입 코드
- `realestateTypeName`: 부동산 타입명
- `tradeTypeCode`: 거래 타입 코드
- `tradeTypeName`: 거래 타입명
- `verificationTypeCode`: 검증 타입 ("SITE", "OWNER")
- `verificationTypeName`: 검증 타입명 ("현장", "소유자")
- `directTradeYN`: 직거래 여부

### 입주 정보
- `moveInTypeCode`: 입주 타입 코드 ("MV001")
- `moveInTypeName`: 입주 타입명 ("즉시입주")
- `moveInDiscussionPossibleYN`: 입주 협의 가능 여부
- `moveInPossibleYmd`: 입주 가능일 ("NOW")

### 관리비 및 부대시설
- `monthlyManagementCost`: 월 관리비 (숫자)
- `parkingCount`: 주차 가능 대수
- `parkingPossibleYN`: 주차 가능 여부
- `roomCount`: 방 개수 ("-")
- `bathroomCount`: 화장실 개수 ("-")

### 건물 구조
- `duplexYN`: 복층 여부
- `floorLayerName`: 층 구조 ("단층")
- `hasBuildingUnitInfo`: 건물 단위 정보 보유 여부

### 설명 및 특징
- `articleFeatureDescription`: 매물 특징 설명
- `detailDescription`: 상세 설명 (긴 텍스트)
- `tagList`: 태그 목록 (배열)

### 기타 플래그
- `applyYN`: 적용 여부
- `mapLocationIndicationYn`: 지도 위치 표시 여부
- `isInterest`: 관심 매물 여부
- `isFalseHoodDeclared`: 허위 신고 여부
- `kisoConnectionYN`: 국토정보시스템 연결 여부
- `isComplex`: 복합 매물 여부
- `isOwnerTradeCompleted`: 소유자 거래 완료 여부
- `isSafeLessorOfHug`: HUG 안전임대 여부

## 🏠 articleAddition 필드 설명

### 기본 정보 (중복)
- `articleNo`: 매물 번호
- `articleName`: 매물명
- `articleStatus`: 매물 상태
- `realEstateTypeCode`: 부동산 타입 코드
- `realEstateTypeName`: 부동산 타입명

### 가격 정보 (목록과 동일)
- `dealOrWarrantPrc`: 매매가/보증금
- `rentPrc`: 월세
- `priceChangeState`: 가격 변동 상태
- `isPriceModification`: 가격 수정 여부

### 면적 및 층수 (목록과 동일)
- `area1`: 전용면적
- `area2`: 공급면적
- `floorInfo`: 층 정보
- `direction`: 방향

### 이미지 정보 (추가)
- `representativeImgUrl`: 대표 이미지 URL
- `representativeImgTypeCode`: 대표 이미지 타입
- `representativeImgThumb`: 썸네일 크기
- `siteImageCount`: 현장 이미지 수

### 기타 (목록과 동일)
- `articleConfirmYmd`: 매물 확인일
- `articleFeatureDesc`: 매물 특징 설명
- `tagList`: 태그 목록

## 🔍 추가 발견된 API

### 대출 정보 API
```
GET /api/loan/article/loan?legalDivisionCode={cortarNo}&warrantAmount={amount}
```

**예시:**
```
GET /api/loan/article/loan?legalDivisionCode=1168010400&warrantAmount=30000
```

## 💡 주요 차이점: 목록 vs 상세

| 구분 | 목록 API | 상세 API |
|------|---------|----------|
| **위치 정보** | 간단한 위도/경도 | 정밀한 좌표 + PNU + 상세 주소 |
| **건물 정보** | 기본 정보만 | 건물 타입, 법적 용도, 층 구조 |
| **입주 정보** | 없음 | 입주 타입, 가능일, 협의 여부 |
| **관리비** | 없음 | 월 관리비 |
| **주차 정보** | 없음 | 주차 대수, 가능 여부 |
| **설명** | 간단한 특징 | 상세 설명 + 특징 설명 |
| **이미지** | 이미지 수만 | 대표 이미지 URL + 썸네일 |
| **지하철** | 없음 | 도보 시간 |
| **검증** | 검증 타입만 | 검증 타입 + 이름 |

## 🚀 활용 방법

```python
# 1. 매물 목록 조회
articles = get_articles_list(cortar_no, page=1)

# 2. 각 매물의 상세 정보 조회
for article in articles:
    article_no = article['articleNo']
    detail = requests.get(
        f"https://new.land.naver.com/api/articles/{article_no}",
        params={"complexNo": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    detail_data = detail.json()
    article_detail = detail_data['articleDetail']
    article_addition = detail_data['articleAddition']
```

## ⚠️ 주의사항

1. **추가 요청 필요**: 각 매물마다 별도 API 호출 필요
2. **Rate Limit**: 너무 많은 요청 시 제한 가능
3. **토큰 공유**: 동일한 JWT 토큰 사용
4. **complexNo 파라미터**: 빈 값으로 설정

## 📊 데이터 품질

상세 API는 목록 API보다 **5배 이상 많은 정보**를 제공하며, 특히 다음 정보가 추가됩니다:

- 📍 정밀한 위치 정보 (PNU, 상세 주소)  
- 🏢 건물 상세 정보 (법적 용도, 구조)
- 💰 관리비 정보
- 🚗 주차 정보  
- 🚇 지하철 접근성
- 📝 상세 설명 텍스트
- 🖼️ 이미지 URL