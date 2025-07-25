# 네이버 부동산 데이터 수집기 사용 가이드

## 🎯 완성된 시스템 개요

이 시스템은 **네이버 부동산 API**를 통해 매물 데이터를 수집하고, **카카오 API**로 정확한 주소 정보를 추가하는 완전한 솔루션입니다.

## 📁 필수 파일 구성

```
production_files/
├── naver_land_smart_collector.py     # 메인 수집기 (토큰 자동 관리)
├── cluster_based_collector.py        # 클러스터 기반 고효율 수집기 (신규)
├── complete_address_converter.py     # 좌표→주소 변환기
├── token.txt                         # JWT 토큰 (자동 갱신)
├── requirements_selenium.txt         # 필요한 패키지 목록
├── complete_address_*.json          # 수집된 최종 데이터 (JSON)
└── complete_address_*.csv           # 수집된 최종 데이터 (CSV)
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements_selenium.txt

# Chrome 설치 (Ubuntu/Debian)
sudo apt-get install google-chrome-stable
```

### 2. 데이터 수집 실행

#### 방법 1: 기본 수집기 (법정동 기반)
```bash
# 토큰 자동 관리 방식
python naver_land_smart_collector.py
```

#### 방법 2: 클러스터 수집기 (고효율)
```bash
# 클러스터 API를 활용한 대규모 수집
python cluster_based_collector.py
```

### 3. 주소 정보 추가
```bash
# 수집된 데이터에 완전한 주소 정보 추가
python complete_address_converter.py
```

## 📊 수집 가능한 데이터

### 매물 기본 정보
- 매물번호, 매물명, 거래타입 (매매/전세/월세)
- 가격 정보 (보증금, 월세)
- 면적 정보 (전용/공급면적)
- 층수, 방향, 건물명
- 등록일, 중개사 정보

### 완전한 주소 정보 (카카오 API)
- **행정구역**: 시도, 시군구, 읍면동, 법정동코드
- **지번 주소**: 정확한 지번 (예: 746, 735-35)
- **도로명 주소**: 도로명, 건물명, 우편번호
- **특수 정보**: 산 여부, 지하 여부

## 🔧 주요 기능

### 1. 스마트 토큰 관리
- ✅ 자동 토큰 획득 (Selenium)
- ✅ 토큰 재사용 (3시간 유효)
- ✅ 만료 시 자동 갱신
- ✅ 파일 기반 캐싱

### 2. 대량 데이터 수집
- ✅ 법정동별 전체 페이지 수집
- ✅ 중복 제거 자동 처리
- ✅ API 제한 방지 딜레이
- ✅ 에러 복구 및 재시도

### 3. 클러스터 기반 수집 (신규)
- ✅ 넓은 지역을 효율적으로 스캔
- ✅ 매물 밀집 지역 자동 감지
- ✅ 병렬 처리로 고속 수집
- ✅ 격자 분할 방식 지원

### 4. 완전한 주소 변환
- ✅ 좌표→주소 배치 처리
- ✅ 병렬 처리로 고속 변환
- ✅ 캐시 시스템으로 중복 방지
- ✅ API 제한 자동 관리

## 📈 성능 현황

- **발견된 총 매물**: 6,402개 (클러스터 분석)
- **실제 수집 가능**: 2,000+ 개 (법정동별)
- **주소 변환 성공률**: 96% (도로명) + 4% (지번)
- **수집 속도**: 페이지당 20개, 초당 약 10-20개

## 🎛️ 사용자 정의

### 수집 지역 변경

#### 기본 수집기 (법정동 기반)
```python
# naver_land_smart_collector.py 파일에서
params = {
    "cortarNo": "1168010100",  # 변경: 다른 법정동 코드
    "realEstateType": "SMS",   # 변경: APT(아파트), OFT(오피스텔)
    "tradeType": "A1",         # 변경: A1(매매), B1(전세), B2(월세)
    # ...
}
```

#### 클러스터 수집기 (좌표 기반)
```python
# cluster_based_collector.py 실행 시
# 옵션 1: 클러스터 기반 수집
center_lat = 37.5665    # 서울시청 위도
center_lng = 126.9780   # 서울시청 경도

# 옵션 2: 격자 분할 수집
bounds = {
    'bottomLat': 37.490,  # 남쪽 경계
    'topLat': 37.510,     # 북쪽 경계
    'leftLon': 127.020,   # 서쪽 경계
    'rightLon': 127.040   # 동쪽 경계
}
```

### 수집 범위 조정
```python
# 페이지 수 제한
articles = collector.collect_data(params, max_pages=10)  # 10페이지만

# 가격 범위 설정  
params.update({
    "priceMin": "50000",      # 5억 이상
    "priceMax": "200000",     # 20억 이하
})
```

## 🔑 API 키 설정

### 카카오 REST API 키
```python
# complete_address_converter.py에서
api_key = "640ac7eb1709ff36aa818f09e8dfbe7d"  # 현재 키
```

## 📋 데이터 출력 형식

### CSV 필드 구성
```
매물번호, 매물명, 거래타입, 보증금/매매가, 월세, 전용면적,
건물명_원본, 기존주소, 위도, 경도,
시도, 시군구, 읍면동, 법정동코드,
지번주소, 지번, 본번, 부번, 산여부,
도로명주소, 건물명_카카오, 지하여부,
완전주소, 주소타입, 우편번호, 중개사
```

## ⚠️ 주의사항

1. **JWT 토큰**: 3시간마다 자동 갱신, 수동 설정 불필요
2. **API 제한**: 
   - 네이버: 요청 간격 0.1초 이상 권장
   - 카카오: 초당 5회, 일일 300,000회 제한
3. **Chrome 브라우저**: Selenium 동작을 위해 필수 설치
4. **데이터 용도**: 개인 연구/분석 목적으로만 사용

## 🛠️ 문제 해결

### 토큰 오류 (401)
```bash
# 토큰 파일 삭제 후 재실행
rm token.txt
python naver_land_smart_collector.py
```

### Chrome 드라이버 오류
```bash
# webdriver-manager가 자동 해결
pip install --upgrade webdriver-manager
```

### 메모리 부족
```bash
# 수집 범위를 줄여서 실행
# max_pages=50 정도로 제한
```

## 📞 기술 지원

시스템 구성 요소:
- **언어**: Python 3.12+
- **주요 라이브러리**: Selenium, Requests, Pandas
- **외부 API**: 네이버 부동산, 카카오 로컬
- **브라우저**: Chrome + ChromeDriver

---

**🎉 축하합니다! 완전한 네이버 부동산 데이터 수집 시스템이 준비되었습니다.**