# 🏠 네이버 부동산 데이터 수집기

네이버 부동산에서 매물 정보를 자동으로 수집하여 정규화된 데이터베이스에 저장하는 시스템입니다.

## ✨ 주요 기능

- **8개 API 섹션 완전 활용**: articleDetail, articleAddition, articleFacility, articleFloor, articlePrice, articleRealtor, articleSpace, articleTax
- **정규화된 데이터베이스 구조**: Supabase를 활용한 관계형 데이터베이스
- **자동 토큰 갱신**: Playwright를 통한 자동 토큰 관리
- **카카오 주소 변환**: 정확한 위치 정보 보강
- **실시간 모니터링**: 수집 진행 상황 실시간 추적

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 생성)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key  
KAKAO_REST_API_KEY=your_kakao_key
```

### 2. 수집 실행

```bash
# 전체 강남구 수집
./start_collection.sh

# 또는 Python으로 직접 실행
python3 enhanced_data_collector.py
```

### 3. 모니터링

```bash
# 실시간 모니터링 대시보드
python3 monitor.py

# 30초마다 새로고침 (기본값)
python3 monitor.py --interval 30
```

## 📊 데이터베이스 구조

### 주요 테이블
- `properties_new`: 기본 매물 정보
- `property_physical`: 물리적 특성 (면적, 층수 등)
- `property_locations`: 위치 정보
- `property_prices`: 가격 정보
- `property_images`: 매물 사진
- `realtors`: 중개사 정보

## 🛠️ 프로젝트 구조

```
naver_land/
├── enhanced_data_collector.py    # 메인 수집기
├── start_collection.sh          # 실행 스크립트
├── monitor.py                   # 모니터링 도구
├── collectors/                  # 핵심 모듈들
│   ├── core/                   # 핵심 컴포넌트
│   ├── monitoring/             # 모니터링 도구들
│   └── config/                 # 설정 파일들
├── archived/                   # 아카이브된 파일들
└── logs/                      # 로그 파일들
```

## 🎯 수집 통계 (현재)

- **총 매물**: 26,800+개
- **수집 지역**: 강남구 14개 동
- **매물 이미지**: 17,000+개
- **데이터 완성도**: 77.5%

## 🔧 최근 개선사항

### Modified Clean Slate 방식 적용
- **130개+ 파일** → **20개 이하**로 정리
- **무한 반복 문제** 근본적 해결
- **개발자 경험** 대폭 개선

### API 필드 매핑 수정
- **30% 데이터 손실 문제** 해결
- **실제 API 응답 구조** 완전 파악
- **백업 로직** 추가로 안정성 향상

## 📈 성능

- **수집 속도**: 약 20매물/분
- **메모리 사용량**: 평균 200MB
- **토큰 갱신**: 자동 (3시간마다)
- **에러 복구**: 자동 재시도

## ⚠️ 주의사항

1. **토큰 갱신**: 3시간마다 자동으로 토큰이 갱신됩니다
2. **API 제한**: 과도한 요청 시 차단될 수 있습니다
3. **데이터 품질**: 정기적인 데이터 검증을 권장합니다

## 🤝 기여

이 프로젝트는 학술 연구 목적으로 개발되었습니다. 
상업적 이용은 네이버의 이용약관을 확인해주세요.

## 📞 지원

문제가 발생하면 다음을 확인해주세요:

1. **토큰 상태**: `python3 monitor.py`
2. **로그 확인**: `collectors/logs/` 디렉토리
3. **환경변수**: `.env` 파일 설정

---

**마지막 업데이트**: 2025-08-30  
**버전**: v2.0 (Modified Clean Slate)