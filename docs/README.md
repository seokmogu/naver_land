# 네이버 부동산 수집기 v3.0

실제 API 분석 결과를 바탕으로 제작된 정확한 매물 수집기

## 주요 파일

1. **fixed_naver_collector.py** - 메인 수집기 (분석된 실제 API 패턴 사용)
2. **playwright_token_collector.py** - JWT 토큰 자동 수집
3. **api_analyzer.py** - API 패턴 분석기 (개발용)

## 사용법

```bash
# 실행
python3 fixed_naver_collector.py

# URL 입력 예시
https://new.land.naver.com/offices?ms=37.522786,127.0466693,15&a=SG:SMS:GJCG:APTHGJ:GM:TJ&e=RETAIL
```

## 수집 과정

1. **JWT 토큰 자동 획득** - Playwright로 실제 브라우저에서 토큰 캡처
2. **좌표 → 지역코드 변환** - `/api/cortars` API로 지역코드 조회
3. **매물 데이터 수집** - `/api/articles` API로 실제 매물 수집
4. **결과 저장** - JSON 형태로 상세 통계와 함께 저장

## 특징

- 실제 네이버 부동산과 동일한 API 패턴 사용
- 오피스/상가 전용 매물 타입 지원
- 페이지네이션 자동 처리
- 상세 통계 및 샘플 데이터 제공